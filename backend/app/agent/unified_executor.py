"""
Unified Test Executor

Bridges the Autonomous Test Agent with both Traditional and Gherkin test formats.
Provides a single entry point for all test execution while leveraging the
self-learning knowledge base.

This ensures:
- Same execution engine for traditional and Gherkin tests
- Consistent UI/reporting across test types
- Training data collection during all test runs
- Reduced AI dependency over time
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

from .core.agent import AutonomousTestAgent, AgentConfig, TestResult, TestStep, StepStatus
from .core.selector_service import SelectorService, ResolutionTier
from .core.spa_handler import SPAHandler, SPAFramework
from .knowledge.knowledge_index import KnowledgeIndex
from .knowledge.learning_engine import LearningEngine
from .knowledge.pattern_store import PatternStore
from .explorer.app_explorer import ApplicationExplorer, ExplorationConfig
from .context.project_context import ProjectContext, get_project_context
from .context.navigation_intelligence import NavigationIntelligence, NavigationResult

# Configure logging
logger = logging.getLogger(__name__)


class TestFormat(Enum):
    """Supported test formats"""
    TRADITIONAL = "traditional"  # Action-based test cases
    GHERKIN = "gherkin"  # BDD feature files
    HYBRID = "hybrid"  # Mix of both


class ExecutionMode(Enum):
    """Test execution modes"""
    AUTONOMOUS = "autonomous"  # Full AI-powered execution
    GUIDED = "guided"  # Use knowledge base, AI fallback
    STRICT = "strict"  # No AI, only knowledge base


@dataclass
class UnifiedTestCase:
    """
    Unified test case format that works for both Traditional and Gherkin.

    This normalizes the differences between formats into a common structure
    that the autonomous agent can execute.
    """
    id: str
    name: str
    description: str
    format: TestFormat
    steps: List[Dict[str, Any]]
    tags: List[str] = field(default_factory=list)

    # Original data (for reference/reporting)
    original_data: Optional[Dict[str, Any]] = None

    # Gherkin-specific
    feature_name: Optional[str] = None
    scenario_name: Optional[str] = None
    background_steps: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class UnifiedTestResult:
    """
    Unified test result format for consistent reporting.
    """
    test_id: str
    test_name: str
    format: TestFormat
    status: str  # passed, failed, skipped

    # Execution details
    total_steps: int
    passed_steps: int
    failed_steps: int
    recovered_steps: int

    # Timing
    duration_ms: int
    started_at: str
    completed_at: str

    # Step details
    step_results: List[Dict[str, Any]]

    # Errors and logs
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    # Artifacts
    screenshot_path: Optional[str] = None
    html_snapshot_path: Optional[str] = None

    # Learning metrics
    ai_calls_made: int = 0
    knowledge_base_hits: int = 0
    selectors_learned: int = 0

    # SPA info
    is_spa: bool = False
    spa_framework: Optional[str] = None


@dataclass
class UnifiedExecutionReport:
    """
    Unified report format for consistent UI display.
    """
    id: str
    project_id: str
    project_name: str

    # Execution info
    format: TestFormat
    execution_mode: ExecutionMode
    executed_at: str
    completed_at: str
    duration_seconds: float

    # Summary
    total_tests: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float

    # Results
    results: List[UnifiedTestResult]

    # Learning summary
    total_ai_calls: int
    total_kb_hits: int
    ai_dependency_percent: float
    new_selectors_learned: int

    # Errors
    errors: List[str] = field(default_factory=list)


class UnifiedTestExecutor:
    """
    Unified test executor that handles both Traditional and Gherkin tests
    using the Autonomous Test Agent.

    Features:
    - Single execution engine for all test formats
    - Automatic knowledge base learning
    - Training data collection
    - Consistent result format
    - Real-time progress callbacks
    """

    def __init__(
        self,
        data_dir: str = "data/agent_knowledge",
        config: Optional[AgentConfig] = None
    ):
        """
        Initialize unified executor.

        Args:
            data_dir: Directory for knowledge storage
            config: Agent configuration
        """
        self.data_dir = Path(data_dir)
        self.config = config or AgentConfig()

        # Initialize knowledge components
        self.knowledge_index = KnowledgeIndex(str(self.data_dir))
        self.pattern_store = PatternStore(str(self.data_dir / "patterns"))
        self.learning_engine = LearningEngine(
            self.knowledge_index,
            self.pattern_store,
            str(self.data_dir)
        )

        # Project context for navigation intelligence (set per project)
        self._project_context: Optional[ProjectContext] = None
        self._nav_intelligence: Optional[NavigationIntelligence] = None

        # Agent will be initialized per execution
        self._agent: Optional[AutonomousTestAgent] = None
        self._page = None
        self._browser = None
        self._playwright = None

        # Callbacks
        self._log_callback: Optional[Callable[[str], None]] = None
        self._progress_callback: Optional[Callable[[Dict], None]] = None
        self._step_callback: Optional[Callable[[Dict], None]] = None

        # Stop control
        self._should_stop = False
        self._stop_check_callback: Optional[Callable[[], bool]] = None

        # Training data collection
        self._collect_training_data = True
        self._training_data: List[Dict] = []

    def set_callbacks(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[Dict], None]] = None,
        step_callback: Optional[Callable[[Dict], None]] = None
    ):
        """Set execution callbacks for real-time updates"""
        self._log_callback = log_callback
        self._progress_callback = progress_callback
        self._step_callback = step_callback

    def set_stop_callback(self, callback: Callable[[], bool]):
        """
        Set a callback to check if execution should stop.

        The callback should return True if execution should stop.
        """
        self._stop_check_callback = callback

    def request_stop(self):
        """Request execution to stop after current test"""
        self._should_stop = True
        self._log("Stop requested - will stop after current test completes")

    async def force_stop(self):
        """Force immediate stop by closing browser - use for emergency stop"""
        self._should_stop = True
        self._log("FORCE STOP - Closing browser immediately!")
        
        try:
            # Close page first to interrupt any running operations
            if self._page:
                try:
                    await self._page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
                self._page = None
            
            # Close browser
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                self._browser = None
            
            # Stop playwright
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
                self._playwright = None
                
            self._log("Force stop completed - browser closed")
            
        except Exception as e:
            logger.error(f"Error during force stop: {e}")

    def _check_should_stop(self) -> bool:
        """Check if execution should stop"""
        if self._should_stop:
            return True
        if self._stop_check_callback:
            return self._stop_check_callback()
        return False

    def _log(self, message: str, level: str = "info"):
        """Log message and send to callback"""
        log_entry = f"[{datetime.utcnow().strftime('%H:%M:%S')}] [{level.upper()}] {message}"
        logger.info(message)
        if self._log_callback:
            self._log_callback(log_entry)

    def _build_step_description(self, step) -> str:
        """Build a human-readable description for a step"""
        action = step.action.lower() if step.action else "unknown"
        target = step.target
        value = step.value if hasattr(step, 'value') else None

        # Build description based on action type
        if action == "navigate":
            url = value or target or "page"
            # Truncate long URLs
            if url and len(url) > 50:
                url = url[:47] + "..."
            return f"Navigate to {url}"

        elif action == "click":
            element = target or "element"
            return f"Click on '{element}'"

        elif action == "type":
            element = target or "field"
            text = value or ""
            # Truncate and mask long/sensitive text
            if len(text) > 20:
                text = text[:17] + "..."
            return f"Type '{text}' into '{element}'"

        elif action == "select":
            element = target or "dropdown"
            option = value or "option"
            return f"Select '{option}' from '{element}'"

        elif action == "assert_visible":
            element = target or "element"
            return f"Assert '{element}' is visible"

        elif action == "assert_text":
            element = target or "element"
            expected = value or ""
            if len(expected) > 30:
                expected = expected[:27] + "..."
            return f"Assert text '{expected}' in '{element}'"

        elif action == "assert_url":
            expected = value or target or "URL"
            if len(expected) > 40:
                expected = expected[:37] + "..."
            return f"Assert URL contains '{expected}'"

        elif action == "wait":
            ms = value or target or "1000"
            return f"Wait {ms}ms"

        elif action == "hover":
            element = target or "element"
            return f"Hover over '{element}'"

        elif action == "clear":
            element = target or "field"
            return f"Clear '{element}'"

        elif action == "scroll":
            direction = value or "down"
            return f"Scroll {direction}"

        elif action == "gherkin_step":
            # For Gherkin steps, use the text directly
            keyword = getattr(step, 'keyword', '') if hasattr(step, 'keyword') else ''
            text = target or value or "step"
            return f"{keyword} {text}".strip()

        elif action == "resolve_precondition":
            page = target or "page"
            return f"Ensure on '{page}' page (navigate if needed)"

        elif action == "smart_navigate":
            page = target or "page"
            return f"Navigate to '{page}' page"

        else:
            # Default: show action and target
            if target:
                return f"{action.capitalize()} on '{target}'"
            return action.capitalize()

    # ==================== Test Conversion ====================

    def convert_traditional_test(self, test_case: Dict[str, Any]) -> UnifiedTestCase:
        """
        Convert a traditional test case to unified format.

        Traditional format:
        {
            "id": "...",
            "name": "...",
            "description": "...",
            "actions": [
                {"action": "navigate", "selector": "...", "value": "..."},
                ...
            ]
        }
        """
        steps = []
        actions = test_case.get("actions", [])
        logger.info(f"Converting test case with {len(actions)} actions")

        for i, action in enumerate(actions):
            # Handle both dict and Pydantic model formats
            if hasattr(action, 'model_dump'):
                action = action.model_dump()
            elif hasattr(action, 'dict'):
                action = action.dict()

            # Get action type - handle both string and enum
            action_type = action.get("action", "")
            if hasattr(action_type, 'value'):
                action_type = action_type.value
            action_type = str(action_type).lower()

            # Get selector - this is the key field
            selector = action.get("selector")

            logger.debug(f"Action {i+1}: type={action_type}, selector={selector}, value={action.get('value')}")

            step = {
                "action": action_type,
                "target": selector,
                "target_type": action.get("selector_type", "css"),
                "value": action.get("value"),
                "description": action.get("description", ""),
                "wait_before": action.get("wait_before", 0),
                "wait_after": action.get("wait_after", 0),
                "expected": action.get("expected")
            }
            steps.append(step)

        return UnifiedTestCase(
            id=test_case.get("id", ""),
            name=test_case.get("name", "Unnamed Test"),
            description=test_case.get("description", ""),
            format=TestFormat.TRADITIONAL,
            steps=steps,
            tags=test_case.get("tags", []),
            original_data=test_case
        )

    def convert_gherkin_scenario(
        self,
        scenario: Dict[str, Any],
        feature: Dict[str, Any],
        background: Optional[List[Dict]] = None
    ) -> UnifiedTestCase:
        """
        Convert a Gherkin scenario to unified format.

        Gherkin format:
        Feature: {
            "name": "...",
            "scenarios": [{
                "name": "...",
                "steps": [{"keyword": "Given", "text": "..."}]
            }]
        }
        """
        # Convert background steps
        bg_steps = []
        if background:
            for step in background:
                bg_steps.append({
                    "action": "gherkin_step",
                    "keyword": step.get("keyword", "Given"),
                    "text": step.get("text", ""),
                    "description": f"{step.get('keyword', 'Given')} {step.get('text', '')}"
                })

        # Convert scenario steps
        steps = []
        for step in scenario.get("steps", []):
            steps.append({
                "action": "gherkin_step",
                "keyword": step.get("keyword", "When"),
                "text": step.get("text", ""),
                "description": f"{step.get('keyword', 'When')} {step.get('text', '')}"
            })

        return UnifiedTestCase(
            id=f"{feature.get('id', '')}_{scenario.get('name', '').replace(' ', '_')}",
            name=scenario.get("name", "Unnamed Scenario"),
            description=scenario.get("description", ""),
            format=TestFormat.GHERKIN,
            steps=steps,
            tags=scenario.get("tags", []),
            feature_name=feature.get("name"),
            scenario_name=scenario.get("name"),
            background_steps=bg_steps,
            original_data={"feature": feature, "scenario": scenario}
        )

    def convert_gherkin_feature(self, feature: Dict[str, Any]) -> List[UnifiedTestCase]:
        """Convert all scenarios in a feature to unified format"""
        test_cases = []
        background = feature.get("background", [])

        for scenario in feature.get("scenarios", []):
            test_case = self.convert_gherkin_scenario(scenario, feature, background)
            test_cases.append(test_case)

        return test_cases

    # ==================== Gherkin Step Interpretation ====================

    def _interpret_gherkin_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpret a Gherkin step into an executable action.

        Uses pattern matching first, then AI if needed.
        """
        keyword = step.get("keyword", "").lower()
        text = step.get("text", "")
        full_step = f"{keyword} {text}".lower()

        print(f"\n[GHERKIN-INTERPRET] === STEP ===", flush=True)
        print(f"[GHERKIN-INTERPRET] Keyword: '{keyword}'", flush=True)
        print(f"[GHERKIN-INTERPRET] Text: '{text}'", flush=True)
        print(f"[GHERKIN-INTERPRET] Full: '{full_step}'", flush=True)

        # Navigation patterns
        if any(p in full_step for p in ["navigate to", "go to", "open", "visit"]):
            import re
            # Pattern 1: Explicit URL (http://, https://, or contains / or .)
            url_match = re.search(r'(?:to|open|visit)\s+["\']?(https?://[^\s"\']+)["\']?', text, re.I)
            if url_match:
                return {"action": "navigate", "value": url_match.group(1)}

            # Pattern 2: Relative path (starts with /)
            path_match = re.search(r'(?:to|open|visit)\s+["\']?(/[^\s"\']+)["\']?', text, re.I)
            if path_match:
                return {"action": "navigate", "value": path_match.group(1)}

            # Pattern 3: Page concept like "registration page", "login page"
            # Instead of navigating directly, find and click the link/button
            page_match = re.search(r'(?:the\s+)?(\w+)\s+page', text, re.I)
            if page_match:
                page_name = page_match.group(1).lower()
                # Return a smart navigation that will find the link/button first
                return {
                    "action": "smart_navigate",
                    "target": page_name,
                    "description": f"Find and click link/button to {page_name} page"
                }

        # Click patterns
        if any(p in full_step for p in ["click", "press", "tap", "select"]):
            import re

            # Pattern 1: "click X button with data-testid 'Y'" - extract data-testid directly
            testid_match = re.search(r'click(?:\s+on)?.*?data-(?:test(?:id)?|cy|qa)\s*["\']([^"\']+)["\']', text, re.I)
            if testid_match:
                return {"action": "click", "target": testid_match.group(1).strip()}

            # Pattern 2: "click the X button" or "click on X" - greedy match for element name
            btn_match = re.search(r'click(?:\s+on)?\s+(?:the\s+)?["\']?(\w+(?:[\s-]\w+)*)["\']?\s*(?:button|link|element|icon)?', text, re.I)
            if btn_match:
                return {"action": "click", "target": btn_match.group(1).strip()}

        # Type/Enter patterns
        if any(p in full_step for p in ["enter", "type", "fill", "input"]):
            import re

            # Pattern 0: "enter my/the/valid username/password" - credential keywords
            cred_match = re.search(r'(?:enter|type|fill|input)\s+(?:my|the|a|valid|test)?\s*(username|password|email)', text, re.I)
            if cred_match:
                field = cred_match.group(1).lower()
                if 'user' in field or 'email' in field:
                    return {"action": "type", "value": "", "target": "username"}
                elif 'pass' in field:
                    return {"action": "type", "value": "", "target": "password"}

            # Pattern 0b: "enter X in the username/password/email field"
            field_match = re.search(r'(?:enter|type|fill|input)\s+(.+?)\s+(?:in(?:to)?|on)\s+(?:the\s+)?(username|password|email|user|login)', text, re.I)
            if field_match:
                val = field_match.group(1).strip().strip("'\"")
                tgt = field_match.group(2).lower()
                return {"action": "type", "value": val, "target": "username" if 'user' in tgt or 'email' in tgt or 'login' in tgt else "password"}


            # Pattern 1: "enter X in the Y field with data-testid 'Z'" - extract data-testid directly
            testid_match = re.search(r'(?:enter|type|fill|input)\s+["\']([^"\']+)["\'].*?data-(?:test(?:id)?|cy|qa)\s*["\']([^"\']+)["\']', text, re.I)
            if testid_match:
                return {"action": "type", "value": testid_match.group(1), "target": testid_match.group(2).strip()}

            # Pattern 2: "enter X in the Y field" - standard pattern
            # Capture field name, then strip trailing 'field', 'input', 'box' from target
            type_match = re.search(r'(?:enter|type|fill|input)\s+["\']([^"\']+)["\']\s+(?:in(?:to)?|on)\s+(?:the\s+)?(.+?)(?:\s+(?:field|input|box)|\s*$)', text, re.I)
            if type_match:
                value = type_match.group(1)
                target = type_match.group(2).strip()
                # Clean up target - remove any trailing punctuation or extra words
                target = re.sub(r'\s+(field|input|box|area|element)$', '', target, flags=re.I)
                # If target is still multi-word with common suffixes, take just the key part
                target = target.strip()
                logger.debug(f"Gherkin Pattern 2: value='{value}', target='{target}'")
                return {"action": "type", "value": value, "target": target}

            # Pattern 3: Fallback - simpler pattern for unquoted values
            simple_match = re.search(r'(?:enter|type|fill|input)\s+(\S+)\s+(?:in(?:to)?|on)\s+(?:the\s+)?(\w+)', text, re.I)
            if simple_match:
                return {"action": "type", "value": simple_match.group(1), "target": simple_match.group(2).strip()}

        # Assertion patterns
        if any(p in full_step for p in ["should see", "should be", "is displayed", "is visible"]):
            import re
            # "should see X"
            see_match = re.search(r'should\s+see\s+["\']?([^"\']+)["\']?', text, re.I)
            if see_match:
                return {"action": "assert", "target": see_match.group(1), "expected": see_match.group(1)}
            # "X should be visible"
            visible_match = re.search(r'["\']?([^"\']+?)["\']?\s+(?:should\s+be|is)\s+(?:visible|displayed)', text, re.I)
            if visible_match:
                return {"action": "assert", "target": visible_match.group(1)}

        # Wait patterns
        if any(p in full_step for p in ["wait", "pause", "delay"]):
            import re
            time_match = re.search(r'(\d+)\s*(?:seconds?|s|ms|milliseconds?)', text, re.I)
            if time_match:
                wait_time = int(time_match.group(1))
                if "ms" in text.lower() or "millisecond" in text.lower():
                    return {"action": "wait", "value": str(wait_time)}
                return {"action": "wait", "value": str(wait_time * 1000)}

        # "Given I am on X page/form/screen" - PRECONDITION requiring navigation
        print(f"[GHERKIN-DEBUG] Interpreting: keyword='{keyword}', text='{text}'", flush=True)
        print(f"[GHERKIN-DEBUG] full_step='{full_step}'", flush=True)
        if any(p in full_step for p in ["i am on", "am on the", "should be on", "user is on"]):
            import re
            # Check for URL in the step
            url_match = re.search(r'(?:at|on)\s+(https?://[^\s]+)', text, re.I)
            if url_match:
                return {"action": "navigate", "value": url_match.group(1)}
            # Check for page/form/screen name - match "registration page", "signup form", "login screen"
            # Pattern matches: "on the registration form", "on registration page", "on the signup screen"
            page_match = re.search(r'(?:on\s+(?:the\s+)?)?(\w+(?:\s+\w+)?)\s+(?:page|form|screen|view)', text, re.I)
            if page_match:
                target_page = page_match.group(1).strip().lower()
                print(f"[GHERKIN-DEBUG] Matched precondition -> target: '{target_page}'", flush=True)
                # Return a PRECONDITION action that will use navigation intelligence
                return {
                    "action": "resolve_precondition",
                    "target": target_page,
                    "precondition_text": text,
                    "description": f"Ensure we are on {target_page} page (navigate if needed)"
                }
            # Generic "I am on" with no specific page - treat as context
            return {"action": "noop", "description": text}

        # "Then I should be redirected to X" - URL assertion
        if any(p in full_step for p in ["redirected to", "redirect to", "taken to"]):
            import re
            # Extract the target page/URL - only capture the key word before "page"
            redirect_match = re.search(r'(?:redirected|redirect|taken)\s+to\s+(?:the\s+)?(\w+)(?:\s+page)?', text, re.I)
            if redirect_match:
                target_page = redirect_match.group(1).strip()
                logger.debug(f"Redirect pattern matched: target_page='{target_page}' from text='{text}'")
                return {"action": "assert_url", "target": target_page, "description": f"Verify URL contains '{target_page}'"}

        # "application is loaded" or "page is loaded" - wait for page ready
        if any(p in full_step for p in ["is loaded", "has loaded", "loaded successfully"]):
            return {"action": "wait", "value": "1000", "description": "Wait for page load"}

        # If no pattern matched, return as-is for AI interpretation
        return {
            "action": "gherkin_step",
            "keyword": keyword,
            "text": text,
            "requires_ai": True
        }
    def _interpret_with_ai(self, step, credentials=None):
        """Use AI to interpret Gherkin step when patterns fail.

        IMPORTANT: This function should NEVER inject credentials into values!
        Data resolution happens AFTER this step and will set appropriate values
        based on whether it's a registration or login flow.
        """
        import os, json

        keyword = step.get("keyword", "")
        text = step.get("text", "")
        step_text = f"{keyword} {text}"

        self._log(f"[AI] Interpreting: {step_text[:60]}...")

        # Build AI prompt - NO CREDENTIALS! Data resolution handles this later.
        prompt = f"""Convert this test step to an action. Return ONLY JSON.

STEP: "{step_text}"

Return JSON: {{"action": "click|fill|navigate|wait|assert_visible", "target": "element", "value": "optional value"}}

RULES:
- For form fields (username, email, password, etc.): set action="fill", target to field name, value="" (empty - will be filled later)
- For click actions: set action="click", target to element description
- For wait: set action="wait", value to milliseconds
- For assertions: set action="assert_visible", target to expected text

IMPORTANT: Do NOT put actual data values - just identify the action and target field.
"""

        # Try Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                msg = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                resp = msg.content[0].text.strip()
                # Extract JSON
                if "{" in resp:
                    resp = resp[resp.find("{"):resp.rfind("}")+1]
                result = json.loads(resp)
                # ALWAYS clear value for fill actions - data resolution will set it
                if result.get("action") == "fill":
                    result["value"] = ""
                self._log(f"[AI] Result: {result.get('action')} -> {result.get('target')}")
                return result
            except Exception as e:
                self._log(f"[AI] Error: {e}")

        # Fallback heuristic - NEVER inject credentials, just identify field type
        text_lower = text.lower()
        if any(w in text_lower for w in ['click', 'press', 'tap']):
            return {"action": "click", "target": text}
        elif any(w in text_lower for w in ['username', 'user', 'login']) and 'email' not in text_lower:
            return {"action": "fill", "target": "username", "value": ""}  # Empty! Data resolution fills it
        elif 'email' in text_lower:
            return {"action": "fill", "target": "email", "value": ""}  # Empty! Data resolution fills it
        elif 'password' in text_lower:
            return {"action": "fill", "target": "password", "value": ""}  # Empty! Data resolution fills it
        elif any(w in text_lower for w in ['enter', 'type', 'fill', 'complete']):
            return {"action": "fill", "target": text, "value": ""}  # Empty! Data resolution fills it
        elif any(w in text_lower for w in ['see', 'visible', 'displayed']):
            return {"action": "assert_visible", "target": text}
        elif any(w in text_lower for w in ['navigate', 'go to', 'open']):
            return {"action": "navigate", "target": text}
        return {"action": "noop", "target": text}



    # ==================== Main Execution ====================

    async def execute(
        self,
        test_cases: List[UnifiedTestCase],
        base_url: str,
        project_id: str,
        project_name: str,
        headless: bool = False,
        execution_mode: ExecutionMode = ExecutionMode.GUIDED,
        ai_callback: Optional[Callable] = None,
        credentials: Optional[Dict[str, str]] = None
    ) -> UnifiedExecutionReport:
        """
        Execute test cases using the autonomous agent.

        Args:
            test_cases: List of unified test cases
            base_url: Application base URL
            project_id: Project identifier
            project_name: Project name for reporting
            headless: Run browser in headless mode
            execution_mode: How much AI to use
            ai_callback: AI decision callback for autonomous mode
            credentials: Optional login credentials

        Returns:
            UnifiedExecutionReport with all results
        """
        from playwright.async_api import async_playwright

        report_id = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.utcnow()
        results: List[UnifiedTestResult] = []
        errors: List[str] = []

        # Reset stop flag at start of execution
        self._should_stop = False

        # Metrics
        total_ai_calls = 0
        total_kb_hits = 0
        new_selectors = 0

        print("")
        print("=" * 60)
        print(f"[GHOSTQA] Starting test execution: {project_name}")
        print(f"[GHOSTQA] Mode: {execution_mode.value}, Headless: {headless}")
        print(f"[GHOSTQA] Base URL: {base_url}")
        if credentials:
            uname = credentials.get('username') or credentials.get('admin_username', 'N/A')
            print(f"[GHOSTQA] Credentials: {uname[:3] if uname else 'N/A'}*** / ****")
        else:
            print("[GHOSTQA] WARNING: No credentials provided!")
        print("=" * 60)
        print("")
        self._log(f"Starting unified test execution for {project_name}")
        self._log(f"Mode: {execution_mode.value}, Tests: {len(test_cases)}, Headless: {headless}")

        # Track current context for cleanup
        current_context = None

        try:
            # Initialize Playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                slow_mo=100 if not headless else 0,
                args=["--start-maximized"] if not headless else []
            )

            # Execute each test with FRESH browser context
            self._log(f"Starting test execution phase ({len(test_cases)} tests)")
            for i, test_case in enumerate(test_cases):
                # Check for stop request before each test
                if self._check_should_stop():
                    self._log("Execution stopped by user request")
                    break

                self._log(f"")
                self._log(f"{'='*50}")
                self._log(f"Executing scenario {i+1}/{len(test_cases)}: {test_case.name}")
                self._log(f"Steps: {len(test_case.steps)}")

                # ============================================================
                # SCENARIO ISOLATION: Create NEW browser context for each scenario
                # This ensures completely fresh state (cookies, localStorage, sessionStorage)
                # ============================================================
                print(f"\n[ISOLATION] === CREATING FRESH BROWSER CONTEXT ===", flush=True)
                print(f"[ISOLATION] Scenario: {test_case.name}", flush=True)
                print(f"[ISOLATION] Previous context exists: {current_context is not None}", flush=True)
                self._log(f"[ISOLATION] Creating fresh browser context for scenario...")
                try:
                    # Close previous context if exists
                    if current_context:
                        try:
                            print(f"[ISOLATION] Closing previous context...", flush=True)
                            await current_context.close()
                            print(f"[ISOLATION] Previous context closed successfully", flush=True)
                            self._log(f"[ISOLATION] Closed previous browser context")
                        except Exception as close_err:
                            print(f"[ISOLATION] Warning closing context: {close_err}", flush=True)
                            self._log(f"[ISOLATION] Warning closing context: {close_err}")

                    # Create brand new context (fresh cookies, storage, cache)
                    print(f"[ISOLATION] Creating new browser context...", flush=True)
                    current_context = await self._browser.new_context(
                        no_viewport=True if not headless else False,
                        viewport={"width": 1920, "height": 1080} if headless else None
                    )
                    print(f"[ISOLATION] New context created: {current_context}", flush=True)

                    self._page = await current_context.new_page()
                    print(f"[ISOLATION] New page created: {self._page.url}", flush=True)

                    # Create fresh agent for this scenario
                    print(f"[ISOLATION] Creating fresh agent...", flush=True)
                    self._agent = AutonomousTestAgent(
                        page=self._page,
                        data_dir=str(self.data_dir),
                        config=self.config
                    )
                    print(f"[ISOLATION] Fresh agent created", flush=True)

                    # Initialize project context and navigation intelligence
                    project_id = test_case.project_id if hasattr(test_case, 'project_id') else "default"
                    self._project_context = get_project_context(project_id, str(self.data_dir))
                    self._project_context.set_base_info(base_url)
                    self._nav_intelligence = NavigationIntelligence(self._page, self._project_context)
                    print(f"[ISOLATION] Navigation intelligence initialized for project: {project_id}", flush=True)

                    # Set AI callback if provided
                    if ai_callback and execution_mode != ExecutionMode.STRICT:
                        self._agent.set_ai_callback(ai_callback)

                    # Set step callback
                    async def on_step(step, status):
                        if self._step_callback:
                            self._step_callback({
                                "step_number": step.step_number,
                                "action": step.action,
                                "status": status,
                                "target": step.target
                            })
                    self._agent.set_callbacks(on_step=on_step)

                    # Navigate to base URL
                    print(f"[ISOLATION] Navigating to base URL: {base_url}", flush=True)
                    await self._page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
                    await self._page.wait_for_timeout(500)
                    print(f"[ISOLATION] Navigation complete, current URL: {self._page.url}", flush=True)

                    self._log(f"[ISOLATION] Fresh context ready, navigated to {base_url}")
                    print(f"[ISOLATION] === FRESH CONTEXT READY ===\n", flush=True)

                except Exception as e:
                    self._log(f"[ISOLATION] Error creating context: {e}")
                    logger.error(f"Failed to create browser context: {e}")
                    # Create failed result and continue to next scenario
                    results.append(UnifiedTestResult(
                        test_id=test_case.id,
                        test_name=test_case.name,
                        format=test_case.format,
                        status="failed",
                        total_steps=len(test_case.steps),
                        passed_steps=0,
                        failed_steps=len(test_case.steps),
                        recovered_steps=0,
                        duration_ms=0,
                        started_at=datetime.utcnow().isoformat(),
                        completed_at=datetime.utcnow().isoformat(),
                        step_results=[],
                        error_message=f"Failed to create browser context: {e}",
                        logs=[f"Context error: {str(e)}"]
                    ))
                    continue

                if self._progress_callback:
                    self._progress_callback({
                        "current": i + 1,
                        "total": len(test_cases),
                        "test_name": test_case.name,
                        "percent": int((i + 1) / len(test_cases) * 100)
                    })

                # ============================================================
                # SCENARIO CACHE: Load pre-cached selectors for this scenario
                # ============================================================
                scenario_id = test_case.id
                scenario_name = test_case.name
                from urllib.parse import urlparse
                domain = urlparse(base_url).netloc

                scenario_cache = self.knowledge_index.get_scenario_cache(
                    scenario_id=scenario_id,
                    scenario_name=scenario_name,
                    domain=domain
                )

                if scenario_cache:
                    self._log(f"[SCENARIO-CACHE] Loaded {len(scenario_cache.selectors)} cached selectors")
                    self._log(f"  Previous runs: {scenario_cache.run_count}, Success rate: {scenario_cache.success_rate:.1%}")
                    # Pass scenario cache to agent for faster lookups
                    self._agent.set_scenario_cache(scenario_cache)
                else:
                    self._log(f"[SCENARIO-CACHE] No cache found, will learn during execution")

                try:
                    self._log(f"Calling agent.execute_test...")
                    result = await self._execute_traditional_batch(
                        test_case,
                        base_url,
                        execution_mode,
                        credentials
                    )
                    self._log(f"Test execution returned: {result.status}")
                    results.append(result)

                    # ============================================================
                    # SCENARIO CACHE: Save learned selectors for next run
                    # ============================================================
                    used_selectors = self._agent.get_used_selectors()
                    if used_selectors:
                        self.knowledge_index.save_scenario_cache(
                            scenario_id=scenario_id,
                            scenario_name=scenario_name,
                            domain=domain,
                            used_selectors=used_selectors,
                            success=(result.status == "passed")
                        )
                        self._log(f"[SCENARIO-CACHE] Saved {len(used_selectors)} selectors to cache")

                    # Aggregate metrics
                    total_ai_calls += result.ai_calls_made
                    total_kb_hits += result.knowledge_base_hits
                    new_selectors += result.selectors_learned

                    # Log result
                    status_emoji = "[OK]" if result.status == "passed" else "[X]"
                    self._log(f"{status_emoji} {test_case.name}: {result.status.upper()}")

                except Exception as e:
                    logger.error(f"Test execution error: {e}")
                    errors.append(f"{test_case.name}: {str(e)}")

                    # Create failed result
                    results.append(UnifiedTestResult(
                        test_id=test_case.id,
                        test_name=test_case.name,
                        format=test_case.format,
                        status="failed",
                        total_steps=len(test_case.steps),
                        passed_steps=0,
                        failed_steps=len(test_case.steps),
                        recovered_steps=0,
                        duration_ms=0,
                        started_at=datetime.utcnow().isoformat(),
                        completed_at=datetime.utcnow().isoformat(),
                        step_results=[],
                        error_message=str(e),
                        logs=[f"Error: {str(e)}"]
                    ))

        except Exception as e:
            logger.error(f"Execution setup error: {e}")
            errors.append(f"Setup error: {str(e)}")

        finally:
            # Cleanup
            await self._cleanup()

        # Calculate summary
        end_time = datetime.utcnow()
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        total = len(results)

        pass_rate = (passed / total * 100) if total > 0 else 0
        ai_dependency = (total_ai_calls / (total_ai_calls + total_kb_hits) * 100) if (total_ai_calls + total_kb_hits) > 0 else 0

        # Flush learnings
        self.learning_engine.flush()

        self._log(f"Execution complete: {passed}/{total} passed ({pass_rate:.1f}%)")
        self._log(f"AI dependency: {ai_dependency:.1f}%, New selectors learned: {new_selectors}")

        # Save execution stats for metrics dashboard
        self._save_execution_stats(total_ai_calls, total_kb_hits)

        return UnifiedExecutionReport(
            id=report_id,
            project_id=project_id,
            project_name=project_name,
            format=test_cases[0].format if test_cases else TestFormat.TRADITIONAL,
            execution_mode=execution_mode,
            executed_at=start_time.isoformat(),
            completed_at=end_time.isoformat(),
            duration_seconds=(end_time - start_time).total_seconds(),
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=pass_rate,
            results=results,
            total_ai_calls=total_ai_calls,
            total_kb_hits=total_kb_hits,
            ai_dependency_percent=ai_dependency,
            new_selectors_learned=new_selectors,
            errors=errors
        )

    def _save_execution_stats(self, ai_calls: int, kb_hits: int):
        """Save execution statistics for metrics tracking"""
        import json
        stats_file = Path(self.data_dir) / "execution_stats.json"

        # Load existing stats or create new
        stats = {
            "total_resolutions": 0,
            "ai_resolutions": 0,
            "kb_resolutions": 0,
            "last_updated": datetime.utcnow().isoformat()
        }

        if stats_file.exists():
            try:
                with open(stats_file) as f:
                    stats = json.load(f)
            except Exception:
                pass

        # Update stats (accumulate over time)
        stats["total_resolutions"] += (ai_calls + kb_hits)
        stats["ai_resolutions"] += ai_calls
        stats["kb_resolutions"] += kb_hits
        stats["last_updated"] = datetime.utcnow().isoformat()

        # Save
        try:
            stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save execution stats: {e}")

    async def _execute_traditional_batch(
        self,
        test_case: UnifiedTestCase,
        base_url: str,
        execution_mode: ExecutionMode,
        credentials: Optional[Dict[str, str]]
    ) -> UnifiedTestResult:
        """Execute a single test case"""
        start_time = datetime.utcnow()
        logs: List[str] = []
        step_results: List[Dict] = []

        # Prepare steps (including background for Gherkin)
        all_steps = []

        # Add background steps for Gherkin
        if test_case.format == TestFormat.GHERKIN and test_case.background_steps:
            all_steps.extend(test_case.background_steps)

        all_steps.extend(test_case.steps)

        self._log(f"Test has {len(all_steps)} steps")
        print(f"\n[DEBUG] ========== STEP CONVERSION ==========", flush=True)
        print(f"[DEBUG] Test format: {test_case.format}", flush=True)
        print(f"[DEBUG] Test name: {test_case.name}", flush=True)
        print(f"[DEBUG] Number of steps: {len(all_steps)}", flush=True)
        for i, s in enumerate(all_steps[:3]):
            print(f"[DEBUG] Step {i}: {s}", flush=True)

        # Convert Gherkin steps to executable actions
        if test_case.format == TestFormat.GHERKIN:
            converted_steps = []
            for step in all_steps:
                if step.get("action") == "gherkin_step":
                    interpreted = self._interpret_gherkin_step(step)
                    # Use AI if pattern matching failed
                    if interpreted.get("requires_ai") or interpreted.get("action") == "gherkin_step":
                        self._log(f"  [AI] Pattern failed, using AI: {step.get('text', '')[:40]}")
                        interpreted = self._interpret_with_ai(step, credentials)
                    interpreted["original_gherkin"] = step
                    converted_steps.append(interpreted)
                else:
                    converted_steps.append(step)
            all_steps = converted_steps

            # ============================================================
            # AUTO-NAVIGATION: If scenario implies a specific page but no
            # navigation step exists, add one at the beginning.
            # This is how a manual tester thinks - "registration test means
            # I need to be on the registration page first"
            # ============================================================
            print(f"\n[DEBUG] ========== AUTO-NAV CHECK ==========", flush=True)
            test_name_lower = (test_case.name or '').lower()
            first_step_action = all_steps[0].get('action', '').lower() if all_steps else ''
            print(f"[DEBUG] Test name lower: '{test_name_lower}'", flush=True)
            print(f"[DEBUG] First step action: '{first_step_action}'", flush=True)
            print(f"[DEBUG] First step full: {all_steps[0] if all_steps else 'NONE'}", flush=True)

            # Check if first step is NOT a navigation/precondition step
            nav_actions = ['navigate', 'goto', 'resolve_precondition', 'smart_navigate']
            needs_auto_nav = first_step_action not in nav_actions
            print(f"[DEBUG] Needs auto nav: {needs_auto_nav}", flush=True)

            if needs_auto_nav:
                # Detect what page we need based on scenario name
                auto_nav_target = None
                if any(kw in test_name_lower for kw in ['register', 'registration', 'signup', 'sign up', 'sign-up', 'create account']):
                    auto_nav_target = 'registration'
                elif any(kw in test_name_lower for kw in ['login', 'log in', 'signin', 'sign in', 'sign-in', 'authenticate']):
                    auto_nav_target = 'login'
                elif any(kw in test_name_lower for kw in ['profile', 'account settings', 'my account']):
                    auto_nav_target = 'profile'
                elif any(kw in test_name_lower for kw in ['dashboard', 'home page', 'main page']):
                    auto_nav_target = 'dashboard'

                if auto_nav_target:
                    print(f"\n[AUTO-NAV] Scenario '{test_case.name}' needs {auto_nav_target} page", flush=True)
                    print(f"[AUTO-NAV] First step is '{first_step_action}' - adding navigation step", flush=True)

                    # Insert navigation step at the beginning
                    nav_step = {
                        'action': 'resolve_precondition',
                        'target': auto_nav_target,
                        'precondition_text': f'Auto-navigate to {auto_nav_target} page',
                        'description': f'Navigate to {auto_nav_target} page (auto-detected from scenario name)'
                    }
                    all_steps.insert(0, nav_step)
                    print(f"[AUTO-NAV] Inserted step: {nav_step}", flush=True)
                    self._log(f"[AUTO-NAV] Added navigation to {auto_nav_target} page")
                else:
                    print(f"[DEBUG] No auto_nav_target detected for: '{test_name_lower}'", flush=True)
        else:
            print(f"[DEBUG] Test format is NOT GHERKIN: {test_case.format}", flush=True)

        # ============================================================
        # SMART DATA RESOLUTION: Registration vs Login
        # ============================================================
        # Registration flows: Generate UNIQUE test data
        # Login flows: Use project credentials
        # ============================================================

        import random
        import string
        import time

        # Detect if this is a REGISTRATION flow based on scenario/test name
        test_name_lower = (test_case.name or '').lower()
        scenario_name_lower = (test_case.scenario_name or '').lower() if hasattr(test_case, 'scenario_name') else ''
        combined_name = f"{test_name_lower} {scenario_name_lower}"

        registration_keywords = ['register', 'registration', 'signup', 'sign up', 'sign-up',
                                 'create account', 'new user', 'new account', 'join']
        login_keywords = ['login', 'log in', 'signin', 'sign in', 'sign-in', 'authenticate']

        is_registration_flow = any(kw in combined_name for kw in registration_keywords)
        is_login_flow = any(kw in combined_name for kw in login_keywords) and not is_registration_flow

        print(f"\n{'='*60}")
        print(f"[DATA-RESOLUTION] ===== STARTING DATA RESOLUTION =====")
        print(f"[FLOW-DETECT] Test: '{test_case.name}'")
        print(f"[FLOW-DETECT] Is Registration: {is_registration_flow}, Is Login: {is_login_flow}")

        # Generate unique test data for this execution
        timestamp = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        unique_id = f"{timestamp}{random_suffix}"

        # First names pool - rotate through these
        first_names = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Quinn', 'Avery', 'Dakota', 'Skyler']
        last_names = ['Smith', 'Johnson', 'Brown', 'Davis', 'Wilson', 'Moore', 'Anderson', 'Thomas', 'Jackson', 'White']

        generated_data = {
            'email': f"testuser{unique_id}@testmail.com",
            'username': f"user{unique_id}",
            'password': f"TestPass{unique_id}!",
            'firstname': random.choice(first_names),
            'lastname': random.choice(last_names),
            'phone': f"555{random.randint(1000000, 9999999)}",
        }

        print(f"[DATA-GEN] Generated unique data: email={generated_data['email']}, user={generated_data['username']}")

        # Extract project credentials for LOGIN flows
        project_username = ''
        project_password = ''
        if credentials:
            if isinstance(credentials, dict):
                project_username = credentials.get('username') or credentials.get('admin_username', '')
                project_password = credentials.get('password') or credentials.get('admin_password', '')
            elif isinstance(credentials, list) and len(credentials) > 0:
                for cred in credentials:
                    if hasattr(cred, 'username'):
                        project_username = cred.username
                        project_password = getattr(cred, 'password', '')
                        break
                    elif isinstance(cred, dict):
                        project_username = cred.get('username', '')
                        project_password = cred.get('password', '')
                        if project_username:
                            break

        project_username = str(project_username) if project_username else ''
        project_password = str(project_password) if project_password else ''

        if is_login_flow and project_username:
            print(f"[CRED-DEBUG] LOGIN flow - using project credentials: {project_username[:3]}***")
        elif is_registration_flow:
            print(f"[CRED-DEBUG] REGISTRATION flow - using generated unique data")
        else:
            print(f"[CRED-DEBUG] Unknown flow - will determine per-field")

        # Process each step for data resolution
        # Track which fields have been filled to detect duplicates
        filled_fields = set()

        for step in all_steps:
            value = step.get('value', '') or ''
            target = (step.get('target', '') or '').lower()
            action = (step.get('action', '') or '').lower()
            original_gherkin = step.get('original_gherkin', {})
            gherkin_text = original_gherkin.get('text', '').lower() if original_gherkin else ''

            search_text = f"{target} {gherkin_text}"

            # For fill/type actions, resolve data
            if action in ('fill', 'type', 'input'):
                value_lower = value.lower() if value else ''
                placeholder_values = ['my', 'the', 'valid', 'test', 'new', 'a', '']

                # Detect if value looks like an HTML attribute, field type, or step description instead of real data
                # These should NEVER be used as actual values - they're field descriptors or action words
                invalid_value_patterns = [
                    'email_address', 'email-address', 'emailaddress', 'mail_address',
                    'auto_complete', 'autocomplete', 'auto-complete',
                    'username_field', 'password_field', 'email_field',
                    'input_email', 'input_password', 'input_username',
                    'text_field', 'form_field', 'field_value',
                    # Action/step description words that should never be values
                    'complete_remaining', 'remaining_fields', 'required_fields',
                    'fill_form', 'complete_form', 'enter_data', 'fill_fields',
                    'valid_email', 'valid_password', 'valid_data',
                    'test_field', 'test_input', 'test_value',
                    'the_form', 'all_fields', 'remaining_required'
                ]
                normalized_value = value_lower.replace(' ', '_').replace('-', '_')
                if value and any(p in normalized_value for p in invalid_value_patterns):
                    print(f"[DATA] WARNING: Value '{value}' looks like a field descriptor, not data! Clearing.")
                    value = ''
                    value_lower = ''
                # Also reject values that look like step descriptions (contain action words)
                action_words = ['complete', 'remaining', 'required', 'enter', 'valid', 'field', 'form']
                if value and sum(1 for w in action_words if w in value_lower) >= 2:
                    print(f"[DATA] WARNING: Value '{value}' looks like step text, not data! Clearing.")
                    value = ''
                    value_lower = ''

                # Email field
                if any(x in search_text for x in ['email', 'e-mail']):
                    if 'email' in filled_fields:
                        print(f"[DATA] WARNING: Duplicate email field detected! Skipping to avoid overwrite.")
                        step['action'] = 'noop'  # Convert to no-op to prevent double-fill
                        step['_skipped_reason'] = 'duplicate_email_field'
                        continue
                    filled_fields.add('email')

                    # DEBUG: Log what value was before we override
                    print(f"[DATA-DEBUG] Email field detected. Current value BEFORE resolution: '{value}'")
                    print(f"[DATA-DEBUG] is_registration_flow={is_registration_flow}, is_login_flow={is_login_flow}")

                    # For REGISTRATION: ALWAYS use generated data (override AI-injected admin creds)
                    # For LOGIN: Use project credentials if available
                    if is_registration_flow:
                        step['value'] = generated_data['email']
                        print(f"[DATA] -> Registration email (forced): {generated_data['email']}")
                    elif is_login_flow and project_username and '@' in project_username:
                        step['value'] = project_username
                        print(f"[DATA] -> Login email: {project_username[:3]}***")
                    elif not value or any(p in value_lower for p in placeholder_values + ['email', 'my email']):
                        step['value'] = generated_data['email']
                        print(f"[DATA] -> Generated email: {generated_data['email']}")

                # Username field (not email)
                elif any(x in search_text for x in ['username', 'user name', 'userid', 'user id', 'login']):
                    # For REGISTRATION: ALWAYS use generated data
                    # For LOGIN: Use project credentials if available
                    if is_registration_flow:
                        step['value'] = generated_data['username']
                        print(f"[DATA] -> Registration username (forced): {generated_data['username']}")
                    elif is_login_flow and project_username:
                        step['value'] = project_username
                        print(f"[DATA] -> Login username: {project_username[:3]}***")
                    elif not value or any(p in value_lower for p in placeholder_values + ['username', 'user']):
                        step['value'] = generated_data['username']
                        print(f"[DATA] -> Generated username: {generated_data['username']}")

                # Password field
                elif any(x in search_text for x in ['password', 'passwd', 'pwd']):
                    # For REGISTRATION: ALWAYS use generated data
                    # For LOGIN: Use project credentials if available
                    if is_registration_flow:
                        step['value'] = generated_data['password']
                        print(f"[DATA] -> Registration password (forced): {generated_data['password'][:4]}***")
                    elif is_login_flow and project_password:
                        step['value'] = project_password
                        print(f"[DATA] -> Login password: ****")
                    elif not value or any(p in value_lower for p in placeholder_values + ['password', 'pass']):
                        step['value'] = generated_data['password']
                        print(f"[DATA] -> Generated password: {generated_data['password'][:4]}***")

                # Confirm password field
                elif any(x in search_text for x in ['confirm', 'repeat', 'retype', 're-enter']):
                    # Always use generated password for registration, project password for login
                    if is_registration_flow:
                        step['value'] = generated_data['password']
                        print(f"[DATA] -> Confirm password (forced): {generated_data['password'][:4]}***")
                    elif is_login_flow and project_password:
                        step['value'] = project_password
                        print(f"[DATA] -> Confirm password (login): ****")
                    else:
                        step['value'] = generated_data['password']
                        print(f"[DATA] -> Confirm password set")

                # First name field
                elif any(x in target for x in ['firstname', 'first', 'fname', 'first name', 'given']):
                    if is_registration_flow or not value or any(p in value_lower for p in placeholder_values + ['name', 'first']):
                        step['value'] = generated_data['firstname']
                        print(f"[DATA] -> First name: {generated_data['firstname']}")

                # Last name field
                elif any(x in target for x in ['lastname', 'last', 'lname', 'last name', 'surname', 'family']):
                    if is_registration_flow or not value or any(p in value_lower for p in placeholder_values + ['name', 'last']):
                        step['value'] = generated_data['lastname']
                        print(f"[DATA] -> Last name: {generated_data['lastname']}")

                # Phone field
                elif any(x in target for x in ['phone', 'mobile', 'tel', 'contact']):
                    if is_registration_flow or not value or any(p in value_lower for p in placeholder_values + ['phone', 'number']):
                        step['value'] = generated_data['phone']
                        print(f"[DATA] -> Phone: {generated_data['phone']}")

        # Log each step for debugging
        for i, step in enumerate(all_steps):
            self._log(f"  Step {i+1}: {step.get('action')} -> {step.get('target', 'N/A')}")

        # ============================================================
        # PRECONDITION RESOLUTION: THINK LIKE A TESTER!
        #
        # A real tester understands:
        # 1. Some pages are PUBLIC (login, register, home) - just navigate
        # 2. Some pages are PROTECTED (dashboard, profile, settings) - LOGIN FIRST!
        #
        # If credentials are available and target is a protected page,
        # we MUST login first before navigating there.
        # ============================================================
        precondition_navigation_done = False

        # Define page types
        PUBLIC_PAGES = ['login', 'register', 'registration', 'signup', 'sign-up', 'home', 'landing', 'forgot-password', 'reset-password']
        PROTECTED_PAGES = ['dashboard', 'profile', 'settings', 'account', 'admin', 'orders', 'cart', 'checkout', 'my-account', 'preferences']

        print(f"\n{'='*60}", flush=True)
        print(f"[TESTER-BRAIN] ===== PRECONDITION RESOLUTION =====", flush=True)
        print(f"[TESTER-BRAIN] Credentials available: {bool(credentials)}", flush=True)
        if credentials:
            uname = credentials.get('username') or credentials.get('admin_username', 'N/A')
            print(f"[TESTER-BRAIN] Username: {uname[:3] if uname else 'N/A'}***", flush=True)

        for i, step in enumerate(all_steps):
            action = step.get('action', '').lower()

            if action == 'resolve_precondition':
                target_page = step.get('target', '').lower()
                precondition_text = step.get('precondition_text', step.get('description', ''))

                self._log(f"[TESTER] Analyzing precondition: '{precondition_text}'")
                self._log(f"[TESTER] Target page: {target_page}")

                # Determine if this is a protected page
                is_protected = any(p in target_page for p in PROTECTED_PAGES)
                is_public = any(p in target_page for p in PUBLIC_PAGES)

                print(f"[TESTER-BRAIN] Page '{target_page}' - Protected: {is_protected}, Public: {is_public}", flush=True)

                try:
                    # ============================================================
                    # PROTECTED PAGE: Login first, then navigate
                    # ============================================================
                    if is_protected and credentials:
                        username = credentials.get('username') or credentials.get('admin_username', '')
                        password = credentials.get('password') or credentials.get('admin_password', '')

                        if username and password:
                            self._log(f"[TESTER] Protected page detected! Logging in first...")
                            print(f"[TESTER-BRAIN] === PERFORMING LOGIN FIRST ===", flush=True)

                            # Step 1: Navigate to login page
                            login_url = f"{base_url.rstrip('/')}/login"
                            self._log(f"[TESTER] Step 1: Navigate to login page: {login_url}")
                            try:
                                await self._page.goto(login_url, wait_until='domcontentloaded', timeout=15000)
                                await asyncio.sleep(1)
                            except Exception as nav_err:
                                for alt in ['/signin', '/auth/login', '/account/login', '/user/login']:
                                    try:
                                        alt_url = f"{base_url.rstrip('/')}{alt}"
                                        await self._page.goto(alt_url, wait_until='domcontentloaded', timeout=10000)
                                        self._log(f"[TESTER] Found login at: {alt_url}")
                                        break
                                    except:
                                        continue

                            # Step 2: Fill username/email field
                            self._log(f"[TESTER] Step 2: Enter username: {username[:3]}***")
                            username_selectors = [
                                'input[name="username"]', 'input[name="email"]', 'input[name="login"]',
                                'input[type="email"]', 'input[type="text"]',
                                '#username', '#email', '#login', '#user',
                                '[data-testid="username"]', '[data-testid="email"]',
                                'input[placeholder*="mail" i]', 'input[placeholder*="user" i]'
                            ]
                            for selector in username_selectors:
                                try:
                                    elem = await self._page.wait_for_selector(selector, timeout=2000)
                                    if elem:
                                        await elem.fill(username)
                                        self._log(f"[TESTER] Username entered in: {selector}")
                                        break
                                except:
                                    continue

                            # Step 3: Fill password field
                            self._log(f"[TESTER] Step 3: Enter password: ****")
                            password_selectors = [
                                'input[name="password"]', 'input[type="password"]',
                                '#password', '[data-testid="password"]'
                            ]
                            for selector in password_selectors:
                                try:
                                    elem = await self._page.wait_for_selector(selector, timeout=2000)
                                    if elem:
                                        await elem.fill(password)
                                        self._log(f"[TESTER] Password entered in: {selector}")
                                        break
                                except:
                                    continue

                            # Step 4: Click login button
                            self._log(f"[TESTER] Step 4: Click login button")
                            login_btn_selectors = [
                                'button[type="submit"]', 'input[type="submit"]',
                                'button:has-text("Login")', 'button:has-text("Sign in")',
                                'button:has-text("Log in")', 'button:has-text("Submit")',
                                '[data-testid="login-button"]', '[data-testid="submit"]',
                                '#login-button', '#submit', '.login-btn', '.submit-btn'
                            ]
                            for selector in login_btn_selectors:
                                try:
                                    elem = await self._page.wait_for_selector(selector, timeout=2000)
                                    if elem:
                                        await elem.click()
                                        self._log(f"[TESTER] Clicked login button: {selector}")
                                        break
                                except:
                                    continue

                            # Step 5: Wait for login to complete
                            self._log(f"[TESTER] Step 5: Waiting for login to complete...")
                            await asyncio.sleep(2)

                            current_url = self._page.url
                            self._log(f"[TESTER] Current URL after login: {current_url}")

                            # Step 6: Navigate to target page
                            target_url = f"{base_url.rstrip('/')}/{target_page}"
                            self._log(f"[TESTER] Step 6: Navigate to target: {target_url}")
                            try:
                                await self._page.goto(target_url, wait_until='domcontentloaded', timeout=15000)
                                await asyncio.sleep(1)
                                self._log(f"[TESTER] SUCCESS - Logged in and navigated to {target_page}")
                                step['action'] = 'noop'
                                step['description'] = f"Logged in and navigated to {target_page} page"
                                precondition_navigation_done = True
                            except Exception as e:
                                self._log(f"[TESTER] Navigation to {target_page} failed: {e}")
                        else:
                            self._log(f"[TESTER] WARNING: Protected page but no credentials!")

                    # ============================================================
                    # PUBLIC PAGE: Just navigate directly
                    # ============================================================
                    elif is_public or not is_protected:
                        self._log(f"[TESTER] Public page - navigating directly")
                        target_url = f"{base_url.rstrip('/')}/{target_page}"
                        try:
                            await self._page.goto(target_url, wait_until='domcontentloaded', timeout=15000)
                            await asyncio.sleep(1)
                            self._log(f"[TESTER] SUCCESS - navigated to {target_page}")
                            step['action'] = 'noop'
                            step['description'] = f"Navigated to {target_page} page"
                            precondition_navigation_done = True
                        except Exception as e:
                            self._log(f"[TESTER] Direct navigation failed: {e}")
                            if self._nav_intelligence:
                                nav_result = await self._nav_intelligence.navigate_to(target_page)
                                if nav_result.success:
                                    step['action'] = 'noop'
                                    precondition_navigation_done = True

                except Exception as e:
                    self._log(f"[TESTER] Precondition error: {e}")
                    step['action'] = 'noop'
                    step['error_message'] = str(e)

        print(f"[TESTER-BRAIN] Precondition resolution complete", flush=True)
        print(f"{'='*60}\n", flush=True)

        # Build agent-compatible test case
        agent_test = {
            "id": test_case.id,
            "name": test_case.name,
            "steps": all_steps
        }

        # Execute with agent
        # If we already navigated via precondition, tell agent to skip initial navigation
        self._log(f"[EXEC] Precondition navigation done: {precondition_navigation_done}")
        try:
            agent_result = await self._agent.execute_test(
                agent_test,
                base_url=base_url,
                skip_initial_navigation=precondition_navigation_done
            )
        except Exception as e:
            self._log(f"Agent execution error: {str(e)}", "error")
            # Return a failed result
            return UnifiedTestResult(
                test_id=test_case.id,
                test_name=test_case.name,
                format=test_case.format,
                status="failed",
                total_steps=len(all_steps),
                passed_steps=0,
                failed_steps=len(all_steps),
                recovered_steps=0,
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                started_at=start_time.isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                step_results=[],
                error_message=str(e),
                logs=[f"Execution error: {str(e)}"]
            )

        # Convert step results
        for step in agent_result.steps:
            # Build descriptive step name
            step_desc = self._build_step_description(step)

            step_results.append({
                "step_number": step.step_number,
                "action": step.action,
                "target": step.target,
                "description": step_desc,
                "status": step.status.value,
                "selector_used": step.selector_used,
                "selector_tier": step.selector_tier,
                "execution_time_ms": step.execution_time_ms,
                "error_message": step.error_message,
                "recovery_attempts": step.recovery_attempts
            })

            # Log with descriptive step name
            logs.append(f"Step {step.step_number}: {step_desc} - {step.status.value}")

        # Collect training data
        if self._collect_training_data:
            self._record_training_data(test_case, agent_result)

        # UPDATE GHERKIN: If agent discovered missing fields, update the Gherkin file
        await self._update_gherkin_with_discovered_steps(test_case)

        # Get agent stats
        agent_stats = self._agent.get_stats()

        end_time = datetime.utcnow()

        return UnifiedTestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            format=test_case.format,
            status=agent_result.status,
            total_steps=agent_result.total_steps,
            passed_steps=agent_result.passed_steps,
            failed_steps=agent_result.failed_steps,
            recovered_steps=agent_result.recovered_steps,
            duration_ms=agent_result.execution_time_ms,
            started_at=start_time.isoformat(),
            completed_at=end_time.isoformat(),
            step_results=step_results,
            error_message=agent_result.errors[0] if agent_result.errors else None,
            logs=logs,
            screenshot_path=agent_result.screenshots[0] if agent_result.screenshots else None,
            ai_calls_made=agent_stats.get("ai_calls", 0),
            knowledge_base_hits=agent_stats.get("knowledge_base_hits", 0),
            selectors_learned=0,  # Will be updated by learning engine
            is_spa=agent_stats.get("is_spa", False),
            spa_framework=agent_stats.get("spa_framework")
        )

    async def _quick_explore(self, base_url: str):
        """Quick exploration to build initial knowledge"""
        try:
            self._log("Starting quick exploration...")

            # Add a timeout to prevent hanging
            try:
                await asyncio.wait_for(
                    self._do_quick_explore(base_url),
                    timeout=15.0  # 15 second max for exploration
                )
                self._log("Quick exploration completed")
            except asyncio.TimeoutError:
                self._log("Quick exploration timed out (15s) - continuing with tests")
                logger.warning("Quick exploration timed out after 15 seconds")

        except Exception as e:
            self._log(f"Quick exploration failed: {str(e)[:100]}")
            logger.warning(f"Quick exploration failed: {e}")

    async def _do_quick_explore(self, base_url: str):
        """Internal quick exploration with proper async handling"""
        try:
            explorer = ApplicationExplorer(
                knowledge_index=self.knowledge_index,
                learning_engine=self.learning_engine
            )

            # Set browser callbacks - use async-compatible methods
            async def navigate_fn(url):
                return await self._page.goto(url)

            async def get_html_fn():
                return await self._page.content()

            async def get_dom_fn():
                return await self._page.evaluate("""
                    () => Array.from(document.querySelectorAll('*')).slice(0, 100).map(el => ({
                        tagName: el.tagName,
                        attributes: Object.fromEntries(Array.from(el.attributes).map(a => [a.name, a.value])),
                        textContent: el.textContent?.substring(0, 100)
                    }))
                """)

            explorer.set_browser_callbacks(
                navigate=navigate_fn,
                get_html=get_html_fn,
                get_dom=get_dom_fn
            )

            # Quick scan - just the starting page
            await explorer.quick_scan(base_url)

        except Exception as e:
            logger.warning(f"Quick exploration internal error: {e}")

    def _record_training_data(self, test_case: UnifiedTestCase, result: TestResult):
        """Record test execution as training data"""
        training_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_id": test_case.id,
            "test_name": test_case.name,
            "format": test_case.format.value,
            "status": result.status,
            "steps": [
                {
                    "action": step.action,
                    "target": step.target,
                    "selector_used": step.selector_used,
                    "status": step.status.value,
                    "recovery_attempts": step.recovery_attempts
                }
                for step in result.steps
            ]
        }

        self._training_data.append(training_entry)

        # Save periodically
        if len(self._training_data) >= 10:
            self._save_training_data()

    def _save_training_data(self):
        """Save collected training data"""
        if not self._training_data:
            return

        training_dir = self.data_dir / "training"
        training_dir.mkdir(parents=True, exist_ok=True)

        filename = f"training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(training_dir / filename, 'w') as f:
            json.dump(self._training_data, f, indent=2)

        self._training_data.clear()

    async def _cleanup(self):
        """Cleanup resources - each step runs independently to ensure all cleanup happens"""
        self._log("Cleaning up browser and resources...")

        # Cleanup agent
        if self._agent:
            try:
                await self._agent.cleanup()
            except Exception as e:
                logger.warning(f"Agent cleanup error: {e}")
            finally:
                self._agent = None

        # Close page
        if self._page:
            try:
                await self._page.close()
            except Exception as e:
                logger.warning(f"Page close error: {e}")
            finally:
                self._page = None

        # Close browser
        if self._browser:
            try:
                await self._browser.close()
                self._log("Browser closed")
            except Exception as e:
                logger.warning(f"Browser close error: {e}")
            finally:
                self._browser = None

        # Stop playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning(f"Playwright stop error: {e}")
            finally:
                self._playwright = None

        # Save any remaining training data
        self._save_training_data()

    # ==================== Convenience Methods ====================

    async def execute_traditional_tests(
        self,
        test_cases: List[Dict[str, Any]],
        base_url: str,
        project_id: str,
        project_name: str,
        **kwargs
    ) -> UnifiedExecutionReport:
        """Execute traditional action-based tests"""
        unified_tests = [self.convert_traditional_test(tc) for tc in test_cases]
        return await self.execute(unified_tests, base_url, project_id, project_name, **kwargs)

    async def execute_gherkin_feature(
        self,
        feature: Dict[str, Any],
        base_url: str,
        project_id: str,
        project_name: str,
        scenario_filter: Optional[List[str]] = None,
        tag_filter: Optional[List[str]] = None,
        **kwargs
    ) -> UnifiedExecutionReport:
        """Execute a Gherkin feature file"""

        # ============================================================
        # PRE-EXECUTION: Analyze and optimize feature structure
        # Like a tester would: check for missing Background, common steps
        # ============================================================
        feature_id = feature.get("id")
        if feature_id:
            await self._optimize_feature_structure(feature_id, feature)

        # Convert all scenarios
        unified_tests = self.convert_gherkin_feature(feature)

        # Apply filters
        if scenario_filter:
            unified_tests = [t for t in unified_tests if t.scenario_name in scenario_filter]
        if tag_filter:
            unified_tests = [t for t in unified_tests if any(tag in t.tags for tag in tag_filter)]

        return await self.execute(unified_tests, base_url, project_id, project_name, **kwargs)

    async def _optimize_feature_structure(self, feature_id: str, feature: Dict[str, Any]):
        """
        Optimize feature structure before execution.

        Like an experienced tester would:
        1. Check if Background is missing
        2. Analyze scenarios for common steps
        3. Create Background from common steps
        4. Use KB to suggest missing setup steps
        """
        try:
            from gherkin_storage import get_gherkin_storage
            gherkin_storage = get_gherkin_storage()

            background = feature.get("background", [])
            scenarios = feature.get("scenarios", [])

            self._log(f"[OPTIMIZE] Analyzing feature structure...")
            self._log(f"  - Background steps: {len(background)}")
            self._log(f"  - Scenarios: {len(scenarios)}")

            # Check 1: If no Background and multiple scenarios, try to create one
            if not background and len(scenarios) >= 2:
                self._log(f"[OPTIMIZE] No Background found, analyzing scenarios for common steps...")

                created = gherkin_storage.analyze_and_create_background(feature_id)
                if created:
                    self._log(f"[OPTIMIZE] Background created from common scenario steps!")
                    # Reload feature to get updated structure
                    updated_feature = gherkin_storage.load_feature_dict(feature_id)
                    if updated_feature:
                        feature.update(updated_feature)
                else:
                    self._log(f"[OPTIMIZE] No common steps found for Background")

            # Check 2: Suggest additional Background steps from KB
            suggestions = gherkin_storage.suggest_background_from_kb(feature_id)
            if suggestions:
                self._log(f"[OPTIMIZE] KB suggests {len(suggestions)} additional setup step(s):")
                for s in suggestions:
                    self._log(f"  - {s.get('keyword')} {s.get('text')}")
                # Note: We log suggestions but don't auto-add them (user should review)

        except Exception as e:
            self._log(f"[OPTIMIZE] Feature optimization skipped: {e}")
            logger.debug(f"Feature optimization error: {e}")

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get current learning statistics"""
        return self.learning_engine.get_learning_summary()

    def export_knowledge(self, output_file: str, domain: Optional[str] = None):
        """Export learned knowledge"""
        self.learning_engine.export_learnings(output_file, domain)

    def import_knowledge(self, input_file: str):
        """Import knowledge from file"""
        self.learning_engine.import_learnings(input_file, merge=True)

    async def _update_gherkin_with_discovered_steps(self, test_case: UnifiedTestCase):
        """
        Update the Gherkin file with steps discovered during execution.

        If the agent discovered missing fields (like confirm password) and filled them,
        add those as steps to the Gherkin so future runs don't need AI.
        """
        try:
            # Get discovered fields from the agent
            discovered_fields = self._agent.get_discovered_fields()

            if not discovered_fields:
                return  # Nothing to update

            # Get feature_id and scenario_name from test case
            original_data = getattr(test_case, 'original_data', None)
            if not original_data:
                self._log("[GHERKIN-UPDATE] No original data, skipping Gherkin update")
                return

            feature_data = original_data.get('feature', {})
            feature_id = feature_data.get('id')
            scenario_name = test_case.scenario_name

            if not feature_id or not scenario_name:
                self._log(f"[GHERKIN-UPDATE] Missing feature_id ({feature_id}) or scenario_name ({scenario_name})")
                return

            # Convert discovered fields to Gherkin steps
            gherkin_steps = []
            for field in discovered_fields:
                field_name = field.get('field_name', 'unknown')
                value_type = field.get('value_type', 'text')

                # Create appropriate Gherkin step text
                if value_type == 'password':
                    if 'confirm' in field_name.lower():
                        step_text = f'I enter my password again in the "{field_name}" field'
                    else:
                        step_text = f'I enter my password in the "{field_name}" field'
                elif value_type == 'email':
                    step_text = f'I enter my email in the "{field_name}" field'
                elif value_type == 'username':
                    step_text = f'I enter my username in the "{field_name}" field'
                elif value_type == 'firstname':
                    step_text = f'I enter my first name in the "{field_name}" field'
                elif value_type == 'lastname':
                    step_text = f'I enter my last name in the "{field_name}" field'
                elif value_type == 'phone':
                    step_text = f'I enter my phone number in the "{field_name}" field'
                else:
                    step_text = f'I fill in the "{field_name}" field'

                gherkin_steps.append({
                    "keyword": "And",
                    "text": step_text,
                    "field_name": field_name  # For smart duplicate detection
                })

            if gherkin_steps:
                # Update the Gherkin file
                from gherkin_storage import get_gherkin_storage
                gherkin_storage = get_gherkin_storage()

                success = gherkin_storage.add_discovered_steps_to_scenario(
                    feature_id=feature_id,
                    scenario_name=scenario_name,
                    discovered_steps=gherkin_steps,
                    insert_before_step_keyword="When"
                )

                if success:
                    self._log(f"[GHERKIN-UPDATE] Added {len(gherkin_steps)} discovered step(s) to '{scenario_name}'")
                    for step in gherkin_steps:
                        self._log(f"  + {step['keyword']} {step['text']}")

            # Clear discovered fields after processing
            self._agent.clear_discovered_fields()

        except Exception as e:
            self._log(f"[GHERKIN-UPDATE] Error updating Gherkin: {e}")
            logger.warning(f"Failed to update Gherkin with discovered steps: {e}")
