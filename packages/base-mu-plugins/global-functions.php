<?php

declare(strict_types=1);

if (!defined('ABSPATH')) {
    exit;
}

if (!function_exists('dump')) {
    function dump(mixed ...$vars): void
    {
        foreach ($vars as $var) {
            \Symfony\Component\VarDumper\VarDumper::dump($var);
        }
    }
}

if (!function_exists('dd')) {
    function dd(mixed ...$vars): never
    {
        dump(...$vars);
        wp_die('Application stopped by dd()', 'Debug & Die', ['response' => 500]);
    }
}
