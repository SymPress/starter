<?php

declare(strict_types=1);

// Run through WP-CLI eval-file in two separate processes after configuring Redis.
$phase = $args[0] ?? '';
$key = $args[1] ?? '';
if (!in_array($phase, ['write', 'read'], true) || !is_string($key)
    || !preg_match('/^[a-f0-9]{32}$/D', $key) || !wp_using_ext_object_cache()) {
    throw new RuntimeException('An external object cache and a valid probe are required.');
}

if ($phase === 'write') {
    if (!wp_cache_set($key, 'persistent', 'sympress-deploy-check', 60)) {
        throw new RuntimeException('Object-cache probe could not be written.');
    }
} else {
    if (wp_cache_get($key, 'sympress-deploy-check') !== 'persistent') {
        throw new RuntimeException('Object-cache value did not survive between processes.');
    }
    wp_cache_delete($key, 'sympress-deploy-check');
}
echo 'Object-cache probe passed.' . PHP_EOL;
