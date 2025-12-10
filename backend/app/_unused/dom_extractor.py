"""
DOM Extractor Module for ghostQA

Provides intelligent DOM analysis, element extraction, and selector suggestion
for autonomous test execution.
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import re


@dataclass
class ExtractedElement:
    """Represents an extracted DOM element with its properties"""
    tag: str
    text: str = ""
    id: Optional[str] = None
    classes: List[str] = field(default_factory=list)
    name: Optional[str] = None
    type: Optional[str] = None
    placeholder: Optional[str] = None
    value: Optional[str] = None
    href: Optional[str] = None
    role: Optional[str] = None
    aria_label: Optional[str] = None
    data_testid: Optional[str] = None
    xpath: str = ""
    css_selector: str = ""
    is_visible: bool = True
    is_interactive: bool = False
    suggested_selectors: List[Dict[str, str]] = field(default_factory=list)


class DOMExtractor:
    """
    Extracts and analyzes DOM elements from HTML content.
    Provides intelligent selector suggestions for test automation.
    """

    # Interactive element tags
    INTERACTIVE_TAGS = {
        'a', 'button', 'input', 'select', 'textarea', 'label',
        'option', 'details', 'summary', 'dialog'
    }

    # Input types that are interactive
    INTERACTIVE_INPUT_TYPES = {
        'text', 'password', 'email', 'number', 'tel', 'url',
        'search', 'date', 'time', 'datetime-local', 'month',
        'week', 'color', 'file', 'checkbox', 'radio', 'submit',
        'button', 'reset', 'range'
    }

    def __init__(self, html_content: str = ""):
        """Initialize with optional HTML content"""
        self.html_content = html_content
        self.soup = None
        if html_content:
            self.parse(html_content)

    def parse(self, html_content: str) -> None:
        """Parse HTML content"""
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'lxml')

    def extract_all_elements(self) -> List[ExtractedElement]:
        """Extract all elements from the DOM"""
        if not self.soup:
            return []

        elements = []
        for tag in self.soup.find_all(True):
            element = self._extract_element(tag)
            if element:
                elements.append(element)

        return elements

    def extract_interactive_elements(self) -> List[ExtractedElement]:
        """Extract only interactive elements (buttons, inputs, links, etc.)"""
        if not self.soup:
            return []

        elements = []

        # Find all interactive elements
        for tag in self.soup.find_all(True):
            if self._is_interactive(tag):
                element = self._extract_element(tag)
                if element:
                    element.is_interactive = True
                    elements.append(element)

        return elements

    def extract_forms(self) -> List[Dict[str, Any]]:
        """Extract form elements with their fields"""
        if not self.soup:
            return []

        forms = []
        for form in self.soup.find_all('form'):
            form_data = {
                'id': form.get('id'),
                'name': form.get('name'),
                'action': form.get('action'),
                'method': form.get('method', 'get'),
                'fields': []
            }

            # Extract form fields
            for field in form.find_all(['input', 'select', 'textarea']):
                field_data = self._extract_element(field)
                if field_data:
                    form_data['fields'].append(field_data)

            forms.append(form_data)

        return forms

    def find_element_by_text(self, text: str, exact: bool = False) -> List[ExtractedElement]:
        """Find elements containing specific text"""
        if not self.soup:
            return []

        elements = []
        text_lower = text.lower()

        for tag in self.soup.find_all(True):
            tag_text = tag.get_text(strip=True).lower()

            if exact:
                if tag_text == text_lower:
                    element = self._extract_element(tag)
                    if element:
                        elements.append(element)
            else:
                if text_lower in tag_text:
                    element = self._extract_element(tag)
                    if element:
                        elements.append(element)

        return elements

    def find_element_by_selector(self, selector: str, selector_type: str = 'css') -> Optional[ExtractedElement]:
        """Find element by CSS selector or XPath"""
        if not self.soup:
            return None

        try:
            if selector_type == 'css':
                tag = self.soup.select_one(selector)
            elif selector_type == 'id':
                tag = self.soup.find(id=selector)
            elif selector_type == 'class':
                tag = self.soup.find(class_=selector)
            elif selector_type == 'name':
                tag = self.soup.find(attrs={'name': selector})
            elif selector_type == 'placeholder':
                tag = self.soup.find(attrs={'placeholder': selector})
            elif selector_type == 'text':
                # Find by text content
                for t in self.soup.find_all(True):
                    if selector.lower() in t.get_text(strip=True).lower():
                        tag = t
                        break
                else:
                    tag = None
            else:
                tag = None

            if tag:
                return self._extract_element(tag)

        except Exception:
            pass

        return None

    def suggest_selectors(self, element: ExtractedElement) -> List[Dict[str, str]]:
        """Generate selector suggestions for an element, ranked by reliability"""
        suggestions = []

        # Priority 1: data-testid (most reliable for testing)
        if element.data_testid:
            suggestions.append({
                'type': 'css',
                'selector': f'[data-testid="{element.data_testid}"]',
                'confidence': 'high',
                'description': 'Test ID selector (most reliable)'
            })

        # Priority 2: ID (usually unique)
        if element.id:
            suggestions.append({
                'type': 'id',
                'selector': element.id,
                'confidence': 'high',
                'description': 'ID selector'
            })
            suggestions.append({
                'type': 'css',
                'selector': f'#{element.id}',
                'confidence': 'high',
                'description': 'CSS ID selector'
            })

        # Priority 3: Name attribute (for forms)
        if element.name:
            suggestions.append({
                'type': 'css',
                'selector': f'[name="{element.name}"]',
                'confidence': 'high',
                'description': 'Name attribute selector'
            })

        # Priority 4: Placeholder (for inputs)
        if element.placeholder:
            suggestions.append({
                'type': 'placeholder',
                'selector': element.placeholder,
                'confidence': 'medium',
                'description': 'Placeholder text selector'
            })
            suggestions.append({
                'type': 'css',
                'selector': f'[placeholder="{element.placeholder}"]',
                'confidence': 'medium',
                'description': 'CSS placeholder selector'
            })

        # Priority 5: aria-label (accessibility)
        if element.aria_label:
            suggestions.append({
                'type': 'css',
                'selector': f'[aria-label="{element.aria_label}"]',
                'confidence': 'medium',
                'description': 'ARIA label selector'
            })

        # Priority 6: Role attribute
        if element.role:
            suggestions.append({
                'type': 'css',
                'selector': f'[role="{element.role}"]',
                'confidence': 'low',
                'description': 'Role attribute selector'
            })

        # Priority 7: Class-based selectors (less reliable)
        if element.classes:
            # Use the most specific class
            for cls in element.classes:
                if not cls.startswith(('css-', 'sc-', 'styles__')):  # Skip generated classes
                    suggestions.append({
                        'type': 'class',
                        'selector': cls,
                        'confidence': 'low',
                        'description': f'Class selector: {cls}'
                    })
                    break

        # Priority 8: Text content (for buttons/links)
        if element.text and element.tag in ('a', 'button', 'span'):
            clean_text = element.text.strip()[:50]  # Limit length
            suggestions.append({
                'type': 'text',
                'selector': clean_text,
                'confidence': 'medium',
                'description': f'Text content: "{clean_text}"'
            })

        return suggestions

    def get_page_structure(self) -> Dict[str, Any]:
        """Get a summary of the page structure"""
        if not self.soup:
            return {}

        structure = {
            'title': '',
            'forms_count': 0,
            'links_count': 0,
            'buttons_count': 0,
            'inputs_count': 0,
            'images_count': 0,
            'headings': [],
            'navigation': [],
            'main_content_areas': []
        }

        # Title
        title_tag = self.soup.find('title')
        if title_tag:
            structure['title'] = title_tag.get_text(strip=True)

        # Counts
        structure['forms_count'] = len(self.soup.find_all('form'))
        structure['links_count'] = len(self.soup.find_all('a'))
        structure['buttons_count'] = len(self.soup.find_all('button'))
        structure['inputs_count'] = len(self.soup.find_all('input'))
        structure['images_count'] = len(self.soup.find_all('img'))

        # Headings
        for level in range(1, 7):
            for heading in self.soup.find_all(f'h{level}'):
                structure['headings'].append({
                    'level': level,
                    'text': heading.get_text(strip=True)[:100]
                })

        # Navigation elements
        for nav in self.soup.find_all(['nav', '[role="navigation"]']):
            links = [a.get_text(strip=True) for a in nav.find_all('a')][:10]
            structure['navigation'].append({'links': links})

        # Main content areas
        for main in self.soup.find_all(['main', '[role="main"]', 'article']):
            structure['main_content_areas'].append({
                'tag': main.name,
                'id': main.get('id'),
                'class': main.get('class')
            })

        return structure

    def _extract_element(self, tag) -> Optional[ExtractedElement]:
        """Extract element data from a BeautifulSoup tag"""
        try:
            element = ExtractedElement(
                tag=tag.name,
                text=tag.get_text(strip=True)[:200] if tag.string or tag.get_text() else "",
                id=tag.get('id'),
                classes=tag.get('class', []),
                name=tag.get('name'),
                type=tag.get('type'),
                placeholder=tag.get('placeholder'),
                value=tag.get('value'),
                href=tag.get('href'),
                role=tag.get('role'),
                aria_label=tag.get('aria-label'),
                data_testid=tag.get('data-testid') or tag.get('data-test-id'),
            )

            # Generate CSS selector
            element.css_selector = self._generate_css_selector(tag)

            # Generate XPath
            element.xpath = self._generate_xpath(tag)

            # Generate selector suggestions
            element.suggested_selectors = self.suggest_selectors(element)

            return element

        except Exception:
            return None

    def _is_interactive(self, tag) -> bool:
        """Check if an element is interactive"""
        # Check tag name
        if tag.name in self.INTERACTIVE_TAGS:
            # For inputs, check the type
            if tag.name == 'input':
                input_type = tag.get('type', 'text')
                return input_type in self.INTERACTIVE_INPUT_TYPES
            return True

        # Check role attribute
        interactive_roles = {'button', 'link', 'checkbox', 'radio', 'textbox',
                           'combobox', 'listbox', 'menu', 'menuitem', 'tab'}
        if tag.get('role') in interactive_roles:
            return True

        # Check for onclick or other event handlers
        for attr in tag.attrs:
            if attr.startswith('on'):
                return True

        # Check for tabindex
        if tag.get('tabindex') is not None:
            return True

        return False

    def _generate_css_selector(self, tag) -> str:
        """Generate a CSS selector for an element"""
        parts = []

        # Start with tag name
        selector = tag.name

        # Add ID if present
        if tag.get('id'):
            return f"#{tag.get('id')}"

        # Add classes (excluding generated ones)
        classes = tag.get('class', [])
        for cls in classes[:2]:  # Limit to 2 classes
            if not cls.startswith(('css-', 'sc-', 'styles__', 'jsx-')):
                selector += f".{cls}"

        # Add type for inputs
        if tag.name == 'input' and tag.get('type'):
            selector += f'[type="{tag.get("type")}"]'

        # Add name if present
        if tag.get('name'):
            selector += f'[name="{tag.get("name")}"]'

        return selector

    def _generate_xpath(self, tag) -> str:
        """Generate an XPath for an element"""
        # If element has ID, use that
        if tag.get('id'):
            return f'//*[@id="{tag.get("id")}"]'

        # Build path from root
        path_parts = []
        current = tag

        while current.parent and current.parent.name:
            siblings = [s for s in current.parent.children
                       if hasattr(s, 'name') and s.name == current.name]

            if len(siblings) > 1:
                index = siblings.index(current) + 1
                path_parts.insert(0, f"{current.name}[{index}]")
            else:
                path_parts.insert(0, current.name)

            current = current.parent

        return '//' + '/'.join(path_parts) if path_parts else f'//{tag.name}'


def extract_dom_info(html_content: str) -> Dict[str, Any]:
    """
    Convenience function to extract DOM information from HTML.
    Returns a dictionary with page structure and interactive elements.
    """
    extractor = DOMExtractor(html_content)

    return {
        'structure': extractor.get_page_structure(),
        'interactive_elements': [
            {
                'tag': el.tag,
                'text': el.text,
                'id': el.id,
                'classes': el.classes,
                'name': el.name,
                'type': el.type,
                'placeholder': el.placeholder,
                'selectors': el.suggested_selectors
            }
            for el in extractor.extract_interactive_elements()
        ],
        'forms': extractor.extract_forms()
    }
