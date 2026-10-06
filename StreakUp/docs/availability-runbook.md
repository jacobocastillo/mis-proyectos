# Availability Runbook

## SLO

StreakUp targets at least 95% monthly availability during normal use.

## Health Checks

- `GET /healthz`: process liveness. Expected `200` with `{ "status": "ok" }`.
- `GET /readyz`: readiness. Expected `200` only when database connectivity and required catalog data are ready.

## Monitor Setup

- External monitor: check `/healthz` every minute.
- Deployment smoke: check `/readyz` after migrations and catalog bootstrap.
- Alert when `/healthz` fails twice consecutively or `/readyz` fails after a deployment.

## Triage

1. Check hosting status and recent deploys.
2. Check `/healthz`; if it fails, restart/redeploy the backend.
3. Check `/readyz`; if only readiness fails, inspect database connectivity and catalog seed state.
4. Check auth login, habit list, profile, and stats as authenticated smoke flows.
5. Record start/end time, suspected cause, user impact, and corrective action.
