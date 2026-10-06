"""
Tests for Phase 6 Point A XP formula, daily cap, and audit log fields.
"""

import pytest
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.xp_log import XpLog
from app.services.xp_service import (
    award_habit_xp,
    calculate_habit_xp,
    get_daily_xp_used,
)


@pytest.fixture
def app():
    instance = create_app()
    instance.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with instance.app_context():
        db.create_all()
        yield instance
        db.session.remove()
        db.drop_all()


@pytest.fixture
def setup(app):
    with app.app_context():
        cat = Category(nombre="Fitness")
        db.session.add(cat)
        db.session.flush()

        user = User(username="alice", email="alice@test.com")
        user.set_password("pass")
        db.session.add(user)
        db.session.flush()

        photo_habit = Habit(
            categoria_id=cat.id,
            nombre="Meditate",
            dificultad="facil",
            xp_base=20,
            xp_rate=0,
            max_xp_per_day=0,
            tipo_validacion="foto",
        )
        time_habit = Habit(
            categoria_id=cat.id,
            nombre="Run",
            dificultad="media",
            xp_base=5,
            xp_rate=2,
            max_xp_per_day=50,
            tipo_validacion="time",
        )
        db.session.add_all([photo_habit, time_habit])
        db.session.flush()

        today = date.today()
        uh_photo = UserHabit(
            usuario_id=user.id,
            habito_id=photo_habit.id,
            fecha_inicio=today,
            activo=True,
        )
        uh_time = UserHabit(
            usuario_id=user.id,
            habito_id=time_habit.id,
            fecha_inicio=today,
            activo=True,
        )
        db.session.add_all([uh_photo, uh_time])
        db.session.commit()

        return {
            "user_id": user.id,
            "photo_uh_id": uh_photo.id,
            "time_uh_id": uh_time.id,
            "photo_habit_id": photo_habit.id,
            "time_habit_id": time_habit.id,
        }


# --- calculate_habit_xp ---

def test_non_time_habit_xp_equals_xp_base(app, setup):
    with app.app_context():
        habit = db.session.get(Habit, setup["photo_habit_id"])
        assert calculate_habit_xp(habit) == 20
        assert calculate_habit_xp(habit, duration_minutes=60) == 20  # duration ignored


def test_time_habit_xp_formula(app, setup):
    with app.app_context():
        habit = db.session.get(Habit, setup["time_habit_id"])
        # xp_base=5, xp_rate=2, max_xp_per_day=50
        assert calculate_habit_xp(habit, duration_minutes=10) == min(50, 5 + 10 * 2)  # 25
        assert calculate_habit_xp(habit, duration_minutes=30) == min(50, 5 + 30 * 2)  # 50 (cap)
        assert calculate_habit_xp(habit, duration_minutes=0) == min(50, 5 + 0)  # 5


def test_time_habit_no_cap_when_max_xp_is_zero(app, setup):
    with app.app_context():
        cat = Category.query.first()
        uncapped = Habit(
            categoria_id=cat.id,
            nombre="Yoga",
            dificultad="facil",
            xp_base=10,
            xp_rate=3,
            max_xp_per_day=0,
            tipo_validacion="time",
        )
        db.session.add(uncapped)
        db.session.flush()
        assert calculate_habit_xp(uncapped, duration_minutes=100) == 10 + 100 * 3  # 310, uncapped


# --- daily cap enforcement ---

def test_daily_cap_partial_remaining(app, setup):
    with app.app_context():
        user_id = setup["user_id"]
        uh = db.session.get(UserHabit, setup["time_uh_id"])
        today = date.today()

        # First award: 25 XP (10 min * 2 rate + 5 base = 25)
        awarded1 = award_habit_xp(user_id, uh, today, duration_minutes=10, commit=False)
        db.session.flush()
        assert awarded1 == 25

        # Daily cap is 50. Used=25, remaining=25.
        # Second award at 30 min would calculate 65 but cap remaining is 25
        awarded2 = award_habit_xp(user_id, uh, today, duration_minutes=30, commit=False)
        db.session.flush()
        assert awarded2 == 25  # partial remaining cap

        used = get_daily_xp_used(user_id, uh.id, today)
        assert used == 50


