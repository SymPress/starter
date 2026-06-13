# SymPress Starter Documentation

This repository is intended to be used as a GitHub template for new SymPress-based WordPress websites.

For the project creation flow, see [Installation](installation.md).

## Local environment

DDEV is the canonical local runtime. The default project is configured as:

- Project name: `sympress-starter`
- URL: `https://sympress-starter.ddev.site`
- Project TLD: `ddev.site`
- PHP: `8.5`
- Database: MariaDB `11.8`
- Web server: nginx-fpm
- Docroot: `public`

After creating a real project from the template, run:

```sh
bin/console setup my-project
```

For manual setup, configure DDEV directly:

```sh
ddev config --project-name=my-project --project-tld=ddev.site --project-type=php --docroot=public --webserver-type=nginx-fpm
```

Then create `.env` from the example and update the project URL values:

```sh
cp .env.example .env
```

```dotenv
WP_HOME=https://my-project.ddev.site
WP_SITEURL=${WP_HOME}/wp
```

## First install

Run the setup from the project root:

```sh
bin/console setup my-project
```

`bin/console setup` configures DDEV, starts the project, and runs Composer inside DDEV. Composer triggers WPStarter. WPStarter checks the database and, on a fresh install, creates WordPress with the site title from `dev-ops/orchestrate.php`.

Default local credentials:

- Username: `admin`
- Password: generated during `bin/console setup` or set through `WP_ADMIN_PASSWORD`

You can override these with `WP_ADMIN_USERNAME` and `WP_ADMIN_PASSWORD`.

## Optional Features

The starter keeps opinionated behavior disabled by default:

```dotenv
SYMPRESS_ENABLE_WORDPRESS_HARDENING=false
SYMPRESS_ENABLE_VARDUMPER=false
```

Set `SYMPRESS_ENABLE_WORDPRESS_HARDENING=true` to enable the cleanup and hardening hooks in `packages/base-mu-plugins/disable.php`.

`SYMPRESS_ENABLE_VARDUMPER` enables the Symfony VarDumper integration in local development only. It is ignored outside `WORDPRESS_ENV=development`.

## Package conventions

Starter-owned code lives in `packages/base-mu-plugins` under the `SymPress\Starter` namespace. Project-specific packages should use their own package name and namespace instead of reusing the starter namespace.

Recommended package naming:

```text
vendor/project-feature
```

Recommended namespace pattern:

```text
Vendor\Project\Feature
```

## DDEV verification

Use these commands when changing local runtime settings:

```sh
ddev start
ddev composer install
ddev exec wp --info
ddev exec wp core is-installed
ddev exec wp db check
bin/console check
bin/console doctor
curl -k -I https://my-project.ddev.site
```

For a browser check:

```sh
ddev launch
```

## Before publishing as a template

- Confirm `.env.example` contains the intended starter defaults.
- Do not commit `.env` or `.env.cached.php`.
- Keep secrets out of `.env.example`.
- Make sure generated runtime directories such as `public/`, `vendor/`, and `var/cache/` are ignored unless intentionally committed.
- Run `ddev start` and at least one WP-CLI smoke test.
- Run `ddev composer qa` and `ddev composer audit`.
