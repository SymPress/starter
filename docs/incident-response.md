# Incident procedure

1. Record the affected site, first observed time, build ID, source commit and
   symptoms in a private incident record. Assign one operator to coordinate work.
2. Preserve the release digest/SBOM, nginx/FPM and security audit logs, deployment
   records and relevant database evidence before editing or deleting anything.
   Restrict access; logs and artifacts may contain personal data.
3. Contain the affected identity or endpoint using the hosting controls. Revoke
   exposed tokens and prevent new writes where feasible. Keep an unaffected
   diagnostic path available to the operator.
4. Compare the running build ID with the independently verified artifact. Inspect
   executable files and writable uploads/cache paths, unusual roles/options and
   audit events. Use a trusted external integrity manifest when one exists.
   Missing events are not evidence that no compromise occurred.
5. Establish the entry point and scope, fix the code/configuration and rotate
   affected application, deployment and service credentials. Run package QA,
   audits and the production doctor gates on the candidate artifact.
6. The operator chooses the site recovery procedure. Validate the public health
   build ID, normal authenticated editor flow and suspicious endpoints afterward.
   Record unresolved evidence and monitor for recurrence.
7. Document cause, impact, corrective actions and owners. Assess required customer
   or authority notifications with the responsible business contact. Never place
   credentials, personal records or exploitable details in a public issue.

This repository does not provision alert services or prescribe customer rollout,
backup or recovery processes. Store site-specific contacts and hosting actions in
a private operations record.
