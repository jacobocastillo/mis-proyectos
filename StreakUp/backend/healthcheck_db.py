"""
Full DB health check for Supabase connection.
Verifies tables, columns, and seeds achievements catalog.
"""
import os
from dotenv import load_dotenv
load_dotenv(".env")

from sqlalchemy import create_engine, text, inspect

db_url = os.environ.get("DATABASE_URL")
print("DATABASE_URL points to:", db_url.split('@')[1] if db_url else 'MISSING!')
print()

engine = create_engine(db_url)

with engine.connect() as conn:
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema="public")
    print("[OK] Tables found ({}): {}".format(len(tables), sorted(tables)))
    print()

    # Check alembic version
    res = conn.execute(text("SELECT version_num FROM alembic_version"))
    rows = res.fetchall()
    print("[OK] Alembic version(s):", [r[0] for r in rows])
    print()

    # Check critical columns per table
    checks = {
        "habitos_usuario": ["min_text_length", "frecuencia", "tipo_validacion"],
        "achievements": ["key", "name", "xp_bonus", "emoji"],
        "user_achievements": ["user_id", "achievement_id", "earned_at"],
        "users": ["id", "username", "email", "password_hash"],
    }

    all_ok = True
    for table, expected_cols in checks.items():
        if table not in tables:
            print("[FAIL] Table '{}' MISSING!".format(table))
            all_ok = False
            continue
        actual_cols = [c["name"] for c in inspector.get_columns(table, schema="public")]
        missing = [c for c in expected_cols if c not in actual_cols]
        if missing:
            print("[FAIL] Table '{}' missing columns: {}".format(table, missing))
            all_ok = False
        else:
            print("[OK] Table '{}' has all required columns.".format(table))

    # Check achievements seeded
    res = conn.execute(text("SELECT COUNT(*) FROM achievements"))
    count = res.scalar()
    print()
    if count == 0:
        print("[WARN] achievements table is EMPTY -- run `flask seed-catalog`")
        all_ok = False
    else:
        print("[OK] achievements catalog has {} entries.".format(count))

    print()
    if all_ok:
        print("[PASS] All checks passed! Database is healthy.")
    else:
        print("[FAIL] Some checks failed -- see above.")
