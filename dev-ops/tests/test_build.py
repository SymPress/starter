import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class DeploymentBuildTest(unittest.TestCase):
    def test_installed_plugins_activate_and_runtime_failure_stops_build(self):
        for runtime_status in [0, 23]:
            with self.subTest(runtime_status=runtime_status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'dev-ops').mkdir()
                (root / 'vendor/bin').mkdir(parents=True)
                shutil.copyfile(Path(__file__).parents[1] / 'build.php', root / 'dev-ops/build.php')
                (root / 'composer.json').write_text(json.dumps({'require': {}}))
                composer = root / 'composer'
                composer.write_text('#!/usr/bin/env python3\nimport json,sys\nwith open("commands.jsonl", "a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n')
                composer.chmod(0o700)
                (root / 'vendor/bin/runtime').write_text('<?php file_put_contents("runtime-reached", "yes"); exit(' + str(runtime_status) + ');')
                env = dict(os.environ, PATH=str(root) + ':' + os.environ['PATH'])
                result = subprocess.run(['php', str(root / 'dev-ops/build.php')], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, runtime_status, result.stderr)
                commands = [json.loads(line) for line in (root / 'commands.jsonl').read_text().splitlines()]
                self.assertEqual(commands[0][0], 'install')
                self.assertIn('--no-dev', commands[0])
                self.assertIn('--no-scripts', commands[0])
                self.assertNotIn('--no-plugins', commands[0], 'Installed WordPress installers must repair fetched core layout')
                self.assertTrue((root / 'runtime-reached').exists())
                self.assertEqual(len(commands), 2 if runtime_status == 0 else 1)
                if runtime_status == 0:
                    self.assertIn('--classmap-authoritative', commands[-1])


if __name__ == '__main__':
    unittest.main()
