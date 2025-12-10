"""
Semantic Element Intelligence (SEI) System

A revolutionary approach to element identification that understands elements
by their PURPOSE, CONTEXT, and RELATIONSHIPS - not just their attributes.

Key Innovations:
1. Element DNA - Multi-dimensional fingerprint capturing everything about an element
2. Semantic Understanding - Knows what an element IS (login button, search field)
3. Relationship Mapping - Understands how elements relate to each other
4. Intent Resolution - Matches human intent to elements naturally
5. Predictive Confidence - Learns which selectors are stable vs fragile
6. Context Awareness - Understands page type and element roles

This goes beyond traditional selector matching by treating elements as
meaningful entities with purpose, not just DOM nodes with attributes.
"""

import re
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# ==================== Semantic Types ====================

class SemanticType(Enum):
    """
    What an element IS, semantically.
    This captures the element's PURPOSE, not its implementation.
    """
    # Authentication
    USERNAME_INPUT = "username_input"
    PASSWORD_INPUT = "password_input"
    LOGIN_BUTTON = "login_button"
    LOGOUT_BUTTON = "logout_button"
    REMEMBER_ME = "remember_me"
    FORGOT_PASSWORD = "forgot_password"

    # Forms
    TEXT_INPUT = "text_input"
    EMAIL_INPUT = "email_input"
    PHONE_INPUT = "phone_input"
    SEARCH_INPUT = "search_input"
    TEXTAREA = "textarea"
    SUBMIT_BUTTON = "submit_button"
    CANCEL_BUTTON = "cancel_button"
    FORM_FIELD = "form_field"

    # Navigation
    NAV_LINK = "nav_link"
    MENU_ITEM = "menu_item"
    BREADCRUMB = "breadcrumb"
    BACK_BUTTON = "back_button"
    HOME_LINK = "home_link"

    # E-commerce
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CART_ICON = "cart_icon"
    CHECKOUT_BUTTON = "checkout_button"
    QUANTITY_INPUT = "quantity_input"
    PRICE_DISPLAY = "price_display"
    PRODUCT_CARD = "product_card"

    # Common UI
    CLOSE_BUTTON = "close_button"
    MODAL_OVERLAY = "modal_overlay"
    DROPDOWN_TOGGLE = "dropdown_toggle"
    CHECKBOX = "checkbox"
    RADIO_BUTTON = "radio_button"
    TOGGLE_SWITCH = "toggle_switch"
    TAB = "tab"
    ACCORDION = "accordion"

    # Content
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    IMAGE = "image"
    LINK = "link"
    BUTTON = "button"

    # Unknown
    UNKNOWN = "unknown"


class PageType(Enum):
    """
    What type of page we're on - provides context for element resolution.
    """
    LOGIN = "login"
    REGISTRATION = "registration"
    HOME = "home"
    PRODUCT_LIST = "product_list"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"
    CHECKOUT = "checkout"
    SEARCH_RESULTS = "search_results"
    PROFILE = "profile"
    SETTINGS = "settings"
    DASHBOARD = "dashboard"
    UNKNOWN = "unknown"


# ==================== Element DNA ====================

