import os
import tempfile
import unittest
from datetime import date

from app import create_app
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.sync_operation import SyncOperation
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.xp_log import XpLog


class SyncRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "sync-test.db")
        self.config = type(
            "SyncTestConfig",
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
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        category = Category(nombre="Sync", descripcion="Sync tests")
        db.session.add(category)
        db.session.flush()

        self.user = User(username="sync_user", email="sync@test.com", role="user")
        self.user.set_password("sync-password")
        self.other_user = User(username="other_user", email="other@test.com", role="user")
        self.other_user.set_password("other-password")
        db.session.add_all([self.user, self.other_user])
        db.session.flush()

        self.simple_habit = Habit(
            categoria_id=category.id,
            nombre="Simple check",
            dificultad="facil",
            xp_base=10,
            tipo_validacion="check",
            meta_type="boolean",
            max_xp_per_day=10,
        )
        self.photo_habit = Habit(
            categoria_id=category.id,
            nombre="Photo",
            dificultad="media",
            xp_base=20,
            tipo_validacion="foto",
            meta_type="boolean",
            max_xp_per_day=20,
        )
        db.session.add_all([self.simple_habit, self.photo_habit])
        db.session.flush()

        self.simple_assignment = UserHabit(
            usuario_id=self.user.id,
            habito_id=self.simple_habit.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        self.photo_assignment = UserHabit(
            usuario_id=self.user.id,
            habito_id=self.photo_habit.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        self.foreign_assignment = UserHabit(
            usuario_id=self.other_user.id,
            habito_id=self.simple_habit.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        db.session.add_all([self.simple_assignment, self.photo_assignment, self.foreign_assignment])
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _login_headers(self) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "sync@test.com", "password": "sync-password"},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _sync(self, operations: list[dict]) -> tuple[int, dict]:
        response = self.client.post(
            "/api/sync",
            json={"operations": operations},
            headers=self._login_headers(),
        )
        return response.status_code, response.get_json()

    def _toggle_operation(self, op_id: str, habit_id: int | None = None) -> dict:
        return {
            "client_operation_id": op_id,
            "operation_type": "toggle_checkin",
            "payload": {
                "habit_id": habit_id if habit_id is not None else self.simple_assignment.id,
                "date": date.today().isoformat(),
            },
        }

    def test_duplicate_client_operation_replays_ack_without_duplicate_progress(self) -> None:
        operation = self._toggle_operation("offline-op-1")

        first_status, first_payload = self._sync([operation])
        second_status, second_payload = self._sync([operation])

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first_payload, second_payload)
        self.assertEqual(first_payload["results"][0]["status"], "acked")
        self.assertTrue(first_payload["results"][0]["result"]["checked"])
        self.assertEqual(CheckIn.query.filter_by(habitousuario_id=self.simple_assignment.id).count(), 1)
        self.assertEqual(XpLog.query.filter_by(user_id=self.user.id, razon="checkin").count(), 1)
        self.assertEqual(SyncOperation.query.count(), 1)

    def test_sync_rejects_foreign_habit_without_receipt_duplication(self) -> None:
        status, payload = self._sync([
            self._toggle_operation("foreign-op", habit_id=self.foreign_assignment.id)
        ])

        self.assertEqual(status, 200)
        result = payload["results"][0]
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(CheckIn.query.count(), 0)
        self.assertEqual(SyncOperation.query.count(), 1)

    def test_sync_rejects_validation_driven_habit_as_conflict(self) -> None:
        status, payload = self._sync([
            self._toggle_operation("photo-op", habit_id=self.photo_assignment.id)
        ])

        self.assertEqual(status, 200)
        result = payload["results"][0]
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["error"]["code"], "conflict")
        self.assertIn("requires validation", result["error"]["message"])
        self.assertEqual(CheckIn.query.count(), 0)
        self.assertEqual(XpLog.query.count(), 0)

    def test_partial_batch_preserves_success_and_reports_permanent_failure(self) -> None:
        status, payload = self._sync(
            [
                self._toggle_operation("good-op"),
                self._toggle_operation("bad-op", habit_id=999_999),
            ]
        )

        self.assertEqual(status, 200)
        results = {result["client_operation_id"]: result for result in payload["results"]}
        self.assertEqual(results["good-op"]["status"], "acked")
        self.assertEqual(results["bad-op"]["status"], "failed")
        self.assertEqual(results["bad-op"]["error"]["retryable"], False)
        self.assertEqual(CheckIn.query.filter_by(habitousuario_id=self.simple_assignment.id).count(), 1)
        self.assertEqual(SyncOperation.query.count(), 2)

    def test_sync_requires_valid_operations_array(self) -> None:
        response = self.client.post(
            "/api/sync",
            json={"operations": "not-a-list"},
            headers=self._login_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "invalid_sync_payload")


if __name__ == "__main__":
    unittest.main()
