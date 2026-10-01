# Production operations

This recipe targets PHP 8.5 FPM, nginx, MariaDB and Composer-managed WordPress.
It is executable, but hostname, Unix identities, SSH host keys, backup encryption
recipient and notification recipient must be selected for the actual deployment.
Do not apply it to a running site without the site's change approval.

## Build before deployment credentials

The reusable `deploy-deployer.yml` workflow builds in `working_directory` before it loads
`GITHUB_USER_SSH_KEY`. Its tool project is `deployment/`, with committed
`composer.json` and `composer.lock`; dependencies are installed with
`--no-dev --no-scripts --no-plugins`. The default `./vendor/bin/dep deploy` works inside `deployment/`: its thin
`deployment/deploy.php` loads the project recipe. The locked root npm `build`
script calls `dev-ops/build.php` before SSH credentials are loaded; no custom
deploy override is needed.
The recipe accepts stages `production` and `staging` and reads `DEPLOY_HOSTNAME`,
`DEPLOY_PORT`, `DEPLOY_USER` and optional `DEPLOY_PATH` (default `/srv/sympress`).
Supply independently verified `SSH_KNOWN_HOSTS`; dependency install credentials
must be a separate read-only key and must end before any lifecycle/build code.

Build the artifact without production credentials:

```sh
composer install --no-dev --no-interaction --prefer-dist --no-scripts --no-plugins
php vendor/bin/runtime --no-interaction
# Demo only: composer compile-assets --mode production
composer dump-autoload --no-dev --optimize --classmap-authoritative
composer audit --locked
composer --working-dir=deployment install --no-dev --no-scripts --no-plugins
```

Do the install in an isolated build environment; `runtime:setup` runs the explicit
reviewed orchestration provider. The demo asset compiler requires the npm lock;
production must not use `--ignore-lock`. Run PHP/asset QA in a separate development install before the final `--no-dev`
install; dropping dev autoload alone leaves dev bundle metadata behind. Authoritative autoload is for the completed deploy artifact; development
keeps dynamic class discovery, and WordPress/plugin classes outside Composer
remain WordPress-owned. Do not inject a production `.env` into a build.

Make the deploy identity a member of the selected PHP group (`www-data` by
default), provision deployment-root group traversal, and select `SYMPRESS_PHP_USER`
and `SYMPRESS_PHP_GROUP` when using a different FPM pool.

Provision `/srv/sympress/shared/.env` privately (0600, readable by the required
runtime identity) and the persistent paths below before first deployment. DB,
mail, salts and any API credentials belong here or in a private secret manager.
A first production site installation is an explicit operator action; routine
deployment expects an existing database and never seeds/resets its content.

```dotenv
WORDPRESS_ENV=production
WP_HOME=https://www.example.com
WP_SITEURL=${WP_HOME}
DISALLOW_FILE_EDIT=true
DISALLOW_FILE_MODS=true
DISALLOW_UNFILTERED_HTML=true
ALLOW_UNFILTERED_UPLOADS=false
FORCE_SSL_ADMIN=true
WP_DEBUG=false
WP_DEBUG_DISPLAY=false
WP_DEBUG_LOG=true
DISABLE_WP_CRON=true
# Only when TLS terminates at a controlled reverse proxy:
# WP_FORCE_SSL_FORWARDED_PROTO=true
# SYMPRESS_RUNTIME_TRUSTED_PROXIES=10.10.0.0/24
```

Add the private DB connection and WordPress salts. Task-6 Runtime requires canonical
`WP_HOME` for staging/production and trusts forwarded HTTPS only when the immediate
`REMOTE_ADDR` matches `SYMPRESS_RUNTIME_TRUSTED_PROXIES` and the header is exactly
`https`. Do not trust `X-Forwarded-For` as the peer address. Until the fixed Runtime
release is published, these changes must be tested with the isolated reviewed
package harness; `^1.1.1` is the public minimum, not a claim that v1.1.1 contains
these subsequent fixes. The release train must pin the new fixed release.

