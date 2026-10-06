import pytest

from app import create_app
from app.extensions import db
from app.services.difficulty_service import recommend_difficulty
from app.services.motivation_service import build_summary_feedback, build_validation_feedback


@pytest.fixture
def app():
    instance = create_app()
    instance.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "OPENAI_API_KEY": "",
    })
    with instance.app_context():
        db.create_all()
        yield instance
        db.session.remove()
        db.drop_all()


def test_difficulty_recommendation_falls_back_without_openai(app):
    with app.app_context():
        result = recommend_difficulty(
            "Leer",
            "facil",
            {"validation_type": "texto", "target_summary": "10 min"},
        )

    assert result["level"] == "facil"
    assert result["source"] == "deterministic"
    assert result["advisory"] is True
    assert "XP" in result["explanation"]


def test_validation_feedback_uses_progress_context():
    result = build_validation_feedback({
        "approved": True,
        "habit_name": "Leer",
        "today_completed": 2,
        "today_total": 3,
        "streak": 5,
        "xp_awarded": 20,
    })

    assert result["tone"] == "streak"
    assert "5 días" in result["message"]
    assert result["context"]["today_completed"] == 2


def test_summary_feedback_uses_remaining_count():
    result = build_summary_feedback({
        "today_completed": 1,
        "today_total": 3,
        "streak": 0,
        "completion_rate": 33,
        "validations_today": 1,
    })

    assert result["tone"] == "progress"
    assert "Te faltan 2" in result["message"]
    assert result["context"]["completion_rate"] == 33
