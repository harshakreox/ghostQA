"""
Human-Like Tester Module for GhostQA
=====================================
Makes the agent behave like a real human tester with TOKEN-EFFICIENT design.

Design Principles:
1. DOM-first analysis (FREE - no tokens)
2. Heuristics before AI (FREE - no tokens)
3. AI only for truly ambiguous cases (EXPENSIVE - use sparingly)
4. Cache all AI decisions (SAVES tokens on repeat)
5. Batch AI calls when possible (REDUCES overhead)

Components:
- PageStateTracker: Tracks app state before/after actions (no AI)
- SmartWaiter: Adaptive waiting based on page signals (no AI)
- OverlayDetector: Finds blocking elements (DOM-first)
- ErrorDetector: Finds validation errors (heuristics-first)
- PreActionChecker: Orchestrates all checks before each action
"""

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class PageType(Enum):
    """Types of pages - detected WITHOUT AI"""
    LOGIN = "login"
    REGISTER = "register"
    FORM = "form"
    DASHBOARD = "dashboard"
    LIST = "list"
    DETAIL = "detail"
    CHECKOUT = "checkout"
    SEARCH = "search"
    ERROR = "error"
    MODAL = "modal"
    UNKNOWN = "unknown"


class BlockerType(Enum):
    """Types of blocking overlays"""
    MODAL = "modal"
    COOKIE_BANNER = "cookie_banner"
    LOADING_SPINNER = "loading_spinner"
    TOAST = "toast"
    POPUP = "popup"
    OVERLAY = "overlay"
    NONE = "none"


class ActionReadiness(Enum):
    """Whether page is ready for action"""
    READY = "ready"
    BLOCKED = "blocked"
    LOADING = "loading"
    HAS_ERROR = "has_error"
    ELEMENT_HIDDEN = "element_hidden"


