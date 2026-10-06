"""
Habit service module.

Responsibility:
- Host catalog and user-assignment habit use cases.
"""

from decimal import Decimal
from datetime import date as date_type, datetime, timezone

from app.extensions import db
from app.models.habit import Habit
from app.models.user_habit import UserHabit
from app.models.user_habit_schedule import UserHabitScheduleDay
from app.services.catalog_bootstrap_service import DEFAULT_HABIT_IDS


_CATEGORY_PRESENTATION = {
    1: {"section": "moon", "icon": "Moon"},
    2: {"section": "plant", "icon": "Sprout"},
    3: {"section": "fire", "icon": "Flame"},
}

_HABIT_ICONS = {
    1: "Droplets",
    2: "Dumbbell",
    3: "Apple",
    4: "Brain",
    5: "Smile",
    6: "Laptop",
    7: "Target",
    8: "Sunrise",
    9: "BookOpen",
    10: "Globe",
    11: "BedDouble",
    12: "Moon",
    13: "PenLine",
    14: "GraduationCap",
}

_CATALOG_ORDER = {habit_id: index for index, habit_id in enumerate(DEFAULT_HABIT_IDS)}


class HabitConfigurationError(ValueError):
    """Raised when user habit configuration violates catalog requirements."""

def _get_presentation(category_id: int) -> dict[str, str]:
    return _CATEGORY_PRESENTATION.get(category_id, {"section": "fire", "icon": "Flame"})


def list_catalog_habits() -> list[dict]:
    """Return the seeded habit catalog."""
    habits = Habit.query.filter_by(activo=True).all()
    habits.sort(key=lambda habit: _CATALOG_ORDER.get(habit.id, len(_CATALOG_ORDER)))
    return [habit.to_dict() for habit in habits]


def get_catalog_habit(habit_id: int) -> Habit | None:
    """Return a catalog habit by id."""
    return Habit.query.filter_by(id=habit_id).first()


def list_active_user_habits(user_id: int) -> list[UserHabit]:
    """Return active user-habit assignments ordered for UI display."""
    return (
        UserHabit.query
        .filter_by(usuario_id=user_id, activo=True)
        .join(Habit, UserHabit.habito_id == Habit.id)
        .order_by(Habit.categoria_id, Habit.nombre)
        .all()
    )


def get_user_habit(habit_id: int, user_id: int, active_only: bool = True) -> UserHabit | None:
    """Return a user-habit assignment for the given user."""
    query = UserHabit.query.filter_by(id=habit_id, usuario_id=user_id)
    if active_only:
        query = query.filter_by(activo=True)
    return query.first()


def _effective_validation_type(user_habit: UserHabit) -> str:
    return user_habit.tipo_validacion or user_habit.habit.tipo_validacion


def _effective_frequency(user_habit: UserHabit) -> str:
    return user_habit.frecuencia or user_habit.habit.frecuencia


def _json_number(value: object) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    return value


def _effective_quantity_target(user_habit: UserHabit) -> Decimal | None:
    return (
        user_habit.cantidad_objetivo
        if user_habit.cantidad_objetivo is not None
        else user_habit.habit.cantidad_objetivo
    )


def _effective_duration_target(user_habit: UserHabit) -> int | None:
    return (
        user_habit.duracion_objetivo_minutos
        if user_habit.duracion_objetivo_minutos is not None
        else user_habit.habit.duracion_objetivo_minutos
    )


def _effective_target_unit(user_habit: UserHabit) -> str | None:
    return (
        user_habit.unidad_objetivo
        if user_habit.unidad_objetivo is not None
        else user_habit.habit.unidad_objetivo
    )


def _effective_deadline_time(user_habit: UserHabit) -> str | None:
    return user_habit.deadline_time


def _effective_name(user_habit: UserHabit) -> str:
    return user_habit.nombre_personalizado or user_habit.habit.nombre


def _effective_description(user_habit: UserHabit) -> str | None:
    return (
        user_habit.descripcion_personalizada
        if user_habit.descripcion_personalizada is not None
        else user_habit.habit.descripcion
    )


def _derive_habit_type(
    validation_type: str,
    *,
    target_quantity: Decimal | None,
    target_duration: int | None,
) -> str:
    if validation_type in {"tiempo", "time"} or target_duration is not None:
        return "time"
    if target_quantity is not None:
        return "quantity"
    return "boolean"


