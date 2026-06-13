<?php

declare(strict_types=1);

namespace SymPress\Starter\Tests\BaseMuPlugins;

use PHPUnit\Framework\TestCase;

final class MuPluginTemplateTest extends TestCase
{
    private string $pluginDir;

    protected function setUp(): void
    {
        $this->pluginDir = dirname(__DIR__, 2) . '/packages/base-mu-plugins';
    }

    public function testMuPluginEntrypointsHaveWordPressGuards(): void
    {
        $files = [
            '000-error-reporting.php',
            'allowed-html-tags.php',
            'app-starter.php',
            'disable.php',
            'global-functions.php',
            'vardumper-integration.php',
        ];

        foreach ($files as $file) {
            self::assertStringContainsString(
                "defined('ABSPATH')",
                (string) file_get_contents($this->pluginDir . '/' . $file),
                "{$file} should not execute outside WordPress.",
            );
        }
    }

    public function testVarDumperDoesNotLoadGeneratedTempPhp(): void
    {
        $source = (string) file_get_contents($this->pluginDir . '/vardumper-integration.php');

        self::assertStringNotContainsString('sys_get_temp_dir()', $source);
        self::assertStringNotContainsString('file_put_contents', $source);
        self::assertStringContainsString("require_once __DIR__ . '/global-functions.php';", $source);
    }
}
