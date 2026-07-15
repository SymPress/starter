# SymPress Starter

Composer project starter and GitHub template for new WordPress websites in the SymPress ecosystem. The starter ships with a DDEV-ready local environment, Composer-managed WordPress core, a small base MU plugin package, SymPress kernel bootstrapping, and default quality tooling.

## What is included

- WordPress generated into `public/wp` with content in `public/wp-content`
- SymPress kernel, Monolog bundle, WP-CLI console, and optional profiler
- Base MU plugins in `packages/base-mu-plugins`
- DDEV configuration for PHP 8.5, MariaDB 11.8, and nginx-fpm
- WPStarter orchestration for first install and repeatable local setup
- PHPCS, PHPStan, PHPUnit, Composer audit, Dependabot/Renovate, and DDEV smoke-test wiring

## Requirements

- Docker or a compatible container runtime
- [DDEV](https://ddev.com/)
- Git
- PHP 8.5 and Composer 2 for creating and bootstrapping the project

Project dependencies are installed inside DDEV. Host PHP/Composer are only needed for `composer create-project` and the lightweight `bin/console setup` bootstrap command.

## Creating Projects

The recommended project creation path is the standalone SymPress CLI. The CLI
discovers this starter's `.sympress/cli.json` manifest automatically, so project
types, setup commands and package suggestions can evolve with this repository:

```sh
sympress new my-project
```

Use `--manifest=https://github.com/SymPress/starter` when you want to pin or test
manifest discovery explicitly.

Create a new SymPress website project:

```sh
composer create-project sympress/starter my_project_directory --no-install
cd my_project_directory
```

Use a specific development line:

```sh
composer create-project sympress/starter:"1.0.x-dev" my_project_directory --no-install
cd my_project_directory
```

Until the package is published on Packagist, use the repository explicitly:

```sh
composer create-project sympress/starter my_project_directory --no-install \
  --repository='{"type":"vcs","url":"https://github.com/sympress/starter"}'
cd my_project_directory
```

Configure the local project name:

```sh
bin/console setup my-project
```

`bin/console` is the single public command surface for the starter. The starter commands work before `vendor/autoload.php` exists, so they can be used immediately after `composer create-project --no-install`.

## Local setup

`bin/console setup` creates `.env`, updates the DDEV URL settings, starts DDEV, and installs dependencies inside the container.

The starter uses DDEV's `ddev.site` URLs by default so first setup works without editing `/etc/hosts`.

Manual setup is also possible:

```sh
cp .env.example .env
ddev config --project-name=my-project --project-tld=ddev.site --project-type=php --docroot=public --webserver-type=nginx-fpm
ddev start
ddev composer install
```

WPStarter runs through Composer and creates the generated WordPress files/configuration. On a fresh database it installs WordPress with these development credentials unless overridden via environment variables:

- Username: `admin`
- Password: generated during `bin/console setup` or set through `WP_ADMIN_PASSWORD`

WPStarter is intentionally part of the Composer install/update flow because it installs, syncs, and regenerates the WordPress project files and plugin/theme layout.

Open the site:

```sh
ddev launch
```

Admin URL:

```text
https://my-project.ddev.site/wp-admin/
```

## Common commands

```sh
ddev start
ddev stop
ddev restart
ddev composer install
ddev composer update
ddev composer qa
ddev composer cs
ddev composer static-analysis
ddev composer test
ddev composer audit
ddev exec wp --info
ddev exec wp db check
bin/console starter:help
bin/console setup my-project
bin/console check
bin/console doctor
bin/console perf
bin/console diagnose-login
bin/console reset --yes my-project
```

Optional Make targets are available when `make` is installed:

```sh
make setup PROJECT=my-project
make check
make doctor
make perf
make qa
make test
make audit
```

Use the login diagnostic when local admin redirects or cookies do not match the expected project URL:

```sh
bin/console diagnose-login
bin/console diagnose-login --env-file=.env.example
```

## Project structure

```text
.
├── .ddev/                     DDEV local environment
├── bin/console                Single starter command surface
├── config/                    SymPress and WordPress configuration
├── dev-ops/                   WPStarter and server support files
├── packages/base-mu-plugins/  Starter MU plugin package
├── .sympress/cli.json         SymPress CLI project creation/update manifest
├── public/                    Generated WordPress webroot, ignored by Git
├── composer.json              Root project dependencies
└── README.md
```

## Documentation

- [Installation](docs/installation.md)
- [Development tools](docs/development.md)
- [Environment configuration](docs/environment.md)
- [Starter notes](docs/starter.md)
- [Customization](docs/customization.md)
- [Enterprise readiness](docs/enterprise.md)
- [Release process](docs/release.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
