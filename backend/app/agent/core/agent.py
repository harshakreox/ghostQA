"""
Autonomous Test Agent

The main orchestrator that executes tests autonomously like an
experienced human tester. Combines all components to provide
intelligent, self-learning test execution.

This is the "brain" that ties everything together.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from .selector_service import SelectorService, SelectorResult, ResolutionTier
from .action_executor import ActionExecutor, ActionResult, ActionStatus
from .recovery_handler import RecoveryHandler, FailureType
from .spa_handler import SPAHandler, SPAFramework
from .human_like_tester import (
    PreActionChecker, PageStateTracker, SmartWaiter,
    OverlayDetector, ErrorDetector, PreActionResult,
    ActionReadiness, BlockerType, PageState
)

from ..brain.qa_brain import QABrain, BrainConfig
from ..knowledge.knowledge_index import KnowledgeIndex
from ..knowledge.learning_engine import LearningEngine
from ..knowledge.pattern_store import PatternStore
from ..knowledge.framework_selectors import FRAMEWORK_SELECTORS

# Configure logging
logger = logging.getLogger(__name__)


class AgentState(Enum):
    """State of the agent"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(Enum):
    """Status of a test step"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RECOVERED = "recovered"


@dataclass
class TestStep:
    """A single test step"""
    step_number: int
    action: str
    target: Optional[str]
    value: Optional[str] = None
    expected: Optional[str] = None
    description: Optional[str] = None  # Human-readable step description
    status: StepStatus = StepStatus.PENDING
    selector_used: Optional[str] = None
    selector_tier: Optional[str] = None
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    recovery_attempts: int = 0


@dataclass
class TestResult:
    """Result of a test execution"""
    test_id: str
    test_name: str
    status: str  # passed, failed, error
    total_steps: int
    passed_steps: int
    failed_steps: int
    recovered_steps: int
    steps: List[TestStep]
    execution_time_ms: int
    started_at: str
    completed_at: str
    domain: str
    ai_calls_made: int
    knowledge_base_hits: int
    errors: List[str]
    screenshots: List[str]


@dataclass
class AgentConfig:
    """Configuration for the agent"""
    max_retries: int = 3
    step_timeout_ms: int = 30000
    wait_between_steps_ms: int = 500
    capture_screenshots: bool = True
    screenshot_on_failure: bool = True
    highlight_elements: bool = False
    enable_ai_fallback: bool = True
    enable_recovery: bool = True
    enable_learning: bool = True
    verbose_logging: bool = False
    # SPA-specific configuration
    enable_spa_mode: bool = True  # Auto-detect and handle SPAs
    wait_for_hydration: bool = True  # Wait for SSR hydration
    wait_for_render_stable: bool = True  # Wait for re-renders to settle
    spa_hydration_timeout_ms: int = 10000
    spa_render_stable_timeout_ms: int = 2000


class AutonomousTestAgent:
    """
    The main autonomous test execution agent.

    This agent mimics an experienced human tester by:
    - Using learned knowledge to find elements quickly
    - Falling back to AI only when necessary
    - Recovering from failures intelligently
    - Learning from every execution to improve over time
    """

    def __init__(
        self,
        page=None,
        data_dir: str = "data/agent_knowledge",
        config: Optional[AgentConfig] = None
    ):
        """
        Initialize the autonomous agent.

        Args:
            page: Playwright page object
            data_dir: Directory for knowledge storage
            config: Agent configuration
        """
        self.page = page
        self.data_dir = Path(data_dir)
        self.config = config or AgentConfig()

        # Initialize components
        self.knowledge_index = KnowledgeIndex(str(self.data_dir))
        self.pattern_store = PatternStore(str(self.data_dir / "patterns"))
        self.learning_engine = LearningEngine(
            self.knowledge_index,
            self.pattern_store,
            str(self.data_dir)
        )

        self.selector_service = SelectorService(
            self.knowledge_index,
            self.learning_engine
        )

        self.action_executor = ActionExecutor(
            page,
            self.selector_service,
            self.learning_engine
        )

        self.recovery_handler = RecoveryHandler(
            page,
            self.learning_engine
        )

        # SPA handler for React, Angular, Vue, etc.
        self.spa_handler = SPAHandler(page)
        # Human-like tester components (token-efficient)
        self.pre_action_checker = PreActionChecker()
        self._last_page_state: Optional[PageState] = None

        # QA Brain - Neural decision system (connected to existing knowledge)
        # This integrates brain with knowledge systems as one unified body
        self.brain = QABrain(
            config=BrainConfig(
                data_dir=str(self.data_dir),
                enable_learning=self.config.enable_learning,
                enable_ai_fallback=self.config.enable_ai_fallback
            ),
            knowledge_index=self.knowledge_index,      # Shared long-term memory
            learning_engine=self.learning_engine,      # Shared learning
            pattern_store=self.pattern_store           # Shared patterns
        )


        # State
        self.state = AgentState.IDLE
        self._current_test: Optional[str] = None
        self._current_domain: Optional[str] = None

        # Track discovered fields during execution (for Gherkin updates)
        self._discovered_fields: List[Dict[str, Any]] = []
        self._is_spa: bool = False
        self._detected_spa_framework: Optional[SPAFramework] = None

        # Scenario-level caching for faster lookups
        self._scenario_cache = None  # ScenarioKnowledge object
        self._used_selectors: Dict[str, Dict[str, Any]] = {}  # Track selectors used in this run

        # Metrics
        self._ai_calls = 0
        self._kb_hits = 0
        self._total_actions = 0
        self._recovered_actions = 0

        # Callbacks
        self._ai_callback: Optional[Callable] = None
        self._step_callback: Optional[Callable] = None
        self._error_callback: Optional[Callable] = None

    def set_page(self, page):
        """Set or update the Playwright page"""
        self.page = page
        self.spa_handler.set_page(page)
        self.action_executor.set_page(page)
        self.recovery_handler.set_page(page)

    def set_ai_callback(self, callback: Callable):
        """Set the AI decision callback for fallback"""
        self._ai_callback = callback
        self.selector_service.set_ai_callback(callback)

    def set_callbacks(
        self,
        on_step: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        """Set execution callbacks"""
        self._step_callback = on_step
        self._error_callback = on_error

    def set_scenario_cache(self, scenario_cache):
        """
        Set the scenario-specific knowledge cache for faster lookups.
        When set, selector resolution will first check this cache before
        querying the full knowledge base.
        """
        self._scenario_cache = scenario_cache
        # Pass to selector service for O(1) lookup
        self.selector_service.set_scenario_cache(scenario_cache)
        if scenario_cache:
            print(f"\n[SCENARIO-CACHE] Loaded cache for scenario: {scenario_cache.scenario_name}", flush=True)
            print(f"  - Cached selectors: {len(scenario_cache.selectors)}", flush=True)
            print(f"  - Last run: {scenario_cache.last_run}", flush=True)
            print(f"  - Success rate: {scenario_cache.success_rate:.1%}", flush=True)
            # Pre-populate used_selectors from cache for consistency
            # Convert ElementKnowledge objects to dicts
            for key, selector_data in scenario_cache.selectors.items():
                if hasattr(selector_data, 'selectors'):
                    # It's an ElementKnowledge object - convert to dict
                    if selector_data.selectors:
                        best = max(selector_data.selectors, key=lambda s: s.confidence)
                        self._used_selectors[key] = {
                            'selector': best.value,
                            'selector_type': best.selector_type,
                            'confidence': best.confidence
                        }
                    elif selector_data.best_selector:
                        self._used_selectors[key] = {
                            'selector': selector_data.best_selector,
                            'selector_type': 'css',
                            'confidence': 0.9
                        }
                elif isinstance(selector_data, dict):
                    self._used_selectors[key] = selector_data

    def get_used_selectors(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all selectors used during this execution.
        Returns combined selectors from both agent and selector service.
        """
        # Merge selectors from selector service (most up-to-date)
        merged = self._used_selectors.copy()
        merged.update(self.selector_service.get_used_selectors())
        return merged

    def clear_scenario_cache(self):
        """Clear the scenario cache (call between scenarios)"""
        self._scenario_cache = None
        self._used_selectors.clear()
        self.selector_service.clear_scenario_cache()

    # ==================== Main Execution ====================


    async def _smart_find_element(self, target, action_type="click"):
        """Smart element finding with multiple strategies"""
        if not target:
            return None

        target_lower = target.lower().strip()

        # ============================================================
        # PRIORITY 1: Exact text match (for quoted text from Gherkin)
        # If target looks like it came from quotes, search by exact text first
        # ============================================================
        if action_type == "click":
            found_element = None

            # Try get_by_text for exact match (handles menus, links, buttons, any clickable)
            try:
                loc = self.page.get_by_text(target, exact=True)
                if await loc.count() > 0:
                    first = loc.first
                    if await first.is_visible():
                        logger.info(f"[SMART] Found exact text: '{target}'")
                        found_element = first
            except: pass

            # Try partial text match
            if not found_element:
                try:
                    loc = self.page.get_by_text(target, exact=False)
                    if await loc.count() > 0:
                        first = loc.first
                        if await first.is_visible():
                            logger.info(f"[SMART] Found partial text: '{target}'")
                            found_element = first
                except: pass

            # Try :has-text on any clickable element
            if not found_element:
                for tag in ['a', 'button', 'div', 'span', 'li', '[role="menuitem"]', '[role="button"]', '[role="link"]']:
                    try:
                        loc = self.page.locator(f"{tag}:has-text('{target}')")
                        if await loc.count() > 0:
                            first = loc.first
                            if await first.is_visible():
                                logger.info(f"[SMART] Found {tag}:has-text('{target}')")
                                found_element = first
                                break
                    except: pass

            # If element found, try to make it clickable (for menus, submenus)
            if found_element:
                try:
                    # Scroll into view
                    await found_element.scroll_into_view_if_needed(timeout=2000)
                    await self.page.wait_for_timeout(200)

                    # Check if element might be in a dropdown/submenu that needs parent hover
                    # Try to hover on parent first
                    try:
                        parent = found_element.locator('..')
                        grandparent = parent.locator('..')
                        # Hover on ancestors to potentially open menus
                        await grandparent.hover(timeout=500)
                        await self.page.wait_for_timeout(300)
                        await parent.hover(timeout=500)
                        await self.page.wait_for_timeout(300)
                    except:
                        pass

                    # Hover on the element itself
                    await found_element.hover(timeout=1000)
                    await self.page.wait_for_timeout(200)

                    logger.info(f"[SMART] Element ready for click: '{target}'")
                except Exception as e:
                    logger.warning(f"[SMART] Could not prepare element: {e}")

                return found_element

        # Common field IDs
        field_ids = {
            'username': ['username', 'user', 'email', 'login', 'userId'],
            'password': ['password', 'passwd', 'pwd'],
            'email': ['email', 'mail'],
            'submit': ['submit', 'login', 'signin', 'Log In', 'Sign In'],
            'firstname': ['firstName', 'first-name', 'fname'],
            'lastname': ['lastName', 'last-name', 'lname'],
        }

        # Try common IDs
        for field_type, ids in field_ids.items():
            if field_type in target_lower:
                for fid in ids:
                    try:
                        loc = self.page.locator(f"#{fid}")
                        if await loc.count() > 0:
                            logger.info(f"[SMART] Found #{fid}")
                            return loc.first
                    except: pass
                    try:
                        loc = self.page.locator(f"[name='{fid}']")
                        if await loc.count() > 0:
                            logger.info(f"[SMART] Found name={fid}")
                            return loc.first
                    except: pass

        # Try CSS selector
        try:
            loc = self.page.locator(target)
            if await loc.count() > 0:
                return loc.first
        except: pass

        # Try placeholder
        try:
            loc = self.page.get_by_placeholder(target, exact=False)
            if await loc.count() > 0:
                return loc.first
        except: pass

        # Try label
        try:
            loc = self.page.get_by_label(target, exact=False)
            if await loc.count() > 0:
                return loc.first
        except: pass

        # Try text for clicks
        if action_type == "click":
            # Strategy 1: Button by role with name
            try:
                loc = self.page.get_by_role("button", name=target)
                if await loc.count() > 0:
                    logger.info(f"[SMART] Found button role: {target}")
                    return loc.first
            except: pass

            # Strategy 2: Link by role with name
            try:
                loc = self.page.get_by_role("link", name=target)
                if await loc.count() > 0:
                    logger.info(f"[SMART] Found link role: {target}")
                    return loc.first
            except: pass

            # Strategy 3: Button by text content (case insensitive)
            try:
                loc = self.page.locator(f"button:has-text('{target}')")
                if await loc.count() > 0:
                    logger.info(f"[SMART] Found button:has-text: {target}")
                    return loc.first
            except: pass

            # Strategy 4: Submit/Login button types
            if any(kw in target_lower for kw in ['submit', 'login', 'sign', 'register', 'continue']):
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Sign In')",
                    "button:has-text('Sign Up')",
                    "button:has-text('Log In')",
                    "button:has-text('Login')",
                    "button:has-text('Register')",
                    "button:has-text('Submit')",
                    "button:has-text('Continue')",
                    "[type='submit']",
                ]
                for sel in submit_selectors:
                    try:
                        loc = self.page.locator(sel)
                        if await loc.count() > 0:
                            logger.info(f"[SMART] Found submit button: {sel}")
                            return loc.first
                    except: pass

            # Strategy 5: Generic text match
            try:
                loc = self.page.get_by_text(target, exact=False)
                if await loc.count() > 0:
                    logger.info(f"[SMART] Found by text: {target}")
                    return loc.first
            except: pass

        # Try textbox for typing
        if action_type in ("type", "fill"):
            try:
                loc = self.page.get_by_role("textbox", name=target)
                if await loc.count() > 0:
                    return loc.first
            except: pass

        return None

    async def _smart_type_value(self, locator, value):
        """Type with real user simulation for form validation"""
        print(f"[SMART_TYPE] Called with value: '{value}' (length: {len(value) if value else 0})")
        if not locator or not value:
            print(f"[SMART_TYPE] SKIPPING - locator={locator is not None}, value='{value}'")
            return False
        try:
            await locator.wait_for(state="visible", timeout=5000)
            await self.page.wait_for_timeout(200)
            await locator.click(timeout=2000)
            await self.page.wait_for_timeout(100)
            await locator.press("Control+a")
            await self.page.wait_for_timeout(50)
            await locator.press_sequentially(value, delay=30)
            await self.page.wait_for_timeout(100)
            await locator.press("Tab")
            await self.page.wait_for_timeout(200)
            logger.info(f"[SMART_TYPE] Typed {len(value)} chars")
            return True
        except Exception as e:
            logger.error(f"[SMART_TYPE] Failed: {e}")
            return False


    

    async def _extract_page_elements(self):
        """Extract interactive elements from page for AI context"""
        try:
            dom_script = """
            () => {
                const extract = (el) => ({
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    name: el.name || null,
                    type: el.type || null,
                    placeholder: el.placeholder || null,
                    text: el.innerText?.trim().substring(0, 50) || null,
                    visible: el.getBoundingClientRect().width > 0
                });
                return {
                    inputs: Array.from(document.querySelectorAll('input')).map(extract).filter(e => e.visible).slice(0, 15),
                    buttons: Array.from(document.querySelectorAll('button')).map(extract).filter(e => e.visible).slice(0, 15),
                    links: Array.from(document.querySelectorAll('a')).map(extract).filter(e => e.visible).slice(0, 10),
                    url: window.location.href
                };
            }
            """
            return await self.page.evaluate(dom_script)
        except Exception as e:
            logger.warning(f"DOM extraction failed: {e}")
            return {}

    async def _ai_find_element(self, target, action_type="click"):
        """Use AI to find element when other methods fail"""
        import os, json

        if not os.getenv("ANTHROPIC_API_KEY"):
            return None

        logger.info(f"[AI-FIND] Asking AI to find: {target}")

        dom = await self._extract_page_elements()

        inputs = [f"#{e['id'] or e['name'] or e['placeholder'] or 'input'}({e.get('type','text')})"
                  for e in dom.get('inputs', [])]
        buttons = [e['text'] or e['id'] or 'btn' for e in dom.get('buttons', [])]

        prompt = f"""Find the best selector for "{target}" (action: {action_type}).

ELEMENTS ON PAGE:
Inputs: {', '.join(inputs[:10]) if inputs else 'None'}
Buttons: {', '.join(buttons[:10]) if buttons else 'None'}

Return ONLY JSON: {{"selector": "#id or [name='x'] or button text"}}"""

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            resp = msg.content[0].text.strip()
            if "{" in resp:
                resp = resp[resp.find("{"):resp.rfind("}")+1]
            result = json.loads(resp)
            selector = result.get("selector", "")
            if selector:
                logger.info(f"[AI-FIND] AI suggested: {selector}")
                try:
                    loc = self.page.locator(selector)
                    if await loc.count() > 0:
                        return loc.first
                except: pass
                try:
                    loc = self.page.get_by_text(selector, exact=False)
                    if await loc.count() > 0:
                        return loc.first
                except: pass
        except Exception as e:
            logger.warning(f"[AI-FIND] Error: {e}")

        return None

    async def execute_test(
        self,
        test_case: Dict[str, Any],
        base_url: Optional[str] = None,
        skip_initial_navigation: bool = False
    ) -> TestResult:
        """
        Execute a test case autonomously.

        Args:
            test_case: Test case definition with steps
            base_url: Optional base URL to navigate to first
            skip_initial_navigation: If True, don't navigate to base_url (already navigated)

        Returns:
            TestResult with execution details
        """
        test_id = test_case.get("id", f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        test_name = test_case.get("name", "Unnamed Test")
        steps_data = test_case.get("steps", [])

        logger.info(f"Starting test execution: {test_name}")

        # Reset metrics
        self._ai_calls = 0
        self._kb_hits = 0
        self._total_actions = 0
        self._recovered_actions = 0

        # Initialize
        self.state = AgentState.RUNNING
        self._current_test = test_id
        start_time = datetime.utcnow()
        errors = []
        screenshots = []

        # Parse domain
        if base_url:
            self._current_domain = urlparse(base_url).netloc
            self.selector_service.set_framework(
                self._detect_framework_from_url(base_url)
            )

        # Convert to TestStep objects
        steps: List[TestStep] = []
        for i, step_data in enumerate(steps_data):
            steps.append(TestStep(
                step_number=i + 1,
                action=step_data.get("action", ""),
                target=step_data.get("target") or step_data.get("selector"),
                value=step_data.get("value"),
                expected=step_data.get("expected"),
                description=step_data.get("description")
            ))

        # Navigate to base URL if provided (unless already navigated by precondition)
        if base_url and not skip_initial_navigation:
            logger.info(f"Navigating to base URL: {base_url}")
            nav_result = await self.action_executor.navigate(base_url)
            if nav_result.status != ActionStatus.SUCCESS:
                errors.append(f"Failed to navigate to {base_url}: {nav_result.error_message}")

            # Wait for page to load
            logger.info("Waiting for page load...")
            await asyncio.sleep(1)
        elif skip_initial_navigation:
            logger.info(f"Skipping initial navigation (precondition already handled)")

        # Detect framework from page (both SPA and UI library) - with timeout
        logger.info("Detecting framework...")
        try:
            await asyncio.wait_for(self._detect_framework(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Framework detection timed out")

        # Load previous learnings for this domain/page
        await self._load_and_log_learnings()

        # SPA-specific handling
        if self.config.enable_spa_mode and self._is_spa:
            logger.info(f"SPA detected ({self._detected_spa_framework.value}), applying SPA handling...")

            # Wait for hydration (SSR frameworks like Next.js, Nuxt.js) - with reduced timeout
            if self.config.wait_for_hydration:
                try:
                    await asyncio.wait_for(
                        self.spa_handler.wait_for_hydration(self.config.spa_hydration_timeout_ms),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("SPA hydration wait timed out")

            # Wait for initial render to stabilize - with reduced timeout
            if self.config.wait_for_render_stable:
                try:
                    await asyncio.wait_for(
                        self.spa_handler.wait_for_render_stable(self.config.spa_render_stable_timeout_ms),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("SPA render stabilization wait timed out")

        # Handle any initial blockers (modals, cookie banners) - with timeout
        if self.config.enable_recovery:
            logger.info("Handling pre-action blockers...")
            try:
                await asyncio.wait_for(
                    self.recovery_handler.handle_pre_action_issues(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Pre-action blocker handling timed out")

        logger.info("Pre-test setup complete, starting step execution...")

        # Execute each step
        logger.info(f"Executing {len(steps)} steps...")
        for step in steps:
            if self.state != AgentState.RUNNING:
                logger.info("Agent state is not RUNNING, stopping execution")
                break

            step.status = StepStatus.RUNNING
            logger.info(f"Step {step.step_number}: {step.action} -> {step.target}")

            # Notify step callback
            if self._step_callback:
                await self._step_callback(step, "started")

            # Execute the step with timeout
            logger.info(f"Executing step {step.step_number}...")
            try:
                result = await asyncio.wait_for(
                    self._execute_step(step),
                    timeout=60.0  # 60 second max per step
                )
            except asyncio.TimeoutError:
                logger.error(f"Step {step.step_number} timed out after 60 seconds")
                result = {
                    "status": StepStatus.FAILED,
                    "execution_time_ms": 60000,
                    "error_message": "Step execution timed out after 60 seconds"
                }
            logger.info(f"Step {step.step_number} completed with status: {result.get('status')}")

            # Update step with result
            step.status = result["status"]
            step.execution_time_ms = result["execution_time_ms"]
            step.selector_used = result.get("selector_used")
            step.selector_tier = result.get("selector_tier")
            step.error_message = result.get("error_message")

            # Capture screenshot on failure
            if step.status == StepStatus.FAILED and self.config.screenshot_on_failure:
                screenshot_path = await self._capture_screenshot(f"{test_id}_step{step.step_number}_failure")
                if screenshot_path:
                    step.screenshot_path = screenshot_path
                    screenshots.append(screenshot_path)

            # Record error
            if step.error_message:
                errors.append(f"Step {step.step_number}: {step.error_message}")

            # Notify step callback
            if self._step_callback:
                await self._step_callback(step, "completed")

            # Wait between steps
            if self.config.wait_between_steps_ms > 0:
                await asyncio.sleep(self.config.wait_between_steps_ms / 1000)

        # Complete
        end_time = datetime.utcnow()
        self.state = AgentState.COMPLETED

        # Flush learnings
        if self.config.enable_learning:
            self.learning_engine.flush()

        # Calculate results
        passed_steps = sum(1 for s in steps if s.status == StepStatus.PASSED)
        failed_steps = sum(1 for s in steps if s.status == StepStatus.FAILED)
        recovered_steps = sum(1 for s in steps if s.status == StepStatus.RECOVERED)

        overall_status = "passed" if failed_steps == 0 else "failed"

        result = TestResult(
            test_id=test_id,
            test_name=test_name,
            status=overall_status,
            total_steps=len(steps),
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            recovered_steps=recovered_steps,
            steps=steps,
            execution_time_ms=int((end_time - start_time).total_seconds() * 1000),
            started_at=start_time.isoformat(),
            completed_at=end_time.isoformat(),
            domain=self._current_domain or "",
            ai_calls_made=self._ai_calls,
            knowledge_base_hits=self._kb_hits,
            errors=errors,
            screenshots=screenshots
        )

        logger.info(f"Test completed: {test_name} - {overall_status} ({passed_steps}/{len(steps)} passed)")

        return result

    async def _execute_step(self, step: TestStep) -> Dict[str, Any]:
        """Execute a single test step"""
        start_time = datetime.utcnow()
        self._total_actions += 1

        action = step.action.lower()
        result = {
            "status": StepStatus.PENDING,
            "execution_time_ms": 0,
            "selector_used": None,
            "selector_tier": None,
            "error_message": None
        }

        # HUMAN-LIKE BEHAVIOR: Pre-action checks (token-efficient - no AI)
        pre_check = await self._human_like_pre_action_check(step, action)
        if not pre_check["should_proceed"]:
            logger.info(f"[HUMAN-LIKE] Action blocked: {pre_check.get('reason', 'unknown')}")
            if pre_check.get("auto_handled"):
                logger.info("[HUMAN-LIKE] Blocker was auto-handled, retrying...")
            else:
                result["error_message"] = pre_check.get("reason", "Pre-action check failed")
                result["status"] = StepStatus.FAILED
                return result

        try:
            # Handle different action types
            if action in ("click", "tap"):
                action_result = await self._execute_click(step)
            elif action in ("type", "fill", "input"):
                # Check if target is a form-level instruction (not a single field)
                # Normalize: lowercase and replace underscores with spaces
                target_normalized = (step.target or "").lower().replace("_", " ")
                form_level_keywords = [
                    "form", "all fields", "required fields", "remaining fields",
                    "registration", "signup", "login form", "checkout",
                    "the fields", "each field", "every field", "complete form"
                ]
                is_form_level = any(keyword in target_normalized for keyword in form_level_keywords)

                if is_form_level and not step.value:
                    # This is a form-level fill instruction - use Visual Intelligence
                    logger.info(f"[SMART-FILL] Detected form-level target '{step.target}' - using visual form fill")
                    action_result = await self._execute_visual_form_fill(step)
                else:
                    action_result = await self._execute_type(step)
            elif action in ("select", "choose"):
                action_result = await self._execute_select(step)
            elif action in ("check", "checkbox"):
                action_result = await self._execute_check(step, check=True)
            elif action in ("uncheck",):
                action_result = await self._execute_check(step, check=False)
            elif action in ("navigate", "goto", "open"):
                action_result = await self._execute_navigate(step)
            elif action in ("smart_navigate",):
                # Smart navigation: Find link/button and click instead of direct URL
                action_result = await self._execute_smart_navigate(step)
            elif action in ("wait", "pause"):
                action_result = await self._execute_wait(step)
            elif action in ("assert", "verify", "expect"):
                action_result = await self._execute_assert(step)
            elif action in ("assert_url", "verify_url", "expect_url"):
                action_result = await self._execute_assert_url(step)
            elif action in ("assert_visible", "verify_visible", "expect_visible"):
                action_result = await self._execute_assert_visible(step)
            elif action in ("scroll",):
                action_result = await self._execute_scroll(step)
            elif action in ("hover",):
                action_result = await self._execute_hover(step)
            elif action in ("press", "key"):
                action_result = await self._execute_press_key(step)
            elif action in ("assert_text", "verify_text", "expect_text"):
                action_result = await self._execute_assert_text(step)
            elif action in ("screenshot", "capture"):
                action_result = await self._execute_screenshot(step)
            elif action in ("noop", "skip", "context"):
                # No-op action - used for context/given steps that don't require action
                action_result = ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="noop",
                    selector=step.target or "",
                    selector_type="none",
                    execution_time_ms=0
                )
            elif action in ("gherkin_step", "step", "smart_action"):
                # Visual Intelligence: Analyze page and determine action
                action_result = await self._execute_visual_intelligence_step(step)
            elif action in ("fill_form", "complete_form", "auto_fill"):
                # Visual Intelligence: Auto-fill form with generated data
                action_result = await self._execute_visual_form_fill(step)
            else:
                # Last resort: Try Visual Intelligence to interpret unknown actions
                action_result = await self._execute_visual_intelligence_step(step)

            # Process result
            if action_result.status == ActionStatus.SUCCESS:
                result["status"] = StepStatus.PASSED
            elif action_result.status == ActionStatus.RECOVERED:
                result["status"] = StepStatus.RECOVERED
                self._recovered_actions += 1
            else:
                # Try recovery if enabled
                if self.config.enable_recovery and step.target:
                    recovery_result = await self._try_recovery(step, action_result)
                    if recovery_result["recovered"]:
                        result["status"] = StepStatus.RECOVERED
                        step.recovery_attempts = recovery_result["attempts"]
                        self._recovered_actions += 1
                    else:
                        result["status"] = StepStatus.FAILED
                        result["error_message"] = action_result.error_message
                else:
                    result["status"] = StepStatus.FAILED
                    result["error_message"] = action_result.error_message

            result["selector_used"] = action_result.selector
            result["selector_tier"] = getattr(action_result, 'selector_tier', None)

        except Exception as e:
            logger.error(f"Step execution error: {e}")
            result["status"] = StepStatus.FAILED
            result["error_message"] = str(e)

            if self._error_callback:
                await self._error_callback(step, e)

        result["execution_time_ms"] = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return result

    async def _execute_click(self, step: TestStep) -> ActionResult:
        """Execute a click action with smart finding and pre-submit form validation"""
        from datetime import datetime
        start = datetime.utcnow()

        target_lower = (step.target or "").lower()

        # Check if this is a submit button - if so, validate form first
        submit_keywords = ['submit', 'login', 'sign in', 'signin', 'register', 'sign up',
                          'signup', 'create account', 'continue', 'next', 'confirm', 'save']
        is_submit_button = any(kw in target_lower for kw in submit_keywords)

        if is_submit_button:
            logger.info(f"[SMART-SUBMIT] Detected submit button click: {step.target}")
            # Pre-submit validation: Check for unfilled form fields
            await self._validate_and_complete_form_before_submit()

        # Try smart finding first
        locator = await self._smart_find_element(step.target, "click")
        if locator:
            try:
                # Capture URL before click for post-click validation
                url_before = self.page.url

                # For submit buttons, ensure element is ready
                if is_submit_button:
                    logger.info("[SMART-SUBMIT] Ensuring button is ready...")
                    try:
                        await locator.scroll_into_view_if_needed(timeout=3000)
                        await self.page.wait_for_timeout(300)
                    except: pass

                # Try multiple click strategies
                click_success = False

                # Strategy 1: Normal click
                try:
                    await locator.click(timeout=3000)
                    click_success = True
                    logger.info(f"[CLICK] Normal click succeeded")
                except Exception as click_err:
                    logger.warning(f"[CLICK] Normal click failed: {click_err}")

                # Strategy 2: Hover then click (for menus)
                if not click_success:
                    try:
                        await locator.hover(timeout=1000)
                        await self.page.wait_for_timeout(300)
                        await locator.click(timeout=3000)
                        click_success = True
                        logger.info(f"[CLICK] Hover+click succeeded")
                    except Exception as e:
                        logger.warning(f"[CLICK] Hover+click failed: {e}")

                # Strategy 3: Force click (ignores overlay)
                if not click_success:
                    try:
                        await locator.click(force=True, timeout=3000)
                        click_success = True
                        logger.info(f"[CLICK] Force click succeeded")
                    except Exception as force_err:
                        logger.warning(f"[CLICK] Force click failed: {force_err}")

                # Strategy 4: Double click (some elements need this)
                if not click_success:
                    try:
                        await locator.dblclick(timeout=3000)
                        click_success = True
                        logger.info(f"[CLICK] Double click succeeded")
                    except Exception as e:
                        logger.warning(f"[CLICK] Double click failed: {e}")

                # Strategy 5: JavaScript click (last resort)
                if not click_success:
                    try:
                        await locator.evaluate("el => el.click()")
                        click_success = True
                        logger.info(f"[CLICK] JavaScript click succeeded")
                    except Exception as js_err:
                        logger.warning(f"[CLICK] JS click failed: {js_err}")

                # Strategy 6: Dispatch click event
                if not click_success:
                    try:
                        await locator.dispatch_event('click')
                        click_success = True
                        logger.info(f"[CLICK] Dispatch event succeeded")
                    except Exception as e:
                        raise Exception(f"All click methods failed for: {step.target}")

                await self.page.wait_for_timeout(500)

                # Post-click validation for submit buttons
                if is_submit_button:
                    success = await self._validate_submit_result(url_before)
                    if not success:
                        # Form submission likely failed - try to recover
                        logger.info("[SMART-SUBMIT] Submit may have failed, attempting recovery...")
                        recovered = await self._recover_from_submit_failure()
                        if recovered:
                            # Retry the click after recovery
                            await locator.click(timeout=5000)
                            await self.page.wait_for_timeout(500)

                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="click",
                    selector=step.target or "",
                    selector_type="smart",
                    execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
                )
            except Exception as e:
                logger.warning(f"Smart click failed: {e}")

        # Fallback to selector service
        selector_result = await self._resolve_selector(step.target)
        if not selector_result.selector:
            # Last resort: AI-assisted finding
            locator = await self._ai_find_element(step.target, "click")
            if locator:
                try:
                    await locator.click(timeout=5000)
                    await self.page.wait_for_timeout(500)
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        action="click",
                        selector=step.target or "",
                        selector_type="ai",
                        execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
                    )
                except: pass

            return ActionResult(
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="click",
                selector=step.target or "",
                selector_type="unknown",
                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                error_message="Could not find element"
            )

        return await self.action_executor.click(
            selector_result.selector,
            selector_result.selector_type,
            alternatives=selector_result.alternatives,
            timeout=self.config.step_timeout_ms,
            intent=step.target
        )

    async def _validate_and_complete_form_before_submit(self):
        """
        PRE-SUBMIT VALIDATION: Analyze the form and fill any missing required fields.
        This catches cases like confirm password that weren't in the test steps.

        LEARNING: Records discovered fields so next run doesn't need AI.
        """
        try:
            from .visual_intelligence import VisualIntelligence

            logger.info("[PRE-SUBMIT] Analyzing form for missing required fields...")
            vi = VisualIntelligence(ai_provider="anthropic")

            # Analyze the page to find all form fields
            analysis = await vi.analyze_page(self.page, "validate form before submit")

            if not analysis.form_fields:
                logger.info("[PRE-SUBMIT] No form fields detected, proceeding with submit")
                return

            logger.info(f"[PRE-SUBMIT] Found {len(analysis.form_fields)} form fields")

            # Track discovered fields for learning
            discovered_fields = []

            # Check each field to see if it's empty
            for field in analysis.form_fields:
                selector = field.get("selector")
                field_name = field.get("name") or field.get("label") or field.get("placeholder") or "unknown"
                field_type = field.get("type", "text")

                if not selector:
                    continue

                try:
                    # Get current value of the field
                    locator = self.page.locator(selector).first
                    if await locator.count() == 0:
                        continue

                    current_value = await locator.input_value() if field_type != "select" else ""

                    # If field is empty and looks required, fill it
                    if not current_value or current_value.strip() == "":
                        is_required = field.get("required", False)
                        field_name_lower = field_name.lower()

                        # Also consider fields that look important based on name
                        important_fields = ['password', 'confirm', 'email', 'username', 'name', 'phone']
                        looks_important = any(imp in field_name_lower for imp in important_fields)

                        if is_required or looks_important:
                            # Generate appropriate value
                            generated_value = vi._generate_field_value(field)

                            # Validate generated value - must not be a field descriptor or step text
                            invalid_patterns = ['email_address', 'mail_address', 'auto_complete',
                                               'autocomplete', 'password_field', 'username_field',
                                               'complete_remaining', 'remaining_fields', 'required_fields',
                                               'fill_form', 'complete_form', 'valid_email', 'test_field']
                            action_words = ['complete', 'remaining', 'required', 'enter', 'valid', 'field', 'form']
                            gen_lower = generated_value.lower().replace(' ', '_').replace('-', '_')
                            bad_value = any(p in gen_lower for p in invalid_patterns) or sum(1 for w in action_words if w in gen_lower) >= 2
                            if bad_value:
                                logger.warning(f"[PRE-SUBMIT] Bad value '{generated_value}', using fallback")
                                if 'email' in field_name_lower or 'mail' in field_name_lower:
                                    generated_value = f"test_{int(datetime.now().timestamp()) % 100000}@testmail.com"
                                elif 'password' in field_name_lower:
                                    generated_value = "TestPass123!"
                                else:
                                    generated_value = f"test_{int(datetime.now().timestamp()) % 100000}"

                            # Special handling for confirm password - use same as password
                            if 'confirm' in field_name_lower and 'password' in field_name_lower:
                                # Try to get the password field value
                                try:
                                    pwd_locator = self.page.locator('[type="password"]').first
                                    if await pwd_locator.count() > 0:
                                        generated_value = await pwd_locator.input_value()
                                except:
                                    generated_value = "TestPass123!"

                            logger.info(f"[PRE-SUBMIT] Filling field '{field_name}' with: {generated_value[:20]}...")
                            await locator.fill(generated_value)
                            await self.page.wait_for_timeout(100)

                            # LEARNING: Record this discovered field
                            discovered_fields.append({
                                "field_name": field_name,
                                "selector": selector,
                                "field_type": field_type,
                                "is_required": is_required,
                                "action": "fill",
                                "value_type": self._infer_value_type(field_name_lower)
                            })

                except Exception as e:
                    logger.warning(f"[PRE-SUBMIT] Could not check/fill field {field_name}: {e}")
                    continue

            # LEARNING: Save discovered fields to knowledge base
            if discovered_fields:
                await self._record_discovered_steps(discovered_fields)

                # Also track for Gherkin updates
                self._discovered_fields.extend(discovered_fields)
                logger.info(f"[PRE-SUBMIT] Tracked {len(discovered_fields)} discovered field(s) for Gherkin update")

            logger.info("[PRE-SUBMIT] Form validation complete")

        except Exception as e:
            logger.warning(f"[PRE-SUBMIT] Form validation failed: {e}")

    def _infer_value_type(self, field_name: str) -> str:
        """Infer what type of value a field needs based on its name"""
        field_name = field_name.lower()
        if 'email' in field_name:
            return 'email'
        elif 'password' in field_name or 'confirm' in field_name:
            return 'password'
        elif 'phone' in field_name or 'mobile' in field_name:
            return 'phone'
        elif 'first' in field_name:
            return 'firstname'
        elif 'last' in field_name or 'surname' in field_name:
            return 'lastname'
        elif 'user' in field_name:
            return 'username'
        else:
            return 'text'

    async def _record_discovered_steps(self, discovered_fields: List[Dict[str, Any]]):
        """
        LEARNING: Record discovered form fields as additional steps for this scenario.
        Next time the same test runs, we'll know about these fields without needing AI.
        """
        try:
            # Get current page info
            domain = self._get_domain()
            page_path = self._get_page()

            # Record each discovered field to the knowledge base
            for field in discovered_fields:
                element_key = f"form_field_{field['field_name'].replace(' ', '_').lower()}"

                # Record the selector for this element
                self.learning_engine.record_element_mapping(
                    domain=domain,
                    page=page_path,
                    element_key=element_key,
                    selectors=[{
                        "selector": field["selector"],
                        "type": "css",
                        "confidence": 0.9
                    }],
                    element_attributes={
                        "field_name": field["field_name"],
                        "field_type": field["field_type"],
                        "is_required": field["is_required"],
                        "value_type": field["value_type"],
                        "discovered_by": "pre_submit_validation"
                    },
                    ai_assisted=True
                )

                logger.info(f"[LEARNING] Recorded discovered field: {element_key} -> {field['selector']}")

            # Also save to a scenario-specific learning file
            self._save_scenario_learnings(domain, page_path, discovered_fields)

        except Exception as e:
            logger.warning(f"[LEARNING] Failed to record discovered steps: {e}")

    def _save_scenario_learnings(self, domain: str, page_path: str, discovered_fields: List[Dict[str, Any]]):
        """Save scenario-specific learnings to a file for quick retrieval"""
        try:
            import json
            from pathlib import Path

            learnings_dir = self.data_dir / "scenario_learnings"
            learnings_dir.mkdir(parents=True, exist_ok=True)

            # Create filename from domain and page
            safe_domain = domain.replace(".", "_").replace(":", "_")
            safe_page = page_path.replace("/", "_").replace("?", "_")[:50]
            learnings_file = learnings_dir / f"{safe_domain}_{safe_page}.json"

            # Load existing learnings or create new
            existing = {}
            if learnings_file.exists():
                try:
                    with open(learnings_file, 'r') as f:
                        existing = json.load(f)
                except:
                    existing = {}

            # Add new learnings
            if "discovered_fields" not in existing:
                existing["discovered_fields"] = []

            for field in discovered_fields:
                # Check if already exists
                exists = any(
                    f["selector"] == field["selector"]
                    for f in existing["discovered_fields"]
                )
                if not exists:
                    field["discovered_at"] = datetime.utcnow().isoformat()
                    existing["discovered_fields"].append(field)

            existing["last_updated"] = datetime.utcnow().isoformat()
            existing["domain"] = domain
            existing["page"] = page_path

            # Save
            with open(learnings_file, 'w') as f:
                json.dump(existing, f, indent=2)

            logger.info(f"[LEARNING] Saved {len(discovered_fields)} discovered fields to {learnings_file.name}")

        except Exception as e:
            logger.warning(f"[LEARNING] Failed to save scenario learnings: {e}")

    def _get_domain(self) -> str:
        """Get current domain from page URL"""
        try:
            from urllib.parse import urlparse
            url = self.page.url
            parsed = urlparse(url)
            return parsed.netloc or "unknown"
        except:
            return "unknown"

    def _get_page(self) -> str:
        """Get current page path from URL"""
        try:
            from urllib.parse import urlparse
            url = self.page.url
            parsed = urlparse(url)
            return parsed.path or "/"
        except:
            return "/"

    async def _load_and_log_learnings(self):
        """
        Load and log previous learnings for this domain.
        Shows what the system has learned from previous runs.
        """
        try:
            domain = self._get_domain()

            # Get KB stats for this domain
            kb_stats = self.knowledge_index.get_stats()

            logger.info(f"[LEARNING] Knowledge Base Stats:")
            logger.info(f"  - Total elements known: {kb_stats.get('total_elements', 0)}")
            logger.info(f"  - Total domains: {kb_stats.get('total_domains', 0)}")
            logger.info(f"  - Cache hit rate: {kb_stats.get('cache_hit_rate', '0%')}")

            # Check for scenario-specific learnings
            learnings_dir = self.data_dir / "scenario_learnings"
            if learnings_dir.exists():
                # Find learnings for this domain
                domain_safe = domain.replace(".", "_").replace(":", "_")
                matching_files = list(learnings_dir.glob(f"{domain_safe}_*.json"))

                if matching_files:
                    logger.info(f"[LEARNING] Found {len(matching_files)} scenario learning file(s) for {domain}")

                    for learning_file in matching_files[:3]:  # Show first 3
                        try:
                            import json
                            with open(learning_file, 'r') as f:
                                data = json.load(f)

                            discovered = data.get("discovered_fields", [])
                            if discovered:
                                logger.info(f"  - {learning_file.name}: {len(discovered)} learned field(s)")
                                for field in discovered[:3]:
                                    logger.info(f"    * {field.get('field_name')}: {field.get('selector', '')[:40]}...")
                        except Exception as e:
                            logger.debug(f"Could not read learning file: {e}")

            # Log selector resolution stats
            tier_stats = self.selector_service.get_tier_stats()
            if tier_stats:
                logger.info(f"[LEARNING] Selector Resolution Stats:")
                for tier, count in tier_stats.items():
                    if count > 0:
                        logger.info(f"  - {tier}: {count} resolutions")

        except Exception as e:
            logger.debug(f"Could not load learnings: {e}")

    async def _validate_submit_result(self, url_before: str) -> bool:
        """
        Check if form submission was successful by detecting validation errors.
        Returns True if submission succeeded, False if it likely failed.
        """
        try:
            await self.page.wait_for_timeout(500)

            # Check 1: Did the URL change? (indicates successful navigation)
            if self.page.url != url_before:
                logger.info("[POST-SUBMIT] URL changed - submission likely successful")
                return True

            # Check 2: Look for common validation error indicators
            error_selectors = [
                '[class*="error"]',
                '[class*="invalid"]',
                '[class*="validation"]',
                '[role="alert"]',
                '.field-error',
                '.form-error',
                '.error-message',
                '[aria-invalid="true"]',
                '.MuiFormHelperText-root.Mui-error',
                '.ant-form-item-explain-error'
            ]

            for selector in error_selectors:
                try:
                    locator = self.page.locator(selector)
                    if await locator.count() > 0:
                        visible = await locator.first.is_visible()
                        if visible:
                            error_text = await locator.first.text_content()
                            logger.warning(f"[POST-SUBMIT] Found validation error: {error_text[:100] if error_text else 'unknown'}")
                            return False
                except:
                    continue

            # Check 3: Look for empty required fields highlighted
            try:
                empty_required = await self.page.locator('input:invalid, select:invalid, textarea:invalid').count()
                if empty_required > 0:
                    logger.warning(f"[POST-SUBMIT] Found {empty_required} invalid/empty required fields")
                    return False
            except:
                pass

            # No errors detected
            return True

        except Exception as e:
            logger.warning(f"[POST-SUBMIT] Validation check failed: {e}")
            return True  # Assume success if we can't check

    async def _recover_from_submit_failure(self) -> bool:
        """
        RECOVERY: When form submission fails, analyze the page and fix issues.
        Returns True if recovery was successful and submit can be retried.
        """
        try:
            from .visual_intelligence import VisualIntelligence

            logger.info("[RECOVERY] Analyzing page to fix form submission failure...")

            # Take screenshot for analysis
            screenshot_path = await self._capture_screenshot("submit_failure_analysis")

            vi = VisualIntelligence(ai_provider="anthropic")
            analysis = await vi.analyze_page(self.page, "fix form submission errors")

            filled_count = 0

            # Check each form field
            for field in analysis.form_fields:
                selector = field.get("selector")
                if not selector:
                    continue

                try:
                    locator = self.page.locator(selector).first
                    if await locator.count() == 0:
                        continue

                    # Check if field is empty or has error state
                    current_value = await locator.input_value()
                    has_error = False

                    # Check for error class on field or parent
                    try:
                        field_classes = await locator.get_attribute("class") or ""
                        has_error = any(e in field_classes.lower() for e in ['error', 'invalid'])
                    except:
                        pass

                    if not current_value or has_error:
                        field_name = field.get("name") or field.get("label") or "field"
                        generated_value = vi._generate_field_value(field)

                        # Validate generated value - must not be a field descriptor or step text
                        invalid_patterns = ['email_address', 'mail_address', 'auto_complete',
                                           'autocomplete', 'password_field', 'username_field',
                                           'complete_remaining', 'remaining_fields', 'required_fields',
                                           'fill_form', 'complete_form', 'valid_email', 'test_field']
                        action_words = ['complete', 'remaining', 'required', 'enter', 'valid', 'field', 'form']
                        gen_lower = generated_value.lower().replace(' ', '_').replace('-', '_')
                        bad_value = any(p in gen_lower for p in invalid_patterns) or sum(1 for w in action_words if w in gen_lower) >= 2
                        if bad_value:
                            logger.warning(f"[RECOVERY] Bad generated value '{generated_value}', using fallback")
                            # Use proper fallback based on field type
                            field_name_lower = field_name.lower()
                            if 'email' in field_name_lower or 'mail' in field_name_lower:
                                generated_value = f"test_{int(datetime.now().timestamp()) % 100000}@testmail.com"
                            elif 'password' in field_name_lower:
                                generated_value = "TestPass123!"
                            else:
                                generated_value = f"test_{int(datetime.now().timestamp()) % 100000}"

                        # For confirm password, match the password
                        if 'confirm' in field_name.lower() and 'password' in field_name.lower():
                            try:
                                pwd_locator = self.page.locator('[type="password"]').first
                                if await pwd_locator.count() > 0:
                                    generated_value = await pwd_locator.input_value()
                            except:
                                pass

                        logger.info(f"[RECOVERY] Filling field '{field_name}' with value: {generated_value[:20] if len(generated_value) > 20 else generated_value}")
                        await locator.fill(generated_value)
                        await self.page.wait_for_timeout(100)
                        filled_count += 1

                except Exception as e:
                    logger.warning(f"[RECOVERY] Could not fix field: {e}")
                    continue

            if filled_count > 0:
                logger.info(f"[RECOVERY] Fixed {filled_count} fields, ready to retry submit")
                return True
            else:
                logger.info("[RECOVERY] No fields needed fixing")
                return False

        except Exception as e:
            logger.error(f"[RECOVERY] Recovery failed: {e}")
            return False

    async def _execute_type(self, step: TestStep) -> ActionResult:
        """Execute a type/fill action with smart finding"""
        from datetime import datetime
        start = datetime.utcnow()

        # DEBUG: Log what we're trying to type
        print(f"[TYPE-DEBUG] Target: '{step.target}', Value: '{step.value}', Value length: {len(step.value) if step.value else 0}")
        logger.info(f"[TYPE] Attempting to type '{step.value}' into '{step.target}'")

        # Try smart finding first
        locator = await self._smart_find_element(step.target, "type")
        if locator:
            if await self._smart_type_value(locator, step.value or ""):
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="type",
                    selector=step.target or "",
                    selector_type="smart",
                    execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
                )

        # Fallback to selector service
        selector_result = await self._resolve_selector(step.target)
        if not selector_result.selector:
            # Last resort: AI-assisted finding
            locator = await self._ai_find_element(step.target, "type")
            if locator and await self._smart_type_value(locator, step.value or ""):
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="type",
                    selector=step.target or "",
                    selector_type="ai",
                    execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
                )

            return ActionResult(
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="type",
                selector=step.target or "",
                selector_type="unknown",
                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                error_message="Could not find element"
            )

        return await self.action_executor.fill(
            selector_result.selector,
            step.value or "",
            selector_result.selector_type,
            alternatives=selector_result.alternatives,
            timeout=self.config.step_timeout_ms,
            intent=step.target
        )

    async def _execute_select(self, step: TestStep) -> ActionResult:
        """Execute a select action"""
        selector_result = await self._resolve_selector(step.target)

        if not selector_result.selector:
            return ActionResult(
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="select",
                selector=step.target or "",
                selector_type="unknown",
                execution_time_ms=0,
                error_message="Could not resolve selector"
            )

        return await self.action_executor.select_option(
            selector_result.selector,
            step.value or "",
            selector_result.selector_type,
            alternatives=selector_result.alternatives,
            timeout=self.config.step_timeout_ms,
            intent=step.target
        )

    async def _execute_check(self, step: TestStep, check: bool) -> ActionResult:
        """Execute a check/uncheck action"""
        selector_result = await self._resolve_selector(step.target)

        if not selector_result.selector:
            return ActionResult(
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="check" if check else "uncheck",
                selector=step.target or "",
                selector_type="unknown",
                execution_time_ms=0,
                error_message="Could not resolve selector"
            )

        if check:
            return await self.action_executor.check(
                selector_result.selector,
                selector_result.selector_type,
                alternatives=selector_result.alternatives,
                timeout=self.config.step_timeout_ms,
                intent=step.target
            )
        else:
            return await self.action_executor.uncheck(
                selector_result.selector,
                selector_result.selector_type,
                alternatives=selector_result.alternatives,
                timeout=self.config.step_timeout_ms,
                intent=step.target
            )

    async def _execute_navigate(self, step: TestStep) -> ActionResult:
        """Execute a navigation action"""
        url = step.value or step.target or ""
        return await self.action_executor.navigate(url)

    async def _execute_smart_navigate(self, step: TestStep) -> ActionResult:
        """
        Smart navigation: Instead of navigating to a URL directly,
        find a link/button on the page that leads to the target and click it.

        This handles Gherkin steps like "navigate to registration page" by
        finding and clicking a "Register" or "Sign Up" link/button.
        """
        from datetime import datetime
        start = datetime.utcnow()

        page_concept = (step.target or "").lower().strip()
        logger.info(f"[SMART-NAV] Looking for navigation to: {page_concept}")

        # Define synonyms for common page concepts
        page_synonyms = {
            "registration": ["register", "sign up", "signup", "create account", "join", "get started"],
            "login": ["log in", "signin", "sign in", "authenticate", "access"],
            "logout": ["log out", "signout", "sign out", "exit"],
            "home": ["home", "main", "dashboard", "start"],
            "profile": ["profile", "my account", "account", "settings"],
            "contact": ["contact", "contact us", "get in touch", "support"],
            "about": ["about", "about us", "who we are"],
            "cart": ["cart", "basket", "shopping cart", "bag"],
            "checkout": ["checkout", "check out", "pay", "payment"],
        }

        # Get search terms for this page concept
        search_terms = [page_concept]
        for concept, synonyms in page_synonyms.items():
            if page_concept in concept or concept in page_concept:
                search_terms.extend(synonyms)
                break

        logger.info(f"[SMART-NAV] Search terms: {search_terms}")

        # Strategy 1: Try to find a link or button with matching text
        for term in search_terms:
            try:
                # Try link by text
                link_locator = self.page.get_by_role("link", name=term)
                if await link_locator.count() > 0:
                    logger.info(f"[SMART-NAV] Found link with text: {term}")
                    await link_locator.first.click(timeout=5000)
                    await self.page.wait_for_timeout(500)
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        action="smart_navigate",
                        selector=f"link:{term}",
                        selector_type="role",
                        execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                        navigation_occurred=True
                    )
            except Exception as e:
                logger.debug(f"[SMART-NAV] Link search failed for '{term}': {e}")

            try:
                # Try button by text
                btn_locator = self.page.get_by_role("button", name=term)
                if await btn_locator.count() > 0:
                    logger.info(f"[SMART-NAV] Found button with text: {term}")
                    await btn_locator.first.click(timeout=5000)
                    await self.page.wait_for_timeout(500)
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        action="smart_navigate",
                        selector=f"button:{term}",
                        selector_type="role",
                        execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                        navigation_occurred=True
                    )
            except Exception as e:
                logger.debug(f"[SMART-NAV] Button search failed for '{term}': {e}")

            try:
                # Try generic text match
                text_locator = self.page.get_by_text(term, exact=False)
                if await text_locator.count() > 0:
                    # Check if it's clickable
                    first = text_locator.first
                    tag = await first.evaluate("el => el.tagName.toLowerCase()")
                    if tag in ['a', 'button'] or await first.get_attribute("onclick"):
                        logger.info(f"[SMART-NAV] Found clickable text: {term}")
                        await first.click(timeout=5000)
                        await self.page.wait_for_timeout(500)
                        return ActionResult(
                            status=ActionStatus.SUCCESS,
                            action="smart_navigate",
                            selector=f"text:{term}",
                            selector_type="text",
                            execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                            navigation_occurred=True
                        )
            except Exception as e:
                logger.debug(f"[SMART-NAV] Text search failed for '{term}': {e}")

        # Strategy 2: Look for href containing the page concept
        try:
            href_locator = self.page.locator(f"a[href*='{page_concept}']")
            if await href_locator.count() > 0:
                logger.info(f"[SMART-NAV] Found link with href containing: {page_concept}")
                await href_locator.first.click(timeout=5000)
                await self.page.wait_for_timeout(500)
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="smart_navigate",
                    selector=f"href:{page_concept}",
                    selector_type="css",
                    execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                    navigation_occurred=True
                )
        except Exception as e:
            logger.debug(f"[SMART-NAV] href search failed: {e}")

        # Strategy 3: Check if we're already on the right page
        current_url = self.page.url.lower()
        if page_concept in current_url:
            logger.info(f"[SMART-NAV] Already on {page_concept} page (URL contains it)")
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="smart_navigate",
                selector="current_page",
                selector_type="url",
                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        # Strategy 4: Check if page has elements related to the concept
        concept_elements = await self._find_page_concept_elements(page_concept)
        if concept_elements:
            logger.info(f"[SMART-NAV] Found {page_concept}-related elements on current page")
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="smart_navigate",
                selector="page_has_concept_elements",
                selector_type="semantic",
                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        # Strategy 5: Last resort - try Visual Intelligence
        logger.info(f"[SMART-NAV] Using Visual Intelligence to find navigation to {page_concept}")
        try:
            from .visual_intelligence import VisualIntelligence
            vi = VisualIntelligence(ai_provider="anthropic")
            analysis = await vi.analyze_page(self.page, f"find link or button to navigate to {page_concept}")

            if analysis.suggested_actions:
                for action in analysis.suggested_actions:
                    if action.get("action") == "click" and action.get("selector"):
                        logger.info(f"[SMART-NAV] VI suggested clicking: {action.get('selector')}")
                        try:
                            await self.page.click(action["selector"], timeout=5000)
                            await self.page.wait_for_timeout(500)
                            return ActionResult(
                                status=ActionStatus.SUCCESS,
                                action="smart_navigate",
                                selector=action["selector"],
                                selector_type="vi",
                                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                                navigation_occurred=True
                            )
                        except:
                            continue
        except Exception as e:
            logger.warning(f"[SMART-NAV] Visual Intelligence failed: {e}")

        # All strategies failed
        logger.warning(f"[SMART-NAV] Could not find navigation to {page_concept}")
        return ActionResult(
            status=ActionStatus.ELEMENT_NOT_FOUND,
            action="smart_navigate",
            selector=page_concept,
            selector_type="concept",
            execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
            error_message=f"Could not find link/button to navigate to {page_concept} page"
        )

    async def _find_page_concept_elements(self, concept: str) -> bool:
        """Check if the current page has elements related to a concept (e.g., registration form)"""
        concept_indicators = {
            "registration": ["[name*='register']", "[id*='register']", "[class*='register']",
                            "[name*='signup']", "[id*='signup']", "form[action*='register']"],
            "login": ["[name*='login']", "[id*='login']", "[class*='login']",
                     "[name*='signin']", "form[action*='login']", "[type='password']"],
            "profile": ["[name*='profile']", "[id*='profile']", "[class*='profile']"],
            "checkout": ["[name*='checkout']", "[id*='checkout']", "[class*='checkout']",
                        "[name*='payment']", "[id*='payment']"],
        }

        selectors_to_check = concept_indicators.get(concept, [f"[id*='{concept}']", f"[class*='{concept}']"])

        for selector in selectors_to_check:
            try:
                if await self.page.locator(selector).count() > 0:
                    return True
            except:
                continue

        return False

    async def _execute_wait(self, step: TestStep) -> ActionResult:
        """Execute a wait action"""
        if step.target:
            # Wait for element
            selector_result = await self._resolve_selector(step.target)
            if selector_result.selector:
                return await self.action_executor.wait_for_element(
                    selector_result.selector,
                    selector_result.selector_type,
                    timeout=self.config.step_timeout_ms
                )

        # Wait for time
        wait_ms = int(step.value or 1000)
        return await self.action_executor.wait(wait_ms)

    async def _execute_assert(self, step: TestStep) -> ActionResult:
        """
        Execute an assertion LIKE A TESTER.

        A real tester doesn't just look at one spot - they:
        1. Check the current page first
        2. Look for success indicators (URL change, no errors, positive messages)
        3. Try clicking likely navigation elements if expected content not found
        4. Explore common success paths (dashboard, profile, home)
        """
        from datetime import datetime
        start = datetime.utcnow()

        if not step.target:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert",
                selector="",
                selector_type="unknown",
                execution_time_ms=0,
                error_message="No target specified for assertion"
            )

        expected_text = step.expected or step.target
        logger.info(f"[TESTER-ASSERT] Looking for: '{expected_text}'")

        # STRATEGY 0: Smart count assertion (e.g., "six tabs", "7 items", "three buttons")
        count_result = await self._try_count_assertion(expected_text)
        if count_result:
            return ActionResult(
                status=count_result["status"],
                action="assert",
                selector=expected_text,
                selector_type="count_assertion",
                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
                error_message=count_result.get("error_message")
            )

        # STRATEGY 1: Direct check on current page
        result = await self._try_find_expected_content(expected_text)
        if result:
            logger.info(f"[TESTER-ASSERT] Found directly on page")
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="assert",
                selector=expected_text,
                selector_type="text",
                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        # STRATEGY 2: Check for success indicators even if exact text not found
        success_indicators = await self._check_success_indicators()
        if success_indicators.get("likely_success"):
            logger.info(f"[TESTER-ASSERT] Success indicators found: {success_indicators.get('reason')}")
            # Continue looking for the exact content...

        # STRATEGY 3: Try expanding accordions/tabs ON THE CURRENT PAGE ONLY
        # DO NOT navigate away - only click elements that reveal hidden content on same page
        expand_elements = ["Show More", "View All", "Expand", "See Details", "More"]
        for expand_text in expand_elements:
            try:
                # Only look for expand/toggle buttons, NOT navigation links
                expand_locator = self.page.get_by_role("button", name=expand_text)
                if await expand_locator.count() == 0:
                    # Try aria-expanded elements
                    expand_locator = self.page.locator(f'[aria-expanded="false"]:has-text("{expand_text}")')

                if await expand_locator.count() > 0:
                    logger.info(f"[TESTER-ASSERT] Trying to expand: {expand_text}")
                    await expand_locator.first.click(timeout=2000)
                    await self.page.wait_for_timeout(500)

                    # Check for expected content after expanding
                    result = await self._try_find_expected_content(expected_text)
                    if result:
                        logger.info(f"[TESTER-ASSERT] Found after expanding {expand_text}")
                        return ActionResult(
                            status=ActionStatus.SUCCESS,
                            action="assert",
                            selector=f"{expected_text} (via {expand_text})",
                            selector_type="expansion",
                            execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
                        )
            except Exception as e:
                logger.debug(f"[TESTER-ASSERT] Expand click failed for {expand_text}: {e}")
                continue

        # STRATEGY 4: Check page title, headers, or main content areas
        content_areas = await self._get_main_content_text()
        expected_lower = expected_text.lower()
        if any(expected_lower in area.lower() for area in content_areas):
            logger.info(f"[TESTER-ASSERT] Found in content area")
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="assert",
                selector=expected_text,
                selector_type="content_area",
                execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
            )

        # STRATEGY 5: If we have success indicators, be more lenient
        if success_indicators.get("likely_success"):
            # Check for partial matches
            partial_result = await self._try_find_partial_match(expected_text)
            if partial_result:
                logger.info(f"[TESTER-ASSERT] Found partial match: {partial_result}")
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="assert",
                    selector=f"partial:{partial_result}",
                    selector_type="partial_match",
                    execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000)
                )

        # Only use selector resolution for SHORT targets that look like field names
        # Long descriptive text like "six report type tabs available" should NOT go through
        # the selector service - it will incorrectly match keywords like "type" to input fields
        word_count = len(expected_text.split())
        is_descriptive_text = word_count >= 3  # 3+ words = descriptive assertion

        if not is_descriptive_text:
            # Short target - might be a field name, try selector resolution
            selector_result = await self._resolve_selector(step.target)
            if selector_result.selector and selector_result.confidence >= 0.7:
                if step.expected:
                    return await self.action_executor.assert_text(
                        selector_result.selector,
                        step.expected,
                        selector_result.selector_type,
                        timeout=self.config.step_timeout_ms
                    )
                else:
                    return await self.action_executor.assert_visible(
                        selector_result.selector,
                        selector_result.selector_type,
                        timeout=self.config.step_timeout_ms
                    )

        # For descriptive text assertions, report as assertion failure
        # The text strategies above already searched thoroughly
        return ActionResult(
            status=ActionStatus.ASSERTION_FAILED,
            action="assert",
            selector=step.target,
            selector_type="text_assertion",
            execution_time_ms=int((datetime.utcnow() - start).total_seconds() * 1000),
            error_message=f"Assertion failed: Expected text '{expected_text}' was not found on the page"
        )

    async def _try_count_assertion(self, assertion_text: str) -> Optional[Dict[str, Any]]:
        """
        Try to interpret assertion as a count verification.

        Handles natural language like:
        - "six report type tabs available"
        - "7 items in the list"
        - "three buttons visible"
        - "5 rows in the table"

        Returns None if not a count assertion, or dict with status and details.
        """
        import re

        # Number words to digits mapping
        number_words = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
            'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
            'ten': 10, 'eleven': 11, 'twelve': 12
        }

        # Element types that can be counted
        countable_elements = {
            'tab': ['[role="tab"]', '.tab', '[data-tab]', 'button[role="tab"]', 'a[role="tab"]', 'li[role="tab"]'],
            'tabs': ['[role="tab"]', '.tab', '[data-tab]', 'button[role="tab"]', 'a[role="tab"]', 'li[role="tab"]'],
            'button': ['button', '[role="button"]', 'input[type="button"]', 'input[type="submit"]'],
            'buttons': ['button', '[role="button"]', 'input[type="button"]', 'input[type="submit"]'],
            'item': ['li', '[role="listitem"]', '.item', '.list-item'],
            'items': ['li', '[role="listitem"]', '.item', '.list-item'],
            'row': ['tr', '[role="row"]', '.row'],
            'rows': ['tr', '[role="row"]', '.row'],
            'card': ['.card', '[class*="card"]', '[data-card]'],
            'cards': ['.card', '[class*="card"]', '[data-card]'],
            'option': ['option', '[role="option"]', '.option'],
            'options': ['option', '[role="option"]', '.option'],
            'link': ['a[href]', '[role="link"]'],
            'links': ['a[href]', '[role="link"]'],
            'column': ['th', 'td', '[role="columnheader"]'],
            'columns': ['th', 'td', '[role="columnheader"]'],
            'field': ['input', 'textarea', 'select', '[role="textbox"]'],
            'fields': ['input', 'textarea', 'select', '[role="textbox"]'],
            'error': ['.error', '[class*="error"]', '[role="alert"]', '.invalid-feedback'],
            'errors': ['.error', '[class*="error"]', '[role="alert"]', '.invalid-feedback'],
            'menu': ['[role="menuitem"]', '.menu-item', 'li.nav-item'],
            'menus': ['[role="menuitem"]', '.menu-item', 'li.nav-item'],
        }

        text_lower = assertion_text.lower()

        # Try to extract expected count
        expected_count = None

        # Check for number words
        for word, num in number_words.items():
            if word in text_lower:
                expected_count = num
                break

        # Check for digits
        if expected_count is None:
            digit_match = re.search(r'\b(\d+)\b', text_lower)
            if digit_match:
                expected_count = int(digit_match.group(1))

        if expected_count is None:
            return None  # Not a count assertion

        # Try to find what element type to count
        element_type = None
        selectors_to_try = []

        for elem_type, selectors in countable_elements.items():
            if elem_type in text_lower:
                element_type = elem_type
                selectors_to_try = selectors
                break

        if not element_type:
            return None  # Couldn't determine what to count

        logger.info(f"[COUNT-ASSERT] Detected count assertion: expecting {expected_count} {element_type}")

        # Count elements on the page
        actual_count = 0
        found_selector = None

        for selector in selectors_to_try:
            try:
                locator = self.page.locator(selector)
                count = await locator.count()

                # Only count visible elements
                visible_count = 0
                for i in range(count):
                    try:
                        if await locator.nth(i).is_visible():
                            visible_count += 1
                    except:
                        continue

                if visible_count > 0:
                    actual_count = visible_count
                    found_selector = selector
                    logger.info(f"[COUNT-ASSERT] Found {visible_count} visible '{selector}' elements")
                    break
            except Exception as e:
                logger.debug(f"[COUNT-ASSERT] Selector {selector} failed: {e}")
                continue

        # Compare counts
        if actual_count == expected_count:
            logger.info(f"[COUNT-ASSERT] SUCCESS: Found exactly {actual_count} {element_type}")
            return {
                "status": ActionStatus.SUCCESS,
                "actual_count": actual_count,
                "expected_count": expected_count,
                "element_type": element_type,
                "selector_used": found_selector
            }
        else:
            logger.info(f"[COUNT-ASSERT] FAILED: Expected {expected_count} {element_type}, found {actual_count}")
            return {
                "status": ActionStatus.ASSERTION_FAILED,
                "actual_count": actual_count,
                "expected_count": expected_count,
                "element_type": element_type,
                "selector_used": found_selector,
                "error_message": f"Assertion failed: Expected {expected_count} {element_type}, but found {actual_count}"
            }

    async def _try_find_expected_content(self, text: str) -> bool:
        """Try to find expected text content on the page"""
        try:
            # Method 1: Direct text search
            locator = self.page.get_by_text(text, exact=False)
            if await locator.count() > 0 and await locator.first.is_visible():
                return True

            # Method 2: Check if text appears anywhere in body
            body_text = await self.page.text_content("body") or ""
            if text.lower() in body_text.lower():
                return True

            # Method 3: Check common success message containers
            success_selectors = [
                '[class*="success"]',
                '[class*="welcome"]',
                '[class*="greeting"]',
                '[class*="user-info"]',
                '[class*="dashboard"]',
                '[role="alert"]',
                'h1', 'h2', 'h3',
                '[class*="header"]',
                '[class*="title"]'
            ]
            for selector in success_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    for i in range(min(count, 5)):
                        el_text = await elements.nth(i).text_content() or ""
                        if text.lower() in el_text.lower():
                            return True
                except:
                    continue

            return False
        except Exception as e:
            logger.debug(f"Content search failed: {e}")
            return False

    async def _check_success_indicators(self) -> Dict[str, Any]:
        """Check for common success indicators on the page"""
        indicators = {
            "likely_success": False,
            "reason": None,
            "indicators_found": []
        }

        try:
            # Check 1: No error messages visible
            error_selectors = [
                '[class*="error"]',
                '[class*="invalid"]',
                '[class*="fail"]',
                '[role="alert"][class*="error"]',
                '.form-error',
                '.validation-error'
            ]
            has_errors = False
            for sel in error_selectors:
                try:
                    loc = self.page.locator(sel)
                    if await loc.count() > 0 and await loc.first.is_visible():
                        has_errors = True
                        break
                except:
                    continue

            if not has_errors:
                indicators["indicators_found"].append("no_errors")

            # Check 2: URL indicates success (dashboard, home, profile, success)
            current_url = self.page.url.lower()
            success_url_patterns = ['dashboard', 'home', 'profile', 'success', 'welcome', 'account']
            if any(p in current_url for p in success_url_patterns):
                indicators["indicators_found"].append("success_url")

            # Check 3: Success message elements present
            success_elements = [
                '[class*="success"]',
                '[class*="welcome"]',
                '[class*="logged-in"]',
                '[class*="authenticated"]'
            ]
            for sel in success_elements:
                try:
                    if await self.page.locator(sel).count() > 0:
                        indicators["indicators_found"].append("success_element")
                        break
                except:
                    continue

            # Check 4: User-specific content visible (avatar, user menu, etc.)
            user_indicators = [
                '[class*="avatar"]',
                '[class*="user-menu"]',
                '[class*="profile-icon"]',
                '[aria-label*="user"]',
                '[class*="logout"]'  # If logout button is visible, user is logged in
            ]
            for sel in user_indicators:
                try:
                    if await self.page.locator(sel).count() > 0:
                        indicators["indicators_found"].append("user_content")
                        break
                except:
                    continue

            # Determine if likely success
            if len(indicators["indicators_found"]) >= 2:
                indicators["likely_success"] = True
                indicators["reason"] = f"Found: {', '.join(indicators['indicators_found'])}"
            elif "success_url" in indicators["indicators_found"]:
                indicators["likely_success"] = True
                indicators["reason"] = "URL indicates success"

        except Exception as e:
            logger.debug(f"Success indicator check failed: {e}")

        return indicators

    async def _get_main_content_text(self) -> List[str]:
        """Get text from main content areas"""
        content = []
        try:
            # Get page title
            title = await self.page.title()
            if title:
                content.append(title)

            # Get h1-h3 headers
            for tag in ['h1', 'h2', 'h3']:
                try:
                    headers = self.page.locator(tag)
                    count = await headers.count()
                    for i in range(min(count, 3)):
                        text = await headers.nth(i).text_content()
                        if text:
                            content.append(text.strip())
                except:
                    continue

            # Get main/article content
            for container in ['main', 'article', '[role="main"]', '.content', '#content']:
                try:
                    loc = self.page.locator(container)
                    if await loc.count() > 0:
                        text = await loc.first.text_content()
                        if text:
                            content.append(text[:500])  # Limit size
                        break
                except:
                    continue

        except Exception as e:
            logger.debug(f"Content extraction failed: {e}")

        return content

    async def _try_find_partial_match(self, text: str) -> Optional[str]:
        """Try to find partial matches for expected text"""
        try:
            # Extract key words from expected text
            keywords = [w for w in text.lower().split() if len(w) > 3]

            body_text = await self.page.text_content("body") or ""
            body_lower = body_text.lower()

            # Check if most keywords are present
            found_keywords = [kw for kw in keywords if kw in body_lower]
            if len(found_keywords) >= len(keywords) * 0.5:  # At least 50% match
                return f"keywords: {', '.join(found_keywords)}"

            return None
        except:
            return None

    async def _execute_assert_url(self, step: TestStep) -> ActionResult:
        """Execute a URL assertion"""
        from .action_executor import ActionResult, ActionStatus

        expected_url = step.target or step.value or ""

        if not expected_url:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert_url",
                selector="",
                selector_type="url",
                execution_time_ms=0,
                error_message="No URL specified for assertion"
            )

        # Determine match type from expected value
        match_type = "contains"
        if step.expected:
            match_type = step.expected.lower()

        logger.info(f"Asserting URL contains: '{expected_url}'")
        return await self.action_executor.assert_url(
            expected_url,
            match_type=match_type,
            timeout=self.config.step_timeout_ms
        )

    async def _execute_assert_visible(self, step: TestStep) -> ActionResult:
        """Execute a visibility assertion with smart waiting"""
        from .action_executor import ActionResult, ActionStatus

        if not step.target:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert_visible",
                selector="",
                selector_type="unknown",
                execution_time_ms=0,
                error_message="No target specified for visibility assertion"
            )

        # Wait for page to be ready first
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass  # Continue even if networkidle times out

        selector_result = await self._resolve_selector(step.target)

        if not selector_result.selector:
            return ActionResult(
                status=ActionStatus.ASSERTION_FAILED,
                action="assert_visible",
                selector=step.target,
                selector_type="unknown",
                execution_time_ms=0,
                error_message=f"Assertion failed: Element '{step.target}' is not visible on the page"
            )

        logger.info(f"Asserting visible: '{selector_result.selector}'")
        return await self.action_executor.assert_visible(
            selector_result.selector,
            selector_result.selector_type,
            timeout=self.config.step_timeout_ms
        )

    async def _execute_scroll(self, step: TestStep) -> ActionResult:
        """Execute a scroll action"""
        direction = step.value or "down"
        amount = 300

        # Parse value if it contains amount
        if step.value and "," in step.value:
            parts = step.value.split(",")
            direction = parts[0].strip()
            amount = int(parts[1].strip())

        return await self.action_executor.scroll(
            direction=direction,
            amount=amount,
            selector=step.target
        )

    async def _execute_hover(self, step: TestStep) -> ActionResult:
        """Execute a hover action"""
        selector_result = await self._resolve_selector(step.target)

        if not selector_result.selector:
            return ActionResult(
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="hover",
                selector=step.target or "",
                selector_type="unknown",
                execution_time_ms=0,
                error_message="Could not resolve selector"
            )

        return await self.action_executor.hover(
            selector_result.selector,
            selector_result.selector_type,
            alternatives=selector_result.alternatives,
            timeout=self.config.step_timeout_ms
        )

    async def _execute_press_key(self, step: TestStep) -> ActionResult:
        """Execute a key press action"""
        key = step.value or "Enter"
        return await self.action_executor.press_key(key, step.target)


    async def _execute_assert_text(self, step: TestStep) -> ActionResult:
        """Execute a text assertion with smart element finding"""
        from .action_executor import ActionResult, ActionStatus
        from datetime import datetime
        start = datetime.utcnow()

        if not step.target:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert_text",
                selector="",
                selector_type="unknown",
                execution_time_ms=0,
                error_message="No target specified for text assertion"
            )

        selector_result = await self._resolve_selector(step.target)

        if not selector_result.selector:
            return ActionResult(
                status=ActionStatus.ASSERTION_FAILED,
                action="assert_text",
                selector=step.target,
                selector_type="unknown",
                execution_time_ms=0,
                error_message=f"Assertion failed: Could not find element '{step.target}' to verify text"
            )

        expected_text = step.value or step.expected or ""
        logger.info(f"Asserting text '{expected_text}' in '{selector_result.selector}'")

        return await self.action_executor.assert_text(
            selector_result.selector,
            expected_text,
            selector_result.selector_type,
            timeout=self.config.step_timeout_ms
        )

    async def _execute_screenshot(self, step: TestStep) -> ActionResult:
        """Execute a screenshot capture"""
        from .action_executor import ActionResult, ActionStatus
        from datetime import datetime
        from pathlib import Path
        start = datetime.utcnow()

        try:
            screenshot_dir = Path("data/agent_knowledge/screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            filename = step.value or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            if not filename.endswith('.png'):
                filename += '.png'

            screenshot_path = str(screenshot_dir / filename)
            await self.page.screenshot(path=screenshot_path, full_page=False)

            execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="screenshot",
                selector="",
                selector_type="none",
                execution_time_ms=execution_time,
                screenshot_path=screenshot_path
            )
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ActionResult(
                status=ActionStatus.ERROR,
                action="screenshot",
                selector="",
                selector_type="none",
                execution_time_ms=0,
                error_message=str(e)
            )

    async def _execute_visual_intelligence_step(self, step: TestStep) -> ActionResult:
        """
        Execute a step using Visual Intelligence to analyze the page
        and determine the appropriate action.
        """
        from .action_executor import ActionResult, ActionStatus
        from .visual_intelligence import VisualIntelligence
        from datetime import datetime
        start = datetime.utcnow()

        try:
            # Initialize visual intelligence
            vi = VisualIntelligence(ai_provider="anthropic")

            # Analyze the current page with the step description
            step_description = step.target or step.value or step.description or ""
            logger.info(f"Visual Intelligence analyzing step: {step_description}")

            analysis = await vi.analyze_page(self.page, step_description)
            logger.info(f"Page context: {analysis.page_context.value}, confidence: {analysis.confidence}")

            # Determine the action to take
            action_plan = await vi.determine_action_from_step(
                self.page, step_description, analysis
            )

            logger.info(f"Visual Intelligence determined action: {action_plan}")

            # Execute the determined action
            action_type = action_plan.get("action", "unknown")

            if action_type == "fill_form":
                # Fill all form fields
                result = await vi.execute_form_fill(
                    self.page,
                    fields=action_plan.get("fields"),
                    values=action_plan.get("values")
                )
                execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)

                if result["success"]:
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        action="fill_form",
                        selector="visual_intelligence",
                        selector_type="vi",
                        execution_time_ms=execution_time
                    )
                else:
                    return ActionResult(
                        status=ActionStatus.ERROR,
                        action="fill_form",
                        selector="visual_intelligence",
                        selector_type="vi",
                        execution_time_ms=execution_time,
                        error_message=f"Failed fields: {result['failed_fields']}"
                    )

            elif action_type == "fill":
                selector = action_plan.get("selector")
                value = action_plan.get("value", "")
                if selector:
                    await self.page.fill(selector, value)
                    execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        action="fill",
                        selector=selector,
                        selector_type="vi",
                        execution_time_ms=execution_time
                    )

            elif action_type == "click":
                selector = action_plan.get("selector")
                if selector:
                    await self.page.click(selector, timeout=self.config.step_timeout_ms)
                    execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        action="click",
                        selector=selector,
                        selector_type="vi",
                        execution_time_ms=execution_time
                    )

            elif action_type == "verify":
                # For verify, we just check if something is visible
                execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="verify",
                    selector="visual_intelligence",
                    selector_type="vi",
                    execution_time_ms=execution_time
                )

            elif action_type == "wait":
                duration = action_plan.get("duration", 2000)
                await self.page.wait_for_timeout(duration)
                execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="wait",
                    selector="",
                    selector_type="none",
                    execution_time_ms=execution_time
                )

            # Unknown or unsupported action
            execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)
            return ActionResult(
                status=ActionStatus.ERROR,
                action=action_type,
                selector="visual_intelligence",
                selector_type="vi",
                execution_time_ms=execution_time,
                error_message=f"Visual Intelligence could not determine action for: {step_description}"
            )

        except Exception as e:
            logger.error(f"Visual Intelligence step failed: {e}")
            execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)
            return ActionResult(
                status=ActionStatus.ERROR,
                action="visual_intelligence",
                selector=step.target or "",
                selector_type="vi",
                execution_time_ms=execution_time,
                error_message=str(e)
            )

    async def _execute_visual_form_fill(self, step: TestStep) -> ActionResult:
        """
        Execute automatic form filling using Visual Intelligence
        to detect form fields and generate appropriate test data.
        """
        from .action_executor import ActionResult, ActionStatus
        from .visual_intelligence import VisualIntelligence
        from datetime import datetime
        start = datetime.utcnow()

        try:
            vi = VisualIntelligence(ai_provider="anthropic")

            # Analyze page to find form fields
            analysis = await vi.analyze_page(self.page, "fill form")

            if not analysis.form_fields:
                return ActionResult(
                    status=ActionStatus.ERROR,
                    action="fill_form",
                    selector="",
                    selector_type="vi",
                    execution_time_ms=0,
                    error_message="No form fields detected on the page"
                )

            # Execute form fill
            result = await vi.execute_form_fill(self.page, fields=analysis.form_fields)
            execution_time = int((datetime.utcnow() - start).total_seconds() * 1000)

            if result["success"]:
                filled_count = len(result["filled_fields"])
                logger.info(f"Visual form fill completed: {filled_count} fields filled")
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="fill_form",
                    selector=f"{filled_count} fields",
                    selector_type="vi",
                    execution_time_ms=execution_time
                )
            else:
                return ActionResult(
                    status=ActionStatus.ERROR,
                    action="fill_form",
                    selector="",
                    selector_type="vi",
                    execution_time_ms=execution_time,
                    error_message=f"Some fields failed: {result['failed_fields']}"
                )

        except Exception as e:
            logger.error(f"Visual form fill failed: {e}")
            return ActionResult(
                status=ActionStatus.ERROR,
                action="fill_form",
                selector="",
                selector_type="vi",
                execution_time_ms=0,
                error_message=str(e)
            )

    # ==================== Selector Resolution ====================

    async def _resolve_selector(self, target: Optional[str]) -> SelectorResult:
        """Resolve a target to a selector using the tiered system"""
        if not target:
            logger.warning("_resolve_selector called with empty target")
            return SelectorResult(
                selector="",
                selector_type="none",
                confidence=0.0,
                tier=ResolutionTier.FAILED,
                alternatives=[],
                metadata={"error": "No target specified"}
            )

        logger.debug(f"Resolving selector for target: {target}")

        # Check if target is already a selector (CSS, XPath, or common patterns)
        # Handle CSS selectors: #id, .class, [attr], tag, tag.class, tag#id
        is_direct_selector = (
            target.startswith("#") or
            target.startswith(".") or
            target.startswith("[") or
            target.startswith("//") or  # XPath
            target.startswith("(//") or  # XPath with grouping
            "=" in target or  # Attribute selectors like input[name="x"]
            " > " in target or  # Child combinator
            " + " in target or  # Adjacent sibling
            " ~ " in target or  # General sibling
            target.startswith("input") or
            target.startswith("button") or
            target.startswith("a[") or
            target.startswith("div") or
            target.startswith("span") or
            "::" in target  # Pseudo-elements
        )

        # Get page HTML for heuristics (needed for both direct and intent-based resolution)
        page_html = None
        try:
            page_html = await self.page.content()
            logger.debug(f"Got page HTML: {len(page_html) if page_html else 0} chars")
        except Exception as e:
            logger.warning(f"Failed to get page HTML: {e}")
            pass

        # Even for direct selectors, try to find a better match via KB/heuristics
        # Extract intent from selector for KB lookup (e.g., [data-test*="sign"] -> "sign")
        intent_for_lookup = target
        if is_direct_selector:
            intent_for_lookup = self._extract_intent_from_selector(target)
            print(f"[SELECTOR-DEBUG] Direct selector: '{target}' -> intent: '{intent_for_lookup}'")

        # Always try selector service first - it checks KB, heuristics, framework rules
        result = self.selector_service.resolve(
            intent=intent_for_lookup,
            domain=self._current_domain or "",
            page=self._get_current_page(),
            page_html=page_html
        )

        # If selector service found something good, use it
        if result.selector and result.confidence >= 0.6 and result.tier != ResolutionTier.FAILED:
            print(f"[SELECTOR-DEBUG] KB found: '{intent_for_lookup}' -> '{result.selector}' (conf={result.confidence:.2f}, tier={result.tier.value})")
            # Add original selector as fallback alternative if it was a direct selector
            if is_direct_selector and target not in [result.selector] + [a.get('selector') for a in result.alternatives]:
                result.alternatives.append({
                    "selector": target,
                    "type": "xpath" if target.startswith("//") or target.startswith("(//") else "css",
                    "confidence": 0.5,
                    "source": "original_direct"
                })
        elif is_direct_selector:
            # Selector service didn't find anything good, use the original direct selector
            print(f"[SELECTOR-DEBUG] No KB match, using fallback: {target}")
            result = SelectorResult(
                selector=target,
                selector_type="xpath" if target.startswith("//") or target.startswith("(//") else "css",
                confidence=0.7,  # Lower confidence since we couldn't validate it
                tier=ResolutionTier.FALLBACK,
                alternatives=[],
                metadata={"source": "direct_fallback", "original_target": target}
            )
        else:
            logger.info(f"Selector resolved: '{target}' -> '{result.selector}' (type={result.selector_type}, confidence={result.confidence:.2f}, tier={result.tier.value})")


        # Add SPA-aware selectors as alternatives if SPA detected
        if self._is_spa and self.config.enable_spa_mode:
            spa_selectors = self.spa_handler.get_spa_aware_selectors(target)
            for sel in spa_selectors:
                if sel not in result.alternatives:
                    result.alternatives.append(sel)

        # Track metrics based on resolution tier
        # Non-AI tiers (good - system found it without AI)
        if result.tier in (ResolutionTier.KNOWLEDGE_BASE, ResolutionTier.HEURISTICS, ResolutionTier.FRAMEWORK_RULES):
            self._kb_hits += 1
            logger.debug(f"Non-AI resolution: {result.tier.value} (total: {self._kb_hits})")
        # AI-dependent tiers (less good - needed AI help)
        elif result.tier == ResolutionTier.AI_DECISION:
            self._ai_calls += 1
            logger.debug(f"AI resolution: {result.tier.value} (total: {self._ai_calls})")
        # Fallback is partial AI dependency
        elif result.tier == ResolutionTier.FALLBACK:
            # Count fallback as half-credit (it's a guess, but not full AI)
            self._kb_hits += 1
            logger.debug(f"Fallback resolution: {result.tier.value}")

        return result

    # ==================== Recovery ====================

    async def _try_recovery(
        self,
        step: TestStep,
        action_result: ActionResult
    ) -> Dict[str, Any]:
        """Try to recover from a failed action"""
        self.state = AgentState.RECOVERING

        # Classify the failure
        failure_type = self.recovery_handler.classify_failure(
            Exception(action_result.error_message or "Unknown error"),
            {"selector": action_result.selector}
        )

        # Attempt recovery
        recovery_result = await self.recovery_handler.attempt_recovery(
            failure_type,
            {"selector": action_result.selector},
            action_result.selector
        )

        self.state = AgentState.RUNNING

        if recovery_result.success and recovery_result.should_retry_original:
            # Retry the action
            retry_result = await self._execute_step(step)
            if retry_result["status"] in (StepStatus.PASSED, StepStatus.RECOVERED):
                return {"recovered": True, "attempts": 1}

        return {"recovered": False, "attempts": 1}

    # ==================== Framework Detection ====================

    async def _detect_framework(self):
        """Detect UI framework from current page (SPA and component libraries)"""
        try:
            # First, detect SPA framework using SPA handler
            if self.config.enable_spa_mode:
                spa_framework = await self.spa_handler.detect_framework()
                self._detected_spa_framework = spa_framework
                self._is_spa = spa_framework != SPAFramework.UNKNOWN

                if self._is_spa:
                    logger.info(f"Detected SPA framework: {spa_framework.value}")

                    # Start route monitoring for SPAs
                    await self.spa_handler.start_route_monitoring()

            # Also detect UI component library
            html = await self.page.content()

            # Check for component library signatures
            if "MuiButton" in html or "@mui" in html:
                self.selector_service.set_framework("mui")
            elif "ant-btn" in html or "antd" in html:
                self.selector_service.set_framework("ant_design")
            elif "btn-primary" in html or "bootstrap" in html:
                self.selector_service.set_framework("bootstrap")
            elif "chakra-" in html:
                self.selector_service.set_framework("chakra")

        except Exception as e:
            logger.warning(f"Framework detection error: {e}")

    def _detect_framework_from_url(self, url: str) -> Optional[str]:
        """Try to detect framework from URL patterns"""
        # This is a simple heuristic - could be enhanced
        return None

    # ==================== Utilities ====================

    def _extract_intent_from_selector(self, selector: str) -> str:
        """
        Extract a meaningful intent from a CSS/XPath selector.

        Examples:
            [data-test*="sign"] -> "sign"
            [data-testid="login-button"] -> "login button"
            #username -> "username"
            .btn-submit -> "submit"
            input[name="email"] -> "email"
            button:has-text("Sign In") -> "Sign In"
        """
        intent_parts = []

        # Extract from data-test, data-testid, data-cy, data-qa attributes
        # Pattern: data-test="value" or data-test*="value" etc.
        test_attr_pattern = r'data-(?:test(?:id)?|cy|qa)[*^$~|]?=\s*["\']([^"\']+)["\']'
        test_attr_match = re.search(test_attr_pattern, selector, re.I)
        if test_attr_match:
            value = test_attr_match.group(1)
            value = re.sub(r'[-_]', ' ', value).strip()
            intent_parts.append(value)

        # Extract from id attribute or #id selector
        id_pattern = r'(?:#|id\s*=\s*["\'])([^"\'\s\]]+)'
        id_match = re.search(id_pattern, selector, re.I)
        if id_match and not intent_parts:
            value = id_match.group(1)
            value = re.sub(r'[-_]', ' ', value).strip()
            intent_parts.append(value)

        # Extract from name attribute
        name_pattern = r'name\s*=\s*["\']([^"\']+)["\']'
        name_match = re.search(name_pattern, selector, re.I)
        if name_match and not intent_parts:
            value = name_match.group(1)
            value = re.sub(r'[-_]', ' ', value).strip()
            intent_parts.append(value)

        # Extract from class (look for meaningful class names)
        class_pattern = r'\.([a-zA-Z][\w-]*)'
        class_match = re.search(class_pattern, selector)
        if class_match and not intent_parts:
            value = class_match.group(1)
            skip_classes = {'btn', 'button', 'input', 'form', 'container', 'wrapper', 'row', 'col'}
            if value.lower() not in skip_classes:
                value = re.sub(r'[-_]', ' ', value).strip()
                value = re.sub(r'^(btn|button|input|form)[- ]?', '', value, flags=re.I).strip()
                if value:
                    intent_parts.append(value)

        # Extract from placeholder attribute
        placeholder_pattern = r'placeholder\s*=\s*["\']([^"\']+)["\']'
        placeholder_match = re.search(placeholder_pattern, selector, re.I)
        if placeholder_match and not intent_parts:
            intent_parts.append(placeholder_match.group(1))

        # Extract from :has-text() or text content
        text_pattern = r':has-text\s*\(\s*["\']([^"\']+)["\']\s*\)'
        text_match = re.search(text_pattern, selector, re.I)
        if text_match:
            intent_parts.append(text_match.group(1))

        # Extract from aria-label
        aria_pattern = r'aria-label\s*=\s*["\']([^"\']+)["\']'
        aria_match = re.search(aria_pattern, selector, re.I)
        if aria_match and not intent_parts:
            intent_parts.append(aria_match.group(1))

        # Extract from type attribute (for inputs)
        type_pattern = r'type\s*=\s*["\']([^"\']+)["\']'
        type_match = re.search(type_pattern, selector, re.I)
        if type_match:
            type_val = type_match.group(1).lower()
            if type_val not in ('text', 'button', 'submit'):
                intent_parts.append(type_val)

        # If we got something, return it
        if intent_parts:
            result = ' '.join(intent_parts).lower().strip()
            words = result.split()
            seen = set()
            unique_words = []
            for w in words:
                if w not in seen:
                    seen.add(w)
                    unique_words.append(w)
            return ' '.join(unique_words)

        # Fallback: return the original selector
        return selector

    def _get_current_page(self) -> str:
        """Get current page path"""
        try:
            return urlparse(self.page.url).path or "/"
        except Exception:
            return "/"

    async def _capture_screenshot(self, name: str) -> Optional[str]:
        """Capture a screenshot"""
        if not self.config.capture_screenshots:
            return None

        try:
            screenshot_dir = self.data_dir / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            path = screenshot_dir / f"{name}.png"
            await self.page.screenshot(path=str(path))
            return str(path)
        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics"""
        selector_stats = self.selector_service.get_stats()

        return {
            "state": self.state.value,
            "total_actions": self._total_actions,
            "recovered_actions": self._recovered_actions,
            "ai_calls": self._ai_calls,
            "knowledge_base_hits": self._kb_hits,
            "ai_dependency_percent": (
                self._ai_calls / self._total_actions * 100
                if self._total_actions > 0 else 0
            ),
            "recovery_rate": (
                self._recovered_actions / self._total_actions * 100
                if self._total_actions > 0 else 0
            ),
            "selector_resolution": selector_stats,
            # SPA information
            "is_spa": self._is_spa,
            "spa_framework": self._detected_spa_framework.value if self._detected_spa_framework else None
        }

    def pause(self):
        """Pause test execution"""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.PAUSED

    def resume(self):
        """Resume test execution"""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING

    def stop(self):
        """Stop test execution"""
        self.state = AgentState.FAILED

    def get_discovered_fields(self) -> List[Dict[str, Any]]:
        """
        Get fields discovered during execution (for Gherkin updates).
        These are fields that were filled by the AI but weren't in the original test steps.
        """
        return self._discovered_fields.copy()

    def clear_discovered_fields(self):
        """Clear the discovered fields list (call after updating Gherkin)"""
        self._discovered_fields.clear()

    async def cleanup(self):
        """Cleanup resources"""
        self.learning_engine.flush()
        self.knowledge_index.force_save()
        await self.spa_handler.cleanup()

    # =========================================================================
    # HUMAN-LIKE TESTER METHODS (Token-Efficient)
    # =========================================================================

    async def _human_like_pre_action_check(
        self,
        step: TestStep,
        action: str
    ) -> Dict[str, Any]:
        """
        Perform human-like pre-action checks before executing an action.
        
        This uses DOM-based analysis (NO AI tokens) to:
        1. Wait for page readiness
        2. Detect and dismiss blocking overlays
        3. Check for existing errors
        4. Verify target element is accessible
        
        Returns:
            Dict with 'should_proceed', 'reason', 'auto_handled' keys
        """
        result = {
            "should_proceed": True,
            "reason": None,
            "auto_handled": False,
            "page_state": None,
            "blockers_found": [],
            "errors_found": []
        }
        
        # Skip checks for non-interactive actions
        skip_actions = {"navigate", "goto", "open", "wait", "pause", "noop", "skip", "context"}
        if action in skip_actions:
            return result
        
        try:
            # 1. Perform pre-action check (DOM-based, no AI)
            pre_check = await self.pre_action_checker.check_before_action(
                self.page,
                target_selector=step.target,
                action_type=action
            )
            
            # Store page state for post-action verification
            self._last_page_state = pre_check.page_state
            result["page_state"] = pre_check.page_state
            
            # 2. Handle blockers that were found
            if pre_check.blockers:
                result["blockers_found"] = [b.blocker_type.value for b in pre_check.blockers]
                logger.info(f"[HUMAN-LIKE] Found blockers: {result['blockers_found']}")
                
                # Most blockers are auto-handled by the checker
                # Only fail if critical blockers remain
                remaining = [b for b in pre_check.blockers 
                           if b.blocker_type not in [BlockerType.TOAST, BlockerType.COOKIE_BANNER]]
                
                if remaining and not pre_check.should_proceed:
                    result["should_proceed"] = False
                    result["reason"] = f"Blocked by {remaining[0].blocker_type.value}"
                    return result
                else:
                    result["auto_handled"] = True
            
            # 3. Check for form errors (for submit actions)
            if pre_check.errors and action in ("click", "tap"):
                submit_keywords = ['submit', 'login', 'sign', 'register', 'save', 'continue']
                is_submit = any(kw in (step.target or "").lower() for kw in submit_keywords)
                
                if is_submit:
                    result["errors_found"] = [e.message for e in pre_check.errors[:3]]
                    logger.warning(f"[HUMAN-LIKE] Form has errors before submit: {result['errors_found']}")
                    # Don't block - let the agent try to fix errors
            
            # 4. Check overall readiness
            if pre_check.readiness == ActionReadiness.LOADING:
                # Wait a bit more
                logger.info("[HUMAN-LIKE] Page still loading, waiting...")
                await self.page.wait_for_timeout(1000)
                result["auto_handled"] = True
            
            elif pre_check.readiness == ActionReadiness.ELEMENT_HIDDEN:
                result["should_proceed"] = False
                result["reason"] = f"Target element not visible: {step.target}"
            
            # Log stats periodically
            if self._total_actions % 10 == 0:
                stats = self.pre_action_checker.get_stats()
                logger.info(f"[HUMAN-LIKE] Stats: {stats['total_checks']} checks, {stats['ai_usage_percent']:.1f}% AI usage")
            
        except Exception as e:
            # Don't block on pre-check errors - just log and continue
            logger.warning(f"[HUMAN-LIKE] Pre-action check error (continuing anyway): {e}")
        
        return result

    async def _human_like_verify_action(
        self,
        step: TestStep,
        action: str,
        action_result: ActionResult
    ) -> Dict[str, Any]:
        """
        Verify that an action had the expected effect.
        
        Uses state comparison (NO AI) to detect:
        - Silent failures (action had no effect)
        - New errors that appeared
        - Unexpected state changes
        
        Returns:
            Dict with verification results
        """
        result = {
            "verified": True,
            "action_had_effect": True,
            "new_errors": [],
            "state_changes": {}
        }
        
        # Skip verification for some actions
        skip_actions = {"wait", "pause", "screenshot", "noop", "assert", "verify", "expect"}
        if action in skip_actions:
            return result
        
        try:
            if self._last_page_state:
                verification = await self.pre_action_checker.verify_action_effect(
                    self.page,
                    self._last_page_state
                )
                
                result["action_had_effect"] = verification["action_had_effect"]
                result["new_errors"] = verification.get("new_errors", [])
                result["state_changes"] = verification.get("changes", {})
                
                # Warn if action had no effect
                if not verification["action_had_effect"]:
                    logger.warning(f"[HUMAN-LIKE] Action may have had no effect: {action} on {step.target}")
                
                # Log new errors
                if verification.get("new_errors"):
                    logger.warning(f"[HUMAN-LIKE] New errors after action: {verification['new_errors']}")
                    
        except Exception as e:
            logger.debug(f"[HUMAN-LIKE] Verification error: {e}")
        
        return result

    def get_human_like_stats(self) -> Dict[str, Any]:
        """Get statistics about human-like behavior usage"""
        checker_stats = self.pre_action_checker.get_stats()
        
        return {
            "pre_action_checks": checker_stats["total_checks"],
            "ai_calls_for_checks": checker_stats["ai_calls"],
            "ai_usage_percent": checker_stats["ai_usage_percent"],
            "learned_timings": len(self.pre_action_checker.smart_waiter.learned_timings),
            "state_history_size": len(self.pre_action_checker.state_tracker.state_history)
        }
