"""
SPA Handler

Specialized handling for Single Page Applications (SPAs).
Addresses unique challenges like dynamic loading, route changes,
virtual DOM re-renders, and shadow DOM.

Supports: React, Angular, Vue, Svelte, and other SPA frameworks.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class SPAFramework(Enum):
    """Detected SPA framework"""
    REACT = "react"
    ANGULAR = "angular"
    VUE = "vue"
    SVELTE = "svelte"
    NEXT = "next"  # Next.js (React-based)
    NUXT = "nuxt"  # Nuxt.js (Vue-based)
    UNKNOWN = "unknown"


class NavigationType(Enum):
    """Type of navigation in SPA"""
    FULL_PAGE = "full_page"  # Traditional page load
    SOFT_NAVIGATION = "soft_navigation"  # SPA route change
    HASH_CHANGE = "hash_change"  # Hash-based routing
    HISTORY_PUSH = "history_push"  # History API
    HISTORY_REPLACE = "history_replace"


@dataclass
class SPAState:
    """Current state of SPA"""
    framework: SPAFramework
    current_route: str
    is_hydrated: bool
    has_pending_requests: bool
    has_pending_animations: bool
    render_count: int
    last_render_time: Optional[datetime]


class SPAHandler:
    """
    Handles SPA-specific challenges.

    Features:
    - Smart waiting for dynamic content
    - Route change detection
    - Hydration detection
    - Re-render stability waiting
    - Shadow DOM piercing
    - Network idle detection
    """

    # Default timeouts
    DEFAULT_HYDRATION_TIMEOUT = 10000  # ms
    DEFAULT_RENDER_STABLE_TIMEOUT = 2000  # ms
    DEFAULT_NETWORK_IDLE_TIMEOUT = 5000  # ms

    # Framework detection patterns
    FRAMEWORK_SIGNATURES = {
        SPAFramework.REACT: {
            "global": ["__REACT_DEVTOOLS_GLOBAL_HOOK__", "__NEXT_DATA__"],
            "attributes": ["data-reactroot", "data-reactid"],
            "comments": ["react-root", "react-app"]
        },
        SPAFramework.ANGULAR: {
            "global": ["ng", "getAllAngularRootElements"],
            "attributes": ["ng-version", "_nghost", "_ngcontent"],
            "comments": []
        },
        SPAFramework.VUE: {
            "global": ["__VUE__", "__VUE_DEVTOOLS_GLOBAL_HOOK__", "__NUXT__"],
            "attributes": ["data-v-", "data-server-rendered"],
            "comments": []
        },
        SPAFramework.SVELTE: {
            "global": ["__svelte"],
            "attributes": [],
            "comments": []
        }
    }

    def __init__(self, page=None):
        """
        Initialize SPA handler.

        Args:
            page: Playwright page object
        """
        self.page = page
        self._detected_framework: SPAFramework = SPAFramework.UNKNOWN
        self._current_url: str = ""
        self._route_change_callbacks: List[Callable] = []
        self._is_monitoring: bool = False

    def set_page(self, page):
        """Set Playwright page object"""
        self.page = page

    # ==================== Framework Detection ====================

    async def detect_framework(self) -> SPAFramework:
        """
        Detect which SPA framework is being used.

        Returns:
            Detected SPA framework
        """
        if not self.page:
            return SPAFramework.UNKNOWN

        try:
            # Check each framework
            for framework, signatures in self.FRAMEWORK_SIGNATURES.items():
                is_detected = await self._check_framework_signatures(signatures)
                if is_detected:
                    self._detected_framework = framework
                    logger.info(f"Detected SPA framework: {framework.value}")
                    return framework

            # Check for Next.js specifically
            has_next = await self.page.evaluate("typeof __NEXT_DATA__ !== 'undefined'")
            if has_next:
                self._detected_framework = SPAFramework.NEXT
                return SPAFramework.NEXT

            # Check for Nuxt.js
            has_nuxt = await self.page.evaluate("typeof __NUXT__ !== 'undefined'")
            if has_nuxt:
                self._detected_framework = SPAFramework.NUXT
                return SPAFramework.NUXT

        except Exception as e:
            logger.warning(f"Framework detection failed: {e}")

        return SPAFramework.UNKNOWN

    async def _check_framework_signatures(self, signatures: Dict) -> bool:
        """Check if framework signatures are present"""
        try:
            # Check global variables
            for global_var in signatures.get("global", []):
                exists = await self.page.evaluate(f"typeof {global_var} !== 'undefined'")
                if exists:
                    return True

            # Check attributes in DOM
            for attr in signatures.get("attributes", []):
                has_attr = await self.page.evaluate(f"""
                    document.querySelector('[{attr}]') !== null ||
                    document.querySelector('[class*="{attr}"]') !== null
                """)
                if has_attr:
                    return True

        except Exception:
            pass

        return False

    # ==================== Hydration Handling ====================

    async def wait_for_hydration(self, timeout: int = None) -> bool:
        """
        Wait for SPA to complete hydration (client-side takeover).

        This is critical for SSR frameworks like Next.js, Nuxt.js.

        Args:
            timeout: Maximum time to wait in ms

        Returns:
            True if hydration completed
        """
        timeout = timeout or self.DEFAULT_HYDRATION_TIMEOUT
        start_time = datetime.utcnow()

        try:
            framework = self._detected_framework or await self.detect_framework()

            if framework == SPAFramework.REACT or framework == SPAFramework.NEXT:
                return await self._wait_for_react_hydration(timeout)
            elif framework == SPAFramework.VUE or framework == SPAFramework.NUXT:
                return await self._wait_for_vue_hydration(timeout)
            elif framework == SPAFramework.ANGULAR:
                return await self._wait_for_angular_hydration(timeout)
            else:
                # Generic wait for interactive state
                await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
                await asyncio.sleep(0.5)  # Small buffer for JS execution
                return True

        except Exception as e:
            logger.warning(f"Hydration wait failed: {e}")
            return False

    async def _wait_for_react_hydration(self, timeout: int) -> bool:
        """Wait for React hydration"""
        try:
            # Wait for React root to be hydrated
            await self.page.wait_for_function("""
                () => {
                    // Check for React 18+ hydration
                    const root = document.getElementById('root') ||
                                 document.getElementById('__next') ||
                                 document.querySelector('[data-reactroot]');
                    if (!root) return true;  // No React root, probably CSR

                    // Check if hydration marker is removed (React 18)
                    if (root._reactRootContainer || root.__reactContainer$) {
                        return true;
                    }

                    // Fallback: check for interactive elements
                    const buttons = document.querySelectorAll('button');
                    for (let btn of buttons) {
                        if (btn.onclick || btn._reactEvents) return true;
                    }

                    return document.readyState === 'complete';
                }
            """, timeout=timeout)
            return True
        except Exception:
            return False

    async def _wait_for_vue_hydration(self, timeout: int) -> bool:
        """Wait for Vue hydration"""
        try:
            await self.page.wait_for_function("""
                () => {
                    // Check for Vue 3
                    if (window.__VUE__) {
                        const apps = document.querySelectorAll('[data-v-app]');
                        return apps.length > 0 || document.querySelector('.__vue_app__');
                    }

                    // Check for Nuxt
                    if (window.__NUXT__ && window.__NUXT__.state) {
                        return true;
                    }

                    // Check for Vue 2
                    const vueElements = document.querySelectorAll('[data-v-]');
                    return vueElements.length > 0;
                }
            """, timeout=timeout)
            return True
        except Exception:
            return False

    async def _wait_for_angular_hydration(self, timeout: int) -> bool:
        """Wait for Angular hydration"""
        try:
            await self.page.wait_for_function("""
                () => {
                    // Check for Angular elements
                    const ngElements = document.querySelectorAll('[_ngcontent-]');
                    if (ngElements.length > 0) return true;

                    // Check for ng-version
                    const ngVersion = document.querySelector('[ng-version]');
                    return ngVersion !== null;
                }
            """, timeout=timeout)
            return True
        except Exception:
            return False

    # ==================== Render Stability ====================

    async def wait_for_render_stable(self, timeout: int = None) -> bool:
        """
        Wait for SPA to stop re-rendering.

        SPAs often re-render multiple times after data loads.
        This waits until the DOM is stable.

        Args:
            timeout: Maximum time to wait in ms

        Returns:
            True if render stabilized
        """
        timeout = timeout or self.DEFAULT_RENDER_STABLE_TIMEOUT
        check_interval = 100  # ms
        stable_checks_needed = 3
        stable_checks = 0

        try:
            # Inject mutation observer
            await self.page.evaluate("""
                window.__ghostqa_mutations = 0;
                window.__ghostqa_observer = new MutationObserver((mutations) => {
                    window.__ghostqa_mutations += mutations.length;
                });
                window.__ghostqa_observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    attributes: true
                });
            """)

            start_time = datetime.utcnow()
            last_mutation_count = 0

            while (datetime.utcnow() - start_time).total_seconds() * 1000 < timeout:
                await asyncio.sleep(check_interval / 1000)

                current_mutations = await self.page.evaluate("window.__ghostqa_mutations")

                if current_mutations == last_mutation_count:
                    stable_checks += 1
                    if stable_checks >= stable_checks_needed:
                        # DOM is stable
                        await self._cleanup_mutation_observer()
                        return True
                else:
                    stable_checks = 0
                    last_mutation_count = current_mutations

            await self._cleanup_mutation_observer()
            return False

        except Exception as e:
            logger.warning(f"Render stability check failed: {e}")
            await self._cleanup_mutation_observer()
            return False

    async def _cleanup_mutation_observer(self):
        """Clean up injected mutation observer"""
        try:
            await self.page.evaluate("""
                if (window.__ghostqa_observer) {
                    window.__ghostqa_observer.disconnect();
                    delete window.__ghostqa_observer;
                    delete window.__ghostqa_mutations;
                }
            """)
        except Exception:
            pass

    # ==================== Route Change Detection ====================

    async def start_route_monitoring(self):
        """
        Start monitoring for SPA route changes.

        Injects listeners for:
        - popstate events
        - pushState/replaceState calls
        - hashchange events
        """
        if self._is_monitoring:
            return

        self._current_url = self.page.url
        self._is_monitoring = True

        try:
            # Inject route change detection
            await self.page.evaluate("""
                window.__ghostqa_route_changes = [];

                // Monitor pushState
                const originalPushState = history.pushState;
                history.pushState = function(...args) {
                    window.__ghostqa_route_changes.push({
                        type: 'pushState',
                        url: args[2],
                        time: Date.now()
                    });
                    return originalPushState.apply(this, args);
                };

                // Monitor replaceState
                const originalReplaceState = history.replaceState;
                history.replaceState = function(...args) {
                    window.__ghostqa_route_changes.push({
                        type: 'replaceState',
                        url: args[2],
                        time: Date.now()
                    });
                    return originalReplaceState.apply(this, args);
                };

                // Monitor popstate
                window.addEventListener('popstate', (e) => {
                    window.__ghostqa_route_changes.push({
                        type: 'popstate',
                        url: location.href,
                        time: Date.now()
                    });
                });

                // Monitor hashchange
                window.addEventListener('hashchange', (e) => {
                    window.__ghostqa_route_changes.push({
                        type: 'hashchange',
                        url: location.href,
                        time: Date.now()
                    });
                });
            """)

            logger.debug("SPA route monitoring started")

        except Exception as e:
            logger.warning(f"Failed to start route monitoring: {e}")
            self._is_monitoring = False

    async def wait_for_route_change(self, timeout: int = 5000) -> Optional[Dict]:
        """
        Wait for a SPA route change to occur.

        Args:
            timeout: Maximum time to wait in ms

        Returns:
            Route change info or None if timeout
        """
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() * 1000 < timeout:
            try:
                changes = await self.page.evaluate("window.__ghostqa_route_changes || []")

                if changes:
                    # Clear the changes
                    await self.page.evaluate("window.__ghostqa_route_changes = []")

                    # Wait for new route to stabilize
                    await self.wait_for_render_stable(2000)

                    return changes[-1]  # Return most recent change

            except Exception:
                pass

            await asyncio.sleep(0.1)

        return None

    async def wait_for_navigation_complete(self, timeout: int = 10000) -> bool:
        """
        Wait for SPA navigation to complete.

        This handles both traditional page loads and SPA route changes.

        Args:
            timeout: Maximum time to wait in ms

        Returns:
            True if navigation completed
        """
        try:
            # Run both checks in parallel
            results = await asyncio.gather(
                self._wait_for_network_idle(timeout),
                self.wait_for_render_stable(min(timeout, 3000)),
                return_exceptions=True
            )

            # Check if network is idle and render is stable
            network_idle = results[0] if not isinstance(results[0], Exception) else False
            render_stable = results[1] if not isinstance(results[1], Exception) else False

            return network_idle or render_stable

        except Exception as e:
            logger.warning(f"Navigation wait failed: {e}")
            return False

    async def _wait_for_network_idle(self, timeout: int) -> bool:
        """Wait for network to be idle"""
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception:
            return False

    async def wait_for_spa_idle(self, timeout: int = 10000) -> bool:
        """
        Comprehensive wait for SPA to be idle.

        Waits for:
        - Pending fetch/XHR requests to complete
        - DOM mutations to stop
        - No pending animations

        This is the recommended wait for SPAs after actions.

        Args:
            timeout: Maximum time to wait in ms

        Returns:
            True if SPA is idle
        """
        try:
            # Inject network request tracking if not already done
            await self.page.evaluate("""
                if (!window.__ghostqa_pending_requests) {
                    window.__ghostqa_pending_requests = 0;

                    // Track fetch requests
                    const originalFetch = window.fetch;
                    window.fetch = function(...args) {
                        window.__ghostqa_pending_requests++;
                        return originalFetch.apply(this, args)
                            .finally(() => {
                                window.__ghostqa_pending_requests--;
                            });
                    };

                    // Track XMLHttpRequest
                    const originalOpen = XMLHttpRequest.prototype.open;
                    const originalSend = XMLHttpRequest.prototype.send;

                    XMLHttpRequest.prototype.open = function(...args) {
                        this.__ghostqa_tracked = true;
                        return originalOpen.apply(this, args);
                    };

                    XMLHttpRequest.prototype.send = function(...args) {
                        if (this.__ghostqa_tracked) {
                            window.__ghostqa_pending_requests++;
                            this.addEventListener('loadend', () => {
                                window.__ghostqa_pending_requests--;
                            });
                        }
                        return originalSend.apply(this, args);
                    };
                }
            """)

            start_time = datetime.utcnow()
            stable_count = 0
            required_stable_checks = 3

            while (datetime.utcnow() - start_time).total_seconds() * 1000 < timeout:
                # Check pending requests
                pending_requests = await self.page.evaluate(
                    "window.__ghostqa_pending_requests || 0"
                )

                if pending_requests == 0:
                    stable_count += 1
                    if stable_count >= required_stable_checks:
                        # Also wait for DOM stability
                        await self.wait_for_render_stable(min(2000, timeout // 2))
                        return True
                else:
                    stable_count = 0

                await asyncio.sleep(0.1)

            return False

        except Exception as e:
            logger.warning(f"SPA idle wait failed: {e}")
            return False

    # ==================== Shadow DOM Support ====================

    async def find_in_shadow_dom(
        self,
        selector: str,
        shadow_host_selector: Optional[str] = None
    ) -> Optional[Any]:
        """
        Find element that may be inside Shadow DOM.

        Args:
            selector: CSS selector for target element
            shadow_host_selector: Optional selector for shadow host

        Returns:
            Playwright locator or None
        """
        try:
            # Try regular selector first
            locator = self.page.locator(selector)
            count = await locator.count()
            if count > 0:
                return locator

            # Try piercing shadow DOM
            if shadow_host_selector:
                # Specific shadow host
                shadow_locator = self.page.locator(f"{shadow_host_selector} >> {selector}")
                if await shadow_locator.count() > 0:
                    return shadow_locator
            else:
                # Search all shadow roots
                element = await self.page.evaluate_handle(f"""
                    (selector) => {{
                        function searchShadowRoots(root, selector) {{
                            // Try in current root
                            let element = root.querySelector(selector);
                            if (element) return element;

                            // Search shadow roots
                            const allElements = root.querySelectorAll('*');
                            for (let el of allElements) {{
                                if (el.shadowRoot) {{
                                    element = searchShadowRoots(el.shadowRoot, selector);
                                    if (element) return element;
                                }}
                            }}
                            return null;
                        }}
                        return searchShadowRoots(document, selector);
                    }}
                """, selector)

                if element:
                    return element

        except Exception as e:
            logger.warning(f"Shadow DOM search failed: {e}")

        return None

    async def get_all_shadow_hosts(self) -> List[str]:
        """
        Get all elements that have shadow roots.

        Returns:
            List of selectors for shadow hosts
        """
        try:
            hosts = await self.page.evaluate("""
                () => {
                    const hosts = [];
                    const allElements = document.querySelectorAll('*');
                    for (let el of allElements) {
                        if (el.shadowRoot) {
                            // Generate a selector for this element
                            let selector = el.tagName.toLowerCase();
                            if (el.id) selector = '#' + el.id;
                            else if (el.className) selector += '.' + el.className.split(' ')[0];
                            hosts.push(selector);
                        }
                    }
                    return hosts;
                }
            """)
            return hosts
        except Exception:
            return []

    # ==================== Dynamic Content ====================

    async def wait_for_dynamic_content(
        self,
        selector: str,
        timeout: int = 10000
    ) -> bool:
        """
        Wait for dynamically loaded content to appear.

        This is smarter than simple wait - it handles:
        - Lazy loaded components
        - Content loaded after API calls
        - Virtualized lists

        Args:
            selector: Selector for expected content
            timeout: Maximum time to wait

        Returns:
            True if content appeared
        """
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() * 1000 < timeout:
            try:
                # Check if element exists
                locator = self.page.locator(selector)
                count = await locator.count()

                if count > 0:
                    # Element exists, wait for it to be visible
                    try:
                        await locator.first.wait_for(state="visible", timeout=1000)
                        return True
                    except Exception:
                        pass

                # Check in shadow DOM
                shadow_element = await self.find_in_shadow_dom(selector)
                if shadow_element:
                    return True

            except Exception:
                pass

            # Small delay before retry
            await asyncio.sleep(0.2)

        return False

    async def scroll_to_load(
        self,
        container_selector: Optional[str] = None,
        scroll_amount: int = 500,
        max_scrolls: int = 10,
        wait_between_scrolls: int = 500
    ) -> int:
        """
        Scroll to trigger lazy loading (infinite scroll, virtualized lists).

        Args:
            container_selector: Selector for scrollable container (None for window)
            scroll_amount: Pixels to scroll each time
            max_scrolls: Maximum number of scroll operations
            wait_between_scrolls: Wait time between scrolls in ms

        Returns:
            Number of new elements loaded
        """
        initial_count = await self._count_list_items(container_selector)
        current_count = initial_count

        for i in range(max_scrolls):
            # Scroll
            if container_selector:
                await self.page.evaluate(f"""
                    document.querySelector('{container_selector}').scrollBy(0, {scroll_amount})
                """)
            else:
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")

            # Wait for new content
            await asyncio.sleep(wait_between_scrolls / 1000)
            await self.wait_for_render_stable(1000)

            # Count items
            new_count = await self._count_list_items(container_selector)

            if new_count == current_count:
                # No new items, we've reached the end
                break

            current_count = new_count

        return current_count - initial_count

    async def _count_list_items(self, container_selector: Optional[str]) -> int:
        """Count items in a list container"""
        try:
            if container_selector:
                return await self.page.evaluate(f"""
                    document.querySelector('{container_selector}').children.length
                """)
            else:
                return await self.page.evaluate("document.body.children.length")
        except Exception:
            return 0

    # ==================== SPA-Specific Selectors ====================

    def get_spa_aware_selectors(self, intent: str) -> List[Dict[str, Any]]:
        """
        Get SPA-framework-aware selectors.

        Args:
            intent: What element to find

        Returns:
            List of selector strategies optimized for SPAs
        """
        selectors = []
        intent_lower = intent.lower()

        # React-specific selectors
        if self._detected_framework in (SPAFramework.REACT, SPAFramework.NEXT):
            selectors.extend([
                {"selector": f'[data-testid*="{intent_lower}"]', "type": "css", "confidence": 0.9},
                {"selector": f'[data-cy*="{intent_lower}"]', "type": "css", "confidence": 0.85},
            ])

        # Angular-specific selectors
        if self._detected_framework == SPAFramework.ANGULAR:
            selectors.extend([
                {"selector": f'[data-e2e*="{intent_lower}"]', "type": "css", "confidence": 0.9},
                {"selector": f'[automation-id*="{intent_lower}"]', "type": "css", "confidence": 0.85},
            ])

        # Vue-specific selectors
        if self._detected_framework in (SPAFramework.VUE, SPAFramework.NUXT):
            selectors.extend([
                {"selector": f'[data-test*="{intent_lower}"]', "type": "css", "confidence": 0.9},
                {"selector": f'[data-testid*="{intent_lower}"]', "type": "css", "confidence": 0.85},
            ])

        # Universal SPA selectors
        selectors.extend([
            {"selector": f'[data-testid="{intent_lower}"]', "type": "css", "confidence": 0.95},
            {"selector": f'[aria-label*="{intent_lower}"]', "type": "css", "confidence": 0.8},
            {"selector": f'[role][aria-label*="{intent_lower}"]', "type": "css", "confidence": 0.85},
        ])

        return selectors

    # ==================== State Management ====================

    async def get_spa_state(self) -> SPAState:
        """
        Get current SPA state information.

        Returns:
            Current SPA state
        """
        framework = self._detected_framework or await self.detect_framework()

        # Check for pending requests
        has_pending = await self._check_pending_requests()

        # Check for animations
        has_animations = await self._check_pending_animations()

        return SPAState(
            framework=framework,
            current_route=self.page.url,
            is_hydrated=True,  # Assume hydrated if we got this far
            has_pending_requests=has_pending,
            has_pending_animations=has_animations,
            render_count=0,
            last_render_time=None
        )

    async def _check_pending_requests(self) -> bool:
        """Check if there are pending XHR/fetch requests"""
        try:
            return await self.page.evaluate("""
                () => {
                    // Check for pending fetch requests (if tracked)
                    if (window.__ghostqa_pending_requests) {
                        return window.__ghostqa_pending_requests > 0;
                    }
                    return false;
                }
            """)
        except Exception:
            return False

    async def _check_pending_animations(self) -> bool:
        """Check if there are running animations"""
        try:
            return await self.page.evaluate("""
                () => {
                    const animations = document.getAnimations();
                    return animations.some(a => a.playState === 'running');
                }
            """)
        except Exception:
            return False

    async def cleanup(self):
        """Clean up injected scripts and observers"""
        await self._cleanup_mutation_observer()
        self._is_monitoring = False
