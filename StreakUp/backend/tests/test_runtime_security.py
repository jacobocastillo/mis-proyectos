import contextlib
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.config import normalize_database_url
from app.extensions import db
from app.models.user import User


class RuntimeSecurityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "runtime-security.db")
        self._initialize_schema()
        self.config = type(
            "RuntimeSecurityConfig",
            (),
            {
                "SECRET_KEY": "test-secret",
                "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": True,
                "ENVIRONMENT": "test",
            },
        )

        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        db.session.remove()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _initialize_schema(self) -> None:
        schema_path = Path(__file__).resolve().parents[2] / "data" / "db" / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(schema_sql)

    def test_runtime_enables_sqlite_foreign_keys(self) -> None:
        value = db.session.execute(text("PRAGMA foreign_keys")).scalar()
        self.assertEqual(value, 1)

    def test_runtime_rejects_invalid_foreign_keys(self) -> None:
        with self.assertRaises(IntegrityError):
            db.session.execute(
                text(
                    """
                    INSERT INTO xp_logs (usuario_id, cantidad, fuente)
                    VALUES (9999, 10, 'checkin')
                    """
                )
            )
            db.session.commit()

        db.session.rollback()

    def test_create_app_does_not_print_database_uri(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            create_app(self.config)

        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn("DB URI:", output)
        self.assertNotIn(self.database_path, output)

    def test_login_does_not_print_sensitive_auth_details(self) -> None:
        user = User(username="Daniel", email="daniel@correo.com", role="user")
        user.set_password("daniel-password")
        db.session.add(user)
        db.session.commit()

        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            response = self.client.post(
                "/api/auth/login",
                json={"email": "daniel@correo.com", "password": "daniel-password"},
            )

        self.assertEqual(response.status_code, 200)

        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn("LOGIN ATTEMPT:", output)
        self.assertNotIn("USER FOUND:", output)
        self.assertNotIn("HASH:", output)
        self.assertNotIn(user.password_hash, output)

    def test_prod_like_config_rejects_weak_secrets(self) -> None:
        prod_config = type(
            "ProdConfig",
            (),
            {
                "SECRET_KEY": "change-me-in-production",
                "JWT_SECRET_KEY": "short-secret",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": False,
                "ENVIRONMENT": "production",
            },
        )

        with self.assertRaisesRegex(ValueError, "Insecure runtime secret configuration"):
            create_app(prod_config)

    def test_prod_like_config_accepts_strong_secrets(self) -> None:
        prod_config = type(
            "ProdConfigStrongSecrets",
            (),
            {
                "SECRET_KEY": "prod-secret-key-with-32-characters!!",
                "JWT_SECRET_KEY": "prod-jwt-secret-key-with-32-characters!!",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": False,
                "ENVIRONMENT": "production",
                "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            },
        )

        app = create_app(prod_config)
        self.assertEqual(app.config["ENVIRONMENT"], "production")

    def test_render_postgres_url_is_normalized_for_sqlalchemy(self) -> None:
        self.assertEqual(
            normalize_database_url("postgres://user:pass@host:5432/streakup"),
            "postgresql+psycopg://user:pass@host:5432/streakup",
        )
        self.assertEqual(
            normalize_database_url("postgresql://user:pass@host:5432/streakup"),
            "postgresql+psycopg://user:pass@host:5432/streakup",
        )

    def test_prod_cors_only_allows_configured_origin(self) -> None:
        prod_config = type(
            "ProdCorsConfig",
            (),
            {
                "SECRET_KEY": "prod-secret-key-with-32-characters!!",
                "JWT_SECRET_KEY": "prod-jwt-secret-key-with-32-characters!!",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": False,
                "ENVIRONMENT": "production",
                "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            },
        )

        app = create_app(prod_config)
        client = app.test_client()

        allowed = client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        blocked = client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(allowed.headers.get("Access-Control-Allow-Origin"), "https://app.example.com")
        self.assertIsNone(blocked.headers.get("Access-Control-Allow-Origin"))

    def test_logout_permanently_blocks_token_on_all_protected_routes(self) -> None:
        user = User(username="RevocationTest", email="revoke@example.com", role="user")
        user.set_password("secure-password")
        db.session.add(user)
        db.session.commit()

        login = self.client.post(
            "/api/auth/login",
            json={"email": "revoke@example.com", "password": "secure-password"},
        )
        self.assertEqual(login.status_code, 200)
        access_token = login.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        self.client.post("/api/auth/logout", headers=headers)

        habits = self.client.get("/api/habits", headers=headers)
        stats = self.client.get("/api/stats/summary", headers=headers)

        self.assertEqual(habits.status_code, 401)
        self.assertEqual(stats.status_code, 401)


if __name__ == "__main__":
    unittest.main()
