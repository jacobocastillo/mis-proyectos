import pytest
from app import create_app
import base64

@pytest.fixture
def app():
    app_instance = create_app()
    app_instance.config.update({"TESTING": True})
    return app_instance

@pytest.fixture
def client(app):
    return app.test_client()

def test_validation_route(client, monkeypatch):
    import flask_jwt_extended
    monkeypatch.setattr(flask_jwt_extended, "verify_jwt_in_request", lambda *a, **kw: None)
    monkeypatch.setattr(flask_jwt_extended, "get_jwt_identity", lambda: "1")
    
    from app.extensions import db
    from app.models.user import User
    from app.models.habit import Habit, Category
    from app.models.user_habit import UserHabit
    from datetime import date
    
    with client.application.app_context():
        db.create_all()
        u = db.session.get(User, 1)
        if not u:
            u = User(username="test", email="test@test.com")
            u.set_password("password")
            db.session.add(u)
        c = Category.query.filter_by(nombre="cat").first()
        if not c:
            c = Category(nombre="cat")
            db.session.add(c)
        h = db.session.get(Habit, 1)
        if not h:
            h = Habit(
                nombre="Beber Agua",
                categoria_id=c.id,
                dificultad="media",
                xp_base=10,
                tipo_validacion="foto",
                frecuencia="daily",
            )
            db.session.add(h)
        db.session.commit()
        uh_q = UserHabit.query.filter_by(usuario_id=u.id, habito_id=h.id).first()
        if not uh_q:
            uh = UserHabit(user=u, habit=h, fecha_inicio=date.today())
            db.session.add(uh)
            db.session.commit()

    payload = {
        "habit_id": 1,
        "image_base64": base64.b64encode(b"abcd").decode("utf-8"),
        "mime_type": "image/png"
    }

    resp = client.post("/api/habits/validate", json=payload)
    print("STATUS", resp.status_code)
    print("OUTPUT", resp.get_json())
    assert resp.status_code != 500
