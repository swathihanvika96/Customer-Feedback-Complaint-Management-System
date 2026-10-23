import pytest

from app.core.exceptions import UnauthorizedError
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security import hash_password, verify_password
from app.schemas.auth import RegisterRequest
from app.services import auth_service
from app.core.exceptions import ConflictError


def test_password_hash_and_verify():
    hashed = hash_password("Secret123")
    assert hashed != "Secret123"
    assert verify_password("Secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_and_refresh_tokens_are_not_interchangeable():
    access = create_access_token(1, "admin")
    refresh, _ = create_refresh_token(1)
    assert decode_token(access, "access")["sub"] == "1"
    with pytest.raises(UnauthorizedError):
        decode_token(access, "refresh")
    with pytest.raises(UnauthorizedError):
        decode_token(refresh, "access")


def test_garbage_token_rejected():
    with pytest.raises(UnauthorizedError):
        decode_token("not-a-token", "access")


def test_register_customer_and_duplicate(db):
    payload = RegisterRequest(email="a@b.com", full_name="Ann Lee", password="Passw0rd1")
    user = auth_service.register_customer(db, payload)
    assert user.customer_profile is not None
    with pytest.raises(ConflictError):
        auth_service.register_customer(db, payload)


def test_weak_password_rejected():
    with pytest.raises(ValueError):
        RegisterRequest(email="a@b.com", full_name="Ann Lee", password="short")
