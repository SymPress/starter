# Runtime migration review

The project replaces WP Starter with `sympress/runtime`. Its configuration is `dev-ops/runtime.json`; compatibility is disabled and dotenv local overrides remain explicitly disabled to preserve the existing two-file convention. The command provider uses the injected environment reader and database status from Runtime preflight. The base MU package declares kernel boot ownership.

The dependency requires Runtime `^1.1.1` from public Packagist. The distribution release train must regenerate the committed lock against the new fixed Runtime and stable kernel/package releases before publication. The Runtime-specific VCS repository and SSH access are no longer needed. Review Runtime's [public API](https://github.com/SymPress/runtime/blob/main/docs/api.md) and [compatibility policy](https://github.com/SymPress/runtime/blob/main/docs/compatibility-policy.md) when upgrading custom extensions. Standalone commands use `vendor/bin/runtime`; `bin/console` remains the public starter command surface. WP-CLI is the independently executed, SHA512-verified root phar; removing the Composer WP-CLI bundle avoids its conflict with Symfony Process 8.1 while retaining all commands. Native downloads are pinned in `sympress-runtime.lock`; review and commit changes, using `--update-lock` only for intentional artifact updates.

Public WordPress URLs remain at the site root: `WP_SITEURL=${WP_HOME}`. The original DDEV Nginx rules map public endpoints to the physical `public/wp` core directory. The production operations recipe and the reviewed DDEV cache/security rules extend the existing routing. The starter setup command and documentation use the same root URL.


The verification sections below record historical revisions. Current October 1 production work and test limitations are documented in [production operations](production-operations.md); historical lock/test statements are not claims about the pending release train.

## Runtime 1.0.0 stable verification

The stable lock pins `1.0.0` at `56b89a0958d24d6ae62944c0dca9e205d9fb63d5`, matching both its public source and dist references. Runtime is the only updated package; the manifest uses `^1.0`.

Fresh verification covered the upgraded DDEV project and a clean dist installation in the existing isolated smoke service with a new database. Previous smoke files and its database were preserved. Both projects passed Composer QA (7 tests / 49 assertions, no skips), strict validation, audit, Runtime validation, WordPress core/database checks and kernel container inspection. The public starter doctor and WP-CLI Runtime doctor each returned 15 passing development checks on both projects.

Browser checks on both stable installations passed homepage HTTP 200, root login form, authenticated root admin dashboard and no JavaScript errors. Repeated Composer installation and standalone setup preserved `wp-config.php`, `wp-cli.yml` and the download lock byte for byte. The reviewed WP-CLI `2.12.0` pin, public URLs, Nginx routes and all unrelated dependencies remain unchanged. These are development and release checks, not production soak evidence.

## Runtime 1.0 release candidate verification

The release-candidate review used `1.0.0-rc.1` at `b532fdc06c3e46b1f7b10a99557814b283d5018d` from public Packagist. Runtime was the only changed package. That revision permitted release candidates with `^1.0@RC` and deployed through the committed lock with `composer install`.

Both the existing isolated DDEV project and a fresh project passed Composer QA (7 tests / 49 assertions), with strict Composer validation and audit passing. The fresh project installed Runtime from its public dist archive and installed WordPress into a new database. Core/database checks, kernel container inspection and Runtime validation passed. The public starter doctor and the WP-CLI Runtime bridge each reported all 15 development checks passing. Browser smoke passed for the upgraded and fresh projects: homepage HTTP 200, root login form, authenticated root admin dashboard and no JavaScript errors.

The fresh install initially exposed an unavailable latest-release lookup for WP-CLI. `dev-ops/runtime.json` now explicitly selects WP-CLI `2.12.0`, matching the existing reviewed download lock. The lock is unchanged. Repeated Composer installation and standalone Runtime setup preserve the download lock, `wp-config.php` and `wp-cli.yml` byte for byte. Upstream WP-CLI PHP 8.5 deprecations remain non-fatal. This evidence covers local development setup; it is not production soak evidence.

## Runtime 0.2.0 upgrade verification

A fresh isolated DDEV project passed Composer installation, validation and audit, PHPCS, PHPStan, PHPUnit (7 tests / 49 assertions), Runtime validation and all 15 development doctor checks. WordPress core/database checks and browser smoke passed: homepage HTTP 200, root login form, authenticated root admin dashboard and no JavaScript errors. A repeated standalone setup also passed. The download lock contains the WP-CLI 2.12.0 release URL, its checksum response and the logical `wp-cli.phar` artifact; all three SHA256 pins and the executable against the official SHA512 checksum were verified.

## Original migration verification

The following records the original migration revision, before the 0.2.0 upgrade. Verification used a fresh DDEV project with a separate database:

- Composer install and WordPress installation succeeded; direct and locked package graphs contain no `wecodemore/*` dependency.
- QA passed: 7 tests, 49 assertions, coding standards and static analysis, including the root-URL setup regression.
- The standalone doctor, `bin/console doctor --json` and `wp console doctor --json` report 14 passing checks.
- The kernel boots once; `wp console debug:container` succeeds.
- Browser smoke verified a successful homepage response, the root `/wp-login.php` form action and authenticated root `/wp-admin/` dashboard with no JavaScript errors.

Reproduce with `ddev composer install`, `ddev composer qa`, `ddev exec php bin/console doctor --json`, and `ddev exec php wp-cli.phar console debug:container`. Runtime's `tools/consumer-smoke.mjs` performs the browser checks using the private local environment credentials. WP-CLI 2.12 can print upstream PHP 8.5 deprecations; use the standalone doctor for clean machine-readable JSON.

Repeated Composer installation, global `composer install --no-plugins` and the standalone runner preserve 575 generated file hashes/link targets on the reviewed revision. Runtime restores the standard WordPress package layout and Composer autoload metadata before loading project code. QA and root-URL browser smoke pass again with this lockfile. Runtime's [mandatory integration and differential job](https://github.com/SymPress/runtime/actions/runs/36704369536) passes all 1,059 tests / 7,365 assertions without skips, the evidence check for 407 rows and 251 differential cases. Its [real WPackagist installation job](https://github.com/SymPress/runtime/actions/runs/36704369440) also passes. Successful consumer CI is required before merge; Runtime's documented offline recovery boundaries still apply.

Existing uncommitted changes in the original checkout were preserved by implementing this migration in a separate Git worktree. Generated configuration, local credentials and browser sessions are not committed.

The original private-repository migration used a read-only Runtime deploy key. Public Packagist distribution removes that requirement; the optional workflow authentication inputs remain available for project-specific private dependencies. When updating an existing environment from a previous `/wp` URL, run `vendor/bin/runtime flush-env-cache` so cached values cannot retain that URL.
