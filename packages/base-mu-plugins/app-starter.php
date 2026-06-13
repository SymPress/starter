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

if (!class_exists(App::class)) {
    require_once __DIR__ . '/vendor/autoload.php';
}

App::bootKernel(new SiteKernel(dirname(__DIR__, 2)));
