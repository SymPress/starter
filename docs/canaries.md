# Locked checks, update canaries and external heartbeat

Pushes and pull requests install the committed Composer lock. Scheduled DDEV runs
resolve the latest stable dependencies allowed by composer.json, retain the
resulting lock as a CI artifact, then execute the normal installation, strict QA
and WordPress/runtime checks. These are separate results: a passing locked push run
does not prove the update path passed.

Use workflow_dispatch with the boolean input `update_dependencies: true` to
exercise the same update path immediately. The default remains false. Invalid
manual event data fails instead of silently selecting the locked path. The shared
workflow remains pinned to its reviewed immutable SHA.

Every multiline command passed to the shared workflow enables its own
`set -euo pipefail`. A failed update, installation, QA or WordPress check stops
that inner shell before later successful commands can hide the error.

## External missing-run detection

Each repository needs its own Healthchecks.io check and its dedicated
`CANARY_HEARTBEAT_URL` Actions secret. Use the UUID HTTPS ping URL on hc-ping.com;
do not commit or print it. The external job receives this secret only after the
DDEV job ends. Dependency installation and build jobs do not receive it.

The heartbeat job runs **only for the schedule event**. A push, PR or manual
update test cannot reset the weekly external check. A successful DDEV job sends
an empty POST success ping; failure, cancellation or skip sends a failure ping
and the heartbeat job remains failed. Missing configuration, malformed results,
transport/HTTP errors and redirects fail. Requests and retries have bounded
timeouts, and neither logs nor customer data are transmitted.

Configure the external check with this repository's DDEV cron expression in UTC
and an initial two-hour grace time. This deliberately reports a run delayed more
than two hours. Review that budget against measured queue/runtime data.

Healthchecks supports these [GitHub Actions completion signals](https://healthchecks.io/docs/github_actions/)
and [cron/grace-time checks](https://healthchecks.io/docs/configuring_checks/).
No own watchdog or additional incident manifest is needed. Keep the existing
GitHub failure notification as the immediate second channel.

## Acceptance before a production pilot

Select and test the actual recipients in the external service. A successful
HTTP ping does not prove a notification reached a person. Use a separate test
check to prove success, a delivered failure alert, and a delivered missing-ping
alert; leave the production check alone. Setting the secret without these tests
does not complete monitoring acceptance.

Record the run URL, selected mode, resolved stable versions/lock and follow-up
checks. A manual `update_dependencies: true` run proves execution of the update
path; the first actual scheduled run and its external heartbeat are recorded
separately. Do not describe a skipped PR heartbeat as a skipped QA gate.

The local operations suite tests mode selection, invalid inputs, secret/result
failures, completion semantics, transport errors and redirects using inert
curl and DDEV doubles. Nested-shell tests execute the actual workflow command
blocks and prove failure propagation. They never send a real heartbeat or notification.
