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
        self.assertLess(order.index('deploy:symlink'), order.index('deploy:fpm-reload'))
        self.assertLess(order.index('deploy:fpm-reload'), order.index('deploy:cleanup'))
        self.assertIn('deploy:fpm-check', recipe['hooks']['before']['rollback'])
        self.assertIn('deploy:fpm-reload', recipe['hooks']['after']['rollback'])

    def test_reload_uses_noninteractive_sudo_and_checks_service(self):
        result = self.probe('deploy:fpm-reload', SYMPRESS_FPM_SERVICE='php8.5-fpm-custom')
        self.assertEqual(result.returncode, 0, result.stderr)
        recipe = json.loads(result.stdout)
        self.assertEqual(recipe['service'], 'php8.5-fpm-custom')
        self.assertEqual(recipe['commands'], [
            'sudo -n /usr/bin/systemctl reload {{php_fpm_service}}',
            '/usr/bin/systemctl is-active --quiet {{php_fpm_service}}'])
        self.assertEqual(self.probe('deploy:fpm-reload', PROBE_FAIL_RELOAD='1').returncode, 17)

    def test_invalid_service_fails_before_remote_commands(self):
        result = self.probe('deploy:fpm-reload', SYMPRESS_FPM_SERVICE='php; touch injected')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
