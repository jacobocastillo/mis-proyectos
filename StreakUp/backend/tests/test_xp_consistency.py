import hashlib
import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from sqlalchemy import func
from sqlalchemy.dialects import postgresql

from app import create_app
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog
from app.services.checkin_service import toggle_checkin
from app.services.stats_service import get_summary
from app.services.validation_service import validate_habit


class XpConsistencyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "xp-consistency.db")
        self.config = type(
            "XpConsistencyConfig",
            (),
            {
                "SECRET_KEY": "test-secret",
                "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "DEBUG": False,
                "TESTING": True,
                "ENVIRONMENT": "test",
                "OPENAI_API_KEY": "test-openai-key",
            },
        )

        self.app = create_app(self.config)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        category = Category(nombre="Salud y Bienestar", descripcion="Hábitos físicos y mentales")
        db.session.add(category)
        db.session.commit()

        self.user = User(username="Daniel", email="daniel@correo.com", role="user")
        self.user.set_password("daniel-password")
        db.session.add(self.user)
        db.session.commit()

        self.habit = Habit(
            categoria_id=category.id,
            nombre="Meditar 5-10 min",
            descripcion="Relajación mental",
            dificultad="facil",
            xp_base=10,
        )
        db.session.add(self.habit)
        db.session.commit()

        self.user_habit = UserHabit(
            usuario_id=self.user.id,
            habito_id=self.habit.id,
            fecha_inicio=date.today(),
            activo=True,
        )
        db.session.add(self.user_habit)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def test_validation_creates_photo_award_when_no_checkin_exists(self) -> None:
        with patch(
            "app.services.validation_service.analyze_habit_image",
            return_value={"valido": True, "razon": "evidencia valida", "confianza": 0.9},
        ):
            result = validate_habit(
                self.user.id,
                self.user_habit.id,
                {"image_base64": "image-base64"},
            )

        db.session.refresh(self.user)
        checkin = CheckIn.query.filter_by(habitousuario_id=self.user_habit.id).one()
        validation = ValidationLog.query.one()

        self.assertEqual(result["xp_ganado"], 10)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(checkin.xp_ganado, 10)
        self.assertEqual(self.user.total_xp, 10)
        self.assertEqual(sum(log.cantidad for log in XpLog.query.all()), 10)
        self.assertIsNotNone(validation.evidencia)
        self.assertEqual(validation.status, "approved")
        self.assertTrue(validation.validado)
        evidence = json.loads(validation.evidencia)
        self.assertEqual(evidence["confidence"], 0.9)
        self.assertEqual(
            evidence["image_sha256"],
            hashlib.sha256("image-base64".encode("utf-8")).hexdigest(),
        )
        self.assertEqual(evidence["mime_type"], "image/jpeg")
        self.assertEqual(evidence["provider"], "openai")
        self.assertEqual(evidence["reason"], "evidencia valida")
        self.assertEqual(evidence["validation_type"], "foto")
        self.assertEqual(evidence["xp_awarded"], 10)
        self.assertTrue(evidence["difficulty_recommendation"]["advisory"])
        self.assertEqual(evidence["feedback"]["context"]["xp_awarded"], 10)
        self.assertEqual(ValidationLog.query.count(), 1)

    def test_validation_day_filter_binds_postgres_date_param(self) -> None:
        statement = ValidationLog.query.filter(
            ValidationLog.habitousuario_id == self.user_habit.id,
            func.date(ValidationLog.fecha) == date.today(),
        ).statement
        compiled = statement.compile(dialect=postgresql.dialect())

        self.assertIn("date(validaciones.fecha) = %(date_1)s", str(compiled))
        self.assertEqual(compiled.binds["date_1"].type.python_type, date)

    def test_validation_after_existing_approved_progress_grants_only_missing_delta(self) -> None:
        approved_progress = CheckIn(
            habitousuario_id=self.user_habit.id,
            fecha=date.today(),
            completado=True,
            xp_ganado=10,
        )
        db.session.add(approved_progress)
        db.session.add(XpLog(user_id=self.user.id, cantidad=10, razon="validation"))
        self.user.total_xp = 10
        self.user.level = 1
        self.user.xp_in_level = 10
        db.session.commit()

        with patch(
            "app.services.validation_service.analyze_habit_image",
            return_value={"valido": True, "razon": "evidencia valida", "confianza": 0.95},
        ):
            result = validate_habit(
                self.user.id,
                self.user_habit.id,
                {"image_base64": "image-base64"},
            )

        db.session.refresh(self.user)
        checkin = CheckIn.query.filter_by(habitousuario_id=self.user_habit.id).one()
        log_amounts = [log.cantidad for log in XpLog.query.order_by(XpLog.id).all()]

        self.assertEqual(result["xp_ganado"], 0)
        self.assertEqual(checkin.xp_ganado, 10)
        self.assertEqual(self.user.total_xp, 10)
        self.assertEqual(log_amounts, [10])
        self.assertEqual(ValidationLog.query.count(), 1)

    def test_toggle_checkin_is_blocked_for_validation_backed_habits(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires validation"):
            toggle_checkin(self.user.id, self.user_habit.id)

        db.session.refresh(self.user)
        self.assertEqual(self.user.total_xp, 0)
        self.assertEqual(CheckIn.query.count(), 0)
        self.assertEqual(XpLog.query.count(), 0)

    def test_pending_validation_grants_no_progress_and_no_xp(self) -> None:
        pending = ValidationLog(
            habitousuario_id=self.user_habit.id,
            tipo_validacion="foto",
            status="pending",
            validado=False,
            evidencia=json.dumps({"provider": "openai"}),
        )
        db.session.add(pending)
        db.session.commit()

        summary = get_summary(self.user.id)

        self.assertEqual(summary["today_completed"], 0)
        self.assertEqual(summary["streak"], 0)
        self.assertEqual(self.user.total_xp, 0)
        self.assertEqual(CheckIn.query.count(), 0)
        self.assertEqual(XpLog.query.count(), 0)

    def test_rejected_validation_grants_nothing_and_resets_current_streak(self) -> None:
        yesterday = date.today() - timedelta(days=1)
        prior_progress = CheckIn(
            habitousuario_id=self.user_habit.id,
            fecha=yesterday,
            completado=True,
            xp_ganado=10,
        )
        db.session.add(prior_progress)
        db.session.add(XpLog(user_id=self.user.id, cantidad=10, razon="validation"))
        self.user.total_xp = 10
        self.user.level = 1
        self.user.xp_in_level = 10
        db.session.commit()

        with patch(
            "app.services.validation_service.analyze_habit_image",
            return_value={"valido": False, "razon": "evidencia invalida", "confianza": 0.2},
        ):
            result = validate_habit(
                self.user.id,
                self.user_habit.id,
                {"image_base64": "image-base64"},
            )

        db.session.refresh(self.user)
        validation = ValidationLog.query.order_by(ValidationLog.id.desc()).first()
        summary = get_summary(self.user.id)

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["xp_ganado"], 0)
        self.assertEqual(result["nueva_racha"], 0)
        self.assertIsNotNone(validation)
        self.assertEqual(validation.status, "rejected")
        self.assertFalse(validation.validado)
        self.assertEqual(self.user.total_xp, 10)
        self.assertEqual(CheckIn.query.count(), 1)
        self.assertEqual(XpLog.query.count(), 1)
        self.assertEqual(summary["today_completed"], 0)
        self.assertEqual(summary["streak"], 0)
        self.assertEqual(summary["validations_today"], 0)

    def test_duplicate_validation_attempt_same_day_is_rejected_before_double_count(self) -> None:
        with patch(
            "app.services.validation_service.analyze_habit_image",
            return_value={"valido": True, "razon": "evidencia valida", "confianza": 0.9},
        ):
            first_result = validate_habit(
                self.user.id,
                self.user_habit.id,
                {"image_base64": "image-base64"},
            )
            with self.assertRaisesRegex(ValueError, "Ya validaste este habito hoy"):
                validate_habit(
                    self.user.id,
                    self.user_habit.id,
                    {"image_base64": "image-base64"},
                )

        db.session.refresh(self.user)
        self.assertEqual(first_result["status"], "approved")
        self.assertEqual(self.user.total_xp, 10)
        self.assertEqual(CheckIn.query.count(), 1)
        self.assertEqual(ValidationLog.query.count(), 1)
        self.assertEqual(XpLog.query.count(), 1)

    def test_blocked_checkin_does_not_mutate_state_even_if_xp_writer_is_patched(self) -> None:
        with patch(
            "app.services.checkin_service.award_xp",
            side_effect=RuntimeError("xp write failed"),
        ):
            with self.assertRaisesRegex(ValueError, "requires validation"):
                toggle_checkin(self.user.id, self.user_habit.id)

        db.session.refresh(self.user)
        self.assertEqual(self.user.total_xp, 0)
        self.assertEqual(CheckIn.query.count(), 0)
        self.assertEqual(XpLog.query.count(), 0)

    def test_validation_rolls_back_when_xp_award_fails(self) -> None:
        with patch(
            "app.services.validation_service.analyze_habit_image",
            return_value={"valido": True, "razon": "evidencia valida", "confianza": 0.9},
        ), patch(
            "app.services.validation_service.award_habit_xp",
            side_effect=RuntimeError("xp write failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "xp write failed"):
                validate_habit(
                    self.user.id,
                    self.user_habit.id,
                    {"image_base64": "image-base64"},
                )

        db.session.refresh(self.user)
        self.assertEqual(self.user.total_xp, 0)
        self.assertEqual(CheckIn.query.count(), 0)
        # flush (not commit) before AI call means the whole transaction rolls back cleanly
        self.assertEqual(ValidationLog.query.count(), 0)
        self.assertEqual(XpLog.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
