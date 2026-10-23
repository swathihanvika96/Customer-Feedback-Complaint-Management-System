from datetime import timedelta

from app.models import Complaint
from app.utils.datetime_utils import utcnow

API = "/api/v1"


def fb(client, h, cat, rating, text):
    return client.post(f"{API}/feedback", headers=h, json={"category_id": cat, "rating": rating, "description": text})


def test_empty_dashboard(client, manager_h):
    s = client.get(f"{API}/dashboard/summary", headers=manager_h).json()
    assert s["total_complaints"] == 0 and s["average_resolution_hours"] is None and s["average_customer_rating"] is None
    assert [p["count"] for p in s["complaints_by_priority"]] == [0, 0, 0]


def test_summary_metrics(client, db, create_complaint, assigned_complaint, agent_h, customer_h, manager_h, category_id):
    # assigned_complaint (medium) -> resolved ; two more open ; one overdue
    cid = assigned_complaint["id"]
    client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"})
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "All sorted out"})
    create_complaint("high")
    late = create_complaint("low")
    c = db.get(Complaint, late["id"])
    c.due_at = utcnow() - timedelta(hours=1)
    db.commit()
    fb(client, customer_h, category_id, 5, "great one")
    fb(client, customer_h, category_id, 2, "poor one")

    s = client.get(f"{API}/dashboard/summary", headers=manager_h).json()
    assert s["total_customers"] == 1
    assert s["total_feedback"] == 2
    assert s["total_complaints"] == 3
    assert s["open_complaints"] == 2
    assert s["resolved_complaints"] == 1
    assert s["overdue_complaints"] == 1
    assert s["average_customer_rating"] == 3.5
    assert s["average_resolution_hours"] is not None and s["average_resolution_hours"] < 1
    by_p = {p["priority"]: p["count"] for p in s["complaints_by_priority"]}
    assert by_p == {"high": 1, "medium": 1, "low": 1}


def test_date_range_filtering(client, create_complaint, manager_h):
    create_complaint()
    assert client.get(f"{API}/dashboard/summary", headers=manager_h, params={"date_from": "2000-01-01"}).json()["total_complaints"] == 1
    assert client.get(f"{API}/dashboard/summary", headers=manager_h, params={"date_to": "2000-01-01"}).json()["total_complaints"] == 0
    assert client.get(f"{API}/dashboard/summary", headers=manager_h, params={"date_from": "2030-01-01", "date_to": "2020-01-01"}).status_code == 400


def test_agent_wise_counts_paginated_and_sorted(client, create_complaint, assigned_complaint, manager_h, agent_id):
    r = client.get(f"{API}/dashboard/agent-complaints", headers=manager_h, params={"sort_by": "total", "size": 5}).json()
    assert r["total"] == 1
    row = r["items"][0]
    assert row["agent_id"] == agent_id and row["total"] == 1 and row["open"] == 1 and row["resolved"] == 0
    assert client.get(f"{API}/dashboard/agent-complaints", headers=manager_h, params={"sort_by": "bogus"}).status_code == 400


def test_dashboard_is_manager_only(client, agent_h, customer_h, manager_h, admin_h):
    for h in (agent_h, customer_h):
        assert client.get(f"{API}/dashboard/summary", headers=h).status_code == 403
    for h in (manager_h, admin_h):
        assert client.get(f"{API}/dashboard/summary", headers=h).status_code == 200
