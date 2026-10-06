import os
import tempfile
from typing import Callable

import pytest

from app import create_app
from app.extensions import db
from app.models.habit import Category, Habit
from app.models.user import User


@pytest.fixture
def requirement_app():
    temp_dir = tempfile.TemporaryDirectory()
    database_path = os.path.join(temp_dir.name, "requirements.db")
    config = type(
        "RequirementTestConfig",
        (),
        {
            "SECRET_KEY": "test-secret",
            "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "DEBUG": False,
            "TESTING": True,
            "ENVIRONMENT": "test",
            "OPENAI_API_KEY": "",
        },
    )

    app = create_app(config)
    app_context = app.app_context()
    app_context.push()
    db.create_all()

    try:
        yield app
    finally:
        db.session.remove()
        db.drop_all()
        app_context.pop()
        temp_dir.cleanup()


@pytest.fixture
def client(requirement_app):
    return requirement_app.test_client()


@pytest.fixture
def create_user() -> Callable[[str, str, str], User]:
    def _create_user(
        username: str = "Daniel",
        email: str = "daniel@correo.com",
        password: str = "daniel-password",
    ) -> User:
        user = User(username=username, email=email, role="user")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _create_user


@pytest.fixture
def auth_headers(client, create_user) -> Callable[[str, str], dict[str, str]]:
    def _auth_headers(
        email: str = "daniel@correo.com",
        password: str = "daniel-password",
    ) -> dict[str, str]:
        if User.query.filter_by(email=email).first() is None:
            create_user(email=email, password=password)

        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.get_json()['access_token']}"}

    return _auth_headers


@pytest.fixture
def seed_catalog() -> Callable[[], Habit]:
    def _seed_catalog() -> Habit:
        category = Category(nombre="Salud", descripcion="Habitos de salud")
        habit = Habit(
            category=category,
            nombre="Tomar agua",
            descripcion="Beber agua diariamente",
            dificultad="facil",
            xp_base=10,
            tipo_validacion="foto",
            frecuencia="daily",
        )
        db.session.add_all([category, habit])
        db.session.commit()
        return habit

    return _seed_catalog
