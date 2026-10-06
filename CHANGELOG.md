# Changelog

All notable changes to `sympress/starter` will be documented in this file.

The project follows semantic versioning once the first stable release is tagged.

## 1.1.5 — 2026-10-06

- Keep the release-local kernel cache out of group-writable directories.
- Evaluate the PHP-user production doctor report and accept only cross-identity readability unknowns; reject failed and malformed checks.
- Disable SSH agent forwarding to deployment hosts.
- Check prepublication WordPress hardening and database access through the private FPM socket, where the web policy applies.
- Advance the fixed update-canary source baseline to `v1.1.5`; locked dependencies remain unchanged.

## 1.1.4 — 2026-10-05

- Require and lock Runtime 1.2.3 and Kernel 1.1.5, keeping outbound HTTP blocking opt-in and mutable cache metadata fresh without reader invalidation.
- Advance the fixed update-canary source baseline to `v1.1.4`.

## 1.1.3 — 2026-10-04

- Explicitly disable JIT while retaining OPcache in the supported WordPress production profile, with a real FPM regression for inherited configuration and request-time activation.
- Advance the fixed source baseline for update canaries to `v1.1.3`; Composer dependencies remain unchanged.

## 1.1.1 — 2026-10-03

- Preserve the browser's default payment permission so production headers do not disable checkout integrations using Payment Request.

## 1.1.0 — 2026-10-03

- Use Runtime 1.2's Composer-managed production policy and lock the released Runtime, Monolog security-audit and Profiler storage-permission fixes. Private Security is not required or loaded.
- Separate production hardening from opt-in legacy content cleanup; preserve ordinary feeds, comments, roles and block styles by default.
- Add report-only CSP, Permissions-Policy and COOP, FPM process/file restrictions, read-only container and split database-grant examples.
- Document repository threat boundaries, plugin admission and incident handling. HSTS remains opt-in after TLS validation; hosting/egress provisioning remains operator-owned.

## 1.0.0 — 2026-10-02

- Initial SymPress Starter package for Composer `create-project` and GitHub templates.
- DDEV-ready WordPress project setup with PHP 8.5, MariaDB 11.8, nginx-fpm, and `ddev.site` project URLs.
- Composer-managed WordPress core and base MU plugin package.
- PHPCS, PHPStan, PHPUnit, Composer audit, Dependabot/Renovate, and DDEV smoke-test workflows.
- Single `bin/console` command surface for setup, checks, diagnostics, reset, and performance smoke checks.
