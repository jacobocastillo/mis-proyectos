"""
Requirement mapping:
- RF-02: Authenticated users can list catalog habits and assign a habit.
"""


def test_rf_02_list_catalog_and_assign_habit(client, auth_headers, seed_catalog):
    catalog_habit = seed_catalog()
    headers = auth_headers()

    catalog = client.get("/api/habits/catalog", headers=headers)
    assert catalog.status_code == 200
    assert catalog.get_json()[0]["name"] == "Tomar agua"

    assigned = client.post(
        "/api/habits",
        json={"habito_id": catalog_habit.id},
        headers=headers,
    )
    assert assigned.status_code == 201
    assigned_payload = assigned.get_json()
    assert assigned_payload["catalog_habit_id"] == catalog_habit.id

    habits = client.get("/api/habits", headers=headers)
    assert habits.status_code == 200
    assert [habit["id"] for habit in habits.get_json()] == [assigned_payload["id"]]
