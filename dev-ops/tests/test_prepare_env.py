import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


class PrepareEnvironmentTest(unittest.TestCase):
    def run_prepare(self, root, **environment):
        env = {key: value for key, value in os.environ.items() if key not in ['APP_SECRET', 'APP_SECRET_FILE', 'SYMPRESS_PROJECT_DIR']}
        return subprocess.run(['php', str(root / 'dev-ops/prepare-env.php')],
                              env=env | environment, capture_output=True, text=True)

    def fixture(self, root):
        (root / 'dev-ops').mkdir()
        shutil.copyfile(Path(__file__).parents[1] / 'prepare-env.php', root / 'dev-ops/prepare-env.php')

    def test_generates_one_private_random_key_and_preserves_other_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / '.env'
            before = 'DB_PASSWORD=existing-value\nAPP_SECRET=\n'
            path.write_text(before)
            path.chmod(0o644)
            result = self.run_prepare(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            after = path.read_text()
            self.assertTrue(after.startswith(before))
            self.assertRegex(after, r'APP_SECRET=[a-f0-9]{64}\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(result.stdout, '')
            self.assertEqual(self.run_prepare(root).returncode, 0)
            self.assertEqual(path.read_text(), after)
            other = root / 'other'
            other.mkdir()
            self.fixture(other)
            (other / '.env').write_text(before)
            self.assertEqual(self.run_prepare(other).returncode, 0)
            self.assertNotEqual(re.findall(r'APP_SECRET=(.+)', (other / '.env').read_text()),
                                re.findall(r'APP_SECRET=(.+)', after))

    def test_preserves_supplied_and_process_values_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / '.env'
            before = 'APP_SECRET=${PRIVATE_PROCESS_KEY}\n'
            path.write_text(before)
            self.assertEqual(self.run_prepare(root).returncode, 0)
            self.assertEqual(path.read_text(), before + f"SYMPRESS_PROJECT_DIR='{root}'\n")
            exported = 'export APP_SECRET="operator-owned-private-key"\n'
            path.write_text(exported)
            self.assertEqual(self.run_prepare(root).returncode, 0)
            self.assertEqual(path.read_text(), exported + f"SYMPRESS_PROJECT_DIR='{root}'\n")
            literal_hash = 'APP_SECRET=""#operator-owned-private-01234567890123456789' + '\n'
            path.write_text(literal_hash)
            self.assertEqual(self.run_prepare(root).returncode, 0)
            self.assertEqual(path.read_text(), literal_hash + f"SYMPRESS_PROJECT_DIR='{root}'\n")
            path.write_text('APP_SECRET=\n')
            self.assertEqual(self.run_prepare(root, APP_SECRET='process-owned-key').returncode, 0)
            self.assertEqual(path.read_text(), f"APP_SECRET=\nSYMPRESS_PROJECT_DIR='{root}'\n")
            path.unlink()
            private = root / 'private'
            private.write_text(before)
            path.symlink_to(private)
            self.assertNotEqual(self.run_prepare(root).returncode, 0)
            self.assertEqual(private.read_text(), before)

    def test_preserves_existing_file_key_and_process_file_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            key = root / 'private-key'
            key.write_text('operator-owned-file-key-with-more-than-32-bytes')
            before = f'APP_SECRET_FILE={key}\nAPP_SECRET=\n'
            path = root / '.env'
            path.write_text(before)
            result = self.run_prepare(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_text(), before + f"SYMPRESS_PROJECT_DIR='{root}'\n")
            self.assertEqual(result.stdout, '')
            path.write_text('APP_SECRET=\n')
            self.assertEqual(self.run_prepare(root, APP_SECRET_FILE=str(key)).returncode, 0)
            self.assertEqual(path.read_text(), f"APP_SECRET=\nSYMPRESS_PROJECT_DIR='{root}'\n")
            self.assertEqual(key.read_text(), 'operator-owned-file-key-with-more-than-32-bytes')

    def test_comment_only_and_empty_quoted_values_generate_a_key(self):
        for value in [' # operator comment', '"" # operator comment', "'' # operator comment"]:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                path = root / '.env'
                path.write_text(f'APP_SECRET={value}\n')
                result = self.run_prepare(root)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertRegex(path.read_text(), r'APP_SECRET=[a-f0-9]{64}\n')
    def test_preserves_explicit_stable_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / '.env'
            before = "APP_SECRET=existing-secret\nSYMPRESS_PROJECT_DIR=/srv/site/current\n"
            path.write_text(before)
            self.assertEqual(self.run_prepare(root).returncode, 0)
            self.assertEqual(path.read_text(), before)

    @unittest.skipUnless((Path(__file__).parents[2] / 'vendor/autoload.php').exists(),
                         'Dotenv round-trip requires installed Composer dependencies.')
    def test_generated_identity_round_trips_through_real_dotenv(self):
        for name in ["operator's site", 'literal\\folder$NAME', 'operator\'s "quoted" \\folder$NAME',
                     "operator's \\new \\runtime", "operator's line\nbreak\rpath"]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / name
                root.mkdir()
                self.fixture(root)
                (root / '.env').write_text('APP_SECRET=operator-owned-secret\n')
                self.assertEqual(self.run_prepare(root).returncode, 0)
                parsed = subprocess.run([
                    'php', '-r', 'require $argv[1]; echo json_encode((new Symfony\\Component\\Dotenv\\Dotenv())->parse(file_get_contents($argv[2]))["SYMPRESS_PROJECT_DIR"]);',
                    str(Path(__file__).parents[2] / 'vendor/autoload.php'), str(root / '.env')],
                    text=True, capture_output=True)
                self.assertEqual(parsed.returncode, 0, parsed.stderr)
                self.assertEqual(json.loads(parsed.stdout), str(root))
