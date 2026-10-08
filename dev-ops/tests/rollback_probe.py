#!/usr/bin/env python3
"""Exercise the locked native Deployer rollback recipe against an owned FPM pool."""
import argparse
import json
import os
from pathlib import Path
import pwd
import grp
import subprocess
import tempfile
import time


def php_literal(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def request(socket, script):
    response = subprocess.run(
        ['/usr/bin/cgi-fcgi', '-bind', '-connect', str(socket)],
        env={'SCRIPT_FILENAME': str(script), 'SCRIPT_NAME': '/' + script.name,
             'REQUEST_METHOD': 'POST', 'SERVER_PROTOCOL': 'HTTP/1.1', 'REDIRECT_STATUS': '200'},
        capture_output=True, text=True, timeout=10, check=True)
    return response.stdout.replace('\r\n', '\n').split('\n\n', 1)[-1].strip()


def run_case(source, deployer, fpm_binary, outcome):
    with tempfile.TemporaryDirectory(prefix='sympress_rollback_probe_') as directory:
        root = Path(directory)
        for name in ('old', 'new'):
            release = root / 'releases' / name
            (release / 'public').mkdir(parents=True)
            (release / 'public/wp').mkdir()
            build_id = '' if name == 'old' and outcome == 'legacy' else 'define("SYMPRESS_KERNEL_BUILD_ID", ' + php_literal(name) + '); '
            (release / 'public/wp/wp-load.php').write_text(
                '<?php ' + build_id
                + 'define("DISALLOW_FILE_MODS", true); define("WP_DEBUG_DISPLAY", false); define("FORCE_SSL_ADMIN", true); '
                + 'function wp_get_environment_type() { return "production"; } function wp_is_file_mod_allowed($context) { return false; } '
                + '$GLOBALS["wpdb"] = new class { public function get_var($query) { return "1"; } };')
            (release / 'public/index.php').write_text(
                '<?php echo json_encode(["build_id"=>' + php_literal(name) + ']);')
        retained = root / 'releases/old'
        # A retained release deliberately contains neither new helper.
        (retained / 'wp-cli.phar').write_text("""<?php
define('WP_CLI', true);
define('SYMPRESS_KERNEL_BUILD_ID', 'old');
class WP_CLI {
    public static function error($message) { fwrite(STDERR, $message); exit(1); }
    public static function success($message) { file_put_contents('verified.marker', $message); echo $message; }
}
require $argv[2];
""")
        current = root / 'current'
        current.symlink_to(root / 'releases/new')
        (root / '.dep').mkdir()
        socket = root / 'fpm.sock'
        pid = root / 'fpm.pid'
        user = pwd.getpwuid(os.getuid()).pw_name
        group = grp.getgrgid(os.getgid()).gr_name
        configuration = root / 'fpm.conf'
        configuration.write_text(f"""[global]
pid={pid}
error_log={root}/fpm.log
daemonize=no
[probe]
user={user}
group={group}
listen={socket}
listen.mode=0600
pm=static
pm.max_children=1
clear_env=yes
php_admin_flag[opcache.enable]=on
php_admin_value[opcache.validate_timestamps]=0
php_admin_value[opcache.file_update_protection]=0
php_admin_value[realpath_cache_ttl]=600
""" + ('php_admin_value[disable_functions]=opcache_reset\n' if outcome == 'reset_failure' else ''))
        pool = subprocess.Popen([fpm_binary, '-F', '-y', str(configuration)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while not socket.exists():
                if pool.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('Owned fixture FPM failed to start.')
                time.sleep(.05)
            assert json.loads(request(socket, current / 'public/index.php'))['build_id'] == 'new'
            recipe = root / 'review.php'
            recipe.write_text('<?php\nnamespace Deployer;\nrequire ' + php_literal(source / 'deploy.php') + ';\n'
                + "localhost('production')->set('deploy_path', " + php_literal(root)
                + ")->set('php_fpm_socket', " + php_literal(socket) + ");\n"
                + "set('rollback_candidate', 'old'); set('user', 'fixture');\n"
                + "task('deploy:fpm-check', static function (): void { "
                + "run('getent group {{log_group}} >/dev/null'); "
                + "run(\"id -nG {{php_user}} | tr ' ' '\\\\n' | grep -Fxq {{log_group}}\"); "
                + "run(\"id -nG | tr ' ' '\\\\n' | grep -Fxq {{log_group}}\"); "
                + "run('test -S {{php_fpm_socket}}'); });\n"
                + "task('deploy:fpm-reload', static function (): void { run("
                + php_literal('kill -USR2 ' + pid.read_text().strip()) + "); run("
                + php_literal('touch ' + str(root / 'reload-ran')) + "); });\n")
            result = subprocess.run(
                ['php', str(deployer), '-f', str(recipe), 'rollback', 'production', '--no-interaction', '--no-ansi'],
                env=os.environ | {'DEPLOY_PATH': str(root), 'SYMPRESS_PHP_USER': user,
                                  'SYMPRESS_PHP_GROUP': group, 'SYMPRESS_LOG_GROUP': group},
                text=True, capture_output=True, timeout=30)
            output = result.stdout + result.stderr
            if current.resolve() != retained or not (root / 'reload-ran').is_file():
                raise RuntimeError('Native rollback did not switch current and reload FPM: ' + output[-2000:])
            assert not (retained / 'dev-ops').exists()
            assert json.loads(request(socket, current / 'public/index.php'))['build_id'] == 'old'
            tools = root / 'shared/sympress-tools'
            assert tools.stat().st_mode & 0o777 == 0o750
            assert all((tools / file).stat().st_mode & 0o777 == 0o640
                       for file in ('opcache-reset.php', 'verify-build.php'))
            if outcome == 'match':
                assert result.returncode == 0, output[-2000:]
                assert (retained / 'verified.marker').read_text() == 'Published health matches the current release build ID.'
            elif outcome == 'legacy':
                assert result.returncode != 0
                assert 'this release cannot be verified' in output
                assert not (retained / 'verified.marker').exists()
            else:
                assert result.returncode != 0
                assert 'deploy:opcache-reset' in output
                assert not (retained / 'verified.marker').exists()
            return {'case': outcome, 'current': 'old', 'fpm_build': 'old',
                    'old_has_helpers': False, 'reload_ran': True,
                    'operation_succeeded': result.returncode == 0,
                    'fpm_validation': 'native private pool with isolated Core configuration double'}
        finally:
            pool.terminate()
            try:
                pool.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pool.kill()
                pool.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deployer', type=Path, required=True,
                        help='Locked deployment/vendor/bin/dep executable')
    parser.add_argument('--php-fpm', default='php-fpm8.5')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[2]
    evidence = [run_case(source, args.deployer.resolve(strict=True), args.php_fpm, outcome)
                for outcome in ('match', 'legacy', 'reset_failure')]
    print(json.dumps({'native_deployer_rollback': evidence, 'passed': True}))


if __name__ == '__main__':
    main()
