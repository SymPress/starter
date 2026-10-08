#!/usr/bin/env python3
"""Explicit encrypted DB/uploads backup, restore, staging sync, and health checks."""
import argparse
import datetime
import hashlib
import fcntl
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def command(argv, *, cwd=None, stdout=subprocess.PIPE, stdin=None):
    result = subprocess.run(argv, cwd=cwd, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE)
    if result.returncode:
        # WP-CLI/provider diagnostics may contain credentials; never forward them.
        raise RuntimeError("Operation command failed (details withheld); check private service logs.")
    return result.stdout


def config(path, *, monitoring=False):
    value = json.loads(Path(path).read_text())
    if monitoring:
        return value
    root = Path(value['project']).resolve(strict=True)
    if not (root / 'wp-cli.phar').is_file() or not (root / 'public/wp/wp-load.php').is_file():
        raise ValueError('Installed Runtime project and pinned WP-CLI required.')
    value['project'] = root
    return value


def wp(settings, *args):
    return command([settings.get('php', 'php'), '-d', 'display_errors=stderr', str(settings['project'] / 'wp-cli.phar'),
                    '--path=' + str(settings['project'] / 'public/wp'), *args], cwd=settings['project'])


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def backup(settings, output):
    output = Path(output).resolve()
    if output.exists() or not settings.get('age_recipient'):
        raise ValueError('New output path and age_recipient required.')
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='sympress-backup-') as tmp:
        work = Path(tmp)
        # Maintenance mode prevents WordPress writes while taking the pair.
        prior_maintenance = (settings['project'] / 'public/wp/.maintenance').is_file()
        if not prior_maintenance:
            wp(settings, 'maintenance-mode', 'activate')
        try:
            sql = work / 'database.sql'
            wp(settings, 'db', 'export', str(sql), '--single-transaction', '--quick', '--skip-lock-tables')
            uploads = Path(settings.get('uploads', settings['project'] / 'public/wp-content/uploads')).resolve(strict=True)
            if uploads.is_symlink() or not uploads.is_dir():
                raise ValueError('Uploads must be a real directory; deployment shared symlinks are resolved in config.')
            manifest = {'version': 1, 'home': wp(settings, 'option', 'get', 'home').decode().strip(),
                        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        'database_sha256': digest(sql)}
            (work / 'manifest.json').write_text(json.dumps(manifest))
            archive = work / 'backup.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                tar.add(sql, arcname='database.sql')
                tar.add(work / 'manifest.json', arcname='manifest.json')
                tar.add(uploads, arcname='uploads', filter=lambda member: member if member.isfile() or member.isdir() else None)
            command(['age', '--encrypt', '--recipient', settings['age_recipient'], '--output', str(output), str(archive)])
            output.chmod(0o600)
        finally:
            if not prior_maintenance:
                wp(settings, 'maintenance-mode', 'deactivate')


