# Environment Configuration

The starter reads environment values from `.env`. Create it from `.env.example`:

```sh
cp .env.example .env
```

`bin/console setup my-project` updates `WP_HOME` and `WP_SITEURL` for the local `ddev.site` URL.

`.env.example` intentionally contains only the starter defaults needed for day-one local development. The additional supported WordPress and SymPress environment values are documented below so project teams can opt in without losing context.

## Runtime

`WORDPRESS_ENV` controls WordPress environment behavior.

Recommended values:

- `development` for local DDEV projects
- `staging` for staging systems
- `production` for production

Never use `development` in production.

## Database

DDEV defaults:

```dotenv
DB_HOST=db
DB_NAME=db
DB_USER=db
DB_PASSWORD=db
```

Production values should come from the deployment platform or secret manager.

## URLs

```dotenv
WP_HOME=https://my-project.ddev.site
WP_SITEURL=${WP_HOME}/wp
```

`WP_HOME` is the public site URL. `WP_SITEURL` points to the Composer-managed WordPress core in `/wp`.

## Installer

WPStarter uses these values only when it installs WordPress on a fresh database:

```dotenv
WP_ADMIN_USERNAME=admin
WP_ADMIN_PASSWORD=
```

`bin/console setup` generates a local password when this value is empty. Use explicit strong values for shared environments.

## SymPress Starter Flags

```dotenv
SYMPRESS_ENABLE_WORDPRESS_HARDENING=false
SYMPRESS_ENABLE_VARDUMPER=false
```

`SYMPRESS_ENABLE_WORDPRESS_HARDENING` enables the opinionated cleanup and hardening hooks in `packages/base-mu-plugins/disable.php`.

`SYMPRESS_ENABLE_VARDUMPER` enables the Symfony VarDumper integration in development only. It is ignored outside `WORDPRESS_ENV=development`.

## Multisite

Supported values:

```dotenv
WP_ALLOW_MULTISITE=false
MULTISITE=false
SUBDOMAIN_INSTALL=false
SITE_ID_CURRENT_SITE=1
BLOG_ID_CURRENT_SITE=1
DOMAIN_CURRENT_SITE=example.test
PATH_CURRENT_SITE=/
ALLOW_SUBDIRECTORY_INSTALL=false
MU_BASE=/
NOBLOGREDIRECT=${WP_SITEURL}
UPLOADBLOGSDIR=blogs.dir
UPLOADS=files
BLOGUPLOADDIR=files
WPMU_ACCEL_REDIRECT=false
WPMU_SENDFILE=false
```

Enable multisite only when the project explicitly needs it.

## Cache

Supported values:

```dotenv
WP_CACHE=true
WP_STASH_DRIVER=\Stash\Driver\Apc
WP_STASH_DRIVER_ARGS=a:1:{s:3:"ttl";i:3600;}
```

For production, document the selected object-cache backend and purge strategy in the project.

## Debug

Supported values:

```dotenv
WP_DEBUG=true
WP_DEBUG_LOG=true
WP_DEBUG_DISPLAY=false
SAVEQUERIES=false
SCRIPT_DEBUG=false
ERRORLOGFILE=/log/error.log
DIEONDBERROR=false
SYMPRESS_DISPLAY_DEPRECATED=false
```

Recommended production values:

```dotenv
WP_DEBUG=false
WP_DEBUG_DISPLAY=false
WP_DEBUG_LOG=true
SYMPRESS_DISPLAY_DEPRECATED=false
```

## Paths And URLs

Supported values:

```dotenv
WP_CONTENT_DIR=./../wp-content
WP_CONTENT_URL=${WP_SITEURL}/wp-content
WP_PLUGIN_DIR=${WP_CONTENT_DIR}/plugins
WP_PLUGIN_URL=${WP_CONTENT_URL}/plugins
WPMU_PLUGIN_DIR=${WP_CONTENT_DIR}/mu-plugins
WPMU_PLUGIN_URL=${WP_CONTENT_URL}/mu-plugins
WP_TEMP_DIR=tmp
```

Most projects should not need to override these.

## Updates

Supported values:

```dotenv
AUTOMATIC_UPDATER_DISABLED=false
WP_AUTO_UPDATE_CORE=false
CORE_UPGRADE_SKIP_NEW_BUNDLED=true
```

Composer should own WordPress core and dependency updates for this starter.

## Post And Media

Supported values:

```dotenv
AUTOSAVE_INTERVAL=60
EMPTY_TRASH_DAYS=30
WP_POST_REVISIONS=true
MEDIA_TRASH=false
IMAGE_EDIT_OVERWRITE=true
```

## Performance

Supported values:

```dotenv
COMPRESS_CSS=false
COMPRESS_SCRIPTS=false
CONCATENATE_SCRIPTS=false
ENFORCE_GZIP=false
WP_MEMORY_LIMIT=64M
WP_MAX_MEMORY_LIMIT=256M
```

Use platform-level compression and caching in production unless the project has a specific reason to use WordPress-level toggles.

## Cookies

Supported values:

```dotenv
COOKIEHASH=
PASS_COOKIE=
LOGGED_IN_COOKIE=
AUTH_COOKIE=
SECURE_AUTH_COOKIE=
USER_COOKIE=
TEST_COOKIE=
COOKIE_DOMAIN=
COOKIEPATH=/
SITECOOKIEPATH=/
ADMIN_COOKIE_PATH=/
PLUGINS_COOKIE_PATH=
```

Use `bin/console diagnose-login` when local login redirects or cookies do not match the expected URL.

## Security

Supported values:

```dotenv
DISALLOW_FILE_MODS=false
DISALLOW_FILE_EDIT=false
DISALLOW_UNFILTERED_HTML=true
ALLOW_UNFILTERED_UPLOADS=false
FORCE_SSL_ADMIN=false
WP_HTTP_BLOCK_EXTERNAL=false
WP_ACCESSIBLE_HOSTS=
```

Recommended production values:

```dotenv
DISALLOW_FILE_EDIT=true
DISALLOW_FILE_MODS=true
FORCE_SSL_ADMIN=true
```

## Filesystem

Supported values:

```dotenv
FS_CHMOD_DIR=0755
FS_CHMOD_FILE=0644
FS_METHOD=
FS_TIMEOUT=30
FS_CONNECT_TIMEOUT=30
FTP_USER=
FTP_PASS=
FTP_HOST=
FTP_SSL=
FTP_SSH=
FTP_BASE=
FTP_CONTENT_DIR=
FTP_PLUGIN_DIR=
FTP_PUBKEY=
FTP_PRIKEY=
```

Composer deployments normally do not need FTP values.

## Cron

Supported values:

```dotenv
ALTERNATE_WP_CRON=false
DISABLE_WP_CRON=false
WP_CRON_LOCK_TIMEOUT=60
```

For production, prefer a platform scheduler:

```sh
wp cron event run --due-now
```

## Language

Supported value:

```dotenv
WP_LANG_DIR=${WP_CONTENT_DIR}/languages
```

## Proxy

Supported values:

```dotenv
WP_PROXY_HOST=
WP_PROXY_PORT=
WP_PROXY_USERNAME=
WP_PROXY_PASSWORD=
WP_PROXY_BYPASS_HOSTS=
```

## Miscellaneous

Supported values:

```dotenv
WP_MAIL_INTERVAL=300
WP_DEFAULT_THEME=twentytwentyfive
```
