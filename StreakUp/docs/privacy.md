# Privacy Baseline

This document is the technical privacy baseline for StreakUp. It supports RNF-12 but is not legal certification.

## Data Inventory

- Account data: username, email, role, creation and update timestamps.
- Habit data: catalog assignments, custom names/descriptions, schedules, targets, validation type, active state.
- Progress data: check-ins, streak inputs, XP logs, achievements, pomodoro sessions.
- Social data: shared streak groups, memberships, invite codes, progress-sharing consent.
- Validation data: validation status, timestamps, validation type, and whether evidence was attached.
- Local app data: cached habits, check-ins, pomodoro sessions, pending sync operations, and non-sensitive user profile cache.

## User Rights Controls

- Access/export: authenticated users can call `GET /api/users/me/export`.
- Deletion: authenticated users can call `DELETE /api/users/me`; the app also clears local offline data after success.
- Correction: authenticated users can update editable profile fields through `PUT /api/users/me`.

## Sensitive Data Rules

- Password hashes are never returned in API payloads or export payloads.
- Access and refresh tokens are stored in the credential store, not `localStorage`.
- Client error telemetry accepts only allowlisted fields and redacts token/password-like values before logging.
- Raw validation evidence is not included in the portable export; the export exposes evidence presence metadata.

## Review Checklist

- Verify export excludes `password_hash`, plaintext passwords, JWTs, refresh tokens, and raw validation evidence.
- Verify account deletion removes server-side user-owned data and local offline caches.
- Verify logs do not contain secrets, authorization headers, passwords, or raw credentials.
- Review this baseline with legal/product owners before production launch in a target jurisdiction.