@dataclass
class ElementDNA:
    """
    Multi-dimensional fingerprint that uniquely identifies an element.

    Like biological DNA, this captures the essence of an element in a way
    that remains identifiable even when surface attributes change.

    The DNA is composed of multiple "genes" - each capturing a different
    aspect of the element's identity.
    """
    # Identity genes
    semantic_type: SemanticType = SemanticType.UNKNOWN
    element_tag: str = ""
    element_type: str = ""  # input type, button type, etc.

    # Attribute genes
    test_id: Optional[str] = None  # data-testid, data-test, data-cy
    element_id: Optional[str] = None
    name: Optional[str] = None
    aria_label: Optional[str] = None
    placeholder: Optional[str] = None
    role: Optional[str] = None

    # Visual genes
    text_content: str = ""
    visible_text: str = ""  # Text user sees
    position_hint: str = ""  # "top", "center", "bottom", "left", "right"

    # Structural genes
    parent_semantic: Optional[str] = None  # What's the parent's purpose
    form_context: Optional[str] = None  # What form is this in
    sibling_hints: List[str] = field(default_factory=list)
    dom_depth: int = 0
    child_count: int = 0

    # Relationship genes
    label_text: Optional[str] = None  # Associated <label>
    nearby_text: List[str] = field(default_factory=list)
    preceding_element: Optional[str] = None
    following_element: Optional[str] = None

    # Behavioral genes (what happens when interacted with)
    is_clickable: bool = False
    is_editable: bool = False
    triggers_navigation: bool = False
    triggers_submit: bool = False

    # Stability genes (how likely to change)
    has_dynamic_id: bool = False
    has_framework_classes: bool = False
    has_test_attribute: bool = True

    # Confidence tracking
    discovery_time: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    match_count: int = 0
    fail_count: int = 0

    def compute_dna_hash(self) -> str:
        """
        Generate a stable hash from the most stable DNA components.
        This hash should remain similar even when some attributes change.
        """
        stable_components = [
            self.semantic_type.value,
            self.element_tag,
            self.element_type,
            self.text_content[:50] if self.text_content else "",
            self.label_text or "",
            self.aria_label or "",
            self.role or "",
        ]
        combined = "|".join(str(c) for c in stable_components)
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def similarity_score(self, other: 'ElementDNA') -> float:
        """
        Calculate how similar two DNA profiles are.
        Returns 0.0 to 1.0
        """
        scores = []
        weights = []

        # Semantic type match (highest weight)
        if self.semantic_type == other.semantic_type and self.semantic_type != SemanticType.UNKNOWN:
            scores.append(1.0)
            weights.append(3.0)
        else:
            scores.append(0.0)
            weights.append(3.0)

        # Tag match
        if self.element_tag == other.element_tag:
            scores.append(1.0)
        else:
            scores.append(0.0)
        weights.append(1.0)

        # Test ID match (very reliable)
        if self.test_id and other.test_id:
            if self.test_id == other.test_id:
                scores.append(1.0)
                weights.append(3.0)
            else:
                scores.append(0.0)
                weights.append(0.5)

        # Text content similarity
        if self.text_content and other.text_content:
            ratio = SequenceMatcher(None,
                self.text_content.lower(),
                other.text_content.lower()
            ).ratio()
            scores.append(ratio)
            weights.append(2.0)

        # Label match
        if self.label_text and other.label_text:
            ratio = SequenceMatcher(None,
                self.label_text.lower(),
                other.label_text.lower()
            ).ratio()
            scores.append(ratio)
            weights.append(2.0)

        # Aria label match
        if self.aria_label and other.aria_label:
            if self.aria_label.lower() == other.aria_label.lower():
                scores.append(1.0)
            else:
                scores.append(0.3)
            weights.append(1.5)

        # Position hint
        if self.position_hint and other.position_hint:
            if self.position_hint == other.position_hint:
                scores.append(1.0)
            else:
                scores.append(0.0)
            weights.append(0.5)

        if not weights:
            return 0.0

        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)


# ==================== Semantic Patterns ====================

