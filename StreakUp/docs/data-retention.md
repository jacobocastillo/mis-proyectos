# Data Retention

## Current Policy

- Active account data is retained while the account exists.
- Deletion is user initiated from the profile screen and is permanent after the backend confirms success.
- Local offline caches are cleared by the app after successful account deletion.
- Operational logs should retain only sanitized metadata needed for reliability and incident analysis.

## Deletion Scope

The account deletion flow removes:

- User profile row.
- Habit assignments, check-ins, validation logs, pomodoro sessions, achievements, XP logs.
- Social memberships and user-owned shared streak groups.
- Sync operation receipts.
- Local cached habits, check-ins, pomodoro sessions, pending operations, and local schema version.

## Retention Follow-ups

- Define production log retention in the hosting provider.
- Define backup retention and restore windows before production launch.
- Define whether raw validation evidence is stored long term or moved to a short-lived evidence store.
