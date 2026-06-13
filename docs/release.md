# Release Process

## Package Names

- Starter repository: `sympress/starter`
- Base MU plugin package: `sympress/base-mu-plugins`

## Versioning

Use semantic versioning for stable releases.

Tag the starter and all required SymPress packages before publishing a stable starter release.

Recommended tag flow:

```sh
git tag 1.0.0
git push origin 1.0.0
```

## Packagist

Enable Packagist auto-updates for:

- `sympress/starter`
- `sympress/base-mu-plugins`
- `sympress/kernel`
- `sympress/monolog-bundle`
- `sympress/wp-cli-console`

After publishing, verify:

```sh
composer create-project sympress/starter my_project_directory --no-install
cd my_project_directory
bin/console setup my-project
bin/console check
```

## Release Checklist

- Update `CHANGELOG.md`.
- Confirm `composer validate --no-check-publish`.
- Run `composer audit --locked`.
- Run `composer qa`.
- Run the DDEV smoke test.
- Confirm `bin/console starter:help` works without `vendor/autoload.php`.
- Confirm `.env`, `.env.cached.php`, `public/`, `vendor/`, and `var/` are not committed.
- Confirm `.gitattributes` excludes only local-only artifacts from Composer archives.
