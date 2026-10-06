# Starter 1.1.5

The deployment recipe keeps `var/cache` out of group-writable directories and
seals the release-local cache with mode 0750. Runtime 1.2.3 can check it before
publication.

The PHP-user doctor report accepts only `production.readable.<number>` unknowns,
which represent ACL readability that the deploy identity cannot verify. Failed
checks, other unknowns, malformed checks and empty reports stop deployment.
SSH agent forwarding to production and staging hosts is disabled.

Locked dependencies are unchanged. Scheduled dependency-update canaries start
from `v1.1.5`. Security remains private and is absent from the manifest, lockfile
and MU-plugin loader.

This release does not include Runtime's pending OPcache fix, the dependency
download-cache transfer for private packages, or a complete disposable-host
deployment CI job. These remain separate follow-ups.
