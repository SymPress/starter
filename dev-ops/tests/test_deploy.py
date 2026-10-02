import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class DeployTest(unittest.TestCase):
    def probe(self, mode='graph', **environment):
        with tempfile.TemporaryDirectory() as directory:
            recipe = Path(directory) / 'recipe'
            recipe.mkdir()
            (recipe / 'common.php').write_text('<?php')
            return subprocess.run(
                ['php', '-d', 'display_errors=stderr', str(Path(__file__).with_name('deploy_probe.php')), directory, mode],
                env=os.environ | environment, text=True, capture_output=True, timeout=10)

    def test_deploy_and_rollback_reload_fpm_after_switching_code(self):
        result = self.probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        recipe = json.loads(result.stdout)
        order = recipe['deploy']
        self.assertLess(order.index('deploy:fpm-check'), order.index('deploy:release'))
        self.assertLess(order.index('deploy:prepare-tools'), order.index('deploy:release'))
        self.assertLess(order.index('deploy:lock'), order.index('deploy:prepare-tools'))
        self.assertLess(order.index('deploy:symlink'), order.index('deploy:refresh'))
        self.assertLess(order.index('deploy:refresh'), order.index('deploy:cleanup'))
        self.assertIn('deploy:fpm-check', recipe['hooks']['before']['rollback'])
        self.assertIn('deploy:prepare-tools', recipe['hooks']['before']['rollback'])
        self.assertIn('deploy:refresh', recipe['hooks']['after']['rollback'])
        self.assertEqual(recipe['refresh'], ['deploy:fpm-reload', 'deploy:opcache-reset', 'deploy:published-health'])

    def test_reload_uses_noninteractive_sudo_and_checks_service(self):
        result = self.probe('deploy:fpm-reload', SYMPRESS_FPM_SERVICE='php8.5-fpm-custom')
        self.assertEqual(result.returncode, 0, result.stderr)
        recipe = json.loads(result.stdout)
        self.assertEqual(recipe['service'], 'php8.5-fpm-custom')
        self.assertEqual(recipe['commands'], [
            'sudo -n /usr/bin/systemctl reload {{php_fpm_service}}',
            '/usr/bin/systemctl is-active --quiet {{php_fpm_service}}'])
        self.assertEqual(self.probe('deploy:fpm-reload', PROBE_FAIL_RELOAD='1').returncode, 17)

    def test_opcache_reset_executes_in_private_fpm_pool(self):
        result = self.probe('deploy:opcache-reset')
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(result.stdout)['commands'][0]
        self.assertIn('cgi-fcgi -bind -connect {{php_fpm_socket}}', command)
        self.assertIn('SCRIPT_FILENAME={{sympress_tools_path}}/opcache-reset.php', command)
        self.assertIn('set -o pipefail', command)

    def test_published_health_runs_from_current_after_switch_and_rollback(self):
        result = self.probe('deploy:published-health')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['commands'], [
            'cd {{current_path}} && {{bin/php}} wp-cli.phar eval-file {{sympress_tools_path}}/verify-build.php'])

    def test_failed_reset_still_reloads_fpm_after_switch(self):
        result = self.probe('deploy:refresh', PROBE_FAIL_RESET='1')
        self.assertEqual(result.returncode, 17)
        commands = json.loads(result.stdout)['commands']
        self.assertIn('systemctl reload', commands[0])
        self.assertIn('is-active', commands[1])
        self.assertIn('cgi-fcgi', commands[2])
        self.assertEqual(len(commands), 3)

    def test_retained_release_needs_no_helper_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            retained = root / 'releases' / 'old'
            retained.mkdir(parents=True)
            current = root / 'current'
            current.symlink_to(retained)
            result = self.probe('deploy:prepare-tools', DEPLOY_PATH=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            recipe = json.loads(result.stdout)
            self.assertEqual(recipe['tools'], '{{deploy_path}}/shared/sympress-tools')
            for upload in recipe['uploads']:
                destination = Path(upload['destination'].replace(
                    '{{sympress_tools_path}}', str(root / 'shared/sympress-tools')))
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(Path(upload['source']).read_bytes())
                self.assertNotIn(current, destination.parents)
            self.assertEqual(len(recipe['uploads']), 2)
            self.assertFalse((retained / 'dev-ops').exists())
            self.assertEqual(current.resolve(), retained)
            self.assertIn('0750', recipe['commands'][0])
            self.assertTrue(all('chmod 0640' in command for command in recipe['commands'][1:]))

    def test_log_group_membership_is_checked_before_release_changes(self):
        result = self.probe('deploy:fpm-check', SYMPRESS_LOG_GROUP='fixture-logs')
        self.assertEqual(result.returncode, 0, result.stderr)
        recipe = json.loads(result.stdout)
        self.assertEqual(recipe['log_group'], 'fixture-logs')
        self.assertEqual(recipe['commands'][0], 'getent group {{log_group}} >/dev/null')
        self.assertEqual(recipe['commands'][1], 'command -v setfacl >/dev/null')
        self.assertIn('id -nG {{php_user}}', recipe['commands'][2])
        self.assertIn('id -nG |', recipe['commands'][3])
        self.assertTrue(all('grep -Fxq {{log_group}}' in command for command in recipe['commands'][2:4]))

    def test_monitor_gets_only_traversal_permissions_on_log_ancestors(self):
        result = self.probe('deploy:permissions')
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = json.loads(result.stdout)['commands']
        self.assertEqual(commands[:3], [
            'setfacl -m g:{{log_group}}:--x {{deploy_path}}',
            'setfacl -m g:{{log_group}}:--x {{deploy_path}}/shared',
            'setfacl -m g:{{log_group}}:--x {{deploy_path}}/shared/var'])
        self.assertFalse(any('setfacl' in command and '.env' in command for command in commands))

    def test_invalid_log_group_fails_before_remote_commands(self):
        result = self.probe('deploy:fpm-check', SYMPRESS_LOG_GROUP='logs;touch injected')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_invalid_socket_fails_before_remote_commands(self):
        result = self.probe('deploy:opcache-reset', SYMPRESS_FPM_SOCKET='/tmp/fpm.sock;touch injected')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_invalid_service_fails_before_remote_commands(self):
        result = self.probe('deploy:fpm-reload', SYMPRESS_FPM_SERVICE='php; touch injected')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
