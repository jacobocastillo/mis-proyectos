We already created a new PostgreSQL database on Render for StreakUP and added the Render Internal Database URL to backend/.env.local as DATABASE_URL.

I want you to perform only the PostgreSQL staging setup for the backend. Do not redo the previous audit. Do not modify unrelated frontend or Android files.

Context:
- Project: StreakUP
- Backend: Flask
- Current goal: connect the backend to the new Render PostgreSQL database, create the schema there, seed only the catalog/base data, and verify that the backend is ready for staging.
- Use Alembic migrations as the source of truth.
- The new Render PostgreSQL database is intentionally empty right now.
- backend/.env.local already contains DATABASE_URL and the required secrets.

Your tasks:
1. Inspect the backend configuration and confirm that backend/.env.local is being read correctly in local development.
2. Verify that DATABASE_URL is resolved correctly for PostgreSQL and that any postgres:// vs postgresql:// normalization works.
3. Run the backend migration command against the Render PostgreSQL database:
   flask --app run.py db upgrade
4. If migration fails, fix only the necessary backend/config/migration issues to make PostgreSQL migration succeed.
5. After migrations succeed, run only the catalog seed:
   flask --app run.py seed-catalog
6. Verify that the expected base tables and catalog data now exist in PostgreSQL.
7. Run the backend locally against the Render PostgreSQL database and verify at minimum:
   - /healthz
   - /readyz
8. If possible, also smoke test:
   - auth register/login
   - habits catalog endpoint
   - habit assignment endpoint
   - check-in endpoint
   - stats summary endpoint
9. Run relevant backend tests if they help validate the Postgres setup, but do not do unrelated refactors.
10. Show me exactly:
   - what commands you ran
   - what files you changed
   - why each change was needed
   - the final result and whether staging is ready

Important constraints:
- Do not insert fake user progress data.
- Do not migrate old SQLite user/check-in history yet.
- Do not touch unrelated frontend/mobile files.
- Prefer minimal, surgical fixes only.
- If a command is destructive or risky, stop and explain first.
- If everything succeeds, give me a concise next-step checklist for deploying the backend service on Render.

Definition of done:
- Render PostgreSQL schema created successfully via Alembic
- catalog seed applied successfully
- backend can start locally using the Render PostgreSQL database
- health/readiness checks pass
- clear go/no-go verdict for moving to backend deploy on Render