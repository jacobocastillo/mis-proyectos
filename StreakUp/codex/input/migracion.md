I need you to perform a deep backend + database readiness audit for my StreakUP project before we migrate from SQLite to PostgreSQL and deploy to Render.

Project context:
- StreakUP is a habit tracking app.
- Frontend is Next.js / mobile-oriented frontend.
- Backend is Flask (Python).
- Current local database has been SQLite.
- Schema and seed files are under data/db/schema.sql and data/db/seed.sql.
- The backend should be the only layer talking to the database. The frontend/APK must only talk to the backend API.
- We want to prepare everything so the migration path is:
  1) clean backend/database logic
  2) migrate SQLite schema/data to PostgreSQL
  3) deploy PostgreSQL on Render
  4) deploy backend on Render
  5) point frontend/APK to the hosted backend

Your mission:
Do a full recon and validation of the current codebase and determine whether the backend and DB layer are truly ready for migration. I want you to find bugs, structural issues, DB mismatches, broken flows, hidden assumptions, hardcoded SQLite behavior, and anything that could break once we move to PostgreSQL/Render.

What I need you to audit:
1. Database architecture
- Inspect all models, schema files, migrations, seed scripts, config files, and DB utilities.
- Confirm whether the current schema is internally consistent.
- Verify all tables, columns, primary keys, foreign keys, indexes, defaults, timestamps, and constraints.
- Detect missing relationships or columns referenced by the backend but not present in schema.sql.
- Detect fields present in schema but unused in backend, or fields used in backend but missing in schema.
- Check if the schema is suitable for PostgreSQL or if there are SQLite-specific assumptions.
- Flag any SQL syntax or datatype that will break or behave differently in PostgreSQL.
- Review whether data types are appropriate for production use.

2. Seed and bootstrap logic
- Inspect data/db/seed.sql and any bootstrap/init scripts.
- Verify that seed data matches actual backend expectations.
- Confirm whether seeded categories, habits, users, stats, check-ins, or validation-related entities match real app flows.
- Detect duplicate inserts, missing required foreign keys, invalid ordering, or inconsistent IDs.
- Ensure seed can be adapted safely for PostgreSQL.

3. Backend DB integration
- Inspect backend app factory, config, extensions, models, services, repositories, routes, and DB session/connection management.
- Verify that every DB operation is correct and properly connected.
- Confirm the backend is not depending on SQLite-only behaviors.
- Check transaction handling, session lifecycle, commits/rollbacks, error handling, and connection URI usage.
- Detect hardcoded local paths, sqlite:/// URIs, sqlite pragmas, or assumptions tied to a local file DB.
- Confirm the backend can be switched cleanly to DATABASE_URL / Postgres configuration.

4. Functional flows that must work correctly
Audit the full path from API -> service -> DB for at least these flows:
- user registration
- user login/auth
- fetching categories
- fetching habits
- creating a habit
- assigning habits to users if applicable
- check-ins / marking a habit as completed
- stats/summary endpoints
- dashboard or daily progress endpoints
- any XP/streak/progress calculations
- any validation logic (photo, timer, text, etc.) if present
- any route that writes to DB
- any route that depends on seed data
For each flow, verify:
- input validation
- DB reads/writes
- foreign keys used correctly
- response matches intended app behavior
- no broken joins or invalid assumptions

5. API and model correctness
- Find mismatches between request/response payloads and backend expectations.
- Detect endpoints that may return wrong shapes, null crashes, or inconsistent field names.
- Check whether frontend-facing data contracts are stable enough for deployment.
- Identify hidden bugs that could break the app once connected to a remote hosted database.

6. PostgreSQL migration readiness
Identify everything that must change before migrating to PostgreSQL on Render:
- SQL syntax changes
- autoincrement/serial/identity differences
- boolean/date/datetime handling
- text/blob/json differences
- unique/index/constraint issues
- connection config changes
- environment variable changes
- migration tooling needed
- package dependencies needed (for example psycopg/psycopg2, SQLAlchemy/Postgres driver, gunicorn if relevant)
- any code paths that need refactoring before deployment

7. Deployment readiness for Render
Review backend deployment readiness:
- config/env handling
- secret validation
- production-safe defaults
- CORS
- host/port binding
- gunicorn or production server requirements
- health endpoint availability
- DB connection from hosted environment
- startup/init behavior
- whether schema creation is safe in production
- whether seeds should or should not run on deploy

Important working style:
- First inspect before changing anything.
- Do not make blind edits.
- Be surgical and evidence-based.
- Assume there may be a dirty worktree; do not overwrite unrelated changes.
- Prefer minimal, production-safe fixes.
- If you find a bug, explain exactly why it is a bug and where it appears.
- If something is acceptable for SQLite but dangerous for PostgreSQL/Render, call it out clearly.

Deliverables I want from you:
1. A concise architecture summary of current backend/DB structure.
2. A bug list with severity:
   - critical
   - high
   - medium
   - low
3. A “migration blockers” section with only the issues that must be fixed before PostgreSQL/Render.
4. A “safe to migrate / not safe to migrate yet” verdict.
5. A concrete remediation plan in the exact order I should implement.
6. If possible, apply the fixes directly for the critical blockers.
7. After fixes, provide a validation checklist I can run locally before migration.
8. If tests exist, run them. If tests are missing in critical DB paths, add focused tests for the risky areas only.
9. Show diffs for all changes and explain why each change was necessary.

Extra priority:
Please pay special attention to:
- data/db/schema.sql
- data/db/seed.sql
- backend app config and DB init
- auth flow
- habits/categories/check-ins/stats flows
- anything that still smells like local-only SQLite logic
- anything that would fail when using a hosted Postgres database on Render

Goal:
I want the codebase clean, consistent, and migration-ready before I create the PostgreSQL instance on Render.
Do a true readiness audit, fix what ecessary, and leave me with a clear go/no-go decision.