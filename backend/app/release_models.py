from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class EnvironmentType(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    QA = "qa"
    UAT = "uat"


class ReleaseStatus(str, Enum):
    """Release status"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    READY = "ready"
    DEPLOYED = "deployed"
    FAILED = "failed"


class Environment(BaseModel):
    """Environment configuration"""
    id: str
    name: str  # e.g., "Development", "Staging", "Production"
    type: EnvironmentType
    base_url: str
    description: Optional[str] = ""
    config: Dict = {}  # Additional environment-specific configs


class ReleaseProject(BaseModel):
    """Project included in a release"""
    project_id: str
    project_name: str
    test_case_ids: List[str] = []  # Specific test cases to run, empty = all


class ReleaseIteration(BaseModel):
    """A single test run iteration for a release in an environment"""
    id: str
    release_id: str
    environment_id: str
    iteration_number: int
    report_id: str
    executed_at: str
    duration: float
    total_tests: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    status: str  # passed, failed, in_progress
    notes: Optional[str] = ""


class Release(BaseModel):
    """Release configuration"""
    id: str
    name: str  # e.g., "v2.1.0", "Sprint 42"
    version: str  # Semantic version: 2.1.0
    description: Optional[str] = ""
    status: ReleaseStatus = ReleaseStatus.DRAFT
    
    # Environments for this release
    environments: List[Environment] = []
    
    # Projects/apps to test in this release
    projects: List[ReleaseProject] = []
    
    # Test iterations per environment
    iterations: List[ReleaseIteration] = []
    
    # Metadata
    created_at: str
    updated_at: str
    created_by: Optional[str] = "admin"
    target_date: Optional[str] = None  # Target deployment date
    
    # Release metrics
    total_iterations: int = 0
    overall_pass_rate: float = 0.0
    deployment_ready: bool = False


class CreateReleaseRequest(BaseModel):
    """Request to create a new release"""
    name: str
    version: str
    description: Optional[str] = ""
    target_date: Optional[str] = None


class UpdateReleaseRequest(BaseModel):
    """Request to update release"""
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ReleaseStatus] = None
    target_date: Optional[str] = None


class AddEnvironmentRequest(BaseModel):
    """Request to add environment to release"""
    name: str
    type: EnvironmentType
    base_url: str
    description: Optional[str] = ""
    config: Dict = {}


class AddProjectToReleaseRequest(BaseModel):
    """Request to add project to release"""
    project_id: str
    test_case_ids: List[str] = []  # Empty = all test cases


class RunReleaseTestsRequest(BaseModel):
    """Request to run tests for a release"""
    release_id: str
    environment_id: str
    headless: bool = True
    notes: Optional[str] = ""


class ReleaseMetrics(BaseModel):
    """Aggregated metrics for a release"""
    release_id: str
    total_environments: int
    total_projects: int
    total_test_cases: int
    total_iterations: int
    
    # Per environment stats
    environment_stats: Dict[str, Dict] = {}
    
    # Overall metrics
    overall_pass_rate: float
    latest_iteration_date: Optional[str] = None
    deployment_ready: bool
    ready_environments: List[str] = []
    blocked_environments: List[str] = []
    
    # Trend data (last 5 iterations)
    pass_rate_trend: List[float] = []
    iteration_dates: List[str] = []