def serialize_user_habit(user_habit: UserHabit) -> dict:
    """Return a frontend-compatible representation of an assigned habit."""
    catalog_habit = user_habit.habit
    presentation = _get_presentation(catalog_habit.categoria_id)
    created_at = user_habit.fecha_creacion.isoformat() if user_habit.fecha_creacion else None
    updated_at = (
        user_habit.fecha_actualizacion.isoformat()
        if user_habit.fecha_actualizacion
        else created_at
    )
    validation_type = _effective_validation_type(user_habit)
    frequency = _effective_frequency(user_habit)
    target_quantity = _effective_quantity_target(user_habit)
    target_duration = _effective_duration_target(user_habit)
    target_unit = _effective_target_unit(user_habit)
    deadline_time = _effective_deadline_time(user_habit)
    custom_name = user_habit.nombre_personalizado
    custom_description = user_habit.descripcion_personalizada
    habit_type = _derive_habit_type(
        validation_type,
        target_quantity=target_quantity,
        target_duration=target_duration,
    )

    return {
        "id": user_habit.id,
        "catalog_habit_id": catalog_habit.id,
        "category_id": catalog_habit.categoria_id,
        "category_name": catalog_habit.category.nombre if catalog_habit.category else None,
        "user_id": user_habit.usuario_id,
        "name": _effective_name(user_habit),
        "custom_name": custom_name,
        "description": _effective_description(user_habit),
        "custom_description": custom_description,
        "difficulty": catalog_habit.dificultad,
        "xp_base": catalog_habit.xp_base,
        "active": bool(user_habit.activo),
        "start_date": user_habit.fecha_inicio.isoformat() if user_habit.fecha_inicio else None,
        "end_date": user_habit.fecha_fin.isoformat() if user_habit.fecha_fin else None,
        "icon": _HABIT_ICONS.get(catalog_habit.id, presentation["icon"]),
        "validation_type": validation_type,
        "habit_type": habit_type,
        "frequency": frequency,
        "section": presentation["section"],
        "target_duration": target_duration,
        "pomodoro_enabled": validation_type in {"tiempo", "time"},
        "target_quantity": _json_number(target_quantity),
        "target_unit": target_unit,
        "deadline_time": deadline_time,
        "min_text_length": user_habit.min_text_length,
        "schedule_days": [
            row.weekday
            for row in UserHabitScheduleDay.query.filter_by(
                habitousuario_id=user_habit.id
            ).order_by(UserHabitScheduleDay.weekday).all()
        ],
        "created_at": created_at,
        "updated_at": updated_at,
    }


def get_habits(user_id: int) -> list[dict]:
    """Compatibility wrapper used by the existing frontend habits list."""
    return [serialize_user_habit(user_habit) for user_habit in list_active_user_habits(user_id)]


def get_user_habit_payload(habit_id: int, user_id: int, active_only: bool = True) -> dict | None:
    """Return a serialized user-habit assignment."""
    user_habit = get_user_habit(habit_id, user_id, active_only=active_only)
    if user_habit is None:
        return None
    return serialize_user_habit(user_habit)


def _apply_user_habit_overrides(user_habit: UserHabit, overrides: dict[str, object]) -> None:
    if "custom_name" in overrides:
        user_habit.nombre_personalizado = overrides["custom_name"]
    if "description" in overrides:
        user_habit.descripcion_personalizada = overrides["description"]
    if "validation_type" in overrides:
        user_habit.tipo_validacion = overrides["validation_type"]
    if "frequency" in overrides:
        user_habit.frecuencia = overrides["frequency"]
    if "target_quantity" in overrides:
        user_habit.cantidad_objetivo = overrides["target_quantity"]
    if "target_unit" in overrides:
        user_habit.unidad_objetivo = overrides["target_unit"]
    if "target_duration" in overrides:
        user_habit.duracion_objetivo_minutos = overrides["target_duration"]
    if "deadline_time" in overrides:
        user_habit.deadline_time = overrides["deadline_time"]
    if "min_text_length" in overrides:
        user_habit.min_text_length = overrides["min_text_length"]
    if "schedule_days" in overrides:
        # Replace all existing schedule rows for this habit in-place
        UserHabitScheduleDay.query.filter_by(
            habitousuario_id=user_habit.id
        ).delete(synchronize_session=False)
        new_days: list[int] = overrides["schedule_days"] or []
        for weekday in new_days:
            db.session.add(
                UserHabitScheduleDay(
                    habitousuario_id=user_habit.id,
                    weekday=weekday,
                )
            )

    user_habit.fecha_actualizacion = datetime.now(timezone.utc)


