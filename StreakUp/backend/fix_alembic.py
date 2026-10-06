import os
from dotenv import load_dotenv
load_dotenv(".env")

from sqlalchemy import create_engine, text

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)"))
    conn.commit()
    print("Altered alembic_version successfully")
