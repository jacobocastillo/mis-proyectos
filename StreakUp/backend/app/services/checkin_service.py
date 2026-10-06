"""
Check-in service module.

Responsibility:
- Toggle daily check-ins for habits.
- Query today's habits with completion status.
"""

from datetime import date as date_type

from app.extensions import db
from app.models.checkin import CheckIn
from app.models.user_habit import UserHabit
from app.services.habit_service import list_active_user_habits, serialize_user_habit
from app.services.xp_service import award_xp, award_habit_xp, revoke_xp

def is_eligible_today(user_habit: UserHabit, target_date: date_type) -> bool:
    """Determine if a habit is eligible to be completed on a given date based on its frequency."""
    freq = user_habit.frecuencia or "daily"
    if freq == "daily":
        return True
    
    if freq == "weekly":
        # Weekly habits are eligible as long as they haven't been completed this week,
        # OR if they were completed exactly on target_date (so we can uncheck them).
        iso_year, iso_week, _ = target_date.isocalendar()
        start_of_week = date_type.fromisocalendar(iso_year, iso_week, 1)
        end_of_week = date_type.fromisocalendar(iso_year, iso_week, 7)
        # Check if completed this week
        weekly_checkin = CheckIn.query.filter(
            CheckIn.habitousuario_id == user_habit.id,
            CheckIn.completado == True,
            CheckIn.fecha >= start_of_week,
            CheckIn.fecha <= end_of_week
        ).first()
        
        if weekly_checkin:
            return weekly_checkin.fecha == target_date
        return True

    if freq == "custom":
        if not user_habit.schedule_days:
            return False
        enabled_weekdays = {day.weekday for day in user_habit.schedule_days}
        return target_date.weekday() in enabled_weekdays

    return True


def _is_validation_driven(user_habit: UserHabit) -> bool:
    validation_type = user_habit.tipo_validacion or user_habit.habit.tipo_validacion
    if validation_type == "check" and not user_habit.deadline_time:
        return False
    return validation_type in {"foto", "texto", "tiempo", "photo", "text_ai", "time", "check"}


def toggle_checkin(
    user_id: int,
    habit_id: int,
    target_date: date_type | None = None,
    *,
    commit: bool = True,
) -> dict:
    """Toggle a check-in for a habit on a given date."""
    if target_date is None:
        target_date = date_type.today()

    user_habit = UserHabit.query.filter_by(
        id=habit_id,
        usuario_id=user_id,
        activo=True,
    ).first()
    if user_habit is None:
        raise LookupError("Habit not found.")
    
    if not is_eligible_today(user_habit, target_date):
        raise ValueError("Este hábito no está programado para hoy.")

    if _is_validation_driven(user_habit):
        raise ValueError("This habit requires validation before progress can be granted.")

    try:
        existing = CheckIn.query.filter_by(
            habitousuario_id=user_habit.id,
            fecha=target_date,
        ).first()

        if existing:
            xp_to_revoke = existing.xp_ganado
            db.session.delete(existing)
            if xp_to_revoke > 0:
                revoke_xp(user_id, xp_to_revoke, "checkin_undo", commit=False)
            if commit:
                db.session.commit()
            else:
                db.session.flush()
            return {"checked": False, "habit_id": habit_id, "date": target_date.isoformat()}

        awarded_xp = award_habit_xp(user_id, user_habit, target_date, reason="checkin", commit=False)
        checkin = CheckIn(
            habitousuario_id=user_habit.id,
            fecha=target_date,
            completado=True,
            xp_ganado=awarded_xp,
        )
        db.session.add(checkin)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return {"checked": True, "habit_id": habit_id, "date": target_date.isoformat()}
    except Exception:
        db.session.rollback()
        raise


def get_today_habits(user_id: int, target_date: date_type | None = None) -> list[dict]:
    """Return all active habits with their check-in status for today."""
    if target_date is None:
        target_date = date_type.today()

    user_habits = list_active_user_habits(user_id)
    user_habit_ids = [uh.id for uh in user_habits]
    if user_habit_ids:
        checkins = CheckIn.query.filter(
            CheckIn.habitousuario_id.in_(user_habit_ids),
            CheckIn.fecha == target_date,
        ).all()
        checked_ids = {checkin.habitousuario_id for checkin in checkins}
    else:
        checked_ids = set()

    result = []
    for user_habit in user_habits:
        if not is_eligible_today(user_habit, target_date):
            continue
            
        habit_dict = serialize_user_habit(user_habit)
        habit_dict["checked_today"] = user_habit.id in checked_ids
        result.append(habit_dict)

    return result
