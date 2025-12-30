"""
Authentication Storage for GhostQA
File-based storage for users
"""
import json
import os
from typing import List, Optional
from datetime import datetime
from auth_models import User, UserRole
import bcrypt


class AuthStorage:
    """File-based storage for users"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.users_dir = os.path.join(data_dir, "users")
        self._ensure_directories()
        self._ensure_default_admin()
        self._run_migration_if_needed()

    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        os.makedirs(self.users_dir, exist_ok=True)

    def _ensure_default_admin(self):
        """Create default admin user if no users exist"""
        users = self.get_all_users()
        if not users:
            import secrets
            import string

            # Generate secure random password
            alphabet = string.ascii_letters + string.digits + "!@#$%"
            admin_password = ''.join(secrets.choice(alphabet) for _ in range(16))

            # Create default admin
            default_admin = User(
                username="admin",
                email="admin@ghostqa.local",
                password_hash=self.hash_password(admin_password),
                role=UserRole.ADMIN,
                must_change_password=True  # Force password change on first login
            )
            self.save_user(default_admin)

            # Save credentials to a secure file (admin should delete after first login)
            creds_file = os.path.join(self.data_dir, "ADMIN_CREDENTIALS.txt")
            with open(creds_file, 'w') as f:
                f.write("=== GhostQA Default Admin Credentials ===\n")
                f.write(f"Username: admin\n")
                f.write(f"Password: {admin_password}\n")
                f.write("\nIMPORTANT: Delete this file after first login!\n")
                f.write("You will be required to change this password on first login.\n")

            print(f"[AUTH] Created default admin user")
            print(f"[AUTH] Credentials saved to: {creds_file}")
            print(f"[AUTH] DELETE THIS FILE AFTER FIRST LOGIN!")


    def _run_migration_if_needed(self):
        """Check if organization migration is needed and run it"""
        migration_marker = os.path.join(self.data_dir, ".org_migration_complete")

        if os.path.exists(migration_marker):
            return  # Already migrated

        # Check if we have any users but no organizations
        users = self.get_all_users()
        orgs_dir = os.path.join(self.data_dir, "organizations")
        has_orgs = os.path.exists(orgs_dir) and any(
            f.endswith('.json') for f in os.listdir(orgs_dir) if os.path.isfile(os.path.join(orgs_dir, f))
        )

        if users and not has_orgs:
            print("[MIGRATION] Running organization migration...")
            try:
                from migrations.migrate_to_organizations import run_migration
                run_migration(self.data_dir)

                # Create marker file
                with open(migration_marker, 'w') as f:
                    f.write(datetime.now().isoformat())

                print("[MIGRATION] Complete!")
            except Exception as e:
                print(f"[MIGRATION] Error: {e}")
        elif not users:
            # No users yet, create marker to skip migration
            with open(migration_marker, 'w') as f:
                f.write(datetime.now().isoformat())

    def _get_user_file(self, user_id: str) -> str:
        """Get user file path"""
        return os.path.join(self.users_dir, f"{user_id}.json")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False

    def save_user(self, user: User):
        """Save user to file"""
        user.updated_at = datetime.now()
        file_path = self._get_user_file(user.id)
        with open(file_path, 'w') as f:
            json.dump(user.model_dump(mode='json'), f, indent=2, default=str)

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        file_path = self._get_user_file(user_id)
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r') as f:
            data = json.load(f)
            return User(**data)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                user_id = filename[:-5]
                user = self.get_user(user_id)
                if user and user.username.lower() == username.lower():
                    return user
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                user_id = filename[:-5]
                user = self.get_user(user_id)
                if user and user.email.lower() == email.lower():
                    return user
        return None

    def get_all_users(self) -> List[User]:
        """Get all users"""
        users = []
        if not os.path.exists(self.users_dir):
            return users
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                user_id = filename[:-5]
                user = self.get_user(user_id)
                if user:
                    users.append(user)
        return sorted(users, key=lambda u: u.created_at, reverse=True)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        file_path = self._get_user_file(user_id)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user = self.get_user_by_username(username)
        if user and user.is_active and self.verify_password(password, user.password_hash):
            return user
        return None


# Singleton instance
_auth_storage = None


def get_auth_storage() -> AuthStorage:
    """Get the auth storage singleton"""
    global _auth_storage
    if _auth_storage is None:
        _auth_storage = AuthStorage()
    return _auth_storage
