import os
from dotenv import load_dotenv
load_dotenv(".env")

from sqlalchemy import create_engine, text

db_url = os.environ.get("DATABASE_URL")
print(f"Connecting to: {db_url}")
engine = create_engine(db_url)

with engine.connect() as conn:
    # Check tables
    res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
    tables = [r[0] for r in res.fetchall()]
    print(f"Tables: {tables}")
    
    # If alembic_version exists, print its content
    if "alembic_version" in tables:
        res = conn.execute(text("SELECT version_num FROM alembic_version"))
        versions = [r[0] for r in res.fetchall()]
        print(f"Alembic versions: {versions}")
        
        # If it's a completely empty database except for the old alembic version and maybe some tables we want to drop, let's just wipe the public schema
        # Actually let's just drop all tables to start fresh
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS \"{table}\" CASCADE"))
            print(f"Dropped {table}")
        
        conn.commit()