@dataclass
class PageState:
    """Snapshot of page state - captured WITHOUT AI"""
    url: str
    title: str
    page_type: PageType
    form_field_count: int
    filled_field_count: int
    visible_error_count: int
    has_modal: bool
    has_loading: bool
    button_texts: List[str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_hash(self) -> str:
        """Create hash for comparison"""
        data = f"{self.url}|{self.title}|{self.form_field_count}|{self.filled_field_count}|{self.visible_error_count}|{self.has_modal}"
        return hashlib.md5(data.encode()).hexdigest()[:16]

    def __eq__(self, other):
        if not isinstance(other, PageState):
            return False
        return self.to_hash() == other.to_hash()


@dataclass
class BlockerInfo:
    """Information about a blocking element"""
    blocker_type: BlockerType
    selector: str
    dismiss_selector: Optional[str] = None
    dismiss_action: str = "click"  # click, press_escape, wait
    confidence: float = 1.0


@dataclass
class ErrorInfo:
    """Information about a detected error"""
    error_type: str  # validation, server, network, custom
    message: str
    selector: Optional[str] = None
    field_name: Optional[str] = None
    severity: str = "error"  # error, warning, info


@dataclass
class PreActionResult:
    """Result of pre-action checks"""
    readiness: ActionReadiness
    blockers: List[BlockerInfo]
    errors: List[ErrorInfo]
    page_state: PageState
    suggestions: List[str]
    should_proceed: bool
    wait_recommended_ms: int = 0


# =============================================================================
# PAGE STATE TRACKER (No AI - Pure DOM Analysis)
# =============================================================================

class PageStateTracker:
    """
    Tracks application state before/after actions.
    Uses ONLY DOM analysis - no AI tokens consumed.
    """

    def __init__(self):
        self.state_history: List[PageState] = []
        self.max_history = 50

    async def capture_state(self, page) -> PageState:
        """Capture current page state from DOM - NO AI USED"""
        try:
            url = page.url
            title = await page.title()

            # Detect page type from URL and content
            page_type = await self._detect_page_type(page, url, title)

            # Count form fields
            form_fields = await page.query_selector_all('input:not([type="hidden"]), textarea, select')
            form_field_count = len(form_fields)

            # Count filled fields
            filled_count = 0
            for field in form_fields:
                value = await field.input_value() if await field.is_visible() else ""
                if value and value.strip():
                    filled_count += 1

            # Count visible errors
            error_count = await self._count_visible_errors(page)

            # Check for modal
            has_modal = await self._has_modal(page)

            # Check for loading
            has_loading = await self._has_loading(page)

            # Get button texts
            button_texts = await self._get_button_texts(page)

            state = PageState(
                url=url,
                title=title,
                page_type=page_type,
                form_field_count=form_field_count,
                filled_field_count=filled_count,
                visible_error_count=error_count,
                has_modal=has_modal,
                has_loading=has_loading,
                button_texts=button_texts
            )

            # Store in history
            self.state_history.append(state)
            if len(self.state_history) > self.max_history:
                self.state_history.pop(0)

            return state

        except Exception as e:
            logger.error(f"[STATE] Failed to capture state: {e}")
            return PageState(
                url=page.url if page else "",
                title="",
                page_type=PageType.UNKNOWN,
                form_field_count=0,
                filled_field_count=0,
                visible_error_count=0,
                has_modal=False,
                has_loading=False,
                button_texts=[]
            )

    async def _detect_page_type(self, page, url: str, title: str) -> PageType:
        """Detect page type from URL and DOM - NO AI"""
        url_lower = url.lower()
        title_lower = title.lower()
        combined = f"{url_lower} {title_lower}"

        # URL-based detection (fast)
        if any(x in combined for x in ['login', 'signin', 'sign-in', 'log-in']):
            return PageType.LOGIN
        if any(x in combined for x in ['register', 'signup', 'sign-up', 'create-account', 'join']):
            return PageType.REGISTER
        if any(x in combined for x in ['checkout', 'payment', 'cart', 'basket']):
            return PageType.CHECKOUT
        if any(x in combined for x in ['dashboard', 'home', 'overview', 'welcome']):
            return PageType.DASHBOARD
        if any(x in combined for x in ['search', 'find', 'results']):
            return PageType.SEARCH
        if any(x in combined for x in ['error', '404', '500', 'not found', 'forbidden']):
            return PageType.ERROR

        # DOM-based detection
        try:
            # Check for password field (login/register indicator)
            password_field = await page.query_selector('input[type="password"]')
            if password_field:
                # Check if it's register (has confirm password or more fields)
                confirm_pw = await page.query_selector('input[name*="confirm"], input[name*="repeat"], input[placeholder*="confirm"]')
                email_field = await page.query_selector('input[type="email"], input[name*="email"]')
                name_fields = await page.query_selector_all('input[name*="name"], input[placeholder*="name"]')

                if confirm_pw or len(name_fields) >= 2:
                    return PageType.REGISTER
                return PageType.LOGIN

            # Check for forms
            forms = await page.query_selector_all('form')
            inputs = await page.query_selector_all('input:not([type="hidden"]):not([type="submit"])')
            if forms or len(inputs) > 2:
                return PageType.FORM

            # Check for lists
            lists = await page.query_selector_all('ul, ol, table, [class*="list"], [class*="grid"]')
            if len(lists) > 0:
                list_items = await page.query_selector_all('li, tr, [class*="item"], [class*="card"]')
                if len(list_items) > 3:
                    return PageType.LIST

        except Exception as e:
            logger.debug(f"[STATE] DOM detection error: {e}")

        return PageType.UNKNOWN

    async def _count_visible_errors(self, page) -> int:
        """Count visible error messages - NO AI"""
        error_selectors = [
            '[class*="error"]:not([class*="error-free"])',
            '[class*="invalid"]',
            '[class*="danger"]',
            '[role="alert"]',
            '[aria-invalid="true"]',
            '.field-error',
            '.form-error',
            '.validation-error',
            '.error-message',
            '.MuiFormHelperText-root.Mui-error',
            '.ant-form-item-explain-error'
        ]

        count = 0
        for selector in error_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    if await el.is_visible():
                        count += 1
            except:
                pass

        return count

    async def _has_modal(self, page) -> bool:
        """Check if a modal is present - NO AI"""
        modal_selectors = [
            '[role="dialog"]',
            '[aria-modal="true"]',
            '.modal.show',
            '.modal.open',
            '.MuiModal-root',
            '.ant-modal-wrap',
            '[class*="modal"][class*="open"]',
            '[class*="modal"][class*="show"]',
            '[class*="dialog"][class*="open"]'
        ]

        for selector in modal_selectors:
            try:
                modal = await page.query_selector(selector)
                if modal and await modal.is_visible():
                    return True
            except:
                pass

        return False

    async def _has_loading(self, page) -> bool:
        """Check if page is loading - NO AI"""
        loading_selectors = [
            '[class*="loading"]',
            '[class*="spinner"]',
            '[class*="loader"]',
            '[aria-busy="true"]',
            '.MuiCircularProgress-root',
            '.ant-spin',
            '[class*="skeleton"]'
        ]

        for selector in loading_selectors:
            try:
                loader = await page.query_selector(selector)
                if loader and await loader.is_visible():
                    return True
            except:
                pass

        return False

    async def _get_button_texts(self, page) -> List[str]:
        """Get visible button texts - NO AI"""
        texts = []
        try:
            buttons = await page.query_selector_all('button, input[type="submit"], a[class*="btn"]')
            for btn in buttons[:10]:  # Limit to first 10
                if await btn.is_visible():
                    text = await btn.text_content() or await btn.get_attribute('value') or ""
                    if text.strip():
                        texts.append(text.strip()[:50])
        except:
            pass
        return texts

    def state_changed(self, before: PageState, after: PageState) -> bool:
        """Check if state changed between snapshots"""
        return before.to_hash() != after.to_hash()

    def get_state_diff(self, before: PageState, after: PageState) -> Dict[str, Any]:
        """Get differences between two states"""
        diff = {}

        if before.url != after.url:
            diff['url_changed'] = {'from': before.url, 'to': after.url}
        if before.page_type != after.page_type:
            diff['page_type_changed'] = {'from': before.page_type.value, 'to': after.page_type.value}
        if before.form_field_count != after.form_field_count:
            diff['form_fields_changed'] = {'from': before.form_field_count, 'to': after.form_field_count}
        if before.filled_field_count != after.filled_field_count:
            diff['filled_fields_changed'] = {'from': before.filled_field_count, 'to': after.filled_field_count}
        if before.visible_error_count != after.visible_error_count:
            diff['errors_changed'] = {'from': before.visible_error_count, 'to': after.visible_error_count}
        if before.has_modal != after.has_modal:
            diff['modal_changed'] = {'from': before.has_modal, 'to': after.has_modal}

        return diff


# =============================================================================
# SMART WAITER (No AI - DOM/Network Signals)
# =============================================================================

class SmartWaiter:
    """
    Adaptive waiting based on page signals.
    Uses ONLY DOM observation - no AI tokens consumed.
    """

    def __init__(self):
        self.default_timeout_ms = 10000
        self.min_stability_ms = 300
        self.learned_timings: Dict[str, int] = {}  # url_pattern -> typical_wait_ms

    async def wait_for_ready(self, page, timeout_ms: int = None) -> Tuple[bool, int]:
        """
        Wait until page is ready for interaction.
        Returns (is_ready, actual_wait_ms)

        NO AI TOKENS USED - pure DOM/network observation.
        """
        timeout = timeout_ms or self.default_timeout_ms
        start_time = asyncio.get_event_loop().time()

        try:
            # 1. Wait for network idle (most reliable)
            await page.wait_for_load_state('networkidle', timeout=timeout)

            # 2. Wait for DOM stability
            await self._wait_for_dom_stability(page, self.min_stability_ms)

            # 3. Wait for any loading indicators to disappear
            await self._wait_for_loading_gone(page, timeout // 2)

            # 4. Wait for animations to complete
            await self._wait_for_animations(page, 500)

            elapsed = int((asyncio.get_event_loop().time() - start_time) * 1000)

            # Learn timing for this URL pattern
            self._record_timing(page.url, elapsed)

            return True, elapsed

        except Exception as e:
            elapsed = int((asyncio.get_event_loop().time() - start_time) * 1000)
            logger.debug(f"[WAIT] Timeout after {elapsed}ms: {e}")
            return False, elapsed

    async def _wait_for_dom_stability(self, page, stability_ms: int = 300):
        """Wait until DOM stops changing"""
        js_code = f"""
        () => new Promise(resolve => {{
            let mutations = 0;
            let lastMutationTime = Date.now();

            const observer = new MutationObserver(() => {{
                mutations++;
                lastMutationTime = Date.now();
            }});

            observer.observe(document.body, {{
                childList: true,
                subtree: true,
                attributes: true
            }});

            const check = () => {{
                if (Date.now() - lastMutationTime >= {stability_ms}) {{
                    observer.disconnect();
                    resolve(mutations);
                }} else {{
                    setTimeout(check, 100);
                }}
            }};

            setTimeout(check, {stability_ms});
        }})
        """
        try:
            await page.evaluate(js_code)
        except:
            await asyncio.sleep(stability_ms / 1000)

    async def _wait_for_loading_gone(self, page, timeout_ms: int = 5000):
        """Wait for loading indicators to disappear"""
        loading_selectors = [
            '[class*="loading"]:not([class*="loaded"])',
            '[class*="spinner"]',
            '[class*="loader"]',
            '[aria-busy="true"]',
            '.MuiCircularProgress-root',
            '.ant-spin-spinning'
        ]

        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) * 1000 < timeout_ms:
            has_loading = False
            for selector in loading_selectors:
                try:
                    loader = await page.query_selector(selector)
                    if loader and await loader.is_visible():
                        has_loading = True
                        break
                except:
                    pass

            if not has_loading:
                return

            await asyncio.sleep(0.1)

    async def _wait_for_animations(self, page, max_wait_ms: int = 500):
        """Wait for CSS animations/transitions to complete"""
        js_code = """
        () => {
            const animating = document.querySelectorAll('*');
            for (const el of animating) {
                const style = getComputedStyle(el);
                if (style.animationName !== 'none' ||
                    style.transition !== 'all 0s ease 0s') {
                    return true;
                }
            }
            return false;
        }
        """

        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) * 1000 < max_wait_ms:
            try:
                has_animations = await page.evaluate(js_code)
                if not has_animations:
                    return
            except:
                return
            await asyncio.sleep(0.05)

    def _record_timing(self, url: str, elapsed_ms: int):
        """Learn timing patterns for URL patterns"""
        # Extract URL pattern (remove dynamic parts)
        pattern = re.sub(r'/\d+', '/:id', url)
        pattern = re.sub(r'\?.*', '', pattern)

        if pattern in self.learned_timings:
            # Moving average
            self.learned_timings[pattern] = int(
                0.7 * self.learned_timings[pattern] + 0.3 * elapsed_ms
            )
        else:
            self.learned_timings[pattern] = elapsed_ms

    def get_expected_wait(self, url: str) -> int:
        """Get expected wait time based on learned patterns"""
        pattern = re.sub(r'/\d+', '/:id', url)
        pattern = re.sub(r'\?.*', '', pattern)
        return self.learned_timings.get(pattern, 1000)


