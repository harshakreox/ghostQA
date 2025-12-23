from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    WAIT = "wait"
    ASSERT_TEXT = "assert_text"
    ASSERT_VISIBLE = "assert_visible"
    SELECT = "select"
    HOVER = "hover"
    SCREENSHOT = "screenshot"
    # NEW ACTION TYPES
    CHECK = "check"
    UNCHECK = "uncheck"
    ASSERT_URL = "assert_url"


class SelectorType(str, Enum):
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ID = "id"
    CLASS = "class"
    PLACEHOLDER = "placeholder"


class UIFrameworkConfig(BaseModel):
    """Configuration for UI frameworks used in the project."""
    frameworks: List[str] = []  # ["react", "material-ui", "tailwind"]
    primary_framework: Optional[str] = None  # Main component library
    testing_library: str = "playwright"  # Default testing library


class TestCredential(BaseModel):
    """A set of test credentials with a role identifier"""
    role_name: str  # e.g., "admin", "standard_user", "manager"
    username: str
    password: str


class TestAction(BaseModel):
    action: ActionType
    selector_type: Optional[SelectorType] = None
    selector: Optional[str] = None
    value: Optional[str] = None
    description: str
    wait_before: Optional[int] = 0  # milliseconds
    wait_after: Optional[int] = 500


class TestCase(BaseModel):
    id: str
    name: str
    description: str
    actions: List[TestAction]
    folder_id: Optional[str] = None  # For folder organization
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Project(BaseModel):
    id: str
    name: str
    description: str
    base_url: Optional[str] = None
    test_cases: List[TestCase] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Owner tracking for role-based access
    owner_id: Optional[str] = None  # User ID who created the project

    # New: Multiple credential sets with roles
    credentials: List[TestCredential] = []

    # Legacy credentials (kept for backward compatibility)
    test_username: Optional[str] = None
    test_password: Optional[str] = None
    test_email: Optional[str] = None
    test_admin_username: Optional[str] = None
    test_admin_password: Optional[str] = None

    # Test Data Configuration
    auto_test_data: bool = True  # Enable auto-generation when no explicit value/creds

    # UI Framework Configuration for AI test generation
    ui_config: Optional[UIFrameworkConfig] = None

    def get_credentials_by_role(self, role_name: str) -> Optional[TestCredential]:
        """Get credentials by role name (case-insensitive)"""
        role_lower = role_name.lower()
        for cred in self.credentials:
            if cred.role_name.lower() == role_lower:
                return cred
        return None

    def get_all_roles(self) -> List[str]:
        """Get list of all available role names"""
        return [cred.role_name for cred in self.credentials]


class TestResult(BaseModel):
    test_case_id: str
    test_case_name: str
    status: str  # "passed", "failed", "skipped"
    duration: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    logs: List[str] = []


class EnhancedTestResult(TestResult):
    """Extended test result with failure artifacts and self-healing info."""
    html_snapshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None
    retry_count: int = 0
    self_healed: bool = False
    healing_method: Optional[str] = None  # "fuzzy_match", "coordinates", "dom_refresh"


class TestReport(BaseModel):
    id: str
    project_id: str
    project_name: str
    executed_at: datetime = Field(default_factory=datetime.now)
    total_tests: int
    passed: int
    failed: int
    skipped: int = 0
    duration: float
    results: List[TestResult]


class CreateProjectRequest(BaseModel):
    name: str
    description: str
    base_url: Optional[str] = None
    # New: Multiple credential sets with roles
    credentials: List[TestCredential] = []
    # Legacy Test Credentials (optional, for backward compatibility)
    test_username: Optional[str] = None
    test_password: Optional[str] = None
    test_admin_username: Optional[str] = None
    test_admin_password: Optional[str] = None
    # Test Data Configuration
    auto_test_data: bool = True
    # UI Framework Configuration (optional)
    ui_config: Optional[UIFrameworkConfig] = None


class CreateTestCaseRequest(BaseModel):
    name: str
    description: str
    actions: List[TestAction]


class RunTestRequest(BaseModel):
    project_id: str
    test_case_ids: List[str]
    headless: bool = False