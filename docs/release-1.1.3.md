# Starter 1.1.3

The production PHP profile retains OPcache and explicitly disables JIT with
`opcache.jit=disable` and `opcache.jit_buffer_size=0`. This sets the supported
WordPress profile after a native PHP 8.5.9 WordPress/guard fixture failed with
SIGSEGV under JIT `1235`/256 MiB and passed with JIT disabled. It does not establish
a failure in every PHP 8.5 release or application.

A real FPM regression loads a prior JIT-enabling configuration, then the exact
production profile, and verifies that OPcache works while JIT remains disabled,
including after an attempted request-time activation. Existing deployments receive
the defaults when their adapted production PHP profile is installed and FPM is
reloaded. Composer dependencies remain unchanged; no private integration is added.

The hosted operations job installs PHP 8.5/FPM, FastCGI, nginx and the locked public
fixture dependencies without running Composer plugins or scripts. Native operation
checks must execute without skips; their assertions remain unchanged.

Scheduled and explicit manual update canaries use the fixed source tag `v1.1.3`.
The first executions of that baseline must be recorded after publication; earlier
`v1.1.2` results do not certify the new source.
