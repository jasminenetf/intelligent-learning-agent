"""Authentication compatibility routes for the local no-login demo.

The current product target is "double-click, fill an API key, use every
feature".  All auth dependencies therefore resolve to one local demo admin
user.  The old login/register endpoints remain as compatibility shims for
scripts and older frontend code, but the UI no longer requires them.
"""

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session
from sqlmodel import select

from app.core.database import get_session
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

DEMO_USERNAME = "local_demo_admin"
DEMO_PASSWORD_HINT = "no-login"


def _get_or_create_demo_user(session: Session) -> User:
    user = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
    if user:
        if user.role != "admin" or not user.is_active:
            user.role = "admin"
            user.is_active = True
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    user = User(
        username=DEMO_USERNAME,
        email="local-demo@example.invalid",
        hashed_password="no-login-demo-user",
        role="admin",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "authenticated": True,
        "mode": "no-login-demo",
    }


@router.post("/register")
def register(session: Session = Depends(get_session)):
    user = _get_or_create_demo_user(session)
    return {
        "ok": True,
        "access_token": "local-demo-token",
        "token_type": "bearer",
        "user": _user_payload(user),
        "message": "No login required. A local demo admin user is active.",
    }


@router.post("/login")
def login(session: Session = Depends(get_session)):
    user = _get_or_create_demo_user(session)
    return {
        "ok": True,
        "access_token": "local-demo-token",
        "token_type": "bearer",
        "user": _user_payload(user),
        "message": "No login required. A local demo admin user is active.",
    }


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    return _get_or_create_demo_user(session)


def get_current_user_optional(
    request: Request,
    session: Session = Depends(get_session),
) -> User:
    return _get_or_create_demo_user(session)


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return _user_payload(user)