# =============================================================================
# OVERLAY DETECTOR (DOM-First, AI Fallback)
# =============================================================================

class OverlayDetector:
    """
    Detects blocking overlays (modals, popups, cookie banners).
    Uses DOM patterns first - AI only for unknown overlays.
    """

    # Known overlay patterns - no AI needed for these
    KNOWN_PATTERNS = {
        BlockerType.COOKIE_BANNER: {
            'selectors': [
                '[class*="cookie"]',
                '[class*="consent"]',
                '[class*="gdpr"]',
                '[id*="cookie"]',
                '[id*="consent"]',
                '#onetrust-banner-sdk',
                '.cc-banner',
                '#CybotCookiebotDialog'
            ],
            'dismiss_selectors': [
                '[class*="accept"]',
                '[class*="agree"]',
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                'button:has-text("OK")',
                '[id*="accept"]'
            ]
        },
        BlockerType.MODAL: {
            'selectors': [
                '[role="dialog"]',
                '[aria-modal="true"]',
                '.modal.show',
                '.modal.open',
                '.MuiDialog-root',
                '.ant-modal-wrap:not(.ant-modal-wrap-hidden)'
            ],
            'dismiss_selectors': [
                '[data-dismiss="modal"]',
                '[aria-label="Close"]',
                '[aria-label="close"]',
                '.modal-close',
                '.close-button',
                'button:has-text("Close")',
                'button:has-text("Cancel")',
                '.MuiDialog-root button[aria-label="close"]',
                '.ant-modal-close'
            ]
        },
        BlockerType.LOADING_SPINNER: {
            'selectors': [
                '[class*="loading"][class*="overlay"]',
                '[class*="spinner"][class*="overlay"]',
                '.loading-mask',
                '.page-loader'
            ],
            'dismiss_selectors': []  # Wait, don't dismiss
        },
        BlockerType.POPUP: {
            'selectors': [
                '[class*="popup"]:not([class*="hidden"])',
                '[class*="promo"]',
                '[class*="newsletter"]',
                '[class*="subscribe"]'
            ],
            'dismiss_selectors': [
                '[class*="close"]',
                '[class*="dismiss"]',
                'button:has-text("No thanks")',
                'button:has-text("Close")'
            ]
        }
    }

    def __init__(self):
        self.ai_cache: Dict[str, BlockerInfo] = {}

    async def detect_blockers(self, page) -> List[BlockerInfo]:
        """
        Detect all blocking overlays on page.
        Uses DOM patterns first - NO AI for known patterns.
        """
        blockers = []

        for blocker_type, patterns in self.KNOWN_PATTERNS.items():
            for selector in patterns['selectors']:
                try:
                    elements = await page.query_selector_all(selector)
                    for el in elements:
                        if await el.is_visible():
                            # Find dismiss button
                            dismiss_selector = await self._find_dismiss_button(
                                page, el, patterns['dismiss_selectors']
                            )

                            blockers.append(BlockerInfo(
                                blocker_type=blocker_type,
                                selector=selector,
                                dismiss_selector=dismiss_selector,
                                dismiss_action="wait" if blocker_type == BlockerType.LOADING_SPINNER else "click",
                                confidence=1.0
                            ))
                            break  # One per type is enough
                except Exception as e:
                    logger.debug(f"[OVERLAY] Selector failed {selector}: {e}")

        return blockers

    async def _find_dismiss_button(
        self,
        page,
        overlay_element,
        dismiss_selectors: List[str]
    ) -> Optional[str]:
        """Find the dismiss button for an overlay"""
        for selector in dismiss_selectors:
            try:
                # Try global selector first
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    return selector
            except:
                pass

        # Try common patterns within the overlay
        try:
            close_btn = await overlay_element.query_selector('button, [role="button"]')
            if close_btn and await close_btn.is_visible():
                return 'button'
        except:
            pass

        return None

    async def dismiss_blocker(self, page, blocker: BlockerInfo) -> bool:
        """Dismiss a blocking overlay"""
        try:
            if blocker.dismiss_action == "wait":
                # For loading spinners, just wait
                await asyncio.sleep(2)
                return True

            if blocker.dismiss_action == "press_escape":
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.3)
                return True

            if blocker.dismiss_selector:
                btn = await page.query_selector(blocker.dismiss_selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.3)
                    return True

            # Fallback: try Escape
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.3)
            return True

        except Exception as e:
            logger.warning(f"[OVERLAY] Failed to dismiss {blocker.blocker_type}: {e}")
            return False


