# Development Tools

The starter keeps the main workflow console-based so projects do not need `make`.
When `make` is available, the `Makefile` is a convenience wrapper around the same commands.

Starter-specific DX commands live in `bin/console` so the project has one clear command surface. These bootstrap commands work before `vendor/autoload.php` exists. Extract them into a reusable SymPress package only when multiple starters or real projects need the same commands.

## Setup

```sh
bin/console setup my-project
```

This creates `.env`, configures DDEV with the `ddev.site` project TLD, starts DDEV, and runs `ddev composer install`.

DDEV's `ddev.site` wildcard DNS is the default so setup should not need administrative permission for host-file changes.

Composer install and update intentionally run WPStarter through the Composer plugin. WPStarter installs, syncs, and regenerates the WordPress project files and plugin/theme layout.

Show the available starter commands:

```sh
bin/console starter:help
```

## Health Checks

Run the full local check:

```sh
bin/console check
```

This runs Composer validation, Composer audit, the project QA command, WordPress CLI checks, database checks, and an HTTP smoke request when `.env` exists.

Run environment diagnostics:

```sh
bin/console doctor
```

Use this when a new project does not start as expected or when a template change might have affected DDEV, `.env`, or WPStarter wiring.

## Login Diagnostic

```sh
bin/console diagnose-login
```

The diagnostic prints the expected `WP_HOME` and `WP_SITEURL`, shows relevant config hints, and gives WP-CLI commands to repair mismatched database URLs.

## Reset Local Generated Files

```sh
bin/console reset --yes my-project
```

This removes generated local files such as `public/`, `vendor/`, `var/`, `.env.cached.php`, `wp-cli.yml`, and `.phpunit.cache`, then runs setup again.

## Performance Smoke

```sh
bin/console perf
```

This performs two frontend requests against `WP_HOME` and prints timing plus common cache-related response headers. It is a quick local sanity check, not a replacement for load testing.

## Optional Make Targets

```sh
make setup PROJECT=my-project
make check
make doctor
make perf
make qa
make test
make audit
make reset PROJECT=my-project
```

The Makefile is optional DX sugar. The canonical commands are `bin/console ...` and `ddev composer ...`.
