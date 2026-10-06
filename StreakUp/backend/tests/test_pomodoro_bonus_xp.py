"""Tests for Pomodoro uninterrupted bonus XP (issue #41)."""

from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.models.habit import Category, Habit
from app.models.pomodoro_session import POMODORO_BONUS_XP
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.xp_log import XpLog
from app.services.pomodoro_service import (
    complete_session,
    create_session,
    interrupt_session,
)


@pytest.fixture
def app():
    app_instance = create_app()
    app_instance.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seeds(app):
    with app.app_context():
        user = User(username="bonususer", email="bonususer@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        cat = Category(nombre="Health")
        db.session.add(cat)
        db.session.commit()

        today = date.today()
        time_habit = Habit(
            nombre="Run",
            categoria_id=cat.id,
            tipo_validacion="tiempo",
            dificultad="media",
            xp_base=10,
            xp_rate=1,
            max_xp_per_day=50,
        )
        db.session.add(time_habit)
        db.session.commit()

        uh_time = UserHabit(
            usuario_id=user.id,
            habito_id=time_habit.id,
            tipo_validacion="tiempo",
            duracion_objetivo_minutos=30,
            activo=True,
            fecha_inicio=today,
        )
        db.session.add(uh_time)
        db.session.commit()

        return {"user_id": user.id, "uh_time_id": uh_time.id}


def _new_session(user_id, habit_id=None):
    return create_session(
        user_id,
        {
            "habit_id": habit_id,
            "study_minutes": 25,
            "break_minutes": 5,
            "cycles": 2,
        },
    )


def test_uninterrupted_session_earns_bonus_xp(app, seeds):
    with app.app_context():
        session = _new_session(seeds["user_id"])
        result = complete_session(session["id"], seeds["user_id"])

        assert result["bonus_xp"] == POMODORO_BONUS_XP
        bonus_log = XpLog.query.filter_by(razon="pomodoro_bonus").first()
        assert bonus_log is not None
        assert bonus_log.cantidad == POMODORO_BONUS_XP


def test_interrupted_session_earns_no_bonus_xp(app, seeds):
    with app.app_context():
        session = _new_session(seeds["user_id"])
        interrupt_session(session["id"], seeds["user_id"])
        result = complete_session(session["id"], seeds["user_id"])

        assert result["bonus_xp"] == 0
        assert XpLog.query.filter_by(razon="pomodoro_bonus").count() == 0


def test_multiple_interruptions_tracked_server_side(app, seeds):
    with app.app_context():
        session = _new_session(seeds["user_id"])
        interrupt_session(session["id"], seeds["user_id"])
        interrupt_session(session["id"], seeds["user_id"])
        interrupt_session(session["id"], seeds["user_id"])

        from app.models.pomodoro_session import PomodoroSession
        s = db.session.get(PomodoroSession, session["id"])
        assert s.interruption_count == 3


def test_bonus_xp_idempotent_on_repeated_complete(app, seeds):
    with app.app_context():
        session = _new_session(seeds["user_id"])
        first = complete_session(session["id"], seeds["user_id"])
        second = complete_session(session["id"], seeds["user_id"])

        assert first["bonus_xp"] == POMODORO_BONUS_XP
        assert second["xp_awarded"] == 0
        assert XpLog.query.filter_by(razon="pomodoro_bonus").count() == 1


def test_bonus_xp_awarded_without_habit(app, seeds):
    with app.app_context():
        session = _new_session(seeds["user_id"], habit_id=None)
        result = complete_session(session["id"], seeds["user_id"])

        assert result["bonus_xp"] == POMODORO_BONUS_XP


def test_interrupt_after_complete_is_ignored(app, seeds):
    with app.app_context():
        session = _new_session(seeds["user_id"])
        complete_session(session["id"], seeds["user_id"])
        interrupted = interrupt_session(session["id"], seeds["user_id"])

        from app.models.pomodoro_session import PomodoroSession
        s = db.session.get(PomodoroSession, session["id"])
        assert s.interruption_count == 0
        assert interrupted["interruption_count"] == 0


def test_interrupt_session_not_found_returns_none(app, seeds):
    with app.app_context():
        result = interrupt_session(99999, seeds["user_id"])
        assert result is None


def test_interrupt_recorded_in_to_dict(app, seeds):
    with app.app_context():
        session = _new_session(seeds["user_id"])
        result = interrupt_session(session["id"], seeds["user_id"])

        assert result["interruption_count"] == 1
        assert result["bonus_xp_awarded"] is None


def test_bonus_xp_updates_user_total_xp(app, seeds):
    with app.app_context():
        user = db.session.get(User, seeds["user_id"])
        xp_before = user.total_xp

        session = _new_session(seeds["user_id"])
        complete_session(session["id"], seeds["user_id"])

        db.session.refresh(user)
        assert user.total_xp == xp_before + POMODORO_BONUS_XP
