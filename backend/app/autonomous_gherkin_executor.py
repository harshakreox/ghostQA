"""
Autonomous AI-Powered Gherkin Executor
Uses AI to interpret and execute Gherkin steps WITHOUT predefined step definitions
Combines DOM extraction, fuzzy matching, and AI intelligence for true autonomous testing
"""

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import List, Optional, Dict, Any
import time
import json
import re
import difflib
from datetime import datetime
from models_gherkin import GherkinFeature, GherkinScenario, GherkinStep
import os
import requests


class AutonomousScenarioResult:
    """Result of executing a single scenario autonomously"""
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.status = "passed"  # "passed", "failed", "skipped"
        self.duration = 0.0
        self.error_message = None
        self.failed_step = None
        self.screenshot_path = None
        self.logs = []
        self.ai_decisions = []  # Track AI decisions for debugging
    
    def add_log(self, message: str):
        """Add log message"""
        self.logs.append(message)
        print(f"  {message}")
    
    def add_ai_decision(self, step: str, decision: Dict[str, Any]):
        """Track AI decision for a step"""
        self.ai_decisions.append({
            "step": step,
            "decision": decision,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self):
        return {
            "scenario_name": self.scenario_name,
            "status": self.status,
            "duration": self.duration,
            "error_message": self.error_message,
            "failed_step": self.failed_step,
            "screenshot_path": self.screenshot_path,
            "logs": self.logs,
            "ai_decisions": self.ai_decisions
        }


class AutonomousFeatureResult:
    """Result of executing a feature autonomously"""
    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self.scenario_results: List[AutonomousScenarioResult] = []
        self.total_scenarios = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.total_duration = 0.0
    
    def add_result(self, result: AutonomousScenarioResult):
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


class AutonomousGherkinExecutor:
    """
    AI-Powered Gherkin Executor
    Uses AI to interpret Gherkin steps and execute them autonomously
    """
    
    def __init__(self, base_url: str = "", headless: bool = True, test_credentials: dict = None):
        self.base_url = base_url
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.dom_cache: Dict[str, Any] = {}
        
        # Test credentials for login/auth scenarios
        self.test_credentials = test_credentials or {
            'username': os.getenv('TEST_USERNAME', 'testuser@example.com'),
            'password': os.getenv('TEST_PASSWORD', 'testpassword123'),
            'admin_username': os.getenv('TEST_ADMIN_USERNAME', 'admin@example.com'),
            'admin_password': os.getenv('TEST_ADMIN_PASSWORD', 'adminpass123'),
        }
        
        # AI Configuration
        self._detect_ai_service()
    
    def _detect_ai_service(self):
        """Detect available AI service"""
        # Check for Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            self.ai_service = "anthropic"
            self.ai_url = "https://api.anthropic.com/v1/messages"
            self.ai_model = "claude-sonnet-4-20250514"
            self.ai_key = os.getenv("ANTHROPIC_API_KEY")
            print("[OK] Using Anthropic Claude for AI execution")
            return
        
        # Check for Ollama
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                self.ai_service = "ollama"
                self.ai_url = "http://localhost:11434/api/generate"
                models = response.json().get('models', [])
                self.ai_model = models[0]['name'] if models else "llama3.1"
                print(f"[OK] Using Ollama ({self.ai_model}) for AI execution")
                return
        except:
            pass
        
        raise ValueError("[ERR] No AI service configured! Set ANTHROPIC_API_KEY or run Ollama")
    
    def setup(self):
        """Setup Playwright browser"""
        print(" Starting Playwright browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        # Use no_viewport when not headless to respect actual window size
        context_options = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'ignore_https_errors': True,
            'java_script_enabled': True
        }
        if self.headless:
            context_options['viewport'] = {'width': 1920, 'height': 1080}
            context_options['device_scale_factor'] = 1.0
        else:
            # no_viewport is incompatible with device_scale_factor
            context_options['no_viewport'] = True
        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
        
        # Set normal zoom level
        self.page.evaluate("() => { document.body.style.zoom = '100%'; }")
        
        print("[OK] Browser ready!")
        print(f"   Viewport: 1366x768 (Standard)")
        print(f"   Zoom: 100%")
    
    def teardown(self):
        """Cleanup Playwright"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print(" Browser closed")
    
    def execute_feature(self, feature: GherkinFeature, 
                       scenario_filter: Optional[List[str]] = None) -> AutonomousFeatureResult:
        """Execute feature with AI"""
        feature_result = AutonomousFeatureResult(feature.name)
        
        print(f"\n{'='*80}")
        print(f" AI-POWERED EXECUTION: {feature.name}")
        print(f"{'='*80}\n")
        
        # Filter scenarios if needed
        scenarios_to_run = feature.scenarios
        if scenario_filter:
            scenarios_to_run = [s for s in scenarios_to_run if s.name in scenario_filter]
        
        # Execute each scenario
        for scenario in scenarios_to_run:
            result = self.execute_scenario(scenario, feature.background)
            feature_result.add_result(result)
        
        return feature_result
    
    def execute_scenario(self, scenario: GherkinScenario, 
                        background: Optional[List[GherkinStep]] = None) -> AutonomousScenarioResult:
        """Execute single scenario with AI"""
        result = AutonomousScenarioResult(scenario.name)
        start_time = time.time()
        
        try:
            print(f"\n{'='*80}")
            print(f" AI Scenario: {scenario.name}")
            print(f"   Tags: {', '.join(scenario.tags)}")
            print(f"{'='*80}")
            
            # Execute background steps first
            if background:
                print(f"\n Background:")
                for step in background:
                    self._execute_step_with_ai(step, result)
            
            # Execute scenario steps
            print(f"\n Scenario Steps:")
            for step in scenario.steps:
                self._execute_step_with_ai(step, result)
            
            result.status = "passed"
            print(f"\n[OK] AI Scenario PASSED")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            result.add_log(f"[ERR] FAILED: {str(e)}")
            print(f"\n[ERR] AI Scenario FAILED: {str(e)}")
            
            # Take screenshot on failure
            try:
                screenshot_dir = "screenshots"
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = f"{screenshot_dir}/ai_failure_{scenario.name.replace(' ', '_')}_{int(time.time())}.png"
                self.page.screenshot(path=screenshot_path, full_page=True)
                result.screenshot_path = screenshot_path
                result.add_log(f" Screenshot: {screenshot_path}")
            except Exception as e:
                result.add_log(f"[WARN] Could not take screenshot: {str(e)}")
        
        finally:
            result.duration = time.time() - start_time
            print(f"⏱  Duration: {result.duration:.2f}s")
        
        return result
    
    def _execute_step_with_ai(self, step: GherkinStep, result: AutonomousScenarioResult):
        """Execute a single step using AI intelligence"""
        step_text = f"{step.keyword} {step.text}"
        print(f"\n AI Step: {step.keyword.value} {step.text}")
        result.add_log(f"Executing: {step_text}")
        
        try:
            # Extract current DOM
            dom_data = self._extract_dom()
            
            # Get current URL and page state
            current_url = self.page.url
            page_title = self.page.title()
            
            # Ask AI what to do
            ai_decision = self._ask_ai_for_action(
                step_text=step_text,
                dom_data=dom_data,
                current_url=current_url,
                page_title=page_title
            )
            
            result.add_ai_decision(step_text, ai_decision)
            
            # Execute the AI's decision
            self._execute_ai_decision(ai_decision, result)
            
            result.add_log(f"[OK] Success: {step_text}")
            
        except Exception as e:
            result.failed_step = step_text
            result.add_log(f"[ERR] Failed: {step_text} - {str(e)}")
            raise Exception(f"Step failed: {step_text}\n  Error: {str(e)}")
    
    def _extract_dom(self) -> Dict[str, Any]:
        """Extract DOM information from current page"""
        try:
            # Extract interactive elements
            dom_script = """
            () => {
                const extractElement = (el) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id || null,
                        name: el.name || null,
                        type: el.type || null,
                        placeholder: el.placeholder || null,
                        value: el.value || null,
                        text: el.innerText?.trim().substring(0, 100) || null,
                        href: el.href || null,
                        visible: rect.width > 0 && rect.height > 0,
                        x: rect.x,
                        y: rect.y
                    };
                };
                
                return {
                    inputs: Array.from(document.querySelectorAll('input')).map(extractElement),
                    buttons: Array.from(document.querySelectorAll('button')).map(extractElement),
                    links: Array.from(document.querySelectorAll('a')).map(extractElement),
                    selects: Array.from(document.querySelectorAll('select')).map(extractElement),
                    textareas: Array.from(document.querySelectorAll('textarea')).map(extractElement),
                    url: window.location.href,
                    title: document.title
                };
            }
            """
            
            dom_data = self.page.evaluate(dom_script)
            
            # Filter to visible elements only
            for key in ['inputs', 'buttons', 'links', 'selects', 'textareas']:
                if key in dom_data:
                    dom_data[key] = [el for el in dom_data[key] if el.get('visible', False)]
            
            return dom_data
            
        except Exception as e:
            print(f"[WARN] DOM extraction error: {str(e)}")
            return {}
    
    def _ask_ai_for_action(self, step_text: str, dom_data: Dict[str, Any], 
                          current_url: str, page_title: str) -> Dict[str, Any]:
        """Ask AI what action to take for this step"""
        
        # Build prompt for AI
        prompt = self._build_ai_prompt(step_text, dom_data, current_url, page_title)
        
        # Call AI service
        if self.ai_service == "anthropic":
            return self._call_anthropic_for_action(prompt)
        elif self.ai_service == "ollama":
            return self._call_ollama_for_action(prompt)
        else:
            raise ValueError(f"Unknown AI service: {self.ai_service}")
    
    def _build_ai_prompt(self, step_text: str, dom_data: Dict[str, Any], 
                        current_url: str, page_title: str) -> str:
        """Build prompt for AI to interpret the step"""
        
        # Summarize DOM (don't send everything)
        inputs_summary = [
            f"- {el['tag']}#{el['id'] or el['name'] or el['placeholder'] or 'unknown'} (type: {el.get('type', 'text')})"
            for el in dom_data.get('inputs', [])[:20]  # Limit to 20
        ]
        
        buttons_summary = [
            f"- {el['text'] or el['id'] or 'button'}"
            for el in dom_data.get('buttons', [])[:20]
        ]
        
        links_summary = [
            f"- {el['text'] or el['href'] or 'link'}"
            for el in dom_data.get('links', [])[:20]
        ]
        
        # Include test credentials in prompt
        credentials_info = f"""
