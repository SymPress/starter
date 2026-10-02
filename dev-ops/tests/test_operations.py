import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('operations', Path(__file__).parents[1] / 'operations.py')
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


class OperationsTest(unittest.TestCase):
    def test_monitor_configuration_needs_no_runtime_or_database_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'monitor.json'
            value = {'health_url': 'https://example.test/health', 'alert_recipient': 'ops@example.invalid'}
            path.write_text(json.dumps(value))
            self.assertEqual(ops.config(path, monitoring=True), value)

    def test_confirmation_fails_before_import(self):
        with patch.object(ops, 'wp', side_effect=[b'https://target.test', b'staging']) as wp:
            with self.assertRaisesRegex(ValueError, 'Confirmation'):
                ops.restore({}, '/missing', '/missing', 'https://wrong.test')
            self.assertEqual(wp.call_count, 2)

    def test_sync_requires_staging_and_scrub(self):
        for environment, scrub in [('production', '/private/scrub.php'), ('staging', None)]:
            with patch.object(ops, 'wp', side_effect=[b'https://target.test', environment.encode()]):
                with self.assertRaisesRegex(ValueError, 'staging target'):
                    ops.restore({}, '/missing', '/missing', 'https://target.test', staging=True, scrub_script=scrub)

    def test_production_restore_needs_private_explicit_policy(self):
        with patch.object(ops, 'wp', side_effect=[b'https://target.test', b'production']):
            with self.assertRaisesRegex(ValueError, 'Production restore'):
                ops.restore({}, '/missing', '/missing', 'https://target.test')

    def test_untrusted_archive_link_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            archive = tmp / 'source.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                member = tarfile.TarInfo('uploads/escape');member.type = tarfile.SYMTYPE;member.linkname = '/etc/passwd'
                tar.addfile(member)
            identity = tmp / 'key';identity.write_text('test')
            def decrypt(argv):
                import shutil
                shutil.copyfile(archive, argv[argv.index('--output') + 1])
            with patch.object(ops, 'wp', side_effect=[b'https://target.test', b'staging']) as wp, patch.object(ops, 'command', side_effect=decrypt):
                with self.assertRaisesRegex(ValueError, 'regular files'):
                    ops.restore({}, archive, identity, 'https://target.test')
                self.assertEqual(wp.call_count, 2)

    def test_database_digest_failure_precedes_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            archive = tmp / 'source.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                for name, data in [('database.sql', b'SELECT 1;'), ('manifest.json', b'{"version":1,"database_sha256":"invalid"}')]:
                    member = tarfile.TarInfo(name);member.size = len(data);tar.addfile(member, io.BytesIO(data))
                member = tarfile.TarInfo('uploads');member.type = tarfile.DIRTYPE;tar.addfile(member)
            identity = tmp / 'key';identity.write_text('test')
            def decrypt(argv):
                import shutil
                shutil.copyfile(archive, argv[argv.index('--output') + 1])
            with patch.object(ops, 'wp', side_effect=[b'https://target.test', b'staging']) as wp, patch.object(ops, 'command', side_effect=decrypt):
                with self.assertRaisesRegex(ValueError, 'database backup manifest'):
                    ops.restore({}, archive, identity, 'https://target.test')
                self.assertEqual(wp.call_count, 2)

    def test_log_monitor_uses_cursor_and_sends_only_generic_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            log = tmp / 'app.log';log.write_text('INFO startup\n')
            settings = {'health_url':'https://target.test/health','log_file':str(log),'state_file':str(tmp / 'state.json'),'alert_recipient':'ops@example.invalid','sendmail':'/no/real/message'}
            class Response(io.BytesIO):
                status = 200
            with patch.object(ops.urllib.request, 'urlopen', side_effect=lambda *a, **kw:Response(b'{"status":"ok"}')):
                self.assertEqual(ops.monitor(settings), 0)
                with log.open('a') as stream:stream.write('PHP Fatal password=private_secret\n')
                with patch.object(ops.subprocess, 'run') as send:
                    send.return_value.returncode = 0
                    self.assertEqual(ops.monitor(settings), 1)
                    self.assertNotIn(b'private_secret', send.call_args.kwargs['input'])
                self.assertEqual(ops.monitor(settings), 0)
                log.write_text('Uncaught fresh\n')
                with patch.object(ops.subprocess, 'run') as send:
                    send.return_value.returncode = 0
                    self.assertEqual(ops.monitor(settings), 1)

    def test_failed_alert_is_retried_after_log_rotation_and_then_acknowledged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'app.log'
            state = root / 'state.json'
            log.write_text('PHP Fatal password=private_secret\n')
            settings = {'health_url': 'https://target.test/health', 'log_file': str(log),
                        'state_file': str(state), 'alert_recipient': 'ops@example.invalid'}
            class Response(io.BytesIO):
                status = 200
            with patch.object(ops.urllib.request, 'urlopen', side_effect=lambda *a, **kw: Response(b'{"status":"ok"}')), patch.object(ops.subprocess, 'run') as send:
                send.return_value.returncode = 75
                with self.assertRaisesRegex(RuntimeError, 'Alert delivery failed'):
                    ops.monitor(settings)
                self.assertTrue(json.loads(state.read_text())['pending_alert'])
                self.assertEqual(state.stat().st_mode & 0o777, 0o600)
                self.assertNotIn('private_secret', state.read_text())
                log.rename(root / 'app.log.1')
                log.write_text('INFO rotated and healthy\n')
                send.return_value.returncode = 0
                self.assertEqual(ops.monitor(settings), 1)
                self.assertEqual(send.call_count, 2)
                self.assertFalse(json.loads(state.read_text())['pending_alert'])
                self.assertEqual(ops.monitor(settings), 0)
                self.assertEqual(send.call_count, 2)


    def test_rotating_monolog_logs_allow_a_quiet_day_and_keep_per_file_cursors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = {'health_url': 'https://target.test/health',
                        'log_glob': str(root / 'production-????-??-??.log'),
                        'state_file': str(root / 'cursor.json'),
                        'alert_recipient': 'ops@example.invalid'}
            class Response(io.BytesIO):
                status = 200
            with patch.object(ops.urllib.request, 'urlopen', side_effect=lambda *a, **kw: Response(b'{"status":"ok"}')), patch.object(ops.subprocess, 'run') as send:
                send.return_value.returncode = 0
                # RotatingFileHandler creates a file only when it emits a record.
                self.assertEqual(ops.monitor(settings), 0)
                send.assert_not_called()
                yesterday = root / 'production-2026-10-01.log'
                yesterday.write_text('production.ERROR: private_secret\n')
                self.assertEqual(ops.monitor(settings), 1)
                self.assertEqual(ops.monitor(settings), 0)
                today = root / 'production-2026-10-02.log'
                today.write_text('WARNING healthy\n')
                with yesterday.open('a') as stream:
                    stream.write('production.CRITICAL: late error\n')
                self.assertEqual(ops.monitor(settings), 1)
                self.assertEqual(ops.monitor(settings), 0)
                with today.open('a') as stream:
                    stream.write('PHP Fatal fresh\n')
                self.assertEqual(ops.monitor(settings), 1)
                self.assertEqual(ops.monitor(settings), 0)
                self.assertEqual(send.call_count, 3)
                self.assertNotIn(b'private_secret', send.call_args.kwargs['input'])
                self.assertNotIn('private_secret', (root / 'cursor.json').read_text())

    def test_rotating_log_directory_must_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = {'health_url': 'https://target.test/health',
                        'log_glob': str(Path(directory) / 'missing/production-*.log'),
                        'state_file': str(Path(directory) / 'cursor.json'),
                        'alert_recipient': 'ops@example.invalid'}
            class Response(io.BytesIO):
                status = 200
            with patch.object(ops.urllib.request, 'urlopen', return_value=Response(b'{"status":"ok"}')), patch.object(ops.subprocess, 'run') as send:
                send.return_value.returncode = 0
                self.assertEqual(ops.monitor(settings), 1)
                send.assert_called_once()

    def test_empty_recipient_never_attempts_delivery(self):
        with patch.object(ops.urllib.request, 'urlopen', side_effect=OSError), patch.object(ops.subprocess, 'run') as send:
            with self.assertRaisesRegex(ValueError, 'alert_recipient'):
                ops.monitor({'health_url':'https://target.test/health'})
            send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
