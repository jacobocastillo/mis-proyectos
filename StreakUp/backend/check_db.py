import os
from dotenv import load_dotenv
load_dotenv(".env")

from sqlalchemy import create_engine, text

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='habitos_usuario'"))
    cols = [r[0] for r in res.fetchall()]
    print("Columns in habitos_usuario:", cols)
    
    res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
    tables = [r[0] for r in res.fetchall()]
    print("Tables in public schema:", tables)
