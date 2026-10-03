<?php

declare(strict_types=1);

namespace SymPress\Starter\Tests\Setup;

use PHPUnit\Framework\TestCase;
use Symfony\Component\Process\Process;

final class TemplateHygieneTest extends TestCase
{
    public function testRootRequiresReleasedRuntimeWithProductionHardening(): void
    {
        $composer = json_decode((string) file_get_contents($this->projectDir . '/composer.json'), true, flags: JSON_THROW_ON_ERROR);
        self::assertSame('^1.2.2', $composer['require']['sympress/runtime']);
        $lock = json_decode((string) file_get_contents($this->projectDir . '/composer.lock'), true, flags: JSON_THROW_ON_ERROR);
        $packages = array_column($lock['packages'], null, 'name');
        self::assertArrayHasKey('sympress/runtime', $packages);
        $runtime = $packages['sympress/runtime'];
        self::assertStringNotContainsString('dev', $runtime['version']);
        self::assertTrue(version_compare(ltrim($runtime['version'], 'v'), '1.2.2', '>='));
        self::assertSame('https://github.com/SymPress/runtime.git', $runtime['source']['url']);
        self::assertStringStartsWith('https://api.github.com/repos/SymPress/runtime/zipball/', $runtime['dist']['url']);
    }

    private string $projectDir;

    protected function setUp(): void
    {
        $this->projectDir = dirname(__DIR__, 2);
    }

    public function testGeneratedLocalArtifactsAreNotTracked(): void
    {
        if (!file_exists($this->projectDir . '/.git')) {
            self::markTestSkipped('Git metadata is not available in this project archive.');
        }

        $paths = [
            '.idea',
            '.ddev/.dbimageBuild',
            '.ddev/.ddev-docker-compose-base.yaml',
            '.ddev/.ddev-docker-compose-full.yaml',
            '.ddev/.homeadditions',
            '.ddev/.webimageBuild',
        ];

        foreach ($paths as $path) {
            exec(
                sprintf('git -C %s ls-files --error-unmatch -- %s 2>/dev/null', escapeshellarg($this->projectDir), escapeshellarg($path)),
                $output,
                $exitCode,
            );

            self::assertNotSame(
                0,
                $exitCode,
                "{$path} must not be part of the public starter template.",
            );
        }
    }

    public function testLicenseMetadataUsesGpl(): void
    {
        $composer = json_decode(
            (string) file_get_contents($this->projectDir . '/composer.json'),
            true,
            flags: JSON_THROW_ON_ERROR,
        );

        self::assertSame('GPL-2.0-or-later', $composer['license'] ?? null);
        self::assertStringContainsString(
            'SPDX-License-Identifier: GPL-2.0-or-later',
            (string) file_get_contents($this->projectDir . '/LICENSE'),
        );
    }

    public function testLocalDefaultsAvoidKnownSharedCredentials(): void
    {
        $envExample = (string) file_get_contents($this->projectDir . '/.env.example');

        self::assertStringNotContainsString('WP_ADMIN_PASSWORD=admin', $envExample);
        self::assertStringContainsString('WP_ADMIN_PASSWORD=', $envExample);
    }

    public function testSetupKeepsWordPressUrlsAtThePublicRoot(): void
    {
        $process = new Process(
            [PHP_BINARY, $this->projectDir . '/bin/console', 'setup', 'root-url-test'],
            $this->projectDir,
            ['SYMPRESS_SETUP_DRY_RUN' => '1', 'DDEV_PROJECT_TLD' => 'ddev.site'],
        );
        $process->mustRun();

        self::assertStringContainsString("WP_HOME=https://root-url-test.ddev.site\n", $process->getOutput());
        self::assertStringContainsString('WP_SITEURL=${WP_HOME}' . "\n", $process->getOutput());
    }

    public function testSetupStoresPrivateGeneratedPasswordWithoutPrintingIt(): void
    {
        $root = sys_get_temp_dir() . '/sympress-setup-' . bin2hex(random_bytes(8));
        mkdir($root . '/bin', 0700, true);
        mkdir($root . '/dev-ops', 0700);
        copy($this->projectDir . '/dev-ops/prepare-env.php', $root . '/dev-ops/prepare-env.php');
        copy($this->projectDir . '/bin/console', $root . '/bin/console');
        copy($this->projectDir . '/.env.example', $root . '/.env.example');
        file_put_contents($root . '/bin/ddev', "#!/bin/sh\nexit 0\n");
        chmod($root . '/bin/ddev', 0700);

        try {
            $process = new Process(
                [PHP_BINARY, $root . '/bin/console', 'setup', 'private-password-test'],
                $root,
                ['PATH' => $root . '/bin:' . getenv('PATH')],
            );
            $process->mustRun();
            $env = (string) file_get_contents($root . '/.env');
            self::assertSame(1, preg_match('/^WP_ADMIN_PASSWORD=(.+)$/m', $env, $match));
            self::assertGreaterThanOrEqual(24, strlen($match[1]));
            self::assertNotSame('admin', $match[1]);
            self::assertStringNotContainsString($match[1], $process->getOutput());
            self::assertSame(0600, fileperms($root . '/.env') & 0777);
            self::assertSame(1, preg_match('/^APP_SECRET=([a-f0-9]{64})$/m', $env, $secret));
            self::assertStringNotContainsString($secret[1], $process->getOutput());
            self::assertStringContainsString("SYMPRESS_PROJECT_DIR='" . $root . "'", $env);
            $process->mustRun();
            self::assertStringContainsString('APP_SECRET=' . $secret[1], (string) file_get_contents($root . '/.env'));
        } finally {
            (new \Symfony\Component\Filesystem\Filesystem())->remove($root);
        }
    }

    public function testCliManifestMatchesTheStarterContract(): void
    {
        $composer = json_decode(
            (string) file_get_contents($this->projectDir . '/composer.json'),
            true,
            flags: JSON_THROW_ON_ERROR,
        );
        $manifest = json_decode(
            (string) file_get_contents($this->projectDir . '/.sympress/cli.json'),
            true,
            flags: JSON_THROW_ON_ERROR,
        );

        self::assertSame(
            'https://raw.githubusercontent.com/sympress/cli/main/schema/repository-manifest.schema.json',
            $manifest['$schema'],
        );
        self::assertSame(1, $manifest['schemaVersion']);
        self::assertSame('stable', $composer['minimum-stability'] ?? null);
        self::assertTrue($composer['prefer-stable'] ?? false);
        self::assertSame($composer['name'], $manifest['templates'][0]['packageName']);
        self::assertSame(['bin/console', 'setup', '{project_slug}'], $manifest['templates'][0]['setupCommand']);
        $profileIds = array_column($manifest['profiles'], 'id');
        self::assertSame(
            ['website', 'app', 'microservice', 'commerce'],
            array_values(array_unique($profileIds)),
        );

        $suggestionNames = array_column($manifest['packageSuggestions'], 'name');
        self::assertSame($suggestionNames, array_values(array_unique($suggestionNames)));
        self::assertContains('sympress/consent', $suggestionNames);

        foreach ($manifest['packageSuggestions'] as $suggestion) {
            $suggestedProfiles = array_merge(
                $suggestion['recommendedProfiles'] ?? [],
                $suggestion['optionalProfiles'] ?? [],
            );
            self::assertSame([], array_values(array_diff($suggestedProfiles, $profileIds)));
        }
    }
}
