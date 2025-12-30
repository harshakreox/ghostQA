"""
Migration script to add organization support to GhostQA
Creates default organization and migrates existing data
"""
import json
import os
from datetime import datetime
import uuid
import re


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = text.strip('-')
    return text or 'default'


def run_migration(data_dir: str = "data"):
    """
    Migrate existing data to organization-based structure
    """
    print("=" * 60)
    print("GhostQA Organization Migration")
    print("=" * 60)

    # Step 1: Create default organization
    default_org = create_default_organization(data_dir)
    print(f"[OK] Created default organization: {default_org['name']} (id: {default_org['id'][:8]}...)")

    # Step 2: Migrate users - add organization_id
    users_migrated = migrate_users(data_dir, default_org['id'])
    print(f"[OK] Migrated {users_migrated} users to organization")

    # Step 3: Create org memberships
    memberships_created = create_org_memberships(data_dir, default_org['id'])
    print(f"[OK] Created {memberships_created} organization memberships")

    # Step 4: Migrate projects - add organization_id
    projects_migrated = migrate_projects(data_dir, default_org['id'])
    print(f"[OK] Migrated {projects_migrated} projects to organization")

    # Step 5: Create project memberships for owners
    project_memberships = create_project_memberships(data_dir)
    print(f"[OK] Created {project_memberships} project memberships for owners")

    # Step 6: Add creator_id fields to features
    features_updated = update_features(data_dir)
    print(f"[OK] Updated {features_updated} gherkin features with creator fields")

    # Step 7: Add creator_id fields to traditional suites
    suites_updated = update_traditional_suites(data_dir)
    print(f"[OK] Updated {suites_updated} traditional suites with creator fields")

    # Step 8: Update test cases in projects with creator fields
    test_cases_updated = update_project_test_cases(data_dir)
    print(f"[OK] Updated {test_cases_updated} action-based test cases with creator fields")

    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)


def create_default_organization(data_dir: str) -> dict:
    """Create the default organization"""
    orgs_dir = os.path.join(data_dir, "organizations")
    os.makedirs(orgs_dir, exist_ok=True)

    # Check if default org already exists
    for filename in os.listdir(orgs_dir) if os.path.exists(orgs_dir) else []:
        if filename.endswith('.json'):
            with open(os.path.join(orgs_dir, filename), 'r') as f:
                org = json.load(f)
                if org.get('slug') == 'default':
                    print("  [INFO] Default organization already exists")
                    return org

    # Create default organization
    org_id = str(uuid.uuid4())
    org = {
        "id": org_id,
        "name": "Default Organization",
        "slug": "default",
        "description": "Auto-generated default organization during migration",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "is_active": True,
        "max_users": None,
        "max_projects": None
    }

    with open(os.path.join(orgs_dir, f"{org_id}.json"), 'w') as f:
        json.dump(org, f, indent=2)

    return org