CONFIGURED TEST CREDENTIALS (USE THESE, NOT LITERAL TEXT FROM STEPS):
- Test Username: {self.test_credentials.get('username', '[not configured]')}
- Test Password: {self.test_credentials.get('password', '[not configured]')}
- Admin Username: {self.test_credentials.get('admin_username', '[not configured]')}
- Admin Password: {self.test_credentials.get('admin_password', '[not configured]')}

[WARN] CRITICAL: When steps mention "username" or "password", ALWAYS use the configured credentials above.
DO NOT use literal text like "valid_uw_username" or "abcd" from the step text.
"""
        
        return f"""You are an expert test automation AI. Interpret this Gherkin step and determine the exact Playwright action needed.

CURRENT STATE:
- URL: {current_url}
- Page Title: {page_title}

AVAILABLE ELEMENTS:
Inputs: {chr(10).join(inputs_summary) if inputs_summary else 'None'}
Buttons: {chr(10).join(buttons_summary) if buttons_summary else 'None'}
Links: {chr(10).join(links_summary) if links_summary else 'None'}

{credentials_info}

GHERKIN STEP TO EXECUTE:
"{step_text}"

[WARN] CRITICAL CREDENTIAL RULES:
1. If step mentions "username" or "user name" or "my username" → USE configured Test Username above
2. If step mentions "password" or "my password" → USE configured Test Password above  
3. If step mentions "admin" credentials → USE configured Admin Username/Password above
4. NEVER type literal placeholder text from step like "valid_uw_username" or "abcd"
5. The step text is just a DESCRIPTION - use the CONFIGURED credentials, not the example text

