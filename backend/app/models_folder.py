"""
Folder Model for organizing Gherkin features and test cases
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
from datetime import datetime


class FolderCategory(str, Enum):
    """Category types for folders"""
    ACTION_BASED = "action-based"
    GHERKIN = "gherkin"
    TRADITIONAL = "traditional"


class Folder(BaseModel):
    """Folder for organizing features/test cases within a project"""
    id: str
    name: str
    project_id: str  # Required - folder belongs to a project
    category: FolderCategory  # Category type (action-based, gherkin, traditional)
    parent_folder_id: Optional[str] = None  # For nested folders
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CreateFolderRequest(BaseModel):
    """Request to create a new folder"""
    name: str
    category: Optional[str] = None  # action-based, gherkin, or traditional
    parent_folder_id: Optional[str] = None


class UpdateFolderRequest(BaseModel):
    """Request to update a folder"""
    name: Optional[str] = None
    parent_folder_id: Optional[str] = None  # Move folder to different parent


class MoveFolderRequest(BaseModel):
    """Request to move a folder to a different parent"""
    parent_folder_id: Optional[str] = None  # None means move to root


class MoveFeatureToFolderRequest(BaseModel):
    """Request to move a feature to a folder"""
    folder_id: Optional[str] = None  # None means move to root


class BulkMoveFeaturesToFolderRequest(BaseModel):
    """Request to move multiple features to a folder"""
    feature_ids: list[str]
    folder_id: Optional[str] = None  # None means move to root
