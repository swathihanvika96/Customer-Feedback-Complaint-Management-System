from app.core.constants import Role

API = "/api/v1"


def test_only_managers_can_assign(client, create_complaint, agent_h, customer_h, manager_h, admin_h, agent_id):
    c = create_complaint()
    for headers in (agent_h, customer_h):
        assert client.post(f"{API}/complaints/{c['id']}/assign", json={"agent_id": agent_id}, headers=headers).status_code == 403
    assert client.post(f"{API}/complaints/{c['id']}/assign", json={"agent_id": agent_id}, headers=admin_h).status_code == 200


def test_assign_sets_status_history_and_notification(client, assigned_complaint, agent_h, manager_h, agent_id):
    assert assigned_complaint["status"] == "assigned" and assigned_complaint["assigned_agent_id"] == agent_id
    history = client.get(f"{API}/complaints/{assigned_complaint['id']}/assignments", headers=manager_h).json()
    assert len(history) == 1 and history[0]["is_active"] is True
    notes = client.get(f"{API}/notifications", headers=agent_h).json()
    assert notes["items"][0]["type"] == "complaint_assigned"
    assert client.get(f"{API}/notifications/unread-count", headers=agent_h).json()["unread"] == 1
    sh = client.get(f"{API}/complaints/{assigned_complaint['id']}/status-history", headers=manager_h).json()
    assert [h["to_status"] for h in sh] == ["open", "assigned"]


def test_cannot_assign_twice_but_can_reassign(client, assigned_complaint, manager_h, make_user, db):
    cid = assigned_complaint["id"]
    other = make_user(Role.SUPPORT_AGENT)
    other_agent = client.get(f"{API}/agents", headers=manager_h, params={"q": other.email}).json()["items"][0]
    assert client.post(f"{API}/complaints/{cid}/assign", json={"agent_id": other_agent["id"]}, headers=manager_h).status_code == 409
    r = client.post(f"{API}/complaints/{cid}/reassign", json={"agent_id": other_agent["id"], "reason": "Specialist"}, headers=manager_h)
    assert r.status_code == 200 and r.json()["assigned_agent_id"] == other_agent["id"]
    assert r.json()["status"] == "assigned"
    history = client.get(f"{API}/complaints/{cid}/assignments", headers=manager_h).json()
    assert [h["is_active"] for h in history] == [False, True]
    assert history[0]["unassigned_at"] is not None
    # reassigning to the same agent is rejected
    assert client.post(f"{API}/complaints/{cid}/reassign", json={"agent_id": other_agent["id"]}, headers=manager_h).status_code == 400
    logs = client.get(f"{API}/audit-logs", headers=manager_h, params={"entity_id": cid}).json()
    assert "agent_reassigned" in {i["action"] for i in logs["items"]}


def test_workload_and_capacity(client, create_complaint, manager_h, make_user):
    busy = make_user(Role.SUPPORT_AGENT, max_workload=1)
    agent = client.get(f"{API}/agents", headers=manager_h, params={"q": busy.email}).json()["items"][0]
    first, second = create_complaint(), create_complaint()
    assert client.post(f"{API}/complaints/{first['id']}/assign", json={"agent_id": agent["id"]}, headers=manager_h).status_code == 200
    r = client.post(f"{API}/complaints/{second['id']}/assign", json={"agent_id": agent["id"]}, headers=manager_h)
    assert r.status_code == 409 and "capacity" in r.json()["error"]["message"]
    wl = client.get(f"{API}/agents/{agent['id']}/workload", headers=manager_h).json()
    assert wl["active_complaints"] == 1 and wl["available_capacity"] == 0 and wl["by_status"] == {"assigned": 1}
    assigned = client.get(f"{API}/agents/{agent['id']}/complaints", headers=manager_h).json()
    assert assigned["total"] == 1


def test_cannot_assign_to_deactivated_agent(client, create_complaint, manager_h, agent_id):
    client.post(f"{API}/agents/{agent_id}/deactivate", headers=manager_h)
    c = create_complaint()
    assert client.post(f"{API}/complaints/{c['id']}/assign", json={"agent_id": agent_id}, headers=manager_h).status_code == 400


def test_manager_creates_agent(client, manager_h):
    r = client.post(f"{API}/agents", headers=manager_h, json={
        "email": "newagent@example.com", "full_name": "New Agent", "password": "Passw0rd!", "department": "Billing", "max_workload": 5})
    assert r.status_code == 201 and r.json()["department"] == "Billing" and r.json()["email"] == "newagent@example.com"
