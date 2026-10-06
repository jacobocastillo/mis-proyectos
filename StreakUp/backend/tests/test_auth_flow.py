import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from flask_jwt_extended import decode_token
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models.habit import Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.xp_log import XpLog
from app.services.xp_service import award_xp


class AuthFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "auth-flow-test.db")
        self._initialize_schema()
        TestConfig = type(
            "TestConfig",
            (),
            {
                "SECRET_KEY": "test-secret",
                "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": True,
            },
        )

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.startup_user_count = User.query.count()

        db.session.execute(
            text(
                """
                INSERT INTO categorias (nombre, descripcion)
                VALUES
                    ('Salud y Bienestar', 'Hábitos físicos y mentales'),
                    ('Productividad', 'Enfoque y rendimiento')
                """
            )
        )

        self.daniel_user = User(
            username="Daniel",
            email="daniel@correo.com",
            role="user",
        )
        self.daniel_user.set_password("daniel-password")

        self.gustavo_user = User(
            username="Gustavo",
            email="gustavo@correo.com",
            role="user",
        )
        self.gustavo_user.set_password("gustavo-password")

        db.session.add(self.daniel_user)
        db.session.add(self.gustavo_user)
        db.session.commit()

        self.meditar = Habit(
            categoria_id=1,
            nombre="Meditar 5-10 min",
            descripcion="Relajación mental",
            xp_base=10,
            dificultad="facil",
            tipo_validacion="tiempo",
            frecuencia="daily",
        )
        self.leer = Habit(
            categoria_id=2,
            nombre="Leer 20 min",
            xp_base=20,
            dificultad="media",
            tipo_validacion="texto",
            frecuencia="daily",
        )
        db.session.add(self.meditar)
        db.session.add(self.leer)
        db.session.commit()

        self.daniel_habit = UserHabit(
            usuario_id=self.daniel_user.id,
            habito_id=self.meditar.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        self.gustavo_habit = UserHabit(
            usuario_id=self.gustavo_user.id,
            habito_id=self.leer.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        db.session.add(self.daniel_habit)
        db.session.add(self.gustavo_habit)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _initialize_schema(self) -> None:
        schema_path = Path(__file__).resolve().parents[2] / "data" / "db" / "schema.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(schema_sql)

    def _login(self, email: str, password: str):
        return self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )

    def _auth_headers(self, access_token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    def test_app_startup_does_not_seed_any_users(self) -> None:
        self.assertEqual(self.startup_user_count, 0)

    def test_login_returns_tokens_and_user_identity(self) -> None:
        response = self._login("  DANIEL@CORREO.COM  ", "daniel-password")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertIsNotNone(payload)
        self.assertEqual(payload["user"]["email"], "daniel@correo.com")
        self.assertTrue(payload["access_token"])
        self.assertTrue(payload["refresh_token"])

        decoded_token = decode_token(payload["access_token"])
        self.assertEqual(decoded_token["sub"], str(self.daniel_user.id))

    def test_invalid_credentials_return_401(self) -> None:
        response = self._login("daniel@correo.com", "wrong-password")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "Invalid email or password."})

    def test_protected_route_requires_a_token(self) -> None:
        response = self.client.get("/api/habits")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"msg": "Missing Authorization Header"})

    def test_catalog_endpoint_returns_seeded_habits(self) -> None:
        login = self._login("daniel@correo.com", "daniel-password").get_json()

        response = self.client.get(
            "/api/habitos",
            headers=self._auth_headers(login["access_token"]),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertEqual({habit["name"] for habit in payload}, {"Meditar 5-10 min", "Leer 20 min"})
        self.assertEqual({habit["difficulty"] for habit in payload}, {"facil", "media"})

    def test_habits_are_scoped_to_the_authenticated_user(self) -> None:
        daniel_login = self._login("daniel@correo.com", "daniel-password").get_json()
        gustavo_login = self._login("gustavo@correo.com", "gustavo-password").get_json()

        daniel_response = self.client.get(
            "/api/mis-habitos",
            headers=self._auth_headers(daniel_login["access_token"]),
        )
        gustavo_response = self.client.get(
            "/api/habits",
            headers=self._auth_headers(gustavo_login["access_token"]),
        )

        self.assertEqual(daniel_response.status_code, 200)
        self.assertEqual(gustavo_response.status_code, 200)

        daniel_habits = daniel_response.get_json()
        gustavo_habits = gustavo_response.get_json()

        self.assertEqual({habit["user_id"] for habit in daniel_habits}, {self.daniel_user.id})
        self.assertEqual({habit["name"] for habit in daniel_habits}, {"Meditar 5-10 min"})

        self.assertEqual({habit["user_id"] for habit in gustavo_habits}, {self.gustavo_user.id})
        self.assertEqual({habit["name"] for habit in gustavo_habits}, {"Leer 20 min"})

    def test_assign_habit_creates_user_relationship(self) -> None:
        login = self._login("daniel@correo.com", "daniel-password").get_json()

        response = self.client.post(
            "/api/habitos_usuario",
            json={"habito_id": self.leer.id},
            headers=self._auth_headers(login["access_token"]),
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()

        self.assertEqual(payload["catalog_habit_id"], self.leer.id)
        self.assertEqual(payload["name"], "Leer 20 min")

        active_assignments = UserHabit.query.filter_by(usuario_id=self.daniel_user.id, activo=True).all()
        self.assertEqual(len(active_assignments), 2)

    def test_assign_habit_accepts_optional_overrides(self) -> None:
        login = self._login("daniel@correo.com", "daniel-password").get_json()

        response = self.client.post(
            "/api/habits",
            json={
                "habito_id": self.leer.id,
                "custom_name": "Leer ficción",
                "description": "Antes de dormir",
                "validation_type": "texto",
                "frequency": "weekly",
                "target_quantity": 20,
                "target_unit": "paginas",
                "target_duration": 30,
            },
            headers=self._auth_headers(login["access_token"]),
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["name"], "Leer ficción")
        self.assertEqual(payload["custom_name"], "Leer ficción")
        self.assertEqual(payload["description"], "Antes de dormir")
        self.assertEqual(payload["custom_description"], "Antes de dormir")
        self.assertEqual(payload["validation_type"], "texto")
        self.assertEqual(payload["frequency"], "weekly")
        self.assertEqual(payload["target_quantity"], 20)
        self.assertEqual(payload["target_unit"], "paginas")
        self.assertEqual(payload["target_duration"], 30)
        self.assertEqual(payload["habit_type"], "time")

    def test_duplicate_active_assignment_returns_409(self) -> None:
        login = self._login("daniel@correo.com", "daniel-password").get_json()

        response = self.client.post(
            "/api/habitos_usuario",
            json={"habito_id": self.meditar.id},
            headers=self._auth_headers(login["access_token"]),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json(),
            {"error": "This habit is already active for the user."},
        )

    def test_award_xp_saves_log_correctly(self) -> None:
        award_xp(self.daniel_user.id, 50, "validation")
        
        log_entry = XpLog.query.filter_by(user_id=self.daniel_user.id).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.cantidad, 50)
        self.assertEqual(log_entry.razon, "validation")

    def test_get_habit_detail_returns_user_scoped_payload(self) -> None:
        login = self._login("daniel@correo.com", "daniel-password").get_json()

        response = self.client.get(
            f"/api/habits/{self.daniel_habit.id}",
            headers=self._auth_headers(login["access_token"]),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["id"], self.daniel_habit.id)
        self.assertEqual(payload["catalog_habit_id"], self.meditar.id)
        self.assertEqual(payload["name"], "Meditar 5-10 min")

    def test_update_habit_persists_user_overrides(self) -> None:
        login = self._login("daniel@correo.com", "daniel-password").get_json()

        response = self.client.put(
            f"/api/habits/{self.daniel_habit.id}",
            json={
                "custom_name": "Meditación profunda",
                "description": "10 minutos sin interrupciones",
                "validation_type": "texto",
                "frequency": "weekly",
                "target_quantity": 3,
                "target_unit": "sesiones",
                "target_duration": 10,
            },
            headers=self._auth_headers(login["access_token"]),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["name"], "Meditación profunda")
        self.assertEqual(payload["custom_name"], "Meditación profunda")
        self.assertEqual(payload["description"], "10 minutos sin interrupciones")
        self.assertEqual(payload["custom_description"], "10 minutos sin interrupciones")
        self.assertEqual(payload["validation_type"], "texto")
        self.assertEqual(payload["frequency"], "weekly")
        self.assertEqual(payload["target_quantity"], 3)
        self.assertEqual(payload["target_unit"], "sesiones")
        self.assertEqual(payload["target_duration"], 10)

    def test_update_habit_allows_clearing_overrides(self) -> None:
        self.daniel_habit.nombre_personalizado = "Nombre temporal"
        self.daniel_habit.descripcion_personalizada = "Descripcion temporal"
        self.daniel_habit.tipo_validacion = "texto"
        self.daniel_habit.frecuencia = "weekly"
        self.daniel_habit.cantidad_objetivo = 4
        self.daniel_habit.unidad_objetivo = "vasos"
        self.daniel_habit.duracion_objetivo_minutos = 15
        db.session.commit()

        login = self._login("daniel@correo.com", "daniel-password").get_json()

        response = self.client.put(
            f"/api/habits/{self.daniel_habit.id}",
            json={
                "custom_name": None,
                "description": None,
                "validation_type": None,
                "frequency": None,
                "target_quantity": None,
                "target_unit": None,
                "target_duration": None,
            },
            headers=self._auth_headers(login["access_token"]),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["custom_name"], None)
        self.assertEqual(payload["custom_description"], None)
        self.assertEqual(payload["name"], "Meditar 5-10 min")
        self.assertEqual(payload["description"], "Relajación mental")
        self.assertEqual(payload["validation_type"], "tiempo")
        self.assertEqual(payload["frequency"], "daily")
        self.assertEqual(payload["target_quantity"], None)
        self.assertEqual(payload["target_unit"], None)
        self.assertEqual(payload["target_duration"], None)

    def test_refresh_returns_new_access_token_for_valid_refresh_token(self) -> None:
        login_payload = self._login("daniel@correo.com", "daniel-password").get_json()
        refresh_token = login_payload["refresh_token"]

        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("access_token", payload)
        self.assertNotEqual(payload["access_token"], login_payload["access_token"])

    def test_refresh_rejects_access_token_used_as_refresh_token(self) -> None:
        login_payload = self._login("daniel@correo.com", "daniel-password").get_json()
        access_token = login_payload["access_token"]

        response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token},
        )

        self.assertEqual(response.status_code, 401)

    def test_refresh_rejects_missing_token(self) -> None:
        response = self.client.post("/api/auth/refresh", json={})
        self.assertEqual(response.status_code, 400)

    def test_logout_revokes_access_token(self) -> None:
        login_payload = self._login("daniel@correo.com", "daniel-password").get_json()
        access_token = login_payload["access_token"]
        headers = self._auth_headers(access_token)

        logout_response = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout_response.status_code, 200)

        # Token must now be rejected on protected routes
        protected_response = self.client.get("/api/habits", headers=headers)
        self.assertEqual(protected_response.status_code, 401)

    def test_revoked_token_rejected_after_logout(self) -> None:
        login_payload = self._login("daniel@correo.com", "daniel-password").get_json()
        headers = self._auth_headers(login_payload["access_token"])

        # Confirm token works before logout
        before = self.client.get("/api/habits", headers=headers)
        self.assertEqual(before.status_code, 200)

        self.client.post("/api/auth/logout", headers=headers)

        # Confirm token is rejected after logout
        after = self.client.get("/api/habits", headers=headers)
        self.assertEqual(after.status_code, 401)

    def test_logout_requires_valid_token(self) -> None:
        response = self.client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        self.assertEqual(response.status_code, 422)

    def test_refreshed_token_works_on_protected_routes(self) -> None:
        login_payload = self._login("daniel@correo.com", "daniel-password").get_json()

        refresh_response = self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": login_payload["refresh_token"]},
        )
        new_token = refresh_response.get_json()["access_token"]

        response = self.client.get(
            "/api/habits",
            headers=self._auth_headers(new_token),
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
