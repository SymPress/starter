# Runtime migration review

The project replaces WP Starter with `sympress/runtime`. Its configuration is `dev-ops/runtime.json`; compatibility is disabled and dotenv local overrides remain explicitly disabled to preserve the existing two-file convention. The command provider uses the injected environment reader and database status from Runtime preflight. The base MU package declares kernel boot ownership.

The dependency follows Runtime main in its private repository; the lockfile pins merged commit `b1c1662`. All six Runtime PRs are merged. Private repository access is required through SSH or Composer GitHub authentication. WP-CLI is the independently executed, SHA512-verified root phar; removing the Composer WP-CLI bundle avoids its conflict with Symfony Process 8.1 while retaining all commands.

Public WordPress URLs remain at the site root: `WP_SITEURL=${WP_HOME}`. The original DDEV Nginx rules map public endpoints to the physical `public/wp` core directory. No Nginx routing changes are required by this migration. The starter setup command and documentation use the same root URL.

Verification in a fresh DDEV project with a separate database:

- Composer install and WordPress installation succeeded; direct and locked package graphs contain no `wecodemore/*` dependency.
- QA passed: 7 tests, 49 assertions, coding standards and static analysis, including the root-URL setup regression.
- The standalone doctor, `bin/console doctor --json` and `wp console doctor --json` report 14 passing checks.
- The kernel boots once; `wp console debug:container` succeeds.
- Browser smoke verified a successful homepage response, the root `/wp-login.php` form action and authenticated root `/wp-admin/` dashboard with no JavaScript errors.

Reproduce with `ddev composer install`, `ddev composer qa`, `ddev exec php bin/console doctor --json`, and `ddev exec php wp-cli.phar console debug:container`. Runtime's `tools/consumer-smoke.mjs` performs the browser checks using the private local environment credentials. WP-CLI 2.12 can print upstream PHP 8.5 deprecations; use the standalone doctor for clean machine-readable JSON.

Repeated Composer installation, global `composer install --no-plugins` and the standalone runner preserve 543 generated file hashes/link targets. Runtime restores the standard WordPress package layout and Composer autoload metadata before loading project code. Real WPackagist plugin/theme/core installation also passes in Runtime's separate integration job. QA #3 is merged and Runtime's remote QA succeeds. Starter CI currently fails while cloning the private Runtime repository because it lacks read access. No CI credentials or access settings have been changed. Keep this PR in draft until that access is configured and its CI passes; Runtime's documented offline recovery boundaries still apply.

Existing uncommitted changes in the original checkout were preserved by implementing this migration in a separate Git worktree. Generated configuration, local credentials and browser sessions are not committed.

GitHub rejects deploy keys for the private Runtime repository. The consumer workflows already forward `COMPOSER_AUTH_JSON`; it must contain GitHub authentication with read access to Runtime. The rejected deploy-key attempt left no new keys or CI secrets. Changing the repository's deploy-key policy is not part of this migration. When updating an existing environment from a previous `/wp` URL, run `vendor/bin/sympress-runtime flush-env-cache` so cached values cannot retain that URL.
