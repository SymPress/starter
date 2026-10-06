# Starter 1.1.6

The manifest requires and the lockfile includes Runtime 1.2.4 and Monolog Bundle
1.1.4. Warm environment-cache and dump reads retain OPcache entries; changed
mutable writes refresh them. Generated Runtime MU files include their installed
version, so the optional Security inventory can identify them.

The deployed recipe keeps the production-doctor JSON checks introduced in 1.1.5
and checks WordPress policy through the private FPM socket. A new CI job runs
two complete deployments against an isolated SSH/MariaDB/FPM host, including
private FPM health, cache permissions, a negative group-writable cache check and
recovery of the previous release after a failing published health check.
Systemd and public HTTPS transport are substituted only inside that fixture.

The nginx examples remove tracking-only query strings from PHP's request URI
and query string as well as from the cache key. Semantic and mixed queries
remain uncached. Regenerate or update existing nginx configurations and reload
nginx before relying on this behavior.

Scheduled dependency-update canaries start from v1.1.6. Security remains private
and is not required or loaded. This release does not close the outstanding
benchmark, load-test or scheduled-canary acceptance gates.
