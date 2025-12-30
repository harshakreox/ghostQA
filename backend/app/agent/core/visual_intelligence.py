"""
Visual Intelligence Module for GhostQA
Adds screenshot-based AI decision making to the SEI pipeline.
Analyzes page screenshots to understand context and determine actions.
"""

import asyncio
import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PageContext(Enum):
    """Types of page contexts detected from visual analysis"""
    LOGIN_PAGE = "login_page"
    REGISTRATION_PAGE = "registration_page"
    FORM_PAGE = "form_page"
    DASHBOARD = "dashboard"
    LIST_VIEW = "list_view"
    DETAIL_VIEW = "detail_view"
    CHECKOUT = "checkout"
    SEARCH_PAGE = "search_page"
    ERROR_PAGE = "error_page"
    MODAL_DIALOG = "modal_dialog"
    CONFIRMATION = "confirmation"
    UNKNOWN = "unknown"


class ActionIntent(Enum):
    """Action intents determined by visual analysis"""
    FILL_FORM = "fill_form"
    CLICK_BUTTON = "click_button"
    CLICK_LINK = "click_link"
    SELECT_OPTION = "select_option"
    NAVIGATE = "navigate"
    WAIT = "wait"
    VERIFY_TEXT = "verify_text"
    VERIFY_ELEMENT = "verify_element"
    CLOSE_MODAL = "close_modal"
    SUBMIT_FORM = "submit_form"
    SCROLL = "scroll"
    UNKNOWN = "unknown"


@dataclass
class VisualAnalysisResult:
    """Result of visual analysis"""
    page_context: PageContext
    detected_elements: List[Dict[str, Any]]
    form_fields: List[Dict[str, Any]]
    buttons: List[Dict[str, Any]]
    suggested_actions: List[Dict[str, Any]]
    confidence: float
    screenshot_path: Optional[str] = None
    raw_analysis: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class FormFieldInfo:
    """Information about a detected form field"""
    field_type: str  # text, email, password, select, checkbox, etc.
    field_name: str  # Name/label of the field
    selector: str  # CSS/XPath selector
    placeholder: Optional[str] = None
    required: bool = False
    current_value: Optional[str] = None
    options: Optional[List[str]] = None  # For select fields


