"""
Authentication API for GhostQA
JWT-based authentication with 30-minute session expiry
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import os

from auth_models import (
    User, UserCreate, UserLogin, UserResponse, Token, TokenData,
    UserRole, ChangePasswordRequest, UpdateUserRequest, ForceChangePasswordRequest
)
from auth_storage import get_auth_storage, AuthStorage

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# JWT Configuration
# SECURITY: JWT_SECRET_KEY must be set in environment
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    print("[SECURITY WARNING] JWT_SECRET_KEY not set! Using auto-generated key.")
    print("[SECURITY WARNING] Sessions will be invalidated on server restart.")
    print("[SECURITY WARNING] Set JWT_SECRET_KEY in .env for production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minute session expiry

security = HTTPBearer()


def create_access_token(user: User) -> Token:
    """Create JWT access token with 30 minute expiry"""
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token_data = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value,
        "exp": expires_at
    }

    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        is_active=user.is_active,
        must_change_password=user.must_change_password
    )

    return Token(
        access_token=access_token,
        expires_at=expires_at,
        user=user_response
    )


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(
            user_id=payload["user_id"],
            username=payload["username"],
            role=UserRole(payload["role"]),
            exp=datetime.fromtimestamp(payload["exp"])
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Get current user from JWT token"""
    token = credentials.credentials
    return decode_token(token)


async def get_current_admin(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[TokenData]:
    """Get current user if token provided (optional auth)"""
    if not credentials:
        return None
    try:
        return decode_token(credentials.credentials)
    except HTTPException:
        return None


# ============ Auth Endpoints ============

@router.post("/login", response_model=Token)
async def login(request: UserLogin):
    """Login with username and password"""
    auth_storage = get_auth_storage()
    user = auth_storage.authenticate(request.username, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )

    return create_access_token(user)


@router.post("/register", response_model=Token)
async def register(request: UserCreate):
    """Register a new user (admin only can set role, otherwise defaults to user)"""
    auth_storage = get_auth_storage()

    # Check if username exists
    if auth_storage.get_user_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email exists
    if auth_storage.get_user_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user (default to USER role for public registration)
    user = User(
        username=request.username,
        email=request.email,
        password_hash=auth_storage.hash_password(request.password),
        role=UserRole.USER  # Always USER for self-registration
    )

    auth_storage.save_user(user)
    return create_access_token(user)




@router.post("/register-with-invite", response_model=Token)
async def register_with_invite(request_data: dict):
    """Register a new user using an invite token"""
    from org_models import OrganizationMember, OrgRole
    from datetime import datetime
    
    token = request_data.get('token')
    username = request_data.get('username')
    email = request_data.get('email')
    password = request_data.get('password')
    
    if not all([token, username, email, password]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: token, username, email, password"
        )
    
    auth_storage = get_auth_storage()
    org_storage = get_org_storage()
    
    # Validate invite
    invite = org_storage.get_invite_by_token(token)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite token"
        )
    
    # Check if expired
    if datetime.now() > invite.expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has expired"
        )
    
    # Check if max uses reached
    if invite.use_count >= invite.max_uses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has already been used"
        )
    
    # Check if invite requires specific email
    if invite.email and invite.email.lower() != email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This invite is for {invite.email} only"
        )
    
    # Check if username exists
    if auth_storage.get_user_by_username(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    if auth_storage.get_user_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user with organization
    user = User(
        username=username,
        email=email,
        password_hash=auth_storage.hash_password(password),
        role=UserRole.USER,
        organization_id=invite.organization_id
    )
    auth_storage.save_user(user)
    
    # Create org membership
    org_role = invite.org_role
    if isinstance(org_role, str):
        org_role = OrgRole(org_role)
    
    org_member = OrganizationMember(
        organization_id=invite.organization_id,
        user_id=user.id,
        org_role=org_role,
        invited_by=invite.created_by
    )
    org_storage.add_org_member(org_member)
    
    # Increment invite usage
    org_storage.increment_invite_use(invite.id)
    
    return create_access_token(user)

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: TokenData = Depends(get_current_user)):
    """Refresh access token (extends session by 30 minutes)"""
    auth_storage = get_auth_storage()
    user = auth_storage.get_user(current_user.user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return create_access_token(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user information"""
    auth_storage = get_auth_storage()
    user = auth_storage.get_user(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        is_active=user.is_active,
        must_change_password=user.must_change_password
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Change current user's password"""
    auth_storage = get_auth_storage()
    user = auth_storage.get_user(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    if not auth_storage.verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    user.password_hash = auth_storage.hash_password(request.new_password)
    auth_storage.save_user(user)

    return {"message": "Password changed successfully"}


# ============ Admin-only Endpoints ============

@router.get("/users", response_model=List[UserResponse])
async def list_users(current_admin: TokenData = Depends(get_current_admin)):
    """List all users (admin only)"""
    auth_storage = get_auth_storage()
    users = auth_storage.get_all_users()

    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            created_at=u.created_at,
            is_active=u.is_active,
            must_change_password=u.must_change_password
        )
        for u in users
    ]


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    current_admin: TokenData = Depends(get_current_admin)
):
    """Create a new user with specified role (admin only)"""
    auth_storage = get_auth_storage()

    # Check if username exists
    if auth_storage.get_user_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email exists
    if auth_storage.get_user_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user with specified role
    user = User(
        username=request.username,
        email=request.email,
        password_hash=auth_storage.hash_password(request.password),
        role=request.role
    )

    auth_storage.save_user(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        is_active=user.is_active,
        must_change_password=user.must_change_password
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_admin: TokenData = Depends(get_current_admin)
):
    """Update user details (admin only)"""
    auth_storage = get_auth_storage()
    user = auth_storage.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update fields
    if request.email is not None:
        # Check if email is already used by another user
        existing = auth_storage.get_user_by_email(request.email)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = request.email

    if request.role is not None:
        user.role = request.role

    if request.is_active is not None:
        user.is_active = request.is_active

    auth_storage.save_user(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        is_active=user.is_active,
        must_change_password=user.must_change_password
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: TokenData = Depends(get_current_admin)
):
    """Delete a user (admin only)"""
    auth_storage = get_auth_storage()

    # Prevent deleting self
    if user_id == current_admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = auth_storage.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    auth_storage.delete_user(user_id)
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    current_admin: TokenData = Depends(get_current_admin)
):
    """Reset user password to a default (admin only)"""
    auth_storage = get_auth_storage()
    user = auth_storage.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Generate secure random temporary password
    import secrets
    import string
    # Generate 12-char password with letters, digits, and symbols
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    new_password = ''.join(secrets.choice(alphabet) for _ in range(12))

    user.password_hash = auth_storage.hash_password(new_password)
    user.must_change_password = True
    auth_storage.save_user(user)

    return {
        "message": "Password reset successfully",
        "temporary_password": new_password
    }


@router.post("/force-change-password")
async def force_change_password(
    request: ForceChangePasswordRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Change password when forced (doesn't require current password)"""
    auth_storage = get_auth_storage()
    user = auth_storage.get_user(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify user actually needs to change password
    if not user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change not required"
        )

    # Validate new password
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    # Update password and clear the flag
    user.password_hash = auth_storage.hash_password(request.new_password)
    user.must_change_password = False
    auth_storage.save_user(user)

    # Return new token with updated user info
    return create_access_token(user)
