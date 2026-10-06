# Starter 1.1.7

Published build verification requests the canonical HTTPS home URL with
`rest_route=/sympress/v1/health`. This works with both plain and pretty
permalinks, including a site installed in a subdirectory. TLS validation, zero
redirects, response-size limits and the exact release build ID remain required.

The production nginx template now uses `/run/php/php8.5-fpm.sock`, matching the
Deployer default. Existing nginx installations need their `fastcgi_pass`
updated or both sides configured for the same custom socket.

The disposable-host CI fixture executes the actual published-build PHP helper
through WordPress HTTP and certificate-verified local HTTPS against real nginx,
PHP-FPM, SSH and MariaDB. It exercises plain and pretty permalinks, manual
rollback, failed-health recovery and rejection of a group-writable kernel cache.
Only the external hostname and systemd reload boundary are substituted.

Dependency versions remain locked to Runtime 1.2.4 and Monolog Bundle 1.1.4.
Scheduled dependency-update canaries start from v1.1.7. Security stays private
and is not installed or loaded. Benchmark, load-test and scheduled-canary
acceptance still require their separate evidence.
