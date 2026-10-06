You are debugging a Flask + SQLAlchemy project called StreakUP.

We have a critical database inconsistency bug:

ERROR:
(sqlite3.OperationalError) no such column: users.total_xp

Context:
- We already recreated the database using:
  make db-reset
- schema.sql DOES include total_xp
- Database file created: data/app.db
- But backend still says column doesn't exist

This strongly suggests the backend is NOT using the same database file.

Your task is to perform a FULL RECON and find the root cause.

----------------------------------------
🔍 INVESTIGATION TASKS
----------------------------------------

1. Locate where SQLAlchemy database URI is defined:
   - search for SQLALCHEMY_DATABASE_URI
   - search for create_engine
   - search for any config/env loading

2. Print ALL possible database paths used in the project:
   - hardcoded paths
   - environment variables (.env)
   - default fallbacks

3. Check if multiple .db files exist:
   - scan project for *.db files
   - list all paths

4. Verify if relative vs absolute path is incorrect:
   - check if using sqlite:///app.db vs sqlite:///data/app.db
   - confirm working directory when app runs

5. Inspect create_app() lifecycle:
   - is db.create_all() being called?
   - is it creating a new DB automatically?

6. Confirm which DB is actually used at runtime:
   - inject debug log to print:
     app.config["SQLALCHEMY_DATABASE_URI"]

7. Check if any of these issues exist:
   - wrong path
   - duplicated DB
   - in-memory DB (sqlite:///:memory:)
   - incorrect relative path

----------------------------------------
🎯 GOAL
----------------------------------------

Identify EXACTLY why backend is not reading data/app.db.

----------------------------------------
🛠 REQUIRED OUTPUT
----------------------------------------

1. Root cause (1 clear sentence)
2. Exact file causing issue
3. Exact line to fix
4. Correct SQLAlchemy URI
5. Any extra bugs found

----------------------------------------
⚠️ IMPORTANT
----------------------------------------

DO NOT guess.
Trace actual execution path and configuration.

Focus ONLY on database mismatch issue.