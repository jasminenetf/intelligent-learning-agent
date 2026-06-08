"""Pydantic schemas for authentication."""

from typing import Optional

from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
