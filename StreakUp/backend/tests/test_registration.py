import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.user import User


class RegistrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "registration-test.db")
        self._initialize_schema()
        TestConfig = type(
            "RegistrationTestConfig",
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

        self.app = create_app(TestConfig)
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

    def _register(self, **overrides):
        payload = {
            "username": "Daniel",
            "email": "daniel@correo.com",
            "password": "daniel-password",
        }
        payload.update(overrides)
        return self.client.post("/api/auth/register", json=payload)

    def test_register_creates_user(self) -> None:
        response = self._register()

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["message"], "User registered successfully.")
        self.assertEqual(payload["user"]["username"], "Daniel")
        self.assertEqual(payload["user"]["email"], "daniel@correo.com")
        self.assertEqual(payload["user"]["role"], "user")
        self.assertNotIn("password_hash", payload["user"])
        self.assertEqual(User.query.count(), 1)

    def test_local_schema_supports_profile_and_pomodoro_api(self) -> None:
        self.assertEqual(self._register().status_code, 201)
        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "daniel@correo.com", "password": "daniel-password"},
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        achievements_response = self.client.get(
            "/api/achievements",
            headers=headers,
        )
        self.assertEqual(achievements_response.status_code, 200)
        self.assertGreater(len(achievements_response.get_json()), 0)

        pomodoro_response = self.client.get(
            "/api/pomodoro/sessions",
            headers=headers,
        )
        self.assertEqual(pomodoro_response.status_code, 200)

    def test_register_rejects_duplicate_email(self) -> None:
        first = self._register()
        self.assertEqual(first.status_code, 201)

        response = self._register(username="Gustavo")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json(), {"error": "A user with this email already exists."})

    def test_register_rejects_duplicate_username(self) -> None:
        first = self._register()
        self.assertEqual(first.status_code, 201)

        response = self._register(email="other@correo.com")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json(), {"error": "A user with this username already exists."})

    def test_register_rejects_invalid_email(self) -> None:
        response = self._register(email="not-an-email")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"errors": ["Invalid email format."]})
        self.assertEqual(User.query.count(), 0)

    def test_register_rejects_short_password(self) -> None:
        response = self._register(password="short")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"errors": ["Password must be at least 8 characters."]},
        )
        self.assertEqual(User.query.count(), 0)

    def test_register_stores_hashed_password(self) -> None:
        response = self._register(password="plain-password")

        self.assertEqual(response.status_code, 201)
        user = User.query.filter_by(email="daniel@correo.com").one()
        self.assertNotEqual(user.password_hash, "plain-password")
        self.assertTrue(user.check_password("plain-password"))
        self.assertFalse(user.check_password("wrong-password"))
        self.assertNotIn("password_hash", response.get_json()["user"])


if __name__ == "__main__":
    unittest.main()