# =============================================================================
# ERROR DETECTOR (Heuristics-First)
# =============================================================================

class ErrorDetector:
    """
    Detects validation errors and error states.
    Uses heuristics first - NO AI for common patterns.
    """

    # Error patterns - detected without AI
    ERROR_SELECTORS = [
        # Semantic/accessibility
        '[role="alert"]',
        '[aria-invalid="true"]',
        '[aria-errormessage]',

        # Class-based
        '[class*="error"]:not([class*="error-free"]):not([class*="no-error"])',
        '[class*="invalid"]',
        '[class*="danger"]',
        '[class*="warning"]',
        '.field-error',
        '.form-error',
        '.validation-error',
        '.error-message',
        '.help-block.error',

        # Framework-specific
        '.MuiFormHelperText-root.Mui-error',
        '.ant-form-item-explain-error',
        '.invalid-feedback',
        '.text-danger',
        '.has-error .help-block'
    ]

    # Error text patterns
    ERROR_TEXT_PATTERNS = [
        r'is required',
        r'cannot be empty',
        r'must be',
        r'invalid',
        r'incorrect',
        r'does not match',
        r'too short',
        r'too long',
        r'already exists',
        r'already taken',
        r'not found',
        r'failed',
        r'error',
        r'please enter',
        r'please provide'
    ]

    async def detect_errors(self, page) -> List[ErrorInfo]:
        """
        Detect all visible errors on page.
        Uses heuristics - NO AI tokens consumed.
        """
        errors = []
        seen_messages = set()

        # 1. Check error selectors
        for selector in self.ERROR_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    if await el.is_visible():
                        text = await el.text_content() or ""
                        text = text.strip()[:200]

                        if text and text not in seen_messages:
                            seen_messages.add(text)
                            errors.append(ErrorInfo(
                                error_type="validation",
                                message=text,
                                selector=selector,
                                severity="error"
                            ))
            except:
                pass

        # 2. Check for error text patterns in visible text
        try:
            page_text = await page.evaluate('''
                () => {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let text = '';
                    let node;
                    while (node = walker.nextNode()) {
                        const parent = node.parentElement;
                        if (parent && getComputedStyle(parent).display !== 'none') {
                            text += node.textContent + ' ';
                        }
                    }
                    return text.substring(0, 5000);
                }
            ''')

            for pattern in self.ERROR_TEXT_PATTERNS:
                matches = re.findall(f'.{{0,30}}{pattern}.{{0,30}}', page_text, re.IGNORECASE)
                for match in matches[:3]:  # Limit matches
                    match = match.strip()
                    if match and match not in seen_messages:
                        seen_messages.add(match)
                        errors.append(ErrorInfo(
                            error_type="text_pattern",
                            message=match,
                            severity="warning"
                        ))
        except:
            pass

        # 3. Check for red-bordered inputs (visual error indicator)
        try:
            red_inputs = await page.evaluate('''
                () => {
                    const inputs = document.querySelectorAll('input, select, textarea');
                    const redInputs = [];
                    for (const inp of inputs) {
                        const style = getComputedStyle(inp);
                        const borderColor = style.borderColor;
                        // Check for red-ish border
                        if (borderColor.includes('rgb(') &&
                            parseInt(borderColor.match(/\\d+/)[0]) > 200 &&
                            parseInt(borderColor.match(/\\d+/g)[1]) < 100) {
                            redInputs.push(inp.name || inp.id || 'unknown');
                        }
                    }
                    return redInputs;
                }
            ''')

            for field_name in red_inputs:
                if field_name not in seen_messages:
                    errors.append(ErrorInfo(
                        error_type="visual",
                        message=f"Field '{field_name}' has error indicator",
                        field_name=field_name,
                        severity="error"
                    ))
        except:
            pass

        return errors

    async def has_form_errors(self, page) -> bool:
        """Quick check if form has any errors"""
        errors = await self.detect_errors(page)
        return len([e for e in errors if e.severity == "error"]) > 0


