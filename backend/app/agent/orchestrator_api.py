"""
Autonomous Orchestrator API Endpoints
======================================
REST API for controlling the autonomous test orchestrator.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

from agent.autonomous_orchestrator import (
    get_orchestrator,
    start_autonomous_mode,
    stop_autonomous_mode,
    ExecutionPriority,
    OrchestratorConfig,
)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


class PriorityEnum(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


def _map_priority(priority: PriorityEnum) -> ExecutionPriority:
    """Map API priority to ExecutionPriority enum"""
    mapping = {
        PriorityEnum.CRITICAL: ExecutionPriority.CRITICAL,
        PriorityEnum.HIGH: ExecutionPriority.HIGH,
        PriorityEnum.NORMAL: ExecutionPriority.NORMAL,
        PriorityEnum.LOW: ExecutionPriority.LOW,
        PriorityEnum.BACKGROUND: ExecutionPriority.BACKGROUND,
    }
    return mapping.get(priority, ExecutionPriority.NORMAL)


class QueueFeatureRequest(BaseModel):
    project_id: str
    feature_id: str
    priority: PriorityEnum = PriorityEnum.HIGH


class QueueProjectRequest(BaseModel):
    project_id: str
    priority: PriorityEnum = PriorityEnum.NORMAL


class ConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    max_concurrent_executions: Optional[int] = None
    poll_interval_seconds: Optional[int] = None
    discovery_interval_seconds: Optional[int] = None
    auto_discover_new_features: Optional[bool] = None
    auto_run_on_feature_change: Optional[bool] = None
    continuous_regression_enabled: Optional[bool] = None
    regression_interval_hours: Optional[int] = None
    headless_mode: Optional[bool] = None
    execution_mode: Optional[str] = None


# =========================================================================
# LIFECYCLE ENDPOINTS
# =========================================================================

@router.post("/start")
async def start_orchestrator():
    """
    Start the autonomous orchestrator.

    Once started, the orchestrator will:
    1. Continuously discover new tests
    2. Queue and execute tests automatically
    3. Learn from results
    4. Never idle - always looking for work
    """
    try:
        orchestrator = start_autonomous_mode()
        return {
            "success": True,
            "message": "Autonomous orchestrator started",
            "status": orchestrator.get_statistics()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_orchestrator():
    """Stop the autonomous orchestrator gracefully"""
    try:
        stop_autonomous_mode()
        return {
            "success": True,
            "message": "Autonomous orchestrator stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_orchestrator():
    """Pause test execution (monitoring continues)"""
    try:
        orchestrator = get_orchestrator()
        orchestrator.pause()
        return {
            "success": True,
            "message": "Orchestrator paused"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_orchestrator():
    """Resume test execution after pause"""
    try:
        orchestrator = get_orchestrator()
        orchestrator.resume()
        return {
            "success": True,
            "message": "Orchestrator resumed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# STATUS ENDPOINTS
# =========================================================================

@router.get("/status")
async def get_status():
    """Get current orchestrator status and statistics"""
    try:
        orchestrator = get_orchestrator()
        return {
            "success": True,
            "statistics": orchestrator.get_statistics(),
            "queue": orchestrator.get_queue_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(limit: int = 50):
    """Get recent execution history"""
    try:
        orchestrator = get_orchestrator()
        return {
            "success": True,
            "history": orchestrator.get_execution_history(limit),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
async def get_queue():
    """Get current queue status"""
    try:
        orchestrator = get_orchestrator()
        return {
            "success": True,
            "queue": orchestrator.get_queue_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# QUEUE MANAGEMENT ENDPOINTS
# =========================================================================

@router.post("/queue/feature")
async def queue_feature(request: QueueFeatureRequest):
    """Manually queue a specific feature for execution"""
    try:
        orchestrator = get_orchestrator()

        if not orchestrator.is_running:
            raise HTTPException(
                status_code=400,
                detail="Orchestrator not running. Call /start first."
            )

        test_id = orchestrator.queue_feature(
            project_id=request.project_id,
            feature_id=request.feature_id,
            priority=_map_priority(request.priority),
        )

        return {
            "success": True,
            "message": "Feature queued for execution",
            "test_id": test_id,
            "queue_size": orchestrator.get_queue_size(),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/project")
async def queue_project(request: QueueProjectRequest):
    """Queue all tests for a project"""
    try:
        orchestrator = get_orchestrator()

        if not orchestrator.is_running:
            raise HTTPException(
                status_code=400,
                detail="Orchestrator not running. Call /start first."
            )

        test_ids = orchestrator.queue_project_tests(
            project_id=request.project_id,
            priority=_map_priority(request.priority),
        )

        return {
            "success": True,
            "message": f"Queued {len(test_ids)} tests for project",
            "test_ids": test_ids,
            "queue_size": orchestrator.get_queue_size(),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queue/regression")
async def trigger_regression():
    """Manually trigger regression tests for all projects"""
    try:
        orchestrator = get_orchestrator()

        if not orchestrator.is_running:
            raise HTTPException(
                status_code=400,
                detail="Orchestrator not running. Call /start first."
            )

        orchestrator._schedule_regression_tests()

        return {
            "success": True,
            "message": "Regression tests scheduled",
            "queue_size": orchestrator.get_queue_size(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# CONFIGURATION ENDPOINTS
# =========================================================================

@router.get("/config")
async def get_config():
    """Get current orchestrator configuration"""
    try:
        orchestrator = get_orchestrator()
        config = orchestrator.config

        return {
            "success": True,
            "config": {
                "enabled": config.enabled,
                "max_concurrent_executions": config.max_concurrent_executions,
                "poll_interval_seconds": config.poll_interval_seconds,
                "discovery_interval_seconds": config.discovery_interval_seconds,
                "auto_discover_new_features": config.auto_discover_new_features,
                "auto_run_on_feature_change": config.auto_run_on_feature_change,
                "continuous_regression_enabled": config.continuous_regression_enabled,
                "regression_interval_hours": config.regression_interval_hours,
                "headless_mode": config.headless_mode,
                "execution_mode": config.execution_mode,
                "max_queue_size": config.max_queue_size,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """Update orchestrator configuration"""
    try:
        orchestrator = get_orchestrator()
        config = orchestrator.config

        # Update only provided fields
        if request.enabled is not None:
            config.enabled = request.enabled
        if request.max_concurrent_executions is not None:
            config.max_concurrent_executions = request.max_concurrent_executions
        if request.poll_interval_seconds is not None:
            config.poll_interval_seconds = request.poll_interval_seconds
        if request.discovery_interval_seconds is not None:
            config.discovery_interval_seconds = request.discovery_interval_seconds
        if request.auto_discover_new_features is not None:
            config.auto_discover_new_features = request.auto_discover_new_features
        if request.auto_run_on_feature_change is not None:
            config.auto_run_on_feature_change = request.auto_run_on_feature_change
        if request.continuous_regression_enabled is not None:
            config.continuous_regression_enabled = request.continuous_regression_enabled
        if request.regression_interval_hours is not None:
            config.regression_interval_hours = request.regression_interval_hours
        if request.headless_mode is not None:
            config.headless_mode = request.headless_mode
        if request.execution_mode is not None:
            config.execution_mode = request.execution_mode

        return {
            "success": True,
            "message": "Configuration updated",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