EXAMPLES:

Step: "When I enter valid_uw_username in the username field"
WRONG: {{"value": "valid_uw_username"}}  [ERR] Don't use literal step text!
RIGHT: {{"value": "{self.test_credentials.get('username', 'testuser@example.com')}"}}  [OK] Use configured credential!

Step: "When I type my username"
RIGHT: {{"value": "{self.test_credentials.get('username', 'testuser@example.com')}"}}  [OK]

Step: "When I enter the password"
RIGHT: {{"value": "{self.test_credentials.get('password', 'testpassword123')}"}}  [OK]

Step: "When I enter abcd in the password field"
WRONG: {{"value": "abcd"}}  [ERR] "abcd" is just a placeholder!
RIGHT: {{"value": "{self.test_credentials.get('password', 'testpassword123')}"}}  [OK]

RESPONSE FORMAT (return ONLY valid JSON):
{{
  "action_type": "navigate|click|type|select|wait|assert_visible|assert_text|assert_url",
  "target": "selector or URL or text to find",
  "value": "value to type or select (if applicable)",
  "reasoning": "brief explanation of your decision",
  "selector_strategy": "id|text|placeholder|name|css",
  "wait_for": "optional: what to wait for after action"
}}

RESPONSE EXAMPLES:

Step: "Given I am on the login page"
{{
  "action_type": "navigate",
  "target": "/login",
  "reasoning": "Navigate to login page URL"
}}

