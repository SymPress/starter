<?php

declare(strict_types=1);

namespace WeCodeMore\WpStarter;

$config = (object) [
    'title' => 'SymPress Starter',
];

$shellArg = static fn (string $value): string => \escapeshellarg($value);

$env = new Env\WordPressEnvBridge();

// If env configuration is invalid nothing to do.
if (!$env->read(Util\DbChecker::WPDB_ENV_VALID)) {
    return ['wp --version'];
}

// If WP already installed, let's just tell WP Cli to check it.
if ($env->read(Util\DbChecker::WP_INSTALLED)) {
    return ['wp db check'];
}

$commands = [];

// If DB does not exist, let's tell WP Cli to create it.
if (!$env->read(Util\DbChecker::WPDB_EXISTS)) {
    $commands[] = 'wp db create';
}

// Build install command.
$user = $env->read('WP_ADMIN_USERNAME') ?: 'admin';
$pass = $env->read('WP_ADMIN_PASSWORD') ?: \bin2hex(\random_bytes(16));
$home = $env->read('WP_HOME');
$siteUrl = $env->read('WP_SITEURL') ?: $home;
$email = "{$user}@admin.com";

if (!$env->read('WP_ADMIN_PASSWORD')) {
    \fwrite(STDOUT, "Generated transient WordPress admin password: {$pass}\n");
}
$install = "wp core install";
$install .= " --skip-packages";
$install .= " --title={$shellArg($config->title)} --url={$shellArg((string) $home)}";
$install .= " --admin_user={$shellArg((string) $user)} --admin_password={$shellArg((string) $pass)} --admin_email={$shellArg($email)}";

// Add install command plus commands to update siteurl option and setup language.
$commands[] = $install;
$commands[] = 'wp option update siteurl ' . $shellArg((string) $siteUrl);
$commands[] = "wp rewrite flush";
$commands[] = "wp theme activate twentytwentyfive";

return $commands;
