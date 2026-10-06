
import pytest
from datetime import date, timedelta, datetime, timezone
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.habit import Habit, Category
from app.models.user_habit import UserHabit
from app.models.checkin import CheckIn
from app.models.validation_log import ValidationLog
from app.services.streak_service import compute_current_streak
from app.services.validation_service import _apply_approved_progress

@pytest.fixture
def app():
    app_instance = create_app()
    app_instance.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })
    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()

@pytest.fixture
def user(app):
    with app.app_context():
        u = User(username="testuser", email="test@example.com")
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
            tipo_validacion="foto"
        )
        db.session.add(h)
        db.session.commit()
        return h.id

@pytest.fixture
def user_habit(app, user, habit):
    with app.app_context():
        # Set fecha_inicio to 5 days ago to allow simulated past check-ins
        past_date = date.today() - timedelta(days=5)
        uh = UserHabit(usuario_id=user, habito_id=habit, fecha_inicio=past_date, tipo_validacion="foto")
        db.session.add(uh)
        db.session.commit()
        return uh.id

def test_streak_with_approved_and_rejected_validations(app, user, user_habit):
    with app.app_context():
        today = date.today()
        yesterday = today - timedelta(days=1)
        uh_ids = [user_habit]

        # 1. Setup yesterday as completed
        ci_yesterday = CheckIn(habitousuario_id=user_habit, fecha=yesterday, completado=True)
        db.session.add(ci_yesterday)
        db.session.commit()

        # Check current streak as of today (should be 1 because yesterday was done)
        assert compute_current_streak(uh_ids, today) == 1

        # 2. Add a pending validation for today
        # We use a fixed date and ensure the log has that date in UTC
        today_dt = datetime.combine(today, datetime.now().time()).replace(tzinfo=timezone.utc)
        
        log_pending = ValidationLog(
            habitousuario_id=user_habit, 
            status="pending", 
            validado=False,
            fecha=today_dt
        )
        db.session.add(log_pending)
        db.session.commit()

        # Streak should still be 1 (pending grants nothing but doesn't break)
        assert compute_current_streak(uh_ids, today) == 1

        # 3. Approve validation
        log_pending.status = "approved"
        log_pending.validado = True
        _apply_approved_progress(user_habit, user, today)
        db.session.commit()

        # Streak should be 2 now
        assert compute_current_streak(uh_ids, today) == 2

        # 4. Add a rejected validation today (maybe a second try that failed?)
        log_rejected = ValidationLog(
            habitousuario_id=user_habit, 
            status="rejected", 
            validado=False,
            fecha=today_dt
        )
        db.session.add(log_rejected)
        db.session.commit()

        # Phase 6: A rejected validation today NO LONGER breaks the streak instantly.
        # User is allowed to re-validate before the day ends.
        assert compute_current_streak(uh_ids, today) == 2

def test_no_double_counting(app, user, user_habit):
    with app.app_context():
        today = date.today()
        
        # Apply progress twice
        xp1 = _apply_approved_progress(user_habit, user, today)
        xp2 = _apply_approved_progress(user_habit, user, today)

        assert xp1 > 0
        assert xp2 == 0
        
        checkins = CheckIn.query.filter_by(habitousuario_id=user_habit, fecha=today).all()
        assert len(checkins) == 1
