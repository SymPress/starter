# Enterprise Readiness

## Deployment

Build artifacts should be created outside the production runtime.

Recommended production install:

```sh
composer install --no-dev --prefer-dist --optimize-autoloader --no-interaction
```

Run WordPress setup, migrations, cache warmups, and deployment-specific commands explicitly in the release pipeline.

## Secrets

Keep secrets out of Git and out of `.env.example`.

Provide production values through the deployment platform, secret manager, or environment-specific configuration.

Minimum production secrets:

- database credentials
- WordPress salts
- admin/bootstrap credentials, if used
- API keys for mail, CDN, object cache, monitoring, or external services

## Cache Strategy

The starter includes local nginx FastCGI caching for DDEV.

Production projects should define their cache layers explicitly:

- page cache or CDN
- object cache, usually Redis
- PHP OPcache
- browser cache headers for immutable assets
- purge strategy for editorial workflows

Use `bin/console perf` locally to confirm the frontend returns successfully and to inspect cache-related response headers after runtime or nginx changes.

## Cron

Disable traffic-driven WordPress cron in production when the hosting platform supports scheduled jobs:

```dotenv
DISABLE_WP_CRON=true
```

Then run cron through the platform scheduler:

```sh
wp cron event run --due-now
```

## Backups

Production projects should document restore-tested backups for:

- database
- uploads/media
- environment configuration
- deployment artifacts

Backup checks should include at least one restore rehearsal before launch.

## Object Cache

Enterprise projects should use a persistent object cache for high-traffic sites.

Document the selected backend, connection settings, eviction policy, and operational owner.

## Observability

Production projects should ship structured logs and health checks to the chosen platform.

Recommended baseline:

- PHP error logs
- webserver access/error logs
- WordPress fatal error logs
- uptime check for the frontend
- uptime check for `/wp-login.php` or the admin entrypoint
- dependency/security update monitoring
- composer audit alerts and dependency update pull requests

## Runtime Modes

Keep development-only features disabled in production unless explicitly approved.

Review these values before launch:

```dotenv
WORDPRESS_ENV=production
DISALLOW_FILE_EDIT=true
DISALLOW_FILE_MODS=true
DISALLOW_UNFILTERED_HTML=true
ALLOW_UNFILTERED_UPLOADS=false
FORCE_SSL_ADMIN=true
WP_DEBUG=false
WP_DEBUG_DISPLAY=false
WP_HTTP_BLOCK_EXTERNAL=true
WP_ALLOW_MULTISITE=false
MULTISITE=false
SYMPRESS_ENABLE_WORDPRESS_HARDENING=true
SYMPRESS_ENABLE_VARDUMPER=false
```

With `WP_HTTP_BLOCK_EXTERNAL=true`, use a narrow `WP_ACCESSIBLE_HOSTS` allowlist
for Wordfence and every other approved outbound integration.

## Security Boundary

Composer audits use the Wordfence-backed WP Sec Adv feed, so Composer-managed
WordPress core, plugin, and theme advisories are checked alongside Packagist
dependencies. The two upstream-unpatched, all-version findings are narrowly
waived with reasons in `composer.json` and remain visible in audit output. For
critical production pipelines, replace the public feed URL with a self-hosted
WP Sec Adv instance.

The direct Wordfence Intelligence v3 gate additionally inventories the files
actually present in the release, including inactive and non-Composer plugins.
Refresh one shared external feed cache in CI with an organization-owned
`WORDFENCE_INTELLIGENCE_API_KEY`; never place the key in the release:

```sh
vendor/bin/sympress-security feed:update \
  --provider=wordfence \
  --output=/trusted/security-feeds/wordfence-v3.json
```

Production receives `SYMPRESS_WORDFENCE_FEED` pointing to that cache and may
use `SYMPRESS_CISA_KEV` for a trusted local KEV snapshot. The default 24-hour
Wordfence freshness policy fails closed when intelligence is unavailable.

Before switching traffic to a production release, prewarm the SymPress kernel
cache and create the integrity manifest outside the release:

```sh
vendor/bin/sympress-security manifest:create \
  --project=. \
  --output=/trusted/manifests/release.json
```

Then make the release, including the kernel cache, read-only for the PHP worker,
include `dev-ops/nginx/security.conf` before the generic PHP location, and run
the gate as that worker user:

```sh
SYMPRESS_SECURITY_MANIFEST=/trusted/manifests/release.json composer security:check
```

The gate requires production WordPress settings, rejects writable executable
code and kernel-cache paths, and reports PHP-like files in writable upload and
log directories. Store the expected manifest with a separate trusted verifier.
Wordfence or an equivalent service remains responsible for the WAF, login
protection, malware scanning, and live threat response.

## Starter Operations

Keep SymPress Runtime enabled for Composer install and update. It is part of the project generation flow and keeps Composer-managed WordPress files, packages, plugins, and themes synchronized.

Before a production release, run:

```sh
bin/console check
bin/console doctor
bin/console perf
```
