# Release Checklist

## Before Deploy

- Run backend tests: `cd backend && pytest`.
- Run frontend lint and unit tests: `cd frontend && npm run lint && npm test`.
- Run Playwright checks: `cd frontend && npx playwright test`.
- Build web and mobile bundles:
  - `cd frontend && npm run build`
  - `cd frontend && NEXT_PUBLIC_OFFLINE_MODE=false NEXT_PUBLIC_API_URL=https://api.example.com npm run build:mobile`
- Build Android debug APK: `cd android && GRADLE_USER_HOME=/tmp/streakup-gradle ./gradlew assembleDebug`.

## Data Safety

- Review new Alembic migrations and confirm forward migration path.
- Verify local storage schema changes and migration behavior.
- Confirm backup/restore plan for the target environment.
- Confirm sync compatibility when pending local operations exist.

## Smoke Tests

- `GET /healthz`.
- `GET /readyz`.
- Login.
- Home screen load.
- Habits screen load.
- Profile screen load.
- Account export.
- Account deletion in a test account.
- Android emulator launch/navigation smoke.

## Rollback

- Keep the previous deploy artifact or branch available.
- Record database migration rollback limits before deploy.
- If rollback cannot revert data shape safely, prefer forward fix with feature disabled.
