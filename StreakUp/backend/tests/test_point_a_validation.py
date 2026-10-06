"""
Point A validation modality tests.

Covers photo, text_ai, time, and check validation types.
"""

import os
import tempfile
from datetime import date
from unittest.mock import patch

import pytest

from app import create_app
from app.extensions import db
from app.models.habit import Category, Habit
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.services.validation_service import validate_habit


def _make_config(db_path: str):
    return type(
        "PointAValidationConfig",
        (),
        {
            "SECRET_KEY": "test-secret-key-with-32-characters!!",
            "JWT_SECRET_KEY": "test-jwt-secret-key-with-32-chars!!",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "TESTING": True,
            "ENVIRONMENT": "test",
            "OPENAI_API_KEY": "",
        },
    )


@pytest.fixture
def app():
    temp_dir = tempfile.TemporaryDirectory()
    db_path = os.path.join(temp_dir.name, "point-a-validation.db")
    app_instance = create_app(_make_config(db_path))
    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()
    temp_dir.cleanup()


@pytest.fixture
def seeded(app):
    with app.app_context():
        user = User(username="val_user", email="val@test.com", role="user")
        user.set_password("password")
        db.session.add(user)
        db.session.flush()

        cat = Category(nombre="Point A Tests", descripcion="")
        db.session.add(cat)
        db.session.flush()

        h_photo = Habit(
            nombre="Ejercicio",
            categoria_id=cat.id,
            dificultad="media",
            xp_base=20,
            tipo_validacion="photo",
            meta_type="boolean",
            xp_rate=0,
            max_xp_per_day=20,
        )
        h_text_ai = Habit(
            nombre="Diario",
            categoria_id=cat.id,
            dificultad="facil",
            xp_base=20,
            tipo_validacion="text_ai",
            meta_type="boolean",
            xp_rate=0,
            max_xp_per_day=20,
        )
        h_time = Habit(
            nombre="Meditación",
            categoria_id=cat.id,
            dificultad="media",
            xp_base=10,
            tipo_validacion="time",
            meta_type="minutes",
            xp_rate=1,
            max_xp_per_day=30,
        )
        h_check_pass = Habit(
            nombre="Empezar temprano",
            categoria_id=cat.id,
            dificultad="media",
            xp_base=20,
            tipo_validacion="check",
            meta_type="boolean",
            xp_rate=0,
            max_xp_per_day=20,
        )
        h_check_fail = Habit(
            nombre="Empezar noche",
            categoria_id=cat.id,
            dificultad="media",
            xp_base=20,
            tipo_validacion="check",
            meta_type="boolean",
            xp_rate=0,
            max_xp_per_day=20,
        )
        db.session.add_all([h_photo, h_text_ai, h_time, h_check_pass, h_check_fail])
        db.session.commit()

        uh_photo = UserHabit(usuario_id=user.id, habito_id=h_photo.id, activo=True, fecha_inicio=date.today())
        uh_text_ai = UserHabit(usuario_id=user.id, habito_id=h_text_ai.id, activo=True, fecha_inicio=date.today(), min_text_length=10)
        uh_time = UserHabit(usuario_id=user.id, habito_id=h_time.id, activo=True, fecha_inicio=date.today(), duracion_objetivo_minutos=15)
        uh_check_p = UserHabit(usuario_id=user.id, habito_id=h_check_pass.id, activo=True, fecha_inicio=date.today(), deadline_time="23:59")
        uh_check_f = UserHabit(usuario_id=user.id, habito_id=h_check_fail.id, activo=True, fecha_inicio=date.today(), deadline_time="00:00")
        db.session.add_all([uh_photo, uh_text_ai, uh_time, uh_check_p, uh_check_f])
        db.session.commit()

        return {
            "user_id": user.id,
            "uh_photo": uh_photo.id,
            "uh_text_ai": uh_text_ai.id,
            "uh_time": uh_time.id,
            "uh_check_pass": uh_check_p.id,
            "uh_check_fail": uh_check_f.id,
        }


