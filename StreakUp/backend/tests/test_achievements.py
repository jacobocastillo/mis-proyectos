"""
Achievement system tests.

Covers:
- Achievement catalog seeding (idempotency)
- Awarding first_validation after first approved validation
- Awarding streak_7 when current streak reaches 7
- Awarding completions_30 after 30 completed checkins
- No double-awarding (idempotency of evaluate_and_award)
- XP bonus is added to user total when achievement is granted
- evaluate_and_award integration with full validate_habit flow
"""

import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models.achievement import Achievement, UserAchievement
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog
from app.services.achievement_service import (
    evaluate_and_award,
    get_all_achievements,
    get_user_achievements,
    seed_achievements,
)
from app.services.validation_service import validate_habit


def _make_config(name: str):
    return type(
        name,
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


class AchievementTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(_make_config("AchievementTestConfig"))
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed catalog (app factory already calls this, but call explicitly to verify)
        seed_achievements()

        # Create test fixtures
        category = Category(nombre="Salud", descripcion="Hábitos de salud")
        db.session.add(category)
        db.session.commit()

        self.user = User(username="achiever", email="achiever@streakup.com", role="user")
        self.user.set_password("test-password")
        db.session.add(self.user)
        db.session.commit()

        self.habit = Habit(
            categoria_id=category.id,
            nombre="Ejercicio 30 min",
            descripcion="Actividad física diaria",
            dificultad="media",
            xp_base=10,
            tipo_validacion="foto",
            frecuencia="daily",
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

    # ------------------------------------------------------------------
    # Catalog / seeding
    # ------------------------------------------------------------------

    def test_seed_achievements_creates_catalog_rows(self) -> None:
        count = Achievement.query.count()
        self.assertGreaterEqual(count, 3)
        keys = {a.key for a in Achievement.query.all()}
        self.assertIn("first_validation", keys)
        self.assertIn("streak_7", keys)
        self.assertIn("completions_30", keys)

    def test_seed_achievements_is_idempotent(self) -> None:
        before = Achievement.query.count()
        seed_achievements()
        after = Achievement.query.count()
        self.assertEqual(before, after)

    # ------------------------------------------------------------------
    # first_validation
    # ------------------------------------------------------------------

    def test_first_validation_achievement_awarded_on_first_approval(self) -> None:
        with patch(
            "app.services.validation_service.analyze_habit_image",
            return_value={"valido": True, "razon": "ok", "confianza": 0.9},
        ):
            result = validate_habit(self.user.id, self.user_habit.id, {"image_base64": "img-data"})

        self.assertIn("new_achievements", result)
        keys = [a["key"] for a in result["new_achievements"]]
        self.assertIn("first_validation", keys)

        # Verify DB record
        ua = (
            UserAchievement.query.join(Achievement)
            .filter(
                UserAchievement.user_id == self.user.id,
                Achievement.key == "first_validation",
            )
            .first()
        )
        self.assertIsNotNone(ua)

    def test_first_validation_xp_bonus_added_to_user(self) -> None:
        achievement = Achievement.query.filter_by(key="first_validation").one()

        with patch(
            "app.services.validation_service.analyze_habit_image",
            return_value={"valido": True, "razon": "ok", "confianza": 0.9},
        ):
            result = validate_habit(self.user.id, self.user_habit.id, {"image_base64": "img-data"})

        db.session.refresh(self.user)
        # base xp (habit.xp_base * 1.5 = 15) + bonus
        expected_xp = result["xp_ganado"] + achievement.xp_bonus
        self.assertEqual(self.user.total_xp, expected_xp)

    def test_first_validation_not_double_awarded(self) -> None:
        """Run evaluate_and_award twice; achievement should appear only once."""
        # Manually create an approved validation
        log = ValidationLog(
            habitousuario_id=self.user_habit.id,
            tipo_validacion="foto",
            status="approved",
            validado=True,
        )
        db.session.add(log)
        db.session.commit()

        first_call = evaluate_and_award(self.user.id, current_streak=1)
        second_call = evaluate_and_award(self.user.id, current_streak=1)

        self.assertEqual(len([a for a in first_call if a["key"] == "first_validation"]), 1)
        self.assertEqual(len([a for a in second_call if a["key"] == "first_validation"]), 0)

        total_ua = UserAchievement.query.filter_by(user_id=self.user.id).count()
        self.assertEqual(total_ua, 1)

    # ------------------------------------------------------------------
    # streak_7
    # ------------------------------------------------------------------

    def test_streak_7_not_awarded_below_threshold(self) -> None:
        awarded = evaluate_and_award(self.user.id, current_streak=6)
        keys = [a["key"] for a in awarded]
        self.assertNotIn("streak_7", keys)

    def test_streak_7_awarded_at_threshold(self) -> None:
        awarded = evaluate_and_award(self.user.id, current_streak=7)
        keys = [a["key"] for a in awarded]
        self.assertIn("streak_7", keys)

    def test_streak_7_awarded_above_threshold(self) -> None:
        awarded = evaluate_and_award(self.user.id, current_streak=30)
        keys = [a["key"] for a in awarded]
        self.assertIn("streak_7", keys)

    # ------------------------------------------------------------------
    # completions_30
    # ------------------------------------------------------------------

    def test_completions_30_not_awarded_below_threshold(self) -> None:
        for i in range(29):
            ci = CheckIn(
                habitousuario_id=self.user_habit.id,
                fecha=date.today() - timedelta(days=i + 1),
                completado=True,
                xp_ganado=10,
            )
            db.session.add(ci)
        db.session.commit()

        awarded = evaluate_and_award(self.user.id, current_streak=0)
        keys = [a["key"] for a in awarded]
        self.assertNotIn("completions_30", keys)

    def test_completions_30_awarded_at_threshold(self) -> None:
        for i in range(30):
            ci = CheckIn(
                habitousuario_id=self.user_habit.id,
                fecha=date.today() - timedelta(days=i + 1),
                completado=True,
                xp_ganado=10,
            )
            db.session.add(ci)
        db.session.commit()

        awarded = evaluate_and_award(self.user.id, current_streak=0)
        keys = [a["key"] for a in awarded]
        self.assertIn("completions_30", keys)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def test_get_all_achievements_returns_catalog_with_earned_flag(self) -> None:
        result = get_all_achievements(self.user.id)
        self.assertGreaterEqual(len(result), 3)
        for entry in result:
            self.assertIn("earned", entry)
            self.assertFalse(entry["earned"])  # none earned yet

    def test_get_user_achievements_empty_initially(self) -> None:
        result = get_user_achievements(self.user.id)
        self.assertEqual(result, [])

    def test_get_user_achievements_returns_earned_after_award(self) -> None:
        evaluate_and_award(self.user.id, current_streak=7)
        result = get_user_achievements(self.user.id)
        keys = [r["achievement"]["key"] for r in result]
        self.assertIn("streak_7", keys)

    def test_get_all_achievements_marks_earned_correctly(self) -> None:
        evaluate_and_award(self.user.id, current_streak=7)
        all_achievements = get_all_achievements(self.user.id)
        for entry in all_achievements:
            if entry["key"] == "streak_7":
                self.assertTrue(entry["earned"])
            else:
                self.assertFalse(entry["earned"])


class AchievementXpBonusTestCase(unittest.TestCase):
    """Verify XP bonus accounting when achievements fire."""

    def setUp(self) -> None:
        self.app = create_app(_make_config("AchievementXpConfig"))
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        seed_achievements()

        self.user = User(username="xpuser", email="xp@test.com", role="user")
        self.user.set_password("pw")
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_streak_7_bonus_added_to_xp_log(self) -> None:
        achievement = Achievement.query.filter_by(key="streak_7").first()
        self.assertIsNotNone(achievement)

        evaluate_and_award(self.user.id, current_streak=7)
        db.session.refresh(self.user)

        # XP log should contain the bonus amount
        total_logged = sum(log.cantidad for log in XpLog.query.all())
        self.assertEqual(total_logged, achievement.xp_bonus)
        self.assertEqual(self.user.total_xp, achievement.xp_bonus)


if __name__ == "__main__":
    unittest.main()
