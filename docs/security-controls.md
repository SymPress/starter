# Repository security controls

The private `sympress/security` package is intentionally absent from this template
and from Demo. Its enumeration, upload sanitizer and nonce middleware are not
implied by this document. Existing author URLs are never renamed automatically.
Use `wp user list --fields=ID,user_login,user_nicename` in a private terminal to
review collisions, then choose an explicit new slug or archive policy per site.

## Production profile

Use the Composer-managed Runtime production profile and the values in
`dev-ops/production.env.example`. It disables unfiltered HTML/uploads and blocks
outbound WordPress HTTP calls except the reviewed `WP_ACCESSIBLE_HOSTS` allowlist.
Add payment, mail or other API hosts only when needed. This WordPress restriction
does not restrict raw sockets; the container network or hosting firewall must do so.
`runtime doctor --production --database-health` is a mandatory deploy gate already
implemented in `deploy.php`. Private Security CLI checks remain deferred while its
integration is prohibited.

The former `disable.php` and `legacy-cleanup.php` hooks belong to the private
Security package. Starter does not install that package or provide its enumeration
guard. Runtime production configuration and the public upload/XML-RPC policies
remain active. Review explicit hardening overrides.

Setup generates a private 64-character `APP_SECRET` when no key or key file is
configured. Existing values are preserved; use `runtime doctor --production` to
diagnose weak keys. `SYMPRESS_PROJECT_DIR` is the literal stable deployment base
for cache identity; `deploy.php` sets it independently of `releases/N`.

The nginx template observes a broader CSP in report-only mode, keeps the enforced
frame-ancestors rule, and sends Permissions-Policy and COOP. Collect violations in
browser diagnostics or configure a private reporting endpoint. Review payment
popups, embeds and API hosts before enforcement. HSTS stays opt-in after TLS
validation. This template does not inject CSP nonces into WordPress markup.

## Process and storage boundaries

`dev-ops/compose-production.example.yml` is an isolated PHP service fragment. Build
an immutable application image separately; provision volume ownership for its
non-root UID, and attach the upstream web server and database to the internal
runtime network. Application code is read-only. Only uploads, cache, logs and
bounded temporary runtime mounts are writable. Kernel compiled containers must be
prewarmed and protected according to the kernel build-ID policy. An operator
must provide the database/Redis services and private egress policy; this fragment
does not install or alter any server.

Install `php-production.ini` only for FPM. The deploy/CLI user has separate PHP
configuration and credentials. The FPM profile disables process execution and
limits file access to the selected site, temporary space, secrets and CA data.
Replace `/srv/sympress` with the actual per-site root. `open_basedir` disables PHP's
realpath cache, so measure its cost before accepting the production profile.
Neither PHP directive substitutes for OS isolation; see the
[PHP manual](https://www.php.net/manual/en/ini.core.php) and
[Compose service reference](https://docs.docker.com/reference/compose-file/services/).

The deploy identity owns executable code; FPM reads it. `deploy:permissions` checks
this boundary with Runtime doctor under the PHP identity. Provision separate
database accounts using `database-grants.example.sql`: the web account has DML
only, and an isolated CLI migration identity has schema privileges within its
one database. Never give either `FILE` or global grants. Inject migration credentials
only into the individual CLI operation, not the FPM environment or cached dump.
Plugins that perform DDL during requests need a reviewed CLI migration path.

Redis must use TLS with verified CA/hostname, authentication and a site-specific
ACL user/prefix. Do not expose its port publicly. Use the framework cache's signed
marshaller and namespace isolation as additional checks; they do not replace
backend authorization. Store Redis credentials in private secret files. An egress
proxy/firewall should admit only documented API hosts and deny metadata services
and unrelated private destinations. The internal Compose network has no general
Internet route by default.

## Releases and plugin admission

Keep `composer.lock` stable, `allow-plugins` explicit and audits mandatory. Daily
QA audits and update canaries remain enabled, without heartbeat/alert services.
The reusable deploy workflow emits a production CycloneDX SBOM, audits Node
dependencies and checks the built archive digest before extraction. Enable its
provenance attestations and pin the reviewed signer commit in production callers;
see the workflow repository's deployment documentation. No second human reviewer
is imposed for the single-maintainer organization.

Before adding a plugin, record its source, maintenance activity, supported PHP/WP
versions, license, privileges, outbound hosts and security history. Reject abandoned
or unsupported packages. Review version diffs for authentication, checkout, mail,
uploads and other critical plugins before changing the lock. Record any advisory
exception with an owner, reason and expiry; critical/actively exploited findings
must block a release.

The integrity manifest commands in private Security remain independently usable
by authorized operators, but are not installed or invoked here. Archive provenance
verifies the build transfer; it is not a periodic live filesystem integrity scan.
Keep an independently trusted, immutable manifest/artifact outside the application
host before enabling such monitoring.

See [threat model](threat-model.md) and [incident procedure](incident-response.md).