def _effective_config_after_update(
    user_habit: UserHabit,
    updates: dict[str, object],
    catalog_habit: Habit | None = None,
) -> dict[str, object]:
    habit = catalog_habit or user_habit.habit
    return {
        "target_quantity": (
            updates["target_quantity"]
            if "target_quantity" in updates
            else (
                user_habit.cantidad_objetivo
                if user_habit.cantidad_objetivo is not None
                else habit.cantidad_objetivo
            )
        ),
        "target_unit": (
            updates["target_unit"]
            if "target_unit" in updates
            else (
                user_habit.unidad_objetivo
                if user_habit.unidad_objetivo is not None
                else habit.unidad_objetivo
            )
        ),
        "target_duration": (
            updates["target_duration"]
            if "target_duration" in updates
            else (
                user_habit.duracion_objetivo_minutos
                if user_habit.duracion_objetivo_minutos is not None
                else habit.duracion_objetivo_minutos
            )
        ),
        "deadline_time": (
            updates["deadline_time"]
            if "deadline_time" in updates
            else _effective_deadline_time(user_habit)
        ),
    }


def _validate_point_a_config(catalog_habit: Habit, config: dict[str, object]) -> None:
    meta_type = catalog_habit.meta_type
    validation_type = catalog_habit.tipo_validacion

    if meta_type == "quantity_liters":
        quantity = config["target_quantity"]
        if quantity is None or Decimal(str(quantity)) <= 0:
            raise HabitConfigurationError("target_quantity greater than zero is required for this habit.")
        if config["target_unit"] is None:
            config["target_unit"] = "litros"

    if meta_type == "minutes":
        duration = config["target_duration"]
        if duration is None or int(duration) <= 0:
            raise HabitConfigurationError("target_duration greater than zero is required for this habit.")

    if validation_type == "check":
        if config["deadline_time"] is None:
            raise HabitConfigurationError("deadline_time is required for this habit.")


def assign_habit_to_user(user_id: int, habito_id: int, overrides: dict[str, object] | None = None) -> dict:
    """Assign a catalog habit to a user as an active habit."""
    catalog_habit = get_catalog_habit(habito_id)
    if catalog_habit is None:
        raise LookupError("Habit catalog entry not found.")

    existing = UserHabit.query.filter_by(
        usuario_id=user_id,
        habito_id=habito_id,
        activo=True,
    ).first()
    if existing is not None:
        raise ValueError("This habit is already active for the user.")

    user_habit = UserHabit(
        usuario_id=user_id,
        habito_id=habito_id,
        fecha_inicio=date_type.today(),
        activo=True,
    )
    effective_config = _effective_config_after_update(user_habit, overrides or {}, catalog_habit)
    _validate_point_a_config(catalog_habit, effective_config)
    db.session.add(user_habit)
    # Flush to get the PK so schedule_days can reference user_habit.id
    db.session.flush()
    if overrides:
        overrides = {**overrides, **effective_config}
        _apply_user_habit_overrides(user_habit, overrides)
    db.session.commit()
    return serialize_user_habit(user_habit)


def update_user_habit(habit_id: int, user_id: int, updates: dict[str, object]) -> dict:
    """Update user-specific overrides for an assigned habit."""
    user_habit = get_user_habit(habit_id, user_id, active_only=True)
    if user_habit is None:
        raise LookupError("Habit not found.")

    effective_config = _effective_config_after_update(user_habit, updates)
    _validate_point_a_config(user_habit.habit, effective_config)
    updates = {**updates, **effective_config}
    _apply_user_habit_overrides(user_habit, updates)
    db.session.commit()
    return serialize_user_habit(user_habit)


def deactivate_user_habit(habit_id: int, user_id: int) -> bool:
    """Deactivate a user-habit assignment without deleting the catalog row."""
    user_habit = get_user_habit(habit_id, user_id, active_only=True)
    if user_habit is None:
        return False

    user_habit.activo = False
    user_habit.fecha_fin = date_type.today()
    db.session.commit()
    return True
