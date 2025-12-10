"""
Authentication Models for GhostQA
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: str  # Stored as bcrypt hash
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    must_change_password: bool = False  # True when admin resets password


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.USER


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    is_active: bool
    must_change_password: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse


class TokenData(BaseModel):
    user_id: str
    username: str
    role: UserRole
    exp: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForceChangePasswordRequest(BaseModel):
    new_password: str


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
