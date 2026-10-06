# Incident Runbook

## Severity

- SEV1: app or API unavailable for most users, data-loss risk, or auth outage.
- SEV2: major feature unavailable, sync failures, or elevated crash/error rate.
- SEV3: degraded performance, partial outage, or isolated user-impacting bug.

## Response Steps

1. Acknowledge the incident and assign an owner.
2. Capture timeline, affected environment, release SHA, and user impact.
3. Stabilize first: rollback, restart, disable risky feature, or block failing path.
4. Verify `/healthz`, `/readyz`, login, home, habits, profile, and account deletion/export paths as relevant.
5. Add a regression test or runbook update before closing the incident.

## Privacy/Security Handling

- Do not paste credentials, JWTs, database URLs, raw evidence, or password hashes into tickets or logs.
- If sensitive data may have leaked, preserve evidence, restrict access, and escalate for legal/security review.
- Use sanitized telemetry records only for crash/error investigation.

## Post-Incident Review

- Root cause.
- Detection gap.
- Prevention change.
- Test or monitor added.
- Remaining risk and owner.
