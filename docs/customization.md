# Customizing SymPress Starter

## Project Identity

After creating a project, run:

```sh
bin/console setup my-project
```

This updates DDEV and `.env` for the local project URL.

## Optional Base Features

Optional starter behavior is controlled through `.env`:

```dotenv
SYMPRESS_ENABLE_WORDPRESS_HARDENING=false
SYMPRESS_ENABLE_VARDUMPER=false
```

Enable hardening only when the project wants the opinionated WordPress cleanup hooks:

```dotenv
SYMPRESS_ENABLE_WORDPRESS_HARDENING=true
```

Disable the development VarDumper integration for shared or production-like environments:

```dotenv
SYMPRESS_ENABLE_VARDUMPER=false
```

## Adding Project Packages

Place project-owned packages in `packages/` and give each package its own Composer package name and namespace.

Recommended naming:

```text
your-vendor/project-feature
```

Recommended namespace:

```text
YourVendor\Project\Feature
```

## Quality Commands

Run quality checks from the project root:

```sh
ddev composer cs
ddev composer static-analysis
ddev composer test
ddev composer qa
bin/console check
bin/console doctor
```

Run base MU plugin package checks from the package working directory:

```sh
ddev composer --working-dir=packages/base-mu-plugins cs
ddev composer --working-dir=packages/base-mu-plugins static-analysis
ddev composer --working-dir=packages/base-mu-plugins test
ddev composer --working-dir=packages/base-mu-plugins qa
```

Run dependency security checks:

```sh
ddev composer audit
```

Diagnose local login URL mismatches:

```sh
bin/console diagnose-login
```

Run a lightweight frontend timing and cache-header smoke check:

```sh
bin/console perf
```
