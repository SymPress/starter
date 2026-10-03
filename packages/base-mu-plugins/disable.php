<?php

declare(strict_types=1);

/**
 * Plugin Name: SymPress Optional WordPress Hardening
 */

if (!defined('ABSPATH')) {
    exit;
}

$sympressStarterHardening = defined('SYMPRESS_ENABLE_WORDPRESS_HARDENING')
    ? constant('SYMPRESS_ENABLE_WORDPRESS_HARDENING')
    : ($_ENV['SYMPRESS_ENABLE_WORDPRESS_HARDENING'] ?? $_SERVER['SYMPRESS_ENABLE_WORDPRESS_HARDENING'] ?? getenv('SYMPRESS_ENABLE_WORDPRESS_HARDENING'));
if (!filter_var($sympressStarterHardening, FILTER_VALIDATE_BOOLEAN)) {
    return;
}
unset($sympressStarterHardening);

remove_action('wp_head', 'wp_generator');

/**
 * Preserve authenticated editors and users while hiding anonymous user listings.
 *
 * @param array<string, mixed> $endpoints
 * @return array<string, mixed>
 */
function sympress_starter_harden_rest_endpoints(array $endpoints): array
{
    if (!is_user_logged_in()) {
        unset($endpoints['/wp/v2/users'], $endpoints['/wp/v2/users/(?P<id>[\d]+)']);
    }

    return $endpoints;
}

add_filter('rest_endpoints', 'sympress_starter_harden_rest_endpoints');
