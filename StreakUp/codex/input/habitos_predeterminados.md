Role:
You are a senior engineer working on the StreakUP project (Flask backend + SQLite + Next.js frontend).

--------------------------------------------------

OBJECTIVE (POINT B)

Migrate the habit creation system from a hardcoded (fake) list to a fully database-driven system.

The final system must satisfy:

1. The habit dropdown must display ONLY data from the `habitos` table.
2. Creating a habit must NOT create a new catalog entry:
   → it must insert into `habitos_usuario` (user-habit relationship).
3. The system must allow retrieving the user's active habits correctly.
4. The UI must dynamically reflect the database state.

--------------------------------------------------

CURRENT STATE (POINT A)

Backend:
- Schema already exists with:
  - habitos (catalog)
  - habitos_usuario (user relation)
  - registro_habitos
  - validaciones
- Database has been populated via seed.sql

Issues:
- No functional endpoint to fetch habits
- No functional endpoint to assign habits to a user
- No endpoint to retrieve "user habits"

Frontend:
- Dropdown uses hardcoded (fake) data
- No real API consumption
- Creating a habit does not persist correctly

--------------------------------------------------

RECON SCOPE

Analyze the entire repository and answer:

1. Backend
   - Do ORM models exist for `habitos` and `habitos_usuario`?
   - Are there any existing endpoints (even partially implemented)?
   - Where should the logic live? (routes vs services)

2. Frontend
   - Where is the habit creation component located?
   - How is the dropdown currently implemented?
   - Where should API fetching be integrated?

3. Broken Flow Analysis
   - Explain exactly why the current flow does NOT persist data correctly

--------------------------------------------------

GAPS (WHAT IS MISSING)

Clearly identify:

- Missing endpoints
- Missing backend logic
- Missing frontend integration
- Any architectural issues

--------------------------------------------------

IMPLEMENTATION PLAN

Propose a step-by-step plan to reach POINT B:

PHASE 1 - Backend
- GET /habitos
- POST /habitos_usuario
- GET /mis-habitos

PHASE 2 - Frontend
- Replace hardcoded list with API fetch
- Connect habit creation flow
- Manage state properly

PHASE 3 - Validation
- Verify DB inserts
- Verify dynamic rendering

--------------------------------------------------

RULES

- Do NOT break existing schema
- Keep SQLite compatibility
- Minimal but correct changes
- Avoid overengineering

--------------------------------------------------

DELIVERABLE

Provide:

1. Full diagnosis (what is wrong today)
2. Exact list of files to modify
3. Step-by-step implementation plan (checklist style)
4. Potential risks or bugs

Do NOT write code yet.
Only provide a deep technical analysis (recon).