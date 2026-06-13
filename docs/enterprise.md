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
WP_DEBUG=false
WP_DEBUG_DISPLAY=false
SYMPRESS_ENABLE_WORDPRESS_HARDENING=true
SYMPRESS_ENABLE_VARDUMPER=false
```

## Starter Operations

Keep WPStarter enabled for Composer install and update. It is part of the project generation flow and keeps Composer-managed WordPress files, packages, plugins, and themes synchronized.

Before a production release, run:

```sh
bin/console check
bin/console doctor
bin/console perf
```
