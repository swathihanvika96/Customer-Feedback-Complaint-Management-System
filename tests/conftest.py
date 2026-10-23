import os

os.environ["BCRYPT_ROUNDS"] = "4"  # fast hashing in tests
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SLA_CHECK_INTERVAL_SECONDS"] = "0"

import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.constants import Role
from app.core.security import hash_password
from app.db.base import Base
from app.db.init_db import seed_defaults
from app.dependencies import get_db
from app.main import app
from app.models import Category, Customer, SupportAgent, User

PASSWORD = "Passw0rd!"
_counter = itertools.count(1)


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    seed_defaults(session)
    yield session
    session.close()


@pytest.fixture()
def client(session_factory, db):
    def _get_db():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db):
    def _make(role: Role, email: str | None = None, **kwargs) -> User:
        n = next(_counter)
        email = email or f"{role.value}{n}@example.com"
        user = User(email=email, full_name=f"{role.value.title()} {n}", hashed_password=hash_password(PASSWORD), role=role)
        db.add(user)
        db.flush()
        if role == Role.CUSTOMER:
            db.add(Customer(user_id=user.id, name=user.full_name, email=email))
        elif role == Role.SUPPORT_AGENT:
            db.add(SupportAgent(user_id=user.id, department="Support", max_workload=kwargs.get("max_workload", 10)))
        db.commit()
        return user

    return _make


@pytest.fixture()
def login(client):
    def _login(user: User) -> dict:
        r = client.post("/api/v1/auth/login", data={"username": user.email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login


@pytest.fixture()
def admin(make_user): return make_user(Role.ADMIN)
@pytest.fixture()
def manager(make_user): return make_user(Role.SUPPORT_MANAGER)
@pytest.fixture()
def agent_user(make_user): return make_user(Role.SUPPORT_AGENT)
@pytest.fixture()
def customer_user(make_user): return make_user(Role.CUSTOMER)
@pytest.fixture()
def admin_h(admin, login): return login(admin)
@pytest.fixture()
def manager_h(manager, login): return login(manager)
@pytest.fixture()
def agent_h(agent_user, login): return login(agent_user)
@pytest.fixture()
def customer_h(customer_user, login): return login(customer_user)


@pytest.fixture()
def category_id(db) -> int:
    return db.query(Category).filter(Category.name == "Product Quality").one().id


@pytest.fixture()
def agent_id(db, agent_user) -> int:
    return db.query(SupportAgent).filter(SupportAgent.user_id == agent_user.id).one().id


@pytest.fixture()
def create_complaint(client, customer_h, category_id):
    def _create(priority="medium", **extra):
        payload = {"title": "Broken item", "description": "The item arrived broken", "category_id": category_id,
                   "priority": priority, "severity": "major", **extra}
        r = client.post("/api/v1/complaints", json=payload, headers=customer_h)
        assert r.status_code == 201, r.text
        return r.json()

    return _create


@pytest.fixture()
def assigned_complaint(client, create_complaint, manager_h, agent_id):
    c = create_complaint()
    r = client.post(f"/api/v1/complaints/{c['id']}/assign", json={"agent_id": agent_id}, headers=manager_h)
    assert r.status_code == 200, r.text
    return r.json()
