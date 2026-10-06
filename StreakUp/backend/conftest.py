"""
Root conftest.py — forces SQLite in-memory database for all local tests.

This must reside here (backend root) so it sets the environment BEFORE
any test module imports Config / create_app, which reads DATABASE_URL
at module level via load_dotenv.
"""
import os

# Override before any app code is imported
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-32-chars-long!!")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-key-that-is-32-chars-long!!!")
os.environ.setdefault("FLASK_ENV", "development")