Deployer uploads the built artifact, copies a private regular `.env` snapshot from shared storage, symlinks `public/wp-content/uploads`
and `var/log`, creates release-specific `var/cache`, generates release-local Runtime configuration with installer commands skipped,
checks that WordPress is already installed, then runs Runtime and
`bin/console lint:container` to warm/validate the kernel, writes the selected environment dump, then runs
`runtime doctor --production --database-health` and a real WP configuration/DB
gate before atomically changing `current`. The recipe selects
`SYMPRESS_KERNEL_IMMUTABLE_CACHE=true` with a unique nonempty
`SYMPRESS_KERNEL_BUILD_ID=release-<release_name>` for every release; default
content/listing checks remain active outside this explicit deployment policy. The source recipe never clones or
builds on production. Failed pre-switch checks leave the current release active;
`deploy:failed` unlocks. The database is not automatically migrated or rolled back.

The deploy identity owns release files. The permission step assigns the selected
PHP group, makes directories 0750 and code/config 0640 (executables 0750), makes
shared uploads/logs 2770/0660, then runs doctor for the selected PHP identity.
PHP-FPM receives read/execute access to
code/config and write access only to uploads/logs/runtime cache as required. Warm
and seal release-specific compiled kernel caches where supported; use Runtime's
`--php-user=www-data --webroot=.../public` doctor to verify that identity after
permission provisioning. Never make the project root the HTTP docroot.

```sh
./deployment/vendor/bin/dep -f deploy.php deploy production -v
# If a code-only rollback is appropriate:
./deployment/vendor/bin/dep -f deploy.php rollback production -v
```

A privileged operator must gracefully reload PHP-FPM after deploy **and rollback**
when timestamp checks or preload are disabled. Verify the new health response after
reload. Do not automatically restore the database for a code rollback; inspect
migration compatibility and use an approved paired backup when restoration is
needed. Five old releases are retained. Shared media/logs/.env survive rollbacks.

## nginx and cache policy

Render the server recipe before installation:

```sh
python3 dev-ops/render-nginx.py --hostname www.example.com \
  --root /srv/sympress --output /tmp/sympress-nginx
```

Install the rendered files in the corresponding release `dev-ops/nginx` paths and
include `cache-http.conf` once inside nginx `http {}` and `production-server.conf`
in the site's enabled virtual hosts. Set the actual FPM socket/certificate paths,
provision `/var/cache/nginx/wordpress` for nginx, run `nginx -t`, then reload only
through the approved deployment mechanism. HTTP redirects to a literal canonical
HTTPS hostname. HSTS applies only to the TLS site and deliberately omits
`includeSubDomains`/`preload` until every subdomain is ready. Headers are repeated
inside locations that declare their own `add_header` because nginx inheritance
otherwise drops them. The baseline CSP limits `frame-ancestors`; extend it only
with a tested application script/style policy.

Uploads/cache/upgrade paths deny nested PHP, phpN, phtml, pht, phar and inc including
PATH_INFO, before asset/PHP locations. Index listings are disabled. XML-RPC is
intentionally unavailable at nginx and WordPress. The native MU policy works
without any unpublished sibling security package. File changes belong to Composer
deployments; WordPress file editing/modification are disabled in production.

Only filenames with 8–64 hex fingerprints get `immutable` for one year. Mutable
assets and JSON manifests use five minutes plus revalidation. Pure sequences of
`utm_*`, `fbclid` and `gclid` parameters use the clean original request path for
page-cache keys. Unknown/semantic/search/auth parameters bypass. Cookie bypass
includes `sympress_consent`, login/password/comment, commerce, membership and
language/currency variants; update the consent cookie matcher if configured to a
custom name. Authorization and unsafe HTTP methods bypass. Upstream Set-Cookie
prevents storage. REST/admin/login endpoints bypass. Consent HTML must still remain
cookie-invariant as defined by the consent package.

## OPcache and object cache

