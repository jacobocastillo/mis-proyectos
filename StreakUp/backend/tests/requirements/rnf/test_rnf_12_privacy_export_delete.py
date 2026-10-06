"""
Requirement mapping:
- RNF-12: Privacy baseline through authenticated export and account deletion.
"""

from datetime import date

from app.extensions import db
from app.models.checkin import CheckIn
from app.models.user import User
from app.models.user_habit import UserHabit


def test_rnf_12_export_excludes_credentials(client, auth_headers, seed_catalog):
    headers = auth_headers()
    catalog_habit = seed_catalog()
    assigned = UserHabit(
        usuario_id=User.query.filter_by(email="daniel@correo.com").one().id,
        habito_id=catalog_habit.id,
        fecha_inicio=date.today(),
        activo=True,
    )
    db.session.add(assigned)
    db.session.flush()
    db.session.add(CheckIn(habitousuario_id=assigned.id, fecha=date.today(), xp_ganado=10))
    db.session.commit()

    response = client.get("/api/users/me/export", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"]["email"] == "daniel@correo.com"
    assert len(payload["habits"]) == 1
    assert len(payload["checkins"]) == 1
    assert "password_hash" not in payload["profile"]
    assert "daniel-password" not in str(payload)


def test_rnf_12_delete_account_removes_user_data(client, auth_headers, seed_catalog):
    headers = auth_headers()
    user = User.query.filter_by(email="daniel@correo.com").one()
    catalog_habit = seed_catalog()
    assigned = UserHabit(
        usuario_id=user.id,
        habito_id=catalog_habit.id,
        fecha_inicio=date.today(),
        activo=True,
    )
    db.session.add(assigned)
    db.session.flush()
    assigned_id = assigned.id
    db.session.add(CheckIn(habitousuario_id=assigned_id, fecha=date.today(), xp_ganado=10))
    db.session.commit()

    response = client.delete("/api/users/me", headers=headers)

    assert response.status_code == 200
    assert db.session.get(User, user.id) is None
    assert UserHabit.query.filter_by(usuario_id=user.id).count() == 0
    assert CheckIn.query.filter_by(habitousuario_id=assigned_id).count() == 0
