"""
Permission checking utilities for organization-based access control
Centralized permission logic for GhostQA
"""
from typing import Optional
from fastapi import HTTPException, status

from org_models import OrgRole, ProjectRole
from org_storage import get_org_storage
from auth_models import TokenData, UserRole


class PermissionChecker:
    """Centralized permission checking for organization-based access control"""

    @staticmethod
    def get_user_org_role(user_id: str) -> Optional[OrgRole]:
        """Get user's role in their organization"""
        org_storage = get_org_storage()
        membership = org_storage.get_user_org_membership(user_id)
        if membership:
            return OrgRole(membership.org_role) if isinstance(membership.org_role, str) else membership.org_role
        return None

    @staticmethod
    def get_user_project_role(user_id: str, project_id: str) -> Optional[ProjectRole]:
        """Get user's role in a specific project"""
        org_storage = get_org_storage()
        membership = org_storage.get_project_member(project_id, user_id)
        if membership:
            return ProjectRole(membership.project_role) if isinstance(membership.project_role, str) else membership.project_role
        return None

    @staticmethod
    def get_user_organization_id(user_id: str) -> Optional[str]:
        """Get user's organization ID"""
        org_storage = get_org_storage()
        membership = org_storage.get_user_org_membership(user_id)
        return membership.organization_id if membership else None

    @staticmethod
    def is_system_admin(current_user: TokenData) -> bool:
        """Check if user is a system-level admin"""
        return current_user.role == UserRole.ADMIN

    @staticmethod
    def can_manage_organization(current_user: TokenData) -> bool:
        """Check if user can manage organization settings"""
        if PermissionChecker.is_system_admin(current_user):
            return True
        org_role = PermissionChecker.get_user_org_role(current_user.user_id)
        return org_role == OrgRole.ORG_ADMIN

    @staticmethod
    def can_manage_org_members(current_user: TokenData) -> bool:
        """Check if user can add/remove organization members"""
        if PermissionChecker.is_system_admin(current_user):
            return True
        org_role = PermissionChecker.get_user_org_role(current_user.user_id)
        return org_role == OrgRole.ORG_ADMIN

    @staticmethod
    def can_create_projects(current_user: TokenData) -> bool:
        """Check if user can create new projects"""
        if PermissionChecker.is_system_admin(current_user):
            return True
        org_role = PermissionChecker.get_user_org_role(current_user.user_id)
        return org_role in [OrgRole.ORG_ADMIN, OrgRole.MANAGER]

    @staticmethod
    def can_manage_project_members(current_user: TokenData, project_id: str) -> bool:
        """Check if user can add/remove project members"""
        if PermissionChecker.is_system_admin(current_user):
            return True

        org_role = PermissionChecker.get_user_org_role(current_user.user_id)
        if org_role == OrgRole.ORG_ADMIN:
            return True

        if org_role == OrgRole.MANAGER:
            return True

        project_role = PermissionChecker.get_user_project_role(current_user.user_id, project_id)
        return project_role == ProjectRole.OWNER

    @staticmethod
    def can_access_project(current_user: TokenData, project_id: str) -> bool:
        """Check if user can access a project (view)"""
        if PermissionChecker.is_system_admin(current_user):
            return True

        org_role = PermissionChecker.get_user_org_role(current_user.user_id)
        if org_role == OrgRole.ORG_ADMIN:
            return True  # Org admins can access all projects in their org

        project_role = PermissionChecker.get_user_project_role(current_user.user_id, project_id)
        return project_role is not None

    @staticmethod
    def can_edit_project(current_user: TokenData, project_id: str) -> bool:
        """Check if user can edit a project (modify test cases, run tests)"""
        if PermissionChecker.is_system_admin(current_user):
            return True

        org_role = PermissionChecker.get_user_org_role(current_user.user_id)
        if org_role == OrgRole.ORG_ADMIN:
            return True

        project_role = PermissionChecker.get_user_project_role(current_user.user_id, project_id)
        return project_role in [ProjectRole.OWNER, ProjectRole.EDITOR]

    @staticmethod
    def can_delete_project(current_user: TokenData, project_id: str) -> bool:
        """Check if user can delete a project"""
        if PermissionChecker.is_system_admin(current_user):
            return True

        org_role = PermissionChecker.get_user_org_role(current_user.user_id)
        if org_role == OrgRole.ORG_ADMIN:
            return True

        project_role = PermissionChecker.get_user_project_role(current_user.user_id, project_id)
        return project_role == ProjectRole.OWNER

    @staticmethod
    def can_run_tests(current_user: TokenData, project_id: str) -> bool:
        """Check if user can run tests on a project"""
        return PermissionChecker.can_edit_project(current_user, project_id)

    @staticmethod
    def can_view_reports(current_user: TokenData, project_id: str) -> bool:
        """Check if user can view reports for a project"""
        return PermissionChecker.can_access_project(current_user, project_id)

    # ============ Exception Raisers ============

    @staticmethod
    def require_system_admin(current_user: TokenData):
        """Raise exception if not system admin"""
        if not PermissionChecker.is_system_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System admin access required"
            )

    @staticmethod
    def require_org_admin(current_user: TokenData):
        """Raise exception if not org admin"""
        if not PermissionChecker.can_manage_organization(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization admin access required"
            )

    @staticmethod
    def require_org_manager(current_user: TokenData):
        """Raise exception if not org admin or manager"""
        if not PermissionChecker.can_create_projects(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization admin or manager access required"
            )

    @staticmethod
    def require_project_access(current_user: TokenData, project_id: str):
        """Raise exception if no project access"""
        if not PermissionChecker.can_access_project(current_user, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project access denied"
            )

    @staticmethod
    def require_project_edit(current_user: TokenData, project_id: str):
        """Raise exception if can't edit project"""
        if not PermissionChecker.can_edit_project(current_user, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project edit access denied"
            )

    @staticmethod
    def require_project_delete(current_user: TokenData, project_id: str):
        """Raise exception if can't delete project"""
        if not PermissionChecker.can_delete_project(current_user, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project delete access denied"
            )

    @staticmethod
    def require_project_member_management(current_user: TokenData, project_id: str):
        """Raise exception if can't manage project members"""
        if not PermissionChecker.can_manage_project_members(current_user, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot manage project members"
            )


# Convenience function for common permission check
def check_project_access(current_user: TokenData, project_id: str, require_edit: bool = False):
    """
    Convenience function to check project access and raise appropriate exception

    Args:
        current_user: The authenticated user's token data
        project_id: The project to check access for
        require_edit: If True, requires edit access; otherwise just view access
    """
    if require_edit:
        PermissionChecker.require_project_edit(current_user, project_id)
    else:
        PermissionChecker.require_project_access(current_user, project_id)
