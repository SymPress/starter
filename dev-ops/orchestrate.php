<?php

declare(strict_types=1);

use SymPress\Runtime\Database\DbChecker;
use SymPress\Runtime\Services;

$config = (object) [
    'title' => 'SymPress Starter',
];

$shellArg = static fn (string $value): string => \escapeshellarg($value);

/** @var Services $services */
$env = $services->env();

// If env configuration is invalid nothing to do.
if (!$env->read(DbChecker::WPDB_ENV_VALID)) {
    return ['wp --version'];
}

// If WP already installed, let's just tell WP Cli to check it.
if ($env->read(DbChecker::WP_INSTALLED)) {
    return ['wp db check'];
}

$commands = [];

// If DB does not exist, let's tell WP Cli to create it.
if (!$env->read(DbChecker::WPDB_EXISTS)) {
    $commands[] = 'wp db create';
}

// Build install command.
$user = $env->read('WP_ADMIN_USERNAME') ?: 'admin';
$pass = $env->read('WP_ADMIN_PASSWORD');

if (!$pass || $pass === 'admin') {
    $pass = \bin2hex(\random_bytes(24));
}
$home = $env->read('WP_HOME');
$siteUrl = $env->read('WP_SITEURL') ?: $home;
$email = $env->read('WP_ADMIN_EMAIL') ?: 'admin@example.invalid';

$install = "wp core install";
$install .= " --skip-packages --skip-email";
$install .= " --title={$shellArg($config->title)} --url={$shellArg((string) $home)}";
$install .= " --admin_user={$shellArg((string) $user)} --admin_password={$shellArg((string) $pass)} --admin_email={$shellArg($email)}";

// Add install command plus commands to update siteurl option and setup language.
$commands[] = $install;
$commands[] = 'wp option update siteurl ' . $shellArg((string) $siteUrl);
$commands[] = "wp rewrite flush";
$commands[] = "wp theme activate twentytwentyfive";

return $commands;
