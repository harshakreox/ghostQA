"""
Gherkin Test Executor
Executes Gherkin scenarios using the Step Definition Library
NO AI REQUIRED AT RUNTIME
"""

from playwright.sync_api import sync_playwright, Page, Browser
from typing import List, Optional, Dict, Any
from models_gherkin import GherkinFeature, GherkinScenario, GherkinStep, StepKeyword
from step_definitions import StepDefinitionLibrary
from gherkin_parser import GherkinParser
from test_data_resolver import configure_resolver
import time


class ScenarioResult:
    """Result of executing a single scenario"""
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.status = "passed"  # "passed", "failed", "skipped"
        self.duration = 0.0
        self.error_message = None
        self.failed_step = None
        self.screenshot_path = None
        self.logs = []
    
    def to_dict(self):
        return {
            "scenario_name": self.scenario_name,
            "status": self.status,
            "duration": self.duration,
            "error_message": self.error_message,
            "failed_step": self.failed_step,
            "screenshot_path": self.screenshot_path,
            "logs": self.logs
        }


class FeatureResult:
    """Result of executing a feature file"""
    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self.scenario_results: List[ScenarioResult] = []
        self.total_scenarios = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.total_duration = 0.0
    
    def add_result(self, result: ScenarioResult):
        self.scenario_results.append(result)
        self.total_scenarios += 1
        self.total_duration += result.duration
        
        if result.status == "passed":
            self.passed += 1
        elif result.status == "failed":
            self.failed += 1
        elif result.status == "skipped":
            self.skipped += 1
    
    def to_dict(self):
        return {
            "feature_name": self.feature_name,
            "total_scenarios": self.total_scenarios,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total_duration": self.total_duration,
            "scenario_results": [r.to_dict() for r in self.scenario_results]
        }


class GherkinExecutor:
    """
    Executes Gherkin scenarios using Playwright and Step Definition Library
    """
    
    def __init__(self, base_url: str = "", headless: bool = True,
                 project_credentials: Optional[Dict[str, Any]] = None,
                 auto_test_data: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.project_credentials = project_credentials or {}
        self.auto_test_data = auto_test_data
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.step_library: Optional[StepDefinitionLibrary] = None
    
    def setup(self):
        """Setup Playwright browser"""
        # Configure the test data resolver with project credentials
        configure_resolver(
            project_credentials=self.project_credentials,
            auto_generate_enabled=self.auto_test_data
        )
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=["--start-maximized"] if not self.headless else []
        )
        context = self.browser.new_context(
            no_viewport=True if not self.headless else False,
            viewport={'width': 1920, 'height': 1080} if self.headless else None
        )
        self.page = context.new_page()
        
        # Initialize step definition library
        self.step_library = StepDefinitionLibrary(self.page, self.base_url)
    
    def teardown(self):
        """Cleanup Playwright"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def execute_feature(self, feature: GherkinFeature, 
                       scenario_filter: Optional[List[str]] = None,
                       tag_filter: Optional[List[str]] = None) -> FeatureResult:
        """
        Execute all scenarios in a feature
        
        Args:
            feature: GherkinFeature to execute
            scenario_filter: Optional list of scenario names to run
            tag_filter: Optional list of tags to filter scenarios
            
        Returns:
            FeatureResult with execution results
        """
        feature_result = FeatureResult(feature.name)
        
        # Filter scenarios if needed
        scenarios_to_run = feature.scenarios
        
        if scenario_filter:
            scenarios_to_run = [s for s in scenarios_to_run if s.name in scenario_filter]
        
        if tag_filter:
            scenarios_to_run = [s for s in scenarios_to_run 
                               if any(tag in s.tags for tag in tag_filter)]
        
        # Execute each scenario
        for scenario in scenarios_to_run:
            result = self.execute_scenario(scenario, feature.background)
            feature_result.add_result(result)
        
        return feature_result
    
    def execute_scenario(self, scenario: GherkinScenario, 
                        background: Optional[List[GherkinStep]] = None) -> ScenarioResult:
        """
        Execute a single scenario
        
        Args:
            scenario: GherkinScenario to execute
            background: Optional background steps to run first
            
        Returns:
            ScenarioResult with execution result
        """
        result = ScenarioResult(scenario.name)
        start_time = time.time()
        
        try:
            print(f"\n{'='*80}")
            print(f" Executing Scenario: {scenario.name}")
            print(f"   Tags: {', '.join(scenario.tags)}")
            print(f"{'='*80}")
            
            # Execute background steps first
            if background:
                print(f"\n Background:")
                for step in background:
                    self._execute_step(step, result)
            
            # Execute scenario steps
            print(f"\n Scenario Steps:")
            for step in scenario.steps:
                self._execute_step(step, result)
            
            result.status = "passed"
            print(f"\n[OK] Scenario PASSED")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            print(f"\n[ERR] Scenario FAILED: {str(e)}")
            
            # Take screenshot on failure
            try:
                screenshot_path = f"screenshots/failure_{scenario.name.replace(' ', '_')}.png"
                self.page.screenshot(path=screenshot_path)
                result.screenshot_path = screenshot_path
            except:
                pass
        
        finally:
            result.duration = time.time() - start_time
            print(f"⏱  Duration: {result.duration:.2f}s")
        
        return result
    
    def _execute_step(self, step: GherkinStep, result: ScenarioResult):
        """Execute a single Gherkin step"""
        step_text = f"{step.keyword} {step.text}"
        print(f"   {step.keyword.value} {step.text}")
        result.logs.append(f"Executing: {step_text}")
        
        try:
            # Try to match and execute the step
            matched = self.step_library.match_and_execute(step.text)
            
            if not matched:
                raise Exception(f"No step definition found for: {step.text}")
            
            result.logs.append(f" Success: {step_text}")
            
        except Exception as e:
            result.failed_step = step_text
            result.logs.append(f" Failed: {step_text} - {str(e)}")
            raise Exception(f"Step failed: {step_text}\n  Error: {str(e)}")
    
    def execute_feature_file(self, feature_file_path: str, **kwargs) -> FeatureResult:
        """
        Execute a .feature file
        
        Args:
            feature_file_path: Path to .feature file
            **kwargs: Additional arguments for execute_feature
            
        Returns:
            FeatureResult with execution results
        """
        # Parse the feature file
        feature = GherkinParser.parse_feature_from_file(feature_file_path)
        
        # Execute the feature
        return self.execute_feature(feature, **kwargs)


# Convenience function for quick execution
def run_feature(feature: GherkinFeature, base_url: str = "", headless: bool = True) -> FeatureResult:
    """
    Quick utility to run a feature
    
    Args:
        feature: GherkinFeature to execute
        base_url: Base URL for the application
        headless: Run in headless mode
        
    Returns:
        FeatureResult with execution results
    """
    executor = GherkinExecutor(base_url=base_url, headless=headless)
    
    try:
        executor.setup()
        result = executor.execute_feature(feature)
        return result
    finally:
        executor.teardown()


def run_feature_file(feature_file_path: str, base_url: str = "", headless: bool = True) -> FeatureResult:
    """
    Quick utility to run a .feature file
    
    Args:
        feature_file_path: Path to .feature file
        base_url: Base URL for the application
        headless: Run in headless mode
        
    Returns:
        FeatureResult with execution results
    """
    executor = GherkinExecutor(base_url=base_url, headless=headless)
    
    try:
        executor.setup()
        result = executor.execute_feature_file(feature_file_path)
        return result
    finally:
        executor.teardown()