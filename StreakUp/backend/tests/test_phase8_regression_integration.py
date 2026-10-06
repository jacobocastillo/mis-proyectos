"""Phase 8 final regression/integration validation tests."""

from datetime import date, timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.pomodoro_session import POMODORO_BONUS_XP
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.user_habit_schedule import UserHabitScheduleDay
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog
from app.services.checkin_service import is_eligible_today
from app.services.pomodoro_service import complete_session, create_session
from app.services.validation_service import validate_habit


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


def _register_and_login(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "phase8_user",
            "email": "phase8@example.com",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": "phase8@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    payload = login_response.get_json()
    return payload["access_token"], payload["user"]["id"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded(app):
    with app.app_context():
        category = Category(nombre="Phase 8", descripcion="Regression fixtures")
        db.session.add(category)
        db.session.flush()

        time_habit = Habit(
            nombre="Deep work",
            categoria_id=category.id,
            dificultad="media",
            xp_base=10,
            tipo_validacion="time",
            meta_type="minutes",
            xp_rate=1,
            max_xp_per_day=40,
        )
        text_habit = Habit(
            nombre="Reflection",
            categoria_id=category.id,
            dificultad="facil",
            xp_base=20,
            tipo_validacion="texto",
            meta_type="boolean",
            xp_rate=0,
            max_xp_per_day=20,
        )
        db.session.add_all([time_habit, text_habit])
        db.session.commit()

        return {
            "time_habit_id": time_habit.id,
            "text_habit_id": text_habit.id,
        }


def test_phase8_validated_progress_history_stats_and_pomodoro_are_integrated(app, seeded):
    client = app.test_client()

    with app.app_context():
        token, user_id = _register_and_login(client)
        today = date.today()
        tomorrow = today + timedelta(days=1)

        time_assignment = UserHabit(
            usuario_id=user_id,
            habito_id=seeded["time_habit_id"],
            tipo_validacion="time",
            frecuencia="custom",
            duracion_objetivo_minutos=10,
            activo=True,
            fecha_inicio=today,
        )
        text_assignment = UserHabit(
            usuario_id=user_id,
            habito_id=seeded["text_habit_id"],
            tipo_validacion="texto",
            frecuencia="daily",
            activo=True,
            fecha_inicio=today,
            min_text_length=10,
        )
        db.session.add_all([time_assignment, text_assignment])
        db.session.flush()
        db.session.add(
            UserHabitScheduleDay(
                habitousuario_id=time_assignment.id,
                weekday=today.weekday(),
            )
        )
        db.session.commit()

        assert is_eligible_today(time_assignment, today) is True
        assert is_eligible_today(time_assignment, tomorrow) is (tomorrow.weekday() == today.weekday())

        validation_result = validate_habit(
            user_id,
            time_assignment.id,
            {"duration_minutes": 30},
        )
        assert validation_result["valido"] is True
        assert validation_result["xp_ganado"] == 40
        assert validation_result["feedback"]["message"]
        assert validation_result["difficulty_recommendation"]["advisory"] is True

        checkin = CheckIn.query.filter_by(
            habitousuario_id=time_assignment.id,
            fecha=today,
        ).one()
        assert checkin.completado is True
        assert checkin.xp_ganado == 40

        validation_log = ValidationLog.query.filter_by(
            habitousuario_id=time_assignment.id,
            status="approved",
        ).one()
        assert validation_log.validado is True

        habit_xp_log = XpLog.query.filter_by(
            user_id=user_id,
            habit_id=time_assignment.id,
            event_date=today,
            razon="validation",
        ).one()
        assert habit_xp_log.cantidad == 40
        assert habit_xp_log.calculated_xp == 40
        assert habit_xp_log.cap_hit is False

        duplicate_toggle = client.post(
            "/api/checkins/toggle",
            headers=_auth_headers(token),
            json={"habit_id": time_assignment.id},
        )
        assert duplicate_toggle.status_code == 409
        assert "requires validation" in duplicate_toggle.get_json()["error"]

        summary_response = client.get("/api/stats/summary", headers=_auth_headers(token))
        assert summary_response.status_code == 200
        summary = summary_response.get_json()
        assert summary["today_completed"] == 1
        assert summary["today_total"] == 2
        assert summary["total_xp"] == 40

        history_response = client.get("/api/checkins/history", headers=_auth_headers(token))
        assert history_response.status_code == 200
        history = history_response.get_json()
        completion_event = next(
            item for item in history["items"] if item["source"] == "completion"
        )
        assert completion_event["habit_id"] == time_assignment.id
        assert completion_event["xp_awarded"] == 40
        assert completion_event["validation_type"] == "time"

        pomodoro = create_session(
            user_id,
            {
                "habit_id": time_assignment.id,
                "study_minutes": 25,
                "break_minutes": 5,
                "cycles": 2,
            },
        )
        first_completion = complete_session(pomodoro["id"], user_id)
        second_completion = complete_session(pomodoro["id"], user_id)

        assert first_completion["xp_awarded"] == 0
        assert first_completion["bonus_xp"] == POMODORO_BONUS_XP
        assert second_completion["xp_awarded"] == 0
        assert CheckIn.query.filter_by(habitousuario_id=time_assignment.id, fecha=today).count() == 1
        assert XpLog.query.filter_by(user_id=user_id, razon="pomodoro_bonus").count() == 1

        user = db.session.get(User, user_id)
        assert user.total_xp == 40 + POMODORO_BONUS_XP


def test_phase8_pomodoro_progress_can_fill_remaining_cap_without_duplicate_bonus(app, seeded):
    client = app.test_client()

    with app.app_context():
        token, user_id = _register_and_login(client)
        today = date.today()

        time_assignment = UserHabit(
            usuario_id=user_id,
            habito_id=seeded["time_habit_id"],
            tipo_validacion="time",
            frecuencia="daily",
            duracion_objetivo_minutos=10,
            activo=True,
            fecha_inicio=today,
        )
        db.session.add(time_assignment)
        db.session.commit()

        # 20 raw XP leaves 20 XP remaining under the 40 XP daily cap.
        first_validation = validate_habit(
            user_id,
            time_assignment.id,
            {"duration_minutes": 10},
        )
        assert first_validation["xp_ganado"] == 20

        db.session.delete(
            CheckIn.query.filter_by(
                habitousuario_id=time_assignment.id,
                fecha=today,
            ).one()
        )
        db.session.commit()

        pomodoro = create_session(
            user_id,
            {
                "habit_id": time_assignment.id,
                "study_minutes": 25,
                "break_minutes": 5,
                "cycles": 1,
            },
        )
        completed = complete_session(pomodoro["id"], user_id)
        repeated = complete_session(pomodoro["id"], user_id)

        assert completed["xp_awarded"] == 20
        assert completed["bonus_xp"] == POMODORO_BONUS_XP
        assert repeated["xp_awarded"] == 0
        assert XpLog.query.filter_by(
            user_id=user_id,
            habit_id=time_assignment.id,
            event_date=today,
            source_event="habit",
        ).count() == 3
        assert db.session.get(User, user_id).total_xp == 20 + 20 + POMODORO_BONUS_XP

        xp_response = client.get("/api/stats/xp", headers=_auth_headers(token))
        assert xp_response.status_code == 200
        assert xp_response.get_json()["total_xp"] == 50
