import pytest
from datetime import date, timedelta
from app.models.user_habit import UserHabit
from app.models.checkin import CheckIn
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.habit import Habit
from app.services.checkin_service import is_eligible_today
from app.models.user_habit_schedule import UserHabitScheduleDay

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
def test_user(app):
    with app.app_context():
        user = User(username="test_schedule", email="schedule@test.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        return user

def test_daily_eligibility(app):
    with app.app_context():
        user = User(username="test_daily", email="daily@test.com")
        user.set_password("pass")
        db.session.add(user)
        
        habit_base = Habit(nombre="Habit Base", categoria_id=1)
        # Assuming category is not fk constrained strictly or we need to add a category? Let's just create a mock habit. Actually, categoria_id is a foreign key too in our DB design!
        from app.models.habit import Category
        cat = Category(nombre="Test Cat")
        db.session.add(cat)
        db.session.commit()
        
        habit_base = Habit(nombre="Habit Base", categoria_id=cat.id, dificultad="media", xp_base=10)
        db.session.add(habit_base)
        db.session.commit()

        habit = UserHabit(usuario_id=user.id, habito_id=habit_base.id, fecha_inicio=date.today(), frecuencia="daily", activo=True)
        assert is_eligible_today(habit, date.today()) is True

def test_custom_eligibility(app):
    with app.app_context():
        user = User(username="test_custom", email="custom@test.com")
        user.set_password("pass")
        db.session.add(user)
        from app.models.habit import Category
        cat = Category(nombre="Test Cat")
        db.session.add(cat)
        db.session.commit()
        habit_base = Habit(nombre="Habit Base", categoria_id=cat.id, dificultad="media", xp_base=10)
        db.session.add(habit_base)
        db.session.commit()
        
        habit = UserHabit(usuario_id=user.id, habito_id=habit_base.id, fecha_inicio=date.today(), frecuencia="custom", activo=True)
        db.session.add(habit)
        db.session.flush()

        today = date.today()
        weekday = today.weekday()

        # Add today to schedule
        schedule = UserHabitScheduleDay(habitousuario_id=habit.id, weekday=weekday)
        habit.schedule_days.append(schedule)
        
        assert is_eligible_today(habit, today) is True

        # Check tomorrow (not in schedule)
        tomorrow = today + timedelta(days=1)
        if tomorrow.weekday() != weekday:
            assert is_eligible_today(habit, tomorrow) is False

def test_custom_without_schedule_is_not_eligible(app):
    with app.app_context():
        user = User(username="test_custom_empty", email="custom-empty@test.com")
        user.set_password("pass")
        db.session.add(user)
        from app.models.habit import Category
        cat = Category(nombre="Test Cat")
        db.session.add(cat)
        db.session.commit()
        habit_base = Habit(nombre="Habit Base", categoria_id=cat.id, dificultad="media", xp_base=10)
        db.session.add(habit_base)
        db.session.commit()

        habit = UserHabit(
            usuario_id=user.id,
            habito_id=habit_base.id,
            fecha_inicio=date.today(),
            frecuencia="custom",
            activo=True,
        )
        db.session.add(habit)
        db.session.flush()

        assert is_eligible_today(habit, date.today()) is False

def test_weekly_eligibility(app):
    with app.app_context():
        user = User(username="test_weekly", email="weekly@test.com")
        user.set_password("pass")
        db.session.add(user)
        from app.models.habit import Category
        cat = Category(nombre="Test Cat")
        db.session.add(cat)
        db.session.commit()
        habit_base = Habit(nombre="Habit Base", categoria_id=cat.id, dificultad="media", xp_base=10)
        db.session.add(habit_base)
        db.session.commit()
        
        habit = UserHabit(usuario_id=user.id, habito_id=habit_base.id, fecha_inicio=date.today(), frecuencia="weekly", activo=True)
        db.session.add(habit)
        db.session.flush()
        
        today = date.today()
        # It should be eligible
        assert is_eligible_today(habit, today) is True
        
        # Complete it today
        checkin = CheckIn(habitousuario_id=habit.id, fecha=today, completado=True, xp_ganado=10)
        db.session.add(checkin)
        db.session.flush()
        
        # Still eligible on the same day (to uncheck)
        assert is_eligible_today(habit, today) is True
        
        # Not eligible tomorrow (since it's completed this week)
        tomorrow = today + timedelta(days=1)
        # If tomorrow is still in the same ISO week
        if today.isocalendar()[1] == tomorrow.isocalendar()[1]:
            assert is_eligible_today(habit, tomorrow) is False
