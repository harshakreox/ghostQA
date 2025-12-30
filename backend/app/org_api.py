"""
Organization Management API for GhostQA
Handles organization CRUD, member management, and project assignments
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
import re

from org_models import (
    Organization, OrganizationMember, ProjectMember, OrganizationInvite,
    CreateOrganizationRequest, UpdateOrganizationRequest,
    AddOrgMemberRequest, UpdateOrgMemberRequest,
    AddProjectMemberRequest, UpdateProjectMemberRequest,
    OrganizationResponse, OrgMemberResponse, ProjectMemberResponse,
    OrgRole, ProjectRole, AccessibleProjectResponse,
    CreateInviteRequest, InviteResponse, ValidateInviteResponse,
    RegisterWithInviteRequest
)
from org_storage import get_org_storage
from auth_api import get_current_user, get_current_admin
from auth_models import TokenData, UserRole
from auth_storage import get_auth_storage
from permissions import PermissionChecker
from storage import get_storage

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = text.strip('-')
    return text or 'default'


# ============ Organization CRUD ============

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: CreateOrganizationRequest,
    current_user: TokenData = Depends(get_current_admin)
):
    """Create a new organization (system admin only)"""
    org_storage = get_org_storage()

    # Generate slug if not provided
    slug = request.slug or slugify(request.name)

    # Check if slug already exists
    existing = org_storage.get_organization_by_slug(slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{slug}' already exists"
        )

    org = Organization(
        name=request.name,
        slug=slug,
        description=request.description
    )

    org_storage.save_organization(org)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        created_at=org.created_at,
        is_active=org.is_active,
        member_count=0,
        project_count=0
    )


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: TokenData = Depends(get_current_admin)
):
    """List all organizations (system admin only)"""
    org_storage = get_org_storage()
    storage = get_storage()

    organizations = org_storage.get_all_organizations()
    all_projects = storage.get_all_projects()

    result = []
    for org in organizations:
        member_count = org_storage.get_org_member_count(org.id)
        project_count = len([p for p in all_projects if p.organization_id == org.id])

        result.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            created_at=org.created_at,
            is_active=org.is_active,
            member_count=member_count,
            project_count=project_count
        ))

    return result


@router.get("/me/organization", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: TokenData = Depends(get_current_user)
):
    """Get current user's organization"""
    org_storage = get_org_storage()
    storage = get_storage()

    membership = org_storage.get_user_org_membership(current_user.user_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of any organization"
        )

    org = org_storage.get_organization(membership.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    all_projects = storage.get_all_projects()
    member_count = org_storage.get_org_member_count(org.id)
    project_count = len([p for p in all_projects if p.organization_id == org.id])

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        created_at=org.created_at,
        is_active=org.is_active,
        member_count=member_count,
        project_count=project_count,
        my_role=membership.org_role.value if hasattr(membership.org_role, 'value') else membership.org_role
    )


