API = "/api/v1"


def start(client, agent_h, cid):
    return client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"})


def test_full_lifecycle(client, assigned_complaint, agent_h, customer_h, manager_h):
    cid = assigned_complaint["id"]
    assert start(client, agent_h, cid).json()["status"] == "in_progress"
    r = client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h,
                    json={"summary": "Replacement sent", "root_cause": "Packaging", "action_taken": "Shipped new item"})
    assert r.status_code == 201 and r.json()["root_cause"] == "Packaging"
    assert client.get(f"{API}/complaints/{cid}/resolution", headers=customer_h).json()["summary"] == "Replacement sent"
    resolved = client.get(f"{API}/complaints/{cid}", headers=customer_h).json()
    assert resolved["status"] == "resolved" and resolved["resolved_at"]
    closed = client.post(f"{API}/complaints/{cid}/close", headers=customer_h, json={})
    assert closed.status_code == 200 and closed.json()["status"] == "closed" and closed.json()["closed_at"]
    history = client.get(f"{API}/complaints/{cid}/status-history", headers=manager_h).json()
    assert [h["to_status"] for h in history] == ["open", "assigned", "in_progress", "resolved", "closed"]
    types = {n["type"] for n in client.get(f"{API}/notifications", headers=customer_h).json()["items"]}
    assert {"status_changed", "complaint_resolved"} <= types


def test_invalid_transitions_are_409(client, create_complaint, assigned_complaint, manager_h, agent_h):
    open_c = create_complaint()
    # cannot close or resolve an open complaint
    r = client.post(f"{API}/complaints/{open_c['id']}/close", headers=manager_h, json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_status_transition"
    assert client.post(f"{API}/complaints/{open_c['id']}/resolve", headers=manager_h, json={"summary": "nothing yet"}).status_code == 409
    assert client.post(f"{API}/complaints/{open_c['id']}/status", headers=manager_h, json={"status": "in_progress"}).status_code == 409
    # cannot close a complaint that is merely in progress
    cid = assigned_complaint["id"]
    start(client, agent_h, cid)
    assert client.post(f"{API}/complaints/{cid}/close", headers=manager_h, json={}).status_code == 409
    # resolving/closing/reopening must use the dedicated endpoints
    r = client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "resolved"})
    assert r.status_code == 400 and "/resolve" in r.json()["error"]["message"]
    # reopen needs a resolved complaint
    assert client.post(f"{API}/complaints/{cid}/reopen", headers=manager_h, json={"reason": "why not"}).status_code == 409


def test_reopen_resets_sla_and_notifies(client, assigned_complaint, agent_h, customer_h, manager_h):
    cid = assigned_complaint["id"]
    start(client, agent_h, cid)
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "Fixed it for you"})
    r = client.post(f"{API}/complaints/{cid}/reopen", headers=customer_h, json={"reason": "Still broken"})
    assert r.status_code == 200 and r.json()["status"] == "reopened"
    assert r.json()["reopen_count"] == 1 and r.json()["resolved_at"] is None
    assert client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"}).json()["status"] == "in_progress"
    assert any("reopened" in n["message"] for n in client.get(f"{API}/notifications", headers=agent_h).json()["items"])
    logs = client.get(f"{API}/audit-logs", headers=manager_h, params={"action": "complaint_reopened"}).json()
    assert logs["total"] == 1 and logs["items"][0]["details"]["note"] == "Still broken"


def test_closed_complaint_reopen_window(client, db, assigned_complaint, agent_h, customer_h):
    from datetime import timedelta

    from app.models import Complaint

    cid = assigned_complaint["id"]
    start(client, agent_h, cid)
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "Fixed it for you"})
    client.post(f"{API}/complaints/{cid}/close", headers=customer_h, json={})
    assert client.post(f"{API}/complaints/{cid}/reopen", headers=customer_h, json={"reason": "again"}).status_code == 200
    # close again, then pretend it was closed long ago
    client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"})
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "Fixed it again"})
    client.post(f"{API}/complaints/{cid}/close", headers=customer_h, json={})
    c = db.get(Complaint, cid)
    c.closed_at = c.closed_at - timedelta(days=30)
    db.commit()
    r = client.post(f"{API}/complaints/{cid}/reopen", headers=customer_h, json={"reason": "too late"})
    assert r.status_code == 400 and "no longer be reopened" in r.json()["error"]["message"]


def test_only_assigned_agent_or_manager_can_resolve(client, make_user, login, assigned_complaint, agent_h, customer_h):
    from app.core.constants import Role

    cid = assigned_complaint["id"]
    start(client, agent_h, cid)
    other_agent_h = login(make_user(Role.SUPPORT_AGENT))
    assert client.post(f"{API}/complaints/{cid}/resolve", headers=other_agent_h, json={"summary": "not mine"}).status_code == 403
    assert client.post(f"{API}/complaints/{cid}/resolve", headers=customer_h, json={"summary": "i resolve it"}).status_code == 403
