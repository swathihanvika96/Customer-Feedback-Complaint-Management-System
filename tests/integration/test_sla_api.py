from datetime import timedelta

from app.models import Complaint
from app.utils.datetime_utils import utcnow

API = "/api/v1"


def test_rules_listed_and_updatable(client, manager_h, customer_h):
    rules = {r["priority"]: r["resolution_hours"] for r in client.get(f"{API}/sla/rules", headers=customer_h).json()}
    assert rules == {"high": 4, "medium": 12, "low": 24}
    assert client.put(f"{API}/sla/rules/low", headers=manager_h, json={"resolution_hours": 48}).json()["resolution_hours"] == 48
    assert client.put(f"{API}/sla/rules/low", headers=customer_h, json={"resolution_hours": 1}).status_code == 403
    assert client.put(f"{API}/sla/rules/low", headers=manager_h, json={"resolution_hours": 0}).status_code == 422


def test_new_complaints_use_priority_hours(client, create_complaint, customer_h):
    for priority, hours in (("high", 4), ("medium", 12), ("low", 24)):
        c = create_complaint(priority)
        assert client.get(f"{API}/sla/complaints/{c['id']}", headers=customer_h).json()["sla_hours"] == hours


def test_overdue_listing_and_breach(client, db, create_complaint, manager_h, customer_h):
    late = create_complaint("high")
    fine = create_complaint("low")
    c = db.get(Complaint, late["id"])
    c.created_at = utcnow() - timedelta(hours=6)
    c.due_at = utcnow() - timedelta(hours=2)
    db.commit()
    overdue = client.get(f"{API}/sla/overdue", headers=manager_h).json()
    assert overdue["total"] == 1 and overdue["items"][0]["complaint_id"] == late["id"]
    assert overdue["items"][0]["is_breached"] and overdue["items"][0]["overdue_seconds"] >= 7000
    assert client.get(f"{API}/complaints", headers=manager_h, params={"overdue": True}).json()["total"] == 1
    sla = client.get(f"{API}/sla/complaints/{fine['id']}", headers=customer_h).json()
    assert not sla["is_breached"] and sla["time_remaining_seconds"] > 0
    assert client.get(f"{API}/sla/overdue", headers=customer_h).status_code == 403


def test_resolution_duration_and_breach_after_resolve(client, db, assigned_complaint, agent_h, manager_h):
    cid = assigned_complaint["id"]
    c = db.get(Complaint, cid)
    c.created_at = utcnow() - timedelta(hours=20)
    c.due_at = c.created_at + timedelta(hours=12)
    db.commit()
    client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"})
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "Done, but late"})
    sla = client.get(f"{API}/sla/complaints/{cid}", headers=manager_h).json()
    assert sla["is_finished"] and sla["is_breached"] and sla["state"] == "breached"
    assert 19.9 * 3600 < sla["resolution_duration_seconds"] < 20.1 * 3600
    assert client.get(f"{API}/sla/overdue", headers=manager_h).json()["total"] == 0  # resolved => no longer overdue


def test_sla_check_notifies_once(client, db, assigned_complaint, create_complaint, manager_h, agent_h):
    soon = db.get(Complaint, assigned_complaint["id"])
    soon.due_at = utcnow() + timedelta(minutes=20)
    gone = db.get(Complaint, create_complaint("high")["id"])
    gone.due_at = utcnow() - timedelta(minutes=5)
    db.commit()

    first = client.post(f"{API}/sla/check", headers=manager_h).json()
    assert first == {"approaching_notified": 1, "breached_notified": 1}
    assert client.post(f"{API}/sla/check", headers=manager_h).json() == {"approaching_notified": 0, "breached_notified": 0}
    types = {n["type"] for n in client.get(f"{API}/notifications", headers=agent_h).json()["items"]}
    assert "sla_approaching" in types
    mgr_types = {n["type"] for n in client.get(f"{API}/notifications", headers=manager_h).json()["items"]}
    assert "sla_breached" in mgr_types
