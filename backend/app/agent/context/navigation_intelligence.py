"""
Navigation Intelligence

The module that enables the agent to navigate applications like a manual tester.
It scans the DOM, predicts where elements lead, executes navigation, and learns.

Key Capabilities:
1. DOM Scanning - Find all clickable/navigation elements
2. Prediction - Guess where elements lead based on text/attributes
3. Execution - Navigate using the best strategy
4. Verification - Confirm we arrived at the right page
5. Learning - Store successful navigation paths
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from playwright.async_api import Page, Locator
import asyncio

from .project_context import ProjectContext, NavigationPath, NavigationElement, PageInfo


class NavigationStrategy(Enum):
    """Strategy for reaching a target page"""
    DIRECT_URL = "direct_url"  # Navigate directly via URL
    CLICK_ELEMENT = "click_element"  # Click a navigation element
    KNOWN_PATH = "known_path"  # Follow a known navigation path
    EXPLORE = "explore"  # Explore DOM to find the way


@dataclass
class NavigableElement:
    """An element that could be used for navigation"""
    selector: str
    text: str
    tag: str
    href: Optional[str]
    predicted_destination: Optional[str]
    confidence: float
    attributes: Dict[str, str]

    def __str__(self):
        return f"<{self.tag}>{self.text}</{self.tag}> -> {self.predicted_destination} ({self.confidence:.0%})"


@dataclass
class NavigationResult:
    """Result of a navigation attempt"""
    success: bool
    strategy_used: NavigationStrategy
    started_url: str
    ended_url: str
    target_page: str
    steps_taken: List[Dict[str, Any]]
    error: Optional[str] = None


class NavigationIntelligence:
    """
    Intelligent navigation system that thinks like a manual tester.

    When asked to reach a page:
    1. Check if already there
    2. Look for known paths
    3. Try direct URL
    4. Scan DOM for navigation elements
    5. Execute best strategy
    6. Verify and learn
    """

    # Patterns for identifying navigation elements
    NAV_ELEMENT_SELECTORS = [
        "nav a",                    # Links in nav
        "header a",                 # Links in header
        "[role='navigation'] a",    # ARIA navigation
        "a[href]",                  # Any link with href
        "button",                   # Buttons
        "[role='button']",          # ARIA buttons
        "[role='link']",            # ARIA links
        ".nav-link",                # Bootstrap nav links
        ".menu-item a",             # Menu items
        ".sidebar a",               # Sidebar links
        "[class*='nav'] a",         # Any nav-related links
        "[class*='menu'] a",        # Any menu-related links
    ]

    # Text patterns that indicate navigation purpose
    DESTINATION_PATTERNS = {
        'registration': [
            r'\bsign\s*up\b', r'\bregister\b', r'\bcreate\s*account\b',
            r'\bjoin\b', r'\bget\s*started\b', r'\bnew\s*user\b',
            r'\bsign\s*up\s*free\b', r'\bregister\s*now\b'
        ],
        'login': [
            r'\blog\s*in\b', r'\bsign\s*in\b', r'\benter\b',
            r'\baccess\b', r'\balready\s*have\b', r'\bexisting\s*user\b'
        ],
        'home': [
            r'\bhome\b', r'\bmain\b', r'\bstart\b', r'\bback\s*to\s*home\b'
        ],
        'dashboard': [
            r'\bdashboard\b', r'\bmy\s*dashboard\b', r'\bgo\s*to\s*dashboard\b'
        ],
        'profile': [
            r'\bprofile\b', r'\bmy\s*profile\b', r'\bmy\s*account\b', r'\baccount\s*settings\b'
        ],
        'logout': [
            r'\blog\s*out\b', r'\bsign\s*out\b', r'\bexit\b', r'\blogout\b'
        ],
        'settings': [
            r'\bsettings\b', r'\bpreferences\b', r'\bconfigur\w*\b'
        ],
        'cart': [
            r'\bcart\b', r'\bbasket\b', r'\bbag\b', r'\bshopping\s*cart\b'
        ],
        'checkout': [
            r'\bcheckout\b', r'\bpay\b', r'\bpurchase\b', r'\border\b'
        ],
    }

    # URL patterns that indicate page type
    URL_DESTINATION_PATTERNS = {
        'registration': [r'/register', r'/signup', r'/sign-up', r'/create-account', r'/join'],
        'login': [r'/login', r'/signin', r'/sign-in', r'/auth'],
        'home': [r'^/$', r'/home', r'/index'],
        'dashboard': [r'/dashboard', r'/app'],
        'profile': [r'/profile', r'/account', r'/me', r'/user'],
        'settings': [r'/settings', r'/preferences'],
        'cart': [r'/cart', r'/basket'],
        'checkout': [r'/checkout', r'/payment', r'/order'],
    }

    def __init__(self, page: Page, project_context: ProjectContext):
        self.page = page
        self.context = project_context

    async def navigate_to(self, target_page: str) -> NavigationResult:
        """
        Navigate to a target page using the best available strategy.

        This is the main entry point. It thinks like a manual tester:
        1. Am I already there?
        2. Do I know the way?
        3. Can I go directly?
        4. Let me find the way
        """
        start_url = self.page.url
        target_normalized = self._normalize_page_name(target_page)

        print(f"\n[NAV-INTEL] === NAVIGATING TO: {target_page} ===", flush=True)
        print(f"[NAV-INTEL] Normalized target: {target_normalized}", flush=True)
        print(f"[NAV-INTEL] Current URL: {start_url}", flush=True)

        # Step 1: Check if already on target page
        if await self._is_on_page(target_normalized):
            print(f"[NAV-INTEL] Already on target page!", flush=True)
            return NavigationResult(
                success=True,
                strategy_used=NavigationStrategy.DIRECT_URL,
                started_url=start_url,
                ended_url=self.page.url,
                target_page=target_page,
                steps_taken=[]
            )

        # Step 2: Try known navigation path
        result = await self._try_known_path(target_normalized, start_url)
        if result and result.success:
            return result

        # Step 3: Try direct URL
        result = await self._try_direct_url(target_normalized, start_url)
        if result and result.success:
            return result

        # Step 4: Scan DOM and find navigation element
        result = await self._try_dom_navigation(target_normalized, start_url)
        if result and result.success:
            return result

        # Step 5: All strategies failed
        print(f"[NAV-INTEL] All navigation strategies failed for: {target_page}", flush=True)
        return NavigationResult(
            success=False,
            strategy_used=NavigationStrategy.EXPLORE,
            started_url=start_url,
            ended_url=self.page.url,
            target_page=target_page,
            steps_taken=[],
            error=f"Could not find way to navigate to '{target_page}'"
        )

    def _normalize_page_name(self, name: str) -> str:
        """Normalize page name for matching"""
        name = name.lower().strip()
        # Remove common suffixes/prefixes
        for suffix in [' page', ' screen', ' view', ' form']:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        for prefix in ['the ', 'a ', 'an ']:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
        return name.replace(' ', '_').replace('-', '_')

    async def _is_on_page(self, target_page: str) -> bool:
        """Check if currently on the target page"""
        current_url = self.page.url.lower()

        # Check URL patterns
        if target_page in self.URL_DESTINATION_PATTERNS:
            patterns = self.URL_DESTINATION_PATTERNS[target_page]
            for pattern in patterns:
                if re.search(pattern, current_url):
                    print(f"[NAV-INTEL] URL matches target: {pattern}", flush=True)
                    return True

        # Check via project context
        title = await self.page.title()
        try:
            body_text = await self.page.locator("body").inner_text()
        except:
            body_text = ""

        if self.context.is_on_page(target_page, current_url, title, body_text[:1000]):
            return True

        return False

    async def _try_known_path(self, target: str, start_url: str) -> Optional[NavigationResult]:
        """Try to use a known navigation path"""
        # Identify current page
        current_page = self.context._infer_page_from_url(self.page.url) or "unknown"

        path = self.context.get_navigation_path(current_page, target)
        if not path or not path.verified:
            return None

        print(f"[NAV-INTEL] Found known path: {current_page} -> {target}", flush=True)
        print(f"[NAV-INTEL] Steps: {path.steps}", flush=True)

        try:
            for step in path.steps:
                if step.get('action') == 'click':
                    selector = step.get('selector')
                    await self.page.click(selector)
                    await self.page.wait_for_load_state('networkidle', timeout=5000)

            # Verify we arrived
            if await self._is_on_page(target):
                self.context.record_navigation_success(current_page, target)
                return NavigationResult(
                    success=True,
                    strategy_used=NavigationStrategy.KNOWN_PATH,
                    started_url=start_url,
                    ended_url=self.page.url,
                    target_page=target,
                    steps_taken=path.steps
                )
            else:
                self.context.record_navigation_failure(current_page, target)

        except Exception as e:
            print(f"[NAV-INTEL] Known path failed: {e}", flush=True)
            self.context.record_navigation_failure(current_page, target)

        return None

    async def _try_direct_url(self, target: str, start_url: str) -> Optional[NavigationResult]:
        """Try navigating directly via URL"""
        url = self.context.get_direct_url_for_page(target)
        if not url:
            # Construct from base URL
            base = self.context.base_url
            if not base:
                # Extract from current URL
                from urllib.parse import urlparse
                parsed = urlparse(self.page.url)
                base = f"{parsed.scheme}://{parsed.netloc}"

            # Common URL mappings
            url_map = {
                'registration': '/register',
                'login': '/login',
                'home': '/',
                'dashboard': '/dashboard',
                'profile': '/profile',
                'settings': '/settings',
            }
            path = url_map.get(target, f'/{target}')
            url = f"{base.rstrip('/')}{path}"

        print(f"[NAV-INTEL] Trying direct URL: {url}", flush=True)

        try:
            await self.page.goto(url, wait_until='networkidle', timeout=10000)

            # Check if we arrived (and weren't redirected to login or error)
            current_url = self.page.url.lower()

            # Check for error indicators
            error_indicators = ['404', 'not found', 'error', 'forbidden', '403']
            page_content = await self.page.content()
            title = await self.page.title()

            is_error = any(ind in current_url or ind in title.lower() for ind in error_indicators)

            if not is_error and await self._is_on_page(target):
                print(f"[NAV-INTEL] Direct URL successful!", flush=True)

                # Learn this path
                current_page = self.context._infer_page_from_url(start_url) or "unknown"
                self.context.learn_navigation(start_url, self.page.url, {'action': 'goto', 'url': url}, True)

                return NavigationResult(
                    success=True,
                    strategy_used=NavigationStrategy.DIRECT_URL,
                    started_url=start_url,
                    ended_url=self.page.url,
                    target_page=target,
                    steps_taken=[{'action': 'goto', 'url': url}]
                )
            else:
                print(f"[NAV-INTEL] Direct URL didn't reach target (current: {current_url})", flush=True)

        except Exception as e:
            print(f"[NAV-INTEL] Direct URL failed: {e}", flush=True)

        return None

    async def _try_dom_navigation(self, target: str, start_url: str) -> Optional[NavigationResult]:
        """Scan DOM and find navigation element to click"""
        print(f"[NAV-INTEL] Scanning DOM for navigation to: {target}", flush=True)

        # Get all navigable elements
        elements = await self._scan_for_nav_elements()
        print(f"[NAV-INTEL] Found {len(elements)} potential navigation elements", flush=True)

        # Filter to elements that might lead to target
        candidates = self._rank_candidates_for_destination(elements, target)
        print(f"[NAV-INTEL] {len(candidates)} candidates for {target}", flush=True)

        for candidate in candidates[:5]:  # Try top 5 candidates
            print(f"[NAV-INTEL] Trying: {candidate}", flush=True)

            try:
                # Click the element
                await self.page.click(candidate.selector)
                await self.page.wait_for_load_state('networkidle', timeout=5000)

                # Check if we arrived
                if await self._is_on_page(target):
                    print(f"[NAV-INTEL] DOM navigation successful!", flush=True)

                    # Learn this navigation
                    current_page = self.context._infer_page_from_url(start_url) or "unknown"
                    step = {
                        'action': 'click',
                        'selector': candidate.selector,
                        'text': candidate.text
                    }
                    self.context.learn_navigation(start_url, self.page.url, step, True)

                    # Add to page's navigation elements
                    self.context.add_navigation_element_to_page(
                        page_key=current_page,
                        selector=candidate.selector,
                        text=candidate.text,
                        leads_to=target,
                        verified=True
                    )

                    return NavigationResult(
                        success=True,
                        strategy_used=NavigationStrategy.CLICK_ELEMENT,
                        started_url=start_url,
                        ended_url=self.page.url,
                        target_page=target,
                        steps_taken=[step]
                    )
                else:
                    print(f"[NAV-INTEL] Clicked but didn't reach target, going back...", flush=True)
                    await self.page.go_back()
                    await self.page.wait_for_load_state('networkidle', timeout=3000)

            except Exception as e:
                print(f"[NAV-INTEL] Failed to click {candidate.selector}: {e}", flush=True)
                # Try to recover by going back to start
                try:
                    await self.page.goto(start_url, wait_until='networkidle', timeout=5000)
                except:
                    pass

        return None

    async def _scan_for_nav_elements(self) -> List[NavigableElement]:
        """Scan the DOM for all potential navigation elements"""
        elements = []

        for selector_pattern in self.NAV_ELEMENT_SELECTORS:
            try:
                locators = self.page.locator(selector_pattern)
                count = await locators.count()

                for i in range(min(count, 50)):  # Limit to 50 per pattern
                    try:
                        locator = locators.nth(i)

                        # Check if visible
                        if not await locator.is_visible():
                            continue

                        # Get element info
                        text = (await locator.inner_text()).strip()
                        if not text or len(text) > 100:  # Skip empty or too long
                            continue

                        tag = await locator.evaluate("el => el.tagName.toLowerCase()")
                        href = await locator.get_attribute("href") or ""

                        # Generate a reliable selector
                        reliable_selector = await self._generate_selector(locator)

                        # Get other attributes
                        attrs = {}
                        for attr in ['class', 'id', 'role', 'aria-label', 'data-testid']:
                            val = await locator.get_attribute(attr)
                            if val:
                                attrs[attr] = val

                        # Predict destination
                        destination, confidence = self._predict_destination(text, href, attrs)

                        elements.append(NavigableElement(
                            selector=reliable_selector,
                            text=text,
                            tag=tag,
                            href=href,
                            predicted_destination=destination,
                            confidence=confidence,
                            attributes=attrs
                        ))

                    except Exception as e:
                        continue  # Skip problematic elements

            except Exception as e:
                continue  # Skip problematic selectors

        # Deduplicate by text
        seen = set()
        unique = []
        for elem in elements:
            key = elem.text.lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(elem)

        return unique

    async def _generate_selector(self, locator: Locator) -> str:
        """Generate a reliable CSS selector for an element"""
        try:
            # Try data-testid first
            testid = await locator.get_attribute("data-testid")
            if testid:
                return f"[data-testid='{testid}']"

            # Try id
            elem_id = await locator.get_attribute("id")
            if elem_id:
                return f"#{elem_id}"

            # Try unique class combination
            classes = await locator.get_attribute("class")
            if classes:
                class_list = classes.split()
                for cls in class_list:
                    if cls and not cls.startswith(('css-', 'sc-', 'MuiButton', 'chakra-')):
                        return f".{cls}"

            # Fall back to text-based selector
            text = (await locator.inner_text()).strip()
            if text and len(text) < 50:
                tag = await locator.evaluate("el => el.tagName.toLowerCase()")
                return f"{tag}:has-text('{text[:30]}')"

            # Last resort: use href for links
            href = await locator.get_attribute("href")
            if href and not href.startswith('#'):
                return f"a[href='{href}']"

        except:
            pass

        return ""

    def _predict_destination(self, text: str, href: str, attrs: Dict[str, str]) -> Tuple[Optional[str], float]:
        """Predict where an element leads based on text, href, and attributes"""
        text_lower = text.lower()
        href_lower = href.lower() if href else ""
        aria_label = attrs.get('aria-label', '').lower()

        combined = f"{text_lower} {href_lower} {aria_label}"

        best_destination = None
        best_confidence = 0.0

        # Check text patterns
        for destination, patterns in self.DESTINATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    confidence = 0.8 if pattern in text_lower else 0.6
                    if confidence > best_confidence:
                        best_destination = destination
                        best_confidence = confidence

        # Check URL patterns (higher confidence for explicit URLs)
        for destination, patterns in self.URL_DESTINATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, href_lower):
                    if best_destination == destination:
                        best_confidence = min(1.0, best_confidence + 0.2)
                    else:
                        if 0.9 > best_confidence:
                            best_destination = destination
                            best_confidence = 0.9

        return best_destination, best_confidence

    def _rank_candidates_for_destination(
        self,
        elements: List[NavigableElement],
        target: str
    ) -> List[NavigableElement]:
        """Rank elements by likelihood of leading to target destination"""

        def score(elem: NavigableElement) -> float:
            if elem.predicted_destination == target:
                return elem.confidence

            # Partial matches
            if elem.predicted_destination and target in elem.predicted_destination:
                return elem.confidence * 0.5

            # Text-based scoring
            text_lower = elem.text.lower()
            if target in self.DESTINATION_PATTERNS:
                for pattern in self.DESTINATION_PATTERNS[target]:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        return 0.7

            # URL-based scoring
            if elem.href and target in self.URL_DESTINATION_PATTERNS:
                for pattern in self.URL_DESTINATION_PATTERNS[target]:
                    if re.search(pattern, elem.href.lower()):
                        return 0.8

            return 0.0

        # Score and filter
        scored = [(elem, score(elem)) for elem in elements]
        scored = [(elem, s) for elem, s in scored if s > 0]

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return [elem for elem, _ in scored]

    async def resolve_precondition(self, precondition_text: str) -> NavigationResult:
        """
        Resolve a Gherkin precondition like "Given user is on registration page".

        This is the main entry point for precondition handling.
        """
        print(f"\n[NAV-INTEL] === RESOLVING PRECONDITION ===", flush=True)
        print(f"[NAV-INTEL] Precondition: {precondition_text}", flush=True)

        # Parse the precondition
        target_page = self._parse_precondition(precondition_text)
        print(f"[NAV-INTEL] Target page: {target_page}", flush=True)

        if not target_page:
            return NavigationResult(
                success=False,
                strategy_used=NavigationStrategy.EXPLORE,
                started_url=self.page.url,
                ended_url=self.page.url,
                target_page="unknown",
                steps_taken=[],
                error=f"Could not parse precondition: {precondition_text}"
            )

        return await self.navigate_to(target_page)

    def _parse_precondition(self, text: str) -> Optional[str]:
        """Parse a precondition to extract the target page"""
        text_lower = text.lower()

        # Common patterns
        patterns = [
            r"(?:user|i)\s+(?:am|is|should be|are)\s+on\s+(?:the\s+)?(.+?)(?:\s+page|\s+screen)?$",
            r"(?:on|at)\s+(?:the\s+)?(.+?)(?:\s+page|\s+screen)?$",
            r"(?:navigate|go)\s+to\s+(?:the\s+)?(.+?)(?:\s+page|\s+screen)?$",
            r"(?:visit|open)\s+(?:the\s+)?(.+?)(?:\s+page|\s+screen)?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                page_name = match.group(1).strip()
                return self._normalize_page_name(page_name)

        return None
