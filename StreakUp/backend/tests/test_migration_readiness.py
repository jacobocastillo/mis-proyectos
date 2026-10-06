import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models.user import User


class MigrationReadinessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "migration-readiness.db")
        self.config = type(
            "MigrationReadinessConfig",
            (),
            {
                "SECRET_KEY": "test-secret-key-with-32-characters!!",
                "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars!!",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": True,
                "ENVIRONMENT": "test",
            },
        )

        self.app = create_app(self.config)
        self.runner = self.app.test_cli_runner()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        db.session.remove()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _create_legacy_sqlite_source(self) -> str:
        source_path = os.path.join(self.temp_dir.name, "legacy-source.db")
        with sqlite3.connect(source_path) as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    total_xp INTEGER NOT NULL DEFAULT 0,
                    level INTEGER NOT NULL DEFAULT 1,
                    xp_in_level INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    descripcion TEXT
                );

                CREATE TABLE habitos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    categoria_id INTEGER NOT NULL,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    dificultad TEXT NOT NULL CHECK (dificultad IN ('facil','media','dificil')),
                    xp_base INTEGER NOT NULL CHECK (xp_base >= 0),
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
                );

                CREATE TABLE habitos_usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    habito_id INTEGER NOT NULL,
                    fecha_inicio DATE NOT NULL,
                    fecha_fin DATE,
                    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
                    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (habito_id) REFERENCES habitos(id) ON DELETE CASCADE,
                    UNIQUE (usuario_id, habito_id, activo)
                );

                CREATE TABLE registro_habitos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habitousuario_id INTEGER NOT NULL,
                    fecha DATE NOT NULL,
                    completado INTEGER NOT NULL DEFAULT 1 CHECK (completado IN (0,1)),
                    xp_ganado INTEGER NOT NULL DEFAULT 0 CHECK (xp_ganado >= 0),
                    FOREIGN KEY (habitousuario_id) REFERENCES habitos_usuario(id) ON DELETE CASCADE,
                    UNIQUE (habitousuario_id, fecha)
                );

                CREATE TABLE validaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    habitousuario_id INTEGER NOT NULL,
                    tipo_validacion TEXT NOT NULL CHECK (tipo_validacion IN ('foto','tiempo','manual')),
                    evidencia TEXT,
                    tiempo_segundos INTEGER,
                    validado INTEGER NOT NULL DEFAULT 0 CHECK (validado IN (0,1)),
                    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (habitousuario_id) REFERENCES habitos_usuario(id) ON DELETE CASCADE
                );

                CREATE TABLE xp_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL,
                    fuente TEXT NOT NULL CHECK (fuente IN ('checkin','checkin_undo','validation')),
                    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE niveles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    xp_minimo INTEGER NOT NULL,
                    xp_maximo INTEGER NOT NULL,
                    recompensa TEXT,
                    descripcion TEXT,
                    CHECK (xp_minimo < xp_maximo)
                );
                """
            )
            connection.executescript(
                """
                INSERT INTO categorias (id, nombre, descripcion) VALUES
                (1, 'Salud y Bienestar', 'Habitos fisicos y mentales');

                INSERT INTO habitos (id, categoria_id, nombre, descripcion, dificultad, xp_base) VALUES
                (1, 1, 'Beber 2L de agua', 'Mantener hidratacion diaria', 'facil', 10);

                INSERT INTO users (id, username, email, password_hash, role, total_xp, level, xp_in_level, created_at, updated_at) VALUES
                (1, 'Daniel', 'daniel@example.com', 'hash-1', 'user', 999, 4, 249, '2026-04-01 10:00:00', '2026-04-01 10:00:00');

                INSERT INTO habitos_usuario (id, usuario_id, habito_id, fecha_inicio, activo, fecha_creacion) VALUES
                (1, 1, 1, '2026-04-01', 1, '2026-04-01 10:05:00');

                INSERT INTO registro_habitos (id, habitousuario_id, fecha, completado, xp_ganado) VALUES
                (1, 1, '2026-04-02', 1, 10);

                INSERT INTO validaciones (id, habitousuario_id, tipo_validacion, evidencia, tiempo_segundos, validado, fecha) VALUES
                (1, 1, 'foto', 'evidence', NULL, 1, '2026-04-02 10:10:00');

                INSERT INTO xp_logs (id, usuario_id, cantidad, fuente, fecha) VALUES
                (1, 1, 10, 'checkin', '2026-04-02 10:10:00'),
                (2, 1, 15, 'validation', '2026-04-02 10:11:00');

                INSERT INTO niveles (id, nombre, xp_minimo, xp_maximo, recompensa, descripcion) VALUES
                (1, 'Bronze', 0, 249, 'badge', 'base level');
                """
            )
        return source_path

    def test_db_upgrade_creates_expected_constraints(self) -> None:
        result = self.runner.invoke(args=["db", "upgrade"])
        self.assertEqual(result.exit_code, 0, msg=result.output)

        inspector = inspect(db.engine)

        self.assertTrue(
            {
                "users",
                "xp_logs",
                "categorias",
                "habitos",
                "habitos_usuario",
                "registro_habitos",
                "validaciones",
                "niveles",
                "pomodoro_sessions",
                "shared_streak_groups",
                "shared_streak_memberships",
                "token_blocklist",
            }.issubset(set(inspector.get_table_names()))
        )

        user_uniques = {
            tuple(constraint["column_names"]) for constraint in inspector.get_unique_constraints("users")
        }
        self.assertIn(("username",), user_uniques)
        self.assertIn(("email",), user_uniques)

        category_uniques = {
            tuple(constraint["column_names"])
            for constraint in inspector.get_unique_constraints("categorias")
        }
        self.assertIn(("nombre",), category_uniques)

        pomodoro_indexes = {index["name"] for index in inspector.get_indexes("pomodoro_sessions")}
        self.assertIn("idx_pomodoro_sessions_user_started", pomodoro_indexes)

        xp_checks = " ".join(
            constraint.get("sqltext", "") for constraint in inspector.get_check_constraints("xp_logs")
        )
        self.assertIn("checkin_undo", xp_checks)

        habit_columns = {column["name"] for column in inspector.get_columns("habitos")}
        self.assertTrue(
            {
                "tipo_validacion",
                "frecuencia",
                "cantidad_objetivo",
                "unidad_objetivo",
                "duracion_objetivo_minutos",
            }.issubset(habit_columns)
        )

        user_habit_columns = {column["name"] for column in inspector.get_columns("habitos_usuario")}
        self.assertTrue(
            {
                "nombre_personalizado",
                "descripcion_personalizada",
                "tipo_validacion",
                "frecuencia",
                "cantidad_objetivo",
                "unidad_objetivo",
                "duracion_objetivo_minutos",
                "fecha_actualizacion",
            }.issubset(user_habit_columns)
        )

        validation_checks = " ".join(
            constraint.get("sqltext", "") for constraint in inspector.get_check_constraints("validaciones")
        )
        self.assertIn("texto", validation_checks)
        self.assertIn("pending", validation_checks)

        validation_columns = {column["name"] for column in inspector.get_columns("validaciones")}
        self.assertIn("status", validation_columns)

        social_membership_columns = {
            column["name"] for column in inspector.get_columns("shared_streak_memberships")
        }
        self.assertTrue(
            {
                "group_id",
                "user_id",
                "user_habit_id",
                "status",
                "share_progress",
                "completed_days",
                "lost_at",
            }.issubset(social_membership_columns)
        )

        social_group_columns = {
            column["name"] for column in inspector.get_columns("shared_streak_groups")
        }
        self.assertTrue(
            {
                "habit_id",
                "winner_user_id",
                "max_participants",
                "start_date",
                "duration_days",
                "end_date",
                "group_status",
            }.issubset(social_group_columns)
        )

    def test_seed_sql_is_idempotent_on_sqlite(self) -> None:
        schema_path = Path(__file__).resolve().parents[2] / "data" / "db" / "schema.sql"
        seed_path = Path(__file__).resolve().parents[2] / "data" / "db" / "seed.sql"

        with sqlite3.connect(":memory:") as connection:
            connection.executescript(schema_path.read_text(encoding="utf-8"))
            connection.executescript(seed_path.read_text(encoding="utf-8"))
            connection.executescript(seed_path.read_text(encoding="utf-8"))

            categories = connection.execute("SELECT COUNT(*) FROM categorias").fetchone()[0]
            habits = connection.execute("SELECT COUNT(*) FROM habitos").fetchone()[0]

        self.assertEqual(categories, 3)
        self.assertEqual(habits, 12)

    def test_audit_legacy_sqlite_reports_optional_drift_and_xp_mismatch(self) -> None:
        legacy_path = self._create_legacy_sqlite_source()

        result = self.runner.invoke(args=["audit-legacy-sqlite", "--path", legacy_path])
        self.assertEqual(result.exit_code, 0, msg=result.output)

        payload = json.loads(result.output)
        self.assertIn("pomodoro_sessions", payload["missing_optional_tables"])
        self.assertIn("alembic_version", payload["missing_optional_tables"])
        self.assertEqual(payload["blocking_issues"], [])
        self.assertEqual(payload["row_counts"]["users"], 1)
        self.assertEqual(payload["row_counts"]["niveles"], 1)
        self.assertEqual(payload["xp_mismatches"][0]["stored_total_xp"], 999)
        self.assertEqual(payload["xp_mismatches"][0]["xp_logs_total"], 25)

    def test_migrate_command_imports_legacy_sqlite_and_recomputes_xp(self) -> None:
        legacy_path = self._create_legacy_sqlite_source()

        upgrade = self.runner.invoke(args=["db", "upgrade"])
        self.assertEqual(upgrade.exit_code, 0, msg=upgrade.output)

        result = self.runner.invoke(args=["migrate-sqlite-to-postgres", "--path", legacy_path])
        self.assertEqual(result.exit_code, 0, msg=result.output)

        payload = json.loads(result.output)
        self.assertEqual(payload["imported_counts"]["users"], 1)
        self.assertEqual(payload["imported_counts"]["pomodoro_sessions"], 0)
        self.assertEqual(payload["recomputed_users"], 1)

        user = db.session.get(User, 1)
        self.assertIsNotNone(user)
        self.assertEqual(user.total_xp, 25)
        self.assertEqual(user.level, 1)
        self.assertEqual(user.xp_in_level, 25)

        counts = {
            "categorias": db.session.execute(text("SELECT COUNT(*) FROM categorias")).scalar(),
            "habitos": db.session.execute(text("SELECT COUNT(*) FROM habitos")).scalar(),
            "habitos_usuario": db.session.execute(text("SELECT COUNT(*) FROM habitos_usuario")).scalar(),
            "registro_habitos": db.session.execute(text("SELECT COUNT(*) FROM registro_habitos")).scalar(),
            "validaciones": db.session.execute(text("SELECT COUNT(*) FROM validaciones")).scalar(),
            "xp_logs": db.session.execute(text("SELECT COUNT(*) FROM xp_logs")).scalar(),
            "niveles": db.session.execute(text("SELECT COUNT(*) FROM niveles")).scalar(),
        }
        self.assertEqual(counts, {
            "categorias": 1,
            "habitos": 1,
            "habitos_usuario": 1,
            "registro_habitos": 1,
            "validaciones": 1,
            "xp_logs": 2,
            "niveles": 1,
        })


if __name__ == "__main__":
    unittest.main()
