"""Request/response models for authentication and users (SRS §19.4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RoleName = Literal["ADMIN", "INVESTIGATOR", "ANALYST"]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    user_id: str
    username: str
    role: RoleName
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: str | None


class LoginUser(BaseModel):
    user_id: str
    username: str
    role: RoleName


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - OAuth token type, not a secret
    expires_in: int
    user: LoginUser


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    role: RoleName
    password: str = Field(min_length=1, max_length=256)


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: RoleName | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=1, max_length=256)


class UserPage(BaseModel):
    items: list[UserOut]
    page: int
    page_size: int
    total: int
    total_is_capped: bool
