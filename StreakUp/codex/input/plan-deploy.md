I need you to execute the next remediation phase for StreakUP based on the validated deployment path findings.

Goal:
Make the project move in the correct order toward:
1. hosted backend
2. frontend retargeted to hosted backend
3. functional APK using the hosted backend

This phase must start with backend hosting blockers first.
Do NOT jump to APK work before backend hosting readiness is fully fixed.

CURRENT KNOWN BLOCKERS

Backend hosting blockers:
1. Missing `pomodoro_sessions` table in migration/schema
2. Fresh deploy does not reconstruct required catalog data
3. No real production startup path
4. OpenAI validation path can deploy broken
5. Missing minimum health/readiness operational endpoints

Frontend retargeting blockers:
1. `next.config.ts` has localhost rewrite hardcoded
2. Online habit editing is not actually implemented
3. Frontend depends on backend completeness for catalog, pomodoro, validation

APK blockers:
1. Capacitor `webDir=out` does not match actual Next build pipeline
2. Mobile build requires explicit hosted `NEXT_PUBLIC_API_URL`
3. Backend must be exposed over HTTPS
4. Camera validation path is MVP-level and may have compatibility risk

EXECUTION ORDER

PHASE 1 — BACKEND HOSTING FIXES
Task 1. Add pomodoro schema parity
- update migration baseline
- update schema.sql
- verify fresh migrated DB includes `pomodoro_sessions`
- verify pomodoro routes no longer fail on fresh deploy

Task 2. Add deploy-safe catalog bootstrap
- implement idempotent seed/bootstrap for categories and catalog habits
- make it suitable for hosted environments, not just local sqlite CLI flow
- document how it runs in deployment
- verify `/api/habits/catalog` returns real data after fresh deploy

Task 3. Add real production startup path
- add WSGI production serving path (Gunicorn or equivalent)
- use env-driven port instead of dev-only assumptions
- define canonical startup command
- add any missing dependency/config required

Task 4. Harden OpenAI validation operationally
- make validation fail safely if OpenAI config is missing
- avoid leaking raw provider exception strings
- decide whether validation is optional or must be startup-validated
- keep photo validation flow working when properly configured

Task 5. Add minimum operational endpoints
- add `/healthz`
- add readiness endpoint if appropriate
- keep implementation simple and honest

Validation after backend phase:
- run backend tests
- create fresh DB from migration path
- run bootstrap/seed
- verify:
  - auth works
  - catalog has data
  - pomodoro works
  - validation path behaves safely
  - health endpoint works

PHASE 2 — FRONTEND RETARGETING
Only after backend hosting blockers are fixed.

Task 6. Remove or parameterize localhost rewrite
- inspect `frontend/next.config.ts`
- replace hardcoded localhost rewrite with safe env-based logic or remove it
- ensure hosted API can be consumed cleanly

Task 7. Validate frontend against hosted-backend assumptions
- verify API base URL resolution path
- confirm auth, habits, stats, pomodoro, validation all use shared runtime config
- identify any remaining local-only assumptions

Task 8. Handle online habit editing honestly
- do not fake support
- either keep it clearly disabled or fully hide entry points in connected mode

Validation after frontend phase:
- verify frontend can run against a non-local backend URL
- verify main user flows work against hosted-style API config

PHASE 3 — APK / MOBILE PIPELINE
Only after phases 1 and 2 are complete.

Task 9. Align Next build output with Capacitor
- inspect `capacitor.config.json`, `package.json`, `next.config.ts`
- make the mobile build pipeline produce the directory Capacitor actually expects
- document the correct build sequence

Task 10. Prepare APK to use hosted backend
- ensure mobile build requires hosted `NEXT_PUBLIC_API_URL`
- confirm no localhost assumptions remain
- confirm HTTPS requirement is clear

Validation after mobile phase:
- build frontend for mobile
- run capacitor sync
- verify build artifacts are consistent
- if possible, prepare exact steps for APK generation

REQUIRED OUTPUT FORMAT

For each task:
1. What changed
2. Root cause
3. Fix implemented
4. Validation performed
5. Remaining risk

At the end provide:
- backend hosting readiness status
- frontend retargeting readiness status
- APK pipeline readiness status
- exact next command sequence to move toward deployment

IMPORTANT RULES
- Work in order: backend first, frontend second, APK third
- Prefer minimal safe changes over broad refactors
- Do not introduce fake success states
- Do not mark anything fixed without validation
- Preserve working flows