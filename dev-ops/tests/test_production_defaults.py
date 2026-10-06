import io
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import importlib.util
import urllib.request
import urllib.parse

spec = importlib.util.spec_from_file_location('operations', Path(__file__).parents[1] / 'operations.py')
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)
NGINX = shutil.which('nginx')
FPM = shutil.which('php-fpm8.5') or shutil.which('php-fpm')
OPENSSL = shutil.which('openssl')


class ProductionDefaultsTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('php'), 'The private WordPress verifier requires PHP.')
    def test_publication_verifier_uses_query_route_and_rejects_redirects_or_stale_builds(self):
        helper = Path(__file__).resolve().parents[1] / 'verify-build.php'
        code = r'''
define('WP_CLI', true);
define('SYMPRESS_KERNEL_BUILD_ID', 'release-probe');
class WP_CLI {
    public static function error($message) { fwrite(STDERR, $message); exit(17); }
    public static function success($message) { echo $message; }
}
function home_url($path) { return $GLOBALS['argv'][2] . $path; }
function wp_parse_url($url, $component) { return parse_url($url, $component); }
function add_query_arg($key, $value, $url) {
    return $url . (str_contains($url, '?') ? '&' : '?') . http_build_query([$key => $value]);
}
function wp_remote_get($url, $options) {
    echo json_encode(['url' => $url, 'options' => $options]) . "\n";
    return ['code' => (int) $GLOBALS['argv'][3], 'body' => json_encode([
        'status' => 'ok', 'build_id' => $GLOBALS['argv'][4]])];
}
function is_wp_error($response) { return false; }
function wp_remote_retrieve_body($response) { return $response['body']; }
function wp_remote_retrieve_response_code($response) { return $response['code']; }
require $argv[1];
'''
        for home in ('https://fixture.invalid', 'https://fixture.invalid/shop'):
            for status, build in ((200, 'release-probe'), (301, 'release-probe'),
                                  (503, 'release-probe'), (200, 'stale')):
                with self.subTest(home=home, status=status, build=build):
                    result = subprocess.run(['php', '-r', code, str(helper), home, str(status), build],
                                            text=True, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0 if status == 200 and build == 'release-probe' else 17)
                    captured = json.loads(result.stdout.splitlines()[0])
                    url = urllib.parse.urlsplit(captured['url'])
                    self.assertEqual(url.path, urllib.parse.urlsplit(home).path + '/')
                    self.assertEqual(urllib.parse.parse_qs(url.query), {
                        'rest_route': ['/sympress/v1/health'], 'sympress_build_probe': ['release-probe']})
                    self.assertEqual(captured['options']['redirection'], 0)
                    self.assertTrue(captured['options']['sslverify'])

    def test_nginx_and_recipe_use_the_same_default_fpm_socket(self):
        root = Path(__file__).resolve().parents[2]
        recipe = (root / 'deploy.php').read_text()
        default = re.search(r"set\('php_fpm_socket', getenv\('SYMPRESS_FPM_SOCKET'\) \?: '([^']+)'\)", recipe)
        self.assertIsNotNone(default)
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['python3', str(root / 'dev-ops/render-nginx.py'), '--hostname', 'fixture.invalid',
                            '--root', '/srv/fixture', '--output', directory], check=True, capture_output=True)
            server = (Path(directory) / 'production-server.conf').read_text()
            self.assertIn('fastcgi_pass unix:' + default.group(1) + ';', server)

    @unittest.skipUnless(shutil.which('php'), 'The private WordPress verifier requires PHP.')
    def test_publication_verifier_bounds_health_body_before_decoding(self):
        helper = Path(__file__).resolve().parents[1] / 'verify-build.php'
        code = r'''
define('WP_CLI', true);
define('SYMPRESS_KERNEL_BUILD_ID', 'release-probe');
class WP_CLI {
    public static function error($message) { fwrite(STDERR, $message); exit(17); }
    public static function success($message) { echo $message; }
}
function home_url($path) { return 'https://fixture.invalid' . $path; }
function wp_parse_url($url, $component) { return parse_url($url, $component); }
function add_query_arg($key, $value, $url) { return $url; }
function wp_remote_get($url, $options) {
    echo json_encode($options) . "\n";
    return ['body' => stream_get_contents(STDIN)];
}
function is_wp_error($response) { return false; }
function wp_remote_retrieve_body($response) { return $response['body']; }
function wp_remote_retrieve_response_code($response) { return 200; }
require $argv[1];
'''
        body = json.dumps({'status': 'ok', 'build_id': 'release-probe'})
        for size in [len(body), 4096, 4097, 1024 * 1024]:
            with self.subTest(bytes=size):
                result = subprocess.run(['php', '-r', code, str(helper)],
                                        input=body + ' ' * (size - len(body)),
                                        text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0 if size <= 4096 else 17, result.stderr)
                options = json.loads(result.stdout.splitlines()[0])
                self.assertEqual(options.get('limit_response_size'), 4097)
                self.assertEqual(options['redirection'], 0)
                self.assertTrue(options['sslverify'])
                if size > 4096:
                    self.assertNotIn('Published health matches', result.stdout)
                    self.assertEqual(result.stderr, 'Published health is unavailable or unhealthy.')

    def test_hsts_is_explicit_and_shared_headers_cover_all_locations(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            for enabled in (False, True):
                output = Path(directory) / str(enabled)
                command = ['python3', str(root / 'render-nginx.py'), '--hostname', 'fixture.invalid',
                           '--root', '/srv/fixture', '--output', str(output)]
                if enabled:
                    command.append('--hsts')
                subprocess.run(command, check=True, capture_output=True)
                rendered = '\n'.join(p.read_text() for p in output.glob('*.conf'))
                self.assertEqual('Strict-Transport-Security' in rendered, enabled)
                if enabled:
                    self.assertIn('Strict-Transport-Security', (output / 'security-headers.conf').read_text())
                    self.assertNotIn('includeSubDomains', rendered)
                    self.assertNotIn('preload;', rendered)

    @unittest.skipUnless(NGINX and FPM and OPENSSL, 'Isolated nginx/PHP-FPM fixture requires nginx, PHP-FPM and OpenSSL.')
    def test_real_php_responses_include_security_headers_with_optional_hsts(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='sympress_nginx_headers_') as directory:
            fixture = Path(directory)
            fixture.chmod(0o755)
            public = fixture / 'current/public'
            public.mkdir(parents=True)
            (public / 'index.php').write_text('<?php echo "private-header-fixture\\n"; echo json_encode(["query" => $_GET, "uri" => $_SERVER["REQUEST_URI"]]);')
            certificate = fixture / 'certificate.pem'
            key = fixture / 'key.pem'
            subprocess.run([OPENSSL, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                            '-keyout', str(key), '-out', str(certificate), '-days', '1',
                            '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1'],
                           check=True, capture_output=True, timeout=15)
            identity = pwd.getpwnam('www-data') if os.geteuid() == 0 else pwd.getpwuid(os.geteuid())
            pool = fixture / 'fpm.conf'
            pool.write_text('[global]\ndaemonize = no\nerror_log = ' + str(fixture / 'fpm.log')
                            + '\n[fixture]\nuser = ' + identity.pw_name
                            + '\ngroup = ' + str(identity.pw_gid)
                            + '\nlisten = ' + str(fixture / 'fpm.sock')
                            + '\nlisten.mode = 0666\npm = static\npm.max_children = 1\n')
            with subprocess.Popen([FPM, '-F', '-y', str(pool)], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL) as fpm:
                self.addCleanup(self.stop_process, fpm)
                deadline = time.monotonic() + 5
                while not (fixture / 'fpm.sock').exists() and fpm.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((fixture / 'fpm.sock').exists(), 'Fixture FPM socket did not start.')
                try:
                    for enabled in (False, True):
                        with self.subTest(hsts=enabled):
                            self.assert_php_headers(root, fixture, certificate, key, enabled)
                finally:
                    self.stop_process(fpm)

    def assert_php_headers(self, root, fixture, certificate, key, enabled):
        output = fixture / 'current/dev-ops/nginx'
        command = ['python3', str(root / 'render-nginx.py'), '--hostname', 'fixture.invalid',
                   '--root', str(fixture), '--output', str(output)]
        if enabled:
            command.append('--hsts')
        subprocess.run(command, check=True, capture_output=True, timeout=10)
        with socket.socket() as socket_handle:
            socket_handle.bind(('127.0.0.1', 0))
            port = socket_handle.getsockname()[1]
        server = (output / 'production-server.conf').read_text()
        server = server[server.index('server {', server.index('server {') + 1):]
        server = server.replace('listen 443 ssl;', f'listen 127.0.0.1:{port} ssl;')
        server = server.replace('/etc/letsencrypt/live/fixture.invalid/fullchain.pem', str(certificate))
        server = server.replace('/etc/letsencrypt/live/fixture.invalid/privkey.pem', str(key))
        server = server.replace('unix:/run/php/php8.5-fpm.sock', 'unix:' + str(fixture / 'fpm.sock'))
        server = server.replace('/var/log/nginx/', str(fixture) + '/')
        (output / 'production-server.conf').write_text(server)
        cache = (output / 'cache-http.conf').read_text().replace('/var/cache/nginx/wordpress', str(fixture / 'cache'))
        (output / 'cache-http.conf').write_text(cache.replace('WORDPRESS:100m', 'WORDPRESS:1m'))
        configuration = fixture / 'nginx.conf'
        configuration.write_text('worker_processes 1;\ndaemon off;\npid ' + str(fixture / 'nginx.pid')
                                 + ';\nerror_log ' + str(fixture / 'nginx.log')
                                 + ';\nevents {}\nhttp {\ninclude ' + str(output / 'cache-http.conf')
                                 + ';\ninclude ' + str(output / 'production-server.conf') + ';\n}\n')
        subprocess.run([NGINX, '-t', '-p', str(fixture), '-c', str(configuration)],
                       check=True, capture_output=True, timeout=10)
        context = ssl.create_default_context(cafile=str(certificate))
        with subprocess.Popen([NGINX, '-p', str(fixture), '-c', str(configuration)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as nginx:
            try:
                deadline = time.monotonic() + 5
                while True:
                    try:
                        with urllib.request.urlopen(f'https://127.0.0.1:{port}/index.php?fixture=1',
                                                    context=context, timeout=1) as response:
                            self.assertEqual(response.status, 200)
                            self.assertTrue(response.read().startswith(b'private-header-fixture\n'))
                            for name in ('X-Content-Type-Options', 'X-Frame-Options',
                                         'Content-Security-Policy', 'Referrer-Policy',
                                         'Content-Security-Policy-Report-Only',
                                         'Permissions-Policy', 'Cross-Origin-Opener-Policy'):
                                self.assertIsNotNone(response.headers.get(name), name)
                            self.assertIn("object-src 'none'", response.headers['Content-Security-Policy-Report-Only'])
                            self.assertEqual(response.headers['Content-Security-Policy'], "frame-ancestors 'self'")
                            self.assertEqual(response.headers['Cross-Origin-Opener-Policy'], 'same-origin-allow-popups')
                            self.assertEqual(response.headers['Permissions-Policy'],
                                             'camera=(), microphone=(), geolocation=()')
                            self.assertEqual(response.headers.get_all('Strict-Transport-Security'),
                                             ['max-age=31536000'] if enabled else None)
                        break
                    except urllib.error.URLError:
                        if nginx.poll() is not None or time.monotonic() >= deadline:
                            raise
                        time.sleep(0.02)
                with urllib.request.urlopen(f'https://127.0.0.1:{port}/index.php?utm_source=first&gclid=123', context=context) as first:
                    canonical = first.read()
                    data = json.loads(canonical.split(b'\n', 1)[1])
                    self.assertEqual(data['query'], [])
                    self.assertEqual(data['uri'], '/index.php')
                    self.assertEqual(first.headers['X-Nginx-Cache'], 'MISS')
                with urllib.request.urlopen(f'https://127.0.0.1:{port}/index.php?utm_source=second', context=context) as second:
                    self.assertEqual(second.headers['X-Nginx-Cache'], 'HIT')
                    self.assertEqual(second.read(), canonical)
                with urllib.request.urlopen(f'https://127.0.0.1:{port}/index.php?utm_source=mixed&s=search', context=context) as mixed:
                    self.assertEqual(mixed.headers['X-Nginx-Cache'], 'BYPASS')
                    data = json.loads(mixed.read().split(b'\n', 1)[1])
                    self.assertEqual(data['query'], {'utm_source': 'mixed', 's': 'search'})
                    self.assertEqual(data['uri'], '/index.php?utm_source=mixed&s=search')
            finally:
                self.stop_process(nginx)
                shutil.rmtree(fixture / 'cache', ignore_errors=True)

    @staticmethod
    def stop_process(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def test_persistent_http_failure_alerts_once_until_recovery(self):
        class Response(io.BytesIO):
            status = 200
        with tempfile.TemporaryDirectory() as directory:
            settings = {'health_url': 'https://fixture.invalid/health',
                        'state_file': str(Path(directory) / 'cursor.json'),
                        'alert_recipient': 'ops@example.invalid'}
            health = [False, False, False, True, False, False]
            calls = iter(health)
            with patch.object(ops, 'open_health',
                              side_effect=lambda *a, **k: Response(b'{"status":"ok"}' if next(calls) else b'{"status":"error"}')), \
                    patch.object(ops.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as send:
                self.assertEqual([ops.monitor(settings) for _ in health], [1, 1, 1, 0, 1, 1])
                self.assertEqual(send.call_count, 2)
                self.assertTrue(json.loads(Path(settings['state_file']).read_text())['health_alerted'])

    def test_http_only_monitor_retries_failed_delivery(self):
        class Response(io.BytesIO):
            status = 200
        with tempfile.TemporaryDirectory() as directory:
            settings = {'health_url': 'https://fixture.invalid/health',
                        'state_file': str(Path(directory) / 'cursor.json'),
                        'alert_recipient': 'ops@example.invalid'}
            with patch.object(ops, 'open_health', side_effect=lambda *a, **k: Response(b'{"status":"error"}')), \
                    patch.object(ops.subprocess, 'run', side_effect=[
                        subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)]) as send:
                with self.assertRaises(RuntimeError):
                    ops.monitor(settings)
                self.assertEqual(ops.monitor(settings), 1)
                self.assertEqual(ops.monitor(settings), 1)
                self.assertEqual(send.call_count, 2)


    def test_health_requires_top_level_json_status_and_bounded_body(self):
        class Response(io.BytesIO):
            status = 200
        for body in [b'{"status":"error","diagnostic":{"status":"ok"}}', b'null', b'[]',
                     b'invalid json', b'{"status":"ok"}' + b' ' * 4096]:
            with self.subTest(body=body[:60]), tempfile.TemporaryDirectory() as directory:
                settings = {'health_url': 'https://fixture.invalid/health',
                            'state_file': str(Path(directory) / 'cursor.json'),
                            'alert_recipient': 'ops@example.invalid'}
                with patch.object(ops, 'open_health', return_value=Response(body)), \
                        patch.object(ops.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as send:
                    self.assertEqual(ops.monitor(settings), 1)
                    self.assertEqual(send.call_count, 1)

    def test_canonical_health_never_follows_redirects(self):
        request = ops.urllib.request.Request('https://fixture.invalid/health')
        for location in ['http://other.invalid/health', 'https://other.invalid/health',
                         'https://fixture.invalid/another-health']:
            with self.subTest(location=location), self.assertRaises(ops.urllib.error.HTTPError):
                ops.RejectHealthRedirect().redirect_request(request, io.BytesIO(), 302, 'Found', {}, location)


if __name__ == '__main__':
    unittest.main()