Step: "When I enter valid_uw_username in username field"
{{
  "action_type": "type",
  "target": "input#username",
  "value": "{self.test_credentials.get('username', 'testuser@example.com')}",
  "selector_strategy": "id",
  "reasoning": "Type configured test username (not literal 'valid_uw_username' text)"
}}

Step: "When I enter my password"
{{
  "action_type": "type",
  "target": "input[type='password']",
  "value": "{self.test_credentials.get('password', 'testpassword123')}",
  "selector_strategy": "css",
  "reasoning": "Type configured test password"
}}

Step: "When I click the login button"
{{
  "action_type": "click",
  "target": "button:has-text('Login')",
  "selector_strategy": "text",
  "reasoning": "Click button with text 'Login'"
}}

Step: "Then I should see the dashboard"
{{
  "action_type": "assert_visible",
  "target": "text=Dashboard",
  "reasoning": "Verify dashboard is visible"
}}

Return ONLY the JSON object, no explanations or markdown."""
    
    def _call_anthropic_for_action(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API"""
        import anthropic
        
        client = anthropic.Anthropic(api_key=self.ai_key)
        
        message = client.messages.create(
            model=self.ai_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        
        # Parse JSON response
        return self._parse_ai_response(response_text)
    
    def _call_ollama_for_action(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API"""
        payload = {
            "model": self.ai_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1}
        }
        
        response = requests.post(self.ai_url, json=payload, timeout=60)
        response.raise_for_status()
        response_text = response.json().get("response", "")
        
        # Parse JSON response
        return self._parse_ai_response(response_text)
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response to JSON"""
        try:
            # Clean response
            cleaned = response_text.strip()
            
            # Remove markdown if present
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            
            cleaned = cleaned.strip()
            
            # Extract JSON if wrapped
            if not cleaned.startswith("{"):
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                if start != -1 and end > start:
                    cleaned = cleaned[start:end]
            
            # Parse
            decision = json.loads(cleaned)
            
            # Validate required fields
            if "action_type" not in decision:
                raise ValueError("Missing action_type in AI response")
            
            return decision
            
        except Exception as e:
            print(f"[WARN] AI response parse error: {str(e)}")
            print(f"Response was: {response_text[:200]}")
            raise Exception(f"Failed to parse AI response: {str(e)}")
    
    def _execute_ai_decision(self, decision: Dict[str, Any], result: AutonomousScenarioResult):
        """Execute the action decided by AI"""
        action_type = decision.get("action_type")
        target = decision.get("target", "")
        value = decision.get("value", "")
        reasoning = decision.get("reasoning", "")
        
        result.add_log(f" AI Decision: {action_type} - {reasoning}")
        
        try:
            if action_type == "navigate":
                url = target
                if not url.startswith("http"):
                    # Ensure base_url is set before constructing relative URLs
                    if not self.base_url:
                        raise ValueError(f"Cannot navigate to relative URL '{target}' - base_url is not configured. Please set base_url in the project settings.")
                    # Construct full URL from base_url and path
                    base = self.base_url.rstrip('/')
                    path = target if target.startswith('/') else '/' + target
                    url = base + path
                result.add_log(f"→ Navigating to: {url}")
                self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                self.page.wait_for_load_state('networkidle', timeout=30000)
                
            elif action_type == "click":
                result.add_log(f"→ Clicking: {target}")
                # Try multiple selector strategies
                self._smart_click(target)
                
            elif action_type == "type":
                result.add_log(f"→ Typing '{value}' into: {target}")
                self._smart_type(target, value)
                
            elif action_type == "select":
                result.add_log(f"→ Selecting '{value}' from: {target}")
                self.page.wait_for_selector(target, state='visible', timeout=10000)
                self.page.select_option(target, value)
                
            elif action_type == "wait":
                wait_ms = int(value) if value.isdigit() else 1000
                result.add_log(f"→ Waiting: {wait_ms}ms")
                time.sleep(wait_ms / 1000)
                
            elif action_type == "assert_visible":
                result.add_log(f"→ Asserting visible: {target}")
                self.page.wait_for_selector(target, state='visible', timeout=10000)
                
            elif action_type == "assert_text":
                result.add_log(f"→ Asserting text present: {value}")
                self.page.wait_for_selector(f"text={value}", timeout=10000)
                
            elif action_type == "assert_url":
                result.add_log(f"→ Asserting URL contains: {target}")
                current_url = self.page.url
                if target not in current_url:
                    raise AssertionError(f"Expected '{target}' in URL but got '{current_url}'")
            
            else:
                raise ValueError(f"Unknown action type: {action_type}")
            
            # Wait for page to stabilize
            time.sleep(0.5)
            
        except Exception as e:
            raise Exception(f"AI action failed: {action_type} on {target} - {str(e)}")
    
    def _smart_click(self, target: str):
        """Smart click with multiple fallback strategies and wait after"""
        strategies = [
            lambda: self.page.click(target, timeout=5000),
            lambda: self.page.locator(target).first.click(timeout=5000),
            lambda: self.page.get_by_text(target, exact=False).first.click(timeout=5000),
            lambda: self.page.get_by_role("button", name=target).click(timeout=5000),
            lambda: self.page.get_by_role("link", name=target).click(timeout=5000),
        ]
        
        last_error = None
        for strategy in strategies:
            try:
                strategy()
                # CRITICAL: Wait for page to stabilize after click!
                self.page.wait_for_load_state("domcontentloaded", timeout=5000)
                self.page.wait_for_timeout(500)
                print(f"[SMART_CLICK] SUCCESS - clicked '{target}'")
                return  # Success!
            except Exception as e:
                last_error = e
                continue
        
        raise Exception(f"Could not click '{target}': {str(last_error)}")
    
    def _simulate_real_typing(self, locator, value: str) -> bool:
        """
        Simulate REAL user typing to trigger form validation properly.
        fill() doesn't trigger React/Vue/Angular change events!
        """
        try:
            # Wait for element to be visible
            locator.wait_for(state="visible", timeout=5000)
            self.page.wait_for_timeout(200)
            
            # Click to focus
            locator.click(timeout=2000)
            self.page.wait_for_timeout(150)
            
            # Clear existing content
            locator.press("Control+a")
            self.page.wait_for_timeout(100)
            
            # Type character by character (triggers input events)
            if value:
                locator.press_sequentially(value, delay=50)
            else:
                locator.press("Backspace")
            
            # Tab out to trigger blur/validation
            self.page.wait_for_timeout(150)
            locator.press("Tab")
            self.page.wait_for_timeout(200)
            
            return True
        except Exception as e:
            print(f"[DEBUG] _simulate_real_typing failed: {e}")
            return False

    def _smart_type(self, target: str, value: str):
        """Smart type with REAL typing simulation for proper form validation"""
        print(f"[SMART_TYPE] Target: '{target}', Value: '{value}'")

        # Normalize for Keycloak field matching
        t = target.lower().replace(' ','').replace('*','').replace('_','').replace('-','')
        
        # Keycloak field ID map
        ids = {
            'username': ['username','user','login'],
            'password': ['password','passwd','pwd'],
            'confirmpassword': ['password-confirm','passwordConfirm'],
            'email': ['email','mail'],
            'firstname': ['firstName','first-name','fname'],
            'lastname': ['lastName','last-name','lname'],
        }
        
        # Strategy 0: Try Keycloak IDs first
        for fid in ids.get(t, [t]):
            try:
                loc = self.page.locator(f'#{fid}')
                if loc.count() > 0:
                    print(f'[SMART_TYPE] Found #{fid}')
                    if self._simulate_real_typing(loc.first, value):
                        print(f'[SMART_TYPE] SUCCESS via #{fid}')
                        return
            except: pass
            try:
                loc = self.page.locator(f"input[name='{fid}']")
                if loc.count() > 0:
                    print(f'[SMART_TYPE] Found name={fid}')
                    if self._simulate_real_typing(loc.first, value):
                        print(f'[SMART_TYPE] SUCCESS via name={fid}')
                        return
            except: pass

        # Strategy 1: By CSS selector
        try:
            locator = self.page.locator(target).first
            if locator.is_visible(timeout=2000):
                if self._simulate_real_typing(locator, value):
                    print(f"[SMART_TYPE] SUCCESS via CSS selector")
                    return
        except Exception as e:
            print(f"[SMART_TYPE] CSS selector failed: {e}")
        
        # Strategy 2: By placeholder
        try:
            locator = self.page.get_by_placeholder(target, exact=False).first
            if locator.is_visible(timeout=2000):
                if self._simulate_real_typing(locator, value):
                    print(f"[SMART_TYPE] SUCCESS via placeholder")
                    return
        except Exception as e:
            print(f"[SMART_TYPE] Placeholder failed: {e}")
        
        # Strategy 3: By label
        try:
            locator = self.page.get_by_label(target, exact=False).first
            if locator.is_visible(timeout=2000):
                if self._simulate_real_typing(locator, value):
                    print(f"[SMART_TYPE] SUCCESS via label")
                    return
        except Exception as e:
            print(f"[SMART_TYPE] Label failed: {e}")
        
        # Strategy 4: By role textbox with name
        try:
            locator = self.page.get_by_role("textbox", name=target).first
            if locator.is_visible(timeout=2000):
                if self._simulate_real_typing(locator, value):
                    print(f"[SMART_TYPE] SUCCESS via role textbox")
                    return
        except Exception as e:
            print(f"[SMART_TYPE] Role textbox failed: {e}")
        
        # Strategy 5: Find input near text
        try:
            locator = self.page.locator(f"input:near(:text('{target}'))").first
            if locator.is_visible(timeout=2000):
                if self._simulate_real_typing(locator, value):
                    print(f"[SMART_TYPE] SUCCESS via :near selector")
                    return
        except Exception as e:
            print(f"[SMART_TYPE] :near selector failed: {e}")
        
        raise Exception(f"Could not type into '{target}' - all strategies failed")


# Convenience function
def run_feature_autonomously(feature: GherkinFeature, base_url: str = "", 
                             headless: bool = False) -> AutonomousFeatureResult:
    """Quick utility to run a feature autonomously with AI"""
    executor = AutonomousGherkinExecutor(base_url=base_url, headless=headless)
    
    try:
        executor.setup()
        result = executor.execute_feature(feature)
        return result
    finally:
        executor.teardown()