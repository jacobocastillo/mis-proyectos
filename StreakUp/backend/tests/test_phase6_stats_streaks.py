import pytest
from datetime import date, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.habit import Habit, Category
from app.models.user_habit import UserHabit
from app.models.user_habit_schedule import UserHabitScheduleDay
from app.models.checkin import CheckIn
from app.services.streak_service import compute_current_streak
from app.services.stats_service import get_summary, get_detailed_stats

@pytest.fixture
def app():
    app_instance = create_app()
    app_instance.config.update({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()

@pytest.fixture
def test_user(app):
    with app.app_context():
        u = User(username="stats_user", email="stats@example.com")
        u.set_password("pass")
        db.session.add(u)
        db.session.commit()
        return u.id

@pytest.fixture
def test_habits(app):
    with app.app_context():
        cat = Category(nombre="Health")
        db.session.add(cat)
        db.session.flush()
        
        h_daily = Habit(nombre="Daily Habit", categoria_id=cat.id, frecuencia="daily", xp_base=10, dificultad="media", tipo_validacion="foto")
        h_weekly = Habit(nombre="Weekly Habit", categoria_id=cat.id, frecuencia="weekly", xp_base=10, dificultad="media", tipo_validacion="foto")
        h_custom = Habit(nombre="Custom Habit", categoria_id=cat.id, frecuencia="daily", xp_base=10, dificultad="media", tipo_validacion="foto")
        
        db.session.add_all([h_daily, h_weekly, h_custom])
        db.session.commit()
        return h_daily.id, h_weekly.id, h_custom.id

def test_streak_and_stats_frequency_aware(app, test_user, test_habits):
    with app.app_context():
        h_daily, h_weekly, h_custom = test_habits
        today = date.today()
        past_date = today - timedelta(days=14)
        
        uh_daily = UserHabit(usuario_id=test_user, habito_id=h_daily, fecha_inicio=past_date, frecuencia="daily")
        uh_weekly = UserHabit(usuario_id=test_user, habito_id=h_weekly, fecha_inicio=past_date, frecuencia="weekly")
        uh_custom = UserHabit(usuario_id=test_user, habito_id=h_custom, fecha_inicio=past_date, frecuencia="custom")
        
        db.session.add_all([uh_daily, uh_weekly, uh_custom])
        db.session.flush()
        
        # Add custom schedule (e.g. today's weekday only, to guarantee it's eligible today)
        today_weekday = today.weekday()
        sd = UserHabitScheduleDay(habitousuario_id=uh_custom.id, weekday=today_weekday)
        db.session.add(sd)
        db.session.commit()

        # Insert check-ins
        # Daily: checked yesterday and today (streak: 2)
        db.session.add(CheckIn(habitousuario_id=uh_daily.id, fecha=today, completado=True))
        db.session.add(CheckIn(habitousuario_id=uh_daily.id, fecha=today - timedelta(days=1), completado=True))
        
        # Weekly: checked exactly one week ago (streak: 1 so far, because this week is not checked yet but grace period applies)
        past_week_date = today - timedelta(days=7)
        db.session.add(CheckIn(habitousuario_id=uh_weekly.id, fecha=past_week_date, completado=True))
        
        # Custom: checked today (streak: 1)
        db.session.add(CheckIn(habitousuario_id=uh_custom.id, fecha=today, completado=True))
        
        db.session.commit()

        # Validate Streak
        # Max streak should be 2 (from daily habit)
        uh_ids = [uh_daily.id, uh_weekly.id, uh_custom.id]
        global_streak = compute_current_streak(uh_ids, today)
        assert global_streak == 2, f"Expected 2 (from daily), got {global_streak}"
        
        # Validate Stats
        summary = get_summary(test_user)
        # Week possible: Daily (7) + Weekly (1) + Custom (1) = 9
        # Week checkins: Daily (2 - today and yesterday) + Weekly (1 - if past_week_date is within 7 days, it's 1, otherwise 0. 7 days ago is within the sliding window) + Custom (1) = 4
        # Wait: today - 7 might not be in the last 7 sliding days (which is today - 6 to today).
        # range(7) is 0 to 6, meaning today-0 to today-6.
        # So past_week_date (today-7) is OUTSIDE the last 7 sliding days in stats!!!
        
        assert summary["streak"] == 2
        # completion rate should not be assuming total_habits * 7 = 21. It should be 9.
        # Let's check detailed stats
        detailed = get_detailed_stats(test_user)
        
        daily_stat = next(p for p in detailed["per_habit"] if p["id"] == uh_daily.id)
        assert daily_stat["total"] == 7
        
        weekly_stat = next(p for p in detailed["per_habit"] if p["id"] == uh_weekly.id)
        assert weekly_stat["total"] == 1
        
        custom_stat = next(p for p in detailed["per_habit"] if p["id"] == uh_custom.id)
        assert custom_stat["total"] == 1 # since it only has 1 schedule_day
