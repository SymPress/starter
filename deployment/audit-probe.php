<?php

declare(strict_types=1);

namespace Deployer;

require 'recipe/common.php';

localhost('fixture');
task('deploy:audit-probe', static function (): void {
    $release = getenv('SYMPRESS_RELEASE_DIRECTORY');
    if (!is_string($release) || !is_file($release . '/deployment/vendor/composer/installed.json')) {
        throw new \RuntimeException('The consumer did not receive the audited release artifact.');
    }
    $inventory = json_decode(file_get_contents($release . '/sympress-sbom.cdx.json'), true, 512, JSON_THROW_ON_ERROR);
    if (($inventory['bomFormat'] ?? null) !== 'CycloneDX') {
        throw new \RuntimeException('The consumer did not receive the independent SBOM.');
    }
    writeln('Audited dependency artifact reached the trusted consumer recipe.');
});
task('deploy', ['deploy:audit-probe']);