Install `dev-ops/php-production.ini` for the FPM SAPI; validate with `php-fpm -tt`
and inspect the loaded settings before reload. `opcache.validate_timestamps=0`
requires immutable release paths and FPM reloads. Optional `opcache.preload` points
to the release's `dev-ops/preload.php`, with `opcache.preload_user=www-data`; it
compiles a small reviewed dependency core from the authoritative class map without
executing WordPress hooks. Whole-vendor preloading includes optional integrations
whose parent classes may be absent; extend the selected list only with measured,
validated production dependencies.
Enable only after testing with the final package set and budget memory from actual
measurements. The kernel cache stays release-specific to avoid stale containers.

The optional `sympress/framework-bundle` supplies a WordPress object-cache adapter.
After the fixed package release, require its reviewed stable tag through Composer,
then select exactly one drop-in owner. In `dev-ops/runtime.json`, add:

```json
"dropins": {"object-cache.php": "vendor/sympress/framework-bundle/dropin/object-cache.php"},
"dropins-op": "copy"
```

Runtime publishes the drop-in during the credential-free build. Re-run Runtime
before deployment; production's file-modification policy intentionally prevents
request-time installation. Keep any existing foreign drop-in until its owner has
been explicitly removed. The Redis PHP extension is required. Add the following
private values to the deployment `.env`, then regenerate its selected environment
dump (do not print the secret or DSN):

```dotenv
SYMPRESS_CACHE_DRIVER=redis
SYMPRESS_CACHE_DSN=redis://127.0.0.1:6379/0
SYMPRESS_CACHE_PREFIX=example.production
SYMPRESS_CACHE_SECRET=<independent-long-random-secret>
```

Use a protected Redis endpoint and private ACL credentials in the DSN when needed;
deny public Redis access and use verified TLS for network connections. Allocate a
unique prefix for every site/environment. The fixed framework adapter reads native
Runtime dotenv values without exporting them into child process environments and
rejects legacy unsigned cache entries. Optional cache installation is not selected
by this template without operator choice.

Verify persistence in two separate WordPress processes, since a request-local
fallback can still report an external drop-in:

```sh
probe=$(php -r 'echo bin2hex(random_bytes(16));')
php wp-cli.phar eval-file dev-ops/object-cache-check.php write "$probe"
php wp-cli.phar eval-file dev-ops/object-cache-check.php read "$probe"
```

Run the same probe as the deployed PHP identity after deployment and perform an
actual HTTP request through FPM. The check uses one unique 60-second key and never
flushes a shared backend. Backend failure must fail the second process's check;
inspect the private application log for the generic fallback warning.

## Encrypted backups and controlled restore

Install Python 3.12+, `age`, PHP and the database CLI. Copy
`dev-ops/operations.example.json` to `/etc/sympress/operations.json`, mode 0600, owned by the backup/deploy identity.
Set the canonical project/shared uploads path and the off-host age public
recipient. The private decryption identity never belongs on the web host or in
Git. Backups enable WordPress maintenance, export the DB with a consistent
transaction, package uploads plus a checksum manifest, encrypt with age and leave
only a 0600 encrypted archive. Maintenance enabled by the backup is cleared after failure; pre-existing
maintenance remains active. Set the shared `lock_file` to serialize DB/media operations
across releases.
Other systems writing media/DB must be quiesced for a paired snapshot. Retention,
off-host replication and restore drills are operator responsibilities.

```sh
python3 dev-ops/operations.py --config /etc/sympress/operations.json \
  backup /srv/backups/sympress/20261001T030000Z.tar.gz.age
# Take a new pre-restore backup FIRST; the target DB is overwritten.
python3 dev-ops/operations.py --config /etc/sympress/operations.json restore \
  /trusted/backups/snapshot.tar.gz.age --identity /private/backup-key.txt \
  --confirm https://www.example.com --allow-destructive
```

Restore requires exact installed target home URL confirmation; production also
requires `allow_production_restore=true` in private config. It validates age,
rejects archive links/device/path traversal, checks the database digest, imports,
performs serialized-aware search-replace (skipping GUIDs), preserves the old uploads
directory, installs restored media and checks DB/cache. A partial restore stays in
maintenance and reports failure; it never claims transactionally restored media/DB
or silently rolls back. Use only backups from trusted storage. The archive contains
production personal data and integration secrets even while encrypted.

