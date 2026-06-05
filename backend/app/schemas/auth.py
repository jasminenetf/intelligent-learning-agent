"""Pydantic schemas for authentication."""

from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import VALID_ROLES


class RegisterRequest(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    role: str = "student"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of: {', '.join(VALID_ROLES)}")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
