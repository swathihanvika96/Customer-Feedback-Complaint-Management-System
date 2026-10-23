from tests.conftest import PASSWORD

API = "/api/v1"


def test_register_login_me(client):
    r = client.post(f"{API}/auth/register", json={"email": "New@Example.com", "full_name": "New User", "password": PASSWORD})
    assert r.status_code == 201
    assert r.json()["role"] == "customer" and r.json()["email"] == "new@example.com"

    r = client.post(f"{API}/auth/login", data={"username": "new@example.com", "password": PASSWORD})
    assert r.status_code == 200
    tokens = r.json()
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "new@example.com"


def test_duplicate_registration_conflicts(client):
    body = {"email": "dup@example.com", "full_name": "Dup User", "password": PASSWORD}
    assert client.post(f"{API}/auth/register", json=body).status_code == 201
    r = client.post(f"{API}/auth/register", json=body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


def test_weak_password_gives_422_with_field(client):
    r = client.post(f"{API}/auth/register", json={"email": "w@example.com", "full_name": "Weak One", "password": "abc"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert r.json()["error"]["details"][0]["field"] == "password"


def test_wrong_password_and_unknown_user(client, customer_user):
    assert client.post(f"{API}/auth/login", data={"username": customer_user.email, "password": "nope12345"}).status_code == 401
    assert client.post(f"{API}/auth/login", data={"username": "ghost@example.com", "password": PASSWORD}).status_code == 401


def test_protected_endpoint_requires_token(client):
    assert client.get(f"{API}/auth/me").status_code == 401
    assert client.get(f"{API}/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_refresh_rotation_and_logout(client, customer_user):
    tokens = client.post(f"{API}/auth/login", data={"username": customer_user.email, "password": PASSWORD}).json()
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # old refresh token is single-use
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    new = r.json()
    assert client.post(f"{API}/auth/logout", json={"refresh_token": new["refresh_token"]}).status_code == 204
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": new["refresh_token"]}).status_code == 401


def test_deactivated_account_cannot_login_or_use_token(client, admin_h, customer_user, customer_h):
    assert client.post(f"{API}/users/{customer_user.id}/deactivate", headers=admin_h).status_code == 200
    assert client.get(f"{API}/auth/me", headers=customer_h).status_code == 403
    assert client.post(f"{API}/auth/login", data={"username": customer_user.email, "password": PASSWORD}).status_code == 403
    assert client.post(f"{API}/users/{customer_user.id}/activate", headers=admin_h).status_code == 200
    assert client.get(f"{API}/auth/me", headers=customer_h).status_code == 200


def test_admin_cannot_deactivate_self(client, admin, admin_h):
    assert client.post(f"{API}/users/{admin.id}/deactivate", headers=admin_h).status_code == 400


def test_admin_creates_users_with_roles(client, admin_h):
    r = client.post(f"{API}/users", headers=admin_h, json={
        "email": "boss@example.com", "full_name": "The Boss", "password": PASSWORD, "role": "support_manager"})
    assert r.status_code == 201 and r.json()["role"] == "support_manager"
