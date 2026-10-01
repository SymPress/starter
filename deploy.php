<?php

declare(strict_types=1);

namespace Deployer;

require 'recipe/common.php';

set('application', 'sympress');
set('keep_releases', 5);
set('shared_files', []);
set('shared_dirs', ['public/wp-content/uploads', 'var/log']);
set('writable_dirs', ['public/wp-content/uploads', 'var/log', 'var/cache']);
set('writable_mode', 'chmod');
set('writable_chmod_mode', '0770');
set('allow_anonymous_stats', false);
set('php_user', getenv('SYMPRESS_PHP_USER') ?: 'www-data');
set('php_group', getenv('SYMPRESS_PHP_GROUP') ?: 'www-data');

// The reusable workflow builds the project before it loads deployment credentials.
// This recipe uploads that exact artifact and never clones/builds on production.
$hostname = getenv('DEPLOY_HOSTNAME') ?: 'example.invalid';
$user = getenv('DEPLOY_USER') ?: 'deploy';
$port = getenv('DEPLOY_PORT') ?: '22';
$path = getenv('DEPLOY_PATH') ?: '/srv/sympress';

if (!ctype_digit($port) || (int) $port < 1 || (int) $port > 65535) {
    throw new \RuntimeException('DEPLOY_PORT must be a valid TCP port.');
}

foreach (['php_user', 'php_group'] as $identity) {
    if (!preg_match('/^[a-z_][a-z0-9_-]*[$]?$/D', get($identity))) {
        throw new \RuntimeException('Invalid PHP identity or group.');
    }
}

if (!preg_match('~^/[A-Za-z0-9/_-]+$~D', $path)) {
    throw new \RuntimeException('DEPLOY_PATH must be an absolute simple path.');
}

foreach (['production', 'staging'] as $stage) {
    host($stage)->setHostname($hostname)->setRemoteUser($user)->setPort((int) $port)
        ->set('deploy_path', $path)->set('stage', $stage);
}

task('deploy:upload', static function (): void {
    if (!is_file(__DIR__ . '/vendor/autoload.php') || !is_file(__DIR__ . '/public/wp/wp-load.php')) {
        throw new \RuntimeException('Build and run composer runtime:setup before loading deploy credentials.');
    }
    upload(__DIR__ . '/', '{{release_path}}', ['options' => [
        '--exclude=.git', '--exclude=.env*', '--exclude=auth.json', '--exclude=.npmrc',
        '--exclude=node_modules', '--exclude=.npm', '--exclude=.cache',
        '--exclude=.ddev', '--exclude=.github', '--exclude=operations-state', '--exclude=var',
        '--exclude=public/wp-content/uploads', '--exclude=deployment/vendor',
    ]]);
});

task('deploy:environment', static function (): void {
    // Doctor rejects symlinked env artifacts: snapshot the private shared secret.
    run('install -m 0600 {{deploy_path}}/shared/.env {{release_path}}/.env');
    $buildId = 'release-' . get('release_name');
    if (!preg_match('/^[A-Za-z0-9._-]+$/D', $buildId)) {
        throw new \RuntimeException('Invalid immutable deployment build ID.');
    }
    run('printf ' . escapeshellarg("\nSYMPRESS_KERNEL_IMMUTABLE_CACHE=true\nSYMPRESS_KERNEL_BUILD_ID=" . $buildId . "\n") . ' >> {{release_path}}/.env');
});

task('deploy:runtime', static function (): void {
    // Generate release-local config without executing a fresh-site installer.
    run('cd {{release_path}} && {{bin/php}} vendor/bin/runtime --skip wpcli --no-interaction');
    run('cd {{release_path}} && {{bin/php}} wp-cli.phar core is-installed');
    // Only an existing database may reach the normal db-check orchestration.
    run('cd {{release_path}} && {{bin/php}} vendor/bin/runtime --no-interaction');
    run('cd {{release_path}} && {{bin/php}} bin/console lint:container --no-interaction');
    run('cd {{release_path}} && {{bin/php}} vendor/bin/runtime dump-env ' . escapeshellarg(get('stage')) . ' --no-interaction');
    run('cd {{release_path}} && {{bin/php}} vendor/bin/runtime doctor --production --database-health --no-interaction');
});

task('deploy:permissions', static function (): void {
    // The deploy identity must be a member of php_group; the FPM identity reads code.
    run('chgrp -R {{php_group}} {{release_path}}');
    run('find {{release_path}} -type d -exec chmod 0750 {} +');
    run('find {{release_path}} -type f ! -perm /111 -exec chmod 0640 {} +');
    run('find {{release_path}} -type f -perm /111 -exec chmod 0750 {} +');
    foreach (['public/wp-content/uploads', 'var/log'] as $path) {
        $shared = '{{deploy_path}}/shared/' . $path;
        run('chgrp -R {{php_group}} ' . $shared);
        run('find ' . $shared . ' -type d -exec chmod 2770 {} +');
        run('find ' . $shared . ' -type f -exec chmod 0660 {} +');
    }
    // Release-specific warmed kernel cache is read-only to FPM under build-ID policy.
    run('cd {{release_path}} && {{bin/php}} vendor/bin/runtime doctor --production --database-health --php-user={{php_user}} --no-interaction');
});

task('deploy:health', static function (): void {
    // Before switching current, validate the actual WP configuration and DB.
    run('cd {{release_path}} && {{bin/php}} wp-cli.phar core is-installed');
    run('cd {{release_path}} && {{bin/php}} wp-cli.phar eval ' . escapeshellarg(
        'if (wp_get_environment_type() !== "production" && wp_get_environment_type() !== "staging") { exit(1); }'
        . 'if (!DISALLOW_FILE_EDIT || !DISALLOW_FILE_MODS || WP_DEBUG_DISPLAY || !FORCE_SSL_ADMIN) { exit(1); }',
    ));
});

task('deploy', [
    'deploy:info', 'deploy:setup', 'deploy:lock', 'deploy:release',
    'deploy:upload', 'deploy:shared', 'deploy:environment', 'deploy:writable',
    'deploy:runtime', 'deploy:permissions', 'deploy:health', 'deploy:symlink', 'deploy:cleanup', 'deploy:unlock',
]);
after('deploy:failed', 'deploy:unlock');
