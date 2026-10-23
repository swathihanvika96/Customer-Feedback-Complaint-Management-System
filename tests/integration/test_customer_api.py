API = "/api/v1"


def test_staff_can_create_search_filter_paginate(client, manager_h):
    for i in range(5):
        r = client.post(f"{API}/customers", headers=manager_h, json={
            "name": f"Customer {i}", "email": f"c{i}@acme.com", "company": "Acme" if i % 2 == 0 else "Globex"})
        assert r.status_code == 201
    r = client.get(f"{API}/customers", headers=manager_h, params={"q": "acme.com", "size": 2, "page": 1, "sort_by": "name", "sort_order": "asc"})
    body = r.json()
    assert body["total"] == 5 and body["pages"] == 3 and len(body["items"]) == 2
    assert body["items"][0]["name"] == "Customer 0"
    r = client.get(f"{API}/customers", headers=manager_h, params={"company": "acme"})
    assert r.json()["total"] == 3


def test_invalid_sort_field_is_400(client, manager_h):
    r = client.get(f"{API}/customers", headers=manager_h, params={"sort_by": "password"})
    assert r.status_code == 400 and "Allowed values" in r.json()["error"]["message"]


def test_duplicate_customer_email(client, manager_h):
    body = {"name": "Same Person", "email": "same@acme.com"}
    assert client.post(f"{API}/customers", headers=manager_h, json=body).status_code == 201
    assert client.post(f"{API}/customers", headers=manager_h, json=body).status_code == 409


def test_customer_sees_only_own_profile(client, customer_h, manager_h):
    mine = client.get(f"{API}/customers/me", headers=customer_h)
    assert mine.status_code == 200
    other = client.post(f"{API}/customers", headers=manager_h, json={"name": "Other One", "email": "o@x.com"}).json()
    assert client.get(f"{API}/customers/{other['id']}", headers=customer_h).status_code == 403
    assert client.get(f"{API}/customers", headers=customer_h).status_code == 403
    assert client.patch(f"{API}/customers/{mine.json()['id']}", headers=customer_h, json={"phone": "123"}).json()["phone"] == "123"


def test_deactivate_customer_blocks_feedback(client, manager_h, customer_h, category_id):
    cid = client.get(f"{API}/customers/me", headers=customer_h).json()["id"]
    assert client.post(f"{API}/customers/{cid}/deactivate", headers=manager_h).status_code == 200
    r = client.post(f"{API}/feedback", headers=customer_h, json={"category_id": category_id, "rating": 4, "description": "nice"})
    assert r.status_code in (400, 403)
