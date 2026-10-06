import json
import unittest
from datetime import date

from app import create_app
from app.extensions import db
from app.models.achievement import Achievement, UserAchievement
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.pomodoro_session import PomodoroSession
from app.models.social import SharedStreakGroup, SharedStreakMembership
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog


class PrivacyExportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        TestConfig = type(
            "PrivacyExportConfig",
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
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _auth_headers(self) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "daniel@correo.com", "password": "daniel-password"},
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.get_json()['access_token']}"}

    def _seed_export_data(self) -> None:
        category = Category(nombre="Salud")
        habit = Habit(
            category=category,
            nombre="Caminar",
            descripcion="Caminar diario",
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
            key="export_test",
            name="Export Test",
            description="Export achievement",
            emoji="*",
            xp_bonus=5,
        )
        group = SharedStreakGroup(
            owner_user_id=self.user.id,
            name="Grupo privado",
            invite_code="INVITE42",
        )
        db.session.add_all([category, habit, user_habit, achievement, group])
        db.session.flush()
        db.session.add_all(
            [
                CheckIn(habitousuario_id=user_habit.id, fecha=date.today(), xp_ganado=10),
                PomodoroSession(user_id=self.user.id, habit_id=user_habit.id, completed=True),
                UserAchievement(user_id=self.user.id, achievement_id=achievement.id),
                XpLog(user_id=self.user.id, cantidad=10, razon="checkin", habit_id=user_habit.id, event_date=date.today()),
                SharedStreakMembership(group_id=group.id, user_id=self.user.id, status="active", share_progress=True),
                ValidationLog(
                    habitousuario_id=user_habit.id,
                    tipo_validacion="foto",
                    evidencia="base64-private-evidence",
                    status="approved",
                    validado=True,
                ),
            ]
        )
        db.session.commit()

    def test_export_requires_authentication(self) -> None:
        response = self.client.get("/api/users/me/export")

        self.assertEqual(response.status_code, 401)

    def test_export_returns_portable_data_without_credentials_or_raw_evidence(self) -> None:
        self._seed_export_data()

        response = self.client.get("/api/users/me/export", headers=self._auth_headers())

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["profile"]["email"], "daniel@correo.com")
        self.assertNotIn("password_hash", payload["profile"])
        self.assertEqual(len(payload["habits"]), 1)
        self.assertEqual(len(payload["checkins"]), 1)
        self.assertEqual(len(payload["pomodoro_sessions"]), 1)
        self.assertEqual(len(payload["achievements"]), 1)
        self.assertEqual(len(payload["xp_logs"]), 1)
        self.assertEqual(len(payload["social_memberships"]), 1)
        self.assertEqual(len(payload["owned_social_groups"]), 1)
        self.assertEqual(payload["validation_records"][0]["evidence_present"], True)

        serialized = json.dumps(payload)
        self.assertNotIn(self.user.password_hash, serialized)
        self.assertNotIn("daniel-password", serialized)
        self.assertNotIn("base64-private-evidence", serialized)


if __name__ == "__main__":
    unittest.main()
