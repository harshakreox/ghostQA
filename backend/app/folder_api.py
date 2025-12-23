"""
Folder API Routes - for organizing features into folders
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from storage import Storage
from gherkin_storage import get_gherkin_storage
from folder_storage import get_folder_storage
from models_folder import (
    CreateFolderRequest, UpdateFolderRequest,
    MoveFeatureToFolderRequest, BulkMoveFeaturesToFolderRequest
)
from auth_api import get_current_user
from auth_models import TokenData, UserRole

router = APIRouter(prefix="/api", tags=["folders"])

storage = Storage()
gherkin_storage = get_gherkin_storage()
folder_storage = get_folder_storage()


@router.post("/projects/{project_id}/folders")
async def create_folder(
    project_id: str,
    request: CreateFolderRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new folder within a project"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if request.parent_folder_id:
        parent = folder_storage.load_folder(request.parent_folder_id)
        if not parent or parent.project_id != project_id:
            raise HTTPException(status_code=400, detail="Invalid parent folder")

    # Default to gherkin category if not specified
    category = request.category or "gherkin"

    folder_dict = folder_storage.create_folder(
        name=request.name,
        project_id=project_id,
        category=category,
        parent_folder_id=request.parent_folder_id
    )
    return folder_dict


@router.get("/projects/{project_id}/folders")
async def get_project_folders(
    project_id: str,
    category: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all folders for a project (flat list), optionally filtered by category"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    folders = folder_storage.list_folders(project_id, category)
    return {"folders": folders}


@router.get("/projects/{project_id}/folders/tree")
async def get_project_folder_tree(
    project_id: str,
    category: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Get folders as a nested tree structure, optionally filtered by category"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    tree = folder_storage.get_folder_tree(project_id, category)
    return {"tree": tree}


@router.get("/folders/{folder_id}")
async def get_folder(
    folder_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific folder"""
    folder = folder_storage.load_folder_dict(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    project = storage.get_project(folder["project_id"])
    if project and current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return folder


@router.get("/folders/{folder_id}/path")
async def get_folder_path(
    folder_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get the full path (breadcrumbs) from root to this folder"""
    folder = folder_storage.load_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    path = folder_storage.get_folder_path(folder_id)
    return {"path": path}


@router.put("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    request: UpdateFolderRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Update a folder (rename or move)"""
    folder = folder_storage.load_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    project = storage.get_project(folder.project_id)
    if project and current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        updated = folder_storage.update_folder(
            folder_id=folder_id,
            name=request.name,
            parent_folder_id=request.parent_folder_id
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    move_children_to_parent: bool = True,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a folder. Children can be moved to parent or deleted recursively."""
    folder = folder_storage.load_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    project = storage.get_project(folder.project_id)
    if project and current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Move features in this folder to root (or parent)
    features = gherkin_storage.list_features_by_folder(folder.project_id, folder_id)
    for feature in features:
        gherkin_storage.update_feature_folder(feature["id"], folder.parent_folder_id)

    folder_storage.delete_folder(folder_id, move_children_to_parent)
    return {"message": "Folder deleted successfully", "features_moved": len(features)}


@router.put("/gherkin/features/{feature_id}/move")
async def move_feature_to_folder(
    feature_id: str,
    request: MoveFeatureToFolderRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Move a feature to a folder (or to root if folder_id is None)"""
    feature_dict = gherkin_storage.load_feature_dict(feature_id)
    if not feature_dict:
        raise HTTPException(status_code=404, detail="Feature not found")

    if request.folder_id:
        folder = folder_storage.load_folder(request.folder_id)
        if not folder:
            raise HTTPException(status_code=400, detail="Folder not found")

        if feature_dict.get("project_id") and folder.project_id != feature_dict["project_id"]:
            raise HTTPException(status_code=400, detail="Folder belongs to different project")

    updated = gherkin_storage.update_feature_folder(feature_id, request.folder_id)
    return updated


@router.put("/gherkin/features/bulk-move")
async def bulk_move_features_to_folder(
    request: BulkMoveFeaturesToFolderRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Move multiple features to a folder"""
    if request.folder_id:
        folder = folder_storage.load_folder(request.folder_id)
        if not folder:
            raise HTTPException(status_code=400, detail="Folder not found")

    moved = []
    failed = []

    for feature_id in request.feature_ids:
        try:
            updated = gherkin_storage.update_feature_folder(feature_id, request.folder_id)
            if updated:
                moved.append(feature_id)
            else:
                failed.append({"id": feature_id, "error": "Feature not found"})
        except Exception as e:
            failed.append({"id": feature_id, "error": str(e)})

    return {
        "moved": moved,
        "failed": failed,
        "message": f"Moved {len(moved)} features, {len(failed)} failed"
    }


@router.get("/projects/{project_id}/folders/{folder_id}/features")
async def get_folder_features(
    project_id: str,
    folder_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all features in a specific folder"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # folder_id of "root" means features with no folder
    actual_folder_id = None if folder_id == "root" else folder_id

    features = gherkin_storage.list_features_by_folder(project_id, actual_folder_id)
    return {"features": features}


@router.get("/projects/{project_id}/features-with-folders")
async def get_project_features_with_folders(
    project_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all features for a project organized by folders"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    folder_tree = folder_storage.get_folder_tree(project_id)
    all_features = gherkin_storage.list_features(project_id=project_id)

    features_by_folder = {}
    root_features = []

    for feature in all_features:
        folder_id = feature.get("folder_id")
        if folder_id:
            if folder_id not in features_by_folder:
                features_by_folder[folder_id] = []
            features_by_folder[folder_id].append(feature)
        else:
            root_features.append(feature)

    return {
        "folder_tree": folder_tree,
        "features_by_folder": features_by_folder,
        "root_features": root_features,
        "total_features": len(all_features),
        "total_folders": len(folder_storage.list_folders(project_id))
    }
