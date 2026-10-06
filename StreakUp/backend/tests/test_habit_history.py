import json
import os
import tempfile
from datetime import date, datetime, timezone

from app import create_app
from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog


def _build_app():
    temp_dir = tempfile.TemporaryDirectory()
    database_path = os.path.join(temp_dir.name, "habit-history.db")
    TestConfig = type(
        "HabitHistoryConfig",
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
    return create_app(TestConfig), temp_dir


def _headers(client, email: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.get_json()['access_token']}"}


def _seed_history_data():
    category = Category(nombre="Productividad", descripcion="Work")
    db.session.add(category)
    db.session.flush()

    habit = Habit(
        nombre="Deep work",
        categoria_id=category.id,
        dificultad="media",
        xp_base=20,
        tipo_validacion="foto",
        meta_type="boolean",
        xp_rate=0,
        max_xp_per_day=20,
    )
    other_habit = Habit(
        nombre="Other habit",
        categoria_id=category.id,
        dificultad="media",
        xp_base=20,
        tipo_validacion="foto",
        meta_type="boolean",
        xp_rate=0,
        max_xp_per_day=20,
    )
    db.session.add_all([habit, other_habit])
    db.session.flush()

    user = User(username="history_user", email="history@test.com", role="user")
    user.set_password("password")
    other_user = User(username="other_history_user", email="other-history@test.com", role="user")
    other_user.set_password("password")
    db.session.add_all([user, other_user])
    db.session.flush()

    user_habit = UserHabit(
        usuario_id=user.id,
        habito_id=habit.id,
        fecha_inicio=date(2026, 5, 1),
        activo=True,
    )
    other_user_habit = UserHabit(
        usuario_id=other_user.id,
        habito_id=other_habit.id,
        fecha_inicio=date(2026, 5, 1),
        activo=True,
    )
    db.session.add_all([user_habit, other_user_habit])
    db.session.flush()

    completed_date = date(2026, 5, 2)
    validation = ValidationLog(
        habitousuario_id=user_habit.id,
        tipo_validacion="foto",
        evidencia=json.dumps({
            "validation_type": "photo",
            "reason": "valid evidence",
            "confidence": 0.91,
            "xp_awarded": 20,
        }),
        status="approved",
        validado=True,
        fecha=datetime(2026, 5, 2, 15, 30, tzinfo=timezone.utc),
    )
    checkin = CheckIn(
        habitousuario_id=user_habit.id,
        fecha=completed_date,
        completado=True,
        xp_ganado=20,
    )
    rejected = ValidationLog(
        habitousuario_id=user_habit.id,
        tipo_validacion="foto",
        evidencia=json.dumps({
            "validation_type": "photo",
            "reason": "not enough evidence",
            "confidence": 0.2,
        }),
        status="rejected",
        validado=False,
        fecha=datetime(2026, 5, 3, 16, 0, tzinfo=timezone.utc),
    )
    pending = ValidationLog(
        habitousuario_id=user_habit.id,
        tipo_validacion="texto",
        evidencia=json.dumps({"validation_type": "text_ai"}),
        status="pending",
        validado=False,
        fecha=datetime(2026, 5, 4, 17, 0, tzinfo=timezone.utc),
    )
    other_checkin = CheckIn(
        habitousuario_id=other_user_habit.id,
        fecha=completed_date,
        completado=True,
        xp_ganado=20,
    )
    xp_log = XpLog(
        user_id=user.id,
        cantidad=20,
        razon="validation",
        habit_id=user_habit.id,
        event_date=completed_date,
        calculated_xp=20,
    )
    db.session.add_all([validation, checkin, rejected, pending, other_checkin, xp_log])
    db.session.commit()

    return {
        "user": user,
        "other_user": other_user,
        "user_habit": user_habit,
        "validation": validation,
        "checkin": checkin,
        "rejected": rejected,
        "pending": pending,
    }


def test_history_returns_unified_completion_and_validation_only_events():
    app, temp_dir = _build_app()
    try:
        with app.app_context():
            db.create_all()
            seeded = _seed_history_data()
            client = app.test_client()
            response = client.get(
                "/api/checkins/history",
                headers=_headers(client, seeded["user"].email),
            )

            assert response.status_code == 200
            payload = response.get_json()
            assert payload["next_cursor"] is None
            assert [item["status"] for item in payload["items"]] == ["pending", "rejected", "completed"]

            completion = payload["items"][2]
            assert completion["id"] == f"checkin:{seeded['checkin'].id}"
            assert completion["source"] == "completion"
            assert completion["habit_id"] == seeded["user_habit"].id
            assert completion["habit_name"] == "Deep work"
            assert completion["category_name"] == "Productividad"
            assert completion["status"] == "completed"
            assert completion["validation_id"] == seeded["validation"].id
            assert completion["validation_type"] == "photo"
            assert completion["xp_awarded"] == 20
            assert completion["reason"] == "valid evidence"
            assert completion["confidence"] == 0.91

            assert all(item["habit_name"] != "Other habit" for item in payload["items"])
            db.session.remove()
            db.drop_all()
    finally:
        temp_dir.cleanup()


def test_history_filters_by_date_habit_status_and_paginates():
    app, temp_dir = _build_app()
    try:
        with app.app_context():
            db.create_all()
            seeded = _seed_history_data()
            client = app.test_client()
            headers = _headers(client, seeded["user"].email)

            rejected = client.get("/api/checkins/history?status=rejected", headers=headers)
            assert rejected.status_code == 200
            assert [item["status"] for item in rejected.get_json()["items"]] == ["rejected"]

            by_date = client.get("/api/checkins/history?from=2026-05-02&to=2026-05-03", headers=headers)
            assert by_date.status_code == 200
            assert [item["status"] for item in by_date.get_json()["items"]] == ["rejected", "completed"]

            by_habit = client.get(f"/api/checkins/history?habit_id={seeded['user_habit'].id}", headers=headers)
            assert by_habit.status_code == 200
            assert len(by_habit.get_json()["items"]) == 3

            first_page = client.get("/api/checkins/history?limit=2", headers=headers)
            assert first_page.status_code == 200
            first_payload = first_page.get_json()
            assert len(first_payload["items"]) == 2
            assert first_payload["next_cursor"] == "2"

            second_page = client.get(
                f"/api/checkins/history?limit=2&cursor={first_payload['next_cursor']}",
                headers=headers,
            )
            assert second_page.status_code == 200
            second_payload = second_page.get_json()
            assert [item["status"] for item in second_payload["items"]] == ["completed"]
            assert second_payload["next_cursor"] is None
            db.session.remove()
            db.drop_all()
    finally:
        temp_dir.cleanup()


def test_history_rejects_invalid_query_params():
    app, temp_dir = _build_app()
    try:
        with app.app_context():
            db.create_all()
            seeded = _seed_history_data()
            client = app.test_client()
            headers = _headers(client, seeded["user"].email)

            for query in (
                "from=bad-date",
                "from=2026-05-04&to=2026-05-01",
                "habit_id=abc",
                "status=unknown",
                "limit=0",
                "cursor=-1",
            ):
                response = client.get(f"/api/checkins/history?{query}", headers=headers)
                assert response.status_code == 400
            db.session.remove()
            db.drop_all()
    finally:
        temp_dir.cleanup()
