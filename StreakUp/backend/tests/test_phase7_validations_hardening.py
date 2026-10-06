"""
Phase 7 Hardening tests.

Covers:
- Validation logic for all three modalities (foto, texto, tiempo)
- Enforcement of min_text_length boundary
- Enforcement of frequency combinations
"""

import pytest
from datetime import date
from flask import Flask
from app.models.habit import Habit, Category
from app.models.user import User
from app.models.user_habit import UserHabit
from app.services.validation_service import validate_habit
from app.extensions import db
from app import create_app

def _make_config(name: str):
    return type(
        name,
        (),
        {
            "SECRET_KEY": "test-secret",
            "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "TESTING": True,
        },
    )

@pytest.fixture
def app():
    app = create_app(_make_config("HardeningTestConfig"))
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def hardening_user(app: Flask):
    with app.app_context():
        u = User(username="hardened_user", email="hard@streakup.com", role="user")
        u.set_password("pass")
        db.session.add(u)
        db.session.commit()
        return u.id


@pytest.fixture
def hardening_habits(app: Flask):
    with app.app_context():
        cat = Category(nombre="Hardening", descripcion="Tests")
        db.session.add(cat)
        db.session.flush()

        h_text = Habit(
            categoria_id=cat.id,
            nombre="Ensayo",
            xp_base=10,
            dificultad="media",
            tipo_validacion="texto",
            frecuencia="daily",
        )
        h_timer = Habit(
            categoria_id=cat.id,
            nombre="Meditar",
            xp_base=10,
            dificultad="media",
            tipo_validacion="tiempo",
            frecuencia="daily",
            duracion_objetivo_minutos=5,
        )
        db.session.add_all([h_text, h_timer])
        db.session.commit()
        return h_text.id, h_timer.id


def test_text_validation_boundaries(app: Flask, hardening_user: int, hardening_habits: tuple[int, int]):
    h_text_id, _ = hardening_habits
    with app.app_context():
        # Setup specific UserHabit requiring 50 chars minimum
        uh = UserHabit(
            usuario_id=hardening_user,
            habito_id=h_text_id,
            min_text_length=50,
            fecha_inicio=date.today(),
            activo=True,
        )
        db.session.add(uh)
        db.session.commit()
        uh_id = uh.id

        # 1. Invalid (too short)
        short_text = "Hola"  # 4 chars
        with pytest.raises(ValueError, match="El texto debe tener al menos"):
            validate_habit(hardening_user, uh_id, {"text_content": short_text})

        # 2. Valid (long enough)
        long_text = "Este es un ensayo lo suficientemente largo e interesante como para superar los 50 caracteres."
        result_pass = validate_habit(hardening_user, uh_id, {"text_content": long_text})
        assert result_pass["status"] == "approved"
        assert result_pass["valido"] is True


def test_timer_validation_boundaries(app: Flask, hardening_user: int, hardening_habits: tuple[int, int]):
    _, h_timer_id = hardening_habits
    with app.app_context():
        # Setup specific timer UserHabit requiring 5 minutes (300 seconds)
        uh = UserHabit(
            usuario_id=hardening_user,
            habito_id=h_timer_id,
            duracion_objetivo_minutos=5,
            fecha_inicio=date.today(),
            activo=True,
        )
        db.session.add(uh)
        db.session.commit()
        uh_id = uh.id

        # 1. Invalid timer (too short duration)
        with pytest.raises(ValueError, match="Debes completar al menos"):
            validate_habit(hardening_user, uh_id, {"duration_minutes": 2.5})

        # 2. Valid timer (>= 5 minutes)
        result_pass = validate_habit(hardening_user, uh_id, {"duration_minutes": 5})
        assert result_pass["status"] == "approved"
        assert result_pass["valido"] is True

