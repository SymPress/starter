# Runtime migration review

The project replaces WP Starter with `sympress/runtime`. Its configuration is `dev-ops/runtime.json`; compatibility is disabled and dotenv local overrides remain explicitly disabled to preserve the existing two-file convention. The command provider uses the injected environment reader and database status from Runtime preflight. The base MU package declares kernel boot ownership.

The dependency follows Runtime main in its private repository; the lockfile pins merged commit `b1c1662`. All six Runtime PRs are merged. SSH repository access is required. WP-CLI is the independently executed, SHA512-verified root phar; removing the Composer WP-CLI bundle avoids its conflict with Symfony Process 8.1 while retaining all commands.

The DDEV Nginx configuration serves physical `/wp/wp-login.php` and `/wp/wp-admin/` endpoints directly. Redirecting those endpoints to the virtual root discarded login POSTs or caused redirect loops with `WP_SITEURL=/wp`. Public root routes remain available.

Verification in a fresh DDEV project with a separate database:

- Composer install and WordPress installation succeeded; direct and locked package graphs contain no `wecodemore/*` dependency.
- QA passed: 6 tests, 47 assertions, coding standards and static analysis.
- The standalone doctor, `bin/console doctor --json` and `wp console doctor --json` report 14 passing checks.
- The kernel boots once; `wp console debug:container` succeeds.
- Browser smoke verified a successful homepage response and authenticated admin dashboard with no JavaScript errors.

Reproduce with `ddev composer install`, `ddev composer qa`, `ddev exec php bin/console doctor --json`, and `ddev exec php wp-cli.phar console debug:container`. Runtime's `tools/consumer-smoke.mjs` performs the browser checks using the private local environment credentials. WP-CLI 2.12 can print upstream PHP 8.5 deprecations; use the standalone doctor for clean machine-readable JSON.

Repeated Composer installation, global `composer install --no-plugins` and the standalone runner preserve 543 generated file hashes/link targets. Runtime restores the standard WordPress package layout and Composer autoload metadata before loading project code. Real WPackagist plugin/theme/core installation also passes in Runtime's separate integration job. QA #3 is merged and Runtime's remote QA succeeds. Starter CI currently fails while cloning the private Runtime repository because it lacks read access. No CI credentials or access settings have been changed. Keep this PR in draft until that access is configured and its CI passes; Runtime's documented offline recovery boundaries still apply.

Existing uncommitted changes in the original checkout were preserved by implementing this migration in a separate Git worktree. Generated configuration, local credentials and browser sessions are not committed.
