"""
Permission checking utilities for GhostQA
Simplified: No organizations - just users and admins
"""
from typing import Optional
from fastapi import HTTPException, status
from auth_models import TokenData, UserRole


class PermissionChecker:
    """Simplified permission checking - no organizations"""

    @staticmethod
    def is_system_admin(current_user: TokenData) -> bool:
        """Check if user is an admin"""
        return current_user.role == UserRole.ADMIN

    @staticmethod
    def can_access_project(current_user: TokenData, project_id: str) -> bool:
        """All authenticated users can access all projects"""
        return True  # Any authenticated user can access

    @staticmethod
    def can_edit_project(current_user: TokenData, project_id: str) -> bool:
        """All authenticated users can edit all projects"""
        return True  # Any authenticated user can edit

    @staticmethod
    def can_delete_project(current_user: TokenData, project_id: str) -> bool:
        """Only admins can delete projects"""
        return PermissionChecker.is_system_admin(current_user)

    @staticmethod
    def can_create_projects(current_user: TokenData) -> bool:
        """All authenticated users can create projects"""
        return True

    @staticmethod
    def can_run_tests(current_user: TokenData, project_id: str) -> bool:
        """All authenticated users can run tests"""
        return True

    @staticmethod
    def can_view_reports(current_user: TokenData, project_id: str) -> bool:
        """All authenticated users can view reports"""
        return True

    # ============ Exception Raisers ============

    @staticmethod
    def require_system_admin(current_user: TokenData):
        """Raise exception if not admin"""
        if not PermissionChecker.is_system_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

    @staticmethod
    def require_org_admin(current_user: TokenData):
        """For backward compatibility - just checks admin"""
        PermissionChecker.require_system_admin(current_user)

    @staticmethod
    def require_org_manager(current_user: TokenData):
        """For backward compatibility - allows all authenticated users"""
        pass  # All authenticated users allowed

    @staticmethod
    def require_project_access(current_user: TokenData, project_id: str):
        """All authenticated users have access"""
        pass  # All authenticated users allowed

    @staticmethod
    def require_project_edit(current_user: TokenData, project_id: str):
        """All authenticated users can edit"""
        pass  # All authenticated users allowed

    @staticmethod
    def require_project_delete(current_user: TokenData, project_id: str):
        """Only admins can delete"""
        if not PermissionChecker.can_delete_project(current_user, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required to delete projects"
            )

    @staticmethod
    def require_project_member_management(current_user: TokenData, project_id: str):
        """For backward compatibility - allows admins"""
        PermissionChecker.require_system_admin(current_user)


def check_project_access(current_user: TokenData, project_id: str, require_edit: bool = False):
    """All authenticated users have full access"""
    pass  # All authenticated users allowed
