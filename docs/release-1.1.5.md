# Starter 1.1.5

Deploys keep `var/cache` outside the group-writable directory list and validate its sealed 0750 permissions as the actual PHP user. The deploy user needs the narrow sudo rule documented in `production-operations.md`; SSH-agent forwarding is disabled.

The recipe now verifies production WordPress policy through FPM before switching the release. Database checks and post-switch build-ID health checks remain mandatory. CI deploys the real recipe twice to a disposable SSH/MariaDB/FPM host and confirms that a 0770 cache still fails.

Tracking-only query strings are removed before PHP and share the canonical page cache. Semantic or mixed query strings retain their original bypass behavior. Reload nginx after adopting the configuration change.

The stable lockfile includes Runtime 1.2.4 and Monolog 1.1.4. Update canaries use the fixed `v1.1.5` source baseline. Future scheduled canaries and customer-environment acceptance remain separate evidence.

Security remains private and is not required or loaded. Projects that install it must keep CSP report-only until validating their own enforced policy; `vulnerability:check` is not added as a mandatory gate here.