def migrate_users(data_dir: str, org_id: str) -> int:
    """Add organization_id to existing users"""
    users_dir = os.path.join(data_dir, "users")
    count = 0

    if not os.path.exists(users_dir):
        return 0

    for filename in os.listdir(users_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(users_dir, filename)
        with open(file_path, 'r') as f:
            user = json.load(f)

        # Skip if already has organization_id
        if user.get('organization_id'):
            continue

        # Add organization_id
        user['organization_id'] = org_id
        user['updated_at'] = datetime.now().isoformat()

        with open(file_path, 'w') as f:
            json.dump(user, f, indent=2)

        count += 1

    return count


def create_org_memberships(data_dir: str, org_id: str) -> int:
    """Create organization memberships for all users"""
    users_dir = os.path.join(data_dir, "users")
    members_dir = os.path.join(data_dir, "org_members")
    os.makedirs(members_dir, exist_ok=True)

    count = 0

    if not os.path.exists(users_dir):
        return 0

    # Get existing memberships to avoid duplicates
    existing_user_ids = set()
    for filename in os.listdir(members_dir) if os.path.exists(members_dir) else []:
        if filename.endswith('.json'):
            with open(os.path.join(members_dir, filename), 'r') as f:
                m = json.load(f)
                if m.get('organization_id') == org_id:
                    existing_user_ids.add(m.get('user_id'))

    for filename in os.listdir(users_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(users_dir, filename)
        with open(file_path, 'r') as f:
            user = json.load(f)

        user_id = user['id']

        # Skip if membership already exists
        if user_id in existing_user_ids:
            continue

        # Determine org role based on existing system role
        # System admins become org_admin, others become members
        org_role = "org_admin" if user.get('role') == 'admin' else "member"

        membership_id = str(uuid.uuid4())
        membership = {
            "id": membership_id,
            "organization_id": org_id,
            "user_id": user_id,
            "org_role": org_role,
            "joined_at": datetime.now().isoformat(),
            "invited_by": None
        }

        with open(os.path.join(members_dir, f"{membership_id}.json"), 'w') as f:
            json.dump(membership, f, indent=2)

        count += 1

    return count


def migrate_projects(data_dir: str, org_id: str) -> int:
    """Add organization_id to existing projects"""
    projects_dir = os.path.join(data_dir, "projects")
    count = 0

    if not os.path.exists(projects_dir):
        return 0

    for filename in os.listdir(projects_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(projects_dir, filename)
        with open(file_path, 'r') as f:
            project = json.load(f)

        # Skip if already has organization_id
        if project.get('organization_id'):
            continue

        # Add organization_id
        project['organization_id'] = org_id
        project['updated_at'] = datetime.now().isoformat()

        with open(file_path, 'w') as f:
            json.dump(project, f, indent=2)

        count += 1

    return count


def create_project_memberships(data_dir: str) -> int:
    """Create project memberships for project owners"""
    projects_dir = os.path.join(data_dir, "projects")
    members_dir = os.path.join(data_dir, "project_members")
    os.makedirs(members_dir, exist_ok=True)

    count = 0

    if not os.path.exists(projects_dir):
        return 0

    # Get existing memberships to avoid duplicates
    existing_memberships = set()
    for filename in os.listdir(members_dir) if os.path.exists(members_dir) else []:
        if filename.endswith('.json'):
            with open(os.path.join(members_dir, filename), 'r') as f:
                m = json.load(f)
                existing_memberships.add((m.get('project_id'), m.get('user_id')))

    for filename in os.listdir(projects_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(projects_dir, filename)
        with open(file_path, 'r') as f:
            project = json.load(f)

        project_id = project['id']
        owner_id = project.get('owner_id')

        if not owner_id:
            continue

        # Skip if membership already exists
        if (project_id, owner_id) in existing_memberships:
            continue

        membership_id = str(uuid.uuid4())
        membership = {
            "id": membership_id,
            "project_id": project_id,
            "user_id": owner_id,
            "project_role": "owner",
            "assigned_at": datetime.now().isoformat(),
            "assigned_by": None
        }

        with open(os.path.join(members_dir, f"{membership_id}.json"), 'w') as f:
            json.dump(membership, f, indent=2)

        count += 1

    return count


def update_features(data_dir: str) -> int:
    """Add creator_id fields to existing gherkin features"""
    features_dir = os.path.join(data_dir, "features")
    count = 0

    if not os.path.exists(features_dir):
        return 0

    for filename in os.listdir(features_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(features_dir, filename)
        with open(file_path, 'r') as f:
            feature = json.load(f)

        # Skip if already has creator_id field
        if 'creator_id' in feature:
            continue

        # Set creator fields to None (unknown for migrated data)
        feature['creator_id'] = None
        feature['creator_username'] = None
        feature['last_modified_by'] = None
        feature['updated_at'] = datetime.now().isoformat()

        with open(file_path, 'w') as f:
            json.dump(feature, f, indent=2)

        count += 1

    return count


def update_traditional_suites(data_dir: str) -> int:
    """Add creator_id fields to existing traditional test suites"""
    suites_dir = os.path.join(data_dir, "traditional")
    count = 0

    if not os.path.exists(suites_dir):
        return 0

    for filename in os.listdir(suites_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(suites_dir, filename)
        with open(file_path, 'r') as f:
            suite = json.load(f)

        # Skip if already has creator_id field
        if 'creator_id' in suite:
            continue

        # Set creator fields to None (unknown for migrated data)
        suite['creator_id'] = None
        suite['creator_username'] = None
        suite['last_modified_by'] = None
        suite['updated_at'] = datetime.now().isoformat()

        with open(file_path, 'w') as f:
            json.dump(suite, f, indent=2)

        count += 1

    return count


def update_project_test_cases(data_dir: str) -> int:
    """Add creator_id fields to action-based test cases in projects"""
    projects_dir = os.path.join(data_dir, "projects")
    count = 0

    if not os.path.exists(projects_dir):
        return 0

    for filename in os.listdir(projects_dir):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(projects_dir, filename)
        with open(file_path, 'r') as f:
            project = json.load(f)

        test_cases = project.get('test_cases', [])
        if not test_cases:
            continue

        updated = False
        for tc in test_cases:
            if 'creator_id' not in tc:
                tc['creator_id'] = None
                tc['creator_username'] = None
                tc['last_modified_by'] = None
                count += 1
                updated = True

        if updated:
            project['updated_at'] = datetime.now().isoformat()
            with open(file_path, 'w') as f:
                json.dump(project, f, indent=2)

    return count


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    run_migration(data_dir)