For staging, provision a separate DB, private staging `.env` with
`WORDPRESS_ENV=staging`, `DISABLE_WP_CRON=true`, canonical staging WP_HOME and outbound
network restrictions **before** importing. Staging mail is disabled by the MU policy.
Select/write a reviewed private scrub PHP script that rotates/removes copied users'
passwords/tokens, API/webhook/payment credentials and personal data for that site.
There is no universal safe scrub for arbitrary plugins; sync refuses without it.

```sh
python3 dev-ops/operations.py --config /etc/sympress/staging.json sync-staging \
  /trusted/backups/snapshot.tar.gz.age --identity /private/backup-key.txt \
  --confirm https://staging.example.com --allow-destructive \
  --scrub-script /private/staging-scrub.php
```

Install the supplied backup service/timer only after filling private config and
validating the commands on a disposable restore target. `%` in systemd date formats
is intentionally escaped as `%%`. Run `systemd-analyze verify` before enabling.

## Uptime/error and canary notifications

The read-only `/wp-json/sympress/v1/health` endpoint performs `SELECT 1` and returns
only `status`, with 503 for DB failure; nginx bypasses its page cache. The supplied
monitor checks canonical HTTPS, the status and newly appended fatal/uncaught/error
log lines. Rotation/truncation reset the private byte cursor. Failed health/log
checks return nonzero and send a generic message through local sendmail to the
explicit `alert_recipient`. They never include URLs/log content/provider secrets.
Select a real recipient and configure/test local MTA delivery before enabling the
monitor timer. Use a separate `/etc/sympress/monitor.json` owned by the monitor
identity (0600), from `dev-ops/monitor.example.json`, with only health/log/cursor/recipient settings.
Monitoring does not load the site environment or require access to DB credentials. Install the reviewed monitor script separately so its identity needs no access to
release code or private `.env` snapshots. Give `sympress-monitor` read access to the selected PHP/application
log, and write access only to `/var/lib/sympress-monitor`.

```sh
systemd-analyze verify dev-ops/sympress-monitor.service dev-ops/sympress-monitor.timer
install -d -m 0755 /usr/local/lib/sympress
# Provision the dedicated sympress-monitor Unix identity first.
install -d -o sympress-monitor -g sympress-monitor -m 0700 /var/lib/sympress-monitor
install -m 0755 dev-ops/operations.py /usr/local/lib/sympress/operations.py
# Provision /etc/sympress/monitor.json from the monitor example, mode0600.
python3 /usr/local/lib/sympress/operations.py --config /etc/sympress/monitor.json monitor
# Approved operator installs units/config and enables both reviewed timers.
```

`Canary failure notification` watches completed main-branch DDEV runs from this
repository and creates an assigned GitHub issue on failure. Set repository variable
`CI_ALERT_RECIPIENT` to the selected GitHub login before enabling delivery; missing
recipient fails explicitly. The workflow checks no PR code and receives only
`issues:write`. The canary itself runs the current locked install and scheduled
current-dependency updates; failures are never converted to success. No alert,
deployment, purge or live restore was executed as part of creating this recipe.

## Primary references

- [Deployer common tasks](https://deployer.org/docs/8.x/recipe/common)
- [nginx header inheritance](https://nginx.org/en/docs/http/ngx_http_headers_module.html)
- [PHP OPcache configuration](https://www.php.net/manual/en/opcache.configuration.php)
- [Official WP-CLI v2.12.0 release](https://github.com/wp-cli/wp-cli/releases/tag/v2.12.0)

Both Runtime configs pin WP-CLI v2.12.0 with SHA256
`ce34ddd838f7351d6759068d09793f26755463b4a4610a5a5c0a97b68220d85c`,
verified against the official release PHAR. Retain `sympress-runtime.lock`; a GitHub
metadata outage does not require floating latest or an integrity bypass.
