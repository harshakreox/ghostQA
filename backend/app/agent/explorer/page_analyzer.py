"""
Page Analyzer

Analyzes web pages to detect frameworks, identify page types,
and understand page structure for intelligent test generation.
"""

import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urljoin


class PageType(Enum):
    """Types of pages commonly found in web apps"""
    LOGIN = "login"
    REGISTRATION = "registration"
    DASHBOARD = "dashboard"
    LISTING = "listing"
    DETAIL = "detail"
    FORM = "form"
    SEARCH = "search"
    SETTINGS = "settings"
    PROFILE = "profile"
    CHECKOUT = "checkout"
    CART = "cart"
    ERROR = "error"
    NOT_FOUND = "not_found"
    HOME = "home"
    LANDING = "landing"
    ARTICLE = "article"
    CONTACT = "contact"
    ABOUT = "about"
    UNKNOWN = "unknown"


class FrameworkType(Enum):
    """Detectable UI frameworks"""
    REACT = "react"
    ANGULAR = "angular"
    VUE = "vue"
    SVELTE = "svelte"
    MUI = "mui"
    ANT_DESIGN = "ant_design"
    BOOTSTRAP = "bootstrap"
    TAILWIND = "tailwind"
    CHAKRA = "chakra"
    SEMANTIC_UI = "semantic_ui"
    BULMA = "bulma"
    FOUNDATION = "foundation"
    UNKNOWN = "unknown"


@dataclass
class PageLink:
    """Represents a link on the page"""
    url: str
    text: str
    is_internal: bool
    link_type: str  # navigation, action, external, anchor


@dataclass
class PageForm:
    """Represents a form on the page"""
    form_id: Optional[str]
    form_name: Optional[str]
    action: str
    method: str
    fields: List[Dict[str, Any]]
    submit_button: Optional[Dict[str, Any]]


@dataclass
class PageAnalysis:
    """Complete analysis of a page"""
    url: str
    title: str
    page_type: PageType
    detected_frameworks: List[FrameworkType]
    primary_framework: Optional[FrameworkType]
    forms: List[PageForm]
    links: List[PageLink]
    interactive_elements_count: int
    has_authentication: bool
    has_navigation: bool
    has_search: bool
    has_pagination: bool
    has_modals: bool
    has_tables: bool
    content_hash: str
    meta_info: Dict[str, Any]


