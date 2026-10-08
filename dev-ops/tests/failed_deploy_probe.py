#!/usr/bin/env python3
"""Exercise failed publication with native Deployer workers and an owned FPM pool."""
import argparse
import grp
import json
import os
from pathlib import Path
import pwd
import subprocess
import tempfile
import time

from rollback_probe import php_literal, request


def run_case(source, deployer, fpm_binary, failure):
    with tempfile.TemporaryDirectory(prefix='sympress_failed_deploy_') as directory:
        root = Path(directory)
        for name in ('old', 'new'):
            release = root / 'releases' / name
            (release / 'public').mkdir(parents=True)
            (release / 'public/wp').mkdir()
            (release / 'public/wp/wp-load.php').write_text(
                '<?php define("SYMPRESS_KERNEL_BUILD_ID", ' + php_literal(name) + '); '
                + 'define("DISALLOW_FILE_MODS", true); define("WP_DEBUG_DISPLAY", false); define("FORCE_SSL_ADMIN", true); '
                + 'function wp_get_environment_type() { return "production"; } function wp_is_file_mod_allowed($context) { return false; } '
                + '$GLOBALS["wpdb"] = new class { public function get_var($query) { return "1"; } };')
            (release / 'public/index.php').write_text(
                '<?php echo json_encode(["build_id"=>' + php_literal(name) + ']);')
            (release / 'wp-cli.phar').write_text("""<?php
define('WP_CLI', true);
define('SYMPRESS_KERNEL_BUILD_ID', """ + php_literal(name) + """);
class WP_CLI {
    public static function error($message) { fwrite(STDERR, $message); exit(1); }
    public static function success($message) { file_put_contents('verified.marker', $message); }
}
require $argv[2];
""")
        current = root / 'current'
        current.symlink_to(root / 'releases/old')
        (root / 'release').symlink_to(root / 'releases/new')
        (root / '.dep').mkdir()
        if failure in ('before_lock', 'lock_conflict'):
            (root / '.dep/deploy.lock').write_text('other-operator')
        socket = root / 'fpm.sock'
        pid = root / 'fpm.pid'
        user = pwd.getpwuid(os.getuid()).pw_name
        group = grp.getgrgid(os.getgid()).gr_name
        config = root / 'fpm.conf'
        config.write_text(f"""[global]
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
""")
        pool = subprocess.Popen([fpm_binary, '-F', '-y', str(config)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while not socket.exists():
                if pool.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError('Owned fixture FPM failed to start.')
                time.sleep(.05)
            assert json.loads(request(socket, current / 'public/index.php'))['build_id'] == 'old'
            recipe = root / 'review.php'
            recipe.write_text('<?php\nnamespace Deployer;\nrequire ' + php_literal(source / 'deploy.php') + ';\n'
                + "localhost('production')->set('deploy_path', " + php_literal(root)
                + ")->set('php_fpm_socket', " + php_literal(socket) + ");\n"
                + "set('user', 'fixture');\n"
                + "task('deploy', " + ("['deploy:fpm-check', 'deploy:lock']" if failure == 'before_lock'
                    else "['deploy:lock']" if failure == 'lock_conflict'
                    else "['deploy:lock', 'deploy:prepare-tools', 'deploy:fail-before-switch']" if failure == 'before_switch'
                    else "['deploy:lock', 'deploy:prepare-tools', 'deploy:symlink', 'deploy:refresh', 'deploy:unlock']") + ");\n"
                + "task('deploy:fail-before-switch', static function (): void { run('false'); });\n"
                + "task('deploy:fpm-reload', static function (): void {\n"
                + "  $publishedNew = test('test $(readlink -f {{current_path}}) = {{deploy_path}}/releases/new');\n"
                + "  if ($publishedNew) { run('touch {{deploy_path}}/published-new'); }\n"
                + ("  if ($publishedNew) { run('false'); }\n" if failure == 'reload' else '')
                + "  run(" + php_literal('kill -USR2 ' + pid.read_text().strip()) + ");\n"
                + "  run('touch {{deploy_path}}/reload-ran');\n"
                + "});\n"
                + ("task('deploy:opcache-reset', static function (): void {\n"
                   + ("  if (test('test $(readlink -f {{current_path}}) = {{deploy_path}}/releases/new')) { run('false'); }\n"
                      if failure == 'reset' else "  run('false');\n")
                   + "  run(" + php_literal('set -o pipefail; env -i SCRIPT_FILENAME={{sympress_tools_path}}/opcache-reset.php SCRIPT_NAME=/opcache-reset.php REQUEST_METHOD=POST SERVER_PROTOCOL=HTTP/1.1 REDIRECT_STATUS=200 /usr/bin/cgi-fcgi -bind -connect {{php_fpm_socket}} | grep -Fq \'"opcache_reset":true\'')
                   + ");\n});\n" if failure in ('reset', 'recovery_reset') else ''))
            env = {key: value for key, value in os.environ.items() if key != 'DEPLOYER_LOCAL_WORKER'}
            result = subprocess.run(
                ['php', str(deployer), '-f', str(recipe), 'deploy', 'production', '--no-interaction', '--no-ansi'],
                env=env | {'DEPLOY_PATH': str(root), 'SYMPRESS_PHP_USER': user,
                           'SYMPRESS_PHP_GROUP': group, 'SYMPRESS_LOG_GROUP': 'sympress-fixture-missing-group' if failure == 'before_lock' else group},
                text=True, capture_output=True, timeout=45)
            output = result.stdout + result.stderr
            assert result.returncode != 0, output[-2500:]
            published = failure not in ('before_lock', 'lock_conflict', 'before_switch')
            assert (root / 'published-new').exists() == published, output[-2500:]
            assert current.resolve() == root / 'releases/old', output[-2500:]
            if failure in ('before_lock', 'lock_conflict'):
                assert (root / '.dep/deploy.lock').is_file(), output[-2500:]
                assert (root / '.dep/deploy.lock').read_text() == 'other-operator'
            else:
                assert not (root / '.dep/deploy.lock').exists(), output[-2500:]
            assert ('deploy:recover-published' in output) == (failure != 'lock_conflict'), output[-2500:]
            assert json.loads(request(socket, current / 'public/index.php'))['build_id'] == 'old'
            if published and failure != 'recovery_reset':
                assert (root / 'releases/old/verified.marker').exists(), output[-2500:]
            return {'failure': failure, 'published_new': published, 'current': 'old',
                    'fpm_build': 'old', 'unlocked': failure not in ('before_lock', 'lock_conflict'), 'separate_native_workers': True,
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
    parser.add_argument('--deployer', type=Path, required=True)
    parser.add_argument('--php-fpm', default='php-fpm8.5')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[2]
    evidence = [run_case(source, args.deployer.resolve(strict=True), args.php_fpm, failure)
                for failure in ('before_lock', 'lock_conflict', 'before_switch', 'reload', 'reset', 'recovery_reset')]
    print(json.dumps({'native_failed_publication': evidence, 'passed': True}))


if __name__ == '__main__':
    main()
