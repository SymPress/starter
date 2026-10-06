<?php

declare(strict_types=1);

namespace Deployer;

// Record the real recipe's task registration and commands without remote effects.
$settings = [];
$tasks = [];
$hooks = [];
$commands = [];
$uploads = [];
function set(string $key, mixed $value): void { $GLOBALS['settings'][$key] = $value; }
function get(string $key, mixed $default = null): mixed { return $GLOBALS['settings'][$key] ?? $default; }
function host(string $stage): object {
    return new class {
        public function __call(string $method, array $arguments): self {
            if ($method === 'set') { set($arguments[0], $arguments[1]); }
            if ($method === 'setForwardAgent') { set('forward_agent', $arguments[0]); }
            return $this;
        }
    };
}
function task(string $name, mixed $action): void { $GLOBALS['tasks'][$name] = $action; }
function before(string $task, string $hook): void { $GLOBALS['hooks']['before'][$task][] = $hook; }
function after(string $task, string $hook): void { $GLOBALS['hooks']['after'][$task][] = $hook; }
function run(string $command): string {
    $GLOBALS['commands'][] = $command;
    if (getenv('PROBE_FAIL_RELOAD') && str_contains($command, 'systemctl reload')) {
        throw new \RuntimeException('Simulated reload failure.');
    }
    if (getenv('PROBE_FAIL_RESET') && str_contains($command, 'cgi-fcgi')) {
        throw new \RuntimeException('Simulated reset failure.');
    }
    if (str_contains($command, 'runtime doctor') && getenv('PROBE_DOCTOR_JSON') !== false) {
        return getenv('PROBE_DOCTOR_JSON');
    }
    return str_contains($command, 'readlink') ? (getenv('PROBE_PREVIOUS_RELEASE') ?: '') : '';
}
function test(string $command): bool { return getenv('PROBE_PREVIOUS_RELEASE') !== false; }
function invoke(string $name): void {
    if ($name === 'deploy:unlock') { $GLOBALS['commands'][] = 'unlock'; return; }
    runTask($name);
}
function upload(string $source, string $destination, array $options = []): void {
    $GLOBALS['uploads'][] = ['source' => $source, 'destination' => $destination, 'options' => $options];
}
function runTask(string $name): void {
    $action = $GLOBALS['tasks'][$name];
    if (is_array($action)) {
        foreach ($action as $child) {
            runTask($child);
        }
    } else {
        $action();
    }
}

set_include_path($argv[1]);
require dirname(__DIR__, 2) . '/deploy.php';
$mode = $argv[2] ?? 'graph';
set('release_name', '42');
if ($mode === 'deploy:recover-published') {
    runTask('deploy:remember-current');
    if (getenv('PROBE_PUBLISHED')) { runTask('deploy:mark-published'); }
    if (getenv('PROBE_LOCK_ACQUIRED')) { runTask('deploy:mark-locked'); }
}
$failed = false;
if ($mode !== 'graph') {
    try {
        runTask($mode);
    } catch (\RuntimeException $exception) {
        fwrite(STDERR, $exception->getMessage());
        $failed = true;
    }
}
echo json_encode(['deploy' => $tasks['deploy'], 'hooks' => $hooks,
    'refresh' => $tasks['deploy:refresh'], 'commands' => $commands, 'uploads' => $uploads,
    'tools' => get('sympress_tools_path'), 'log_group' => get('log_group'),
    'service' => get('php_fpm_service'), 'writable_dirs' => get('writable_dirs'),
    'forward_agent' => get('forward_agent')], JSON_THROW_ON_ERROR);
exit($failed ? 17 : 0);
