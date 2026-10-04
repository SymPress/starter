import grp
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import tempfile
import time
import unittest


class ProductionPhpProfileTest(unittest.TestCase):
    def test_real_fpm_retains_opcache_and_disables_inherited_and_request_time_jit(self):
        fpm = shutil.which('php-fpm8.5') or shutil.which('php-fpm')
        fcgi = shutil.which('cgi-fcgi')
        self.assertIsNotNone(fpm, 'The native production-profile test requires PHP-FPM.')
        self.assertIsNotNone(fcgi, 'The native production-profile test requires cgi-fcgi.')
        source = Path(__file__).parents[1] / 'php-production.ini'
        info = subprocess.run([fpm, '-i'], text=True, capture_output=True, timeout=10)
        self.assertEqual(info.returncode, 0, info.stderr)
        scan = re.search(r'^Scan this dir for additional .ini files => (.+)$', info.stdout, re.M)
        self.assertIsNotNone(scan, info.stdout)
        with tempfile.TemporaryDirectory(prefix='sympress_php_profile_') as directory:
            root = Path(directory)
            fragments = root / 'conf.d'
            fragments.mkdir()
            # The exact source profile must win over an inherited JIT-enabling ini.
            inherited = root / 'inherited.ini'
            inherited.write_text('opcache.jit=1235\nopcache.jit_buffer_size=256M\n')
            installed = fragments / '99-sympress.ini'
            shutil.copyfile(source, installed)
            socket = root / 'fpm.sock'
            config = root / 'fpm.conf'
            config.write_text(f"""[global]
pid={root}/fpm.pid
error_log={root}/fpm.log
daemonize=no
[probe]
user={pwd.getpwuid(os.getuid()).pw_name}
group={grp.getgrgid(os.getgid()).gr_name}
listen={socket}
listen.mode=0600
pm=static
pm.max_children=1
clear_env=yes
""")
            script = root / 'profile.php'
            script.write_text("""<?php
$before = opcache_get_status(false);
$jitBefore = ini_get('opcache.jit');
@ini_set('opcache.jit', '1235');
$after = opcache_get_status(false);
echo json_encode([
    'sapi' => PHP_SAPI,
    'opcache_enabled' => $before['opcache_enabled'] ?? false,
    'jit_before' => $jitBefore,
    'jit_after' => ini_get('opcache.jit'),
    'jit_buffer_size' => ini_get('opcache.jit_buffer_size'),
    'jit_enabled' => $after['jit']['enabled'] ?? false,
    'jit_on' => $after['jit']['on'] ?? false,
    'scanned_ini' => php_ini_scanned_files(),
], JSON_THROW_ON_ERROR);
""")
            env = os.environ | {'PHP_INI_SCAN_DIR': scan.group(1) + ':' + str(fragments)}
            command = [fpm, '-F', '-c', str(inherited), '-y', str(config),
                       '-d', 'open_basedir=' + str(root)]
            check = subprocess.run(command + ['-tt'], env=env, text=True, capture_output=True, timeout=10)
            self.assertEqual(check.returncode, 0, check.stderr)
            pool = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 10
                while not socket.exists():
                    if pool.poll() is not None or time.monotonic() >= deadline:
                        self.fail('Native production-profile FPM failed to start: ' + (root / 'fpm.log').read_text())
                    time.sleep(.05)
                response = subprocess.run(
                    [fcgi, '-bind', '-connect', str(socket)],
                    env=os.environ | {'SCRIPT_FILENAME': str(script), 'SCRIPT_NAME': '/profile.php',
                                      'REQUEST_METHOD': 'GET', 'SERVER_PROTOCOL': 'HTTP/1.1',
                                      'REDIRECT_STATUS': '200'},
                    text=True, capture_output=True, timeout=10)
                self.assertEqual(response.returncode, 0, response.stderr)
                body = response.stdout.split('\r\n\r\n')[-1].split('\n\n')[-1]
                data = json.loads(body)
                self.assertEqual(data['sapi'], 'fpm-fcgi')
                self.assertTrue(data['opcache_enabled'])
                self.assertEqual(data['jit_before'], 'disable')
                self.assertEqual(data['jit_after'], 'disable')
                self.assertEqual(data['jit_buffer_size'], '0')
                self.assertFalse(data['jit_enabled'])
                self.assertFalse(data['jit_on'])
                self.assertIn(str(installed), data['scanned_ini'])
            finally:
                pool.terminate()
                try:
                    pool.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pool.kill()
                    pool.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
