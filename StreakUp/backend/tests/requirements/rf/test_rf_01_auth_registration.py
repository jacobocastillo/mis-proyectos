"""
Requirement mapping:
- RF-01: Users can register an account and authenticate with that account.
"""

from app.models.user import User


def test_rf_01_register_user_and_login(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "rf_user",
            "email": "rf@example.com",
            "password": "rf-password",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["user"]["email"] == "rf@example.com"
    assert "password_hash" not in payload["user"]

    user = User.query.filter_by(email="rf@example.com").first()
    assert user is not None
    assert user.password_hash != "rf-password"

    login = client.post(
        "/api/auth/login",
        json={"email": "rf@example.com", "password": "rf-password"},
    )

    assert login.status_code == 200
    assert login.get_json()["user"]["email"] == "rf@example.com"
    assert login.get_json()["access_token"]
