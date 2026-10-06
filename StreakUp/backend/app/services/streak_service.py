"""
Streak service placeholder module.

Responsibility:
- Host streak computation and streak-related domain workflows.

Should contain:
- Streak progression/reset business rules.
- Domain orchestration helpers.

Should NOT contain:
- Flask blueprint code.
- Raw database schema declarations.
- Cross-cutting infrastructure setup.
"""

from datetime import date as date_type, datetime, timedelta, timezone

from app.models.checkin import CheckIn
from app.models.validation_log import ValidationLog
from app.models.user_habit import UserHabit
from app.extensions import db

_LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo or timezone.utc

def _to_local_date(value: datetime | None) -> date_type | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_LOCAL_TIMEZONE).date()


def _compute_habit_streaks(user_habit: UserHabit, today: date_type) -> tuple[int, int]:
    """Compute the current and longest streak for a single habit based on its frequency."""
    freq = user_habit.frecuencia or "daily"
    fecha_inicio = user_habit.fecha_inicio
    if not fecha_inicio:
        return 0, 0
    
    # fetch all approved checkins for this habit up to today
    checkins = CheckIn.query.filter(
        CheckIn.habitousuario_id == user_habit.id,
        CheckIn.completado == True,
        CheckIn.fecha >= fecha_inicio,
        CheckIn.fecha <= today
    ).all()
    checkin_dates = {c.fecha for c in checkins}

    current_streak = 0
    longest_streak = 0

    if freq in ("daily", "custom"):
        if freq == "custom" and user_habit.schedule_days:
            enabled_weekdays = {sd.weekday for sd in user_habit.schedule_days}
        else:
            enabled_weekdays = set(range(7))

        curr_date = fecha_inicio
        while curr_date <= today:
            if curr_date.weekday() in enabled_weekdays:
                if curr_date in checkin_dates:
                    current_streak += 1
                    if current_streak > longest_streak:
                        longest_streak = current_streak
                else:
                    if curr_date < today:
                        current_streak = 0
            curr_date += timedelta(days=1)
            
    elif freq == "weekly":
        iso_y, iso_w, _ = fecha_inicio.isocalendar()
        curr_week_start = date_type.fromisocalendar(iso_y, iso_w, 1)
        
        iso_y_end, iso_w_end, _ = today.isocalendar()
        end_week_start = date_type.fromisocalendar(iso_y_end, iso_w_end, 1)
        
        while curr_week_start <= end_week_start:
            curr_week_end = curr_week_start + timedelta(days=6)
            checked = any(curr_week_start <= d <= curr_week_end for d in checkin_dates)
            
            if checked:
                current_streak += 1
                if current_streak > longest_streak:
                    longest_streak = current_streak
            else:
                if curr_week_start < end_week_start:
                    current_streak = 0
            
            curr_week_start += timedelta(weeks=1)

    return current_streak, longest_streak


def compute_current_streak(uh_ids: list[int], today: date_type) -> int:
    """Compute the global current streak (max of all individual current streaks)."""
    if not uh_ids:
        return 0

    user_habits = db.session.query(UserHabit).filter(UserHabit.id.in_(uh_ids)).all()
    
    max_streak = 0
    for uh in user_habits:
        curr, _ = _compute_habit_streaks(uh, today)
        if curr > max_streak:
            max_streak = curr

    return max_streak


def compute_longest_streak(uh_ids: list[int]) -> int:
    """Compute the global longest streak (max of all individual longest streaks)."""
    if not uh_ids:
        return 0

    user_habits = db.session.query(UserHabit).filter(UserHabit.id.in_(uh_ids)).all()
    
    max_longest = 0
    for uh in user_habits:
        _, longest = _compute_habit_streaks(uh, date_type.today())
        if longest > max_longest:
            max_longest = longest

    return max_longest
