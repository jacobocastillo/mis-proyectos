"""
Legacy SQLite audit and migration service.

Responsibility:
- Audit a pre-Alembic SQLite database before migration.
- Import legacy SQLite data into the current SQLAlchemy-managed schema.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.extensions import db
from app.models.checkin import CheckIn
from app.models.habit import Category, Habit
from app.models.pomodoro_session import PomodoroSession
from app.models.user import User
from app.models.user_habit import UserHabit
from app.models.validation_log import ValidationLog
from app.models.xp_log import XpLog
from app.services.xp_service import XP_PER_LEVEL, normalize_xp_reason, recompute_all_users_xp

_REQUIRED_SOURCE_TABLES = (
    "users",
    "categorias",
    "habitos",
    "habitos_usuario",
    "registro_habitos",
    "validaciones",
    "xp_logs",
)
_OPTIONAL_SOURCE_TABLES = ("pomodoro_sessions", "niveles", "alembic_version")
_TARGET_TABLES = (
    "users",
    "categorias",
    "habitos",
    "habitos_usuario",
    "registro_habitos",
    "validaciones",
    "xp_logs",
    "pomodoro_sessions",
    "niveles",
)


def audit_legacy_sqlite(sqlite_path: str | Path) -> dict[str, Any]:
    """Inspect a legacy SQLite file and report migration blockers."""
    source_path = _resolve_sqlite_path(sqlite_path)
    with _connect_sqlite(source_path) as connection:
        table_names = _get_table_names(connection)
        counts = {
            table: _count_rows(connection, table_names, table)
            for table in _REQUIRED_SOURCE_TABLES + _OPTIONAL_SOURCE_TABLES
        }
        integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_violations = [list(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]

        xp_mismatches: list[dict[str, Any]] = []
        if {"users", "xp_logs"}.issubset(table_names):
            for row in connection.execute(
                """
                SELECT u.id, u.username, u.total_xp, u.level, u.xp_in_level,
                       COALESCE(SUM(x.cantidad), 0) AS xp_logs_total
                FROM users u
                LEFT JOIN xp_logs x ON x.usuario_id = u.id
                GROUP BY u.id, u.username, u.total_xp, u.level, u.xp_in_level
                ORDER BY u.id
                """
            ).fetchall():
                expected_total = max(0, int(row[5] or 0))
                expected_level = (expected_total // XP_PER_LEVEL) + 1
                expected_xp_in_level = expected_total % XP_PER_LEVEL
                if (
                    int(row[2] or 0) != expected_total
                    or int(row[3] or 1) != expected_level
                    or int(row[4] or 0) != expected_xp_in_level
                ):
                    xp_mismatches.append(
                        {
                            "user_id": row[0],
                            "username": row[1],
                            "stored_total_xp": int(row[2] or 0),
                            "xp_logs_total": expected_total,
                            "stored_level": int(row[3] or 1),
                            "expected_level": expected_level,
                            "stored_xp_in_level": int(row[4] or 0),
                            "expected_xp_in_level": expected_xp_in_level,
                        }
                    )

        invalid_xp_reasons: list[str] = []
        if "xp_logs" in table_names:
            for row in connection.execute("SELECT DISTINCT fuente FROM xp_logs ORDER BY fuente").fetchall():
                reason = str(row[0] or "").strip()
                try:
                    normalize_xp_reason(reason)
                except ValueError:
                    invalid_xp_reasons.append(reason)

        report = {
            "sqlite_path": str(source_path),
            "tables_present": sorted(table_names),
            "missing_required_tables": [table for table in _REQUIRED_SOURCE_TABLES if table not in table_names],
            "missing_optional_tables": [table for table in _OPTIONAL_SOURCE_TABLES if table not in table_names],
            "row_counts": counts,
            "integrity_check": integrity_check,
            "foreign_key_violations": foreign_key_violations,
            "duplicate_usernames": _safe_duplicate_count(
                connection,
                table_names,
                {"users"},
                "SELECT username FROM users GROUP BY username HAVING COUNT(*) > 1",
            ),
            "duplicate_emails": _safe_duplicate_count(
                connection,
                table_names,
                {"users"},
                "SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1",
            ),
            "duplicate_active_user_habits": _safe_duplicate_count(
                connection,
                table_names,
                {"habitos_usuario"},
                "SELECT usuario_id, habito_id, activo FROM habitos_usuario GROUP BY usuario_id, habito_id, activo HAVING COUNT(*) > 1",
            ),
            "invalid_xp_reasons": invalid_xp_reasons,
            "xp_mismatches": xp_mismatches,
        }
        report["blocking_issues"] = _collect_blocking_issues(report)
        return report


def migrate_legacy_sqlite(sqlite_path: str | Path) -> dict[str, Any]:
    """Import a legacy SQLite database into the current target schema."""
    audit_report = audit_legacy_sqlite(sqlite_path)
    if audit_report["blocking_issues"]:
        raise ValueError("Legacy SQLite import blocked: " + "; ".join(audit_report["blocking_issues"]))

    _assert_target_is_empty()

    source_path = Path(audit_report["sqlite_path"])
    with _connect_sqlite(source_path) as connection:
        user_ids: list[int] = []

        for row in connection.execute("SELECT id, nombre, descripcion FROM categorias ORDER BY id").fetchall():
            db.session.add(Category(id=row[0], nombre=row[1], descripcion=row[2]))

        for row in connection.execute(
            "SELECT id, categoria_id, nombre, descripcion, dificultad, xp_base FROM habitos ORDER BY id"
        ).fetchall():
            db.session.add(
                Habit(
                    id=row[0],
                    categoria_id=row[1],
                    nombre=row[2],
                    descripcion=row[3],
                    dificultad=row[4],
                    xp_base=row[5],
                )
            )

        for row in connection.execute(
            "SELECT id, username, email, password_hash, role, total_xp, level, xp_in_level, created_at, updated_at FROM users ORDER BY id"
        ).fetchall():
            user_ids.append(int(row[0]))
            db.session.add(
                User(
                    id=row[0],
                    username=row[1],
                    email=row[2],
                    password_hash=row[3],
                    role=row[4],
                    total_xp=int(row[5] or 0),
                    level=int(row[6] or 1),
                    xp_in_level=int(row[7] or 0),
                    created_at=_parse_datetime(row[8]),
                    updated_at=_parse_datetime(row[9]),
                )
            )

        for row in connection.execute(
            "SELECT id, usuario_id, habito_id, fecha_inicio, fecha_fin, activo, fecha_creacion FROM habitos_usuario ORDER BY id"
        ).fetchall():
            db.session.add(
                UserHabit(
                    id=row[0],
                    usuario_id=row[1],
                    habito_id=row[2],
                    fecha_inicio=_parse_date(row[3]),
                    fecha_fin=_parse_date(row[4]),
                    activo=bool(row[5]),
                    fecha_creacion=_parse_datetime(row[6]),
                )
            )

        for row in connection.execute(
            "SELECT id, habitousuario_id, fecha, completado, xp_ganado FROM registro_habitos ORDER BY id"
        ).fetchall():
            db.session.add(
                CheckIn(
                    id=row[0],
                    habitousuario_id=row[1],
                    fecha=_parse_date(row[2]),
                    completado=bool(row[3]),
                    xp_ganado=int(row[4] or 0),
                )
            )

        for row in connection.execute(
            "SELECT id, habitousuario_id, tipo_validacion, evidencia, tiempo_segundos, validado, fecha FROM validaciones ORDER BY id"
        ).fetchall():
            db.session.add(
                ValidationLog(
                    id=row[0],
                    habitousuario_id=row[1],
                    tipo_validacion=row[2],
                    evidencia=row[3],
                    tiempo_segundos=row[4],
                    status="approved" if bool(row[5]) else "rejected",
                    validado=bool(row[5]),
                    fecha=_parse_datetime(row[6]),
                )
            )

        for row in connection.execute(
            "SELECT id, usuario_id, cantidad, fuente, fecha FROM xp_logs ORDER BY id"
        ).fetchall():
            db.session.add(
                XpLog(
                    id=row[0],
                    user_id=row[1],
                    cantidad=int(row[2] or 0),
                    razon=normalize_xp_reason(str(row[3] or "")),
                    fecha=_parse_datetime(row[4]),
                )
            )

        if "pomodoro_sessions" in audit_report["tables_present"]:
            for row in connection.execute(
                """
                SELECT id, user_id, habit_id, theme, study_minutes, break_minutes, cycles,
                       completed, started_at, completed_at
                FROM pomodoro_sessions
                ORDER BY id
                """
            ).fetchall():
                db.session.add(
                    PomodoroSession(
                        id=row[0],
                        user_id=row[1],
                        habit_id=row[2],
                        theme=row[3],
                        study_minutes=int(row[4]),
                        break_minutes=int(row[5]),
                        cycles=int(row[6]),
                        completed=bool(row[7]),
                        started_at=_parse_datetime(row[8]),
                        completed_at=_parse_datetime(row[9]),
                    )
                )

        if "niveles" in audit_report["tables_present"]:
            niveles_rows = [
                {
                    "id": row[0],
                    "nombre": row[1],
                    "xp_minimo": row[2],
                    "xp_maximo": row[3],
                    "recompensa": row[4],
                    "descripcion": row[5],
                }
                for row in connection.execute(
                    "SELECT id, nombre, xp_minimo, xp_maximo, recompensa, descripcion FROM niveles ORDER BY id"
                ).fetchall()
            ]
            if niveles_rows:
                db.session.execute(
                    text(
                        """
                        INSERT INTO niveles (id, nombre, xp_minimo, xp_maximo, recompensa, descripcion)
                        VALUES (:id, :nombre, :xp_minimo, :xp_maximo, :recompensa, :descripcion)
                        """
                    ),
                    niveles_rows,
                )

        db.session.flush()
        recompute_all_users_xp(user_ids, commit=False)
        db.session.commit()
        _reset_postgresql_sequences()

    return {
        "sqlite_path": str(source_path),
        "imported_counts": {
            "users": len(user_ids),
            "categorias": audit_report["row_counts"]["categorias"],
            "habitos": audit_report["row_counts"]["habitos"],
            "habitos_usuario": audit_report["row_counts"]["habitos_usuario"],
            "registro_habitos": audit_report["row_counts"]["registro_habitos"],
            "validaciones": audit_report["row_counts"]["validaciones"],
            "xp_logs": audit_report["row_counts"]["xp_logs"],
            "pomodoro_sessions": audit_report["row_counts"]["pomodoro_sessions"],
            "niveles": audit_report["row_counts"]["niveles"],
        },
        "recomputed_users": len(user_ids),
    }


def _resolve_sqlite_path(sqlite_path: str | Path) -> Path:
    path = Path(sqlite_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"SQLite source file not found: {path}")
    return path


def _connect_sqlite(sqlite_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    return connection


def _get_table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }


def _count_rows(connection: sqlite3.Connection, table_names: set[str], table_name: str) -> int:
    if table_name not in table_names:
        return 0
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _safe_duplicate_count(
    connection: sqlite3.Connection,
    table_names: set[str],
    required_tables: set[str],
    query: str,
) -> int:
    if not required_tables.issubset(table_names):
        return 0
    return len(connection.execute(query).fetchall())


def _collect_blocking_issues(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report["missing_required_tables"]:
        issues.append("missing required tables")
    if report["integrity_check"] != "ok":
        issues.append("sqlite integrity_check failed")
    if report["foreign_key_violations"]:
        issues.append("foreign key violations detected")
    if report["duplicate_usernames"]:
        issues.append("duplicate usernames detected")
    if report["duplicate_emails"]:
        issues.append("duplicate emails detected")
    if report["duplicate_active_user_habits"]:
        issues.append("duplicate active user habits detected")
    if report["invalid_xp_reasons"]:
        issues.append("unsupported xp_log reasons detected")
    return issues


def _assert_target_is_empty() -> None:
    try:
        table_counts = {
            "users": User.query.count(),
            "categorias": Category.query.count(),
            "habitos": Habit.query.count(),
            "habitos_usuario": UserHabit.query.count(),
            "registro_habitos": CheckIn.query.count(),
            "validaciones": ValidationLog.query.count(),
            "xp_logs": XpLog.query.count(),
            "pomodoro_sessions": PomodoroSession.query.count(),
            "niveles": int(db.session.execute(text("SELECT COUNT(*) FROM niveles")).scalar() or 0),
        }
    except Exception as exc:  # pragma: no cover - defensive operational guard
        raise ValueError(
            "Target database is missing current schema tables. Run flask db upgrade before importing legacy data."
        ) from exc

    non_empty = {table: count for table, count in table_counts.items() if count > 0}
    if not non_empty:
        return

    seed_only_state = (
        table_counts["users"] == 0
        and table_counts["habitos_usuario"] == 0
        and table_counts["registro_habitos"] == 0
        and table_counts["validaciones"] == 0
        and table_counts["xp_logs"] == 0
        and table_counts["pomodoro_sessions"] == 0
        and table_counts["niveles"] == 0
        and table_counts["categorias"] == 3
        and table_counts["habitos"] == 11
    )
    if seed_only_state:
        db.session.execute(text("DELETE FROM habitos"))
        db.session.execute(text("DELETE FROM categorias"))
        db.session.commit()
        return

    details = ", ".join(f"{table}={count}" for table, count in sorted(non_empty.items()))
    raise ValueError(f"Target database is not empty: {details}")


def _parse_date(raw_value: Any) -> date | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, date) and not isinstance(raw_value, datetime):
        return raw_value
    return date.fromisoformat(str(raw_value))


def _parse_datetime(raw_value: Any) -> datetime | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, datetime):
        return raw_value

    text_value = str(raw_value).strip()
    if text_value.endswith("Z"):
        text_value = text_value[:-1] + "+00:00"
    if " " in text_value and "T" not in text_value:
        text_value = text_value.replace(" ", "T", 1)
    return datetime.fromisoformat(text_value)


def _reset_postgresql_sequences() -> None:
    if db.session.bind is None or db.session.bind.dialect.name != "postgresql":
        return

    for table_name in _TARGET_TABLES:
        result = db.session.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}"))
        max_id = int(result.scalar() or 0)
        if max_id == 0:
            db.session.execute(
                text("SELECT setval(pg_get_serial_sequence(:table_name, 'id'), 1, false)"),
                {"table_name": table_name},
            )
        else:
            db.session.execute(
                text("SELECT setval(pg_get_serial_sequence(:table_name, 'id'), :max_id, true)"),
                {"table_name": table_name, "max_id": max_id},
            )
    db.session.commit()
