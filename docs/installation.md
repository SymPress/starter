# Installing SymPress Starter

This guide follows the same idea as Symfony's `composer create-project` workflow: Composer creates the project directory, then the local runtime installs and boots the application.

## Technical Requirements

Before creating a project, install:

- Docker or a compatible container runtime
- DDEV
- PHP 8.5
- Composer 2
- Git

Host PHP and Composer are used to create the project directory and run the lightweight `bin/console setup` bootstrap command. The WordPress and SymPress dependencies are installed inside DDEV.

## Creating SymPress Websites

Create a new website project:

```sh
composer create-project sympress/starter my_project_directory --no-install
cd my_project_directory
```

Use a specific development line:

```sh
composer create-project sympress/starter:"1.0.x-dev" my_project_directory --no-install
cd my_project_directory
```

Until `sympress/starter` is available on Packagist, point Composer at the VCS repository:

```sh
composer create-project sympress/starter my_project_directory --no-install \
  --repository='{"type":"vcs","url":"https://github.com/sympress/starter"}'
cd my_project_directory
```

The `--no-install` flag is intentional. It prevents Composer from installing dependencies on the host machine so DDEV can run the real install with the expected PHP, database, and webserver environment.

## Configuring the Project

Run the starter setup command from the project root:

```sh
bin/console setup my-project
```

`bin/console setup` works before `vendor/autoload.php` exists. It creates `.env`, sets the DDEV project name, updates `WP_HOME` and `WP_SITEURL`, starts DDEV, and runs `ddev composer install`.

The starter uses DDEV's `ddev.site` URLs by default, so first setup does not need to edit `/etc/hosts`.

Manual setup is also possible:

```sh
cp .env.example .env
ddev config --project-name=my-project --project-tld=ddev.site --project-type=php --docroot=public --webserver-type=nginx-fpm
```

Update the project URL values in `.env`:

```dotenv
WP_HOME=https://my-project.ddev.site
WP_SITEURL=${WP_HOME}/wp
```

## Installing Dependencies

If you used `bin/console setup`, the project is already installed. Otherwise, start DDEV and install the project manually:

```sh
ddev start
ddev composer install
```

Composer triggers WPStarter during install and update. This is intentional: WPStarter creates and syncs the generated WordPress files, writes the local WordPress configuration, and installs WordPress on a fresh database.

Default local admin credentials:

- Username: `admin`
- Password: generated during `bin/console setup` or set through `WP_ADMIN_PASSWORD`

You can override them before installation with `WP_ADMIN_USERNAME` and `WP_ADMIN_PASSWORD` in `.env`.

## Running the Website

Open the frontend:

```sh
ddev launch
```

Open the WordPress admin:

```text
https://my-project.ddev.site/wp-admin/
```

## Setting Up an Existing Project

For an existing project created from this starter:

```sh
git clone git@github.com:your-organization/your-project.git
cd your-project
bin/console setup my-project
```

Adjust `.env` if the DDEV project name differs from the default.

## Verification

Run these smoke checks:

```sh
ddev exec wp --info
ddev exec wp core is-installed
ddev exec wp db check
curl -k -I https://my-project.ddev.site
```

The HTTP check should return `200` after WordPress has been installed.

You can also run the bundled local check:

```sh
bin/console check
```