class SemanticPatterns:
    """
    Patterns for identifying what an element IS based on multiple signals.
    This is the "brain" that understands element purposes.
    """

    # Patterns that identify semantic types
    # Each pattern is: (attribute_type, pattern, semantic_type, confidence_boost)
    SEMANTIC_INDICATORS = {
        SemanticType.USERNAME_INPUT: {
            "test_ids": ["username", "user-name", "user_name", "login-username", "email", "userid", "user-id"],
            "names": ["username", "user", "email", "login", "userid"],
            "ids": ["username", "user-name", "user_name", "email", "login-email", "userid"],
            "placeholders": ["username", "user name", "email", "enter username", "enter email"],
            "labels": ["username", "user name", "email", "login", "user id"],
            "aria": ["username", "user name", "email address", "login email"],
            "autocomplete": ["username", "email"],
            "input_types": ["text", "email"],
        },
        SemanticType.PASSWORD_INPUT: {
            "test_ids": ["password", "pass", "pwd", "login-password", "user-password"],
            "names": ["password", "pass", "pwd"],
            "ids": ["password", "pass", "pwd", "login-password"],
            "placeholders": ["password", "enter password", "your password"],
            "labels": ["password", "pass"],
            "aria": ["password", "enter password"],
            "autocomplete": ["current-password", "new-password"],
            "input_types": ["password"],
        },
        SemanticType.LOGIN_BUTTON: {
            "test_ids": ["login", "login-button", "signin", "sign-in", "submit-login", "login-submit"],
            "ids": ["login", "login-button", "signin", "sign-in", "btnLogin"],
            "text_content": ["log in", "login", "sign in", "signin", "submit", "enter"],
            "aria": ["log in", "sign in", "login"],
            "names": ["login", "signin", "submit"],
        },
        SemanticType.SEARCH_INPUT: {
            "test_ids": ["search", "search-input", "search-box", "query", "search-field"],
            "names": ["search", "query", "q", "s", "keyword"],
            "ids": ["search", "search-input", "searchbox", "query"],
            "placeholders": ["search", "find", "look for", "what are you looking for"],
            "labels": ["search", "find"],
            "aria": ["search", "site search", "search products"],
            "input_types": ["search", "text"],
            "roles": ["searchbox"],
        },
        SemanticType.ADD_TO_CART: {
            "test_ids": ["add-to-cart", "addtocart", "add-cart", "buy-now"],
            "ids": ["add-to-cart", "addToCart", "buyNow", "add-cart"],
            "text_content": ["add to cart", "add to bag", "buy now", "add to basket"],
            "aria": ["add to cart", "add to shopping cart", "buy now"],
            "classes": ["add-to-cart", "addToCart", "buy-button"],
        },
        SemanticType.CART_ICON: {
            "test_ids": ["cart", "shopping-cart", "cart-icon", "basket"],
            "ids": ["cart", "shopping-cart", "cart-icon", "mini-cart"],
            "aria": ["cart", "shopping cart", "view cart", "basket"],
            "classes": ["cart-icon", "shopping-cart", "cart-link"],
        },
        SemanticType.CHECKOUT_BUTTON: {
            "test_ids": ["checkout", "checkout-button", "proceed-checkout"],
            "ids": ["checkout", "checkoutButton", "proceed-checkout"],
            "text_content": ["checkout", "proceed to checkout", "check out", "go to checkout"],
            "aria": ["checkout", "proceed to checkout"],
        },
        SemanticType.SUBMIT_BUTTON: {
            "input_types": ["submit"],
            "button_types": ["submit"],
            "text_content": ["submit", "send", "save", "continue", "next", "done", "confirm"],
            "roles": ["button"],
        },
        SemanticType.CLOSE_BUTTON: {
            "test_ids": ["close", "close-button", "dismiss", "close-modal"],
            "aria": ["close", "dismiss", "close dialog", "close modal"],
            "text_content": ["×", "x", "close", "dismiss"],
            "classes": ["close", "close-button", "modal-close", "dismiss"],
        },
    }

    # Page type indicators
    PAGE_INDICATORS = {
        PageType.LOGIN: {
            "url_patterns": ["/login", "/signin", "/sign-in", "/auth", "/account/login"],
            "title_patterns": ["login", "sign in", "log in", "authentication"],
            "element_hints": ["password input present", "login button present"],
        },
        PageType.CART: {
            "url_patterns": ["/cart", "/basket", "/shopping-cart", "/bag"],
            "title_patterns": ["cart", "basket", "shopping bag", "your items"],
            "element_hints": ["cart items present", "checkout button present"],
        },
        PageType.CHECKOUT: {
            "url_patterns": ["/checkout", "/payment", "/order", "/purchase"],
            "title_patterns": ["checkout", "payment", "complete order", "shipping"],
        },
        PageType.PRODUCT_LIST: {
            "url_patterns": ["/products", "/catalog", "/shop", "/collection", "/inventory"],
            "title_patterns": ["products", "shop", "browse", "catalog"],
            "element_hints": ["multiple product cards", "filter options"],
        },
        PageType.PRODUCT_DETAIL: {
            "url_patterns": ["/product/", "/item/", "/p/"],
            "element_hints": ["add to cart button", "product images", "price display"],
        },
    }

    @classmethod
    def identify_semantic_type(cls, dna: ElementDNA) -> Tuple[SemanticType, float]:
        """
        Identify what semantic type an element is based on its DNA.
        Returns (semantic_type, confidence)
        """
        best_type = SemanticType.UNKNOWN
        best_score = 0.0

        for sem_type, patterns in cls.SEMANTIC_INDICATORS.items():
            score = 0.0
            matches = 0

            # Check test IDs
            if dna.test_id and "test_ids" in patterns:
                test_id_lower = dna.test_id.lower()
                for pattern in patterns["test_ids"]:
                    if pattern in test_id_lower or test_id_lower in pattern:
                        score += 0.4
                        matches += 1
                        break

            # Check element ID
            if dna.element_id and "ids" in patterns:
                id_lower = dna.element_id.lower()
                for pattern in patterns["ids"]:
                    if pattern in id_lower or id_lower in pattern:
                        score += 0.25
                        matches += 1
                        break

            # Check name
            if dna.name and "names" in patterns:
                name_lower = dna.name.lower()
                for pattern in patterns["names"]:
                    if pattern in name_lower:
                        score += 0.2
                        matches += 1
                        break

            # Check placeholder
            if dna.placeholder and "placeholders" in patterns:
                ph_lower = dna.placeholder.lower()
                for pattern in patterns["placeholders"]:
                    if pattern in ph_lower:
                        score += 0.15
                        matches += 1
                        break

            # Check text content
            if dna.text_content and "text_content" in patterns:
                text_lower = dna.text_content.lower()
                for pattern in patterns["text_content"]:
                    if pattern in text_lower:
                        score += 0.2
                        matches += 1
                        break

            # Check aria label
            if dna.aria_label and "aria" in patterns:
                aria_lower = dna.aria_label.lower()
                for pattern in patterns["aria"]:
                    if pattern in aria_lower:
                        score += 0.15
                        matches += 1
                        break

            # Check input type
            if dna.element_type and "input_types" in patterns:
                if dna.element_type.lower() in patterns["input_types"]:
                    score += 0.3
                    matches += 1

            # Check label text
            if dna.label_text and "labels" in patterns:
                label_lower = dna.label_text.lower()
                for pattern in patterns["labels"]:
                    if pattern in label_lower:
                        score += 0.2
                        matches += 1
                        break

            # Boost for multiple matches
            if matches >= 2:
                score *= 1.2
            if matches >= 3:
                score *= 1.3

            # Cap at 1.0
            score = min(score, 1.0)

            if score > best_score:
                best_score = score
                best_type = sem_type

        return best_type, best_score

    @classmethod
    def identify_page_type(cls, url: str, title: str, html_hints: List[str]) -> Tuple[PageType, float]:
        """
        Identify what type of page we're on.
        """
        best_type = PageType.UNKNOWN
        best_score = 0.0
        url_lower = url.lower()
        title_lower = title.lower()

        for page_type, indicators in cls.PAGE_INDICATORS.items():
            score = 0.0

            # Check URL patterns
            for pattern in indicators.get("url_patterns", []):
                if pattern in url_lower:
                    score += 0.5
                    break

            # Check title patterns
            for pattern in indicators.get("title_patterns", []):
                if pattern in title_lower:
                    score += 0.3
                    break

            if score > best_score:
                best_score = score
                best_type = page_type

        return best_type, best_score


