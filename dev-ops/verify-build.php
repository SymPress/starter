<?php

declare(strict_types=1);

// The private candidate helper runs with wp eval-file from the actual current release.
if (!defined('WP_CLI') || !WP_CLI) {
    exit(1);
}
$buildId = defined('SYMPRESS_KERNEL_BUILD_ID') ? constant('SYMPRESS_KERNEL_BUILD_ID')
    : ($_ENV['SYMPRESS_KERNEL_BUILD_ID'] ?? $_SERVER['SYMPRESS_KERNEL_BUILD_ID'] ?? getenv('SYMPRESS_KERNEL_BUILD_ID'));
if (!is_string($buildId) || !preg_match('/^[A-Za-z0-9._-]{1,128}$/D', $buildId)) {
    WP_CLI::error('The current release has no valid build ID.');
}
$url = home_url('/wp-json/sympress/v1/health');
if (wp_parse_url($url, PHP_URL_SCHEME) !== 'https') {
    WP_CLI::error('Published health verification requires the canonical HTTPS site.');
}
$response = wp_remote_get(add_query_arg('sympress_build_probe', $buildId, $url), [
    'timeout' => 15, 'redirection' => 0, 'sslverify' => true,
    'headers' => ['Cache-Control' => 'no-cache'],
]);
$body = is_wp_error($response) ? null : json_decode(wp_remote_retrieve_body($response), true);
if (is_wp_error($response) || wp_remote_retrieve_response_code($response) !== 200
    || !is_array($body) || ($body['status'] ?? '') !== 'ok') {
    WP_CLI::error('Published health is unavailable or unhealthy.');
}
if (!is_string($body['build_id'] ?? null) || !preg_match('/^[A-Za-z0-9._-]{1,128}$/D', $body['build_id'])) {
    WP_CLI::error('Published health exposes no valid build ID; this release cannot be verified.');
}
if ($body['build_id'] !== $buildId) {
    WP_CLI::error('Published health does not match the current release build ID.');
}
WP_CLI::success('Published health matches the current release build ID.');
