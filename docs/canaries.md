# Locked checks and update canaries

Pushes and pull requests test their own source commit and install its committed
Composer lock. Scheduled DDEV runs and explicit manual update runs check out the
fixed source baseline `v1.1.7`, resolve the latest stable dependencies allowed by
that tag's composer.json, retain the
resulting lock as a CI artifact, then execute the normal installation, strict QA
and WordPress/runtime checks. These are separate results: a passing locked push run
does not prove the update path passed.

Use workflow_dispatch with the boolean input `update_dependencies: true` to
exercise the same update path immediately. The default remains false. Invalid
manual event data fails instead of silently selecting the locked path. The shared
workflow remains pinned to its reviewed immutable SHA.

The source tag remains fixed when dependencies change. A normal manual run with
`update_dependencies: false` tests the selected workflow ref and its lock.

Publication of `v1.1.7` does not establish a successful scheduled run of this
baseline. Record the next scheduled execution separately; local QA and
passing push/PR checks do not establish its result.

The [manual update run for `v1.1.2`](https://github.com/SymPress/starter/actions/runs/37140442401)
passed on 2026-10-03. It certifies that earlier source baseline, not `v1.1.7`.

Every multiline command passed to the shared workflow enables its own
`set -euo pipefail`. A failed update, installation, QA or WordPress check stops
that inner shell before later successful commands can hide the error.

## Verification

Record the run URL, selected mode, resolved stable versions/lock and follow-up
checks. A manual `update_dependencies: true` run exercises the scheduled update
path. Results and failure notifications are provided by GitHub Actions.

These repositories require no external monitoring service or heartbeat secret.
Website uptime and application-log monitoring are configured by the operator
for each deployed installation, separately from repository CI.

The local operations suite tests mode selection and invalid inputs. Nested-shell
tests execute the actual workflow command blocks and prove failure propagation
with inert DDEV doubles.
