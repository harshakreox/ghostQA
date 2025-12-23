"""
Folder Storage - Handle folder CRUD operations
"""

import json
import os
from typing import List, Optional
from datetime import datetime
import uuid

from models_folder import Folder


class FolderStorage:
    """Handle Folder storage in JSON files"""

    def __init__(self, data_folder: str = "data"):
        self.folders_folder = os.path.join(data_folder, "folders")

        # Create folder if it doesn't exist
        os.makedirs(self.folders_folder, exist_ok=True)

    def save_folder(self, folder: Folder) -> dict:
        """Save a folder to JSON"""

        folder_dict = {
            "id": folder.id,
            "name": folder.name,
            "project_id": folder.project_id,
            "category": folder.category.value if hasattr(folder.category, 'value') else folder.category,
            "parent_folder_id": folder.parent_folder_id,
            "created_at": folder.created_at.isoformat() if hasattr(folder.created_at, 'isoformat') else str(folder.created_at),
            "updated_at": datetime.now().isoformat()
        }

        # Save to file
        file_path = os.path.join(self.folders_folder, f"{folder.id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(folder_dict, f, indent=2, ensure_ascii=False)

        return folder_dict

    def load_folder(self, folder_id: str) -> Optional[Folder]:
        """Load a folder from JSON"""

        file_path = os.path.join(self.folders_folder, f"{folder_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        folder = Folder(
            id=data["id"],
            name=data["name"],
            project_id=data["project_id"],
            category=data.get("category", "gherkin"),
            parent_folder_id=data.get("parent_folder_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

        return folder

    def load_folder_dict(self, folder_id: str) -> Optional[dict]:
        """Load folder as dictionary"""
        file_path = os.path.join(self.folders_folder, f"{folder_id}.json")

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def list_folders(self, project_id: str, category: str = None) -> List[dict]:
        """List all folders for a project, optionally filtered by category"""
        folders = []

        if not os.path.exists(self.folders_folder):
            return folders

        for filename in os.listdir(self.folders_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(self.folders_folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    folder_data = json.load(f)

                    if folder_data.get("project_id") == project_id:
                        # Filter by category if specified (default to gherkin for backwards compatibility)
                        folder_category = folder_data.get("category", "gherkin")
                        if category is None or folder_category == category:
                            # Add category to output if missing
                            if "category" not in folder_data:
                                folder_data["category"] = folder_category
                            folders.append(folder_data)

        # Sort by name
        folders.sort(key=lambda x: x.get("name", "").lower())
        return folders

    def get_folder_tree(self, project_id: str, category: str = None) -> List[dict]:
        """Get folders as a nested tree structure, optionally filtered by category"""
        folders = self.list_folders(project_id, category)

        # Create lookup by id
        folder_map = {f["id"]: {**f, "children": []} for f in folders}

        # Build tree
        root_folders = []
        for folder in folders:
            folder_with_children = folder_map[folder["id"]]
            parent_id = folder.get("parent_folder_id")

            if parent_id and parent_id in folder_map:
                folder_map[parent_id]["children"].append(folder_with_children)
            else:
                root_folders.append(folder_with_children)

        return root_folders

    def update_folder(self, folder_id: str, name: str = None, parent_folder_id: str = None) -> Optional[dict]:
        """Update a folder's name or parent"""
        folder = self.load_folder(folder_id)

        if not folder:
            return None

        if name is not None:
            folder.name = name

        if parent_folder_id is not None:
            # Prevent circular references
            if parent_folder_id == folder_id:
                raise ValueError("A folder cannot be its own parent")

            # Check if new parent is a descendant of this folder
            if parent_folder_id and self._is_descendant(folder_id, parent_folder_id):
                raise ValueError("Cannot move folder to its own descendant")

            folder.parent_folder_id = parent_folder_id if parent_folder_id else None

        folder.updated_at = datetime.now()
        return self.save_folder(folder)

    def _is_descendant(self, ancestor_id: str, potential_descendant_id: str) -> bool:
        """Check if potential_descendant_id is a descendant of ancestor_id"""
        folder = self.load_folder(potential_descendant_id)

        while folder and folder.parent_folder_id:
            if folder.parent_folder_id == ancestor_id:
                return True
            folder = self.load_folder(folder.parent_folder_id)

        return False

    def delete_folder(self, folder_id: str, move_children_to_parent: bool = True) -> bool:
        """Delete a folder

        Args:
            folder_id: The folder to delete
            move_children_to_parent: If True, move children to deleted folder's parent.
                                     If False, delete all children recursively.
        """
        folder = self.load_folder(folder_id)

        if not folder:
            return False

        # Get all children folders
        all_folders = self.list_folders(folder.project_id)
        children = [f for f in all_folders if f.get("parent_folder_id") == folder_id]

        if move_children_to_parent:
            # Move children to deleted folder's parent
            for child in children:
                self.update_folder(child["id"], parent_folder_id=folder.parent_folder_id or "")
        else:
            # Delete children recursively
            for child in children:
                self.delete_folder(child["id"], move_children_to_parent=False)

        # Delete the folder file
        file_path = os.path.join(self.folders_folder, f"{folder_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True

        return False

    def create_folder(self, name: str, project_id: str, category: str = "gherkin", parent_folder_id: str = None) -> dict:
        """Create a new folder"""
        folder = Folder(
            id=str(uuid.uuid4()),
            name=name,
            project_id=project_id,
            category=category,
            parent_folder_id=parent_folder_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        return self.save_folder(folder)

    def get_folder_path(self, folder_id: str) -> List[dict]:
        """Get the full path from root to this folder (breadcrumbs)"""
        path = []
        current = self.load_folder(folder_id)

        while current:
            path.insert(0, {
                "id": current.id,
                "name": current.name
            })
            if current.parent_folder_id:
                current = self.load_folder(current.parent_folder_id)
            else:
                break

        return path


# Singleton
_folder_storage = None


def get_folder_storage(data_folder: str = "data") -> FolderStorage:
    """Get Folder storage instance"""
    global _folder_storage
    if _folder_storage is None:
        _folder_storage = FolderStorage(data_folder)
    return _folder_storage
