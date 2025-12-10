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

        # State
        self.state = AgentState.IDLE
        self._current_test: Optional[str] = None
        self._current_domain: Optional[str] = None
        self._is_spa: bool = False
        self._detected_spa_framework: Optional[SPAFramework] = None

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

    # ==================== Main Execution ====================


    async def _smart_find_element(self, target, action_type="click"):
        """Smart element finding with multiple strategies"""
        if not target:
            return None

        target_lower = target.lower().strip()

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
            try:
                loc = self.page.get_by_text(target, exact=False)
                if await loc.count() > 0:
                    return loc.first
            except: pass
            try:
                loc = self.page.get_by_role("button", name=target)
                if await loc.count() > 0:
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
        base_url: Optional[str] = None
    ) -> TestResult:
        """
        Execute a test case autonomously.

        Args:
            test_case: Test case definition with steps
            base_url: Optional base URL to navigate to first

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

        # Navigate to base URL if provided
        if base_url:
            logger.info(f"Navigating to base URL: {base_url}")
            nav_result = await self.action_executor.navigate(base_url)
            if nav_result.status != ActionStatus.SUCCESS:
                errors.append(f"Failed to navigate to {base_url}: {nav_result.error_message}")

            # Wait for page to load
            logger.info("Waiting for page load...")
            await asyncio.sleep(1)

            # Detect framework from page (both SPA and UI library) - with timeout
            logger.info("Detecting framework...")
            try:
                await asyncio.wait_for(self._detect_framework(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Framework detection timed out")

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

        try:
            # Handle different action types
            if action in ("click", "tap"):
                action_result = await self._execute_click(step)
            elif action in ("type", "fill", "input"):
                action_result = await self._execute_type(step)
            elif action in ("select", "choose"):
                action_result = await self._execute_select(step)
            elif action in ("check", "checkbox"):
                action_result = await self._execute_check(step, check=True)
            elif action in ("uncheck",):
                action_result = await self._execute_check(step, check=False)
            elif action in ("navigate", "goto", "open"):
                action_result = await self._execute_navigate(step)
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
        """Execute a click action with smart finding"""
        from datetime import datetime
        start = datetime.utcnow()

        # Try smart finding first
        locator = await self._smart_find_element(step.target, "click")
        if locator:
            try:
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
        """Execute an assertion"""
        if not step.target:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert",
                selector="",
                selector_type="unknown",
                execution_time_ms=0,
                error_message="No target specified for assertion"
            )

        selector_result = await self._resolve_selector(step.target)

        if not selector_result.selector:
            return ActionResult(
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="assert",
                selector=step.target,
                selector_type="unknown",
                execution_time_ms=0,
                error_message="Could not resolve selector for assertion"
            )

        # Determine assertion type
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
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="assert_visible",
                selector=step.target,
                selector_type="unknown",
                execution_time_ms=0,
                error_message="Could not resolve selector for visibility assertion"
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
                status=ActionStatus.ELEMENT_NOT_FOUND,
                action="assert_text",
                selector=step.target,
                selector_type="unknown",
                execution_time_ms=0,
                error_message="Could not resolve selector for text assertion"
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

    async def cleanup(self):
        """Cleanup resources"""
        self.learning_engine.flush()
        self.knowledge_index.force_save()
        await self.spa_handler.cleanup()
