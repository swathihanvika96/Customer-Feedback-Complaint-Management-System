from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Register a new customer account")
def register(payload: RegisterRequest, db: DbSession):
    return auth_service.register_customer(db, payload)


@router.post("/login", response_model=TokenPair, summary="Login (OAuth2 form: username = email)",
             description="Example: username `ravi@example.com`, password `Ravi@12345`. Or use the Authorize button.")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    user = auth_service.authenticate(db, form.username, form.password)
    return auth_service.issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token for a new token pair")
def refresh(payload: RefreshRequest, db: DbSession):
    return auth_service.refresh_tokens(db, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a refresh token")
def logout(payload: RefreshRequest, db: DbSession):
    auth_service.logout(db, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: CurrentUser):
    return user
