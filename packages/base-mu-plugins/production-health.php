<?php

declare(strict_types=1);

/**
 * Plugin Name: SymPress Production Health
 */

if (!defined('ABSPATH')) {
    exit;
}

// Public, read-only status with no version, secret, DB name or stack disclosure.
add_action('rest_api_init', static function (): void {
    register_rest_route('sympress/v1', '/health', [
        'methods'             => 'GET',
        'permission_callback' => '__return_true',
        'callback'            => static function (): WP_REST_Response {
            /** @var wpdb $wpdb */
            $wpdb = $GLOBALS['wpdb'];
            $healthy = $wpdb->get_var('SELECT 1') === '1';

            $buildId = defined('SYMPRESS_KERNEL_BUILD_ID')
                ? constant('SYMPRESS_KERNEL_BUILD_ID')
                : sanitize_text_field(wp_unslash(
                    $_ENV['SYMPRESS_KERNEL_BUILD_ID']
                    ?? $_SERVER['SYMPRESS_KERNEL_BUILD_ID']
                    ?? getenv('SYMPRESS_KERNEL_BUILD_ID'),
                ));
            $buildId = is_string($buildId) && preg_match('/^[A-Za-z0-9._-]{1,128}$/D', $buildId) ? $buildId : null;
            return new WP_REST_Response(
                ['status' => $healthy ? 'ok' : 'error', 'build_id' => $buildId],
                $healthy ? 200 : 503,
            );
        },
    ]);
});

// Staging sync cannot send real mail while copies are being scrubbed.
if (wp_get_environment_type() === 'staging') {
    add_filter('pre_wp_mail', '__return_false');
}