# ==================== Element Relationship Graph ====================

@dataclass
class ElementRelationship:
    """Represents a relationship between two elements."""
    source_key: str
    target_key: str
    relationship_type: str  # "label_for", "inside_form", "sibling", "parent", "child"
    strength: float  # 0.0 to 1.0


class ElementRelationshipGraph:
    """
    Tracks how elements relate to each other.

    This allows us to find elements by their relationships:
    - "The input that the 'Username' label points to"
    - "The submit button inside the login form"
    - "The field after the username field"
    """

    def __init__(self):
        self.relationships: List[ElementRelationship] = []
        self.element_keys: Set[str] = set()

    def add_relationship(self, source: str, target: str, rel_type: str, strength: float = 1.0):
        """Add a relationship between two elements."""
        self.relationships.append(ElementRelationship(source, target, rel_type, strength))
        self.element_keys.add(source)
        self.element_keys.add(target)

    def find_by_relationship(self, anchor: str, rel_type: str) -> List[Tuple[str, float]]:
        """
        Find elements by their relationship to an anchor element.
        Returns list of (element_key, strength) tuples.
        """
        results = []
        for rel in self.relationships:
            if rel.source_key == anchor and rel.relationship_type == rel_type:
                results.append((rel.target_key, rel.strength))
            elif rel.target_key == anchor and rel.relationship_type == rel_type:
                results.append((rel.source_key, rel.strength))
        return sorted(results, key=lambda x: x[1], reverse=True)

    def get_context_elements(self, element_key: str) -> Dict[str, List[str]]:
        """
        Get all elements related to the given element, grouped by relationship type.
        """
        context = {}
        for rel in self.relationships:
            if rel.source_key == element_key:
                if rel.relationship_type not in context:
                    context[rel.relationship_type] = []
                context[rel.relationship_type].append(rel.target_key)
            elif rel.target_key == element_key:
                if rel.relationship_type not in context:
                    context[rel.relationship_type] = []
                context[rel.relationship_type].append(rel.source_key)
        return context


