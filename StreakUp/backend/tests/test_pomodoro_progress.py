"""Tests for Pomodoro → habit progress integration (issue #40)."""

from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.services.pomodoro_service import complete_session, create_session


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
        user = User(username="pomuser", email="pomuser@test.com")
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
        text_habit = Habit(
            nombre="Journal",
            categoria_id=cat.id,
            tipo_validacion="texto",
            dificultad="media",
            xp_base=10,
        )
        db.session.add_all([time_habit, text_habit])
        db.session.commit()

        uh_time = UserHabit(
            usuario_id=user.id,
            habito_id=time_habit.id,
            tipo_validacion="tiempo",
            duracion_objetivo_minutos=30,
            activo=True,
            fecha_inicio=today,
        )
        uh_text = UserHabit(
            usuario_id=user.id,
            habito_id=text_habit.id,
            tipo_validacion="texto",
            activo=True,
            fecha_inicio=today,
        )
        db.session.add_all([uh_time, uh_text])
        db.session.commit()

        return {
            "user_id": user.id,
            "uh_time_id": uh_time.id,
            "uh_text_id": uh_text.id,
        }


def test_create_session_rejects_non_time_habit(app, seeds):
    with app.app_context():
        with pytest.raises(ValueError, match="time-based"):
            create_session(
                seeds["user_id"],
                {"habit_id": seeds["uh_text_id"], "study_minutes": 25, "break_minutes": 5, "cycles": 1},
            )


def test_create_session_rejects_foreign_habit(app, seeds):
    with app.app_context():
        with pytest.raises(ValueError, match="owned by the user"):
            create_session(
                seeds["user_id"],
                {"habit_id": 99999, "study_minutes": 25, "break_minutes": 5, "cycles": 1},
            )


def test_complete_session_awards_xp_and_creates_checkin(app, seeds):
    with app.app_context():
        session = create_session(
            seeds["user_id"],
            {"habit_id": seeds["uh_time_id"], "study_minutes": 25, "break_minutes": 5, "cycles": 2},
        )
        result = complete_session(session["id"], seeds["user_id"])

        assert result["completed"] is True
        assert result["xp_awarded"] > 0

        checkin = CheckIn.query.filter_by(
            habitousuario_id=seeds["uh_time_id"],
            fecha=date.today(),
        ).first()
        assert checkin is not None
        assert checkin.completado is True
        assert checkin.xp_ganado == result["xp_awarded"]


def test_complete_session_idempotent_no_duplicate_xp(app, seeds):
    with app.app_context():
        session = create_session(
            seeds["user_id"],
            {"habit_id": seeds["uh_time_id"], "study_minutes": 25, "break_minutes": 5, "cycles": 2},
        )
        first = complete_session(session["id"], seeds["user_id"])
        second = complete_session(session["id"], seeds["user_id"])

        assert first["xp_awarded"] > 0
        assert second["xp_awarded"] == 0

        checkins = CheckIn.query.filter_by(
            habitousuario_id=seeds["uh_time_id"],
            fecha=date.today(),
        ).all()
        assert len(checkins) == 1


def test_complete_session_without_habit_awards_no_xp(app, seeds):
    with app.app_context():
        session = create_session(
            seeds["user_id"],
            {"study_minutes": 25, "break_minutes": 5, "cycles": 4},
        )
        result = complete_session(session["id"], seeds["user_id"])

        assert result["completed"] is True
        assert result["xp_awarded"] == 0
        assert CheckIn.query.count() == 0


def test_complete_session_not_found_returns_none(app, seeds):
    with app.app_context():
        result = complete_session(99999, seeds["user_id"])
        assert result is None


def test_complete_existing_checkin_skips_xp(app, seeds):
    """If a CheckIn already exists for today (from validation), Pomodoro should not double-award."""
    with app.app_context():
        existing = CheckIn(
            habitousuario_id=seeds["uh_time_id"],
            fecha=date.today(),
            completado=True,
            xp_ganado=15,
        )
        db.session.add(existing)
        db.session.commit()

        session = create_session(
            seeds["user_id"],
            {"habit_id": seeds["uh_time_id"], "study_minutes": 25, "break_minutes": 5, "cycles": 2},
        )
        result = complete_session(session["id"], seeds["user_id"])

        assert result["xp_awarded"] == 0
        assert CheckIn.query.count() == 1
