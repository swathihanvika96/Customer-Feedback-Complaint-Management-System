API = "/api/v1"


def test_create_complaint(client, create_complaint, customer_h):
    c = create_complaint("high", attachment_urls=["https://files.example.com/a.png"])
    assert c["status"] == "open" and c["priority"] == "high"
    assert c["reference_no"].startswith("CMP-") and c["attachment_urls"] == ["https://files.example.com/a.png"]
    assert c["assigned_agent_id"] is None
    sla = client.get(f"{API}/sla/complaints/{c['id']}", headers=customer_h).json()
    assert sla["sla_hours"] == 4.0 and sla["state"] in ("on_track", "at_risk")


def test_reference_numbers_are_unique(create_complaint):
    refs = {create_complaint()["reference_no"] for _ in range(5)}
    assert len(refs) == 5


def test_validation_errors(client, customer_h, category_id):
    bad = [
        {"title": "x", "description": "short", "category_id": category_id},
        {"title": "Valid title", "description": "valid description", "category_id": category_id, "priority": "urgent"},
        {"title": "Valid title", "description": "valid description", "category_id": category_id, "attachment_urls": ["ftp://nope"]},
    ]
    for body in bad:
        assert client.post(f"{API}/complaints", headers=customer_h, json=body).status_code == 422
    r = client.post(f"{API}/complaints", headers=customer_h, json={"title": "Valid title", "description": "valid description", "category_id": 9999})
    assert r.status_code == 400


def test_customer_sees_only_own_complaints(client, make_user, login, create_complaint):
    from app.core.constants import Role

    c = create_complaint()
    other_h = login(make_user(Role.CUSTOMER))
    assert client.get(f"{API}/complaints", headers=other_h).json()["total"] == 0
    assert client.get(f"{API}/complaints/{c['id']}", headers=other_h).status_code == 403


def test_staff_on_behalf_requires_customer_id(client, manager_h, category_id):
    body = {"title": "Phone call", "description": "Customer phoned us", "category_id": category_id}
    assert client.post(f"{API}/complaints", headers=manager_h, json=body).status_code == 400
    cid = client.post(f"{API}/customers", headers=manager_h, json={"name": "Phone Caller", "email": "pc@x.com"}).json()["id"]
    assert client.post(f"{API}/complaints", headers=manager_h, json={**body, "customer_id": cid}).status_code == 201


def test_combined_filters_and_sorting(client, create_complaint, manager_h, agent_id, category_id):
    a = create_complaint("high")
    b = create_complaint("low")
    create_complaint("medium")
    client.post(f"{API}/complaints/{a['id']}/assign", json={"agent_id": agent_id}, headers=manager_h)

    def ids(**params):
        r = client.get(f"{API}/complaints", headers=manager_h, params=params)
        assert r.status_code == 200, r.text
        return [i["id"] for i in r.json()["items"]]

    assert ids(status="assigned") == [a["id"]]
    assert ids(priority="low") == [b["id"]]
    assert ids(agent_id=agent_id) == [a["id"]]
    assert ids(category_id=category_id, status="open", priority="low") == [b["id"]]
    assert ids(status="assigned", priority="low") == []
    assert ids(sort_by="priority", sort_order="desc")[0] == a["id"]
    assert ids(sort_by="priority", sort_order="asc")[0] == b["id"]
    assert len(ids(created_from="2000-01-01", created_to="2100-01-01")) == 3
    assert ids(created_from="2100-01-01") == []
    assert ids(q=a["reference_no"]) == [a["id"]]
    assert client.get(f"{API}/complaints", headers=manager_h, params={"created_from": "2026-12-01", "created_to": "2026-01-01"}).status_code == 400


def test_agent_sees_only_assigned_complaints(client, agent_h, create_complaint, assigned_complaint):
    other = create_complaint()
    r = client.get(f"{API}/complaints", headers=agent_h)
    assert [c["id"] for c in r.json()["items"]] == [assigned_complaint["id"]]
    assert client.get(f"{API}/complaints/{other['id']}", headers=agent_h).status_code == 403


def test_customer_can_edit_only_while_open(client, create_complaint, customer_h, assigned_complaint):
    open_c = create_complaint()
    ok = client.patch(f"{API}/complaints/{open_c['id']}", headers=customer_h, json={"title": "Better title"})
    assert ok.status_code == 200 and ok.json()["title"] == "Better title"
    assert client.patch(f"{API}/complaints/{open_c['id']}", headers=customer_h, json={"priority": "high"}).status_code == 403
    assert client.patch(f"{API}/complaints/{assigned_complaint['id']}", headers=customer_h, json={"title": "Too late"}).status_code == 409


def test_manager_priority_change_recalculates_due_date(client, create_complaint, manager_h):
    c = create_complaint("low")
    r = client.patch(f"{API}/complaints/{c['id']}", headers=manager_h, json={"priority": "high"})
    assert r.status_code == 200
    sla = client.get(f"{API}/sla/complaints/{c['id']}", headers=manager_h).json()
    assert sla["sla_hours"] == 4.0
    logs = client.get(f"{API}/audit-logs", headers=manager_h, params={"entity_type": "complaint", "entity_id": c["id"]}).json()
    assert {"complaint_created", "complaint_updated"} <= {i["action"] for i in logs["items"]}
