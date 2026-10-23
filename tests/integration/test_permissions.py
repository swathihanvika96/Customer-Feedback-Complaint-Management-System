import pytest

API = "/api/v1"


def call(client, method, path, headers):
    kwargs = {"json": {}} if method == "post" else {}
    return getattr(client, method)(API + path, headers=headers, **kwargs)

# (method, path, who is ALLOWED -> everyone else must be 403)
MANAGER_ONLY = [
    ("get", "/dashboard/summary"),
    ("get", "/reports/satisfaction"),
    ("get", "/audit-logs"),
    ("post", "/sla/check"),
    ("post", "/agents"),
    ("post", "/categories"),
]
ADMIN_ONLY = [("get", "/users"), ("post", "/users")]
STAFF_ONLY = [("get", "/customers"), ("get", "/agents"), ("get", "/sla/overdue")]


@pytest.mark.parametrize("method,path", MANAGER_ONLY)
def test_manager_only_endpoints(client, method, path, customer_h, agent_h, manager_h):
    for h in (customer_h, agent_h):
        assert call(client, method, path, h).status_code == 403
    assert call(client, method, path, manager_h).status_code != 403


@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_admin_only_endpoints(client, method, path, customer_h, agent_h, manager_h, admin_h):
    for h in (customer_h, agent_h, manager_h):
        assert call(client, method, path, h).status_code == 403
    assert call(client, method, path, admin_h).status_code != 403


@pytest.mark.parametrize("method,path", STAFF_ONLY)
def test_staff_only_endpoints(client, method, path, customer_h, agent_h):
    assert getattr(client, method)(API + path, headers=customer_h).status_code == 403
    assert getattr(client, method)(API + path, headers=agent_h).status_code == 200


@pytest.mark.parametrize("path", ["/complaints", "/feedback", "/notifications", "/categories", "/dashboard/summary"])
def test_all_endpoints_require_authentication(client, path):
    assert client.get(API + path).status_code == 401


def test_agent_cannot_view_other_agents_workload(client, make_user, login, agent_id, manager_h):
    from app.core.constants import Role

    other_h = login(make_user(Role.SUPPORT_AGENT))
    assert client.get(f"{API}/agents/{agent_id}/workload", headers=other_h).status_code == 403
    assert client.get(f"{API}/agents/{agent_id}/workload", headers=manager_h).status_code == 200


def test_notifications_are_private(client, assigned_complaint, agent_h, customer_h):
    note = client.get(f"{API}/notifications", headers=agent_h).json()["items"][0]
    assert client.patch(f"{API}/notifications/{note['id']}/read", headers=customer_h).status_code == 403
    assert client.patch(f"{API}/notifications/{note['id']}/read", headers=agent_h).json()["is_read"] is True
    assert client.get(f"{API}/notifications/unread-count", headers=agent_h).json()["unread"] == 0
    assert client.post(f"{API}/notifications/read-all", headers=agent_h).status_code == 200


def test_error_format_has_request_id(client, customer_h):
    r = client.get(f"{API}/complaints/99999", headers=customer_h)
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "not_found" and err["request_id"] and r.headers["X-Request-ID"] == err["request_id"]
