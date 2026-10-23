API = "/api/v1"


def test_internal_notes_hidden_from_customer(client, assigned_complaint, agent_h, customer_h):
    cid = assigned_complaint["id"]
    assert client.post(f"{API}/complaints/{cid}/comments", headers=agent_h, json={"body": "Check the warehouse log", "is_internal": True}).status_code == 201
    assert client.post(f"{API}/complaints/{cid}/comments", headers=agent_h, json={"body": "We are looking into it"}).status_code == 201
    staff_view = client.get(f"{API}/complaints/{cid}/comments", headers=agent_h).json()
    customer_view = client.get(f"{API}/complaints/{cid}/comments", headers=customer_h).json()
    assert len(staff_view) == 2 and len(customer_view) == 1 and customer_view[0]["is_internal"] is False


def test_customer_cannot_write_internal_note(client, assigned_complaint, customer_h):
    r = client.post(f"{API}/complaints/{assigned_complaint['id']}/comments", headers=customer_h, json={"body": "secret", "is_internal": True})
    assert r.status_code == 403


def test_customer_comment_notifies_agent_and_ends_waiting(client, assigned_complaint, agent_h, customer_h):
    cid = assigned_complaint["id"]
    client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "waiting_for_customer", "note": "Need photos"})
    assert client.get(f"{API}/complaints/{cid}", headers=agent_h).json()["status"] == "waiting_for_customer"
    client.post(f"{API}/complaints/{cid}/comments", headers=customer_h, json={"body": "Here are the photos"})
    assert client.get(f"{API}/complaints/{cid}", headers=agent_h).json()["status"] == "in_progress"
    types = [n["type"] for n in client.get(f"{API}/notifications", headers=agent_h).json()["items"]]
    assert "new_comment" in types


def test_staff_comment_notifies_customer(client, assigned_complaint, agent_h, customer_h):
    cid = assigned_complaint["id"]
    client.post(f"{API}/complaints/{cid}/comments", headers=agent_h, json={"body": "Replacement shipped"})
    types = [n["type"] for n in client.get(f"{API}/notifications", headers=customer_h).json()["items"]]
    assert "new_comment" in types


def test_unrelated_user_cannot_comment(client, make_user, login, assigned_complaint):
    from app.core.constants import Role

    other = login(make_user(Role.CUSTOMER))
    assert client.post(f"{API}/complaints/{assigned_complaint['id']}/comments", headers=other, json={"body": "hi"}).status_code == 403
