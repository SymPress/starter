import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

INSTALLER_SOURCE = Path(__file__).parents[2] / 'vendor/composer/installers'


class DeploymentBuildTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('composer') and INSTALLER_SOURCE.is_dir(),
                         'Native fetch/installer fixture requires Composer and installed composer/installers.')
    def test_script_free_fetch_then_normal_install_restores_wordpress_archive_paths(self):
        with tempfile.TemporaryDirectory(prefix='sympress_installer_archive_') as directory:
            root = Path(directory)
            archive = root / 'plugin.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('fixture.php', '<?php namespace InstallerProbe; final class Fixture {}')
            manifest = {'name': 'sympress/installer-safety-fixture',
                        'require': {'composer/installers': '2.3.0', 'sympress/installer-probe': '1.0.0'},
                        'repositories': [
                            {'type': 'path', 'url': str(INSTALLER_SOURCE.resolve()),
                             'options': {'symlink': False, 'versions': {'composer/installers': '2.3.0'}}},
                            {'type': 'package', 'package': {
                                'name': 'sympress/installer-probe', 'version': '1.0.0',
                                'type': 'wordpress-muplugin', 'dist': {'type': 'zip', 'url': str(archive)},
                                'autoload': {'classmap': ['fixture.php']}}},
                            {'packagist.org': False}],
                        'extra': {'installer-paths': {'public/wp-content/mu-plugins/{$name}/': ['type:wordpress-muplugin']}},
                        'config': {'allow-plugins': {'composer/installers': True}}}
            (root / 'composer.json').write_text(json.dumps(manifest))
            env = {key: value for key, value in os.environ.items()
                   if not any(word in key for word in ['TOKEN', 'AUTH', 'SSH', 'PASSWORD'])}
            env |= {'COMPOSER_HOME': str(root / 'composer-home'), 'COMPOSER_NO_NETWORK': '1'}
            def composer(*arguments):
                result = subprocess.run(['composer', *arguments, '--no-interaction', '--no-progress'],
                                        cwd=root, env=env, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
            composer('update', '--no-install', '--no-plugins', '--no-scripts')
            composer('install', '--no-plugins', '--no-scripts')
            public = root / 'public/wp-content/mu-plugins/installer-probe/fixture.php'
            self.assertFalse(public.exists())
            self.assertTrue((root / 'vendor/sympress/installer-probe/fixture.php').exists())
            composer('install', '--no-scripts')
            self.assertTrue(public.exists())
            loaded = subprocess.run(['php', '-r',
                'require $argv[1]; echo (new ReflectionClass("InstallerProbe\\Fixture"))->getFileName();',
                str(root / 'vendor/autoload.php')], text=True, capture_output=True, timeout=10)
            self.assertEqual(loaded.returncode, 0, loaded.stderr)
            self.assertEqual(Path(loaded.stdout), public)

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