# ==================== Intent Resolution ====================

class IntentResolver:
    """
    Resolves human intent to element semantic types.

    This allows natural language queries like:
    - "enter username" -> USERNAME_INPUT
    - "click login" -> LOGIN_BUTTON
    - "add to cart" -> ADD_TO_CART
    """

    # Intent patterns mapped to semantic types
    INTENT_PATTERNS = {
        # Authentication intents
        r"(enter|type|input|fill).*?(user\s*name|user|login|email)": SemanticType.USERNAME_INPUT,
        r"(enter|type|input|fill).*?(password|pass|pwd)": SemanticType.PASSWORD_INPUT,
        r"(click|press|tap|submit).*?(log\s*in|sign\s*in|login|signin|enter)": SemanticType.LOGIN_BUTTON,
        r"(click|press|tap).*?(log\s*out|sign\s*out|logout|signout)": SemanticType.LOGOUT_BUTTON,

        # Search intents
        r"(search|find|look\s*for|query)": SemanticType.SEARCH_INPUT,

        # E-commerce intents
        r"(add|put).*?(cart|basket|bag)": SemanticType.ADD_TO_CART,
        r"(remove|delete).*?(cart|basket|bag)": SemanticType.REMOVE_FROM_CART,
        r"(view|open|go\s*to).*?(cart|basket|bag)": SemanticType.CART_ICON,
        r"(checkout|purchase|buy|complete\s*order)": SemanticType.CHECKOUT_BUTTON,

        # Form intents
        r"(submit|send|save|confirm).*?(form)?": SemanticType.SUBMIT_BUTTON,
        r"(cancel|close|dismiss|back)": SemanticType.CLOSE_BUTTON,

        # Navigation intents
        r"(go|navigate|click).*?(home|main|start)": SemanticType.HOME_LINK,
        r"(go|navigate|click).*?(back|previous)": SemanticType.BACK_BUTTON,
    }

    @classmethod
    def resolve_intent(cls, intent: str) -> Tuple[Optional[SemanticType], float]:
        """
        Resolve a human intent to a semantic type.
        Returns (semantic_type, confidence) or (None, 0.0) if no match.
        """
        intent_lower = intent.lower().strip()

        for pattern, sem_type in cls.INTENT_PATTERNS.items():
            if re.search(pattern, intent_lower, re.I):
                return sem_type, 0.9

        # Fallback: try keyword matching
        keywords = {
            SemanticType.USERNAME_INPUT: ["username", "user", "email", "login field"],
            SemanticType.PASSWORD_INPUT: ["password", "pass", "secret"],
            SemanticType.LOGIN_BUTTON: ["login", "sign in", "log in", "signin"],
            SemanticType.SEARCH_INPUT: ["search", "find", "query"],
            SemanticType.ADD_TO_CART: ["cart", "add to cart", "buy"],
            SemanticType.SUBMIT_BUTTON: ["submit", "send", "save", "ok", "confirm"],
        }

        for sem_type, kws in keywords.items():
            for kw in kws:
                if kw in intent_lower:
                    return sem_type, 0.7

        return None, 0.0


# ==================== Predictive Confidence ====================

