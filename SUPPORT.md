# Support

SymPress Starter is a Composer project template for DDEV-backed WordPress
projects. Good support requests include the starter version or commit, setup
commands, the failing run or local output, and the expected outcome.

## Before Opening An Issue

1. Check [Installation](docs/installation.md) and [Development tools](docs/development.md).
2. Run the local diagnostics:

   ```bash
   bin/console doctor
   bin/console check
   ```

3. Confirm the issue reproduces from a clean checkout.
4. Search existing issues and pull requests.

## Where To Ask

- Reproducible setup or runtime failures: open a bug report.
- Missing starter capabilities or adoption problems: open a feature request.
- Documentation gaps: open a documentation issue.
- Security issues: use the private vulnerability reporting flow described in
  [SECURITY.md](SECURITY.md).

## What Maintainers Need

- Link to the failed GitHub Actions run, if relevant.
- The commands you ran, with secrets removed.
- Relevant DDEV, PHP, Composer, WordPress, and SymPress versions.
- Logs from the failing step or command.
- Whether the issue reproduces with the latest starter release tag.
