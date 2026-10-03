# Changelog

All notable changes to `sympress/starter` will be documented in this file.

The project follows semantic versioning once the first stable release is tagged.

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
