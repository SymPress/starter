<?php

declare(strict_types=1);

// Compile a small dependency core without executing WordPress/application hooks.
// Whole-vendor preloading also sees optional integrations with absent parents.
$release = dirname(__DIR__);
$classmap = require $release . '/vendor/composer/autoload_classmap.php';
$classes = [
    'Symfony\\Contracts\\Service\\ResetInterface',
    'Psr\\Container\\ContainerInterface',
    'Psr\\Container\\ContainerExceptionInterface',
    'Psr\\Container\\NotFoundExceptionInterface',
    'Symfony\\Component\\DependencyInjection\\ContainerInterface',
    'Symfony\\Component\\DependencyInjection\\Container',
    'Symfony\\Component\\DependencyInjection\\Definition',
    'Symfony\\Component\\DependencyInjection\\ChildDefinition',
    'Symfony\\Component\\DependencyInjection\\Reference',
    'Symfony\\Component\\DependencyInjection\\TypedReference',
    'Symfony\\Component\\DependencyInjection\\Alias',
    'Symfony\\Component\\DependencyInjection\\Parameter',
    'Symfony\\Component\\DependencyInjection\\ParameterBag\\ParameterBagInterface',
    'Symfony\\Component\\DependencyInjection\\ParameterBag\\ParameterBag',
    'Symfony\\Component\\DependencyInjection\\ParameterBag\\FrozenParameterBag',
    'Symfony\\Component\\DependencyInjection\\ParameterBag\\EnvPlaceholderParameterBag',
];

foreach ($classes as $class) {
    $file = $classmap[$class] ?? null;
    if (is_string($file) && str_starts_with($file, $release . '/vendor/')) {
        if (!opcache_compile_file($file)) {
            throw new RuntimeException('A selected preload file could not be compiled.');
        }
    }
}
