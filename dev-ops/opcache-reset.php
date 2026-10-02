<?php

declare(strict_types=1);

// Deployer installs this candidate helper in shared/sympress-tools outside the HTTP root.
if (PHP_SAPI !== 'fpm-fcgi' || ($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    exit;
}
header('Content-Type: application/json');
$reset = function_exists('opcache_reset') && opcache_reset();
http_response_code($reset ? 200 : 503);
echo json_encode(['opcache_reset' => $reset], JSON_THROW_ON_ERROR);
