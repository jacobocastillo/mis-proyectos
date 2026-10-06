You are auditing and fixing a full-stack app (Next.js frontend + Flask backend) called StreakUP.

The backend uses:
- Flask
- SQLAlchemy
- JWT authentication

The database is SQLite:
- data/app.db

----------------------------------------
🐞 CURRENT PROBLEMS
----------------------------------------

1. Login fails with:
   "Invalid email or password"
   (even though users exist in DB and passwords are hashed)

2. Frontend gets:
   401 Unauthorized on ALL protected endpoints

3. App does NOT redirect to login when unauthenticated

4. Sessions are NOT independent per user

----------------------------------------
🎯 GOAL
----------------------------------------

Make authentication fully functional and tied to the database so that:

1. Users log in using DB credentials (email + hashed password)
2. Each login returns a valid JWT token
3. Each request is linked to a specific user (session-like behavior)
4. Each user sees ONLY their own data (habits, stats, etc.)
5. Frontend properly handles auth state

----------------------------------------
🔍 BACKEND TASKS
----------------------------------------

1. Fix login logic:
   - Ensure use of:
     check_password_hash(user.password_hash, password)

2. Ensure JWT token includes user identity:
   Example:
     create_access_token(identity=user.id)

3. Verify protected routes:
   - Must use @jwt_required()

4. Ensure user context is loaded correctly:
   Example:
     user_id = get_jwt_identity()

5. Ensure ALL queries are user-scoped:
   Example:
     Habit.query.filter_by(user_id=user_id)

6. Fix ensure_seed_user if needed:
   - Must not override DB
   - Must respect existing users

----------------------------------------
🔍 FRONTEND TASKS
----------------------------------------

1. Fix login flow:
   - Call POST /api/auth/login
   - Save token in localStorage

2. Create auth utility:
   getToken()
   setToken()
   removeToken()

3. Create API wrapper:
   fetchWithAuth():
     - Adds Authorization: Bearer <token>
     - Handles 401 → redirect to /login

4. Protect routes:
   - If no token → redirect to login

5. On login success:
   - Redirect to dashboard

----------------------------------------
🔍 SESSION BEHAVIOR (CRITICAL)
----------------------------------------

Ensure each user session is independent:

- JWT acts as session (stateless) :contentReference[oaicite:0]{index=0}
- Each request must include token
- Backend must resolve user from token

Example flow:
  login → token → request → decode → user_id → query DB

----------------------------------------
🛠 REQUIRED OUTPUT
----------------------------------------

1. Fixes in:
   - auth_service.py
   - routes using JWT
   - frontend login
   - API wrapper

2. Show corrected login function

3. Show JWT creation and usage

4. Show how user_id flows:
   login → token → request → DB query

5. Confirm:
   - login works
   - no more 401
   - each user sees their own data

----------------------------------------
⚠️ IMPORTANT
----------------------------------------

DO NOT guess.

Trace real flow:
login → token → request → backend → DB

Ensure EVERYTHING is tied to user_id.

----------------------------------------
FINAL OBJECTIVE:
Make authentication + database fully integrated and session-safe.