class PageAnalyzer:
    """
    Analyzes web pages for structure, frameworks, and patterns.

    Features:
    - Framework detection (React, Angular, Vue, MUI, etc.)
    - Page type classification
    - Form identification
    - Link extraction and classification
    - Change detection via content hashing
    """

    # Framework detection patterns
    FRAMEWORK_SIGNATURES = {
        FrameworkType.REACT: {
            "scripts": [r"react\.production\.min\.js", r"react-dom", r"\_\_REACT"],
            "attributes": ["data-reactroot", "data-reactid"],
            "classes": [],
            "comments": ["react-app"]
        },
        FrameworkType.ANGULAR: {
            "scripts": [r"angular\.min\.js", r"@angular/core", r"ng-version"],
            "attributes": ["ng-app", "ng-controller", "_ngcontent", "_nghost"],
            "classes": ["ng-", "mat-"],
            "comments": []
        },
        FrameworkType.VUE: {
            "scripts": [r"vue\.min\.js", r"vue\.runtime", r"vue\.global"],
            "attributes": ["data-v-", "v-cloak"],
            "classes": [],
            "comments": []
        },
        FrameworkType.SVELTE: {
            "scripts": [r"svelte"],
            "attributes": [],
            "classes": ["svelte-"],
            "comments": []
        },
        FrameworkType.MUI: {
            "scripts": [r"@mui/material", r"material-ui"],
            "attributes": [],
            "classes": ["MuiButton", "MuiTextField", "MuiPaper", "Mui"],
            "comments": []
        },
        FrameworkType.ANT_DESIGN: {
            "scripts": [r"antd"],
            "attributes": [],
            "classes": ["ant-btn", "ant-input", "ant-form", "ant-"],
            "comments": []
        },
        FrameworkType.BOOTSTRAP: {
            "scripts": [r"bootstrap\.min\.js", r"bootstrap\.bundle"],
            "attributes": ["data-bs-", "data-toggle"],
            "classes": ["btn-primary", "btn-secondary", "form-control", "container-fluid", "navbar"],
            "comments": []
        },
        FrameworkType.TAILWIND: {
            "scripts": [r"tailwindcss", r"tailwind\.config"],
            "attributes": [],
            "classes": ["flex", "grid", "bg-", "text-", "p-", "m-", "w-", "h-"],
            "comments": []
        },
        FrameworkType.CHAKRA: {
            "scripts": [r"@chakra-ui"],
            "attributes": [],
            "classes": ["chakra-"],
            "comments": []
        },
        FrameworkType.SEMANTIC_UI: {
            "scripts": [r"semantic\.min\.js", r"semantic-ui"],
            "attributes": [],
            "classes": ["ui button", "ui form", "ui input", "ui container"],
            "comments": []
        },
        FrameworkType.BULMA: {
            "scripts": [],
            "attributes": [],
            "classes": ["is-primary", "is-info", "is-success", "column", "columns"],
            "comments": []
        }
    }

    # Page type detection patterns
    PAGE_TYPE_PATTERNS = {
        PageType.LOGIN: {
            "url_patterns": [r"/login", r"/signin", r"/sign-in", r"/auth"],
            "title_patterns": [r"login", r"sign.?in", r"log.?in"],
            "content_patterns": [r"password", r"username", r"email.*password", r"forgot.*password"]
        },
        PageType.REGISTRATION: {
            "url_patterns": [r"/register", r"/signup", r"/sign-up", r"/create.*account"],
            "title_patterns": [r"register", r"sign.?up", r"create.*account"],
            "content_patterns": [r"confirm.*password", r"create.*account", r"already.*member"]
        },
        PageType.DASHBOARD: {
            "url_patterns": [r"/dashboard", r"/home", r"/overview", r"/admin"],
            "title_patterns": [r"dashboard", r"overview", r"home"],
            "content_patterns": [r"welcome", r"overview", r"statistics", r"analytics"]
        },
        PageType.SETTINGS: {
            "url_patterns": [r"/settings", r"/preferences", r"/account"],
            "title_patterns": [r"settings", r"preferences", r"account"],
            "content_patterns": [r"save.*changes", r"update.*profile", r"notification"]
        },
        PageType.PROFILE: {
            "url_patterns": [r"/profile", r"/user", r"/me"],
            "title_patterns": [r"profile", r"my.*account"],
            "content_patterns": [r"profile", r"avatar", r"bio"]
        },
        PageType.SEARCH: {
            "url_patterns": [r"/search", r"\?q=", r"\?query="],
            "title_patterns": [r"search"],
            "content_patterns": [r"search.*results", r"no.*results", r"found.*\d+"]
        },
        PageType.LISTING: {
            "url_patterns": [r"/list", r"/products", r"/items", r"/catalog"],
            "title_patterns": [r"list", r"catalog", r"products"],
            "content_patterns": [r"showing.*\d+", r"items", r"filter", r"sort.*by"]
        },
        PageType.DETAIL: {
            "url_patterns": [r"/\d+$", r"/view/", r"/detail/", r"/product/"],
            "title_patterns": [],
            "content_patterns": [r"add.*to.*cart", r"buy.*now", r"description"]
        },
        PageType.CHECKOUT: {
            "url_patterns": [r"/checkout", r"/payment"],
            "title_patterns": [r"checkout", r"payment"],
            "content_patterns": [r"order.*summary", r"payment.*method", r"billing"]
        },
        PageType.CART: {
            "url_patterns": [r"/cart", r"/basket"],
            "title_patterns": [r"cart", r"basket", r"shopping"],
            "content_patterns": [r"your.*cart", r"subtotal", r"checkout"]
        },
        PageType.ERROR: {
            "url_patterns": [r"/error", r"/500", r"/403"],
            "title_patterns": [r"error", r"500", r"server"],
            "content_patterns": [r"error.*occurred", r"something.*wrong"]
        },
        PageType.NOT_FOUND: {
            "url_patterns": [r"/404", r"/not-found"],
            "title_patterns": [r"not.*found", r"404"],
            "content_patterns": [r"not.*found", r"page.*exist", r"404"]
        },
        PageType.CONTACT: {
            "url_patterns": [r"/contact", r"/support"],
            "title_patterns": [r"contact", r"support", r"help"],
            "content_patterns": [r"contact.*us", r"get.*in.*touch", r"support"]
        },
        PageType.ABOUT: {
            "url_patterns": [r"/about", r"/team", r"/company"],
            "title_patterns": [r"about", r"team", r"company"],
            "content_patterns": [r"about.*us", r"our.*story", r"mission"]
        }
    }

    def __init__(self, base_url: str = ""):
        """
        Initialize page analyzer.

        Args:
            base_url: Base URL of the application
        """
        self.base_url = base_url
        self._page_cache: Dict[str, PageAnalysis] = {}

    def analyze_page(
        self,
        html: str,
        url: str,
        title: str = "",
        dom_info: Optional[Dict[str, Any]] = None
    ) -> PageAnalysis:
        """
        Analyze a web page.

        Args:
            html: Page HTML content
            url: Page URL
            title: Page title
            dom_info: Additional DOM information from browser

        Returns:
            Complete page analysis
        """
        # Detect frameworks
        frameworks = self._detect_frameworks(html, dom_info)
        primary = frameworks[0] if frameworks else None

        # Detect page type
        page_type = self._detect_page_type(url, title, html)

        # Extract forms
        forms = self._extract_forms(html)

        # Extract links
        links = self._extract_links(html, url)

        # Detect features
        features = self._detect_features(html, dom_info)

        # Generate content hash
        content_hash = self._generate_content_hash(html)

        # Extract meta info
        meta_info = self._extract_meta_info(html)

        analysis = PageAnalysis(
            url=url,
            title=title or self._extract_title(html),
            page_type=page_type,
            detected_frameworks=frameworks,
            primary_framework=primary,
            forms=forms,
            links=links,
            interactive_elements_count=features.get("interactive_count", 0),
            has_authentication=features.get("has_auth", False),
            has_navigation=features.get("has_nav", False),
            has_search=features.get("has_search", False),
            has_pagination=features.get("has_pagination", False),
            has_modals=features.get("has_modals", False),
            has_tables=features.get("has_tables", False),
            content_hash=content_hash,
            meta_info=meta_info
        )

        # Cache analysis
        self._page_cache[url] = analysis

        return analysis

    def _detect_frameworks(
        self,
        html: str,
        dom_info: Optional[Dict[str, Any]]
    ) -> List[FrameworkType]:
        """Detect UI frameworks used on the page"""
        detected = []
        scores: Dict[FrameworkType, int] = {}

        for framework, signatures in self.FRAMEWORK_SIGNATURES.items():
            score = 0

            # Check scripts
            for pattern in signatures["scripts"]:
                if re.search(pattern, html, re.I):
                    score += 3

            # Check attributes
            for attr in signatures["attributes"]:
                if attr in html:
                    score += 2

            # Check classes
            for cls in signatures["classes"]:
                if cls in html:
                    score += 1

            # Check comments
            for comment in signatures["comments"]:
                if comment in html:
                    score += 1

            if score > 0:
                scores[framework] = score

        # Sort by score
        sorted_frameworks = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        detected = [f for f, _ in sorted_frameworks]

        return detected if detected else [FrameworkType.UNKNOWN]

    def _detect_page_type(self, url: str, title: str, html: str) -> PageType:
        """Detect the type of page"""
        url_lower = url.lower()
        title_lower = title.lower() if title else ""
        html_lower = html.lower()[:5000]  # Check first 5000 chars

        scores: Dict[PageType, int] = {}

        for page_type, patterns in self.PAGE_TYPE_PATTERNS.items():
            score = 0

            # Check URL patterns
            for pattern in patterns["url_patterns"]:
                if re.search(pattern, url_lower):
                    score += 3

            # Check title patterns
            for pattern in patterns["title_patterns"]:
                if re.search(pattern, title_lower):
                    score += 2

            # Check content patterns
            for pattern in patterns["content_patterns"]:
                if re.search(pattern, html_lower):
                    score += 1

            if score > 0:
                scores[page_type] = score

        if not scores:
            return PageType.UNKNOWN

        # Return highest scoring type
        return max(scores.items(), key=lambda x: x[1])[0]

    def _extract_forms(self, html: str) -> List[PageForm]:
        """Extract forms from HTML"""
        forms = []

        form_pattern = r'<form([^>]*)>(.*?)</form>'
        for match in re.finditer(form_pattern, html, re.DOTALL | re.I):
            form_attrs_str = match.group(1)
            form_content = match.group(2)

            # Extract form attributes
            form_id = self._extract_attr(form_attrs_str, "id")
            form_name = self._extract_attr(form_attrs_str, "name")
            action = self._extract_attr(form_attrs_str, "action") or ""
            method = self._extract_attr(form_attrs_str, "method") or "get"

            # Extract fields
            fields = self._extract_form_fields(form_content)

            # Find submit button
            submit_button = self._find_submit_button(form_content)

            forms.append(PageForm(
                form_id=form_id,
                form_name=form_name,
                action=action,
                method=method.upper(),
                fields=fields,
                submit_button=submit_button
            ))

        return forms

    def _extract_form_fields(self, form_html: str) -> List[Dict[str, Any]]:
        """Extract fields from a form"""
        fields = []

        # Extract inputs
        input_pattern = r'<input([^>]*)/?>'
        for match in re.finditer(input_pattern, form_html, re.I):
            attrs_str = match.group(1)
            field_type = self._extract_attr(attrs_str, "type") or "text"

            # Skip hidden and submit
            if field_type in ("hidden", "submit", "button"):
                continue

            fields.append({
                "type": field_type,
                "name": self._extract_attr(attrs_str, "name"),
                "id": self._extract_attr(attrs_str, "id"),
                "placeholder": self._extract_attr(attrs_str, "placeholder"),
                "required": "required" in attrs_str.lower()
            })

        # Extract textareas
        textarea_pattern = r'<textarea([^>]*)>'
        for match in re.finditer(textarea_pattern, form_html, re.I):
            attrs_str = match.group(1)
            fields.append({
                "type": "textarea",
                "name": self._extract_attr(attrs_str, "name"),
                "id": self._extract_attr(attrs_str, "id"),
                "placeholder": self._extract_attr(attrs_str, "placeholder"),
                "required": "required" in attrs_str.lower()
            })

        # Extract selects
        select_pattern = r'<select([^>]*)>'
        for match in re.finditer(select_pattern, form_html, re.I):
            attrs_str = match.group(1)
            fields.append({
                "type": "select",
                "name": self._extract_attr(attrs_str, "name"),
                "id": self._extract_attr(attrs_str, "id"),
                "required": "required" in attrs_str.lower()
            })

        return fields

    def _find_submit_button(self, form_html: str) -> Optional[Dict[str, Any]]:
        """Find the submit button in a form"""
        # Check for input type=submit
        submit_input = re.search(
            r'<input[^>]*type=["\']submit["\'][^>]*>',
            form_html, re.I
        )
        if submit_input:
            attrs_str = submit_input.group(0)
            return {
                "type": "input",
                "value": self._extract_attr(attrs_str, "value") or "Submit",
                "id": self._extract_attr(attrs_str, "id"),
                "name": self._extract_attr(attrs_str, "name")
            }

        # Check for button type=submit or no type
        button_pattern = r'<button([^>]*)>(.*?)</button>'
        for match in re.finditer(button_pattern, form_html, re.DOTALL | re.I):
            attrs_str = match.group(1)
            button_type = self._extract_attr(attrs_str, "type")

            if button_type in (None, "submit", ""):
                text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                return {
                    "type": "button",
                    "value": text or "Submit",
                    "id": self._extract_attr(attrs_str, "id"),
                    "name": self._extract_attr(attrs_str, "name")
                }

        return None

    def _extract_links(self, html: str, current_url: str) -> List[PageLink]:
        """Extract and classify links from HTML"""
        links = []
        seen_urls: Set[str] = set()

        parsed_base = urlparse(current_url)
        base_domain = parsed_base.netloc

        link_pattern = r'<a([^>]*)>(.*?)</a>'
        for match in re.finditer(link_pattern, html, re.DOTALL | re.I):
            attrs_str = match.group(1)
            text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

            href = self._extract_attr(attrs_str, "href")
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            # Normalize URL
            if href.startswith("/"):
                full_url = f"{parsed_base.scheme}://{base_domain}{href}"
            elif not href.startswith("http"):
                full_url = urljoin(current_url, href)
            else:
                full_url = href

            # Skip duplicates
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Determine if internal
            parsed_href = urlparse(full_url)
            is_internal = parsed_href.netloc == base_domain or not parsed_href.netloc

            # Classify link type
            link_type = self._classify_link(href, text, attrs_str)

            links.append(PageLink(
                url=full_url,
                text=text[:100],  # Limit text length
                is_internal=is_internal,
                link_type=link_type
            ))

        return links

    def _classify_link(self, href: str, text: str, attrs: str) -> str:
        """Classify the type of link"""
        text_lower = text.lower()
        href_lower = href.lower()

        # Action links
        action_patterns = ["logout", "delete", "remove", "cancel", "submit"]
        for pattern in action_patterns:
            if pattern in text_lower or pattern in href_lower:
                return "action"

        # Navigation links (in nav element or has nav-related classes)
        if "nav" in attrs.lower():
            return "navigation"

        # External links
        if href.startswith("http") and "mailto:" not in href:
            return "external"

        # Default to navigation for internal links
        return "navigation"

    def _detect_features(
        self,
        html: str,
        dom_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect various page features"""
        html_lower = html.lower()

        features = {
            "interactive_count": 0,
            "has_auth": False,
            "has_nav": False,
            "has_search": False,
            "has_pagination": False,
            "has_modals": False,
            "has_tables": False
        }

        # Count interactive elements
        features["interactive_count"] = (
            html_lower.count("<button") +
            html_lower.count("<input") +
            html_lower.count("<select") +
            html_lower.count("<textarea") +
            html_lower.count('role="button"')
        )

        # Has authentication
        auth_patterns = ["login", "logout", "sign in", "sign out", "password"]
        features["has_auth"] = any(p in html_lower for p in auth_patterns)

        # Has navigation
        features["has_nav"] = "<nav" in html_lower or 'role="navigation"' in html_lower

        # Has search
        search_patterns = ['type="search"', 'role="search"', "search-input", "searchbox"]
        features["has_search"] = any(p in html_lower for p in search_patterns)

        # Has pagination
        pagination_patterns = ["pagination", "page-", "pager", "next", "previous"]
        features["has_pagination"] = any(p in html_lower for p in pagination_patterns)

        # Has modals
        modal_patterns = ['role="dialog"', "modal", "popup", "overlay"]
        features["has_modals"] = any(p in html_lower for p in modal_patterns)

        # Has tables
        features["has_tables"] = "<table" in html_lower or 'role="grid"' in html_lower

        return features

    def _generate_content_hash(self, html: str) -> str:
        """Generate a hash of page content for change detection"""
        # Remove dynamic content (timestamps, session IDs, etc.)
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}', '', html)  # Dates
        cleaned = re.sub(r'\d+:\d+:\d+', '', cleaned)  # Times
        cleaned = re.sub(r'[a-f0-9]{32}', '', cleaned)  # MD5-like hashes
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace

        return hashlib.md5(cleaned.encode()).hexdigest()

    def _extract_meta_info(self, html: str) -> Dict[str, Any]:
        """Extract meta information from page"""
        meta_info = {}

        # Extract meta tags
        meta_pattern = r'<meta([^>]*)/?>'
        for match in re.finditer(meta_pattern, html, re.I):
            attrs_str = match.group(1)
            name = self._extract_attr(attrs_str, "name") or self._extract_attr(attrs_str, "property")
            content = self._extract_attr(attrs_str, "content")

            if name and content:
                meta_info[name] = content

        # Extract canonical URL
        canonical = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html, re.I)
        if canonical:
            meta_info["canonical"] = canonical.group(1)

        return meta_info

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML"""
        match = re.search(r'<title>([^<]+)</title>', html, re.I)
        return match.group(1).strip() if match else ""

    def _extract_attr(self, attrs_str: str, attr_name: str) -> Optional[str]:
        """Extract a specific attribute value"""
        pattern = rf'{attr_name}=["\']([^"\']*)["\']'
        match = re.search(pattern, attrs_str, re.I)
        return match.group(1) if match else None

    def has_page_changed(self, url: str, new_hash: str) -> bool:
        """Check if a page has changed since last analysis"""
        cached = self._page_cache.get(url)
        if not cached:
            return True
        return cached.content_hash != new_hash

    def get_page_type_for_testing(self, page_type: PageType) -> Dict[str, Any]:
        """
        Get testing recommendations for a page type.

        Returns suggested test scenarios and elements to test.
        """
        recommendations = {
            PageType.LOGIN: {
                "priority": "high",
                "test_scenarios": [
                    "Valid login with correct credentials",
                    "Invalid login with wrong password",
                    "Empty field validation",
                    "Remember me functionality",
                    "Forgot password link"
                ],
                "elements_to_test": ["email/username input", "password input", "submit button", "forgot password link"],
                "security_tests": ["SQL injection", "XSS in inputs"]
            },
            PageType.REGISTRATION: {
                "priority": "high",
                "test_scenarios": [
                    "Valid registration with all fields",
                    "Duplicate email/username handling",
                    "Password strength validation",
                    "Required field validation",
                    "Terms acceptance"
                ],
                "elements_to_test": ["all form fields", "password confirmation", "submit button"],
                "security_tests": ["Input validation", "Rate limiting"]
            },
            PageType.FORM: {
                "priority": "medium",
                "test_scenarios": [
                    "Submit with valid data",
                    "Submit with invalid data",
                    "Required field validation",
                    "Field format validation"
                ],
                "elements_to_test": ["all input fields", "submit button", "cancel button"],
                "security_tests": ["XSS", "Input sanitization"]
            },
            PageType.SEARCH: {
                "priority": "medium",
                "test_scenarios": [
                    "Search with valid query",
                    "Search with no results",
                    "Empty search handling",
                    "Special character handling"
                ],
                "elements_to_test": ["search input", "search button", "results list"],
                "security_tests": ["XSS in search"]
            },
            PageType.LISTING: {
                "priority": "medium",
                "test_scenarios": [
                    "Pagination navigation",
                    "Sort functionality",
                    "Filter application",
                    "Item selection"
                ],
                "elements_to_test": ["list items", "pagination", "sort dropdown", "filters"],
                "security_tests": []
            }
        }

        return recommendations.get(page_type, {
            "priority": "low",
            "test_scenarios": ["Basic functionality"],
            "elements_to_test": ["interactive elements"],
            "security_tests": []
        })