# =============================================================================
# PRE-ACTION CHECKER (Orchestrator)
# =============================================================================

class PreActionChecker:
    """
    Orchestrates all pre-action checks.
    Determines if action can proceed safely.

    Token Usage:
    - Phase 1 (DOM): FREE
    - Phase 2 (Heuristics): FREE
    - Phase 3 (AI): Only if phases 1-2 fail (RARELY USED)
    """

    def __init__(self):
        self.state_tracker = PageStateTracker()
        self.smart_waiter = SmartWaiter()
        self.overlay_detector = OverlayDetector()
        self.error_detector = ErrorDetector()

        # AI usage tracking
        self.ai_calls_made = 0
        self.checks_performed = 0

    async def check_before_action(
        self,
        page,
        target_selector: Optional[str] = None,
        action_type: str = "click"
    ) -> PreActionResult:
        """
        Perform all pre-action checks.
        Returns whether action should proceed.

        This is the MAIN entry point - call before every action.
        """
        self.checks_performed += 1
        suggestions = []

        # 1. Wait for page readiness (NO AI)
        is_ready, wait_time = await self.smart_waiter.wait_for_ready(page)

        # 2. Capture page state (NO AI)
        page_state = await self.state_tracker.capture_state(page)

        # 3. Check for blocking overlays (NO AI for known patterns)
        blockers = await self.overlay_detector.detect_blockers(page)

        # 4. Auto-dismiss non-essential blockers
        for blocker in blockers:
            if blocker.blocker_type in [BlockerType.COOKIE_BANNER, BlockerType.POPUP]:
                logger.info(f"[PRE-ACTION] Auto-dismissing {blocker.blocker_type.value}")
                dismissed = await self.overlay_detector.dismiss_blocker(page, blocker)
                if dismissed:
                    blockers.remove(blocker)

        # 5. Check for errors (NO AI)
        errors = await self.error_detector.detect_errors(page)

        # 6. Check if target element is accessible
        element_ready = True
        if target_selector:
            element_ready = await self._check_element_ready(page, target_selector)
            if not element_ready:
                suggestions.append(f"Target element '{target_selector}' not ready")

        # 7. Determine overall readiness
        readiness = ActionReadiness.READY
        should_proceed = True

        if not is_ready:
            readiness = ActionReadiness.LOADING
            should_proceed = False
            suggestions.append("Page still loading")
        elif blockers:
            remaining_blockers = [b for b in blockers if b.blocker_type not in [BlockerType.TOAST]]
            if remaining_blockers:
                readiness = ActionReadiness.BLOCKED
                should_proceed = False
                suggestions.append(f"Blocked by {remaining_blockers[0].blocker_type.value}")
        elif errors and action_type == "submit":
            readiness = ActionReadiness.HAS_ERROR
            should_proceed = False
            suggestions.append(f"Form has {len(errors)} error(s)")
        elif not element_ready:
            readiness = ActionReadiness.ELEMENT_HIDDEN
            should_proceed = False

        return PreActionResult(
            readiness=readiness,
            blockers=blockers,
            errors=errors,
            page_state=page_state,
            suggestions=suggestions,
            should_proceed=should_proceed,
            wait_recommended_ms=wait_time
        )

    async def _check_element_ready(self, page, selector: str) -> bool:
        """Check if target element is visible and enabled"""
        try:
            # Skip check if selector is not a valid CSS selector (it's an intent name/text)
            if not selector:
                return True

            # Check if this looks like a CSS/XPath selector vs plain text
            # CSS selectors typically start with specific characters or contain combinators
            is_css_selector = (
                selector.startswith('#') or           # ID selector
                selector.startswith('.') or           # Class selector
                selector.startswith('[') or           # Attribute selector
                selector.startswith('//') or          # XPath
                selector.startswith('input') or
                selector.startswith('button') or
                selector.startswith('a[') or          # Link with attribute
                selector.startswith('div[') or
                selector.startswith('span[') or
                '::' in selector or                   # Pseudo-elements
                ' > ' in selector or                  # Direct child combinator
                ' + ' in selector or                  # Adjacent sibling
                ' ~ ' in selector or                  # General sibling
                selector.startswith('*') or           # Universal selector
                ':nth-' in selector or                # nth-child etc
                ':has(' in selector or                # has() pseudo-class
                ':not(' in selector or                # not() pseudo-class
                '=' in selector                       # Attribute value selector
            )

            # Plain text with spaces (like "List Export", "Add to Cart") is NOT a CSS selector
            # Only consider it CSS if it has actual CSS syntax markers
            if not is_css_selector:
                # It's plain text or an intent name - skip visibility check
                # The actual element finding happens later via smart_find_element
                return True

            element = await page.query_selector(selector)
            if not element:
                return False

            is_visible = await element.is_visible()
            is_enabled = await element.is_enabled()

            return is_visible and is_enabled
        except:
            # On any error, don't block - let the main flow handle it
            return True

    async def verify_action_effect(
        self,
        page,
        state_before: PageState,
        expected_changes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verify that an action had the expected effect.
        Call AFTER action execution.

        NO AI - pure state comparison.
        """
        state_after = await self.state_tracker.capture_state(page)

        changed = self.state_tracker.state_changed(state_before, state_after)
        diff = self.state_tracker.get_state_diff(state_before, state_after)

        result = {
            "action_had_effect": changed,
            "state_before": state_before,
            "state_after": state_after,
            "changes": diff,
            "new_errors": []
        }

        # Check for new errors
        if state_after.visible_error_count > state_before.visible_error_count:
            errors = await self.error_detector.detect_errors(page)
            result["new_errors"] = [e.message for e in errors]

        # Validate expected changes
        if expected_changes:
            result["expected_changes_met"] = []
            for expected in expected_changes:
                if expected == "url_change" and "url_changed" in diff:
                    result["expected_changes_met"].append(expected)
                elif expected == "form_filled" and "filled_fields_changed" in diff:
                    result["expected_changes_met"].append(expected)
                elif expected == "modal_closed" and diff.get("modal_changed", {}).get("to") == False:
                    result["expected_changes_met"].append(expected)

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_checks": self.checks_performed,
            "ai_calls": self.ai_calls_made,
            "ai_usage_percent": (self.ai_calls_made / max(1, self.checks_performed)) * 100
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global instance for easy access
_checker: Optional[PreActionChecker] = None


def get_pre_action_checker() -> PreActionChecker:
    """Get or create the global pre-action checker"""
    global _checker
    if _checker is None:
        _checker = PreActionChecker()
    return _checker


async def check_before_action(page, target_selector: str = None, action_type: str = "click") -> PreActionResult:
    """Convenience function to check before action"""
    checker = get_pre_action_checker()
    return await checker.check_before_action(page, target_selector, action_type)


async def verify_action(page, state_before: PageState, expected: List[str] = None) -> Dict[str, Any]:
    """Convenience function to verify action effect"""
    checker = get_pre_action_checker()
    return await checker.verify_action_effect(page, state_before, expected)
