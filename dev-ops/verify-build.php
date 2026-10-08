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
// The trusted recipe pipes the private pool's CGI response into this process.
$raw = stream_get_contents(STDIN, 4097);
$parts = is_string($raw) && strlen($raw) <= 4096 ? preg_split('/\r?\n\r?\n/', $raw, 2) : false;
$headers = is_array($parts) && count($parts) === 2 ? $parts[0] : '';
$body = is_array($parts) && count($parts) === 2 ? json_decode($parts[1], true) : null;
$status = preg_match('/^Status:\s*(\d{3})\b/im', $headers, $match) ? (int) $match[1] : 200;
if ($status !== 200 || !is_array($body) || ($body['runtime_health'] ?? '') !== 'ok') {
    WP_CLI::error('Published health is unavailable or unhealthy.');
}
if (!is_string($body['build_id'] ?? null) || !preg_match('/^[A-Za-z0-9._-]{1,128}$/D', $body['build_id'])) {
    WP_CLI::error('Published health exposes no valid build ID; this release cannot be verified.');
}
if ($body['build_id'] !== $buildId) {
    WP_CLI::error('Published health does not match the current release build ID.');
}
WP_CLI::success('Published health matches the current release build ID.');
