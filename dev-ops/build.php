<?php

declare(strict_types=1);

// Credential-free build entry point used by the reusable Deployer npm build stage.
chdir(dirname(__DIR__));
$commands = [
    // Fetch disables plugins; this secret-free phase activates the installed WordPress installers.
    ['composer', 'install', '--no-dev', '--no-interaction', '--prefer-dist', '--no-scripts'],
    [PHP_BINARY, 'vendor/bin/runtime', '--no-interaction'],
];
$composer = json_decode((string) file_get_contents('composer.json'), true, flags: JSON_THROW_ON_ERROR);

if (isset($composer['require']['sympress/asset-compiler'])) {
    $commands[] = ['composer', 'compile-assets', '--mode', 'production'];
}

$commands[] = ['composer', 'dump-autoload', '--no-dev', '--optimize', '--classmap-authoritative'];

foreach ($commands as $command) {
    $process = proc_open($command, [STDIN, STDOUT, STDERR], $pipes);

    if (!is_resource($process)) {
        exit(1);
    }

    $code = proc_close($process);

    if ($code !== 0) {
        exit($code);
    }
}
