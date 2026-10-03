# Repository threat model

Scope: the shipped Composer-managed application, reusable build/deploy workflow,
nginx/FPM templates and public Symfony packages. Hosting controls and customer
data migrations require separate acceptance. Private Security is not installed.

| Boundary | Plausible failure | Repository control | Remaining dependency |
| --- | --- | --- | --- |
| Source to release | Compromised dependency or build script | Locked installs without scripts/plugins during fetch; isolated credential-free build; audits, SBOM, archive digest and optional attestations | Maintainer account, reviewed workflow pin and plugin admission |
| Internet to PHP | Executable upload, exposed secret, bad proxy input | nginx upload/dotfile rules, canonical production URL, trusted proxy checks and Runtime doctor | Actual enabled virtual host and TLS; external scan not performed |
| PHP to files | Compromised admin writes code or reads another tenant | File mods disabled, separate deploy/FPM identities, read-only container example, private signed caches | Operator permissions, tenant isolation and secret mounts |
| PHP to services | SSRF, database destruction or shared cache injection | WordPress outbound allowlist, web/migration grant example, signed per-site cache | Network egress policy, per-site TLS Redis ACL and DB account provisioning |
| Admin to logs | Credentials or options leak into diagnostic files | Redaction preserves safe traces; private profiler files; dedicated sanitized security audit channel | Log retention, read access and off-host collection |

An application compromise can still read application credentials and modify its
allowed database rows. Local audit logs cannot prove absence of manipulation.
Author archives and existing nicenames remain public unless an operator changes
them; the full private enumeration guard has deliberately not been integrated.
Review this model after adding plugins, network access or new admin interfaces.
