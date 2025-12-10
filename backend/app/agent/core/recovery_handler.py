"""
Recovery Handler

Handles error recovery during test execution.
Implements smart recovery strategies based on the type of failure.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures that can occur"""
    ELEMENT_NOT_FOUND = "element_not_found"
    ELEMENT_NOT_VISIBLE = "element_not_visible"
    ELEMENT_NOT_ENABLED = "element_not_enabled"
    ELEMENT_STALE = "element_stale"
    ELEMENT_INTERCEPTED = "element_intercepted"
    TIMEOUT = "timeout"
    NAVIGATION_ERROR = "navigation_error"
    NETWORK_ERROR = "network_error"
    DIALOG_BLOCKING = "dialog_blocking"
    MODAL_BLOCKING = "modal_blocking"
    COOKIE_BANNER = "cookie_banner"
    LOADING_SPINNER = "loading_spinner"
    FRAME_SWITCH_NEEDED = "frame_switch_needed"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Types of recovery actions"""
    WAIT_AND_RETRY = "wait_and_retry"
    SCROLL_INTO_VIEW = "scroll_into_view"
    DISMISS_MODAL = "dismiss_modal"
    DISMISS_DIALOG = "dismiss_dialog"
    DISMISS_COOKIE_BANNER = "dismiss_cookie_banner"
    WAIT_FOR_LOADING = "wait_for_loading"
    REFRESH_PAGE = "refresh_page"
    SWITCH_FRAME = "switch_frame"
    SWITCH_TO_MAIN = "switch_to_main"
    USE_ALTERNATIVE_SELECTOR = "use_alternative_selector"
    FORCE_CLICK = "force_click"
    JS_CLICK = "js_click"
    CLEAR_OVERLAYS = "clear_overlays"
    RESIZE_VIEWPORT = "resize_viewport"
    NONE = "none"


@dataclass
class RecoveryResult:
    """Result of a recovery attempt"""
    success: bool
    action_taken: RecoveryAction
    details: str
    execution_time_ms: int
    should_retry_original: bool = True


class RecoveryHandler:
    """
    Handles error recovery during test execution.

    Features:
    - Automatic failure classification
    - Smart recovery strategy selection
    - Learning from successful recoveries
    - Multiple recovery attempts
    """

    # Maximum recovery attempts per failure
    MAX_RECOVERY_ATTEMPTS = 3

    # Common selectors for dismissing overlays
    MODAL_DISMISS_SELECTORS = [
        '[data-dismiss="modal"]',
        '[aria-label="Close"]',
        '[aria-label="close"]',
        '.modal-close',
        '.close-button',
        '.close-modal',
        '.btn-close',
        'button:has-text("Close")',
        'button:has-text("×")',
        '[class*="close"]',
        '.modal-header button',
        '[data-testid*="close"]'
    ]

    COOKIE_BANNER_SELECTORS = [
        '[data-testid*="cookie"] button',
        '[class*="cookie"] button:has-text("Accept")',
        '[class*="cookie"] button:has-text("OK")',
        '[class*="cookie"] button:has-text("Got it")',
        '[class*="cookie"] button:has-text("I agree")',
        '[class*="consent"] button',
        '#cookie-accept',
        '.cookie-accept',
        '#accept-cookies',
        '.accept-cookies',
        '[aria-label*="cookie"] button',
        '[id*="cookie"] button:first-child',
        '.cc-btn.cc-dismiss',
        '[class*="gdpr"] button'
    ]

    LOADING_INDICATORS = [
        '.loading',
        '.spinner',
        '.loader',
        '[class*="loading"]',
        '[class*="spinner"]',
        '[class*="loader"]',
        '[data-loading="true"]',
        '.MuiCircularProgress-root',
        '.ant-spin',
        '.sk-spinner'
    ]

    def __init__(
        self,
        page=None,
        learning_engine=None
    ):
        """
        Initialize recovery handler.

        Args:
            page: Playwright page object
            learning_engine: LearningEngine for recording successful recoveries
        """
        self.page = page
        self.learning_engine = learning_engine

        # Recovery attempt tracking
        self._recovery_attempts: Dict[str, int] = {}

        # Successful recovery cache
        self._successful_recoveries: Dict[FailureType, List[RecoveryAction]] = {}

    def set_page(self, page):
        """Set the Playwright page object"""
        self.page = page

    def classify_failure(self, error: Exception, context: Dict[str, Any] = None) -> FailureType:
        """
        Classify a failure based on the error and context.

        Args:
            error: The exception that occurred
            context: Additional context about the failure

        Returns:
            Classified failure type
        """
        error_str = str(error).lower()
        context = context or {}

        # Element not found
        if any(msg in error_str for msg in ["no element", "not found", "unable to locate"]):
            return FailureType.ELEMENT_NOT_FOUND

        # Element not visible
        if any(msg in error_str for msg in ["not visible", "hidden", "display: none"]):
            return FailureType.ELEMENT_NOT_VISIBLE

        # Element not enabled
        if any(msg in error_str for msg in ["disabled", "not enabled", "readonly"]):
            return FailureType.ELEMENT_NOT_ENABLED

        # Stale element
        if any(msg in error_str for msg in ["stale", "detached", "no longer attached"]):
            return FailureType.ELEMENT_STALE

        # Element intercepted (another element is covering it)
        if any(msg in error_str for msg in ["intercepted", "covered", "obscured", "other element"]):
            return FailureType.ELEMENT_INTERCEPTED

        # Timeout
        if "timeout" in error_str:
            return FailureType.TIMEOUT

        # Navigation error
        if any(msg in error_str for msg in ["navigation", "net::", "err_"]):
            return FailureType.NAVIGATION_ERROR

        # Check context for additional clues
        if context.get("has_modal"):
            return FailureType.MODAL_BLOCKING

        if context.get("has_dialog"):
            return FailureType.DIALOG_BLOCKING

        if context.get("in_frame"):
            return FailureType.FRAME_SWITCH_NEEDED

        return FailureType.UNKNOWN

    def get_recovery_strategy(
        self,
        failure_type: FailureType,
        context: Dict[str, Any] = None
    ) -> List[RecoveryAction]:
        """
        Get ordered list of recovery actions to try.

        Args:
            failure_type: Type of failure
            context: Additional context

        Returns:
            List of recovery actions to try in order
        """
        # Check if we've successfully recovered from this before
        if failure_type in self._successful_recoveries:
            return self._successful_recoveries[failure_type] + self._get_default_strategy(failure_type)

        return self._get_default_strategy(failure_type)

    def _get_default_strategy(self, failure_type: FailureType) -> List[RecoveryAction]:
        """Get default recovery strategy for a failure type"""
        strategies = {
            FailureType.ELEMENT_NOT_FOUND: [
                RecoveryAction.WAIT_AND_RETRY,
                RecoveryAction.SCROLL_INTO_VIEW,
                RecoveryAction.WAIT_FOR_LOADING,
                RecoveryAction.SWITCH_TO_MAIN,
                RecoveryAction.REFRESH_PAGE
            ],
            FailureType.ELEMENT_NOT_VISIBLE: [
                RecoveryAction.SCROLL_INTO_VIEW,
                RecoveryAction.DISMISS_MODAL,
                RecoveryAction.CLEAR_OVERLAYS,
                RecoveryAction.WAIT_AND_RETRY
            ],
            FailureType.ELEMENT_NOT_ENABLED: [
                RecoveryAction.WAIT_AND_RETRY,
                RecoveryAction.WAIT_FOR_LOADING
            ],
            FailureType.ELEMENT_STALE: [
                RecoveryAction.WAIT_AND_RETRY,
                RecoveryAction.REFRESH_PAGE
            ],
            FailureType.ELEMENT_INTERCEPTED: [
                RecoveryAction.DISMISS_MODAL,
                RecoveryAction.DISMISS_COOKIE_BANNER,
                RecoveryAction.SCROLL_INTO_VIEW,
                RecoveryAction.CLEAR_OVERLAYS,
                RecoveryAction.JS_CLICK
            ],
            FailureType.TIMEOUT: [
                RecoveryAction.WAIT_FOR_LOADING,
                RecoveryAction.REFRESH_PAGE
            ],
            FailureType.MODAL_BLOCKING: [
                RecoveryAction.DISMISS_MODAL,
                RecoveryAction.CLEAR_OVERLAYS
            ],
            FailureType.DIALOG_BLOCKING: [
                RecoveryAction.DISMISS_DIALOG
            ],
            FailureType.COOKIE_BANNER: [
                RecoveryAction.DISMISS_COOKIE_BANNER
            ],
            FailureType.LOADING_SPINNER: [
                RecoveryAction.WAIT_FOR_LOADING
            ],
            FailureType.FRAME_SWITCH_NEEDED: [
                RecoveryAction.SWITCH_FRAME,
                RecoveryAction.SWITCH_TO_MAIN
            ],
            FailureType.UNKNOWN: [
                RecoveryAction.WAIT_AND_RETRY,
                RecoveryAction.CLEAR_OVERLAYS,
                RecoveryAction.REFRESH_PAGE
            ]
        }

        return strategies.get(failure_type, [RecoveryAction.NONE])

    async def attempt_recovery(
        self,
        failure_type: FailureType,
        context: Dict[str, Any] = None,
        selector: Optional[str] = None
    ) -> RecoveryResult:
        """
        Attempt to recover from a failure.

        Args:
            failure_type: Type of failure
            context: Additional context
            selector: Optional selector that failed

        Returns:
            RecoveryResult
        """
        context = context or {}
        recovery_key = f"{failure_type.value}:{selector or 'general'}"

        # Check attempt count
        attempt_count = self._recovery_attempts.get(recovery_key, 0)
        if attempt_count >= self.MAX_RECOVERY_ATTEMPTS:
            return RecoveryResult(
                success=False,
                action_taken=RecoveryAction.NONE,
                details="Max recovery attempts exceeded",
                execution_time_ms=0,
                should_retry_original=False
            )

        self._recovery_attempts[recovery_key] = attempt_count + 1

        # Get recovery strategy
        strategy = self.get_recovery_strategy(failure_type, context)

        # Try each recovery action
        for action in strategy:
            start_time = datetime.utcnow()

            try:
                success = await self._execute_recovery_action(action, selector, context)

                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                if success:
                    # Record successful recovery
                    if failure_type not in self._successful_recoveries:
                        self._successful_recoveries[failure_type] = []
                    if action not in self._successful_recoveries[failure_type]:
                        self._successful_recoveries[failure_type].insert(0, action)

                    # Record to learning engine
                    if self.learning_engine:
                        self.learning_engine.record_recovery_attempt(
                            domain=self._get_domain(),
                            page=self._get_page(),
                            problem_type=failure_type.value,
                            recovery_action=action.value,
                            success=True,
                            context=context
                        )

                    return RecoveryResult(
                        success=True,
                        action_taken=action,
                        details=f"Recovery successful with {action.value}",
                        execution_time_ms=execution_time,
                        should_retry_original=True
                    )

            except Exception as e:
                logger.warning(f"Recovery action {action.value} failed: {e}")
                continue

        return RecoveryResult(
            success=False,
            action_taken=RecoveryAction.NONE,
            details="All recovery actions failed",
            execution_time_ms=0,
            should_retry_original=False
        )

    async def _execute_recovery_action(
        self,
        action: RecoveryAction,
        selector: Optional[str],
        context: Dict[str, Any]
    ) -> bool:
        """Execute a specific recovery action"""
        if action == RecoveryAction.WAIT_AND_RETRY:
            await asyncio.sleep(1)
            return True

        elif action == RecoveryAction.SCROLL_INTO_VIEW:
            if selector:
                try:
                    locator = self.page.locator(selector)
                    await locator.scroll_into_view_if_needed()
                    return True
                except Exception:
                    # Try scrolling page instead
                    await self.page.evaluate("window.scrollBy(0, 300)")
                    return True
            return False

        elif action == RecoveryAction.DISMISS_MODAL:
            return await self._dismiss_modal()

        elif action == RecoveryAction.DISMISS_DIALOG:
            return await self._dismiss_dialog()

        elif action == RecoveryAction.DISMISS_COOKIE_BANNER:
            return await self._dismiss_cookie_banner()

        elif action == RecoveryAction.WAIT_FOR_LOADING:
            return await self._wait_for_loading()

        elif action == RecoveryAction.REFRESH_PAGE:
            await self.page.reload()
            await asyncio.sleep(1)
            return True

        elif action == RecoveryAction.SWITCH_FRAME:
            return await self._switch_to_frame(context.get("frame_selector"))

        elif action == RecoveryAction.SWITCH_TO_MAIN:
            # In Playwright, locators automatically handle frames
            return True

        elif action == RecoveryAction.CLEAR_OVERLAYS:
            return await self._clear_overlays()

        elif action == RecoveryAction.JS_CLICK:
            if selector:
                try:
                    await self.page.evaluate(f"""
                        document.querySelector('{selector}').click()
                    """)
                    return True
                except Exception:
                    return False
            return False

        elif action == RecoveryAction.FORCE_CLICK:
            if selector:
                try:
                    locator = self.page.locator(selector)
                    await locator.click(force=True)
                    return True
                except Exception:
                    return False
            return False

        return False

    async def _dismiss_modal(self) -> bool:
        """Try to dismiss any open modals"""
        for selector in self.MODAL_DISMISS_SELECTORS:
            try:
                locator = self.page.locator(selector).first
                if await locator.is_visible():
                    await locator.click()
                    await asyncio.sleep(0.5)
                    return True
            except Exception:
                continue

        # Try pressing Escape
        try:
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
            return True
        except Exception:
            pass

        return False

    async def _dismiss_dialog(self) -> bool:
        """Dismiss any open dialogs"""
        try:
            # Playwright handles dialogs via event handlers
            # This sets up a handler for the next dialog
            self.page.on("dialog", lambda dialog: dialog.dismiss())
            return True
        except Exception:
            return False

    async def _dismiss_cookie_banner(self) -> bool:
        """Try to dismiss cookie consent banners"""
        for selector in self.COOKIE_BANNER_SELECTORS:
            try:
                locator = self.page.locator(selector).first
                if await locator.is_visible():
                    await locator.click()
                    await asyncio.sleep(0.5)
                    return True
            except Exception:
                continue

        return False

    async def _wait_for_loading(self) -> bool:
        """Wait for loading indicators to disappear"""
        try:
            # Wait for network to be idle
            await self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # Also check for loading indicators
        for selector in self.LOADING_INDICATORS:
            try:
                locator = self.page.locator(selector)
                await locator.wait_for(state="hidden", timeout=5000)
            except Exception:
                continue

        return True

    async def _switch_to_frame(self, frame_selector: Optional[str]) -> bool:
        """Switch to an iframe"""
        if not frame_selector:
            return False

        try:
            frame = self.page.frame_locator(frame_selector)
            return frame is not None
        except Exception:
            return False

    async def _clear_overlays(self) -> bool:
        """Remove overlay elements that might be blocking"""
        try:
            await self.page.evaluate("""
                // Remove common overlay elements
                const overlays = document.querySelectorAll(
                    '.overlay, .modal-backdrop, [class*="overlay"], [class*="backdrop"]'
                );
                overlays.forEach(el => {
                    if (el.style.position === 'fixed' || el.style.position === 'absolute') {
                        el.style.display = 'none';
                    }
                });

                // Remove fixed position elements that might be blocking
                document.querySelectorAll('[style*="position: fixed"]').forEach(el => {
                    if (el.style.zIndex > 100) {
                        el.style.display = 'none';
                    }
                });
            """)
            return True
        except Exception:
            return False

    def reset_attempts(self, selector: Optional[str] = None):
        """Reset recovery attempt counters"""
        if selector:
            keys_to_remove = [k for k in self._recovery_attempts if selector in k]
            for key in keys_to_remove:
                del self._recovery_attempts[key]
        else:
            self._recovery_attempts.clear()

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

    async def pre_action_check(self) -> List[FailureType]:
        """
        Check for potential issues before executing an action.

        Returns list of detected issues that should be handled.
        """
        issues = []

        # Check for modals
        for selector in self.MODAL_DISMISS_SELECTORS[:3]:
            try:
                if await self.page.locator(selector).first.is_visible():
                    issues.append(FailureType.MODAL_BLOCKING)
                    break
            except Exception:
                continue

        # Check for cookie banners
        for selector in self.COOKIE_BANNER_SELECTORS[:3]:
            try:
                if await self.page.locator(selector).first.is_visible():
                    issues.append(FailureType.COOKIE_BANNER)
                    break
            except Exception:
                continue

        # Check for loading indicators
        for selector in self.LOADING_INDICATORS[:3]:
            try:
                if await self.page.locator(selector).first.is_visible():
                    issues.append(FailureType.LOADING_SPINNER)
                    break
            except Exception:
                continue

        return issues

    async def handle_pre_action_issues(self) -> bool:
        """
        Handle any issues detected before action execution.

        Returns True if all issues were handled successfully.
        """
        issues = await self.pre_action_check()

        for issue in issues:
            result = await self.attempt_recovery(issue)
            if not result.success:
                return False

        return True
