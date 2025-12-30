"""
Project Context System

Stores and manages project-specific knowledge that helps the agent
understand and navigate the application like a manual tester would.

Key Components:
1. Application Map - Known pages and their URLs/identifiers
2. Navigation Paths - How to get from one page to another
3. Page Signatures - How to identify which page we're on
4. Navigation Elements - Buttons/links that lead to pages
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import re


class PageType(Enum):
    """Types of pages in an application"""
    LOGIN = "login"
    REGISTER = "register"
    HOME = "home"
    DASHBOARD = "dashboard"
    PROFILE = "profile"
    SETTINGS = "settings"
    LIST = "list"
    DETAIL = "detail"
    FORM = "form"
    SEARCH = "search"
    CHECKOUT = "checkout"
    CART = "cart"
    OTHER = "other"


@dataclass
class PageSignature:
    """How to identify if we're on a specific page"""
    url_patterns: List[str] = field(default_factory=list)  # URL patterns (regex)
    title_patterns: List[str] = field(default_factory=list)  # Page title patterns
    element_signatures: List[str] = field(default_factory=list)  # Unique elements on page
    text_markers: List[str] = field(default_factory=list)  # Text that appears on page

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'PageSignature':
        return cls(**data)


@dataclass
class NavigationElement:
    """An element that can be used for navigation"""
    selector: str  # CSS selector
    text: str  # Button/link text
    leads_to: str  # Page key it leads to
    confidence: float = 1.0  # How confident we are this leads there
    verified: bool = False  # Has this been verified by actual navigation?
    last_verified: str = ""  # When it was last verified

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'NavigationElement':
        return cls(**data)


