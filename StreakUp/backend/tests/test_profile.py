import unittest
from datetime import date
import json

from app import create_app
from app.extensions import db
from app.models.achievement import Achievement, UserAchievement
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.pomodoro_session import PomodoroSession
from app.models.social import SharedStreakGroup, SharedStreakMembership
from app.models.sync_operation import SyncOperation
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog


class ProfileTestCase(unittest.TestCase):
    def setUp(self) -> None:
        TestConfig = type(
            "ProfileTestConfig",
            (),
            {
                "SECRET_KEY": "test-secret",
                "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
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
        db.create_all()

        self.user = User(username="Daniel", email="daniel@correo.com", role="user")
        self.user.set_password("daniel-password")
        self.other_user = User(username="Gustavo", email="gustavo@correo.com", role="user")
        self.other_user.set_password("gustavo-password")
        db.session.add_all([self.user, self.other_user])
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self, email: str = "daniel@correo.com", password: str = "daniel-password"):
        return self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )

    def _auth_headers(self) -> dict[str, str]:
        token = self._login().get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_profile_returns_authenticated_user(self) -> None:
        response = self.client.get("/api/users/me", headers=self._auth_headers())

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["id"], self.user.id)
        self.assertEqual(payload["username"], "Daniel")
        self.assertEqual(payload["email"], "daniel@correo.com")
        self.assertNotIn("password_hash", payload)

    def test_update_profile_changes_username(self) -> None:
        response = self.client.put(
            "/api/users/me",
            json={"username": "Daniel Nuevo"},
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["username"], "Daniel Nuevo")
        self.assertEqual(payload["email"], "daniel@correo.com")

        db.session.refresh(self.user)
        self.assertEqual(self.user.username, "Daniel Nuevo")

    def test_update_profile_rejects_duplicate_username(self) -> None:
        response = self.client.put(
            "/api/users/me",
            json={"username": "Gustavo"},
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json(), {"error": "A user with this username already exists."})

    def test_update_profile_rejects_invalid_username(self) -> None:
        response = self.client.put(
            "/api/users/me",
            json={"username": "Al"},
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"errors": ["Username must be at least 3 characters."]})

    def test_update_profile_rejects_email_change(self) -> None:
        response = self.client.put(
            "/api/users/me",
            json={"username": "Daniel", "email": "new@correo.com"},
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"errors": ["Email cannot be changed from this endpoint."]})

        db.session.refresh(self.user)
        self.assertEqual(self.user.email, "daniel@correo.com")

    def test_profile_routes_require_authentication(self) -> None:
        get_response = self.client.get("/api/users/me")
        put_response = self.client.put("/api/users/me", json={"username": "Daniel Nuevo"})

        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(put_response.status_code, 401)

    def _seed_user_owned_data(self) -> UserHabit:
        category = Category(nombre="Salud")
        habit = Habit(
            category=category,
            nombre="Tomar agua",
            descripcion="Beber agua",
            dificultad="facil",
            xp_base=10,
            tipo_validacion="check",
            frecuencia="daily",
        )
        user_habit = UserHabit(
            usuario_id=self.user.id,
            habit=habit,
            fecha_inicio=date.today(),
            activo=True,
        )
        achievement = Achievement(
            key="privacy_test",
            name="Privacy Test",
            description="Test achievement",
            emoji="*",
            xp_bonus=5,
        )
        group = SharedStreakGroup(
            owner_user_id=self.user.id,
            name="Grupo privado",
            invite_code="ABC123",
        )
        db.session.add_all([category, habit, user_habit, achievement, group])
        db.session.flush()
        db.session.add_all(
            [
                CheckIn(habitousuario_id=user_habit.id, fecha=date.today(), completado=True, xp_ganado=10),
                ValidationLog(
                    habitousuario_id=user_habit.id,
                    tipo_validacion="foto",
                    evidencia="base64-private-evidence",
                    status="approved",
                    validado=True,
                ),
                PomodoroSession(user_id=self.user.id, habit_id=user_habit.id, completed=True),
                UserAchievement(user_id=self.user.id, achievement_id=achievement.id),
                XpLog(user_id=self.user.id, cantidad=10, razon="checkin", habit_id=user_habit.id, event_date=date.today()),
                SharedStreakMembership(group_id=group.id, user_id=self.user.id, status="active", share_progress=True),
                SyncOperation(
                    user_id=self.user.id,
                    client_operation_id="client-op-1",
                    operation_type="toggle_checkin",
                    payload_json=json.dumps({"habit_id": user_habit.id}),
                    status="acked",
                    response_json=json.dumps({"ok": True}),
                ),
            ]
        )
        db.session.commit()
        return user_habit

    def test_delete_account_cascades_user_owned_data(self) -> None:
        user_habit = self._seed_user_owned_data()
        user_habit_id = user_habit.id
        headers = self._auth_headers()

        response = self.client.delete("/api/users/me", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.get(User, self.user.id))
        self.assertEqual(UserHabit.query.filter_by(usuario_id=self.user.id).count(), 0)
        self.assertEqual(CheckIn.query.filter_by(habitousuario_id=user_habit_id).count(), 0)
        self.assertEqual(ValidationLog.query.filter_by(habitousuario_id=user_habit_id).count(), 0)
        self.assertEqual(PomodoroSession.query.filter_by(user_id=self.user.id).count(), 0)
        self.assertEqual(UserAchievement.query.filter_by(user_id=self.user.id).count(), 0)
        self.assertEqual(XpLog.query.filter_by(user_id=self.user.id).count(), 0)
        self.assertEqual(SharedStreakMembership.query.filter_by(user_id=self.user.id).count(), 0)
        self.assertEqual(SharedStreakGroup.query.filter_by(owner_user_id=self.user.id).count(), 0)
        self.assertEqual(SyncOperation.query.filter_by(user_id=self.user.id).count(), 0)


if __name__ == "__main__":
    unittest.main()
