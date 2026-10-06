You are debugging a full-stack app (Next.js frontend + Flask backend) called StreakUP.

We already fixed the database and backend runs correctly.

Now there is a CRITICAL AUTHENTICATION FLOW BUG.

----------------------------------------
🐞 PROBLEM
----------------------------------------

Frontend shows:
"API request failed with status 401"

Backend logs show:
- GET /api/checkins/today → 401
- POST /api/habits → 401

The app DOES NOT redirect to login when unauthenticated.

----------------------------------------
🎯 GOAL
----------------------------------------

Fix the authentication flow so that:

1. User logs in → receives JWT token
2. Token is stored properly (localStorage or equivalent)
3. All API requests include:
   Authorization: Bearer <token>
4. If request returns 401:
   → automatically redirect to login
5. Protected pages cannot load without auth

----------------------------------------
🔍 INVESTIGATION TASKS
----------------------------------------

1. Find login implementation in frontend:
   - where POST /api/auth/login is called
   - verify token is returned

2. Verify token storage:
   - localStorage / cookies / state
   - is token actually saved?

3. Inspect API layer:
   - fetch / axios wrapper
   - check if Authorization header is added

4. Search for ALL API calls:
   - ensure they use token

5. Check routing / guards:
   - is there a protected route system?
   - is auth checked before rendering pages?

6. Check 401 handling:
   - is there a global interceptor?
   - is user redirected on 401?

7. Verify logout behavior:
   - token cleared?
   - redirect to login?

----------------------------------------
🛠 REQUIRED FIXES
----------------------------------------

Implement:

1. Auth utility (getToken / setToken / removeToken)

2. Global API wrapper:

   fetchWithAuth(url, options):
     - adds Authorization header
     - handles 401 → redirect to /login

3. Login flow:
   - save token
   - redirect to dashboard

4. Route protection:
   - if no token → redirect

----------------------------------------
📦 OUTPUT
----------------------------------------

1. Files modified
2. Exact code for:
   - login
   - API wrapper
   - auth guard
3. Explanation of fix

----------------------------------------
⚠️ IMPORTANT
----------------------------------------

Do NOT assume token exists.
Trace actual data flow from login → request.

Focus ONLY on fixing auth flow.