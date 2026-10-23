API = "/api/v1"


def test_default_categories_seeded_and_filterable(client, customer_h):
    r = client.get(f"{API}/categories", headers=customer_h)
    names = {c["name"] for c in r.json()["items"]}
    assert {"Product Quality", "Customer Support", "Service Experience", "Delivery Experience", "Technical Issue"} <= names
    assert client.get(f"{API}/categories", headers=customer_h, params={"q": "delivery"}).json()["total"] == 1


def test_manager_crud_and_deactivation(client, manager_h, customer_h):
    r = client.post(f"{API}/categories", headers=manager_h, json={"name": "Billing", "description": "Invoices"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.post(f"{API}/categories", headers=manager_h, json={"name": "billing"}).status_code == 409  # case-insensitive
    assert client.patch(f"{API}/categories/{cid}", headers=manager_h, json={"description": "Billing issues"}).json()["description"] == "Billing issues"
    assert client.post(f"{API}/categories/{cid}/deactivate", headers=manager_h).json()["is_active"] is False
    assert client.get(f"{API}/categories", headers=manager_h, params={"is_active": False}).json()["total"] == 1
    # cannot use a deactivated category
    r = client.post(f"{API}/feedback", headers=customer_h, json={"category_id": cid, "rating": 3, "description": "meh meh"})
    assert r.status_code == 400 and "deactivated" in r.json()["error"]["message"]


def test_customer_cannot_manage_categories(client, customer_h):
    assert client.post(f"{API}/categories", headers=customer_h, json={"name": "Hack"}).status_code == 403
