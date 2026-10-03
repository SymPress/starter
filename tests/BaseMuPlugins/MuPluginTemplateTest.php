<?php

declare(strict_types=1);

namespace SymPress\Starter\Tests\BaseMuPlugins;

use PHPUnit\Framework\TestCase;
use Symfony\Component\Process\Process;

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
            'legacy-cleanup.php',
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

    public function testNativeDotenvAndExplicitHardeningPrecedence(): void
    {
        $bootstrap = <<<'PHP'
        define('ABSPATH', '/disposable/');
        $GLOBALS['registered'] = 0;
        function add_action(...$arguments) { $GLOBALS['registered']++; }
        function add_filter(...$arguments) { $GLOBALS['registered']++; }
        function remove_action(...$arguments) {}
        function remove_filter(...$arguments) {}
        PHP;
        foreach ([
            ["putenv('SYMPRESS_ENABLE_WORDPRESS_HARDENING');", false],
            ["putenv('SYMPRESS_ENABLE_WORDPRESS_HARDENING'); \$_ENV['SYMPRESS_ENABLE_WORDPRESS_HARDENING'] = 'true';", true],
            ["putenv('SYMPRESS_ENABLE_WORDPRESS_HARDENING=true'); \$_ENV['SYMPRESS_ENABLE_WORDPRESS_HARDENING'] = 'false';", false],
            ["\$_ENV['SYMPRESS_ENABLE_WORDPRESS_HARDENING'] = 'true'; define('SYMPRESS_ENABLE_WORDPRESS_HARDENING', false);", false],
        ] as [$environment, $enabled]) {
            $code = $bootstrap . $environment . 'require ' . var_export($this->pluginDir . '/disable.php', true)
                . '; echo $GLOBALS["registered"];';
            $process = new Process([PHP_BINARY, '-r', $code]);
            $process->mustRun();
            self::assertSame($enabled, (int) $process->getOutput() > 0);
        }
    }

    public function testVarDumperDoesNotLoadGeneratedTempPhp(): void
    {
        $source = (string) file_get_contents($this->pluginDir . '/vardumper-integration.php');

        self::assertStringNotContainsString('sys_get_temp_dir()', $source);
        self::assertStringNotContainsString('file_put_contents', $source);
        self::assertStringContainsString("require_once __DIR__ . '/global-functions.php';", $source);
    }

    public function testProductionHardeningDoesNotRegisterLegacyContentChanges(): void
    {
        $code = <<<'PHP'
        define('ABSPATH', '/disposable/');
        define('SYMPRESS_ENABLE_WORDPRESS_HARDENING', true);
        $GLOBALS['hooks'] = [];
        function add_action($hook, ...$arguments) { $GLOBALS['hooks'][] = $hook; }
        function add_filter($hook, ...$arguments) { $GLOBALS['hooks'][] = $hook; }
        function remove_action(...$arguments) {}
        function remove_filter(...$arguments) {}
        PHP;
        $code .= 'require ' . var_export($this->pluginDir . '/disable.php', true) . ';';
        $code .= 'require ' . var_export($this->pluginDir . '/legacy-cleanup.php', true) . ';';
        $code .= 'echo json_encode($GLOBALS["hooks"]);';
        $process = new Process([PHP_BINARY, '-r', $code]);
        $process->mustRun();
        self::assertSame(['rest_endpoints'], json_decode($process->getOutput(), true));
    }
}
