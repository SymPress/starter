<?php

declare(strict_types=1);

// Outside the docroot; called only through the private FPM socket before and after promotion.
if (PHP_SAPI !== 'fpm-fcgi' || ($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(404);
    exit;
}

$release = $_SERVER['SYMPRESS_RELEASE_PATH'] ?? '';
$release = is_string($release) ? realpath($release) : false;
if (!is_string($release) || !preg_match('~^/[A-Za-z0-9/_-]+/releases/[A-Za-z0-9._-]+$~D', $release)
    || !is_file($release . '/public/wp/wp-load.php')) {
    http_response_code(503);
    exit;
}

$buildId = null;
try {
    require $release . '/public/wp/wp-load.php';
    $healthy = in_array(wp_get_environment_type(), ['production', 'staging'], true)
        && !wp_is_file_mod_allowed('capability_edit_themes')
        && defined('DISALLOW_FILE_MODS') && DISALLOW_FILE_MODS
        && defined('WP_DEBUG_DISPLAY') && !WP_DEBUG_DISPLAY
        && defined('FORCE_SSL_ADMIN') && FORCE_SSL_ADMIN
        && $GLOBALS['wpdb']->get_var('SELECT 1') === '1';
    $candidate = defined('SYMPRESS_KERNEL_BUILD_ID') ? constant('SYMPRESS_KERNEL_BUILD_ID')
        : ($_ENV['SYMPRESS_KERNEL_BUILD_ID'] ?? $_SERVER['SYMPRESS_KERNEL_BUILD_ID'] ?? getenv('SYMPRESS_KERNEL_BUILD_ID'));
    $buildId = is_string($candidate) && preg_match('/^[A-Za-z0-9._-]{1,128}$/D', $candidate) ? $candidate : null;
} catch (Throwable) {
    $healthy = false;
}

http_response_code($healthy ? 200 : 503);
header('Content-Type: application/json');
echo json_encode(['runtime_health' => $healthy ? 'ok' : 'error', 'build_id' => $buildId]);
