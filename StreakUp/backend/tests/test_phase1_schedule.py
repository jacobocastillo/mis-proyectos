"""
Phase 1 tests: custom frequency, weekday schedule, and min_text_length persistence.
"""

import pytest
from datetime import date

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.habit import Category, Habit
from app.models.user_habit import UserHabit
from app.models.user_habit_schedule import UserHabitScheduleDay
from app.services.habit_service import assign_habit_to_user, update_user_habit, serialize_user_habit
from app.schemas.habit_validations import normalize_habit_payload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    app_instance = create_app()
    app_instance.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()


@pytest.fixture
def user(app):
    with app.app_context():
        u = User(username="p1_user", email="p1@test.com")
        u.set_password("password")
        db.session.add(u)
        db.session.commit()
        return u.id


@pytest.fixture
def habit(app):
    with app.app_context():
        cat = Category(nombre="Health")
        db.session.add(cat)
        db.session.flush()
        h = Habit(
            nombre="Exercise",
            categoria_id=cat.id,
            frecuencia="daily",
            xp_base=10,
            dificultad="media",
            tipo_validacion="foto",
        )
        db.session.add(h)
        db.session.commit()
        return h.id


# ---------------------------------------------------------------------------
# Model / persistence tests
# ---------------------------------------------------------------------------

def test_custom_frequency_persists(app, user, habit):
    """Assigning a habit with frequency=custom + schedule_days persists correctly."""
    with app.app_context():
        result = assign_habit_to_user(
            user,
            habit,
            overrides={"frequency": "custom", "schedule_days": [1, 3, 5]},
        )

        assert result["frequency"] == "custom"
        assert result["schedule_days"] == [1, 3, 5]

        # Confirm rows exist in DB
        uh = UserHabit.query.filter_by(usuario_id=user, habito_id=habit, activo=True).first()
        assert uh is not None
        assert uh.frecuencia == "custom"
        days_in_db = sorted(
            [row.weekday for row in UserHabitScheduleDay.query.filter_by(habitousuario_id=uh.id).all()]
        )
        assert days_in_db == [1, 3, 5]


def test_schedule_days_replace_on_update(app, user, habit):
    """Updating schedule_days replaces all old rows atomically."""
    with app.app_context():
        result = assign_habit_to_user(
            user,
            habit,
            overrides={"frequency": "custom", "schedule_days": [0, 2, 4]},
        )
        uh_id = result["id"]

        update_user_habit(uh_id, user, {"schedule_days": [1, 6]})

        uh = UserHabit.query.get(uh_id)
        days_in_db = sorted(
            [row.weekday for row in UserHabitScheduleDay.query.filter_by(habitousuario_id=uh.id).all()]
        )
        assert days_in_db == [1, 6]


def test_min_text_length_persists(app, user, habit):
    """min_text_length is saved and returned through serialization."""
    with app.app_context():
        result = assign_habit_to_user(
            user,
            habit,
            overrides={"validation_type": "texto", "min_text_length": 50},
        )
        assert result["min_text_length"] == 50

        # Confirm round-trip after update
        update_user_habit(result["id"], user, {"min_text_length": 100})
        uh = UserHabit.query.get(result["id"])
        assert uh.min_text_length == 100
        serialized = serialize_user_habit(uh)
        assert serialized["min_text_length"] == 100


def test_daily_weekly_still_work(app, user, habit):
    """Regression: daily habits work without schedule_days."""
    with app.app_context():
        result = assign_habit_to_user(user, habit, overrides={"frequency": "daily"})
        assert result["frequency"] == "daily"
        assert result["schedule_days"] == []

        # weekly
        uh_id = result["id"]
        updated = update_user_habit(uh_id, user, {"frequency": "weekly"})
        assert updated["frequency"] == "weekly"
        assert updated["schedule_days"] == []


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

def test_schema_rejects_invalid_weekday():
    """Days outside 0-6 must be rejected."""
    _, errors = normalize_habit_payload(
        {"habito_id": 1, "frequency": "custom", "schedule_days": [1, 7]},
        require_habito_id=True,
    )
    assert any("schedule_days" in e for e in errors)

    _, errors2 = normalize_habit_payload(
        {"habito_id": 1, "frequency": "custom", "schedule_days": [-1]},
        require_habito_id=True,
    )
    assert any("schedule_days" in e for e in errors2)


def test_custom_frequency_requires_schedule_days_on_create():
    """Creating a habit with custom frequency but no schedule_days should error."""
    _, errors = normalize_habit_payload(
        {"habito_id": 1, "frequency": "custom"},
        require_habito_id=True,
    )
    assert any("schedule_days" in e for e in errors)


def test_custom_frequency_empty_schedule_days_errors():
    """An empty schedule_days list with custom frequency must be rejected."""
    _, errors = normalize_habit_payload(
        {"habito_id": 1, "frequency": "custom", "schedule_days": []},
        require_habito_id=True,
    )
    assert any("schedule_days" in e for e in errors)


def test_schedule_days_deduplication():
    """Duplicate weekday values are silently deduplicated."""
    normalized, errors = normalize_habit_payload(
        {"habito_id": 1, "frequency": "custom", "schedule_days": [2, 2, 4, 4, 4]},
        require_habito_id=True,
    )
    assert errors == []
    assert normalized["schedule_days"] == [2, 4]


def test_min_text_length_schema_validation():
    """min_text_length accepts 0 and positives, rejects negatives and non-int."""
    normalized, errors = normalize_habit_payload(
        {"habito_id": 1, "min_text_length": 0},
        require_habito_id=True,
    )
    assert errors == []
    assert normalized["min_text_length"] == 0

    _, errors2 = normalize_habit_payload(
        {"habito_id": 1, "min_text_length": -5},
        require_habito_id=True,
    )
    assert any("min_text_length" in e for e in errors2)

    _, errors3 = normalize_habit_payload(
        {"habito_id": 1, "min_text_length": "big"},
        require_habito_id=True,
    )
    assert any("min_text_length" in e for e in errors3)
