<?php

declare(strict_types=1);

namespace Deployer;

// Record the real recipe's task registration and commands without remote effects.
$settings = [];
$tasks = [];
$hooks = [];
$commands = [];
function set(string $key, mixed $value): void { $GLOBALS['settings'][$key] = $value; }
function get(string $key): mixed { return $GLOBALS['settings'][$key]; }
function host(string $stage): object {
    return new class {
        public function __call(string $method, array $arguments): self { return $this; }
    };
}
function task(string $name, mixed $action): void { $GLOBALS['tasks'][$name] = $action; }
function before(string $task, string $hook): void { $GLOBALS['hooks']['before'][$task][] = $hook; }
function after(string $task, string $hook): void { $GLOBALS['hooks']['after'][$task][] = $hook; }
function run(string $command): void {
    $GLOBALS['commands'][] = $command;
    if (getenv('PROBE_FAIL_RELOAD') && str_contains($command, 'systemctl reload')) {
        throw new \RuntimeException('Simulated reload failure.');
    }
}

set_include_path($argv[1]);
require dirname(__DIR__, 2) . '/deploy.php';
$mode = $argv[2] ?? 'graph';
if ($mode !== 'graph') {
    try {
        $tasks[$mode]();
    } catch (\RuntimeException $exception) {
        fwrite(STDERR, $exception->getMessage());
        exit(17);
    }
}
echo json_encode(['deploy' => $tasks['deploy'], 'hooks' => $hooks,
    'commands' => $commands, 'service' => get('php_fpm_service')], JSON_THROW_ON_ERROR);
