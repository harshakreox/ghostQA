"""
Organization and Multi-Tenant Models for GhostQA
Supports organization-based user management with role hierarchy
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class OrgRole(str, Enum):
    """Organization-level roles"""
    ORG_ADMIN = "org_admin"   # Full org control, manage all users and projects
    MANAGER = "manager"        # Can manage projects, assign users to projects
    MEMBER = "member"          # Can only access assigned projects


class ProjectRole(str, Enum):
    """Project-level permissions"""
    OWNER = "owner"     # Full project control, can delete, assign users
    EDITOR = "editor"   # Can modify test cases, run tests
    VIEWER = "viewer"   # Read-only access


class Organization(BaseModel):
    """Organization - top-level multi-tenant entity"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str  # URL-friendly identifier
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    # Settings
    max_users: Optional[int] = None  # License limit
    max_projects: Optional[int] = None


class OrganizationMember(BaseModel):
    """User membership in an organization"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: str
    org_role: OrgRole = OrgRole.MEMBER
    joined_at: datetime = Field(default_factory=datetime.now)
    invited_by: Optional[str] = None  # user_id who invited


class ProjectMember(BaseModel):
    """User membership in a project with specific role"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    user_id: str
    project_role: ProjectRole = ProjectRole.VIEWER
    assigned_at: datetime = Field(default_factory=datetime.now)
    assigned_by: Optional[str] = None  # user_id who assigned


class OrganizationInvite(BaseModel):
    """Invitation to join an organization"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    token: str  # Unique invite token
    email: Optional[str] = None  # Optional: restrict to specific email
    org_role: OrgRole = OrgRole.MEMBER  # Role user will get when joining
    created_by: str  # user_id who created the invite
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime  # When the invite expires
    max_uses: int = 1  # How many times this invite can be used
    use_count: int = 0  # How many times it has been used
    is_active: bool = True


# ============ Request Models ============

class CreateOrganizationRequest(BaseModel):
    """Request to create a new organization"""
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None


class UpdateOrganizationRequest(BaseModel):
    """Request to update organization details"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class AddOrgMemberRequest(BaseModel):
    """Request to add a user to an organization"""
    user_id: str
    org_role: OrgRole = OrgRole.MEMBER


class UpdateOrgMemberRequest(BaseModel):
    """Request to update a member's organization role"""
    org_role: OrgRole


class AddProjectMemberRequest(BaseModel):
    """Request to add a user to a project"""
    user_id: str
    project_role: ProjectRole = ProjectRole.VIEWER


class UpdateProjectMemberRequest(BaseModel):
    """Request to update a member's project role"""
    project_role: ProjectRole


# ============ Response Models ============

class OrganizationResponse(BaseModel):
    """Organization details for API response"""
    id: str
    name: str
    slug: str
    description: Optional[str]
    created_at: datetime
    is_active: bool
    member_count: int = 0
    project_count: int = 0
    my_role: Optional[str] = None  # Current user's role in this org


class OrgMemberResponse(BaseModel):
    """Organization member details for API response"""
    id: str
    user_id: str
    username: str
    email: str
    org_role: OrgRole
    joined_at: datetime
    is_active: bool = True


class ProjectMemberResponse(BaseModel):
    """Project member details for API response"""
    id: str
    user_id: str
    username: str
    email: str
    project_role: ProjectRole
    assigned_at: datetime


class MyOrganizationResponse(BaseModel):
    """Current user's organization info"""
    organization: OrganizationResponse
    my_role: OrgRole
    accessible_projects: List[str] = []  # List of project IDs


class AccessibleProjectResponse(BaseModel):
    """Project with user's access role"""
    id: str
    name: str
    description: Optional[str]
    my_role: ProjectRole
    member_count: int = 0


# ============ Invite Models ============

class CreateInviteRequest(BaseModel):
    """Request to create an organization invite"""
    email: Optional[str] = None  # Optional: restrict to specific email
    org_role: OrgRole = OrgRole.MEMBER
    expires_in_hours: int = 48  # Default 48 hours
    max_uses: int = 1  # Default single use


class InviteResponse(BaseModel):
    """Invite details for API response"""
    id: str
    organization_id: str
    organization_name: str
    token: str
    invite_url: str
    email: Optional[str]
    org_role: OrgRole
    created_at: datetime
    expires_at: datetime
    max_uses: int
    use_count: int
    is_active: bool
    is_expired: bool


class ValidateInviteResponse(BaseModel):
    """Response when validating an invite token"""
    valid: bool
    organization_name: Optional[str] = None
    organization_id: Optional[str] = None
    org_role: Optional[OrgRole] = None
    email_required: Optional[str] = None  # If invite is for specific email
    message: str


class RegisterWithInviteRequest(BaseModel):
    """Request to register using an invite token"""
    token: str
    username: str
    email: str
    password: str
