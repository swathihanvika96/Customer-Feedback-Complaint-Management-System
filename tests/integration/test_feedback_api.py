API = "/api/v1"


def submit(client, headers, category_id, rating=5, description="Great service", **extra):
    return client.post(f"{API}/feedback", headers=headers, json={"category_id": category_id, "rating": rating, "description": description, **extra})


def test_submit_feedback(client, customer_h, category_id):
    r = submit(client, customer_h, category_id, 4)
    assert r.status_code == 201
    body = r.json()
    assert body["rating"] == 4 and body["status"] == "submitted" and body["feedback_date"].endswith("+00:00")


def test_invalid_ratings_rejected(client, customer_h, category_id):
    for rating in (0, 6, -3):
        assert submit(client, customer_h, category_id, rating).status_code == 422
    assert submit(client, customer_h, category_id, "abc").status_code == 422


def test_duplicate_submission_blocked(client, customer_h, category_id):
    assert submit(client, customer_h, category_id).status_code == 201
    assert submit(client, customer_h, category_id).status_code == 409


def test_customers_only_see_their_own_feedback(client, make_user, login, customer_h, category_id):
    fb = submit(client, customer_h, category_id).json()
    from app.core.constants import Role

    other_h = login(make_user(Role.CUSTOMER))
    assert client.get(f"{API}/feedback/{fb['id']}", headers=other_h).status_code == 403
    assert client.get(f"{API}/feedback", headers=other_h).json()["total"] == 0
    assert client.patch(f"{API}/feedback/{fb['id']}", headers=other_h, json={"rating": 1}).status_code == 403
    assert client.get(f"{API}/feedback", headers=customer_h).json()["total"] == 1


def test_update_feedback_is_audited_and_has_history(client, customer_h, manager_h, category_id):
    fb = submit(client, customer_h, category_id, 5).json()
    r = client.patch(f"{API}/feedback/{fb['id']}", headers=customer_h, json={"rating": 2, "description": "Changed my mind"})
    assert r.status_code == 200 and r.json()["rating"] == 2
    assert client.patch(f"{API}/feedback/{fb['id']}", headers=customer_h, json={"rating": 9}).status_code == 422
    history = client.get(f"{API}/feedback/{fb['id']}/history", headers=customer_h).json()
    assert [h["action"] for h in history] == ["feedback_created", "feedback_updated"]
    assert history[1]["details"]["rating"] == {"from": 5, "to": 2}
    logs = client.get(f"{API}/audit-logs", headers=manager_h, params={"action": "feedback_updated"}).json()
    assert logs["total"] == 1


def test_staff_can_filter_and_change_status(client, customer_h, agent_h, manager_h, category_id):
    fb1 = submit(client, customer_h, category_id, 5, "first one").json()
    submit(client, customer_h, category_id, 1, "second one")
    assert client.get(f"{API}/feedback", headers=manager_h, params={"rating_max": 2}).json()["total"] == 1
    assert client.patch(f"{API}/feedback/{fb1['id']}/status", headers=agent_h, json={"status": "reviewed"}).json()["status"] == "reviewed"
    assert client.get(f"{API}/feedback", headers=manager_h, params={"status": "reviewed"}).json()["total"] == 1
    assert client.patch(f"{API}/feedback/{fb1['id']}/status", headers=customer_h, json={"status": "archived"}).status_code == 403


def test_feedback_linked_to_complaint_only_when_resolved(client, customer_h, assigned_complaint, agent_h, category_id):
    cid = assigned_complaint["id"]
    assert submit(client, customer_h, category_id, 3, "too early", complaint_id=cid).status_code == 400
    client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"})
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "Replaced the item"})
    assert submit(client, customer_h, category_id, 5, "thanks", complaint_id=cid).status_code == 201
    assert submit(client, customer_h, category_id, 4, "again", complaint_id=cid).status_code == 409
