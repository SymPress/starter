<?php

declare(strict_types=1);

use Symfony\Component\DependencyInjection\Loader\Configurator\ContainerConfigurator;

return static function (ContainerConfigurator $container): void {
    $parameters = $container->parameters();

    $parameters->set('wordpress.content_dir', defined('WP_CONTENT_DIR') ? WP_CONTENT_DIR : null);
    $parameters->set('wordpress.content_url', function_exists('content_url') ? content_url('/') : null);
};