def restore(settings, archive, identity, confirm, *, staging=False, scrub_script=None):
    target = wp(settings, 'option', 'get', 'home').decode().strip()
    environment = wp(settings, 'eval', 'echo wp_get_environment_type();').decode().strip()
    if confirm != target:
        raise ValueError('Confirmation must equal the installed target home URL.')
    if staging and (environment != 'staging' or not scrub_script):
        raise ValueError('Sync requires a staging target and an explicit private scrub PHP script.')
    if staging and wp(settings, 'eval', 'echo apply_filters("pre_wp_mail", null, []) === false ? "blocked" : "enabled";').strip() != b'blocked':
        raise ValueError('Sync requires an active staging mail guard before importing; activate the private Security MU loader or a project-owned guard.')
    if environment == 'production' and not settings.get('allow_production_restore', False):
        raise ValueError('Production restore requires allow_production_restore in private operation config.')
    with tempfile.TemporaryDirectory(prefix='sympress-restore-') as tmp:
        work = Path(tmp)
        decrypted = work / 'backup.tar.gz'
        command(['age', '--decrypt', '--identity', str(Path(identity).resolve(strict=True)), '--output', str(decrypted), str(Path(archive).resolve(strict=True))])
        with tarfile.open(decrypted) as tar:
            # data filter rejects links, device nodes, and paths escaping the workspace.
            if any(not (m.isfile() or m.isdir()) for m in tar.getmembers()):
                raise ValueError('Backup may contain only regular files and directories.')
            tar.extractall(work / 'payload', filter='data')
        payload = work / 'payload'
        if not (payload / 'uploads').is_dir():
            raise ValueError('Backup uploads directory missing.')
        manifest = json.loads((payload / 'manifest.json').read_text())
        if manifest.get('version') != 1 or digest(payload / 'database.sql') != manifest['database_sha256']:
            raise ValueError('Invalid database backup manifest.')
        uploads = Path(settings.get('uploads', settings['project'] / 'public/wp-content/uploads')).resolve(strict=True)
        if uploads.is_symlink() or not uploads.is_dir():
            raise ValueError('Uploads target must be a real directory.')
        wp(settings, 'maintenance-mode', 'activate')
        try:
            wp(settings, 'db', 'import', str(payload / 'database.sql'))
            wp(settings, 'search-replace', manifest['home'], target, '--all-tables-with-prefix', '--skip-columns=guid', '--precise', '--report-changed-only')
            # Keep old media for recovery; publish restored uploads only after DB import.
            previous = uploads.with_name('uploads.before-' + datetime.datetime.now().strftime('%Y%m%d%H%M%S%f'))
            uploads.rename(previous)
            shutil.copytree(payload / 'uploads', uploads)
            if staging:
                wp(settings, 'eval-file', str(Path(scrub_script).resolve(strict=True)))
                wp(settings, 'option', 'update', 'blog_public', '0')
            wp(settings, 'db', 'check')
            wp(settings, 'cache', 'flush')
        except Exception:
            # Remain in maintenance after partial DB/data failures; never claim rollback.
            raise RuntimeError('Restore incomplete; target remains in maintenance. Recover from the pre-restore backup.') from None
        wp(settings, 'maintenance-mode', 'deactivate')


def write_monitor_state(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            os.chmod(temporary, 0o600)
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)



def monitor_logs(settings, prior):
    if settings.get('log_glob'):
        pattern = Path(settings['log_glob'])
        # An existing readable directory may legitimately contain no records yet.
        if not pattern.parent.is_dir():
            raise OSError('Application log directory is unavailable.')
        paths = sorted(path for path in pattern.parent.iterdir()
                       if path.match(pattern.name))
        cursors = prior.get('files', {})
    else:
        paths = [Path(settings['log_file'])]
        cursors = {str(paths[0]): prior}
    healthy = True
    files = {}
    now = int(time.time())
    seen = {key: stamp for key, stamp in prior.get('log_error_seen', {}).items()
            if isinstance(stamp, int) and now - stamp < 86400}
    for path in paths:
        stat = path.stat()
        previous = cursors.get(str(path), {})
        offset = previous.get('offset', 0) if previous.get('inode') == stat.st_ino else 0
        if not prior:
            # First activation establishes a baseline rather than mailing historic incidents.
            offset = stat.st_size
        if offset > stat.st_size:
            offset = 0
        with path.open('rb') as stream:
            stream.seek(offset)
            for line in stream:
                text = line.lower()
                category = next((word for word in
                    (b'.critical:', b'.error:', b'php fatal', b'uncaught') if word in text), None)
                if category is None:
                    continue
                # Retain only severity and PHP location, never exception text or credentials.
                location = re.search(rb'(?:in |at |"file"\s*:\s*")([a-z0-9_./-]+\.php(?::| on line )\d+)', text)
                source = location[1] if location else b'unknown-location'
                if location is None:
                    structured = re.search(rb'"file"\s*:\s*"([a-z0-9_./-]+\.php)"\s*,\s*"line"\s*:\s*(\d+)', text)
                    if structured:
                        source = structured[1] + b':' + structured[2]
                source = re.sub(rb'/releases/[a-z0-9._-]+/', b'/releases/current/',
                                source)
                key = hashlib.sha256(category + source).hexdigest()
                if key not in seen:
                    healthy = False
                    seen[key] = now
            files[str(path)] = {'offset': stream.tell(), 'inode': stat.st_ino}
    state = {'files': files} if settings.get('log_glob') else files[str(paths[0])]
    state['log_error_seen'] = dict(sorted(seen.items(), key=lambda item: item[1])[-256:])
    return healthy, state


class RejectHealthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise urllib.error.HTTPError(request.full_url, code, 'Canonical health endpoint must not redirect.', headers, response)


def open_health(url, timeout=15):
    return urllib.request.build_opener(RejectHealthRedirect()).open(url, timeout=timeout)


def monitor(settings):
    url = settings['health_url']
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password:
        raise ValueError('Monitoring requires a canonical HTTPS health URL without credentials.')
    state = Path(settings['state_file']) if settings.get('state_file') else None
    prior = json.loads(state.read_text()) if state and state.exists() else {}
    next_state = dict(prior)
    health_healthy = True
    logs_healthy = True
    try:
        with open_health(url, timeout=15) as response:
            body = response.read(4097)
            payload = json.loads(body) if len(body) <= 4096 else None
            health_healthy = response.status == 200 and isinstance(payload, dict) and payload.get('status') == 'ok'
        if settings.get('log_file') or settings.get('log_glob'):
            logs_healthy, next_state = monitor_logs(settings, prior)
    except (OSError, ValueError, urllib.error.URLError):
        health_healthy = False
    healthy = health_healthy and logs_healthy
    next_state['health_alerted'] = bool(prior.get('health_alerted')) and not health_healthy
    notify = prior.get('pending_alert', False) or not logs_healthy or (not health_healthy and not next_state['health_alerted'])
    if notify:
        if state:
            # Persist the generic pending alert before advancing the log cursor.
            # A failed delivery survives log rotation and a later healthy poll.
            write_monitor_state(state, {**next_state, 'pending_alert': True})
        recipient = settings.get('alert_recipient')
        if not isinstance(recipient, str) or len(recipient) > 254 or not re.fullmatch(r'[A-Za-z0-9.!#$%&*+_=?^`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', recipient):
            raise ValueError('Select an explicit single alert_recipient before enabling monitoring.')
        # Never send URLs, response bodies, logs or credentials in alerts.
        message = f'To: {recipient}\nSubject: SymPress production health check failed\n\nCheck the private monitoring logs.\n'.encode()
        result = subprocess.run([settings.get('sendmail', '/usr/sbin/sendmail'), '-t'], input=message, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode: raise RuntimeError('Alert delivery failed.')
        if state:
            write_monitor_state(state, {**next_state, 'pending_alert': False, 'health_alerted': not health_healthy})
        return 1
    if state:
        write_monitor_state(state, {**next_state, 'pending_alert': False})
    return 0 if healthy else 1


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    subs = parser.add_subparsers(dest='action', required=True)
    b = subs.add_parser('backup'); b.add_argument('output')
    for name in ('restore', 'sync-staging'):
        r = subs.add_parser(name); r.add_argument('archive'); r.add_argument('--identity', required=True)
        r.add_argument('--confirm', required=True); r.add_argument('--allow-destructive', action='store_true', required=True)
        if name == 'sync-staging': r.add_argument('--scrub-script', required=True)
    subs.add_parser('monitor')
    args = parser.parse_args()
    try:
        settings = config(args.config, monitoring=args.action == 'monitor')
        lock = None
        if args.action != 'monitor':
            lock_path = Path(settings.get('lock_file', settings['project'] / 'var/operations.lock'))
            lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            lock = lock_path.open('a')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'backup': backup(settings, args.output)
        elif args.action == 'monitor': return monitor(settings)
        else: restore(settings, args.archive, args.identity, args.confirm, staging=args.action == 'sync-staging', scrub_script=getattr(args, 'scrub_script', None))
    except (ValueError, RuntimeError, OSError, KeyError, tarfile.TarError) as error:
        # JSON/env values and subprocess output are never printed.
        print('Operation failed: ' + str(error) if isinstance(error, (ValueError, RuntimeError)) else 'Operation failed: check private configuration and services.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
