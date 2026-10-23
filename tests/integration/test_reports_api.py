API = "/api/v1"


def fb(client, h, cat, rating, text, **extra):
    r = client.post(f"{API}/feedback", headers=h, json={"category_id": cat, "rating": rating, "description": text, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_satisfaction_report(client, customer_h, manager_h, category_id):
    for i, rating in enumerate([5, 4, 3, 2, 1, 5]):
        fb(client, customer_h, category_id, rating, f"feedback {i}")
    s = client.get(f"{API}/reports/satisfaction", headers=manager_h).json()
    assert s == {"total_feedback": 6, "average_rating": 3.33, "positive_count": 3, "neutral_count": 1,
                 "negative_count": 2, "satisfaction_percentage": 50.0}
    cats = client.get(f"{API}/reports/satisfaction/categories", headers=manager_h).json()
    assert len(cats) == 1 and cats[0]["category_name"] == "Product Quality" and cats[0]["total_feedback"] == 6
    trend = client.get(f"{API}/reports/satisfaction/trends", headers=manager_h).json()
    assert len(trend) == 1 and trend[0]["total_feedback"] == 6 and trend[0]["average_rating"] == 3.33
    assert client.get(f"{API}/reports/satisfaction", headers=manager_h, params={"date_to": "2000-01-01"}).json()["total_feedback"] == 0


def test_formulas_documented(client, manager_h):
    f = client.get(f"{API}/reports/satisfaction/formulas", headers=manager_h).json()
    assert {"average_rating", "positive_count", "negative_count", "satisfaction_percentage", "feedback_trends"} <= set(f)


def test_resolved_complaint_satisfaction(client, assigned_complaint, create_complaint, agent_h, customer_h, manager_h, category_id):
    cid = assigned_complaint["id"]
    create_complaint()  # stays open
    client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"})
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "Fixed for the customer"})
    fb(client, customer_h, category_id, 5, "great fix", complaint_id=cid)
    fb(client, customer_h, category_id, 1, "unrelated general")
    r = client.get(f"{API}/reports/satisfaction/resolved-complaints", headers=manager_h).json()
    assert r["total_feedback"] == 1 and r["average_rating"] == 5.0 and r["satisfaction_percentage"] == 100.0
    assert r["resolved_complaints"] == 1 and r["resolved_with_feedback"] == 1 and r["feedback_response_rate"] == 100.0


def test_complaints_by_category_and_agent_performance(client, assigned_complaint, agent_h, manager_h, agent_id):
    cid = assigned_complaint["id"]
    client.post(f"{API}/complaints/{cid}/status", headers=agent_h, json={"status": "in_progress"})
    client.post(f"{API}/complaints/{cid}/resolve", headers=agent_h, json={"summary": "Fixed for the customer"})
    cats = client.get(f"{API}/reports/complaints-by-category", headers=manager_h).json()
    assert cats[0]["total"] == 1 and cats[0]["resolved"] == 1 and cats[0]["open"] == 0
    perf = client.get(f"{API}/reports/agent-performance", headers=manager_h).json()["items"][0]
    assert perf["agent_id"] == agent_id and perf["assigned"] == 1 and perf["resolved"] == 1
    assert perf["average_resolution_hours"] is not None


def test_reports_forbidden_for_non_managers(client, customer_h, agent_h):
    for h in (customer_h, agent_h):
        assert client.get(f"{API}/reports/satisfaction", headers=h).status_code == 403
        assert client.get(f"{API}/audit-logs", headers=h).status_code == 403