@dataclass
class PageInfo:
    """Information about a page in the application"""
    key: str  # Unique identifier (e.g., "registration_page")
    name: str  # Human-readable name
    page_type: PageType
    url: Optional[str] = None  # Direct URL if known
    signature: Optional[PageSignature] = None
    navigation_elements: List[NavigationElement] = field(default_factory=list)  # Elements ON this page

    def to_dict(self) -> Dict:
        data = {
            'key': self.key,
            'name': self.name,
            'page_type': self.page_type.value,
            'url': self.url,
            'signature': self.signature.to_dict() if self.signature else None,
            'navigation_elements': [e.to_dict() for e in self.navigation_elements]
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'PageInfo':
        return cls(
            key=data['key'],
            name=data['name'],
            page_type=PageType(data.get('page_type', 'other')),
            url=data.get('url'),
            signature=PageSignature.from_dict(data['signature']) if data.get('signature') else None,
            navigation_elements=[NavigationElement.from_dict(e) for e in data.get('navigation_elements', [])]
        )


@dataclass
class NavigationPath:
    """A path from one page to another"""
    from_page: str  # Page key
    to_page: str  # Page key
    steps: List[Dict[str, Any]]  # Steps to navigate (actions)
    verified: bool = False
    success_count: int = 0
    fail_count: int = 0
    last_used: str = ""

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'NavigationPath':
        return cls(**data)


class ProjectContext:
    """
    Manages project-specific context and navigation knowledge.

    This is the "brain" that helps the agent understand the application
    and navigate it like a manual tester would.
    """

    # Common page name mappings
    PAGE_NAME_ALIASES = {
        'registration': ['register', 'signup', 'sign up', 'sign-up', 'create account', 'join'],
        'login': ['signin', 'sign in', 'sign-in', 'log in', 'authenticate'],
        'home': ['homepage', 'main', 'index', 'landing', 'start'],
        'dashboard': ['main dashboard', 'user dashboard', 'admin dashboard'],
        'profile': ['my profile', 'user profile', 'account'],
        'settings': ['preferences', 'configuration', 'options'],
        'cart': ['shopping cart', 'basket', 'bag'],
        'checkout': ['payment', 'pay', 'purchase'],
    }

    # Common navigation element patterns
    NAV_ELEMENT_PATTERNS = {
        'registration': [
            'sign up', 'signup', 'register', 'create account', 'join', 'get started',
            'new user', 'create an account', 'join now', 'register now', 'sign up free'
        ],
        'login': [
            'log in', 'login', 'sign in', 'signin', 'enter', 'access',
            'already have an account', 'existing user'
        ],
        'home': [
            'home', 'main', 'start', 'back to home', 'homepage'
        ],
        'dashboard': [
            'dashboard', 'my dashboard', 'go to dashboard'
        ],
        'profile': [
            'profile', 'my profile', 'my account', 'account settings'
        ],
        'logout': [
            'log out', 'logout', 'sign out', 'signout', 'exit'
        ],
    }

    def __init__(self, project_id: str, data_dir: str = "data"):
        self.project_id = project_id
        self.data_dir = Path(data_dir) / "project_context"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.context_file = self.data_dir / f"{self._safe_filename(project_id)}.json"

        # In-memory context
        self.pages: Dict[str, PageInfo] = {}
        self.navigation_paths: Dict[str, NavigationPath] = {}  # "from_page->to_page" as key
        self.base_url: Optional[str] = None
        self.app_name: Optional[str] = None
        self.framework: Optional[str] = None  # react, angular, vue, etc.

        # Load existing context
        self._load()

    def _safe_filename(self, name: str) -> str:
        """Create a safe filename from project ID"""
        return re.sub(r'[^\w\-]', '_', name.lower())

    def _load(self):
        """Load context from disk"""
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r') as f:
                    data = json.load(f)

                self.base_url = data.get('base_url')
                self.app_name = data.get('app_name')
                self.framework = data.get('framework')

                for page_data in data.get('pages', []):
                    page = PageInfo.from_dict(page_data)
                    self.pages[page.key] = page

                for path_data in data.get('navigation_paths', []):
                    path = NavigationPath.from_dict(path_data)
                    key = f"{path.from_page}->{path.to_page}"
                    self.navigation_paths[key] = path

                print(f"[PROJECT-CONTEXT] Loaded context for {self.project_id}: {len(self.pages)} pages, {len(self.navigation_paths)} paths", flush=True)

            except Exception as e:
                print(f"[PROJECT-CONTEXT] Error loading context: {e}", flush=True)

    def save(self):
        """Save context to disk"""
        data = {
            'project_id': self.project_id,
            'base_url': self.base_url,
            'app_name': self.app_name,
            'framework': self.framework,
            'updated_at': datetime.now().isoformat(),
            'pages': [p.to_dict() for p in self.pages.values()],
            'navigation_paths': [p.to_dict() for p in self.navigation_paths.values()]
        }

        with open(self.context_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"[PROJECT-CONTEXT] Saved context: {len(self.pages)} pages, {len(self.navigation_paths)} paths", flush=True)

    def set_base_info(self, base_url: str, app_name: Optional[str] = None, framework: Optional[str] = None):
        """Set basic application info"""
        self.base_url = base_url
        if app_name:
            self.app_name = app_name
        if framework:
            self.framework = framework
        self.save()

    # ==================== Page Management ====================

    def add_page(self, page: PageInfo) -> None:
        """Add or update a page"""
        self.pages[page.key] = page
        self.save()

    def get_page(self, key: str) -> Optional[PageInfo]:
        """Get a page by key"""
        return self.pages.get(key)

    def find_page_by_name(self, name: str) -> Optional[PageInfo]:
        """
        Find a page by name or alias.
        Uses fuzzy matching to handle variations like:
        - "registration page" -> "registration"
        - "the login screen" -> "login"
        """
        name_lower = name.lower().strip()

        # Remove common suffixes
        for suffix in [' page', ' screen', ' view', ' form']:
            if name_lower.endswith(suffix):
                name_lower = name_lower[:-len(suffix)].strip()

        # Remove common prefixes
        for prefix in ['the ', 'a ', 'an ']:
            if name_lower.startswith(prefix):
                name_lower = name_lower[len(prefix):].strip()

        # Direct key match
        if name_lower in self.pages:
            return self.pages[name_lower]

        # Check aliases
        for canonical, aliases in self.PAGE_NAME_ALIASES.items():
            if name_lower == canonical or name_lower in aliases:
                if canonical in self.pages:
                    return self.pages[canonical]
                # Try with _page suffix
                if f"{canonical}_page" in self.pages:
                    return self.pages[f"{canonical}_page"]

        # Fuzzy match on page names
        for page in self.pages.values():
            page_name_lower = page.name.lower()
            if name_lower in page_name_lower or page_name_lower in name_lower:
                return page

        return None

    def detect_page_type(self, name: str) -> PageType:
        """Detect the type of page from its name"""
        name_lower = name.lower()

        for page_type in PageType:
            if page_type.value in name_lower:
                return page_type

        # Check aliases
        for canonical, aliases in self.PAGE_NAME_ALIASES.items():
            if canonical in name_lower or any(alias in name_lower for alias in aliases):
                try:
                    return PageType(canonical)
                except ValueError:
                    pass

        return PageType.OTHER

    # ==================== Navigation Path Management ====================

    def add_navigation_path(self, path: NavigationPath) -> None:
        """Add or update a navigation path"""
        key = f"{path.from_page}->{path.to_page}"
        self.navigation_paths[key] = path
        self.save()

    def get_navigation_path(self, from_page: str, to_page: str) -> Optional[NavigationPath]:
        """Get the navigation path between two pages"""
        key = f"{from_page}->{to_page}"
        return self.navigation_paths.get(key)

    def record_navigation_success(self, from_page: str, to_page: str):
        """Record a successful navigation"""
        key = f"{from_page}->{to_page}"
        if key in self.navigation_paths:
            path = self.navigation_paths[key]
            path.success_count += 1
            path.verified = True
            path.last_used = datetime.now().isoformat()
            self.save()

    def record_navigation_failure(self, from_page: str, to_page: str):
        """Record a failed navigation"""
        key = f"{from_page}->{to_page}"
        if key in self.navigation_paths:
            path = self.navigation_paths[key]
            path.fail_count += 1
            path.last_used = datetime.now().isoformat()
            self.save()

    # ==================== Navigation Discovery ====================

    def get_nav_patterns_for_page(self, page_key: str) -> List[str]:
        """Get text patterns that typically lead to a page type"""
        # Normalize the key
        key = page_key.lower().replace('_page', '').replace('_', ' ').strip()

        # Direct match
        if key in self.NAV_ELEMENT_PATTERNS:
            return self.NAV_ELEMENT_PATTERNS[key]

        # Check aliases
        for canonical, aliases in self.PAGE_NAME_ALIASES.items():
            if key == canonical or key in aliases:
                if canonical in self.NAV_ELEMENT_PATTERNS:
                    return self.NAV_ELEMENT_PATTERNS[canonical]

        return []

    def get_direct_url_for_page(self, page_key: str) -> Optional[str]:
        """
        Get a direct URL for a page if known.
        Falls back to common URL patterns.
        """
        page = self.get_page(page_key)
        if page and page.url:
            return page.url

        # Try to construct URL from common patterns
        if not self.base_url:
            return None

        base = self.base_url.rstrip('/')
        key = page_key.lower().replace('_page', '').replace('_', '-')

        # Common URL patterns by page type
        url_patterns = {
            'registration': ['/register', '/signup', '/sign-up', '/create-account'],
            'login': ['/login', '/signin', '/sign-in', '/auth/login'],
            'home': ['/', '/home', '/index'],
            'dashboard': ['/dashboard', '/home', '/app'],
            'profile': ['/profile', '/account', '/me'],
            'settings': ['/settings', '/preferences', '/account/settings'],
            'cart': ['/cart', '/basket', '/shopping-cart'],
            'checkout': ['/checkout', '/payment', '/order'],
        }

        # Find matching pattern
        for pattern_key, urls in url_patterns.items():
            if pattern_key in key:
                return f"{base}{urls[0]}"

        # Default: try the key as URL
        return f"{base}/{key}"

    def suggest_navigation_strategy(self, target_page: str) -> Dict[str, Any]:
        """
        Suggest a strategy to navigate to a target page.
        Returns prioritized list of strategies.
        """
        strategies = []

        # 1. Known navigation path
        for path in self.navigation_paths.values():
            if path.to_page == target_page and path.verified:
                strategies.append({
                    'type': 'known_path',
                    'priority': 1,
                    'path': path,
                    'confidence': path.success_rate
                })

        # 2. Direct URL navigation
        url = self.get_direct_url_for_page(target_page)
        if url:
            strategies.append({
                'type': 'direct_url',
                'priority': 2,
                'url': url,
                'confidence': 0.8
            })

        # 3. Find navigation element on current page
        nav_patterns = self.get_nav_patterns_for_page(target_page)
        if nav_patterns:
            strategies.append({
                'type': 'find_nav_element',
                'priority': 3,
                'patterns': nav_patterns,
                'confidence': 0.7
            })

        # 4. Explore DOM for navigation
        strategies.append({
            'type': 'explore_dom',
            'priority': 4,
            'target': target_page,
            'confidence': 0.5
        })

        # Sort by priority
        strategies.sort(key=lambda s: s['priority'])

        return {
            'target_page': target_page,
            'strategies': strategies
        }

    # ==================== Page Detection ====================

    def identify_current_page(self, url: str, title: str, page_text: str) -> Optional[str]:
        """
        Identify which page we're currently on based on URL, title, and content.
        Returns the page key if found.
        """
        url_lower = url.lower()
        title_lower = title.lower() if title else ""
        text_lower = page_text.lower() if page_text else ""

        for page in self.pages.values():
            if not page.signature:
                continue

            sig = page.signature

            # Check URL patterns
            for pattern in sig.url_patterns:
                if re.search(pattern, url_lower):
                    return page.key

            # Check title patterns
            for pattern in sig.title_patterns:
                if re.search(pattern, title_lower):
                    return page.key

            # Check text markers
            matches = sum(1 for marker in sig.text_markers if marker.lower() in text_lower)
            if len(sig.text_markers) > 0 and matches >= len(sig.text_markers) * 0.7:
                return page.key

        # Fallback: infer from URL
        return self._infer_page_from_url(url)

    def _infer_page_from_url(self, url: str) -> Optional[str]:
        """Infer page type from URL patterns"""
        url_lower = url.lower()

        url_to_page = {
            '/register': 'registration',
            '/signup': 'registration',
            '/sign-up': 'registration',
            '/login': 'login',
            '/signin': 'login',
            '/sign-in': 'login',
            '/dashboard': 'dashboard',
            '/home': 'home',
            '/profile': 'profile',
            '/settings': 'settings',
            '/cart': 'cart',
            '/checkout': 'checkout',
        }

        for url_pattern, page_key in url_to_page.items():
            if url_pattern in url_lower:
                return page_key

        # Check if on root (likely home)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.path in ['', '/', '/index', '/index.html']:
            return 'home'

        return None

    def is_on_page(self, target_page: str, current_url: str, title: str = "", page_text: str = "") -> bool:
        """Check if we're currently on a specific page"""
        current = self.identify_current_page(current_url, title, page_text)

        if current == target_page:
            return True

        # Normalize and compare
        target_normalized = target_page.lower().replace('_page', '').replace('_', ' ').strip()

        # Check aliases
        for canonical, aliases in self.PAGE_NAME_ALIASES.items():
            if target_normalized == canonical or target_normalized in aliases:
                if current == canonical:
                    return True

        return False

    # ==================== Learning from Execution ====================

    def learn_page(self, page_key: str, url: str, title: str, unique_elements: List[str]) -> PageInfo:
        """Learn about a page from observation"""
        from urllib.parse import urlparse

        page_type = self.detect_page_type(page_key)
        parsed = urlparse(url)

        # Create signature
        signature = PageSignature(
            url_patterns=[re.escape(parsed.path)],
            title_patterns=[re.escape(title)] if title else [],
            element_signatures=unique_elements[:5],  # Top 5 unique elements
        )

        page = PageInfo(
            key=page_key,
            name=page_key.replace('_', ' ').title(),
            page_type=page_type,
            url=url,
            signature=signature
        )

        self.add_page(page)
        return page

    def learn_navigation(self, from_url: str, to_url: str, action: Dict[str, Any], success: bool):
        """Learn a navigation from observation"""
        from_page = self._infer_page_from_url(from_url) or "unknown"
        to_page = self._infer_page_from_url(to_url) or "unknown"

        if from_page == "unknown" or to_page == "unknown":
            return

        key = f"{from_page}->{to_page}"

        if key in self.navigation_paths:
            path = self.navigation_paths[key]
            if success:
                path.success_count += 1
                path.verified = True
            else:
                path.fail_count += 1
            path.last_used = datetime.now().isoformat()
        else:
            path = NavigationPath(
                from_page=from_page,
                to_page=to_page,
                steps=[action],
                verified=success,
                success_count=1 if success else 0,
                fail_count=0 if success else 1,
                last_used=datetime.now().isoformat()
            )

        self.navigation_paths[key] = path
        self.save()

    def add_navigation_element_to_page(
        self,
        page_key: str,
        selector: str,
        text: str,
        leads_to: str,
        verified: bool = False
    ):
        """Add a navigation element to a page"""
        page = self.get_page(page_key)
        if not page:
            page = PageInfo(
                key=page_key,
                name=page_key.replace('_', ' ').title(),
                page_type=self.detect_page_type(page_key)
            )

        nav_element = NavigationElement(
            selector=selector,
            text=text,
            leads_to=leads_to,
            verified=verified,
            last_verified=datetime.now().isoformat() if verified else ""
        )

        # Check if already exists
        existing = None
        for i, elem in enumerate(page.navigation_elements):
            if elem.selector == selector or elem.text.lower() == text.lower():
                existing = i
                break

        if existing is not None:
            page.navigation_elements[existing] = nav_element
        else:
            page.navigation_elements.append(nav_element)

        self.add_page(page)


# Singleton pattern for project context
_contexts: Dict[str, ProjectContext] = {}

def get_project_context(project_id: str, data_dir: str = "data") -> ProjectContext:
    """Get or create a project context"""
    if project_id not in _contexts:
        _contexts[project_id] = ProjectContext(project_id, data_dir)
    return _contexts[project_id]