class PredictiveConfidence:
    """
    Predicts selector stability and adjusts confidence accordingly.

    Some selectors are inherently more stable than others:
    - data-testid: Very stable (intentionally added for testing)
    - id: Usually stable, but can be dynamic
    - class: Often unstable (changes with styling)
    - XPath position: Very unstable

    This system learns from history which selectors tend to break.
    """

    # Base stability scores for different selector types
    STABILITY_SCORES = {
        "data-testid": 0.98,
        "data-test": 0.98,
        "data-cy": 0.97,
        "data-qa": 0.97,
        "id": 0.85,
        "name": 0.80,
        "aria-label": 0.85,
        "placeholder": 0.70,
        "class": 0.50,
        "xpath_position": 0.30,
        "text_content": 0.65,
    }

    # Patterns that indicate instability
    INSTABILITY_PATTERNS = [
        (r"[a-z]+[-_]?[0-9a-f]{6,}", -0.3),  # Dynamic IDs with hashes
        (r"^[0-9]+$", -0.4),  # Numeric-only IDs
        (r"ng-|_ng[A-Z]|mat-", -0.2),  # Angular framework
        (r"css-[a-z0-9]+", -0.3),  # CSS-in-JS
        (r"sc-[a-zA-Z]+", -0.3),  # Styled components
        (r"jsx?-[0-9]+", -0.3),  # JSX dynamic
        (r"__[a-zA-Z]+__", -0.2),  # BEM modifiers
        (r"svelte-[a-z0-9]+", -0.3),  # Svelte
    ]

    # Patterns that indicate stability
    STABILITY_PATTERNS = [
        (r"^[a-z]+-[a-z]+(-[a-z]+)?$", 0.1),  # Clean kebab-case
        (r"^[a-z]+_[a-z]+$", 0.1),  # Clean snake_case
        (r"(btn|button|input|form|nav|header|footer|main)", 0.05),  # Semantic names
    ]

    @classmethod
    def predict_stability(cls, selector: str, selector_type: str) -> float:
        """
        Predict how stable a selector is likely to be.
        Returns 0.0 (very unstable) to 1.0 (very stable).
        """
        # Start with base score for selector type
        base_score = cls.STABILITY_SCORES.get(selector_type, 0.5)

        # Apply instability penalties
        for pattern, penalty in cls.INSTABILITY_PATTERNS:
            if re.search(pattern, selector, re.I):
                base_score += penalty

        # Apply stability bonuses
        for pattern, bonus in cls.STABILITY_PATTERNS:
            if re.search(pattern, selector, re.I):
                base_score += bonus

        # Clamp to valid range
        return max(0.1, min(1.0, base_score))

    @classmethod
    def adjust_confidence(
        cls,
        base_confidence: float,
        selector: str,
        selector_type: str,
        history: Optional[Dict] = None
    ) -> float:
        """
        Adjust confidence based on predicted stability and history.
        """
        stability = cls.predict_stability(selector, selector_type)

        # Blend base confidence with stability prediction
        adjusted = base_confidence * 0.7 + stability * 0.3

        # Apply historical adjustments if available
        if history:
            success_rate = history.get("success_rate", 1.0)
            adjusted *= success_rate

            # Decay for old selectors
            days_since_success = history.get("days_since_success", 0)
            if days_since_success > 30:
                adjusted *= 0.9
            if days_since_success > 90:
                adjusted *= 0.8

        return adjusted


# ==================== Main Intelligence Engine ====================

