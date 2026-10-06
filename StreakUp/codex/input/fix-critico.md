I need you to execute a FIX PLAN for StreakUP based on the completed functional recon. This is no longer a diagnostic phase. This is a remediation phase.

Your mission is to fix the highest-priority deployment blockers first, validate each fix, and leave the project in a materially safer and more deployable state.

IMPORTANT:
- Do NOT start with broad refactors.
- Do NOT add unnecessary abstractions.
- Do NOT try to “improve everything”.
- Focus first on blockers that directly prevent safe deployment.
- After each fix, validate it with the appropriate test or reproduction step.
- Preserve existing working flows wherever possible.
- Be explicit about files changed, why, and how the fix was validated.

---

## PROJECT CONTEXT

The recon found that the core MVP flows mostly work, but StreakUP is NOT deployment-ready due to several critical blockers:

### Critical / P0 blockers
1. `data/db/seed.sql` is broken and fails against the `dificultad` CHECK constraint.
2. SQLite foreign keys are not enforced at runtime (`PRAGMA foreign_keys = 0`).
3. Sensitive information is printed in logs during auth/bootstrap, including DB URI and password hash related info.
4. Runtime JWT/secret configuration is too weak for production.
5. Frontend stats can hide real backend/data problems by falling back to `DEMO_DATA`.

### Important / P1 issues
6. “Create habit” is really “assign catalog habit”; this behavior must be clarified and kept consistent across UI/backend wording.
7. Online habit editing is exposed in UI/backend but not implemented (`501`).
8. XP/check-in persistence model is inconsistent (`xp_logs` vs `registro_habitos.xp_ganado`).
9. Frontend auth guard trusts localStorage too much and does not validate session/token properly.

### Important / P2 issues
10. No real migrations are versioned even though migration tooling exists.
11. Dashboard/profile hide API failures with silent default states.
12. Profile achievements use wrong stats field.
13. Validation modes are incomplete beyond photo.

---

## EXECUTION STRATEGY

Work in this order:

# PHASE 1 — FIX ONLY P0 DEPLOYMENT BLOCKERS

## Task 1. Fix reproducible DB initialization
Goal:
Make `data/db/schema.sql` + `data/db/seed.sql` produce a valid fresh SQLite database without partial failure.

Required actions:
- Inspect schema and seed mismatch around `dificultad`
- Fix `seed.sql` so all inserted values respect the schema constraints
- Ensure seed execution is consistent and leaves expected base records inserted
- If needed, normalize inserted values to match backend expectations

Validation:
- Recreate a fresh SQLite DB from `schema.sql` + corrected `seed.sql`
- Confirm tables load successfully
- Confirm `habitos` and related base data are actually inserted
- Report exact inserted counts after fix

Deliverable:
- Updated SQL files
- Short note explaining root cause and why fix is safe

---

## Task 2. Enforce SQLite foreign keys at runtime
Goal:
Ensure SQLite actually enforces foreign key constraints in the real app runtime.

Required actions:
- Find the SQLAlchemy/Flask DB initialization path
- Add the proper connection hook/event so every SQLite connection runs `PRAGMA foreign_keys = ON`
- Make sure this applies both in app runtime and isolated test contexts where appropriate

Validation:
- Verify `PRAGMA foreign_keys` returns `1` during runtime
- Add or adjust a test proving FK enforcement actually works
- Confirm existing critical flows still pass

Deliverable:
- Code change in DB/app initialization
- Validation proof that FK enforcement is active

---

## Task 3. Remove sensitive runtime logging
Goal:
Eliminate sensitive auth/bootstrap logging without harming observability.

Required actions:
- Find all prints/logs exposing:
  - DB URI
  - password hash
  - raw auth internals
  - excessive user object dumps
- Replace unsafe logs with minimal safe logging where useful
- Keep logs operationally useful but non-sensitive

Validation:
- Run auth-related flows and confirm sensitive values are no longer printed
- Confirm no functional regressions in register/login

Deliverable:
- Cleaned logging in affected files
- Summary of removed/replaced log statements

---

## Task 4. Harden runtime secrets handling
Goal:
Make runtime configuration safer and fail more explicitly on insecure secret usage.

