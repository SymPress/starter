<?php

declare(strict_types=1);

/**
 * Plugin Name: SymPress App Starter
 */

namespace SymPress\Starter\AppStarter;

use SymPress\Kernel\App;
use SymPress\Kernel\Kernel\SiteKernel;

if (!defined('ABSPATH')) {
    exit;
}

/** Resolve the website root for copied and symlinked MU packages. */
function resolve_project_dir(string $startDir): string
{
    $dir = $startDir;
    while (true) {
        if (is_file($dir . '/composer.json') && is_dir($dir . '/config')) {
            return $dir;
        }
        $parent = dirname($dir);
        if ($parent === $dir) {
            throw new \RuntimeException('Cannot find the SymPress project root.');
        }
        $dir = $parent;
    }
}

$projectDir = resolve_project_dir(__DIR__);
if (!class_exists(App::class)) {
    require_once $projectDir . '/vendor/autoload.php';
}

if (App::kernel() === null) {
    App::bootKernel(new SiteKernel($projectDir));
}
