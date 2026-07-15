<?php

declare(strict_types=1);

namespace SymPress\Starter\Tests\Setup;

use PHPUnit\Framework\TestCase;

final class TemplateHygieneTest extends TestCase
{
    private string $projectDir;

    protected function setUp(): void
    {
        $this->projectDir = dirname(__DIR__, 2);
    }

    public function testGeneratedLocalArtifactsAreNotTracked(): void
    {
        if (!is_dir($this->projectDir . '/.git')) {
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
        self::assertSame('dev', $composer['minimum-stability'] ?? null);
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
        self::assertNotContains('sympress/consent', $suggestionNames);

        $suggestions = array_column($manifest['packageSuggestions'], null, 'name');
        foreach (['sympress/mailer', 'sympress/nginx-cache'] as $unpublishedPackage) {
            self::assertSame('dev-main', $suggestions[$unpublishedPackage]['constraint'] ?? null);
            self::assertSame(
                'https://github.com/SymPress/' . substr($unpublishedPackage, strlen('sympress/')),
                $suggestions[$unpublishedPackage]['repositoryUrl'] ?? null,
            );
        }

        foreach ($manifest['packageSuggestions'] as $suggestion) {
            $suggestedProfiles = array_merge(
                $suggestion['recommendedProfiles'] ?? [],
                $suggestion['optionalProfiles'] ?? [],
            );
            self::assertSame([], array_values(array_diff($suggestedProfiles, $profileIds)));
        }
    }
}
