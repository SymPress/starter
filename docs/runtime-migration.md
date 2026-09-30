# Runtime migration review

The project replaces WP Starter with `sympress/runtime`. Its configuration is `dev-ops/runtime.json`; compatibility is disabled and dotenv local overrides remain explicitly disabled to preserve the existing two-file convention. The command provider uses the injected environment reader and database status from Runtime preflight. The base MU package declares kernel boot ownership.

The dependency pins Runtime `0.2.0` from its private repository. Follow the [Runtime 0.2.0 upgrade notes](https://github.com/SymPress/runtime/blob/v0.2.0/docs/releases/0.2.0.md) when upgrading existing projects. Standalone commands use `vendor/bin/runtime`; `bin/console` remains the public starter command surface. Private repository access is required through SSH or Composer GitHub authentication. WP-CLI is the independently executed, SHA512-verified root phar; removing the Composer WP-CLI bundle avoids its conflict with Symfony Process 8.1 while retaining all commands. Native downloads are pinned in `sympress-runtime.lock`; review and commit changes, using `--update-lock` only for intentional artifact updates.

Public WordPress URLs remain at the site root: `WP_SITEURL=${WP_HOME}`. The original DDEV Nginx rules map public endpoints to the physical `public/wp` core directory. No Nginx routing changes are required by this migration. The starter setup command and documentation use the same root URL.

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

Repeated Composer installation, global `composer install --no-plugins` and the standalone runner preserve 575 generated file hashes/link targets on the reviewed revision. Runtime restores the standard WordPress package layout and Composer autoload metadata before loading project code. QA and root-URL browser smoke pass again with this lockfile. Runtime's [mandatory integration and differential job](https://github.com/SymPress/runtime/actions/runs/36704369536) passes all 1,059 tests / 7,365 assertions without skips, the evidence check for 407 rows and 251 differential cases. Its [real WPackagist installation job](https://github.com/SymPress/runtime/actions/runs/36704369440) also passes. The previous CI authentication blocker is resolved by the read-only deploy key described below. Successful consumer CI is required before merge; Runtime's documented offline recovery boundaries still apply.

Existing uncommitted changes in the original checkout were preserved by implementing this migration in a separate Git worktree. Generated configuration, local credentials and browser sessions are not committed.

The project owner approved enabling deploy keys for SymPress. A repository-scoped, read-only Runtime key now supplies `COMPOSER_SSH_KEY` to the consumer workflows; `COMPOSER_SSH_KNOWN_HOSTS` pins GitHub's published host keys. The workflows are pinned to the reviewed SSH-support commit. CI must pass with that access before merge. When updating an existing environment from a previous `/wp` URL, run `vendor/bin/runtime flush-env-cache` so cached values cannot retain that URL.
