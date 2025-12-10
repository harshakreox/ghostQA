from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import List, Callable, Optional
import asyncio
import sys
from datetime import datetime
import os
import json
import re
import difflib
from models import TestCase, TestAction, TestResult, TestReport, ActionType
from dom_manager import DOMManager

# NOTE: Event loop policy is now set by the caller (main.py) in the thread
# that runs the test execution. This avoids conflicts when importing this
# module from different contexts.


class TestEngine:
    """Autonomous test execution engine with self-healing capabilities."""
    
    def __init__(self, log_callback: Optional[Callable] = None):
        self._playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.dom_manager: Optional[DOMManager] = None
        self.log_callback = log_callback or print
        self.current_report_id: Optional[str] = None
        
    async def initialize(self, headless: bool = False):
        """Initialize Playwright browser and DOM manager."""
        self.log("Initializing Playwright browser...")

        try:
            self._playwright = await async_playwright().start()
            self.log("   Playwright started")
        except Exception as e:
            self.log(f"  [ERR] Failed to start Playwright: {e}")
            raise

        try:
            self.browser = await self._playwright.chromium.launch(
                headless=headless, 
                slow_mo=200,
                args=["--start-maximized"] if not headless else []
            )
            self.log("   Browser launched")
        except Exception as e:
            self.log(f"  [ERR] Failed to launch browser: {e}")
            raise

        try:
            self.context = await self.browser.new_context(
                no_viewport=True if not self.headless else False,
                viewport={'width': 1920, 'height': 1080} if self.headless else None
            )
            self.log("   Browser context created")
        except Exception as e:
            self.log(f"  [ERR] Failed to create context: {e}")
            raise

        try:
            self.page = await self.context.new_page()
            self.log("   New page opened")
        except Exception as e:
            self.log(f"  [ERR] Failed to open page: {e}")
            raise

        # Initialize DOM Manager for self-healing (optional - won't fail tests if unavailable)
        try:
            self.log("Initializing DOM Manager...")
            self.dom_manager = DOMManager(
                page=self.page,
                dom_path="data/dom_library.json",
                debounce_interval=1.0,
                auto_init=True
            )

            if self.dom_manager._initialized:
                self.log("   DOM Manager initialized (self-healing enabled)")
            else:
                self.log("  [WARN] DOM Manager partial init (some self-healing may be limited)")
        except Exception as e:
            self.log(f"  [WARN] DOM Manager unavailable: {e}")
            self.log("  [INFO] Tests will run without self-healing capabilities")
            self.dom_manager = None

        self.log("[OK] Browser initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, '_playwright') and self._playwright:
                await self._playwright.stop()
            self.log("Browser closed")
        except Exception as e:
            self.log(f"[WARN] Error during cleanup: {e}")
    
    def log(self, message: str):
        """Log message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        if self.log_callback:
            self.log_callback(log_message)
    
    # ============================================================
    # SELF-HEALING HELPERS (from main_script.py)
    # ============================================================
    
    def normalize_text(self, text):
        """Normalize text for comparison."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.lower()).strip()
    
    def build_selector(self, elem):
        """Build selector from element dict."""
        tag = elem.get("tag", "input")
        
        if elem.get("id"):
            return f'#{elem["id"]}'
        elif elem.get("name"):
            return f'{tag}[name="{elem["name"]}"]'
        elif elem.get("placeholder"):
            return f'{tag}[placeholder="{elem["placeholder"]}"]'
        elif elem.get("text"):
            return f'{tag}:has-text("{elem["text"]}")'
        
        return tag
    
    async def find_element_with_fuzzy_match(self, dom_data, target_text, tag_hint=None):
        """Find element using fuzzy matching with 60% threshold."""
        if not dom_data or not target_text:
            return None
        
        target_norm = self.normalize_text(target_text)
        
        # Try exact matches first
        for form in dom_data.get("forms", []):
            for elem in form.get("inputs", []):
                if tag_hint and elem.get("tag") != tag_hint:
                    continue
                    
                for attr in ["id", "name", "placeholder", "label_for", "aria_label"]:
                    val = elem.get(attr)
                    if val and self.normalize_text(val) == target_norm:
                        return self.build_selector(elem)
        
        for elem in dom_data.get("buttons_and_links", []):
            if tag_hint and elem.get("tag") != tag_hint:
                continue
                
            for attr in ["text", "id", "name", "aria_label"]:
                val = elem.get(attr)
                if val and self.normalize_text(val) == target_norm:
                    return self.build_selector(elem)
        
        # Fuzzy matching with 60% similarity threshold
        candidates = []
        
        for form in dom_data.get("forms", []):
            for elem in form.get("inputs", []):
                for attr in ["id", "name", "placeholder", "label_for", "aria_label"]:
                    val = elem.get(attr)
                    if val:
                        ratio = difflib.SequenceMatcher(
                            None,
                            self.normalize_text(val),
                            target_norm
                        ).ratio()
                        if ratio > 0.6:
                            candidates.append((ratio, elem))
        
        for elem in dom_data.get("buttons_and_links", []):
            for attr in ["text", "id", "name", "aria_label"]:
                val = elem.get(attr)
                if val:
                    ratio = difflib.SequenceMatcher(
                        None,
                        self.normalize_text(val),
                        target_norm
                    ).ratio()
                    if ratio > 0.6:
                        candidates.append((ratio, elem))
        
        if candidates:
            best = max(candidates, key=lambda x: x[0])
            self.log(f" Self-healing: fuzzy match found (score: {best[0]:.2f})")
            return self.build_selector(best[1])
        
        return None
    
    async def click_by_coordinates(self, target_text):
        """Last resort: click by coordinates using DOM data."""
        if not self.dom_manager:
            self.log("[WARN] DOM Manager not available for coordinate click")
            return False

        dom_data = self.dom_manager.get_dom()
        if not dom_data:
            return False
        
        candidates = []
        
        # Collect visible elements with coordinates
        for elem in dom_data.get("visible_elements", []):
            if elem.get("x") is not None and elem.get("y") is not None:
                candidates.append(elem)
        
        # Also check buttons and links
        for elem in dom_data.get("buttons_and_links", []):
            if elem.get("x") is not None and elem.get("y") is not None:
                candidates.append(elem)
        
        if not candidates:
            self.log("[WARN] No elements with coordinates found")
            return False
        
        # Find best match by fuzzy text matching
        target_norm = self.normalize_text(target_text)
        best_score = 0
        best_elem = None
        
        for elem in candidates:
            text_parts = [
                elem.get("text", ""),
                elem.get("aria_label", ""),
                elem.get("placeholder", ""),
                elem.get("id", ""),
                elem.get("name", "")
            ]
            combined = " ".join(filter(None, text_parts))
            
            if combined:
                score = difflib.SequenceMatcher(
                    None,
                    self.normalize_text(combined),
                    target_norm
                ).ratio()
                
                if score > best_score:
                    best_score = score
                    best_elem = elem
        
        # Click if we found something reasonable (>25% match)
        if best_elem and best_score >= 0.25:
            x = best_elem["x"] + (best_elem.get("w", 0) / 2)
            y = best_elem["y"] + (best_elem.get("h", 0) / 2)
            self.log(f" Coordinate click at ({x:.0f}, {y:.0f}) - score: {best_score:.2f}")
            await self.page.mouse.click(x, y)
            return True
        
        # Fallback: click topmost element
        try:
            topmost = min(candidates, key=lambda e: e.get("y", 999999))
            x = topmost["x"] + (topmost.get("w", 0) / 2)
            y = topmost["y"] + (topmost.get("h", 0) / 2)
            self.log(f" Coordinate click at topmost element ({x:.0f}, {y:.0f})")
            await self.page.mouse.click(x, y)
            return True
        except Exception as e:
            self.log(f"[WARN] Coordinate click failed: {e}")
            return False
    
    async def save_failure_artifacts(self, test_case_id, step_idx, report_dir):
        """Save screenshot, HTML, and DOM snapshot on failure."""
        artifacts = {}
        
        os.makedirs(report_dir, exist_ok=True)
        
        try:
            # Screenshot
            screenshot_path = f"{report_dir}/step_{step_idx}_failure.png"
            await self.page.screenshot(path=screenshot_path)
            artifacts["screenshot"] = screenshot_path
            self.log(f" Screenshot saved: {screenshot_path}")
        except Exception as e:
            self.log(f"[WARN] Could not save screenshot: {e}")
        
        try:
            # HTML snapshot
            html_path = f"{report_dir}/step_{step_idx}_failure.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(await self.page.content())
            artifacts["html"] = html_path
            self.log(f" HTML saved: {html_path}")
        except Exception as e:
            self.log(f"[WARN] Could not save HTML: {e}")
        
        try:
            # DOM snapshot (if available)
            if self.dom_manager:
                dom_path = f"{report_dir}/step_{step_idx}_dom.json"
                with open(dom_path, "w", encoding="utf-8") as f:
                    json.dump(self.dom_manager.get_dom() or {}, f, indent=2)
                artifacts["dom"] = dom_path
                self.log(f" DOM saved: {dom_path}")
        except Exception as e:
            self.log(f"[WARN] Could not save DOM: {e}")
        
        return artifacts
    
    # ============================================================
    # TEST EXECUTION WITH SELF-HEALING
    # ============================================================
    
    async def execute_test_case(self, test_case: TestCase, base_url: Optional[str], 
                                 report_dir: str) -> TestResult:
        """Execute a single test case with self-healing."""
        self.log(f"\n{'='*60}")
        self.log(f"Starting test: {test_case.name}")
        self.log(f"Description: {test_case.description}")
        self.log(f"{'='*60}\n")
        
        start_time = datetime.now()
        logs = []
        error_message = None
        screenshot_path = None
        status = "passed"
        
        try:
            for idx, action in enumerate(test_case.actions, 1):
                self.log(f"Step {idx}/{len(test_case.actions)}: {action.description}")
                
                # Wait before action if specified
                if action.wait_before:
                    await asyncio.sleep(action.wait_before / 1000)
                
                # Execute action with self-healing
                await self._execute_action_with_healing(action, base_url)
                logs.append(f" {action.description}")
                
                # Wait after action
                if action.wait_after:
                    await asyncio.sleep(action.wait_after / 1000)
            
            self.log(f" Test PASSED: {test_case.name}")
            
        except Exception as e:
            status = "failed"
            error_message = str(e)
            logs.append(f" Error: {error_message}")
            self.log(f" Test FAILED: {test_case.name}")
            self.log(f"Error: {error_message}")
            
            # Save failure artifacts
            artifacts = await self.save_failure_artifacts(test_case.id, idx, report_dir)
            screenshot_path = artifacts.get("screenshot")
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return TestResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            status=status,
            duration=duration,
            error_message=error_message,
            screenshot_path=screenshot_path,
            logs=logs
        )
    
    async def _execute_action_with_healing(self, action: TestAction, base_url: Optional[str]):
        """Execute action with multiple fallback strategies."""
        
        max_attempts = 3
        attempt = 0
        last_error = None
        
        while attempt < max_attempts:
            attempt += 1
            
            try:
                # Try to execute the action
                await self._execute_action_core(action, base_url)
                
                # Success!
                if attempt > 1:
                    self.log(f"[OK] Action succeeded on attempt {attempt}")
                return
                
            except Exception as e:
                last_error = e
                self.log(f"[WARN] Attempt {attempt}/{max_attempts} failed: {str(e)[:100]}")
                
                if attempt >= max_attempts:
                    raise last_error
                
                # Apply recovery strategies
                if attempt == 1:
                    # Strategy 1: Refresh DOM (if available)
                    if self.dom_manager:
                        self.log(" Strategy 1: Refreshing DOM...")
                        self.dom_manager.maybe_refresh_dom(force=True, reason="action failed")
                    else:
                        self.log(" Strategy 1: Waiting and retrying...")
                    await asyncio.sleep(0.5)
                    
                elif attempt == 2:
                    # Strategy 2: Self-healing with fuzzy match (only if DOM manager available)
                    if self.dom_manager and action.selector and action.action in [ActionType.CLICK, ActionType.TYPE, ActionType.SELECT]:
                        self.log(" Strategy 2: Attempting self-healing...")

                        alt_selector = await self.find_element_with_fuzzy_match(
                            self.dom_manager.get_dom(),
                            action.selector,
                            action.selector_type.value if action.selector_type else None
                        )

                        if alt_selector:
                            self.log(f" Found alternative selector: {alt_selector}")
                            # Update action with new selector
                            original_selector = action.selector
                            action.selector = alt_selector

                            try:
                                await self._execute_action_core(action, base_url)
                                self.log(f"[OK] Self-healing successful!")
                                return
                            except Exception:
                                # Restore original selector
                                action.selector = original_selector

                        # Strategy 3: Coordinate-based click (only for clicks)
                        if action.action == ActionType.CLICK:
                            self.log(" Strategy 3: Attempting coordinate click...")
                            success = await self.click_by_coordinates(action.selector)
                            if success:
                                self.log(f"[OK] Coordinate click successful!")
                                return
        
        # All attempts exhausted
        raise last_error
    
    def _build_selector(self, action: TestAction) -> str:
        """Build proper CSS selector based on selector_type and selector value."""
        selector = action.selector or ""
        selector_type = action.selector_type.value if action.selector_type else None

        if not selector:
            return selector

        # If selector already looks like a CSS selector, use it as-is
        if selector.startswith('#') or selector.startswith('.') or selector.startswith('['):
            return selector
        if ':' in selector or ' ' in selector:  # Complex selectors
            return selector

        # Build selector based on type
        if selector_type == 'id':
            return f'#{selector}'
        elif selector_type == 'css':
            return selector  # Already a CSS selector
        elif selector_type == 'class':
            return f'.{selector}'
        elif selector_type == 'name':
            return f'[name="{selector}"]'
        elif selector_type == 'xpath':
            return selector  # Playwright handles xpath differently
        elif selector_type == 'text':
            return f'text={selector}'
        else:
            # Default: try as-is, might be a valid selector
            return selector

    async def _execute_action_core(self, action: TestAction, base_url: Optional[str]):
        """Core action execution logic."""

        if action.action == ActionType.NAVIGATE:
            url = action.value
            if base_url and not url.startswith('http'):
                url = base_url + url
            self.log(f"  → Navigating to: {url}")
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=30000)

            # Force DOM refresh after navigation (if available)
            if self.dom_manager:
                self.log("   Refreshing DOM after navigation...")
                self.dom_manager.maybe_refresh_dom(force=True, reason="navigation")
            
        elif action.action == ActionType.CLICK:
            selector = self._build_selector(action)
            self.log(f"  → Clicking: {selector}")
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.click(selector)

        elif action.action == ActionType.TYPE:
            selector = self._build_selector(action)
            self.log(f"  → Typing into: {selector}")
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.fill(selector, action.value or "")

        elif action.action == ActionType.SELECT:
            selector = self._build_selector(action)
            self.log(f"  → Selecting option: {action.value}")
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.select_option(selector, action.value or "")

        elif action.action == ActionType.CHECK:
            selector = self._build_selector(action)
            self.log(f"  → Checking checkbox: {selector}")
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.check(selector)

        elif action.action == ActionType.UNCHECK:
            selector = self._build_selector(action)
            self.log(f"  → Unchecking checkbox: {selector}")
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.uncheck(selector)

        elif action.action == ActionType.HOVER:
            selector = self._build_selector(action)
            self.log(f"  → Hovering over: {selector}")
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            await self.page.hover(selector)
            
        elif action.action == ActionType.WAIT:
            wait_time = int(action.value or "1000")
            self.log(f"  → Waiting: {wait_time}ms")
            await asyncio.sleep(wait_time / 1000)
            
        elif action.action == ActionType.ASSERT_TEXT:
            selector = self._build_selector(action) if action.selector else "body"
            self.log(f"  → Asserting text '{action.value}' in: {selector}")
            element = await self.page.wait_for_selector(selector, timeout=10000)
            text = await element.inner_text()
            assert action.value in text, f"Expected text '{action.value}' not found in '{text}'"

        elif action.action == ActionType.ASSERT_URL:
            self.log(f"  → Asserting URL contains: {action.value}")
            assert action.value in self.page.url, f"Expected '{action.value}' in URL but got '{self.page.url}'"

        elif action.action == ActionType.ASSERT_VISIBLE:
            selector = self._build_selector(action)
            self.log(f"  → Asserting visibility: {selector}")
            await self.page.wait_for_selector(selector, state='visible', timeout=10000)
            
        elif action.action == ActionType.SCREENSHOT:
            filename = action.value or f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.log(f"  → Taking screenshot: {filename}")
            await self.page.screenshot(path=filename)
    
    async def run_tests(self, test_cases: List[TestCase], base_url: Optional[str], 
                       report_dir: str, headless: bool = False) -> TestReport:
        """Run multiple test cases and generate report."""
        
        os.makedirs(report_dir, exist_ok=True)
        self.current_report_id = os.path.basename(report_dir)
        
        await self.initialize(headless=headless)
        
        results = []
        start_time = datetime.now()
        
        for test_case in test_cases:
            result = await self.execute_test_case(test_case, base_url, report_dir)
            results.append(result)
        
        await self.cleanup()
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        
        self.log(f"\n{'='*60}")
        self.log(f"Test Summary:")
        self.log(f"  Total: {len(results)}")
        self.log(f"  Passed: {passed}")
        self.log(f"  Failed: {failed}")
        self.log(f"  Skipped: {skipped}")
        self.log(f"  Duration: {total_duration:.2f}s")
        self.log(f"{'='*60}\n")
        
        return TestReport(
            id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            project_id="",
            project_name="",
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=total_duration,
            results=results
        )