# --- photo ---

def test_photo_missing_image_raises(app, seeded):
    with app.app_context():
        with pytest.raises(ValueError, match="image .base64. is required"):
            validate_habit(seeded["user_id"], seeded["uh_photo"], {})


def test_photo_calls_ai_and_approves(app, seeded):
    with app.app_context():
        fake_b64 = "aGVsbG8="  # valid base64
        ai_response = {"valido": True, "razon": "Evidencia válida.", "confianza": 0.95}
        with patch("app.services.validation_service.analyze_habit_image", return_value=ai_response):
            result = validate_habit(
                seeded["user_id"],
                seeded["uh_photo"],
                {"image_base64": fake_b64, "mime_type": "image/jpeg"},
            )
        assert result["valido"] is True
        assert result["xp_ganado"] > 0
        assert result["status"] == "approved"
        assert result["difficulty_recommendation"]["advisory"] is True
        assert result["difficulty_recommendation"]["source"] == "deterministic"
        assert result["feedback"]["message"]


def test_photo_calls_ai_and_rejects(app, seeded):
    with app.app_context():
        fake_b64 = "aGVsbG8="
        ai_response = {"valido": False, "razon": "No hay evidencia.", "confianza": 0.85}
        with patch("app.services.validation_service.analyze_habit_image", return_value=ai_response):
            result = validate_habit(
                seeded["user_id"],
                seeded["uh_photo"],
                {"image_base64": fake_b64, "mime_type": "image/jpeg"},
            )
        assert result["valido"] is False
        assert result["xp_ganado"] == 0
        assert result["status"] == "rejected"


# --- text_ai ---

def test_text_ai_missing_text_raises(app, seeded):
    with app.app_context():
        with pytest.raises(ValueError, match="Se requiere texto"):
            validate_habit(seeded["user_id"], seeded["uh_text_ai"], {})


def test_text_ai_too_short_raises(app, seeded):
    with app.app_context():
        with pytest.raises(ValueError, match="El texto debe tener al menos"):
            validate_habit(seeded["user_id"], seeded["uh_text_ai"], {"text_content": "corto"})


def test_text_ai_calls_ai_and_approves(app, seeded):
    with app.app_context():
        ai_response = {"valido": True, "razon": "Buen texto.", "confianza": 0.9}
        with patch("app.services.validation_service.analyze_habit_text", return_value=ai_response) as mock_ai:
            result = validate_habit(
                seeded["user_id"],
                seeded["uh_text_ai"],
                {"text_content": "Hoy escribí en mi diario sobre el día."},
            )
        mock_ai.assert_called_once()
        assert result["valido"] is True
        assert result["xp_ganado"] > 0
        assert result["status"] == "approved"


def test_text_ai_calls_ai_and_rejects(app, seeded):
    with app.app_context():
        ai_response = {"valido": False, "razon": "Texto irrelevante.", "confianza": 0.7}
        with patch("app.services.validation_service.analyze_habit_text", return_value=ai_response):
            result = validate_habit(
                seeded["user_id"],
                seeded["uh_text_ai"],
                {"text_content": "Hoy escribí en mi diario sobre el día."},
            )
        assert result["valido"] is False
        assert result["xp_ganado"] == 0
        assert result["status"] == "rejected"


# --- time ---

def test_time_missing_duration_raises(app, seeded):
    with app.app_context():
        with pytest.raises(ValueError, match="Se requiere la duración"):
            validate_habit(seeded["user_id"], seeded["uh_time"], {})


def test_time_insufficient_duration_raises(app, seeded):
    with app.app_context():
        with pytest.raises(ValueError, match="Debes completar al menos"):
            validate_habit(seeded["user_id"], seeded["uh_time"], {"duration_minutes": 10})


def test_time_sufficient_duration_approves(app, seeded):
    with app.app_context():
        result = validate_habit(seeded["user_id"], seeded["uh_time"], {"duration_minutes": 20})
        assert result["valido"] is True
        assert result["xp_ganado"] == 30
        assert result["status"] == "approved"