class SemanticElementIntelligence:
    """
    The main intelligence engine that brings everything together.

    This is the "brain" of GhostQA's element identification system.
    It understands elements semantically, tracks relationships,
    resolves intents, and predicts selector stability.
    """

    def __init__(self):
        self.element_dna_cache: Dict[str, ElementDNA] = {}  # key -> DNA
        self.relationship_graph = ElementRelationshipGraph()
        self.page_context: Optional[PageType] = None
        self.url: str = ""

    def extract_element_dna(self, element_html: str, context_html: str = "") -> ElementDNA:
        """
        Extract DNA from an element's HTML.
        """
        dna = ElementDNA()

        # Extract tag
        tag_match = re.match(r'<(\w+)', element_html)
        if tag_match:
            dna.element_tag = tag_match.group(1).lower()

        # Extract attributes
        attr_patterns = {
            'data-testid': r'data-testid=["\']([^"\']+)["\']',
            'data-test': r'data-test=["\']([^"\']+)["\']',
            'data-cy': r'data-cy=["\']([^"\']+)["\']',
            'id': r'\bid=["\']([^"\']+)["\']',
            'name': r'\bname=["\']([^"\']+)["\']',
            'class': r'\bclass=["\']([^"\']+)["\']',
            'placeholder': r'placeholder=["\']([^"\']+)["\']',
            'aria-label': r'aria-label=["\']([^"\']+)["\']',
            'type': r'\btype=["\']([^"\']+)["\']',
            'role': r'\brole=["\']([^"\']+)["\']',
            'value': r'\bvalue=["\']([^"\']+)["\']',
        }

        for attr, pattern in attr_patterns.items():
            match = re.search(pattern, element_html, re.I)
            if match:
                value = match.group(1)
                if attr in ('data-testid', 'data-test', 'data-cy'):
                    dna.test_id = value
                elif attr == 'id':
                    dna.element_id = value
                    dna.has_dynamic_id = bool(re.search(r'[0-9a-f]{6,}|^\d+$', value))
                elif attr == 'name':
                    dna.name = value
                elif attr == 'placeholder':
                    dna.placeholder = value
                elif attr == 'aria-label':
                    dna.aria_label = value
                elif attr == 'type':
                    dna.element_type = value
                elif attr == 'role':
                    dna.role = value
                elif attr == 'class':
                    dna.has_framework_classes = bool(re.search(
                        r'ng-|_ng|mat-|css-|sc-|jsx-|svelte-', value
                    ))

        # Extract text content
        text_match = re.search(r'>([^<]+)<', element_html)
        if text_match:
            dna.text_content = text_match.group(1).strip()
            dna.visible_text = dna.text_content

        # Determine behavioral properties
        dna.is_clickable = dna.element_tag in ('button', 'a', 'input') or \
                          dna.role in ('button', 'link', 'tab')
        dna.is_editable = dna.element_tag in ('input', 'textarea', 'select') or \
                         dna.role in ('textbox', 'combobox')
        dna.triggers_submit = dna.element_type == 'submit' or \
                            (dna.element_tag == 'button' and 'submit' in element_html.lower())

        # Identify semantic type
        dna.semantic_type, _ = SemanticPatterns.identify_semantic_type(dna)

        # Set test attribute flag
        dna.has_test_attribute = dna.test_id is not None

        return dna

    def find_by_intent(
        self,
        intent: str,
        page_html: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Find elements that match a given intent.

        Args:
            intent: Human intent like "enter username" or "click login"
            page_html: Full page HTML for context
            candidates: List of candidate elements with their selectors

        Returns:
            Reordered candidates with semantic matches first
        """
        # Resolve intent to semantic type
        target_type, intent_confidence = IntentResolver.resolve_intent(intent)

        if not target_type:
            return candidates

        # Score each candidate
        scored = []
        for candidate in candidates:
            selector = candidate.get("selector", "")
            element_html = self._find_element_html(selector, page_html)

            if element_html:
                dna = self.extract_element_dna(element_html)

                # Check if semantic type matches
                if dna.semantic_type == target_type:
                    # Boost confidence for semantic match
                    new_score = candidate.get("score", 0.5) * 1.5
                    new_score = min(new_score, 1.0)
                    scored.append({**candidate, "score": new_score, "semantic_match": True})
                else:
                    scored.append({**candidate, "semantic_match": False})
            else:
                scored.append({**candidate, "semantic_match": False})

        # Sort by score, with semantic matches first
        scored.sort(key=lambda x: (x.get("semantic_match", False), x.get("score", 0)), reverse=True)

        return scored

    def analyze_page(self, url: str, title: str, html: str) -> Dict[str, Any]:
        """
        Analyze a page to understand its context and elements.
        """
        self.url = url

        # Identify page type
        self.page_context, page_confidence = SemanticPatterns.identify_page_type(url, title, [])

        # Find and analyze key elements
        elements_found = {}

        # Look for common interactive elements
        input_pattern = r'<input[^>]*>'
        button_pattern = r'<button[^>]*>.*?</button>'
        link_pattern = r'<a[^>]*>.*?</a>'

        for match in re.finditer(input_pattern, html, re.I | re.S):
            dna = self.extract_element_dna(match.group())
            if dna.semantic_type != SemanticType.UNKNOWN:
                elements_found[dna.semantic_type.value] = {
                    "found": True,
                    "test_id": dna.test_id,
                    "element_id": dna.element_id,
                }

        for match in re.finditer(button_pattern, html, re.I | re.S):
            dna = self.extract_element_dna(match.group())
            if dna.semantic_type != SemanticType.UNKNOWN:
                elements_found[dna.semantic_type.value] = {
                    "found": True,
                    "test_id": dna.test_id,
                    "text": dna.text_content,
                }

        return {
            "url": url,
            "page_type": self.page_context.value if self.page_context else "unknown",
            "page_confidence": page_confidence,
            "elements_found": elements_found,
            "is_login_page": self.page_context == PageType.LOGIN,
            "is_checkout": self.page_context == PageType.CHECKOUT,
        }

    def _find_element_html(self, selector: str, page_html: str) -> Optional[str]:
        """
        Find an element's HTML by its selector.
        This is a simplified implementation - real one would use proper DOM parsing.
        """
        # Handle data-test selectors
        if selector.startswith('[data-test'):
            match = re.search(r'\[data-test[^=]*=["\']([^"\']+)["\']', selector)
            if match:
                value = match.group(1)
                pattern = rf'<[^>]*data-test[^=]*=["\']?{re.escape(value)}["\']?[^>]*>.*?(?:</\w+>)?'
                element_match = re.search(pattern, page_html, re.I | re.S)
                if element_match:
                    return element_match.group()

        # Handle ID selectors
        elif selector.startswith('#'):
            id_value = selector[1:]
            pattern = rf'<[^>]*\bid=["\']?{re.escape(id_value)}["\']?[^>]*>.*?(?:</\w+>)?'
            element_match = re.search(pattern, page_html, re.I | re.S)
            if element_match:
                return element_match.group()

        return None

    def get_smart_alternatives(
        self,
        element_key: str,
        primary_selector: str,
        page_html: str
    ) -> List[Dict[str, Any]]:
        """
        Generate smart alternative selectors based on semantic understanding.
        """
        alternatives = []

        # Get DNA for the element
        element_html = self._find_element_html(primary_selector, page_html)
        if not element_html:
            return alternatives

        dna = self.extract_element_dna(element_html)

        # Generate alternatives based on DNA
        if dna.test_id:
            alternatives.append({
                "selector": f'[data-test="{dna.test_id}"]',
                "type": "css",
                "confidence": PredictiveConfidence.adjust_confidence(0.98, dna.test_id, "data-testid"),
                "source": "semantic_dna"
            })

        if dna.element_id and not dna.has_dynamic_id:
            alternatives.append({
                "selector": f'#{dna.element_id}',
                "type": "css",
                "confidence": PredictiveConfidence.adjust_confidence(0.90, dna.element_id, "id"),
                "source": "semantic_dna"
            })

        if dna.name:
            alternatives.append({
                "selector": f'[name="{dna.name}"]',
                "type": "css",
                "confidence": PredictiveConfidence.adjust_confidence(0.85, dna.name, "name"),
                "source": "semantic_dna"
            })

        if dna.aria_label:
            alternatives.append({
                "selector": f'[aria-label="{dna.aria_label}"]',
                "type": "css",
                "confidence": PredictiveConfidence.adjust_confidence(0.85, dna.aria_label, "aria-label"),
                "source": "semantic_dna"
            })

        if dna.placeholder:
            alternatives.append({
                "selector": f'[placeholder="{dna.placeholder}"]',
                "type": "css",
                "confidence": PredictiveConfidence.adjust_confidence(0.75, dna.placeholder, "placeholder"),
                "source": "semantic_dna"
            })

        # Text-based selector for buttons
        if dna.text_content and dna.is_clickable:
            alternatives.append({
                "selector": f'text={dna.text_content}',
                "type": "text",
                "confidence": PredictiveConfidence.adjust_confidence(0.70, dna.text_content, "text_content"),
                "source": "semantic_dna"
            })

        # Sort by confidence
        alternatives.sort(key=lambda x: x["confidence"], reverse=True)

        return alternatives


# ==================== Singleton Instance ====================

_sei_instance: Optional[SemanticElementIntelligence] = None

def get_semantic_intelligence() -> SemanticElementIntelligence:
    """Get the singleton SEI instance."""
    global _sei_instance
    if _sei_instance is None:
        _sei_instance = SemanticElementIntelligence()
    return _sei_instance