Required actions:
- Inspect how `JWT_SECRET_KEY` and `SECRET_KEY` are loaded
- Enforce or strongly validate minimum acceptable secret length for non-dev environments
- Avoid silently accepting insecure production-like secrets
- Preserve developer ergonomics for local dev where reasonable, but be explicit

Validation:
- Confirm app still runs in development with sane config
- Confirm insecure config is either warned clearly or blocked in non-dev mode
- Document expected env var requirements

Deliverable:
- Updated config/bootstrap logic
- Clear note on required secret settings

---

## Task 5. Remove misleading demo fallback from production-critical stats path
Goal:
Stop the frontend from masking real data/backend failures with fake demo stats in production-critical flow.

Required actions:
- Inspect `frontend/app/(dashboard)/stats/page.tsx`
- Remove or gate `DEMO_DATA` behavior so users do not see fake healthy-looking data when backend fails or real data is empty
- Replace with honest empty/error states
- If demo mode must remain for dev, isolate it explicitly behind a safe dev-only condition

Validation:
- Confirm stats page shows real empty state when user has no real data
- Confirm stats page shows real error state when backend fails
- Confirm page still renders correctly with real stats

Deliverable:
- Updated stats page behavior
- Clear explanation of new empty/error handling

---

# PHASE 2 — FIX FUNCTIONAL CONSISTENCY ISSUES

Only after Phase 1 is complete and validated.

## Task 6. Clarify “create habit” vs “assign habit”
Goal:
Align naming and expectations across backend/frontend so product language matches actual behavior.

Required actions:
- Confirm current backend behavior
- Update frontend wording/UI labels if needed
- Update service naming/comments if needed
- Do NOT implement custom habit creation unless clearly necessary for this phase

Validation:
- Confirm the flow is understandable and consistent in UI + API usage

---

## Task 7. Resolve online habit editing inconsistency
Goal:
Remove dead/false affordances.

Required actions:
Choose ONE minimal safe path:
- either hide/disable edit entry points in UI if backend is not ready
- or fully implement the supported backend edit flow if small and safe

Prefer consistency over ambition.

Validation:
- No user path should lead to a fake working feature

---

## Task 8. Fix XP persistence consistency
Goal:
Make XP behavior internally coherent.

Required actions:
- Analyze relationship between `xp_logs`, stats calculation, validations, and `registro_habitos.xp_ganado`
- Decide the canonical source of truth
- Make code consistent with that decision
- Avoid double counting

Validation:
- Re-run check-in/validation flow
- Verify XP totals, logs, and stats are coherent

---

## Task 9. Harden frontend auth/session guard
Goal:
Reduce false-authenticated UI state.

Required actions:
- Review current `hasSavedSession()` / dashboard guard logic
- Make frontend session checks stricter
- Avoid treating arbitrary stale localStorage as a valid authenticated state
- Prefer minimal safe validation, not overengineering

Validation:
- Expired/invalid/malformed local session should not silently pass as valid
- Real authenticated flow should continue working

---

# PHASE 3 — SECONDARY HARDENING

Do not start this until Phases 1 and 2 are done.

## Task 10. Add real migration baseline or document official DB evolution path
## Task 11. Replace silent dashboard/profile fallbacks with honest UI states
## Task 12. Fix profile achievements calculation
## Task 13. Audit validation modes and explicitly mark unsupported ones

---

## REQUIRED OUTPUT FORMAT

For each task, provide:

1. WHAT YOU CHANGED
- files modified
- exact purpose

2. ROOT CAUSE
- what was wrong

3. FIX IMPLEMENTED
- what you changed and why

4. VALIDATION
- commands run
- tests run
- manual verification steps
- result

5. RISK / FOLLOW-UP
- anything still pending
- any compatibility concern

---

## RULES FOR IMPLEMENTATION

- Make small, targeted fixes
- Prefer safe fixes over broad refactors
- Do not invent new product scope
- Do not leave fake-success UI behavior in place
- Do not mark something “fixed” without validating it
- If a task reveals a deeper dependency, note it clearly but still complete as much as possible
- Preserve working MVP flows

---

## FINAL GOAL

At the end of this remediation phase, I want:
- a fresh DB that initializes correctly
- runtime foreign keys actually enforced
- no sensitive auth/bootstrap logging
- safer secret handling
- honest frontend stats behavior
- a clear report of what was fixed and what still blocks deployment

Start with PHASE 1 only. Do not skip validation.