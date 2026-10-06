import os
import tempfile
import unittest

from app import create_app
from app.extensions import db
from app.models.habit import Category, Habit
from app.models.user import User
from app.services.catalog_bootstrap_service import seed_catalog


EXPECTED_CATALOG = (
    ("Beber agua", "photo", "quantity_liters", 20, 0, 20),
    ("Comida saludable", "photo", "boolean", 25, 0, 25),
    ("Ejercicio", "time", "minutes", 0, 1, 60),
    ("Meditar", "time", "minutes", 10, 1, 25),
    ("Tarea clave", "text_ai", "boolean", 30, 0, 30),
    ("Empezar antes de X hora", "check", "boolean", 20, 0, 20),
    ("Leer", "time", "minutes", 0, 1, 30),
    ("Practicar idioma", "text_ai", "boolean", 25, 0, 25),
    ("Trabajo profundo", "time", "minutes", 0, 1, 60),
    ("Escribir diario", "text_ai", "boolean", 20, 0, 20),
    ("Estudiar", "time", "minutes", 0, 1, 45),
)


class PointACatalogTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "point-a-catalog.db")
        self.config = type(
            "PointACatalogConfig",
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

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _create_user_and_headers(self) -> dict[str, str]:
        user = User(username="Daniel", email="daniel@correo.com", role="user")
        user.set_password("daniel-password")
        db.session.add(user)
        db.session.commit()

        response = self.client.post(
            "/api/auth/login",
            json={"email": "daniel@correo.com", "password": "daniel-password"},
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.get_json()['access_token']}"}

    def test_seed_catalog_creates_exact_point_a_defaults(self) -> None:
        summary = seed_catalog()

        self.assertEqual(summary["habits_created"], 11)
        self.assertEqual(Habit.query.filter_by(activo=True).count(), 11)
        self.assertEqual(Habit.query.count(), 11)

        rows = [
            (
                habit.nombre,
                habit.tipo_validacion,
                habit.meta_type,
                habit.xp_base,
                habit.xp_rate,
                habit.max_xp_per_day,
            )
            for habit in Habit.query.filter_by(activo=True).order_by(Habit.id).all()
        ]
        self.assertEqual(set(rows), set(EXPECTED_CATALOG))

    def test_seed_catalog_is_idempotent_and_hides_legacy_extras(self) -> None:
        db.session.add(Category(id=99, nombre="Legacy", descripcion="Old defaults"))
        db.session.add(
            Habit(
                id=99,
                categoria_id=99,
                nombre="Legacy extra",
                descripcion="Preserved hidden row",
                dificultad="facil",
                xp_base=5,
                tipo_validacion="foto",
                meta_type="boolean",
                xp_rate=0,
                max_xp_per_day=5,
                activo=True,
            )
        )
        db.session.commit()

        first = seed_catalog()
        second = seed_catalog()

        self.assertEqual(first["habits_created"], 11)
        self.assertEqual(second["habits_created"], 0)
        self.assertEqual(Habit.query.count(), 12)
        self.assertEqual(Habit.query.filter_by(activo=True).count(), 11)
        self.assertFalse(db.session.get(Habit, 99).activo)

    def test_catalog_endpoint_returns_only_active_point_a_metadata(self) -> None:
        db.session.add(Category(id=99, nombre="Legacy", descripcion="Old defaults"))
        db.session.add(
            Habit(
                id=99,
                categoria_id=99,
                nombre="Legacy extra",
                descripcion="Preserved hidden row",
                dificultad="facil",
                xp_base=5,
                tipo_validacion="foto",
                meta_type="boolean",
                xp_rate=0,
                max_xp_per_day=5,
                activo=True,
            )
        )
        db.session.commit()
        seed_catalog()

        response = self.client.get(
            "/api/habits/catalog",
            headers=self._create_user_and_headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()

        self.assertEqual(len(payload), 11)
        self.assertEqual([row["name"] for row in payload], [row[0] for row in EXPECTED_CATALOG])
        self.assertNotIn("Legacy extra", {row["name"] for row in payload})

        by_name = {row["name"]: row for row in payload}
        for name, validation_type, meta_type, xp_base, xp_rate, max_xp_per_day in EXPECTED_CATALOG:
            row = by_name[name]
            self.assertEqual(row["validation_type"], validation_type)
            self.assertEqual(row["meta_type"], meta_type)
            self.assertEqual(row["xp_base"], xp_base)
            self.assertEqual(row["xp_rate"], xp_rate)
            self.assertEqual(row["max_xp_per_day"], max_xp_per_day)
            self.assertTrue(row["active"])


if __name__ == "__main__":
    unittest.main()