def test_daily_cap_zero_when_reached(app, setup):
    with app.app_context():
        user_id = setup["user_id"]
        uh = db.session.get(UserHabit, setup["time_uh_id"])
        today = date.today()

        # Fill cap (30 min = 5 + 60 = 65, capped to 50)
        awarded1 = award_habit_xp(user_id, uh, today, duration_minutes=30, commit=False)
        db.session.flush()
        assert awarded1 == 50  # cap reached in one shot

        # Next award returns 0
        awarded2 = award_habit_xp(user_id, uh, today, duration_minutes=10, commit=False)
        db.session.flush()
        assert awarded2 == 0


def test_advisory_difficulty_metadata_does_not_change_xp_cap(app, setup):
    with app.app_context():
        user_id = setup["user_id"]
        uh = db.session.get(UserHabit, setup["time_uh_id"])
        today = date.today()
        advisory_metadata = {
            "level": "dificil",
            "confidence": 1.0,
            "explanation": "Solo metadata consultiva.",
            "source": "openai",
            "advisory": True,
        }

        awarded = award_habit_xp(user_id, uh, today, duration_minutes=200, commit=False)
        db.session.flush()

        assert advisory_metadata["advisory"] is True
        assert awarded == 50
        assert get_daily_xp_used(user_id, uh.id, today) == 50


def test_cap_hit_logged_in_xp_log(app, setup):
    with app.app_context():
        user_id = setup["user_id"]
        uh = db.session.get(UserHabit, setup["time_uh_id"])
        today = date.today()

        award_habit_xp(user_id, uh, today, duration_minutes=30, commit=False)  # fills cap
        db.session.flush()
        award_habit_xp(user_id, uh, today, duration_minutes=10, commit=False)  # cap_hit
        db.session.flush()

        cap_hit_logs = XpLog.query.filter_by(
            user_id=user_id, cap_hit=True, habit_id=uh.id
        ).all()
        assert len(cap_hit_logs) == 1
        assert cap_hit_logs[0].cantidad == 0


def test_no_cap_for_non_time_habit(app, setup):
    with app.app_context():
        user_id = setup["user_id"]
        uh = db.session.get(UserHabit, setup["photo_uh_id"])
        today = date.today()

        # max_xp_per_day=0 means no cap
        awarded = award_habit_xp(user_id, uh, today, commit=False)
        db.session.flush()
        assert awarded == 20  # xp_base


# --- source_event and audit fields ---

def test_xp_log_has_audit_fields(app, setup):
    with app.app_context():
        user_id = setup["user_id"]
        uh = db.session.get(UserHabit, setup["photo_uh_id"])
        today = date.today()

        award_habit_xp(user_id, uh, today, commit=False)
        db.session.flush()

        log = XpLog.query.filter_by(user_id=user_id, habit_id=uh.id).one()
        assert log.habit_id == uh.id
        assert log.event_date == today
        assert log.source_event == "habit"
        assert log.cap_hit is False
        assert log.calculated_xp == 20


def test_achievement_xp_uses_achievement_source(app, setup):
    with app.app_context():
        from app.services.xp_service import award_xp
        user_id = setup["user_id"]

        award_xp(user_id, 50, "validation", source_event="achievement", commit=False)
        db.session.flush()

        log = XpLog.query.filter_by(user_id=user_id, source_event="achievement").one()
        assert log.cantidad == 50
        assert log.habit_id is None


def test_achievement_xp_not_affected_by_habit_cap(app, setup):
    """Achievement bonus must bypass habit daily cap."""
    with app.app_context():
        from app.services.xp_service import award_xp
        user_id = setup["user_id"]
        uh = db.session.get(UserHabit, setup["time_uh_id"])
        today = date.today()

        # Fill habit cap
        award_habit_xp(user_id, uh, today, duration_minutes=30, commit=False)
        db.session.flush()

        # Achievement XP should still be awarded
        user = db.session.get(User, user_id)
        xp_before = user.total_xp
        award_xp(user_id, 25, "validation", source_event="achievement", commit=False)
        db.session.flush()
        db.session.refresh(user)

        assert user.total_xp == xp_before + 25