def test_ai_difficulty_metadata_cannot_bypass_time_xp_cap(app, seeded):
    with app.app_context():
        advisory = {
            "level": "dificil",
            "confidence": 0.99,
            "explanation": "Parece más demandante.",
            "source": "openai",
            "advisory": True,
        }
        with patch("app.services.validation_service.recommend_difficulty", return_value=advisory):
            result = validate_habit(seeded["user_id"], seeded["uh_time"], {"duration_minutes": 200})

        assert result["difficulty_recommendation"] == advisory
        assert result["xp_ganado"] == 30


# --- check ---

def test_check_before_deadline_approves(app, seeded):
    with app.app_context():
        with patch("app.services.validation_service._get_current_time_str", return_value="07:00"):
            result = validate_habit(seeded["user_id"], seeded["uh_check_pass"], {})
        assert result["valido"] is True
        assert result["xp_ganado"] > 0
        assert result["status"] == "approved"


def test_check_after_deadline_rejects(app, seeded):
    with app.app_context():
        # uh_check_fail has deadline "00:00"; any time after midnight fails
        with patch("app.services.validation_service._get_current_time_str", return_value="09:00"):
            result = validate_habit(seeded["user_id"], seeded["uh_check_fail"], {})
        assert result["valido"] is False
        assert result["xp_ganado"] == 0
        assert result["status"] == "rejected"


def test_check_no_deadline_raises(app, seeded):
    with app.app_context():
        cat = Category.query.first()
        h = Habit(
            nombre="Sin deadline",
            categoria_id=cat.id,
            dificultad="facil",
            xp_base=10,
            tipo_validacion="check",
            meta_type="boolean",
            xp_rate=0,
            max_xp_per_day=10,
        )
        db.session.add(h)
        db.session.flush()
        uh = UserHabit(
            usuario_id=seeded["user_id"],
            habito_id=h.id,
            activo=True,
            fecha_inicio=date.today(),
        )
        db.session.add(uh)
        db.session.commit()

        with pytest.raises(ValueError, match="deadline_time"):
            validate_habit(seeded["user_id"], uh.id, {})


# --- retry after rejection ---

def test_photo_rejected_allows_retry(app, seeded):
    """Rejected photo must not block a subsequent attempt on the same day."""
    with app.app_context():
        fake_b64 = "aGVsbG8="
        reject_resp = {"valido": False, "razon": "No hay evidencia.", "confianza": 0.85}
        approve_resp = {"valido": True, "razon": "Evidencia válida.", "confianza": 0.95}

        with patch("app.services.validation_service.analyze_habit_image", return_value=reject_resp):
            first = validate_habit(
                seeded["user_id"],
                seeded["uh_photo"],
                {"image_base64": fake_b64, "mime_type": "image/jpeg"},
            )

        assert first["valido"] is False
        assert first["status"] == "rejected"
        assert first["xp_ganado"] == 0

        with patch("app.services.validation_service.analyze_habit_image", return_value=approve_resp):
            second = validate_habit(
                seeded["user_id"],
                seeded["uh_photo"],
                {"image_base64": fake_b64, "mime_type": "image/jpeg"},
            )

        assert second["valido"] is True
        assert second["status"] == "approved"
        assert second["xp_ganado"] > 0

        logs = ValidationLog.query.filter_by(habitousuario_id=seeded["uh_photo"]).all()
        assert len(logs) == 2
        assert {log.status for log in logs} == {"rejected", "approved"}


