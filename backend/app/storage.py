import json
import os
from typing import List, Optional
from datetime import datetime
from models import Project, TestCase, TestReport
import uuid


class Storage:
    """File-based storage for projects, test cases, and reports"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.projects_dir = os.path.join(data_dir, "projects")
        self.reports_dir = os.path.join(data_dir, "reports")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        os.makedirs(self.projects_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def _get_project_file(self, project_id: str) -> str:
        """Get project file path"""
        return os.path.join(self.projects_dir, f"{project_id}.json")
    
    def _get_report_file(self, report_id: str) -> str:
        """Get report file path"""
        return os.path.join(self.reports_dir, f"{report_id}.json")
    
    # Project operations
    
    def create_project(self, name: str, description: str, base_url: Optional[str] = None) -> Project:
        """Create a new project"""
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            base_url=base_url,
            test_cases=[]
        )
        self.save_project(project)
        return project
    
    def save_project(self, project: Project):
        """Save project to file"""
        project.updated_at = datetime.now()
        file_path = self._get_project_file(project.id)
        with open(file_path, 'w') as f:
            json.dump(project.model_dump(mode='json'), f, indent=2, default=str)
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        file_path = self._get_project_file(project_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
            return Project(**data)
    
    def get_all_projects(self) -> List[Project]:
        """Get all projects"""
        projects = []
        for filename in os.listdir(self.projects_dir):
            if filename.endswith('.json'):
                project_id = filename[:-5]
                project = self.get_project(project_id)
                if project:
                    projects.append(project)
        return sorted(projects, key=lambda p: p.created_at, reverse=True)
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        file_path = self._get_project_file(project_id)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    # Test case operations
    
    def add_test_case(self, project_id: str, test_case: TestCase) -> Optional[Project]:
        """Add test case to project"""
        project = self.get_project(project_id)
        if not project:
            return None
        
        # Check if test case already exists
        existing_ids = [tc.id for tc in project.test_cases]
        if test_case.id in existing_ids:
            # Update existing test case
            project.test_cases = [tc if tc.id != test_case.id else test_case 
                                  for tc in project.test_cases]
        else:
            # Add new test case
            project.test_cases.append(test_case)
        
        self.save_project(project)
        return project
    
    def get_test_case(self, project_id: str, test_case_id: str) -> Optional[TestCase]:
        """Get specific test case from project"""
        project = self.get_project(project_id)
        if not project:
            return None
        
        for tc in project.test_cases:
            if tc.id == test_case_id:
                return tc
        return None
    
    def delete_test_case(self, project_id: str, test_case_id: str) -> Optional[Project]:
        """Delete test case from project"""
        project = self.get_project(project_id)
        if not project:
            return None
        
        project.test_cases = [tc for tc in project.test_cases if tc.id != test_case_id]
        self.save_project(project)
        return project
    
    # Report operations
    
    def save_report(self, report: TestReport):
        """Save test report"""
        file_path = self._get_report_file(report.id)
        with open(file_path, 'w') as f:
            json.dump(report.model_dump(mode='json'), f, indent=2, default=str)
    
    def get_report(self, report_id: str) -> Optional[TestReport]:
        """Get report by ID"""
        file_path = self._get_report_file(report_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
            return TestReport(**data)
    
    def get_project_reports(self, project_id: str) -> List[TestReport]:
        """Get all reports for a project"""
        reports = []
        for filename in os.listdir(self.reports_dir):
            if filename.endswith('.json'):
                report_id = filename[:-5]
                report = self.get_report(report_id)
                if report and report.project_id == project_id:
                    reports.append(report)
        return sorted(reports, key=lambda r: r.executed_at, reverse=True)
    
    def get_all_reports(self) -> List[TestReport]:
        """Get all reports"""
        reports = []
        for filename in os.listdir(self.reports_dir):
            if filename.endswith('.json'):
                report_id = filename[:-5]
                report = self.get_report(report_id)
                if report:
                    reports.append(report)
        return sorted(reports, key=lambda r: r.executed_at, reverse=True)

    def delete_report(self, report_id: str) -> bool:
        """Delete a test report"""
        file_path = self._get_report_file(report_id)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    # =========================================================================
    # GHERKIN FEATURE OPERATIONS (delegated to GherkinStorage)
    # =========================================================================

    def _get_gherkin_storage(self):
        """Get the GherkinStorage instance"""
        try:
            from gherkin_storage import get_gherkin_storage
            return get_gherkin_storage()
        except ImportError:
            return None

    def get_gherkin_features(self, project_id: str) -> List[dict]:
        """Get all Gherkin features for a project"""
        gherkin_storage = self._get_gherkin_storage()
        if gherkin_storage:
            return gherkin_storage.list_features(project_id=project_id) or []
        return []

    def get_gherkin_feature(self, feature_id: str) -> Optional[dict]:
        """Get a specific Gherkin feature by ID"""
        gherkin_storage = self._get_gherkin_storage()
        if gherkin_storage:
            return gherkin_storage.load_feature_dict(feature_id)
        return None

    def get_projects(self) -> List[Project]:
        """Alias for get_all_projects (used by orchestrator)"""
        return self.get_all_projects()
