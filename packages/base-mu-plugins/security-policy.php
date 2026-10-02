<?php

declare(strict_types=1);

/**
 * Plugin Name: SymPress Native Security Policy
 */

if (!defined('ABSPATH')) {
    exit;
}

// XML-RPC is deliberately unsupported by this Composer-managed website.
add_filter('xmlrpc_enabled', '__return_false');
add_filter('xmlrpc_methods', '__return_empty_array');

// Runtime maps these environment constants into wp-config.php.
// Production .env must set DISALLOW_FILE_EDIT and DISALLOW_FILE_MODS to true.
