# SymPress Starter

## Purpose and boundaries

This repository is the source template for new SymPress WordPress websites. Keep it
small, secure by default and usable before Composer dependencies exist. Project-only
features belong in generated projects or reusable packages, not in this template.

## Read first

- `README.md` — supported setup and command surface.
- `docs/starter.md` — owned versus generated files and runtime conventions.
- `docs/development.md` — extension and package-extraction rules.
- `bin/console` — the public bootstrap, setup and diagnostic entry point.
- `.sympress/cli.json` — the CLI template/profile/package contract.

`public/`, `vendor/`, runtime caches and local `.env` files are generated. Do not
commit them. Base runtime behavior belongs in `packages/base-mu-plugins/`; website
configuration belongs in `config/`.

## Verification

The normal full static/unit contract is:

```sh
ddev composer qa
```

Use the matching focused scripts (`cs`, `static-analysis`, `test`) while iterating.
Changes to setup, Composer/WPStarter wiring, DDEV, database or HTTP behavior also
require the DDEV Smoke workflow or an equivalent fresh local setup. Commands in
`bin/console` must continue to work before `vendor/autoload.php` exists.

## Invariants

- `bin/console` remains the single public starter command surface.
- `.sympress/cli.json` must match the starter package, setup command and supported
  project profiles; update it with starter behavior.
- Never restore a shared default admin password. Setup generates or accepts one.
- Keep WordPress core/content locations aligned across Composer, WPStarter and DDEV.
- Extract behavior to a package only after more than one real consumer needs it.

## Definition of done

Keep README examples, manifest metadata and executable commands consistent. Run the
smallest relevant checks plus `composer qa` before release, and report any DDEV smoke
not run. Do not commit secrets, local DDEV output or generated WordPress files.
