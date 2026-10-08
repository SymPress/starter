"""Run the complete real recipe on an isolated SSH/MariaDB/FPM host.

Run as root only inside the disposable deploy-host container. Only the systemd
reload boundary and public hostname are replaced. The published PHP verifier
uses real WordPress HTTP over certificate-verified local HTTPS and PHP-FPM.
"""
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import socket
import subprocess
import time


def run(command, **kwargs):
    result = subprocess.run(command, text=True, capture_output=True, timeout=240, **kwargs)
    if result.returncode:
        if os.environ.get('SYMPRESS_DEPLOY_TEST_LOG'):
            Path(os.environ['SYMPRESS_DEPLOY_TEST_LOG']).write_text(result.stdout + result.stderr)
        raise RuntimeError(result.stdout[-5000:] + result.stderr[-1800:])
    return result.stdout


def free_port():
    with socket.socket() as handle:
        handle.bind(('127.0.0.1', 0))
        return handle.getsockname()[1]


def main():
    if os.geteuid() != 0 or os.environ.get('SYMPRESS_DISPOSABLE_DEPLOY_HOST') != '1' or not Path('/usr/sbin/sshd').exists():
        raise RuntimeError('Use the disposable deploy-host container as root.')
    source = Path(__file__).resolve().parents[2]
    base = Path('/srv/sympress_go_probe')
    if base.exists():
        raise RuntimeError('Refusing to overwrite an existing fixture.')
    base.mkdir(mode=0o755)
    home = base / 'home'
    home.mkdir()
    run(['groupadd', '-f', 'sympress-log'])
    try:
        pwd.getpwnam('sympress-probe')
    except KeyError:
        run(['useradd', '-M', '-d', str(home), '-s', '/bin/bash', '-G', 'www-data,sympress-log', 'sympress-probe'])
    password = run(['openssl', 'passwd', '-6', '-stdin'], input=secrets.token_hex(24)).strip()
    run(['usermod', '-p', password, 'sympress-probe'])
    run(['usermod', '-aG', 'sympress-log', 'www-data'])
    identity = pwd.getpwnam('sympress-probe')
    os.chown(base, identity.pw_uid, identity.pw_gid)
    os.chown(home, identity.pw_uid, identity.pw_gid)
    ssh = home / '.ssh'
    ssh.mkdir(mode=0o700)
    key = ssh / 'id_ed25519'
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)])
    shutil.copyfile(str(key) + '.pub', ssh / 'authorized_keys')
    ssh_port = free_port()
    host_key = base / 'host_key'
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(host_key)])
    known_hosts = ssh / 'known_hosts'
    known_hosts.write_text(f'[127.0.0.1]:{ssh_port} ' + Path(str(host_key) + '.pub').read_text())
    for path in ssh.rglob('*'):
        path.chmod(0o600)
        os.chown(path, identity.pw_uid, identity.pw_gid)
    os.chown(ssh, identity.pw_uid, identity.pw_gid)
    ssh_config = base / 'sshd.conf'
    ssh_config.write_text(f'Port {ssh_port}\nListenAddress 127.0.0.1\nHostKey {host_key}\n'
                          f'PidFile {base}/sshd.pid\nAuthorizedKeysFile .ssh/authorized_keys\n'
                          'UsePAM no\nPasswordAuthentication no\nAllowUsers sympress-probe\n'
                          'Subsystem sftp internal-sftp\n')
    Path('/run/sshd').mkdir(exist_ok=True)
    socket_path = base / 'fpm.sock'
    https_port = free_port()
    certificate = base / 'certificate.pem'
    certificate_key = base / 'certificate.key'
    run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-keyout', str(certificate_key), '-out', str(certificate), '-days', '1',
         '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1'])
    fpm_config = base / 'fpm.conf'
    fpm_config.write_text(f'[global]\ndaemonize=no\npid={base}/fpm.pid\nerror_log={base}/fpm.log\n'
                          '[probe]\nuser=www-data\ngroup=www-data\npm=static\npm.max_children=2\n'
                          f'listen={socket_path}\nlisten.owner=sympress-probe\nlisten.group=www-data\n'
                          'listen.mode=0660\nclear_env=yes\nphp_admin_value[opcache.jit_buffer_size]=0\n'
                          'php_admin_value[opcache.jit]=disable\nphp_admin_flag[opcache.enable]=on\n'
                          'php_admin_value[opcache.validate_timestamps]=0\n')
    payload = base / 'payload'
    run(['rsync', '-a', '--exclude=.git', '--exclude=node_modules', '--exclude=.env*',
         '--exclude=var', str(source) + '/', str(payload) + '/'])
    if os.environ.get('SYMPRESS_RUNTIME_SOURCE'):
        runtime = Path(os.environ['SYMPRESS_RUNTIME_SOURCE'])
        for directory in ['src', 'templates']:
            run(['rsync', '-a', str(runtime / directory) + '/', str(payload / 'vendor/sympress/runtime' / directory) + '/'])
    if os.environ.get('SYMPRESS_FRAMEWORK_SOURCE'):
        framework = Path(os.environ['SYMPRESS_FRAMEWORK_SOURCE'])
        run(['rsync', '-a', str(framework / 'src') + '/', str(payload / 'vendor/sympress/framework-bundle/src') + '/'])
    deploy_path = base / 'site'
    (deploy_path / 'shared').mkdir(parents=True)
    nginx_config = base / 'nginx.conf'
    nginx_config.write_text(f'user www-data;\nworker_processes 1;\ndaemon off;\npid {base}/nginx.pid;\n'
                           f'error_log {base}/nginx.log;\nevents {{}}\nhttp {{\n'
                           f'access_log {base}/https-access.log;\nserver {{\n'
                           f'listen 127.0.0.1:{https_port} ssl;\n'
                           f'ssl_certificate {certificate};\nssl_certificate_key {certificate_key};\n'
                           f'root {deploy_path}/current/public;\nindex index.php;\n'
                           'location / { try_files $uri $uri/ /index.php?$args; }\n'
                           'location ~ \\.php$ {\ninclude /etc/nginx/fastcgi_params;\n'
                           'fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;\n'
                           'fastcgi_param HTTPS on;\nfastcgi_param HTTP_HOST fixture.invalid;\n'
                           f'fastcgi_pass unix:{socket_path};\n}}\n}}\n}}\n')
    database = 'sympress_review_deploy_go'
    run(['mariadb', '-e', f'CREATE DATABASE `{database}`; CREATE USER IF NOT EXISTS go_review@127.0.0.1; GRANT ALL ON `{database}`.* TO go_review@127.0.0.1;'])
    env_text = ('WORDPRESS_ENV=production\nWP_HOME=https://fixture.invalid\nWP_SITEURL=${WP_HOME}\n'
                f'DB_HOST=127.0.0.1:3306\nDB_NAME={database}\nDB_USER=go_review\nDB_PASSWORD=\n'
                f'APP_SECRET={secrets.token_hex(32)}\n'
                'SYMPRESS_ENABLE_WORDPRESS_HARDENING=true\nDISALLOW_UNFILTERED_HTML=true\n'
                'ALLOW_UNFILTERED_UPLOADS=false\nWP_HTTP_BLOCK_EXTERNAL=false\n')
    for path in [payload / '.env', deploy_path / 'shared/.env']:
        path.write_text(env_text)
        path.chmod(0o600)
    run(['chown', '-R', 'sympress-probe:sympress-probe', str(payload), str(deploy_path)])
    sudoers = Path('/etc/sudoers.d/sympress-go-probe')
    sudoers.write_text('sympress-probe ALL=(www-data) NOPASSWD: /usr/bin/php ' + str(deploy_path)
                       + '/releases/*/vendor/bin/runtime doctor --production --database-health --php-user=www-data --no-interaction\n')
    sudoers.chmod(0o440)
    environment = os.environ | {'HOME': str(home), 'DEPLOY_HOSTNAME': '127.0.0.1',
                                'DEPLOY_PORT': str(ssh_port), 'DEPLOY_USER': 'sympress-probe',
                                'DEPLOY_PATH': str(deploy_path), 'SYMPRESS_RELEASE_DIRECTORY': str(payload),
                                'SYMPRESS_FPM_SOCKET': str(socket_path), 'GITHUB_SHA': 'a' * 40,
                                'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'safe.directory', 'GIT_CONFIG_VALUE_0': '*'}
    def user_run(command, cwd=payload):
        return run(['sudo', '-E', '-u', 'sympress-probe', *command], cwd=cwd, env=environment)
    # A pristine Core has no tables yet. Run its project WP-CLI commands only
    # after installation; deployment executes the complete Runtime normally.
    user_run(['php', 'vendor/bin/runtime', '--skip', 'db-check', 'wpcli', '-n'])
    tool = payload / 'wp-cli.phar'
    tool_config = json.loads((payload / 'dev-ops/runtime.json').read_text())
    if not tool.exists():
        version = tool_config['wp-cli-version']
        run(['curl', '--fail', '--silent', '--show-error', '--location',
             f'https://github.com/wp-cli/wp-cli/releases/download/v{version}/wp-cli-{version}.phar',
             '--output', str(tool)])
    assert hashlib.sha256(tool.read_bytes()).hexdigest() == tool_config['wp-cli-sha256']
    tool.chmod(0o550)
    os.chown(tool, identity.pw_uid, identity.pw_gid)
    user_run(['php', 'wp-cli.phar', 'core', 'install', '--url=https://fixture.invalid', '--title=Fixture',
              '--admin_user=probe', '--admin_password=' + secrets.token_hex(20), '--admin_email=probe@example.invalid', '--skip-email'])
    recipe = base / 'recipe.php'
    recipe.write_text('<?php\nnamespace Deployer;\nrequire ' + json.dumps(str(source / 'deploy.php')) + ';\n'
        + "set('bin/php', '/usr/bin/php');\n"
        + "task('deploy:fpm-check', static function (): void { run('test -S {{php_fpm_socket}} && test -w {{php_fpm_socket}}'); run('getent group {{log_group}} >/dev/null'); run('command -v setfacl'); });\n"
        + "task('deploy:fpm-reload', static function (): void { run('kill -USR2 $(cat " + str(base / 'fpm.pid') + ")'); });\n")
    recipe.chmod(0o644)
    processes = []
    try:
        processes.append(subprocess.Popen(['/usr/sbin/sshd', '-D', '-e', '-f', str(ssh_config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        processes.append(subprocess.Popen(['php-fpm8.5', '-F', '-y', str(fpm_config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        run(['nginx', '-t', '-p', str(base), '-c', str(nginx_config)])
        processes.append(subprocess.Popen(['nginx', '-p', str(base), '-c', str(nginx_config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for _ in range(100):
            if socket_path.exists():
                break
            time.sleep(.05)
        # The signal command runs as deploy user through a narrow test-only sudo rule.
        with sudoers.open('a') as stream:
            stream.write('sympress-probe ALL=(root) NOPASSWD: /bin/kill -USR2 *\n')
        recipe.write_text(recipe.read_text().replace("run('kill -USR2", "run('sudo -n /bin/kill -USR2"))
        user_run(['php', 'wp-cli.phar', 'option', 'update', 'permalink_structure', ''])
        user_run(['php', 'wp-cli.phar', 'eval',
                  "if (get_option('permalink_structure') !== '') { WP_CLI::error('Expected plain permalinks.'); }"])
        previous = None
        for iteration in range(2):
            if iteration:
                previous = current
                user_run(['php', 'wp-cli.phar', 'option', 'update', 'permalink_structure', '/%postname%/'], cwd=current)
            output = user_run(['php', str(source / 'deployment/vendor/bin/dep'), '-f', str(recipe), 'deploy', 'production', '-n', '--no-ansi'], cwd=source)
            print(output[-600:])
            current = (deploy_path / 'current').resolve(strict=True)
            assert (current / 'vendor/autoload.php').is_file()
            assert (current / 'public/wp/wp-load.php').is_file()
            assert (current / 'var/cache').stat().st_mode & 0o777 == 0o750
            assert not (deploy_path / '.dep/deploy.lock').exists()
            run(['curl', '--fail', '--silent', '--show-error', '--cacert', str(certificate), f'https://127.0.0.1:{https_port}/'])
            absent = user_run(['php', 'wp-cli.phar', 'eval', '$response = rest_do_request(new WP_REST_Request("GET", "/sympress/v1/health")); echo $response->get_status();'], cwd=current)
            assert absent.strip() == '404', absent
        assert 'GET / ' in (base / 'https-access.log').read_text()
        user_run(['php', str(source / 'deployment/vendor/bin/dep'), '-f', str(recipe), 'rollback', 'production', '-n', '--no-ansi'], cwd=source)
        assert (deploy_path / 'current').resolve(strict=True) == previous
        assert not (deploy_path / '.dep/deploy.lock').exists()
        current = previous
        cache = current / 'var/cache'
        cache.chmod(0o770)
        negative = subprocess.run(['sudo', '-u', 'www-data', 'php', str(current / 'vendor/bin/runtime'), 'doctor', '--production', '--json', '--php-user=www-data', '-n'],
                                  cwd=current, text=True, capture_output=True)
        assert negative.returncode != 0
        report = json.loads(negative.stdout)
        assert any(check['id'] == 'kernel.cache' and check['status'] == 'fail' for check in report['checks'])
        cache.chmod(0o750)
        recipe.write_text(recipe.read_text() + "\ntask('deploy:published-health', static function (): void { throw new \\RuntimeException('Expected health failure after publication.'); });\n")
        failed = subprocess.run(['sudo', '-E', '-u', 'sympress-probe', 'php', str(source / 'deployment/vendor/bin/dep'),
                                 '-f', str(recipe), 'deploy', 'production', '-n', '--no-ansi'],
                                cwd=source, env=environment, text=True, capture_output=True, timeout=240)
        assert failed.returncode != 0, failed.stdout + failed.stderr
        assert (deploy_path / 'current').resolve(strict=True) == current, failed.stdout + failed.stderr
        assert not (deploy_path / '.dep/deploy.lock').exists()
        print(json.dumps({'deploys': 2, 'permalinks': ['plain', 'pretty'], 'published_verifier': 'private FPM build ID', 'public_https': 'verified', 'private_package_required': False,
                          'manual_rollback': 'pass', 'failed_health_rollback': 'pass', 'doctor_identity': 'www-data',
                          'cache_mode': '0750', 'ssh_agent_forwarding': False, 'fpm_health': 'ok'}))
    except Exception:
        candidates = sorted((deploy_path / 'releases').glob('*'))
        if candidates and socket_path.exists():
            debug = base / 'diagnose.php'
            debug.write_text('<?php try { require ' + json.dumps(str(candidates[-1] / 'public/wp/wp-load.php'))
                             + '; foreach (["DISALLOW_FILE_EDIT", "DISALLOW_FILE_MODS", "WP_DEBUG_DISPLAY", "FORCE_SSL_ADMIN"] as $name) { $data[$name] = defined($name) ? constant($name) : null; } $data["environment"] = wp_get_environment_type(); echo json_encode($data); } catch (Throwable $e) { echo json_encode(["error" => get_class($e), "file" => $e->getFile(), "line" => $e->getLine()]); }')
            probe = subprocess.run(['cgi-fcgi', '-bind', '-connect', str(socket_path)],
                                   env={'SCRIPT_FILENAME': str(debug), 'SCRIPT_NAME': '/diagnose.php', 'REQUEST_METHOD': 'POST', 'HTTPS': 'on', 'REDIRECT_STATUS': '200'}, text=True, capture_output=True)
            print('FPM diagnostic: ' + probe.stdout[-1800:] + probe.stderr[-500:], flush=True)
        raise
    finally:
        for process in processes:
            process.terminate()
            process.wait(timeout=10)
        run(['mariadb', '-e', f'DROP DATABASE `{database}`;'])
        sudoers.unlink(missing_ok=True)
        shutil.rmtree(base)


if __name__ == '__main__':
    main()
