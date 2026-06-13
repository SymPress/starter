# Security Policy

## Supported Versions

Security updates are provided for the latest tagged `1.x` release line.

Development branches are supported on a best-effort basis until the first stable tag exists.

## Reporting a Vulnerability

Report suspected vulnerabilities privately to the SymPress maintainers.

Do not open public GitHub issues for security-sensitive reports.

Include:

- affected package and version or commit
- reproduction steps
- expected impact
- any relevant logs or proof of concept

## Dependency Security

The starter runs Composer audit in CI and includes Dependabot/Renovate configuration for dependency update pull requests.

Projects created from this starter should keep their lock file committed and review dependency update pull requests regularly.
