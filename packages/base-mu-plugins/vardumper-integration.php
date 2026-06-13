<?php

/**
 * Plugin Name: VarDumper Integration
 * Description: Symfony VarDumper integration for WordPress
 * Version: 1.0.0
 * Requires PHP: 8.2
 */

declare(strict_types=1);

namespace SymPress\Starter\WordPress\MustUsePlugin;

use Symfony\Component\VarDumper\Cloner\VarCloner;
use Symfony\Component\VarDumper\Dumper\CliDumper;
use Symfony\Component\VarDumper\Dumper\HtmlDumper;
use Symfony\Component\VarDumper\VarDumper;

if (!defined('ABSPATH')) {
    exit;
}

if (!function_exists('wp_get_environment_type') || wp_get_environment_type() !== 'development') {
    return;
}

if (!filter_var(getenv('SYMPRESS_ENABLE_VARDUMPER'), FILTER_VALIDATE_BOOLEAN)) {
    return;
}

if (is_admin()) {
    return;
}

final class VarDumperIntegration
{
    private static ?self $instance = null;

    private function __construct()
    {
        $this->loadComposerAutoloader();
        $this->initializeVarDumper();
    }

    public static function getInstance(): self
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }

        return self::$instance;
    }

    private function loadComposerAutoloader(): void
    {
        $autoloadPath = $this->resolveAutoloaderPath();

        if ($autoloadPath === null) {
            return;
        }

        require_once $autoloadPath;
    }

    private function resolveAutoloaderPath(): ?string
    {
        $possiblePaths = $this->getAutoloaderPaths();

        foreach ($possiblePaths as $path) {
            if (file_exists($path)) {
                return $path;
            }
        }

        $this->logAutoloaderError();

        return null;
    }

    /** @return array<int, string> */
    private function getAutoloaderPaths(): array
    {
        return [
            dirname(ABSPATH, 2) . '/vendor/autoload.php',
            ABSPATH . 'vendor/autoload.php',
            dirname(ABSPATH) . '/vendor/autoload.php',
            WP_CONTENT_DIR . '/vendor/autoload.php',
            (defined('WP_PLUGIN_DIR') ? WP_PLUGIN_DIR : WP_CONTENT_DIR . '/plugins') . '/vendor/autoload.php',
            get_stylesheet_directory() . '/vendor/autoload.php',
            get_template_directory() . '/vendor/autoload.php',
        ];
    }

    private function logAutoloaderError(): void
    {
        if (!function_exists('error_log')) {
            return;
        }

        error_log('VarDumper MU Plugin: Composer autoloader not found. Install symfony/var-dumper via composer.');
    }

    private function initializeVarDumper(): void
    {
        if (!class_exists(VarDumper::class)) {
            return;
        }

        VarDumper::setHandler(function ($var): void {
            $cloner = new VarCloner();
            $dumper = $this->isCliEnvironment() ? new CliDumper() : $this->createHtmlDumper();

            $dumper->dump($cloner->cloneVar($var));
        });

        $this->registerGlobalFunctions();
    }

    private function isCliEnvironment(): bool
    {
        return PHP_SAPI === 'cli' || (defined('WP_CLI') && WP_CLI);
    }

    private function createHtmlDumper(): HtmlDumper
    {
        return new HtmlDumper();
    }

    private function registerGlobalFunctions(): void
    {
        if (function_exists('dump') && function_exists('dd')) {
            return;
        }

        require_once __DIR__ . '/global-functions.php';
    }
}

VarDumperIntegration::getInstance();