class VisualIntelligence:
    """
    Visual Intelligence engine that uses screenshots and AI vision
    to understand page context and determine appropriate actions.
    """

    def __init__(self, ai_provider: str = "anthropic"):
        self.ai_provider = ai_provider
        self.screenshot_dir = Path("data/agent_knowledge/screenshots/visual_analysis")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._analysis_cache: Dict[str, VisualAnalysisResult] = {}

        # Test data generator integration
        try:
            from test_data_generator import TestDataGenerator
            self.data_generator = TestDataGenerator()
        except ImportError:
            self.data_generator = None
            logger.warning("TestDataGenerator not available - form filling will be limited")

    async def analyze_page(
        self,
        page,
        step_description: Optional[str] = None,
        take_screenshot: bool = True
    ) -> VisualAnalysisResult:
        """
        Analyze the current page using screenshot and AI vision.

        Args:
            page: Playwright page object
            step_description: Optional description of what we're trying to do
            take_screenshot: Whether to capture a new screenshot

        Returns:
            VisualAnalysisResult with page context and suggested actions
        """
        screenshot_path = None
        screenshot_base64 = None

        if take_screenshot:
            try:
                # Capture screenshot
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                screenshot_path = str(self.screenshot_dir / f"analysis_{timestamp}.png")
                await page.screenshot(path=screenshot_path, full_page=False)

                # Read as base64 for AI analysis
                with open(screenshot_path, "rb") as f:
                    screenshot_base64 = base64.standard_b64encode(f.read()).decode("utf-8")

            except Exception as e:
                logger.error(f"Failed to capture screenshot: {e}")

        # Get page HTML for supplementary analysis
        try:
            page_html = await page.content()
            page_url = page.url
        except Exception as e:
            logger.error(f"Failed to get page content: {e}")
            page_html = ""
            page_url = ""

        # Analyze using AI vision
        analysis = await self._analyze_with_ai(
            screenshot_base64=screenshot_base64,
            page_html=page_html,
            page_url=page_url,
            step_description=step_description
        )

        analysis.screenshot_path = screenshot_path
        return analysis

    async def _analyze_with_ai(
        self,
        screenshot_base64: Optional[str],
        page_html: str,
        page_url: str,
        step_description: Optional[str]
    ) -> VisualAnalysisResult:
        """Use AI to analyze the page"""

        # Build the prompt
        prompt = self._build_analysis_prompt(page_url, step_description, page_html)

        try:
            if self.ai_provider == "anthropic":
                response = await self._call_anthropic(prompt, screenshot_base64)
            elif self.ai_provider == "ollama":
                response = await self._call_ollama(prompt, screenshot_base64)
            else:
                response = await self._call_anthropic(prompt, screenshot_base64)

            return self._parse_analysis_response(response)

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Return a basic fallback analysis from HTML
            return self._fallback_html_analysis(page_html, page_url, step_description)

    def _build_analysis_prompt(
        self,
        page_url: str,
        step_description: Optional[str],
        page_html: str
    ) -> str:
        """Build the prompt for AI analysis"""

        # Extract form fields from HTML for context
        form_context = self._extract_form_fields_from_html(page_html)

        prompt = f"""Analyze this web page and provide structured information for test automation.

URL: {page_url}
{f'Step to execute: {step_description}' if step_description else ''}

Form fields detected in HTML:
{json.dumps(form_context, indent=2) if form_context else 'None detected'}

Please analyze the page (screenshot if provided) and return a JSON response with:

{{
    "page_context": "login_page|registration_page|form_page|dashboard|list_view|detail_view|checkout|search_page|error_page|modal_dialog|confirmation|unknown",
    "confidence": 0.0-1.0,
    "detected_elements": [
        {{"type": "input|button|link|select|checkbox|radio", "purpose": "description", "selector": "css_selector", "visible": true}}
    ],
    "form_fields": [
        {{"name": "field_name", "type": "text|email|password|tel|select|checkbox|radio|date", "selector": "css_selector", "required": true|false, "placeholder": "hint text"}}
    ],
    "buttons": [
        {{"text": "button_text", "type": "submit|cancel|action", "selector": "css_selector"}}
    ],
    "suggested_actions": [
        {{"action": "fill|click|select|type|wait|verify", "target": "element_description", "selector": "css_selector", "value": "value_if_applicable", "priority": 1-10}}
    ],
    "interpretation": "Brief description of what's on the page and what actions are needed"
}}

Focus on:
1. Identifying all form fields and their purpose (username, email, password, etc.)
2. Finding primary action buttons (Submit, Login, Register, etc.)
3. Detecting any error messages or validation states
4. Understanding the page context to determine appropriate test data

Return ONLY valid JSON, no markdown formatting or extra text."""

        return prompt

    async def _call_anthropic(self, prompt: str, screenshot_base64: Optional[str]) -> str:
        """Call Anthropic Claude API with vision capability"""
        import httpx

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        messages_content = []

        # Add screenshot if available
        if screenshot_base64:
            messages_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_base64
                }
            })

        messages_content.append({
            "type": "text",
            "text": prompt
        })

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": messages_content
                        }
                    ]
                }
            )

            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.text}")

            data = response.json()
            return data["content"][0]["text"]

    async def _call_ollama(self, prompt: str, screenshot_base64: Optional[str]) -> str:
        """Call Ollama API (with llava for vision if screenshot provided)"""
        import httpx

        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

        # Use llava for vision if we have a screenshot, otherwise use llama
        model = "llava" if screenshot_base64 else "llama3.2:3b"

        request_body = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        if screenshot_base64 and model == "llava":
            request_body["images"] = [screenshot_base64]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json=request_body
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.text}")

            data = response.json()
            return data.get("response", "")

    def _parse_analysis_response(self, response: str) -> VisualAnalysisResult:
        """Parse the AI analysis response into structured result"""
        try:
            # Clean up the response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```\w*\n?', '', cleaned)
                cleaned = re.sub(r'\n?```$', '', cleaned)

            data = json.loads(cleaned)

            # Map page context
            context_map = {
                "login_page": PageContext.LOGIN_PAGE,
                "registration_page": PageContext.REGISTRATION_PAGE,
                "form_page": PageContext.FORM_PAGE,
                "dashboard": PageContext.DASHBOARD,
                "list_view": PageContext.LIST_VIEW,
                "detail_view": PageContext.DETAIL_VIEW,
                "checkout": PageContext.CHECKOUT,
                "search_page": PageContext.SEARCH_PAGE,
                "error_page": PageContext.ERROR_PAGE,
                "modal_dialog": PageContext.MODAL_DIALOG,
                "confirmation": PageContext.CONFIRMATION
            }

            page_context = context_map.get(
                data.get("page_context", "").lower(),
                PageContext.UNKNOWN
            )

            return VisualAnalysisResult(
                page_context=page_context,
                detected_elements=data.get("detected_elements", []),
                form_fields=data.get("form_fields", []),
                buttons=data.get("buttons", []),
                suggested_actions=data.get("suggested_actions", []),
                confidence=float(data.get("confidence", 0.5)),
                raw_analysis=data.get("interpretation", "")
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return VisualAnalysisResult(
                page_context=PageContext.UNKNOWN,
                detected_elements=[],
                form_fields=[],
                buttons=[],
                suggested_actions=[],
                confidence=0.0,
                raw_analysis=response
            )

    def _fallback_html_analysis(
        self,
        page_html: str,
        page_url: str,
        step_description: Optional[str]
    ) -> VisualAnalysisResult:
        """Fallback analysis using just HTML when AI is unavailable"""

        form_fields = self._extract_form_fields_from_html(page_html)
        buttons = self._extract_buttons_from_html(page_html)

        # Determine page context from URL and elements
        page_context = self._infer_page_context(page_url, form_fields, page_html)

        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(
            page_context, form_fields, buttons, step_description
        )

        return VisualAnalysisResult(
            page_context=page_context,
            detected_elements=[],
            form_fields=form_fields,
            buttons=buttons,
            suggested_actions=suggested_actions,
            confidence=0.6,
            raw_analysis="Fallback HTML analysis (AI unavailable)"
        )

    def _extract_form_fields_from_html(self, html: str) -> List[Dict[str, Any]]:
        """Extract form fields from HTML with comprehensive metadata"""
        from bs4 import BeautifulSoup

        fields = []
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find all input fields
            for inp in soup.find_all(['input', 'textarea', 'select']):
                field_type = inp.get('type', 'text')
                if field_type in ('hidden', 'submit', 'button'):
                    continue

                # Get all available identifiers for better data generation
                field_name = inp.get('name', '')
                field_id = inp.get('id', '')
                field_placeholder = inp.get('placeholder', '')
                field_aria = inp.get('aria-label', '')
                field_autocomplete = inp.get('autocomplete', '')  # e.g., "email", "tel", "given-name"
                field_label = self._find_label_for_input(soup, inp)

                # Also check for data attributes that might indicate field purpose
                data_testid = inp.get('data-testid', '') or inp.get('data-test', '') or inp.get('data-cy', '')

                field = {
                    "name": field_name or field_id or '',
                    "id": field_id,
                    "type": field_type if inp.name != 'select' else 'select',
                    "selector": self._build_selector(inp),
                    "required": inp.has_attr('required'),
                    "placeholder": field_placeholder,
                    "aria_label": field_aria,
                    "autocomplete": field_autocomplete,  # This is very useful for field type detection!
                    "label": field_label,
                    "data_testid": data_testid
                }

                # Log for debugging
                logger.debug(f"[FIELD] Found: name={field_name}, label={field_label}, placeholder={field_placeholder}, autocomplete={field_autocomplete}")

                # Get options for select fields
                if inp.name == 'select':
                    field["options"] = [
                        opt.get('value', opt.text.strip())
                        for opt in inp.find_all('option')
                    ]

                fields.append(field)

        except Exception as e:
            logger.error(f"Failed to extract form fields: {e}")

        return fields

    def _extract_buttons_from_html(self, html: str) -> List[Dict[str, Any]]:
        """Extract buttons from HTML"""
        from bs4 import BeautifulSoup

        buttons = []
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find button elements and input[type=submit/button]
            for btn in soup.find_all(['button', 'input']):
                if btn.name == 'input' and btn.get('type') not in ('submit', 'button'):
                    continue

                text = btn.get_text(strip=True) or btn.get('value', '')
                btn_type = "submit" if btn.get('type') == 'submit' else "action"

                buttons.append({
                    "text": text,
                    "type": btn_type,
                    "selector": self._build_selector(btn)
                })

            # Also find links that look like buttons (common pattern)
            for link in soup.find_all('a', class_=re.compile(r'btn|button', re.I)):
                buttons.append({
                    "text": link.get_text(strip=True),
                    "type": "link",
                    "selector": self._build_selector(link)
                })

        except Exception as e:
            logger.error(f"Failed to extract buttons: {e}")

        return buttons

    def _build_selector(self, element) -> str:
        """Build a CSS selector for an element"""
        # Priority: data-testid > id > name > class combination
        if element.get('data-testid'):
            return f'[data-testid="{element["data-testid"]}"]'
        if element.get('data-test'):
            return f'[data-test="{element["data-test"]}"]'
        if element.get('id'):
            return f'#{element["id"]}'
        if element.get('name'):
            return f'[name="{element["name"]}"]'
        if element.get('class'):
            classes = '.'.join(element['class'][:2])  # First 2 classes
            return f'{element.name}.{classes}'
        if element.get('placeholder'):
            return f'[placeholder="{element["placeholder"]}"]'
        return element.name

    def _find_label_for_input(self, soup, inp) -> str:
        """Find the label associated with an input"""
        # Check for label with 'for' attribute
        inp_id = inp.get('id')
        if inp_id:
            label = soup.find('label', attrs={'for': inp_id})
            if label:
                return label.get_text(strip=True)

        # Check for parent label
        parent_label = inp.find_parent('label')
        if parent_label:
            return parent_label.get_text(strip=True)

        # Check for preceding label sibling
        prev = inp.find_previous_sibling('label')
        if prev:
            return prev.get_text(strip=True)

        return ""

    def _infer_page_context(
        self,
        url: str,
        form_fields: List[Dict],
        html: str
    ) -> PageContext:
        """Infer page context from URL and elements"""
        url_lower = url.lower()

        # URL-based detection
        if any(x in url_lower for x in ['login', 'signin', 'sign-in']):
            return PageContext.LOGIN_PAGE
        if any(x in url_lower for x in ['register', 'signup', 'sign-up', 'create-account']):
            return PageContext.REGISTRATION_PAGE
        if any(x in url_lower for x in ['checkout', 'payment', 'cart']):
            return PageContext.CHECKOUT
        if any(x in url_lower for x in ['dashboard', 'home', 'overview']):
            return PageContext.DASHBOARD
        if any(x in url_lower for x in ['search', 'find']):
            return PageContext.SEARCH_PAGE

        # Field-based detection
        field_names = ' '.join([f.get('name', '') + f.get('placeholder', '') + f.get('label', '') for f in form_fields]).lower()

        if 'password' in field_names:
            if any(x in field_names for x in ['confirm', 'email', 'first', 'last', 'name']):
                return PageContext.REGISTRATION_PAGE
            return PageContext.LOGIN_PAGE

        if form_fields:
            return PageContext.FORM_PAGE

        return PageContext.UNKNOWN

    def _generate_suggested_actions(
        self,
        page_context: PageContext,
        form_fields: List[Dict],
        buttons: List[Dict],
        step_description: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Generate suggested actions based on analysis"""
        actions = []
        priority = 1

        # Fill form fields
        for field in form_fields:
            value = self._generate_field_value(field)
            actions.append({
                "action": "fill",
                "target": field.get("name") or field.get("label") or "field",
                "selector": field.get("selector"),
                "value": value,
                "priority": priority
            })
            priority += 1

        # Add button click for submit
        for btn in buttons:
            if btn.get("type") == "submit" or any(
                x in btn.get("text", "").lower()
                for x in ['submit', 'login', 'sign', 'register', 'continue', 'next']
            ):
                actions.append({
                    "action": "click",
                    "target": btn.get("text"),
                    "selector": btn.get("selector"),
                    "priority": priority
                })
                break

        return actions

    def _generate_field_value(self, field: Dict) -> str:
        """Generate appropriate test data for a field based on ALL available metadata"""
        # Combine ALL field identifiers for better matching
        field_name = field.get("name", "")
        field_label = field.get("label", "")
        field_placeholder = field.get("placeholder", "")
        field_aria = field.get("aria_label", "") or field.get("aria-label", "")
        field_id = field.get("id", "")
        field_type = field.get("type", "text").lower()
        field_autocomplete = field.get("autocomplete", "").lower()  # e.g., "email", "tel", "given-name"

        # Combine all identifiers into searchable text
        all_identifiers = f"{field_name} {field_label} {field_placeholder} {field_aria} {field_id} {field_autocomplete}".lower()

        # AUTOCOMPLETE attribute is the most reliable indicator - check first!
        # Common autocomplete values: email, tel, given-name, family-name, username, current-password, new-password
        if field_autocomplete:
            if field_autocomplete in ('email', 'username email'):
                return f"test_{datetime.now().strftime('%H%M%S')}@example.com"
            if field_autocomplete in ('tel', 'tel-national', 'tel-local'):
                return "555-123-4567"
            if field_autocomplete in ('given-name', 'first-name'):
                return "John"
            if field_autocomplete in ('family-name', 'last-name', 'surname'):
                return "Doe"
            if field_autocomplete in ('name', 'full-name'):
                return "John Doe"
            if field_autocomplete in ('username', 'nickname'):
                return f"user_{datetime.now().strftime('%H%M%S')}"
            if field_autocomplete in ('current-password', 'new-password', 'password'):
                return "TestPass123!"
            if field_autocomplete in ('street-address', 'address-line1'):
                return "123 Test Street"
            if field_autocomplete in ('address-level2',):  # city
                return "Test City"
            if field_autocomplete in ('address-level1',):  # state
                return "California"
            if field_autocomplete in ('postal-code', 'zip'):
                return "12345"
            if field_autocomplete in ('country', 'country-name'):
                return "United States"
            if field_autocomplete in ('bday', 'birthday'):
                return "1990-01-15"
            if field_autocomplete in ('organization', 'company'):
                return "Test Company Inc."

        logger.debug(f"[DATA-GEN] Field identifiers: {all_identifiers[:80]}...")

        if self.data_generator:
            # Use the most descriptive identifier for data generation
            best_identifier = field_label or field_placeholder or field_aria or field_name or ""
            if best_identifier:
                return self.data_generator.generate_for_field(best_identifier)

        # Fallback: pattern matching on combined identifiers
        # Email detection
        if field_type == "email" or any(x in all_identifiers for x in ['email', 'e-mail', 'mail']):
            return f"test_{datetime.now().strftime('%H%M%S')}@example.com"

        # Password detection
        if field_type == "password" or 'password' in all_identifiers or 'passwd' in all_identifiers:
            return "TestPass123!"

        # Name fields
        if any(x in all_identifiers for x in ['first name', 'firstname', 'first_name', 'fname', 'given name']):
            return "John"
        if any(x in all_identifiers for x in ['last name', 'lastname', 'last_name', 'lname', 'surname', 'family name']):
            return "Doe"
        if any(x in all_identifiers for x in ['full name', 'fullname', 'your name']) or ('name' in all_identifiers and 'user' not in all_identifiers):
            return "John Doe"

        # Username detection
        if any(x in all_identifiers for x in ['username', 'user name', 'user_name', 'userid', 'login']):
            return f"user_{datetime.now().strftime('%H%M%S')}"

        # Phone detection
        if field_type == "tel" or any(x in all_identifiers for x in ['phone', 'mobile', 'cell', 'telephone', 'contact number']):
            return "555-123-4567"

        # Address fields
        if any(x in all_identifiers for x in ['street', 'address line', 'address1', 'street address']):
            return "123 Test Street"
        if 'city' in all_identifiers or 'town' in all_identifiers:
            return "Test City"
        if any(x in all_identifiers for x in ['state', 'province', 'region']):
            return "California"
        if any(x in all_identifiers for x in ['zip', 'postal', 'postcode']):
            return "12345"
        if 'country' in all_identifiers:
            return "United States"

        # Company/organization
        if any(x in all_identifiers for x in ['company', 'organization', 'org name', 'business']):
            return "Test Company Inc."

        # Date fields
        if field_type == "date" or any(x in all_identifiers for x in ['date of birth', 'dob', 'birthday', 'birth date']):
            return "1990-01-15"

        # Generic fallback with timestamp
        return f"test_value_{datetime.now().strftime('%H%M%S')}"

    async def determine_action_from_step(
        self,
        page,
        step_text: str,
        analysis: Optional[VisualAnalysisResult] = None
    ) -> Dict[str, Any]:
        """
        Determine the concrete action to take based on a step description.

        Args:
            page: Playwright page object
            step_text: Natural language step description (e.g., "fill in the registration form")
            analysis: Optional pre-computed page analysis

        Returns:
            Action dictionary with action type, selector, and value
        """
        if not analysis:
            analysis = await self.analyze_page(page, step_text)

        step_lower = step_text.lower()

        # Determine intent from step text
        if any(x in step_lower for x in ['fill', 'complete', 'enter', 'type', 'input']):
            if 'form' in step_lower or not analysis.form_fields:
                # Fill the entire form
                return {
                    "action": "fill_form",
                    "fields": analysis.form_fields,
                    "values": {
                        f.get("selector"): self._generate_field_value(f)
                        for f in analysis.form_fields
                    }
                }
            else:
                # Fill specific field - find best match
                best_field = self._find_best_matching_field(step_text, analysis.form_fields)
                if best_field:
                    return {
                        "action": "fill",
                        "selector": best_field.get("selector"),
                        "value": self._generate_field_value(best_field)
                    }

        if any(x in step_lower for x in ['click', 'press', 'tap', 'submit']):
            # Find best matching button
            best_button = self._find_best_matching_button(step_text, analysis.buttons)
            if best_button:
                return {
                    "action": "click",
                    "selector": best_button.get("selector"),
                    "target": best_button.get("text")
                }

        if any(x in step_lower for x in ['see', 'verify', 'check', 'should', 'assert']):
            return {
                "action": "verify",
                "target": step_text
            }

        if any(x in step_lower for x in ['wait', 'pause']):
            return {
                "action": "wait",
                "duration": 2000
            }

        # Default: use AI-suggested actions
        if analysis.suggested_actions:
            return analysis.suggested_actions[0]

        return {
            "action": "unknown",
            "target": step_text,
            "error": "Could not determine action from step"
        }

    def _find_best_matching_field(
        self,
        step_text: str,
        fields: List[Dict]
    ) -> Optional[Dict]:
        """Find the field that best matches the step description"""
        step_lower = step_text.lower()

        best_score = 0
        best_field = None

        for field in fields:
            score = 0
            field_text = ' '.join([
                str(field.get("name", "")),
                str(field.get("label", "")),
                str(field.get("placeholder", ""))
            ]).lower()

            # Check for keyword matches
            for word in step_lower.split():
                if len(word) > 2 and word in field_text:
                    score += 1

            if score > best_score:
                best_score = score
                best_field = field

        return best_field

    def _find_best_matching_button(
        self,
        step_text: str,
        buttons: List[Dict]
    ) -> Optional[Dict]:
        """Find the button that best matches the step description"""
        step_lower = step_text.lower()

        best_score = 0
        best_button = None

        for button in buttons:
            score = 0
            button_text = button.get("text", "").lower()

            # Direct text match
            if button_text in step_lower:
                score += 5

            # Word matches
            for word in step_lower.split():
                if len(word) > 2 and word in button_text:
                    score += 1

            # Common action words
            if any(x in button_text for x in ['submit', 'login', 'register', 'sign', 'continue']):
                if any(x in step_lower for x in ['submit', 'login', 'register', 'sign', 'continue']):
                    score += 3

            if score > best_score:
                best_score = score
                best_button = button

        return best_button

    async def execute_form_fill(
        self,
        page,
        fields: Optional[List[Dict]] = None,
        values: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute form fill with generated or provided data.

        Args:
            page: Playwright page object
            fields: Optional list of field definitions
            values: Optional pre-defined values for fields

        Returns:
            Result dictionary with filled fields
        """
        if not fields:
            analysis = await self.analyze_page(page, "fill form")
            fields = analysis.form_fields

        results = {
            "filled_fields": [],
            "failed_fields": [],
            "success": True
        }

        for field in fields:
            selector = field.get("selector")
            value = values.get(selector) if values else self._generate_field_value(field)

            # Validate value - must not be a field descriptor or step description
            value_lower = value.lower() if value else ''
            invalid_patterns = [
                'email_address', 'mail_address', 'auto_complete', 'autocomplete',
                'complete_remaining', 'remaining_fields', 'required_fields',
                'fill_form', 'complete_form', 'valid_email', 'test_field'
            ]
            action_words = ['complete', 'remaining', 'required', 'enter', 'valid', 'field', 'form']
            normalized = value_lower.replace(' ', '_').replace('-', '_')

            if any(p in normalized for p in invalid_patterns) or sum(1 for w in action_words if w in value_lower) >= 2:
                logger.warning(f"[VI] Invalid value '{value}' detected, generating proper value")
                # Generate proper fallback based on field type
                field_name = (field.get("name") or field.get("label") or "").lower()
                if 'email' in field_name or field.get("type") == "email":
                    value = f"test_{datetime.now().strftime('%H%M%S%f')[:10]}@testmail.com"
                elif 'password' in field_name or field.get("type") == "password":
                    value = "TestPass123!"
                else:
                    value = f"TestValue{datetime.now().strftime('%H%M%S')}"

            try:
                field_type = field.get("type", "text")

                if field_type == "select":
                    await page.select_option(selector, value)
                elif field_type in ("checkbox", "radio"):
                    await page.check(selector)
                else:
                    await page.fill(selector, value)

                results["filled_fields"].append({
                    "selector": selector,
                    "value": value,
                    "field_name": field.get("name", "")
                })

            except Exception as e:
                logger.error(f"Failed to fill field {selector}: {e}")
                results["failed_fields"].append({
                    "selector": selector,
                    "error": str(e)
                })
                results["success"] = False

        return results
