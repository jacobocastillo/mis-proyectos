import pytest
from app import create_app
from app.models.user import User
from app.models.habit import Habit, Category
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.services.validation_service import validate_habit
from app.extensions import db

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
def setup_validation_records(app):
    with app.app_context():
        user = User(username="valuser", email="valuser@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        cat = Category(nombre="Health")
        db.session.add(cat)
        db.session.commit()
        
        habit1 = Habit(nombre="Habit Text", categoria_id=cat.id, tipo_validacion="texto", dificultad="media", xp_base=10)
        habit2 = Habit(nombre="Habit Time", categoria_id=cat.id, tipo_validacion="tiempo", dificultad="media", xp_base=10)
        habit3 = Habit(nombre="Habit Photo", categoria_id=cat.id, tipo_validacion="foto", dificultad="media", xp_base=10)
        
        db.session.add_all([habit1, habit2, habit3])
        db.session.commit()
        
        from datetime import date
        today = date.today()
        uh_text = UserHabit(usuario_id=user.id, habito_id=habit1.id, tipo_validacion="texto", min_text_length=15, activo=True, fecha_inicio=today)
        uh_time = UserHabit(usuario_id=user.id, habito_id=habit2.id, tipo_validacion="tiempo", duracion_objetivo_minutos=10, activo=True, fecha_inicio=today)
        uh_photo = UserHabit(usuario_id=user.id, habito_id=habit3.id, tipo_validacion="foto", activo=True, fecha_inicio=today)
        
        db.session.add_all([uh_text, uh_time, uh_photo])
        db.session.commit()
        
        return {
            "user": user.id,
            "habit_text": habit1.id,
            "habit_time": habit2.id,
            "habit_photo": habit3.id
        }

def test_validation_texto(app, setup_validation_records):
    # Success text
    with app.app_context():
        payload = {"text_content": "This is a super long valid text of at least fifteen chars."}
        res = validate_habit(setup_validation_records["user"], setup_validation_records["habit_text"], payload)
        assert res["valido"] is True
        assert res["xp_ganado"] > 0
        
        vlog = ValidationLog.query.filter_by(tipo_validacion="texto").first()
        import json
        ev = json.loads(vlog.evidencia)
        assert ev["text_length"] >= 15
        assert ev["validation_type"] == "texto"

def test_validation_texto_fails_length(app, setup_validation_records):
    # Too short
    with app.app_context():
        payload = {"text_content": "Short text"}
        with pytest.raises(ValueError, match="El texto debe tener al menos"):
            validate_habit(setup_validation_records["user"], setup_validation_records["habit_text"], payload)

def test_validation_tiempo(app, setup_validation_records):
    with app.app_context():
        payload = {"duration_minutes": 15}
        res = validate_habit(setup_validation_records["user"], setup_validation_records["habit_time"], payload)
        assert res["valido"] is True
        
        vlog = ValidationLog.query.filter_by(tipo_validacion="tiempo").first()
        import json
        ev = json.loads(vlog.evidencia)
        assert ev["duration_minutes"] == 15

def test_validation_tiempo_fails_duration(app, setup_validation_records):
    with app.app_context():
        payload = {"duration_minutes": 5}
        with pytest.raises(ValueError, match="Debes completar al menos 10"):
            validate_habit(setup_validation_records["user"], setup_validation_records["habit_time"], payload)

def test_validation_photo_missing(app, setup_validation_records):
    with app.app_context():
        payload = {"dummy": "data"}
        with pytest.raises(ValueError, match="image .base64. is required"):
            validate_habit(setup_validation_records["user"], setup_validation_records["habit_photo"], payload)
