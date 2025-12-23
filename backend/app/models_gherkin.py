"""
Gherkin-based Test Models for BDD Test Cases
Replaces action-based TestCase with proper BDD/Gherkin structure
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class StepKeyword(str, Enum):
    """Gherkin step keywords"""
    GIVEN = "Given"
    WHEN = "When"
    THEN = "Then"
    AND = "And"
    BUT = "But"


class GherkinStep(BaseModel):
    """A single Gherkin step (Given/When/Then/And/But)"""
    keyword: StepKeyword
    text: str  # e.g., "I am on the login page"
    
    def __str__(self):
        return f"{self.keyword.value} {self.text}"  # [OK] FIXED: Added .value


class GherkinScenario(BaseModel):
    """A single test scenario in BDD format"""
    name: str  # e.g., "Successful login with valid credentials"
    tags: List[str] = []  # e.g., ["@smoke", "@login", "@happy-path"]
    steps: List[GherkinStep]
    description: Optional[str] = None
    
    def to_gherkin(self) -> str:
        """Convert to Gherkin text format"""
        lines = []
        
        # Add tags
        if self.tags:
            lines.append("  " + " ".join(self.tags))
        
        # Add scenario name
        lines.append(f"  Scenario: {self.name}")
        
        # Add description if exists
        if self.description:
            lines.append(f"    {self.description}")
        
        # Add steps
        for step in self.steps:
            lines.append(f"    {step}")  # This calls __str__ which now uses .value
        
        return "\n".join(lines)


class GherkinFeature(BaseModel):
    """A complete feature file with multiple scenarios"""
    id: str
    name: str  # Feature title
    description: Optional[str] = None
    background: Optional[List[GherkinStep]] = None  # Background steps
    scenarios: List[GherkinScenario]
    folder_id: Optional[str] = None  # Optional folder for organization (None = root level)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def to_gherkin(self) -> str:
        """Convert to complete .feature file format"""
        lines = [f"Feature: {self.name}"]
        
        # Add description
        if self.description:
            lines.append(f"  {self.description}")
            lines.append("")
        
        # Add background
        if self.background:
            lines.append("  Background:")
            for step in self.background:
                lines.append(f"    {step}")  # This calls __str__ which now uses .value
            lines.append("")
        
        # Add scenarios
        for idx, scenario in enumerate(self.scenarios):
            if idx > 0:
                lines.append("")  # Blank line between scenarios
            lines.append(scenario.to_gherkin())
        
        return "\n".join(lines)


class TestCredential(BaseModel):
    """A set of test credentials with a role identifier"""
    role_name: str  # e.g., "admin", "standard_user", "manager"
    username: str
    password: str


class Project(BaseModel):
    """Project containing Gherkin features"""
    id: str
    name: str
    description: str
    base_url: Optional[str] = None
    features: List[GherkinFeature] = []  # Changed from test_cases to features
    # New: Multiple credential sets with roles
    credentials: List[TestCredential] = []
    # Legacy fields (kept for backward compatibility, will be migrated to credentials)
    test_username: Optional[str] = None
    test_password: Optional[str] = None
    test_email: Optional[str] = None
    test_admin_username: Optional[str] = None
    test_admin_password: Optional[str] = None
    auto_test_data: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

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
    """Result of executing a single scenario"""
    scenario_id: str
    scenario_name: str
    status: str  # "passed", "failed", "skipped"
    duration: float
    error_message: Optional[str] = None
    failed_step: Optional[str] = None  # Which step failed
    screenshot_path: Optional[str] = None
    logs: List[str] = []


class EnhancedTestResult(TestResult):
    """Extended test result with failure artifacts"""
    html_snapshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None
    retry_count: int = 0
    self_healed: bool = False
    healing_method: Optional[str] = None


class TestReport(BaseModel):
    """Report for a test execution run"""
    id: str
    project_id: str
    project_name: str
    executed_at: datetime = Field(default_factory=datetime.now)
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    results: List[TestResult]


class CreateProjectRequest(BaseModel):
    """Request to create a new project"""
    name: str
    description: str
    base_url: Optional[str] = None
    credentials: List[TestCredential] = []
    auto_test_data: bool = True


class CreateFeatureRequest(BaseModel):
    """Request to create a new Gherkin feature"""
    name: str
    description: Optional[str] = None
    background: Optional[List[GherkinStep]] = None
    scenarios: List[GherkinScenario]


class RunTestRequest(BaseModel):
    """Request to run tests"""
    project_id: str
    feature_ids: List[str]  # Changed from test_case_ids
    scenario_names: Optional[List[str]] = None  # Optionally run specific scenarios
    headless: bool = False
    tags: Optional[List[str]] = None  # Run scenarios with specific tags


# ============ TRADITIONAL TEST CASE FORMAT ============
class TraditionalTestCase(BaseModel):
    """Traditional table format test case"""
    test_case_no: int
    scenario_name: str
    precondition: str
    steps: str  # Steps as a string (can be multiline)
    expected_outcome: str
    post_condition: str
    tags: List[str] = []


class TraditionalTestSuite(BaseModel):
    """Collection of traditional test cases"""
    id: str
    name: str
    description: Optional[str] = None
    test_cases: List[TraditionalTestCase]
    folder_id: Optional[str] = None  # For folder organization
    project_id: Optional[str] = None  # Link to project
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_csv(self) -> str:
        """Convert to CSV format"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'Test Case No',
            'Scenario Name',
            'Precondition',
            'Steps',
            'Expected Outcome',
            'Post Condition',
            'Tags'
        ])

        # Data rows
        for tc in self.test_cases:
            writer.writerow([
                tc.test_case_no,
                tc.scenario_name,
                tc.precondition,
                tc.steps,
                tc.expected_outcome,
                tc.post_condition,
                ', '.join(tc.tags)
            ])

        return output.getvalue()


class GenerateTraditionalRequest(BaseModel):
    """Request to generate traditional test cases"""
    brd_content: str
    project_id: Optional[str] = None
    project_context: Optional[str] = None
    end_to_end: bool = False


class GenerateTraditionalResponse(BaseModel):
    """Response containing generated traditional test cases"""
    test_suite: TraditionalTestSuite
    brd_summary: str
    suggestions: List[str] = []


# Backward compatibility aliases (if needed during migration)
TestCase = GherkinFeature  # Alias for backward compatibility
CreateTestCaseRequest = CreateFeatureRequest