# Starter 1.1.4

The stable lockfile includes Runtime 1.2.3 and Kernel 1.1.5. Outbound WordPress
HTTP blocking is an explicit environment/constant choice. An existing generated
configuration from Runtime 1.2.0–1.2.2 must have its managed section regenerated;
review preserved customized sections before deployment. Existing explicit host
allowlists remain authoritative.

Kernel container/discovery metadata uses private atomic JSON. Unchanged mutable
reads keep OPcache entries, and a CLI publication is visible to existing FPM
workers. Runtime diagnostics and cache maintenance share that contract. Existing
legacy PHP metadata is ignored and rebuilt without execution.

The scheduled and manually requested dependency-update canary starts from the
tagged `v1.1.4` source set. The private Security package remains absent from the
manifest, lockfile and MU-plugin loader.