def test_text_ai_rejected_allows_retry(app, seeded):
    """Rejected text_ai must not block a subsequent attempt on the same day."""
    with app.app_context():
        text = "Hoy escribí en mi diario sobre el día."
        reject_resp = {"valido": False, "razon": "Texto irrelevante.", "confianza": 0.7}
        approve_resp = {"valido": True, "razon": "Buen progreso.", "confianza": 0.9}

        with patch("app.services.validation_service.analyze_habit_text", return_value=reject_resp):
            first = validate_habit(seeded["user_id"], seeded["uh_text_ai"], {"text_content": text})

        assert first["valido"] is False
        assert first["status"] == "rejected"

        with patch("app.services.validation_service.analyze_habit_text", return_value=approve_resp):
            second = validate_habit(seeded["user_id"], seeded["uh_text_ai"], {"text_content": text})

        assert second["valido"] is True
        assert second["status"] == "approved"
        assert second["xp_ganado"] > 0


def test_check_failed_allows_retry(app, seeded):
    """check-type rejected by deadline must not block retry attempts."""
    with app.app_context():
        with patch("app.services.validation_service._get_current_time_str", return_value="09:00"):
            first = validate_habit(seeded["user_id"], seeded["uh_check_fail"], {})

        assert first["valido"] is False
        assert first["status"] == "rejected"

        # Second attempt must process without raising "Ya validaste"
        with patch("app.services.validation_service._get_current_time_str", return_value="10:00"):
            second = validate_habit(seeded["user_id"], seeded["uh_check_fail"], {})

        assert second["valido"] is False
        assert second["status"] == "rejected"


def test_pending_log_does_not_block_retry(app, seeded):
    """A stale pending ValidationLog for today must not block a new attempt."""
    with app.app_context():
        import json as _json
        stale = ValidationLog(
            habitousuario_id=seeded["uh_photo"],
            tipo_validacion="foto",
            evidencia=_json.dumps({"validation_type": "foto"}),
            status="pending",
            validado=False,
        )
        db.session.add(stale)
        db.session.commit()

        fake_b64 = "aGVsbG8="
        approve_resp = {"valido": True, "razon": "OK.", "confianza": 0.95}

        with patch("app.services.validation_service.analyze_habit_image", return_value=approve_resp):
            result = validate_habit(
                seeded["user_id"],
                seeded["uh_photo"],
                {"image_base64": fake_b64, "mime_type": "image/jpeg"},
            )

        assert result["valido"] is True
        assert result["status"] == "approved"


def test_approved_still_blocks_second_attempt(app, seeded):
    """Approved validation must block any subsequent attempt the same day."""
    with app.app_context():
        fake_b64 = "aGVsbG8="
        approve_resp = {"valido": True, "razon": "Evidencia válida.", "confianza": 0.95}

        with patch("app.services.validation_service.analyze_habit_image", return_value=approve_resp):
            validate_habit(
                seeded["user_id"],
                seeded["uh_photo"],
                {"image_base64": fake_b64, "mime_type": "image/jpeg"},
            )

        with pytest.raises(ValueError, match="Ya validaste este habito hoy"):
            with patch("app.services.validation_service.analyze_habit_image", return_value=approve_resp):
                validate_habit(
                    seeded["user_id"],
                    seeded["uh_photo"],
                    {"image_base64": fake_b64, "mime_type": "image/jpeg"},
                )


def test_photo_ai_exception_does_not_block_retry(app, seeded):
    """If AI throws during photo validation, rollback leaves no blocking record."""
    with app.app_context():
        fake_b64 = "aGVsbG8="

        with pytest.raises(RuntimeError):
            with patch(
                "app.services.validation_service.analyze_habit_image",
                side_effect=RuntimeError("OpenAI timeout"),
            ):
                validate_habit(
                    seeded["user_id"],
                    seeded["uh_photo"],
                    {"image_base64": fake_b64, "mime_type": "image/jpeg"},
                )

        # No committed record — next attempt must proceed
        approve_resp = {"valido": True, "razon": "OK.", "confianza": 0.95}
        with patch("app.services.validation_service.analyze_habit_image", return_value=approve_resp):
            result = validate_habit(
                seeded["user_id"],
                seeded["uh_photo"],
                {"image_base64": fake_b64, "mime_type": "image/jpeg"},
            )

        assert result["valido"] is True
        assert result["status"] == "approved"
