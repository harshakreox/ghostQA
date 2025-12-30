"""
Organization Storage for GhostQA
File-based storage for organizations and memberships
"""
import json
import os
from typing import List, Optional
from datetime import datetime

from org_models import (
    Organization, OrganizationMember, ProjectMember, OrganizationInvite,
    OrgRole, ProjectRole
)


class OrgStorage:
    """File-based storage for organizations and memberships"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.orgs_dir = os.path.join(data_dir, "organizations")
        self.org_members_dir = os.path.join(data_dir, "org_members")
        self.project_members_dir = os.path.join(data_dir, "project_members")
        self.invites_dir = os.path.join(data_dir, "org_invites")
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        os.makedirs(self.orgs_dir, exist_ok=True)
        os.makedirs(self.org_members_dir, exist_ok=True)
        os.makedirs(self.project_members_dir, exist_ok=True)
        os.makedirs(self.invites_dir, exist_ok=True)

    # ============ Organization CRUD ============

    def save_organization(self, org: Organization) -> None:
        """Save organization to file"""
        org.updated_at = datetime.now()
        file_path = os.path.join(self.orgs_dir, f"{org.id}.json")
        with open(file_path, 'w') as f:
            json.dump(org.model_dump(mode='json'), f, indent=2, default=str)

    def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        file_path = os.path.join(self.orgs_dir, f"{org_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r') as f:
            data = json.load(f)
            return Organization(**data)

    def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug"""
        for filename in os.listdir(self.orgs_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.orgs_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('slug') == slug:
                    return Organization(**data)
        return None

    def get_all_organizations(self) -> List[Organization]:
        """Get all organizations"""
        organizations = []
        if not os.path.exists(self.orgs_dir):
            return organizations
        for filename in os.listdir(self.orgs_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.orgs_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                organizations.append(Organization(**data))
        return sorted(organizations, key=lambda x: x.created_at, reverse=True)

    def delete_organization(self, org_id: str) -> bool:
        """Delete organization"""
        file_path = os.path.join(self.orgs_dir, f"{org_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    # ============ Organization Members CRUD ============

    def add_org_member(self, member: OrganizationMember) -> None:
        """Add user to organization"""
        file_path = os.path.join(self.org_members_dir, f"{member.id}.json")
        with open(file_path, 'w') as f:
            json.dump(member.model_dump(mode='json'), f, indent=2, default=str)

    def get_org_member(self, org_id: str, user_id: str) -> Optional[OrganizationMember]:
        """Get specific org membership"""
        for filename in os.listdir(self.org_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.org_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('organization_id') == org_id and data.get('user_id') == user_id:
                    return OrganizationMember(**data)
        return None

    def get_org_members(self, org_id: str) -> List[OrganizationMember]:
        """Get all members of an organization"""
        members = []
        if not os.path.exists(self.org_members_dir):
            return members
        for filename in os.listdir(self.org_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.org_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('organization_id') == org_id:
                    members.append(OrganizationMember(**data))
        return sorted(members, key=lambda x: x.joined_at, reverse=True)

    def get_user_org_membership(self, user_id: str) -> Optional[OrganizationMember]:
        """Get user's organization membership (single org per user)"""
        if not os.path.exists(self.org_members_dir):
            return None
        for filename in os.listdir(self.org_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.org_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('user_id') == user_id:
                    return OrganizationMember(**data)
        return None

    def update_org_member_role(self, org_id: str, user_id: str, role: OrgRole) -> bool:
        """Update member's organization role"""
        if not os.path.exists(self.org_members_dir):
            return False
        for filename in os.listdir(self.org_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.org_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
            if data.get('organization_id') == org_id and data.get('user_id') == user_id:
                data['org_role'] = role.value
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                return True
        return False

    def remove_org_member(self, org_id: str, user_id: str) -> bool:
        """Remove user from organization"""
        if not os.path.exists(self.org_members_dir):
            return False
        for filename in os.listdir(self.org_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.org_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
            if data.get('organization_id') == org_id and data.get('user_id') == user_id:
                os.remove(file_path)
                return True
        return False

    # ============ Project Members CRUD ============

    def add_project_member(self, member: ProjectMember) -> None:
        """Add user to project"""
        file_path = os.path.join(self.project_members_dir, f"{member.id}.json")
        with open(file_path, 'w') as f:
            json.dump(member.model_dump(mode='json'), f, indent=2, default=str)

    def get_project_member(self, project_id: str, user_id: str) -> Optional[ProjectMember]:
        """Get specific project membership"""
        if not os.path.exists(self.project_members_dir):
            return None
        for filename in os.listdir(self.project_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.project_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('project_id') == project_id and data.get('user_id') == user_id:
                    return ProjectMember(**data)
        return None

    def get_project_members(self, project_id: str) -> List[ProjectMember]:
        """Get all members of a project"""
        members = []
        if not os.path.exists(self.project_members_dir):
            return members
        for filename in os.listdir(self.project_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.project_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('project_id') == project_id:
                    members.append(ProjectMember(**data))
        return sorted(members, key=lambda x: x.assigned_at, reverse=True)

    def get_user_project_memberships(self, user_id: str) -> List[ProjectMember]:
        """Get all project memberships for a user"""
        memberships = []
        if not os.path.exists(self.project_members_dir):
            return memberships
        for filename in os.listdir(self.project_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.project_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('user_id') == user_id:
                    memberships.append(ProjectMember(**data))
        return memberships

    def update_project_member_role(self, project_id: str, user_id: str, role: ProjectRole) -> bool:
        """Update member's project role"""
        if not os.path.exists(self.project_members_dir):
            return False
        for filename in os.listdir(self.project_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.project_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
            if data.get('project_id') == project_id and data.get('user_id') == user_id:
                data['project_role'] = role.value
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                return True
        return False

    def remove_project_member(self, project_id: str, user_id: str) -> bool:
        """Remove user from project"""
        if not os.path.exists(self.project_members_dir):
            return False
        for filename in os.listdir(self.project_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.project_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
            if data.get('project_id') == project_id and data.get('user_id') == user_id:
                os.remove(file_path)
                return True
        return False

    def remove_all_project_members(self, project_id: str) -> int:
        """Remove all members from a project (used when deleting project)"""
        count = 0
        if not os.path.exists(self.project_members_dir):
            return count
        for filename in os.listdir(self.project_members_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.project_members_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
            if data.get('project_id') == project_id:
                os.remove(file_path)
                count += 1
        return count

    # ============ Utility Methods ============

    def get_org_member_count(self, org_id: str) -> int:
        """Get count of members in an organization"""
        return len(self.get_org_members(org_id))

    def get_project_member_count(self, project_id: str) -> int:
        """Get count of members in a project"""
        return len(self.get_project_members(project_id))

    def get_user_accessible_project_ids(self, user_id: str) -> List[str]:
        """Get list of project IDs user has access to"""
        memberships = self.get_user_project_memberships(user_id)
        return [m.project_id for m in memberships]



    # ============ Organization Invites CRUD ============

    def save_invite(self, invite: OrganizationInvite) -> None:
        """Save invite to file"""
        file_path = os.path.join(self.invites_dir, f"{invite.id}.json")
        with open(file_path, 'w') as f:
            json.dump(invite.model_dump(mode='json'), f, indent=2, default=str)

    def get_invite(self, invite_id: str) -> Optional[OrganizationInvite]:
        """Get invite by ID"""
        file_path = os.path.join(self.invites_dir, f"{invite_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r') as f:
            data = json.load(f)
            return OrganizationInvite(**data)

    def get_invite_by_token(self, token: str) -> Optional[OrganizationInvite]:
        """Get invite by token"""
        if not os.path.exists(self.invites_dir):
            return None
        for filename in os.listdir(self.invites_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.invites_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('token') == token:
                    return OrganizationInvite(**data)
        return None

    def get_org_invites(self, org_id: str) -> List[OrganizationInvite]:
        """Get all invites for an organization"""
        invites = []
        if not os.path.exists(self.invites_dir):
            return invites
        for filename in os.listdir(self.invites_dir):
            if not filename.endswith('.json'):
                continue
            file_path = os.path.join(self.invites_dir, filename)
            with open(file_path, 'r') as f:
                data = json.load(f)
                if data.get('organization_id') == org_id:
                    invites.append(OrganizationInvite(**data))
        return sorted(invites, key=lambda x: x.created_at, reverse=True)

    def delete_invite(self, invite_id: str) -> bool:
        """Delete an invite"""
        file_path = os.path.join(self.invites_dir, f"{invite_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def increment_invite_use(self, invite_id: str) -> bool:
        """Increment the use count of an invite"""
        invite = self.get_invite(invite_id)
        if not invite:
            return False
        invite.use_count += 1
        if invite.use_count >= invite.max_uses:
            invite.is_active = False
        self.save_invite(invite)
        return True


# Singleton instance
_org_storage = None


def get_org_storage() -> OrgStorage:
    """Get singleton OrgStorage instance"""
    global _org_storage
    if _org_storage is None:
        _org_storage = OrgStorage()
    return _org_storage
