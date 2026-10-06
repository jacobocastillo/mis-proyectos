"""
Synchronization service module.

Responsibility:
- Host domain-level synchronization workflows.
- Keep client operation replay idempotent.
"""

from __future__ import annotations

import json
from datetime import date as date_type
from typing import Any

from app.extensions import db
from app.models.sync_operation import SyncOperation
from app.services.checkin_service import toggle_checkin


SUPPORTED_OPERATION_TYPES = {"toggle_checkin"}


class SyncPayloadError(ValueError):
    """Raised when the sync request envelope is malformed."""


def _json_dumps(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _json_loads(value: str) -> dict[str, Any]:
    loaded = json.loads(value)
    return loaded if isinstance(loaded, dict) else {}


def _receipt_result(receipt: SyncOperation) -> dict[str, object]:
    response = _json_loads(receipt.response_json)
    return {
        "client_operation_id": receipt.client_operation_id,
        "operation_type": receipt.operation_type,
        "status": receipt.status,
        "result": response.get("result"),
        "error": response.get("error"),
    }


def _normalize_operations(raw_operations: object) -> list[dict[str, Any]]:
    if not isinstance(raw_operations, list):
        raise SyncPayloadError("operations must be a list.")

    normalized: list[dict[str, Any]] = []
    for index, raw_operation in enumerate(raw_operations):
        if not isinstance(raw_operation, dict):
            raise SyncPayloadError(f"operations[{index}] must be an object.")

        client_operation_id = str(raw_operation.get("client_operation_id") or "").strip()
        operation_type = str(raw_operation.get("operation_type") or "").strip()
        payload = raw_operation.get("payload")

        if not client_operation_id:
            raise SyncPayloadError(f"operations[{index}].client_operation_id is required.")
        if operation_type not in SUPPORTED_OPERATION_TYPES:
            raise SyncPayloadError(f"Unsupported operation_type: {operation_type}.")
        if not isinstance(payload, dict):
            raise SyncPayloadError(f"operations[{index}].payload must be an object.")

        normalized.append(
            {
                "client_operation_id": client_operation_id,
                "operation_type": operation_type,
                "payload": payload,
            }
        )

    return normalized


def _store_receipt(
    *,
    user_id: int,
    operation: dict[str, Any],
    status: str,
    result: dict[str, object] | None = None,
    error: dict[str, object] | None = None,
) -> SyncOperation:
    receipt = SyncOperation(
        user_id=user_id,
        client_operation_id=operation["client_operation_id"],
        operation_type=operation["operation_type"],
        payload_json=_json_dumps(operation["payload"]),
        status=status,
        response_json=_json_dumps({"result": result, "error": error}),
        error_code=str(error.get("code")) if error else None,
    )
    db.session.add(receipt)
    db.session.commit()
    return receipt


def _apply_toggle_checkin(user_id: int, payload: dict[str, Any]) -> dict[str, object]:
    if "habit_id" not in payload:
        raise SyncPayloadError("payload.habit_id is required.")

    try:
        habit_id = int(payload["habit_id"])
    except (TypeError, ValueError) as exc:
        raise SyncPayloadError("payload.habit_id must be an integer.") from exc

    target_date = None
    if payload.get("date") is not None:
        try:
            target_date = date_type.fromisoformat(str(payload["date"]))
        except ValueError as exc:
            raise SyncPayloadError("payload.date must use YYYY-MM-DD.") from exc

    return toggle_checkin(user_id, habit_id, target_date, commit=False)


def _apply_operation(user_id: int, operation: dict[str, Any]) -> dict[str, object]:
    if operation["operation_type"] == "toggle_checkin":
        return _apply_toggle_checkin(user_id, operation["payload"])

    raise SyncPayloadError(f"Unsupported operation_type: {operation['operation_type']}.")


def process_sync_operations(user_id: int, raw_operations: object) -> dict[str, object]:
    """Apply a batch of client operations and return per-operation outcomes."""
    operations = _normalize_operations(raw_operations)
    results: list[dict[str, object]] = []

    for operation in operations:
        existing = SyncOperation.query.filter_by(
            user_id=user_id,
            client_operation_id=operation["client_operation_id"],
        ).first()
        if existing:
            results.append(_receipt_result(existing))
            continue

        try:
            result = _apply_operation(user_id, operation)
        except SyncPayloadError as exc:
            error = {"code": "invalid_operation", "message": str(exc), "retryable": False}
            receipt = _store_receipt(
                user_id=user_id,
                operation=operation,
                status="failed",
                error=error,
            )
            results.append(_receipt_result(receipt))
        except LookupError as exc:
            db.session.rollback()
            error = {"code": "not_found", "message": str(exc), "retryable": False}
            receipt = _store_receipt(
                user_id=user_id,
                operation=operation,
                status="failed",
                error=error,
            )
            results.append(_receipt_result(receipt))
        except ValueError as exc:
            db.session.rollback()
            error = {"code": "conflict", "message": str(exc), "retryable": False}
            receipt = _store_receipt(
                user_id=user_id,
                operation=operation,
                status="conflict",
                error=error,
            )
            results.append(_receipt_result(receipt))
        except Exception:
            db.session.rollback()
            results.append(
                {
                    "client_operation_id": operation["client_operation_id"],
                    "operation_type": operation["operation_type"],
                    "status": "retry",
                    "result": None,
                    "error": {
                        "code": "transient_error",
                        "message": "Sync operation could not be applied.",
                        "retryable": True,
                    },
                }
            )
        else:
            receipt = _store_receipt(
                user_id=user_id,
                operation=operation,
                status="acked",
                result=result,
            )
            results.append(_receipt_result(receipt))

    return {"results": results}
