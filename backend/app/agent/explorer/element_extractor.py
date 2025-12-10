"""
Element Extractor

Extracts interactive elements from a page and generates
multiple selector strategies for each element.
"""

import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ElementType(Enum):
    """Types of interactive elements"""
    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    FILE_INPUT = "file_input"
    FORM = "form"
    TABLE = "table"
    LIST = "list"
    MENU = "menu"
    TAB = "tab"
    MODAL = "modal"
    ACCORDION = "accordion"
    SLIDER = "slider"
    DATE_PICKER = "date_picker"
    AUTOCOMPLETE = "autocomplete"
    TOGGLE = "toggle"
    TOOLTIP = "tooltip"
    DROPDOWN = "dropdown"
    NAVIGATION = "navigation"
    UNKNOWN = "unknown"


@dataclass
class ExtractedElement:
    """Represents an extracted interactive element"""
    element_type: ElementType
    element_key: str  # Semantic identifier
    selectors: List[Dict[str, Any]]  # Multiple selector strategies
    attributes: Dict[str, Any]  # Original attributes
    text_content: str = ""
    is_visible: bool = True
    is_enabled: bool = True
    bounding_box: Optional[Dict[str, float]] = None
    parent_context: str = ""  # Parent element context (form name, section, etc.)
    confidence: float = 1.0


