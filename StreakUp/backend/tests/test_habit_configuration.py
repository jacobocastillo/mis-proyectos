import os
import tempfile
from datetime import date

import pytest

from app import create_app
from app.extensions import db
from app.models.habit import Category, Habit
from app.models.user import User
from app.services.habit_service import assign_habit_to_user, update_user_habit


@pytest.fixture
def app():
    temp_dir = tempfile.TemporaryDirectory()
    database_path = os.path.join(temp_dir.name, "habit-configuration.db")
    TestConfig = type(
        "HabitConfigurationConfig",
        (),
        {
            "SECRET_KEY": "test-secret-key-with-32-characters!!",
            "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars!!",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "DEBUG": False,
            "TESTING": True,
            "ENVIRONMENT": "test",
            "OPENAI_API_KEY": "",
        },
    )
    app_instance = create_app(TestConfig)
    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()
    temp_dir.cleanup()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_id(app):
    with app.app_context():
        user = User(username="config_user", email="config@test.com", role="user")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def headers(app, client, user_id):
    response = client.post(
        "/api/auth/login",
        json={"email": "config@test.com", "password": "password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['access_token']}"}


@pytest.fixture
def catalog_ids(app):
    with app.app_context():
        category = Category(nombre="Point A", descripcion="Config tests")
        db.session.add(category)
        db.session.flush()
        habits = {
            "liters": Habit(
                nombre="Water",
                categoria_id=category.id,
                dificultad="facil",
                xp_base=20,
                tipo_validacion="photo",
                meta_type="quantity_liters",
                xp_rate=0,
                max_xp_per_day=20,
            ),
            "minutes": Habit(
                nombre="Study",
                categoria_id=category.id,
                dificultad="media",
                xp_base=0,
                tipo_validacion="time",
                meta_type="minutes",
                xp_rate=1,
                max_xp_per_day=45,
            ),
            "check": Habit(
                nombre="Start early",
                categoria_id=category.id,
                dificultad="media",
                xp_base=20,
                tipo_validacion="check",
                meta_type="boolean",
                xp_rate=0,
                max_xp_per_day=20,
            ),
            "boolean": Habit(
                nombre="Journal",
                categoria_id=category.id,
                dificultad="facil",
                xp_base=20,
                tipo_validacion="text_ai",
                meta_type="boolean",
                xp_rate=0,
                max_xp_per_day=20,
            ),
        }
        db.session.add_all(habits.values())
        db.session.commit()
        return {name: habit.id for name, habit in habits.items()}


def test_decimal_liters_persist_and_serialize(app, user_id, catalog_ids):
    with app.app_context():
        payload = assign_habit_to_user(
            user_id,
            catalog_ids["liters"],
            {"target_quantity": 2.5},
        )

        assert payload["target_quantity"] == 2.5
        assert payload["target_unit"] == "litros"
        assert payload["category_id"] is not None
        assert payload["category_name"] == "Point A"


def test_quantity_liters_requires_positive_quantity(app, user_id, catalog_ids):
    with app.app_context():
        with pytest.raises(ValueError, match="target_quantity"):
            assign_habit_to_user(user_id, catalog_ids["liters"])

        with pytest.raises(ValueError, match="target_quantity"):
            assign_habit_to_user(
                user_id,
                catalog_ids["liters"],
                {"target_quantity": 0},
            )


def test_minutes_requires_positive_duration(app, user_id, catalog_ids):
    with app.app_context():
        with pytest.raises(ValueError, match="target_duration"):
            assign_habit_to_user(user_id, catalog_ids["minutes"])

        payload = assign_habit_to_user(
            user_id,
            catalog_ids["minutes"],
            {"target_duration": 45},
        )
        assert payload["target_duration"] == 45


def test_check_requires_valid_deadline_time(app, client, headers, catalog_ids):
    missing = client.post(
        "/api/habits",
        json={"habito_id": catalog_ids["check"]},
        headers=headers,
    )
    assert missing.status_code == 400
    assert "deadline_time" in missing.get_json()["error"]

    invalid = client.post(
        "/api/habits",
        json={"habito_id": catalog_ids["check"], "deadline_time": "25:00"},
        headers=headers,
    )
    assert invalid.status_code == 400
    assert any("deadline_time" in error for error in invalid.get_json()["errors"])

    valid = client.post(
        "/api/habits",
        json={"habito_id": catalog_ids["check"], "deadline_time": "08:30"},
        headers=headers,
    )
    assert valid.status_code == 201
    assert valid.get_json()["deadline_time"] == "08:30"


def test_api_rejects_canonical_rule_overrides(client, headers, catalog_ids):
    response = client.post(
        "/api/habits",
        json={
            "habito_id": catalog_ids["boolean"],
            "validation_type": "photo",
            "xp_base": 999,
            "meta_type": "minutes",
            "max_xp_per_day": 999,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "Catalog rule fields cannot be overridden" in response.get_json()["errors"][0]


def test_update_cannot_clear_required_config(app, user_id, catalog_ids):
    with app.app_context():
        created = assign_habit_to_user(
            user_id,
            catalog_ids["minutes"],
            {"target_duration": 30},
        )

        with pytest.raises(ValueError, match="target_duration"):
            update_user_habit(created["id"], user_id, {"target_duration": None})


def test_update_persists_deadline_time(app, user_id, catalog_ids):
    with app.app_context():
        created = assign_habit_to_user(
            user_id,
            catalog_ids["check"],
            {"deadline_time": "08:00"},
        )
        updated = update_user_habit(
            created["id"],
            user_id,
            {"deadline_time": "07:45"},
        )

        assert updated["deadline_time"] == "07:45"
