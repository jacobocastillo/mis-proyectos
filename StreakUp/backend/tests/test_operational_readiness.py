import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models.habit import Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.services.openai_service import (
    VALIDATION_PROVIDER_UNAVAILABLE_CODE,
    ValidationUnavailableError,
)


class OperationalReadinessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "operational-readiness.db")
        self.config = type(
            "OperationalReadinessConfig",
            (),
            {
                "SECRET_KEY": "test-secret-key-with-32-characters!!",
                "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars!!",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": True,
                "ENVIRONMENT": "test",
                "OPENAI_API_KEY": "",
            },
        )

        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.runner = self.app.test_cli_runner()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _seed_catalog(self) -> None:
        result = self.runner.invoke(args=["seed-catalog"])
        self.assertEqual(result.exit_code, 0, msg=result.output)

    def _create_user(self) -> User:
        user = User(username="Daniel", email="daniel@correo.com", role="user")
        user.set_password("daniel-password")
        db.session.add(user)
        db.session.commit()
        return user

    def _login_headers(self) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "daniel@correo.com", "password": "daniel-password"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        return {"Authorization": f"Bearer {payload['access_token']}"}

    def test_seed_catalog_command_is_idempotent(self) -> None:
        first = self.runner.invoke(args=["seed-catalog"])
        second = self.runner.invoke(args=["seed-catalog"])

        self.assertEqual(first.exit_code, 0, msg=first.output)
        self.assertEqual(second.exit_code, 0, msg=second.output)
        self.assertIn("categories_created=3", first.output)
        self.assertIn("habits_created=11", first.output)
        self.assertIn("categories_created=0", second.output)
        self.assertIn("habits_created=0", second.output)
        self.assertEqual(Habit.query.filter_by(activo=True).count(), 11)

    def test_healthz_and_readyz_report_real_state(self) -> None:
        health = self.client.get("/healthz")
        before = self.client.get("/readyz")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json(), {"status": "ok"})
        self.assertEqual(before.status_code, 503)

        self._seed_catalog()

        after = self.client.get("/readyz")
        payload = after.get_json()

        self.assertEqual(after.status_code, 200)
        self.assertIsNotNone(payload)
        self.assertTrue(payload["checks"]["database"]["ready"])
        self.assertTrue(payload["checks"]["catalog"]["ready"])
        self.assertEqual(payload["checks"]["catalog"]["categories"], 3)
        self.assertEqual(payload["checks"]["catalog"]["habits"], 11)
        self.assertEqual(
            payload["checks"]["validation"],
            {
                "provider": "openai",
                "configured": False,
                "status": "not_configured",
                "message": "OpenAI API key is not configured.",
            },
        )

    def test_readyz_reports_validation_as_configured_but_unverified_when_key_exists(self) -> None:
        self._seed_catalog()
        self.app.config["OPENAI_API_KEY"] = "test-openai-key"

        response = self.client.get("/readyz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["checks"]["validation"],
            {
                "provider": "openai",
                "configured": True,
                "status": "configured_unverified",
                "message": "OpenAI API key is configured; provider availability is verified at request time.",
            },
        )

    def test_client_error_telemetry_accepts_and_redacts_sensitive_data(self) -> None:
        with patch("app.routes.ops_routes.logger.warning") as warning:
            response = self.client.post(
                "/api/telemetry/errors",
                json={
                    "message": "Request failed with password=super-secret and Bearer abc.def.ghi",
                    "name": "Error",
                    "url": "/profile",
                    "password": "super-secret",
                    "authorization": "Bearer abc.def.ghi",
                    "ignored": "not included",
                },
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json(), {"status": "accepted"})
        self.assertTrue(warning.called)
        output = str(warning.call_args)
        self.assertIn("[REDACTED]", output)
        self.assertNotIn("super-secret", output)
        self.assertNotIn("abc.def.ghi", output)
        self.assertNotIn("not included", output)

    def test_validation_returns_safe_503_when_openai_is_missing(self) -> None:
        self._seed_catalog()
        user = self._create_user()
        habit = db.session.get(Habit, 1)
        self.assertIsNotNone(habit)

        db.session.add(
            UserHabit(
                usuario_id=user.id,
                habito_id=habit.id,
                fecha_inicio=date.today(),
                activo=True,
            )
        )
        db.session.commit()

        response = self.client.post(
            "/api/habits/validate",
            json={"habit_id": 1, "image": "image-base64"},
            headers=self._login_headers(),
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                "error": "La validación de fotos no está disponible en este entorno.",
                "code": "validation_not_configured",
            },
        )

    def test_validation_returns_stable_code_when_provider_is_temporarily_unavailable(self) -> None:
        self._seed_catalog()
        user = self._create_user()
        habit = db.session.get(Habit, 1)
        self.assertIsNotNone(habit)
        self.app.config["OPENAI_API_KEY"] = "test-openai-key"

        db.session.add(
            UserHabit(
                usuario_id=user.id,
                habito_id=habit.id,
                fecha_inicio=date.today(),
                activo=True,
            )
        )
        db.session.commit()

        with patch(
            "app.services.validation_service.analyze_habit_image",
            side_effect=ValidationUnavailableError(
                "La validación de fotos no está disponible temporalmente.",
                VALIDATION_PROVIDER_UNAVAILABLE_CODE,
            ),
        ):
            response = self.client.post(
                "/api/habits/validate",
                json={"habit_id": 1, "image": "image-base64"},
                headers=self._login_headers(),
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.get_json(),
            {
                "error": "La validación de fotos no está disponible temporalmente.",
                "code": VALIDATION_PROVIDER_UNAVAILABLE_CODE,
            },
        )

    def test_pomodoro_routes_work_with_current_schema(self) -> None:
        self._create_user()
        headers = self._login_headers()

        create_response = self.client.post(
            "/api/pomodoro/sessions",
            json={"theme": "fire", "study_minutes": 25, "break_minutes": 5, "cycles": 4},
            headers=headers,
        )
        self.assertEqual(create_response.status_code, 201)

        created_session = create_response.get_json()
        self.assertIsNotNone(created_session)
        self.assertEqual(created_session["theme"], "fire")
        self.assertFalse(created_session["completed"])

        list_response = self.client.get("/api/pomodoro/sessions", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        sessions = list_response.get_json()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["id"], created_session["id"])

        complete_response = self.client.put(
            f"/api/pomodoro/sessions/{created_session['id']}/complete",
            headers=headers,
        )
        self.assertEqual(complete_response.status_code, 200)
        completed = complete_response.get_json()
        self.assertTrue(completed["completed"])
        self.assertIsNotNone(completed["completed_at"])

    def test_pomodoro_rejects_invalid_payloads_and_foreign_habit_ids(self) -> None:
        self._seed_catalog()
        user = self._create_user()
        headers = self._login_headers()

        other_user = User(username="Other", email="other@correo.com", role="user")
        other_user.set_password("other-password")
        db.session.add(other_user)
        db.session.commit()

        habit = db.session.get(Habit, 1)
        self.assertIsNotNone(habit)

        foreign_assignment = UserHabit(
            usuario_id=other_user.id,
            habito_id=habit.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        db.session.add(foreign_assignment)
        db.session.commit()

        invalid_minutes = self.client.post(
            "/api/pomodoro/sessions",
            json={"study_minutes": 0, "break_minutes": 5, "cycles": 4},
            headers=headers,
        )
        self.assertEqual(invalid_minutes.status_code, 400)
        self.assertEqual(
            invalid_minutes.get_json(),
            {"error": "study_minutes must be greater than 0."},
        )

        foreign_habit = self.client.post(
            "/api/pomodoro/sessions",
            json={"habit_id": foreign_assignment.id, "study_minutes": 25, "break_minutes": 5, "cycles": 4},
            headers=headers,
        )
        self.assertEqual(foreign_habit.status_code, 400)
        self.assertEqual(
            foreign_habit.get_json(),
            {"error": "habit_id must reference an active habit owned by the user."},
        )


if __name__ == "__main__":
    unittest.main()