class ElementExtractor:
    """
    Extracts interactive elements from DOM and generates selectors.

    Features:
    - Multiple selector strategies per element
    - Semantic element key generation
    - Framework-aware extraction
    - Accessibility-first approach
    """

    # Tags that are typically interactive
    INTERACTIVE_TAGS = {
        "button", "a", "input", "select", "textarea", "option",
        "label", "summary", "details"
    }

    # Roles that indicate interactivity
    INTERACTIVE_ROLES = {
        "button", "link", "textbox", "checkbox", "radio", "combobox",
        "listbox", "option", "menuitem", "tab", "switch", "slider",
        "spinbutton", "searchbox", "menu", "menubar", "tablist"
    }

    # Attributes that make elements clickable
    CLICKABLE_ATTRIBUTES = {
        "onclick", "ng-click", "@click", "v-on:click",
        "(click)", "data-action", "data-toggle"
    }

    def __init__(self, framework_selectors: Optional[Dict] = None):
        """
        Initialize extractor.

        Args:
            framework_selectors: Framework-specific selector patterns
        """
        self.framework_selectors = framework_selectors or {}
        self._detected_framework: Optional[str] = None

    def extract_from_dom(
        self,
        dom_elements: List[Dict[str, Any]],
        page_url: str = "",
        detected_framework: Optional[str] = None
    ) -> List[ExtractedElement]:
        """
        Extract interactive elements from DOM.

        Args:
            dom_elements: List of DOM element data (from Playwright locator.evaluate)
            page_url: Current page URL for context
            detected_framework: Detected UI framework if known

        Returns:
            List of extracted elements with selectors
        """
        self._detected_framework = detected_framework
        extracted = []

        for elem_data in dom_elements:
            if self._is_interactive(elem_data):
                element = self._extract_element(elem_data, page_url)
                if element:
                    extracted.append(element)

        # De-duplicate and merge similar elements
        extracted = self._deduplicate_elements(extracted)

        return extracted

    def _is_interactive(self, elem_data: Dict[str, Any]) -> bool:
        """Check if element is interactive"""
        tag = elem_data.get("tagName", "").lower()
        role = elem_data.get("role", "").lower()
        attrs = elem_data.get("attributes", {})

        # Check tag
        if tag in self.INTERACTIVE_TAGS:
            return True

        # Check role
        if role in self.INTERACTIVE_ROLES:
            return True

        # Check for click handlers
        for attr in self.CLICKABLE_ATTRIBUTES:
            if attr in attrs:
                return True

        # Check tabindex
        tabindex = attrs.get("tabindex")
        if tabindex is not None and tabindex != "-1":
            return True

        # Check contenteditable
        if attrs.get("contenteditable") == "true":
            return True

        return False

    def _extract_element(
        self,
        elem_data: Dict[str, Any],
        page_url: str
    ) -> Optional[ExtractedElement]:
        """Extract a single element"""
        tag = elem_data.get("tagName", "").lower()
        attrs = elem_data.get("attributes", {})
        text = elem_data.get("textContent", "").strip()

        # Determine element type
        element_type = self._determine_type(elem_data)

        # Generate semantic key
        element_key = self._generate_element_key(elem_data, element_type)

        if not element_key:
            return None

        # Generate multiple selectors
        selectors = self._generate_selectors(elem_data, element_key)

        if not selectors:
            return None

        # Extract bounding box
        bbox = elem_data.get("boundingBox")

        return ExtractedElement(
            element_type=element_type,
            element_key=element_key,
            selectors=selectors,
            attributes=attrs,
            text_content=text[:200],  # Limit text content
            is_visible=elem_data.get("isVisible", True),
            is_enabled=not attrs.get("disabled"),
            bounding_box=bbox,
            parent_context=self._get_parent_context(elem_data),
            confidence=self._calculate_confidence(selectors)
        )

    def _determine_type(self, elem_data: Dict[str, Any]) -> ElementType:
        """Determine the element type"""
        tag = elem_data.get("tagName", "").lower()
        attrs = elem_data.get("attributes", {})
        role = attrs.get("role", "").lower()
        input_type = attrs.get("type", "").lower()
        classes = attrs.get("class", "")

        # Check by tag
        if tag == "button" or (tag == "input" and input_type == "submit"):
            return ElementType.BUTTON
        elif tag == "a":
            return ElementType.LINK
        elif tag == "input":
            if input_type in ("text", "email", "password", "tel", "url", "search"):
                return ElementType.INPUT
            elif input_type == "checkbox":
                return ElementType.CHECKBOX
            elif input_type == "radio":
                return ElementType.RADIO
            elif input_type == "file":
                return ElementType.FILE_INPUT
            else:
                return ElementType.INPUT
        elif tag == "select":
            return ElementType.SELECT
        elif tag == "textarea":
            return ElementType.TEXTAREA
        elif tag == "form":
            return ElementType.FORM
        elif tag == "table":
            return ElementType.TABLE
        elif tag in ("ul", "ol"):
            return ElementType.LIST
        elif tag == "nav":
            return ElementType.NAVIGATION

        # Check by role
        role_mapping = {
            "button": ElementType.BUTTON,
            "link": ElementType.LINK,
            "textbox": ElementType.INPUT,
            "checkbox": ElementType.CHECKBOX,
            "radio": ElementType.RADIO,
            "combobox": ElementType.SELECT,
            "listbox": ElementType.SELECT,
            "menu": ElementType.MENU,
            "menubar": ElementType.MENU,
            "tab": ElementType.TAB,
            "tablist": ElementType.TAB,
            "switch": ElementType.TOGGLE,
            "slider": ElementType.SLIDER,
            "dialog": ElementType.MODAL
        }

        if role in role_mapping:
            return role_mapping[role]

        # Check by class patterns
        class_patterns = {
            r'date[-_]?picker|calendar': ElementType.DATE_PICKER,
            r'autocomplete|typeahead': ElementType.AUTOCOMPLETE,
            r'toggle|switch': ElementType.TOGGLE,
            r'dropdown': ElementType.DROPDOWN,
            r'modal|dialog': ElementType.MODAL,
            r'accordion': ElementType.ACCORDION,
            r'tab': ElementType.TAB,
            r'menu': ElementType.MENU,
            r'nav': ElementType.NAVIGATION
        }

        for pattern, elem_type in class_patterns.items():
            if re.search(pattern, classes, re.I):
                return elem_type

        return ElementType.UNKNOWN

    def _generate_element_key(
        self,
        elem_data: Dict[str, Any],
        element_type: ElementType
    ) -> str:
        """
        Generate a semantic key for the element.

        Priority:
        1. aria-label
        2. name attribute
        3. id (cleaned)
        4. label association
        5. text content
        6. placeholder
        7. Generated from type + position
        """
        attrs = elem_data.get("attributes", {})
        text = elem_data.get("textContent", "").strip()

        # Try aria-label first (most semantic)
        aria_label = attrs.get("aria-label")
        if aria_label:
            return self._normalize_key(aria_label)

        # Try name attribute
        name = attrs.get("name")
        if name:
            return self._normalize_key(name)

        # Try id (clean it up)
        elem_id = attrs.get("id")
        if elem_id:
            cleaned = self._clean_id(elem_id)
            if cleaned:
                return cleaned

        # Try label association
        label_text = elem_data.get("labelText")
        if label_text:
            return self._normalize_key(label_text)

        # Try text content (for buttons/links)
        if text and element_type in (ElementType.BUTTON, ElementType.LINK, ElementType.TAB):
            return self._normalize_key(text[:50])

        # Try placeholder
        placeholder = attrs.get("placeholder")
        if placeholder:
            return self._normalize_key(placeholder)

        # Try title
        title = attrs.get("title")
        if title:
            return self._normalize_key(title)

        # Generate from type and other attributes
        type_name = element_type.value
        if attrs.get("type"):
            type_name = f"{type_name}_{attrs.get('type')}"

        return f"{type_name}_element"

    def _normalize_key(self, key: str) -> str:
        """Normalize a key to consistent format"""
        # Convert to lowercase
        key = key.lower()

        # Replace spaces and special chars with underscores
        key = re.sub(r'[^a-z0-9]+', '_', key)

        # Remove leading/trailing underscores
        key = key.strip('_')

        # Limit length
        if len(key) > 50:
            key = key[:50]

        return key

    def _clean_id(self, elem_id: str) -> str:
        """Clean up an element ID to be more semantic"""
        # Skip IDs that look auto-generated
        if re.match(r'^[a-z]*[0-9]+$', elem_id):  # e.g., "input123"
            return ""
        if re.match(r'^[a-f0-9]{8,}', elem_id):  # UUID-like
            return ""
        if re.match(r'^:r[0-9]+:', elem_id):  # React generated
            return ""

        return self._normalize_key(elem_id)

    def _generate_selectors(
        self,
        elem_data: Dict[str, Any],
        element_key: str
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple selector strategies for an element.

        Returns list of selectors ordered by reliability.
        """
        selectors = []
        tag = elem_data.get("tagName", "").lower()
        attrs = elem_data.get("attributes", {})
        text = elem_data.get("textContent", "").strip()

        # 1. Test ID selector (most reliable if available)
        test_id = attrs.get("data-testid") or attrs.get("data-test-id") or attrs.get("data-cy")
        if test_id:
            selectors.append({
                "selector": f'[data-testid="{test_id}"]',
                "type": "css",
                "strategy": "test_id",
                "confidence": 0.95
            })

        # 2. Role + Name (accessibility-first)
        role = attrs.get("role")
        aria_label = attrs.get("aria-label")
        if role and aria_label:
            selectors.append({
                "selector": f'[role="{role}"][aria-label="{aria_label}"]',
                "type": "css",
                "strategy": "role_name",
                "confidence": 0.9
            })

        # 3. ID selector (if clean ID exists)
        elem_id = attrs.get("id")
        if elem_id and self._clean_id(elem_id):
            selectors.append({
                "selector": f'#{elem_id}',
                "type": "css",
                "strategy": "id",
                "confidence": 0.85
            })

        # 4. Name attribute
        name = attrs.get("name")
        if name:
            selectors.append({
                "selector": f'[name="{name}"]',
                "type": "css",
                "strategy": "name",
                "confidence": 0.8
            })

        # 5. Label association (for form inputs)
        label_text = elem_data.get("labelText")
        if label_text and tag in ("input", "select", "textarea"):
            selectors.append({
                "selector": f'label:has-text("{label_text}") + input, label:has-text("{label_text}") input',
                "type": "css",
                "strategy": "label",
                "confidence": 0.75
            })
            # Also add getByLabel style
            selectors.append({
                "selector": label_text,
                "type": "label",
                "strategy": "playwright_label",
                "confidence": 0.85
            })

        # 6. Text content (for buttons/links)
        if text and len(text) < 100:
            if tag == "button" or (tag == "input" and attrs.get("type") == "submit"):
                selectors.append({
                    "selector": text,
                    "type": "text",
                    "strategy": "button_text",
                    "confidence": 0.8
                })
                selectors.append({
                    "selector": f'button:has-text("{text}")',
                    "type": "css",
                    "strategy": "button_text_css",
                    "confidence": 0.75
                })
            elif tag == "a":
                selectors.append({
                    "selector": text,
                    "type": "text",
                    "strategy": "link_text",
                    "confidence": 0.8
                })
                selectors.append({
                    "selector": f'a:has-text("{text}")',
                    "type": "css",
                    "strategy": "link_text_css",
                    "confidence": 0.75
                })

        # 7. Placeholder (for inputs)
        placeholder = attrs.get("placeholder")
        if placeholder:
            selectors.append({
                "selector": f'[placeholder="{placeholder}"]',
                "type": "css",
                "strategy": "placeholder",
                "confidence": 0.7
            })
            selectors.append({
                "selector": placeholder,
                "type": "placeholder",
                "strategy": "playwright_placeholder",
                "confidence": 0.8
            })

        # 8. Type-specific selectors
        input_type = attrs.get("type", "").lower()
        if tag == "input" and input_type:
            if input_type == "email":
                selectors.append({
                    "selector": 'input[type="email"]',
                    "type": "css",
                    "strategy": "input_type",
                    "confidence": 0.6
                })
            elif input_type == "password":
                selectors.append({
                    "selector": 'input[type="password"]',
                    "type": "css",
                    "strategy": "input_type",
                    "confidence": 0.6
                })

        # 9. Framework-specific selectors
        if self._detected_framework and self._detected_framework in self.framework_selectors:
            framework_sels = self._get_framework_selectors(elem_data)
            selectors.extend(framework_sels)

        # 10. XPath fallback (most specific but fragile)
        xpath = elem_data.get("xpath")
        if xpath:
            selectors.append({
                "selector": xpath,
                "type": "xpath",
                "strategy": "xpath",
                "confidence": 0.5
            })

        return selectors

    def _get_framework_selectors(self, elem_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get framework-specific selectors"""
        selectors = []
        framework = self._detected_framework
        attrs = elem_data.get("attributes", {})
        classes = attrs.get("class", "")

        if framework not in self.framework_selectors:
            return selectors

        framework_config = self.framework_selectors[framework]

        # Match against framework patterns
        for component_name, component_selectors in framework_config.items():
            for sel in component_selectors:
                # Check if element matches this pattern
                if self._matches_pattern(elem_data, sel):
                    selectors.append({
                        "selector": sel,
                        "type": "css",
                        "strategy": f"framework_{framework}",
                        "confidence": 0.7
                    })

        return selectors

    def _matches_pattern(self, elem_data: Dict[str, Any], pattern: str) -> bool:
        """Check if element matches a selector pattern"""
        classes = elem_data.get("attributes", {}).get("class", "")
        tag = elem_data.get("tagName", "").lower()

        # Simple class matching
        if "." in pattern:
            class_match = pattern.split(".")[-1].split("[")[0]
            if class_match in classes:
                return True

        return False

    def _get_parent_context(self, elem_data: Dict[str, Any]) -> str:
        """Get context from parent elements (form name, section, etc.)"""
        parent = elem_data.get("parentContext", {})

        # Check for form context
        form_name = parent.get("formName") or parent.get("formId")
        if form_name:
            return f"form:{form_name}"

        # Check for section context
        section = parent.get("sectionName") or parent.get("heading")
        if section:
            return f"section:{section}"

        return ""

    def _calculate_confidence(self, selectors: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence for an element based on its selectors"""
        if not selectors:
            return 0.0

        # Return highest selector confidence
        return max(s.get("confidence", 0.5) for s in selectors)

    def _deduplicate_elements(
        self,
        elements: List[ExtractedElement]
    ) -> List[ExtractedElement]:
        """Remove duplicate elements, keeping best selectors"""
        seen: Dict[str, ExtractedElement] = {}

        for elem in elements:
            key = elem.element_key

            if key in seen:
                # Merge selectors
                existing = seen[key]
                existing_sels = {s["selector"] for s in existing.selectors}

                for sel in elem.selectors:
                    if sel["selector"] not in existing_sels:
                        existing.selectors.append(sel)
                        existing_sels.add(sel["selector"])

                # Update confidence
                existing.confidence = max(existing.confidence, elem.confidence)
            else:
                seen[key] = elem

        return list(seen.values())

    def extract_from_html(self, html: str, page_url: str = "") -> List[ExtractedElement]:
        """
        Extract elements from raw HTML string.
        This is a lightweight extraction when full DOM is not available.

        Args:
            html: Raw HTML string
            page_url: Page URL for context

        Returns:
            List of extracted elements
        """
        elements = []

        # Extract forms
        form_pattern = r'<form[^>]*>(.*?)</form>'
        for match in re.finditer(form_pattern, html, re.DOTALL | re.I):
            form_html = match.group(0)
            form_attrs = self._extract_attrs(form_html)

            elements.append(ExtractedElement(
                element_type=ElementType.FORM,
                element_key=form_attrs.get("name") or form_attrs.get("id") or "form",
                selectors=self._selectors_from_attrs(form_attrs, "form"),
                attributes=form_attrs
            ))

        # Extract inputs
        input_pattern = r'<input[^>]*>'
        for match in re.finditer(input_pattern, html, re.I):
            input_html = match.group(0)
            attrs = self._extract_attrs(input_html)
            input_type = attrs.get("type", "text")

            elem_type = ElementType.INPUT
            if input_type == "checkbox":
                elem_type = ElementType.CHECKBOX
            elif input_type == "radio":
                elem_type = ElementType.RADIO
            elif input_type in ("submit", "button"):
                elem_type = ElementType.BUTTON

            key = attrs.get("name") or attrs.get("id") or attrs.get("placeholder") or f"input_{input_type}"

            elements.append(ExtractedElement(
                element_type=elem_type,
                element_key=self._normalize_key(key),
                selectors=self._selectors_from_attrs(attrs, "input"),
                attributes=attrs
            ))

        # Extract buttons
        button_pattern = r'<button[^>]*>(.*?)</button>'
        for match in re.finditer(button_pattern, html, re.DOTALL | re.I):
            button_html = match.group(0)
            text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            attrs = self._extract_attrs(button_html)

            key = attrs.get("name") or text or "button"

            elements.append(ExtractedElement(
                element_type=ElementType.BUTTON,
                element_key=self._normalize_key(key),
                selectors=self._selectors_from_attrs(attrs, "button"),
                attributes=attrs,
                text_content=text
            ))

        # Extract links
        link_pattern = r'<a[^>]*>(.*?)</a>'
        for match in re.finditer(link_pattern, html, re.DOTALL | re.I):
            link_html = match.group(0)
            text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            attrs = self._extract_attrs(link_html)

            if not text and not attrs.get("aria-label"):
                continue  # Skip empty links

            key = text or attrs.get("aria-label") or "link"

            elements.append(ExtractedElement(
                element_type=ElementType.LINK,
                element_key=self._normalize_key(key[:50]),
                selectors=self._selectors_from_attrs(attrs, "a"),
                attributes=attrs,
                text_content=text
            ))

        # Extract selects
        select_pattern = r'<select[^>]*>'
        for match in re.finditer(select_pattern, html, re.I):
            select_html = match.group(0)
            attrs = self._extract_attrs(select_html)

            key = attrs.get("name") or attrs.get("id") or "select"

            elements.append(ExtractedElement(
                element_type=ElementType.SELECT,
                element_key=self._normalize_key(key),
                selectors=self._selectors_from_attrs(attrs, "select"),
                attributes=attrs
            ))

        return self._deduplicate_elements(elements)

    def _extract_attrs(self, html_tag: str) -> Dict[str, str]:
        """Extract attributes from an HTML tag string"""
        attrs = {}

        # Match attribute patterns
        attr_pattern = r'(\w+(?:-\w+)*)=["\']([^"\']*)["\']'
        for match in re.finditer(attr_pattern, html_tag):
            attrs[match.group(1)] = match.group(2)

        # Match boolean attributes
        bool_pattern = r'\s(\w+)(?=\s|>|/)'
        for match in re.finditer(bool_pattern, html_tag):
            attr = match.group(1)
            if attr not in attrs:
                attrs[attr] = "true"

        return attrs

    def _selectors_from_attrs(self, attrs: Dict[str, str], tag: str) -> List[Dict[str, Any]]:
        """Generate selectors from attributes"""
        selectors = []

        # ID
        if attrs.get("id"):
            selectors.append({
                "selector": f'#{attrs["id"]}',
                "type": "css",
                "strategy": "id",
                "confidence": 0.85
            })

        # Name
        if attrs.get("name"):
            selectors.append({
                "selector": f'{tag}[name="{attrs["name"]}"]',
                "type": "css",
                "strategy": "name",
                "confidence": 0.8
            })

        # data-testid
        if attrs.get("data-testid"):
            selectors.append({
                "selector": f'[data-testid="{attrs["data-testid"]}"]',
                "type": "css",
                "strategy": "test_id",
                "confidence": 0.95
            })

        return selectors