@router.get("/me/projects", response_model=List[AccessibleProjectResponse])
async def get_my_accessible_projects(
    current_user: TokenData = Depends(get_current_user)
):
    """Get list of projects current user can access"""
    org_storage = get_org_storage()
    storage = get_storage()

    membership = org_storage.get_user_org_membership(current_user.user_id)
    if not membership:
        return []

    org_role = membership.org_role
    if isinstance(org_role, str):
        org_role = OrgRole(org_role)

    all_projects = storage.get_all_projects()
    org_projects = [p for p in all_projects if p.organization_id == membership.organization_id]

    result = []

    # Org admins can access all org projects
    if org_role == OrgRole.ORG_ADMIN:
        for project in org_projects:
            result.append(AccessibleProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                my_role=ProjectRole.OWNER,  # Org admin has full access
                member_count=org_storage.get_project_member_count(project.id)
            ))
    else:
        # Get user's project memberships
        project_memberships = org_storage.get_user_project_memberships(current_user.user_id)
        accessible_project_ids = {pm.project_id: pm for pm in project_memberships}

        for project in org_projects:
            if project.id in accessible_project_ids:
                pm = accessible_project_ids[project.id]
                role = pm.project_role
                if isinstance(role, str):
                    role = ProjectRole(role)
                result.append(AccessibleProjectResponse(
                    id=project.id,
                    name=project.name,
                    description=project.description,
                    my_role=role,
                    member_count=org_storage.get_project_member_count(project.id)
                ))

    return result


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get organization details"""
    org_storage = get_org_storage()
    storage = get_storage()

    # Check if user has access to this org
    if current_user.role != UserRole.ADMIN:
        membership = org_storage.get_user_org_membership(current_user.user_id)
        if not membership or membership.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )

    org = org_storage.get_organization(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    all_projects = storage.get_all_projects()
    member_count = org_storage.get_org_member_count(org.id)
    project_count = len([p for p in all_projects if p.organization_id == org.id])

    # Get user's role in this org
    membership = org_storage.get_user_org_membership(current_user.user_id)
    my_role = None
    if membership and membership.organization_id == org_id:
        my_role = membership.org_role.value if hasattr(membership.org_role, 'value') else membership.org_role

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        created_at=org.created_at,
        is_active=org.is_active,
        member_count=member_count,
        project_count=project_count,
        my_role=my_role
    )


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    request: UpdateOrganizationRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Update organization details (org admin only)"""
    org_storage = get_org_storage()

    # Check permissions
    PermissionChecker.require_org_admin(current_user)

    org = org_storage.get_organization(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Update fields
    if request.name is not None:
        org.name = request.name
    if request.description is not None:
        org.description = request.description
    if request.is_active is not None:
        org.is_active = request.is_active

    org_storage.save_organization(org)

    member_count = org_storage.get_org_member_count(org.id)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        created_at=org.created_at,
        is_active=org.is_active,
        member_count=member_count,
        project_count=0
    )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Delete an organization (system admin only)"""
    org_storage = get_org_storage()

    org = org_storage.get_organization(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check if organization has members
    member_count = org_storage.get_org_member_count(org_id)
    if member_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete organization with {member_count} members"
        )

    org_storage.delete_organization(org_id)


# ============ Organization Members ============

@router.get("/{org_id}/members", response_model=List[OrgMemberResponse])
async def list_org_members(
    org_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """List all members of an organization"""
    org_storage = get_org_storage()
    auth_storage = get_auth_storage()

    # Check access
    if current_user.role != UserRole.ADMIN:
        membership = org_storage.get_user_org_membership(current_user.user_id)
        if not membership or membership.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    members = org_storage.get_org_members(org_id)

    result = []
    for member in members:
        user = auth_storage.get_user(member.user_id)
        if user:
            result.append(OrgMemberResponse(
                id=member.id,
                user_id=member.user_id,
                username=user.username,
                email=user.email,
                org_role=member.org_role,
                joined_at=member.joined_at,
                is_active=user.is_active
            ))

    return result


@router.post("/{org_id}/members", status_code=status.HTTP_201_CREATED)
async def add_org_member(
    org_id: str,
    request: AddOrgMemberRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Add a user to the organization (org admin only)"""
    org_storage = get_org_storage()
    auth_storage = get_auth_storage()

    # Check permissions
    PermissionChecker.require_org_admin(current_user)

    # Check if org exists
    org = org_storage.get_organization(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check if user exists
    user = auth_storage.get_user(request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already a member
    existing = org_storage.get_org_member(org_id, request.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )

    # Create membership
    member = OrganizationMember(
        organization_id=org_id,
        user_id=request.user_id,
        org_role=request.org_role,
        invited_by=current_user.user_id
    )

    org_storage.add_org_member(member)

    # Update user's organization_id
    user.organization_id = org_id
    auth_storage.save_user(user)

    return {"message": "Member added successfully", "membership_id": member.id}


@router.put("/{org_id}/members/{user_id}")
async def update_org_member(
    org_id: str,
    user_id: str,
    request: UpdateOrgMemberRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Update a member's organization role (org admin only)"""
    org_storage = get_org_storage()

    # Check permissions
    PermissionChecker.require_org_admin(current_user)

    # Cannot change your own role
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )

    success = org_storage.update_org_member_role(org_id, user_id, request.org_role)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    return {"message": "Member role updated successfully"}


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_member(
    org_id: str,
    user_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Remove a user from the organization (org admin only)"""
    org_storage = get_org_storage()
    auth_storage = get_auth_storage()

    # Check permissions
    PermissionChecker.require_org_admin(current_user)

    # Cannot remove yourself
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the organization"
        )

    success = org_storage.remove_org_member(org_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    # Clear user's organization_id
    user = auth_storage.get_user(user_id)
    if user:
        user.organization_id = None
        auth_storage.save_user(user)


# ============ Project Members ============

@router.get("/{org_id}/projects/{project_id}/members", response_model=List[ProjectMemberResponse])
async def list_project_members(
    org_id: str,
    project_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """List all members of a project"""
    org_storage = get_org_storage()
    auth_storage = get_auth_storage()

    # Check project access
    PermissionChecker.require_project_access(current_user, project_id)

    members = org_storage.get_project_members(project_id)

    result = []
    for member in members:
        user = auth_storage.get_user(member.user_id)
        if user:
            result.append(ProjectMemberResponse(
                id=member.id,
                user_id=member.user_id,
                username=user.username,
                email=user.email,
                project_role=member.project_role,
                assigned_at=member.assigned_at
            ))

    return result


@router.post("/{org_id}/projects/{project_id}/members", status_code=status.HTTP_201_CREATED)
async def add_project_member(
    org_id: str,
    project_id: str,
    request: AddProjectMemberRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Add a user to a project (owner/manager only)"""
    org_storage = get_org_storage()
    auth_storage = get_auth_storage()
    storage = get_storage()

    # Check permissions
    PermissionChecker.require_project_member_management(current_user, project_id)

    # Check if project exists
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check if user exists and is in the same org
    user = auth_storage.get_user(request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_membership = org_storage.get_user_org_membership(request.user_id)
    if not user_membership or user_membership.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this organization"
        )

    # Check if already a project member
    existing = org_storage.get_project_member(project_id, request.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project"
        )

    # Create membership
    member = ProjectMember(
        project_id=project_id,
        user_id=request.user_id,
        project_role=request.project_role,
        assigned_by=current_user.user_id
    )

    org_storage.add_project_member(member)

    return {"message": "Member added to project successfully", "membership_id": member.id}


@router.put("/{org_id}/projects/{project_id}/members/{user_id}")
async def update_project_member(
    org_id: str,
    project_id: str,
    user_id: str,
    request: UpdateProjectMemberRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Update a member's project role (owner only)"""
    org_storage = get_org_storage()

    # Check permissions - only project owner can change roles
    project_role = PermissionChecker.get_user_project_role(current_user.user_id, project_id)
    if project_role != ProjectRole.OWNER and not PermissionChecker.can_manage_organization(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can change member roles"
        )

    # Cannot change owner role if you're the only owner
    if user_id == current_user.user_id and request.project_role != ProjectRole.OWNER:
        # Check if there's another owner
        members = org_storage.get_project_members(project_id)
        owner_count = sum(1 for m in members if m.project_role == ProjectRole.OWNER or m.project_role == 'owner')
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the only project owner"
            )

    success = org_storage.update_project_member_role(project_id, user_id, request.project_role)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    return {"message": "Member role updated successfully"}


@router.delete("/{org_id}/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    org_id: str,
    project_id: str,
    user_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Remove a user from a project (owner only)"""
    org_storage = get_org_storage()

    # Check permissions
    PermissionChecker.require_project_member_management(current_user, project_id)

    # Cannot remove yourself if you're the only owner
    if user_id == current_user.user_id:
        member = org_storage.get_project_member(project_id, user_id)
        if member and (member.project_role == ProjectRole.OWNER or member.project_role == 'owner'):
            members = org_storage.get_project_members(project_id)
            owner_count = sum(1 for m in members if m.project_role == ProjectRole.OWNER or m.project_role == 'owner')
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the only project owner"
                )

    success = org_storage.remove_project_member(project_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )



# ============ Organization Invites ============

@router.post("/{org_id}/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    org_id: str,
    request: CreateInviteRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Create an invite link for an organization (super admin, org admin, or manager)"""
    org_storage = get_org_storage()

    # Super admin can create invites for any org
    is_super_admin = current_user.role == UserRole.ADMIN

    if not is_super_admin:
        # Check permissions - must be org admin or manager
        membership = org_storage.get_user_org_membership(current_user.user_id)
        if not membership or membership.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")

        org_role = membership.org_role
        if hasattr(org_role, 'value'):
            org_role = org_role.value

        if org_role not in ['org_admin', 'manager']:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only org admins and managers can create invites")
    
    # Get organization
    org = org_storage.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    
    # Create invite
    invite = OrganizationInvite(
        organization_id=org_id,
        token=token,
        email=request.email,
        org_role=request.org_role,
        created_by=current_user.user_id,
        expires_at=datetime.now() + timedelta(hours=request.expires_in_hours),
        max_uses=request.max_uses
    )
    
    org_storage.save_invite(invite)
    
    # Build invite URL (frontend will need to handle this route)
    invite_url = f"/register?invite={token}"
    
    return InviteResponse(
        id=invite.id,
        organization_id=invite.organization_id,
        organization_name=org.name,
        token=invite.token,
        invite_url=invite_url,
        email=invite.email,
        org_role=invite.org_role,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        use_count=invite.use_count,
        is_active=invite.is_active,
        is_expired=datetime.now() > invite.expires_at
    )


@router.get("/{org_id}/invites", response_model=List[InviteResponse])
async def list_invites(
    org_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """List all invites for an organization (org admin only)"""
    org_storage = get_org_storage()
    
    # Check permissions
    membership = org_storage.get_user_org_membership(current_user.user_id)
    if not membership or membership.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    
    org_role = membership.org_role
    if hasattr(org_role, 'value'):
        org_role = org_role.value
    
    if org_role != 'org_admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only org admins can view invites")
    
    org = org_storage.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    invites = org_storage.get_org_invites(org_id)
    
    return [
        InviteResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            organization_name=org.name,
            token=inv.token,
            invite_url=f"/register?invite={inv.token}",
            email=inv.email,
            org_role=inv.org_role,
            created_at=inv.created_at,
            expires_at=inv.expires_at,
            max_uses=inv.max_uses,
            use_count=inv.use_count,
            is_active=inv.is_active,
            is_expired=datetime.now() > inv.expires_at
        )
        for inv in invites
    ]


@router.delete("/{org_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    org_id: str,
    invite_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Revoke an invite (org admin only)"""
    org_storage = get_org_storage()
    
    # Check permissions
    membership = org_storage.get_user_org_membership(current_user.user_id)
    if not membership or membership.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization")
    
    org_role = membership.org_role
    if hasattr(org_role, 'value'):
        org_role = org_role.value
    
    if org_role != 'org_admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only org admins can revoke invites")
    
    success = org_storage.delete_invite(invite_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")


# Public endpoint - no auth required
@router.get("/invites/validate/{token}", response_model=ValidateInviteResponse)
async def validate_invite(token: str):
    """Validate an invite token (public endpoint)"""
    org_storage = get_org_storage()
    
    invite = org_storage.get_invite_by_token(token)
    
    if not invite:
        return ValidateInviteResponse(
            valid=False,
            message="Invalid or expired invite link"
        )
    
    # Check if expired
    if datetime.now() > invite.expires_at:
        return ValidateInviteResponse(
            valid=False,
            message="This invite link has expired"
        )
    
    # Check if max uses reached
    if invite.use_count >= invite.max_uses:
        return ValidateInviteResponse(
            valid=False,
            message="This invite link has already been used"
        )
    
    # Check if deactivated
    if not invite.is_active:
        return ValidateInviteResponse(
            valid=False,
            message="This invite link is no longer active"
        )
    
    # Get organization name
    org = org_storage.get_organization(invite.organization_id)
    org_name = org.name if org else "Unknown Organization"
    
    return ValidateInviteResponse(
        valid=True,
        organization_name=org_name,
        organization_id=invite.organization_id,
        org_role=invite.org_role,
        email_required=invite.email,
        message=f"You are invited to join {org_name}"
    )
