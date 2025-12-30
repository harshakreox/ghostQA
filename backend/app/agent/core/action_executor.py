"""
Action Executor

Executes actions on web pages using Playwright.
Handles element location, action execution, and result verification.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class ActionStatus(Enum):
    """Status of an executed action"""
    SUCCESS = "success"
    ELEMENT_NOT_FOUND = "element_not_found"
    ELEMENT_NOT_VISIBLE = "element_not_visible"
    ELEMENT_NOT_ENABLED = "element_not_enabled"
    TIMEOUT = "timeout"
    ERROR = "error"
    RECOVERED = "recovered"


@dataclass
class ActionResult:
    """Result of executing an action"""
    status: ActionStatus
    action: str
    selector: str
    selector_type: str
    execution_time_ms: int
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    alternative_used: bool = False
    recovery_attempted: bool = False
    dom_changed: bool = False
    navigation_occurred: bool = False


class ActionExecutor:
    """
    Executes actions on web pages.

    Features:
    - Multiple selector strategy support
    - Automatic retries with alternatives
    - Visual feedback for debugging
    - Action timing and metrics
    """

    # Default timeouts in milliseconds
    DEFAULT_TIMEOUT = 10000
    DEFAULT_WAIT_AFTER_ACTION = 100

    def __init__(
        self,
        page=None,
        selector_service=None,
        learning_engine=None
    ):
        """
        Initialize action executor.

        Args:
            page: Playwright page object
            selector_service: SelectorService for resolving elements
            learning_engine: LearningEngine for recording results
        """
        self.page = page
        self.selector_service = selector_service
        self.learning_engine = learning_engine

        # Configuration
        self.timeout = self.DEFAULT_TIMEOUT
        self.wait_after_action = 500  # 500ms for debugging
        self.capture_screenshots = False
        self.highlight_elements = True  # ENABLED for debugging

        # Callbacks
        self._before_action_callback: Optional[Callable] = None
        self._after_action_callback: Optional[Callable] = None

    def set_page(self, page):
        """Set the Playwright page object"""
        self.page = page

    def set_callbacks(
        self,
        before_action: Optional[Callable] = None,
        after_action: Optional[Callable] = None
    ):
        """Set action callbacks for hooks"""
        self._before_action_callback = before_action
        self._after_action_callback = after_action

    # ==================== Core Actions ====================

    async def click(
        self,
        selector: str,
        selector_type: str = "css",
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None,
        intent: Optional[str] = None
    ) -> ActionResult:
        """
        Click an element.

        Args:
            selector: Element selector
            selector_type: Type of selector
            alternatives: Alternative selectors to try
            timeout: Custom timeout
            intent: Original intent/target for learning

        Returns:
            ActionResult
        """
        return await self._execute_action(
            action="click",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=self._do_click,
            intent=intent
        )

    async def fill(
        self,
        selector: str,
        value: str,
        selector_type: str = "css",
        alternatives: Optional[List[Dict]] = None,
        clear_first: bool = True,
        timeout: Optional[int] = None,
        intent: Optional[str] = None
    ) -> ActionResult:
        """
        Fill an input element.

        Args:
            selector: Element selector
            value: Value to type
            selector_type: Type of selector
            alternatives: Alternative selectors
            clear_first: Clear existing value first
            timeout: Custom timeout
            intent: Original intent/target for learning

        Returns:
            ActionResult
        """
        return await self._execute_action(
            action="fill",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: self._do_fill(loc, value, clear_first),
            intent=intent
        )

    async def type_text(
        self,
        selector: str,
        value: str,
        selector_type: str = "css",
        delay: int = 50,
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None
    ) -> ActionResult:
        """
        Type text into an element character by character.

        Args:
            selector: Element selector
            value: Value to type
            selector_type: Type of selector
            delay: Delay between keystrokes in ms
            alternatives: Alternative selectors
            timeout: Custom timeout

        Returns:
            ActionResult
        """
        return await self._execute_action(
            action="type",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: self._do_type(loc, value, delay)
        )

    async def select_option(
        self,
        selector: str,
        value: Union[str, List[str]],
        selector_type: str = "css",
        by: str = "value",
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None,
        intent: Optional[str] = None
    ) -> ActionResult:
        """
        Select option(s) from a dropdown.

        Args:
            selector: Element selector
            value: Value(s) to select
            selector_type: Type of selector
            by: Selection method (value, label, index)
            alternatives: Alternative selectors
            timeout: Custom timeout
            intent: Original intent/target for learning

        Returns:
            ActionResult
        """
        return await self._execute_action(
            action="select",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: self._do_select(loc, value, by),
            intent=intent
        )

    async def check(
        self,
        selector: str,
        selector_type: str = "css",
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None,
        intent: Optional[str] = None
    ) -> ActionResult:
        """Check a checkbox"""
        return await self._execute_action(
            action="check",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: loc.check(),
            intent=intent
        )

    async def uncheck(
        self,
        selector: str,
        selector_type: str = "css",
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None,
        intent: Optional[str] = None
    ) -> ActionResult:
        """Uncheck a checkbox"""
        return await self._execute_action(
            action="uncheck",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: loc.uncheck(),
            intent=intent
        )

    async def hover(
        self,
        selector: str,
        selector_type: str = "css",
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None
    ) -> ActionResult:
        """Hover over an element"""
        return await self._execute_action(
            action="hover",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: loc.hover()
        )

    async def double_click(
        self,
        selector: str,
        selector_type: str = "css",
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None
    ) -> ActionResult:
        """Double-click an element"""
        return await self._execute_action(
            action="double_click",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: loc.dblclick()
        )

    async def press_key(
        self,
        key: str,
        selector: Optional[str] = None,
        selector_type: str = "css"
    ) -> ActionResult:
        """
        Press a keyboard key.

        Args:
            key: Key to press (e.g., "Enter", "Tab", "Escape")
            selector: Optional element to focus first
            selector_type: Type of selector

        Returns:
            ActionResult
        """
        start_time = datetime.utcnow()

        try:
            if selector:
                locator = self._get_locator(selector, selector_type)
                await locator.press(key)
            else:
                await self.page.keyboard.press(key)

            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="press_key",
                selector=selector or "page",
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="press_key",
                selector=selector or "page",
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: Optional[str] = None,
        selector_type: str = "css"
    ) -> ActionResult:
        """
        Scroll the page or element.

        Args:
            direction: Scroll direction (up, down, left, right)
            amount: Pixels to scroll
            selector: Optional element to scroll within
            selector_type: Type of selector

        Returns:
            ActionResult
        """
        start_time = datetime.utcnow()

        delta_x, delta_y = 0, 0
        if direction == "down":
            delta_y = amount
        elif direction == "up":
            delta_y = -amount
        elif direction == "right":
            delta_x = amount
        elif direction == "left":
            delta_x = -amount

        try:
            if selector:
                locator = self._get_locator(selector, selector_type)
                await locator.evaluate(f"el => el.scrollBy({delta_x}, {delta_y})")
            else:
                await self.page.evaluate(f"window.scrollBy({delta_x}, {delta_y})")

            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="scroll",
                selector=selector or "page",
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="scroll",
                selector=selector or "page",
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def upload_file(
        self,
        selector: str,
        file_path: Union[str, List[str]],
        selector_type: str = "css",
        alternatives: Optional[List[Dict]] = None,
        timeout: Optional[int] = None
    ) -> ActionResult:
        """Upload file(s) to a file input"""
        return await self._execute_action(
            action="upload",
            selector=selector,
            selector_type=selector_type,
            alternatives=alternatives,
            timeout=timeout,
            action_fn=lambda loc: loc.set_input_files(file_path)
        )

    # ==================== Navigation Actions ====================

    async def navigate(self, url: str, wait_until: str = "networkidle") -> ActionResult:
        """Navigate to a URL"""
        start_time = datetime.utcnow()

        try:
            await self.page.goto(url, wait_until=wait_until, timeout=30000)

            # Wait for DOM to be fully ready
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass

            # Disable autocomplete on all form inputs to prevent browser from overwriting our values
            try:
                await self.page.evaluate("""() => {
                    // Disable on all forms
                    document.querySelectorAll('form').forEach(form => {
                        form.setAttribute('autocomplete', 'off');
                    });
                    // Disable on all inputs
                    document.querySelectorAll('input').forEach(input => {
                        input.setAttribute('autocomplete', 'off');
                        input.setAttribute('data-lpignore', 'true');
                        input.setAttribute('data-form-type', 'other');
                    });
                }""")
            except Exception:
                pass  # Not critical

            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="navigate",
                selector=url,
                selector_type="url",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                navigation_occurred=True
            )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="navigate",
                selector=url,
                selector_type="url",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def go_back(self) -> ActionResult:
        """Go back in browser history"""
        start_time = datetime.utcnow()

        try:
            await self.page.go_back()
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="go_back",
                selector="history",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                navigation_occurred=True
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="go_back",
                selector="history",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def go_forward(self) -> ActionResult:
        """Go forward in browser history"""
        start_time = datetime.utcnow()

        try:
            await self.page.go_forward()
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="go_forward",
                selector="history",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                navigation_occurred=True
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="go_forward",
                selector="history",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def refresh(self) -> ActionResult:
        """Refresh the current page"""
        start_time = datetime.utcnow()

        try:
            await self.page.reload()
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="refresh",
                selector="page",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                navigation_occurred=True
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="refresh",
                selector="page",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    # ==================== Wait Actions ====================

    async def wait_for_element(
        self,
        selector: str,
        selector_type: str = "css",
        state: str = "visible",
        timeout: Optional[int] = None
    ) -> ActionResult:
        """Wait for an element to reach a state"""
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout

        try:
            locator = self._get_locator(selector, selector_type)

            if state == "visible":
                await locator.wait_for(state="visible", timeout=timeout)
            elif state == "hidden":
                await locator.wait_for(state="hidden", timeout=timeout)
            elif state == "attached":
                await locator.wait_for(state="attached", timeout=timeout)
            elif state == "detached":
                await locator.wait_for(state="detached", timeout=timeout)

            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="wait_for_element",
                selector=selector,
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.TIMEOUT if "timeout" in str(e).lower() else ActionStatus.ERROR,
                action="wait_for_element",
                selector=selector,
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def wait_for_navigation(self, timeout: Optional[int] = None) -> ActionResult:
        """Wait for navigation to complete"""
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout

        try:
            await self.page.wait_for_load_state("load", timeout=timeout)
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action="wait_for_navigation",
                selector="page",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                navigation_occurred=True
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.TIMEOUT if "timeout" in str(e).lower() else ActionStatus.ERROR,
                action="wait_for_navigation",
                selector="page",
                selector_type="browser",
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def wait(self, milliseconds: int) -> ActionResult:
        """Wait for a specified time"""
        start_time = datetime.utcnow()
        await asyncio.sleep(milliseconds / 1000)
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action="wait",
            selector=str(milliseconds),
            selector_type="time",
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
        )

    # ==================== Assertion Actions ====================

    async def assert_url(
        self,
        expected_url: str,
        match_type: str = "contains",
        timeout: Optional[int] = None
    ) -> ActionResult:
        """
        Assert the current URL matches expected.

        Works for both MPA (full page loads) and SPA (client-side routing).

        Args:
            expected_url: The URL or pattern to match
            match_type: How to match - 'exact', 'contains', 'startswith', 'endswith', 'regex'
            timeout: Time to wait for URL to match
        """
        import re
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout

        # Try multiple wait strategies for both MPA and SPA
        try:
            # First try networkidle (works for MPA)
            await self.page.wait_for_load_state("networkidle", timeout=min(timeout, 5000))
        except Exception:
            pass

        # Also wait for DOM to stabilize (works for SPA)
        try:
            await self._wait_for_dom_stable(timeout=2000)
        except Exception:
            pass

        # Poll for URL match with timeout (max 10 seconds for URL assertions)
        effective_timeout = min(timeout, 10000)
        end_time = datetime.utcnow().timestamp() + (effective_timeout / 1000)
        last_url = ""
        check_count = 0

        logger.info(f"assert_url: Checking for '{expected_url}' in URL (timeout: {effective_timeout}ms)")

        while datetime.utcnow().timestamp() < end_time:
            try:
                current_url = self.page.url
                last_url = current_url
                check_count += 1

                if check_count <= 3 or check_count % 10 == 0:
                    logger.debug(f"assert_url check #{check_count}: current_url='{current_url}'")

                matched = False
                if match_type == "exact":
                    matched = current_url == expected_url
                elif match_type == "contains":
                    matched = expected_url in current_url
                elif match_type == "startswith":
                    matched = current_url.startswith(expected_url)
                elif match_type == "endswith":
                    matched = current_url.endswith(expected_url)
                elif match_type == "regex":
                    matched = bool(re.search(expected_url, current_url))
                else:
                    # Default to contains
                    matched = expected_url in current_url

                if matched:
                    return ActionResult(
                        status=ActionStatus.SUCCESS,
                        action="assert_url",
                        selector=expected_url,
                        selector_type="url",
                        execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    )

                await asyncio.sleep(0.2)  # Poll every 200ms

            except Exception:
                await asyncio.sleep(0.2)
                continue

        return ActionResult(
            status=ActionStatus.ERROR,
            action="assert_url",
            selector=expected_url,
            selector_type="url",
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            error_message=f"URL assertion failed. Expected '{expected_url}' ({match_type}) but got '{last_url}'"
        )

    async def assert_visible(
        self,
        selector: str,
        selector_type: str = "css",
        timeout: Optional[int] = None
    ) -> ActionResult:
        """Assert element is visible with smart waiting for MPA and SPA"""
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout

        # Wait for page to be ready - try multiple strategies
        try:
            # networkidle for MPA
            await self.page.wait_for_load_state("networkidle", timeout=min(timeout, 5000))
        except Exception:
            pass

        # DOM stability for SPA
        try:
            await self._wait_for_dom_stable(timeout=2000)
        except Exception:
            pass

        try:
            locator = self._get_locator(selector, selector_type)
            # Wait for element to be visible with timeout
            await locator.wait_for(state="visible", timeout=timeout)
            is_visible = await locator.is_visible()

            if is_visible:
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="assert_visible",
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            else:
                return ActionResult(
                    status=ActionStatus.ERROR,
                    action="assert_visible",
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    error_message="Element exists but is not visible"
                )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert_visible",
                selector=selector,
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=f"Visibility assertion failed: {str(e)}"
            )

    async def assert_text(
        self,
        selector: str,
        expected_text: str,
        selector_type: str = "css",
        timeout: Optional[int] = None
    ) -> ActionResult:
        """Assert element contains text"""
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout

        try:
            locator = self._get_locator(selector, selector_type)
            await locator.wait_for(state="visible", timeout=timeout)
            actual_text = await locator.text_content()

            if expected_text in (actual_text or ""):
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="assert_text",
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            else:
                return ActionResult(
                    status=ActionStatus.ERROR,
                    action="assert_text",
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    error_message=f"Expected '{expected_text}' but got '{actual_text}'"
                )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert_text",
                selector=selector,
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def assert_value(
        self,
        selector: str,
        expected_value: str,
        selector_type: str = "css",
        timeout: Optional[int] = None
    ) -> ActionResult:
        """Assert input element has value"""
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout

        try:
            locator = self._get_locator(selector, selector_type)
            await locator.wait_for(state="visible", timeout=timeout)
            actual_value = await locator.input_value()

            if expected_value == actual_value:
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action="assert_value",
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            else:
                return ActionResult(
                    status=ActionStatus.ERROR,
                    action="assert_value",
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    error_message=f"Expected '{expected_value}' but got '{actual_value}'"
                )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action="assert_value",
                selector=selector,
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    # ==================== Internal Methods ====================

    def _get_locator(self, selector: str, selector_type: str):
        """Get a Playwright locator based on selector type"""
        if selector_type == "xpath":
            return self.page.locator(f"xpath={selector}")
        elif selector_type == "text":
            return self.page.get_by_text(selector)
        elif selector_type == "label":
            return self.page.get_by_label(selector)
        elif selector_type == "placeholder":
            return self.page.get_by_placeholder(selector)
        elif selector_type == "role":
            return self.page.get_by_role(selector)
        elif selector_type == "testid":
            return self.page.get_by_test_id(selector)
        else:
            return self.page.locator(selector)

    async def _execute_action(
        self,
        action: str,
        selector: str,
        selector_type: str,
        alternatives: Optional[List[Dict]],
        timeout: Optional[int],
        action_fn: Callable,
        intent: Optional[str] = None
    ) -> ActionResult:
        """Execute an action with retry logic"""
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout
        all_selectors = [{"selector": selector, "type": selector_type}]
        # Use intent for learning, fallback to selector if not provided
        element_key = intent or selector

        if alternatives:
            all_selectors.extend(alternatives)

        last_error = None
        alternative_used = False

        # Try each selector
        for i, sel_info in enumerate(all_selectors):
            sel = sel_info.get("selector", sel_info) if isinstance(sel_info, dict) else sel_info
            sel_type = sel_info.get("type", "css") if isinstance(sel_info, dict) else "css"

            try:
                # Before action callback
                if self._before_action_callback:
                    await self._before_action_callback(action, sel, sel_type)

                locator = self._get_locator(sel, sel_type)

                # Wait for element
                await locator.wait_for(state="visible", timeout=timeout)
                
                # Log what we're about to do
                print(f"[ACTION] {action.upper()} on {sel[:50]}...")
                logger.info(f"[ACTION] Executing {action} on selector: {sel}")

                # Highlight if enabled
                if self.highlight_elements:
                    await self._highlight_element(locator)

                # Execute the action
                await action_fn(locator)

                # Wait after action
                if self.wait_after_action > 0:
                    await asyncio.sleep(self.wait_after_action / 1000)

                # After action callback
                if self._after_action_callback:
                    await self._after_action_callback(action, sel, sel_type, True)

                # Record success
                if self.learning_engine:
                    self.learning_engine.record_selector_result(
                        domain=self._get_domain(),
                        page=self._get_page(),
                        element_key=element_key,  # Use intent for key
                        selector=sel,
                        success=True,
                        selector_type=sel_type
                    )

                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action=action,
                    selector=sel,
                    selector_type=sel_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    alternative_used=(i > 0)
                )

            except Exception as e:
                last_error = str(e)
                alternative_used = True

                # Record failure
                if self.learning_engine:
                    self.learning_engine.record_selector_result(
                        domain=self._get_domain(),
                        page=self._get_page(),
                        element_key=element_key,  # Use intent for key
                        selector=sel,
                        success=False,
                        selector_type=sel_type
                    )

                logger.warning(f"Action {action} failed with selector {sel}: {e}")
                continue

        # All selectors failed
        return ActionResult(
            status=ActionStatus.ELEMENT_NOT_FOUND,
            action=action,
            selector=selector,
            selector_type=selector_type,
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            error_message=last_error,
            alternative_used=alternative_used
        )

    async def _execute_assertion(
        self,
        action: str,
        selector: str,
        selector_type: str,
        timeout: Optional[int],
        check_fn: Callable
    ) -> ActionResult:
        """Execute an assertion"""
        start_time = datetime.utcnow()
        timeout = timeout or self.timeout

        try:
            locator = self._get_locator(selector, selector_type)
            await locator.wait_for(state="attached", timeout=timeout)
            result = await check_fn(locator)

            if result:
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action=action,
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            else:
                return ActionResult(
                    status=ActionStatus.ERROR,
                    action=action,
                    selector=selector,
                    selector_type=selector_type,
                    execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    error_message="Assertion failed"
                )

        except Exception as e:
            return ActionResult(
                status=ActionStatus.ERROR,
                action=action,
                selector=selector,
                selector_type=selector_type,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                error_message=str(e)
            )

    async def _do_click(self, locator):
        """Execute click action with smart navigation/SPA detection"""
        # Get current URL before click
        url_before = self.page.url

        # Click the element
        await locator.click()

        # Small wait to see if navigation/SPA route change starts
        await asyncio.sleep(0.5)

        # Check if URL changed (MPA navigation or SPA route change)
        url_after = self.page.url
        if url_before != url_after:
            # Navigation happened, wait for it to complete
            logger.info(f"Navigation detected: {url_before} -> {url_after}")
            try:
                # Wait for page load or network idle
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                # Continue if timeout, the page may have loaded enough
                pass
        else:
            # URL didn't change - might be SPA with internal state change
            # Wait for DOM to stabilize (handles SPA re-renders)
            try:
                await self._wait_for_dom_stable(timeout=3000)
            except Exception:
                pass

    async def _wait_for_dom_stable(self, timeout: int = 3000) -> bool:
        """Wait for DOM to stop changing (useful for SPAs)"""
        try:
            await self.page.evaluate("""
                window.__ghostqa_dom_mutations = 0;
                if (!window.__ghostqa_dom_observer) {
                    window.__ghostqa_dom_observer = new MutationObserver((mutations) => {
                        window.__ghostqa_dom_mutations += mutations.length;
                    });
                    window.__ghostqa_dom_observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true
                    });
                }
            """)

            # Wait for mutations to stop
            check_interval = 100  # ms
            stable_checks = 0
            required_stable = 3
            last_count = 0

            start = datetime.utcnow()
            while (datetime.utcnow() - start).total_seconds() * 1000 < timeout:
                current = await self.page.evaluate("window.__ghostqa_dom_mutations || 0")
                if current == last_count:
                    stable_checks += 1
                    if stable_checks >= required_stable:
                        break
                else:
                    stable_checks = 0
                    last_count = current
                await asyncio.sleep(check_interval / 1000)

            # Cleanup
            await self.page.evaluate("""
                if (window.__ghostqa_dom_observer) {
                    window.__ghostqa_dom_observer.disconnect();
                    delete window.__ghostqa_dom_observer;
                    delete window.__ghostqa_dom_mutations;
                }
            """)
            return True

        except Exception:
            return False

    async def _do_fill(self, locator, value: str, clear_first: bool):
        """Execute fill action with REAL user simulation for proper form validation"""
        # fill() alone doesn't trigger React/Vue/Angular events!
        # Simulate real user: click -> clear -> type char by char -> tab out

        print(f"[FILL] Typing value: '{value}' (len={len(value) if value else 0})")
        logger.info(f"[FILL] About to type: {value}")

        # Step 0: Disable browser autocomplete to prevent it from overwriting our value
        try:
            await locator.evaluate("""el => {
                el.setAttribute('autocomplete', 'off');
                el.setAttribute('data-lpignore', 'true');  // LastPass
                el.setAttribute('data-form-type', 'other');  // Dashlane
            }""")
        except Exception:
            pass  # Not critical if this fails

        # Step 1: Click to focus
        await locator.click()
        await self.page.wait_for_timeout(200)  # Increased for debugging

        # Step 2: Clear with keyboard
        if clear_first:
            await locator.press("Control+a")
            await self.page.wait_for_timeout(50)

        # Step 3: Type character by character
        if value:
            await locator.press_sequentially(value, delay=30)
        else:
            await locator.press("Backspace")

        # Step 4: Tab out to trigger blur/validation
        await self.page.wait_for_timeout(200)
        await locator.press("Tab")
        await self.page.wait_for_timeout(500)  # 500ms wait after tab
        print(f"[FILL] Completed typing and tabbed out")

    async def _do_type(self, locator, value: str, delay: int):
        """Execute type action with real user simulation"""
        await locator.click()
        await self.page.wait_for_timeout(100)
        await locator.press_sequentially(value, delay=delay)
        await self.page.wait_for_timeout(100)
        await locator.press("Tab")

    async def _do_select(self, locator, value, by: str):
        """Execute select action"""
        if by == "value":
            await locator.select_option(value=value)
        elif by == "label":
            await locator.select_option(label=value)
        elif by == "index":
            await locator.select_option(index=int(value))

    async def _highlight_element(self, locator):
        """Highlight an element with visible animation and cursor indicator"""
        try:
            # Get element position for cursor indicator
            box = await locator.bounding_box()
            if box:
                # Create a visible cursor indicator at element center
                cx, cy = box['x'] + box['width']/2, box['y'] + box['height']/2
                await self.page.evaluate("""
                    (args) => {
                        const {x, y} = args;
                        // Remove old cursor if exists
                        const old = document.getElementById('ghostqa-cursor');
                        if (old) old.remove();
                        
                        // Create cursor indicator
                        const cursor = document.createElement('div');
                        cursor.id = 'ghostqa-cursor';
                        cursor.style.cssText = `
                            position: fixed;
                            left: ${x}px;
                            top: ${y}px;
                            width: 30px;
                            height: 30px;
                            border-radius: 50%;
                            background: rgba(255, 0, 0, 0.5);
                            border: 3px solid red;
                            z-index: 999999;
                            pointer-events: none;
                            transform: translate(-50%, -50%);
                            animation: ghostqa-pulse 0.5s ease-in-out 3;
                        `;
                        document.body.appendChild(cursor);
                        
                        // Add pulse animation
                        if (!document.getElementById('ghostqa-style')) {
                            const style = document.createElement('style');
                            style.id = 'ghostqa-style';
                            style.textContent = `
                                @keyframes ghostqa-pulse {
                                    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
                                    50% { transform: translate(-50%, -50%) scale(1.5); opacity: 0.5; }
                                }
                            `;
                            document.head.appendChild(style);
                        }
                        
                        // Remove cursor after animation
                        setTimeout(() => cursor.remove(), 2000);
                    }
                """, {'x': cx, 'y': cy})
            
            # Also highlight the element with bold outline
            await locator.evaluate("""
                (el) => {
                    const orig = el.style.outline;
                    const origBg = el.style.backgroundColor;
                    el.style.outline = '4px solid #FF0000';
                    el.style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
                    setTimeout(() => {
                        el.style.outline = orig;
                        el.style.backgroundColor = origBg;
                    }, 2000);
                }
            """)
            
            # Give time to see the highlight
            await self.page.wait_for_timeout(300)
            
        except Exception as e:
            logger.debug(f"Highlight failed: {e}")


    def _get_domain(self) -> str:
        """Get current page domain"""
        try:
            from urllib.parse import urlparse
            return urlparse(self.page.url).netloc
        except Exception:
            return "unknown"

    def _get_page(self) -> str:
        """Get current page path"""
        try:
            from urllib.parse import urlparse
            return urlparse(self.page.url).path or "/"
        except Exception:
            return "/"
