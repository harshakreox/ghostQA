"""
Selector Service

The intelligent selector resolution system that implements the
5-tier decision pipeline to find the best selector for any element.

Tier Order:
1. Knowledge Base (learned selectors) - O(1) lookup
2. Framework Rules (pre-seeded patterns) - O(1) lookup
3. Heuristic Engine (smart guessing) - O(n) DOM scan
4. AI Decision (LLM-powered) - External call, but learns for future
5. Graceful Degradation (fallback strategies)
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable, Set
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher

from ..knowledge.knowledge_index import KnowledgeIndex, SelectorMatch
from ..knowledge.framework_selectors import FRAMEWORK_SELECTORS, UNIVERSAL_PATTERNS
from ..knowledge.learning_engine import LearningEngine
from .element_intelligence import (
    get_semantic_intelligence,
    SemanticElementIntelligence,
    IntentResolver,
    PredictiveConfidence,
    SemanticType,
    ElementDNA
)

# Configure logging
logger = logging.getLogger(__name__)


# ==================== Intelligent Keyword Matching ====================

# Common synonyms and variations for UI elements
KEYWORD_SYNONYMS = {
    # Authentication
    "login": ["log in", "log-in", "signin", "sign in", "sign-in", "authenticate", "enter"],
    "logout": ["log out", "log-out", "signout", "sign out", "sign-out", "exit"],
    "register": ["signup", "sign up", "sign-up", "create account", "join", "enroll"],
    "password": ["pwd", "pass", "secret", "credential"],
    "username": ["user", "userid", "user id", "user-id", "email", "login id", "account"],
    "email": ["e-mail", "mail", "email address"],

    # Actions
    "submit": ["send", "confirm", "done", "ok", "go", "continue", "proceed", "next"],
    "cancel": ["close", "dismiss", "abort", "back", "nevermind"],
    "save": ["store", "keep", "apply", "update"],
    "delete": ["remove", "trash", "erase", "clear"],
    "edit": ["modify", "change", "update", "revise"],
    "add": ["create", "new", "plus", "insert"],
    "search": ["find", "lookup", "look up", "query", "filter"],
    "refresh": ["reload", "sync", "update"],

    # Navigation
    "home": ["main", "dashboard", "start", "index"],
    "back": ["previous", "return", "go back"],
    "next": ["forward", "continue", "proceed", "advance"],
    "menu": ["nav", "navigation", "hamburger", "sidebar"],

    # Common elements
    "button": ["btn", "cta", "action"],
    "input": ["field", "textbox", "text box", "entry"],
    "checkbox": ["check", "tick", "toggle"],
    "dropdown": ["select", "combo", "combobox", "picker", "list"],
    "link": ["anchor", "href", "url"],
    "modal": ["dialog", "popup", "overlay", "lightbox"],
    "tab": ["panel", "section"],
    "card": ["tile", "box", "container"],

    # E-commerce
    "cart": ["basket", "bag", "shopping cart"],
    "checkout": ["check out", "pay", "purchase", "buy"],
    "product": ["item", "goods", "merchandise"],
    "price": ["cost", "amount", "total"],
    "quantity": ["qty", "count", "amount"],
}

# Build reverse lookup: synonym -> canonical form
SYNONYM_TO_CANONICAL = {}
for canonical, synonyms in KEYWORD_SYNONYMS.items():
    SYNONYM_TO_CANONICAL[canonical.lower()] = canonical.lower()
    for syn in synonyms:
        SYNONYM_TO_CANONICAL[syn.lower()] = canonical.lower()


def normalize_text(text: str) -> str:
    """Normalize text for comparison - lowercase, remove extra spaces, handle variations"""
    text = text.lower().strip()
    # Replace common separators with space
    text = re.sub(r'[-_]', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text


def get_keyword_variations(keyword: str) -> Set[str]:
    """Get all variations of a keyword including synonyms"""
    variations = set()
    keyword_lower = keyword.lower()

    # Add the original keyword
    variations.add(keyword_lower)

    # Add with different separators
    variations.add(keyword_lower.replace(' ', '-'))
    variations.add(keyword_lower.replace(' ', '_'))
    variations.add(keyword_lower.replace('-', ' '))
    variations.add(keyword_lower.replace('_', ' '))
    variations.add(keyword_lower.replace('-', ''))
    variations.add(keyword_lower.replace('_', ''))
    variations.add(keyword_lower.replace(' ', ''))

    # Add synonyms
    if keyword_lower in SYNONYM_TO_CANONICAL:
        canonical = SYNONYM_TO_CANONICAL[keyword_lower]
        # Add all synonyms of this canonical form
        if canonical in KEYWORD_SYNONYMS:
            for syn in KEYWORD_SYNONYMS[canonical]:
                variations.add(syn.lower())
                variations.add(syn.lower().replace(' ', '-'))
                variations.add(syn.lower().replace(' ', '_'))
                variations.add(syn.lower().replace(' ', ''))
        variations.add(canonical)

    # Check if this keyword is a synonym of something else
    for canonical, synonyms in KEYWORD_SYNONYMS.items():
        if keyword_lower == canonical or keyword_lower in [s.lower() for s in synonyms]:
            variations.add(canonical)
            for syn in synonyms:
                variations.add(syn.lower())

    return variations


def fuzzy_match(s1: str, s2: str, threshold: float = 0.8) -> Tuple[bool, float]:
    """
    Check if two strings are similar using fuzzy matching.
    Returns (is_match, similarity_score)
    """
    s1_norm = normalize_text(s1)
    s2_norm = normalize_text(s2)

    # Exact match
    if s1_norm == s2_norm:
        return True, 1.0

    # Check if one contains the other
    if s1_norm in s2_norm or s2_norm in s1_norm:
        shorter = min(len(s1_norm), len(s2_norm))
        longer = max(len(s1_norm), len(s2_norm))
        return True, shorter / longer

    # Use SequenceMatcher for fuzzy comparison
    ratio = SequenceMatcher(None, s1_norm, s2_norm).ratio()
    return ratio >= threshold, ratio


def text_contains_keyword(text: str, keyword: str, fuzzy: bool = True) -> Tuple[bool, float]:
    """
    Check if text contains a keyword or its variations.
    Returns (found, confidence_score)

    Scoring hierarchy:
    - 1.0: Original keyword is an exact match for the text
    - 0.98: Text contains the original keyword exactly
    - 0.95: Text contains a variation of the keyword
    - 0.85: Word boundary match
    - <0.85: Fuzzy match
    """
    text_norm = normalize_text(text)
    keyword_norm = normalize_text(keyword)
    variations = get_keyword_variations(keyword)

    # Highest priority: exact match of original keyword to text
    if text_norm == keyword_norm:
        return True, 1.0

    # Second priority: text contains original keyword exactly
    if keyword_norm in text_norm:
        return True, 0.98

    best_score = 0.0

    for variation in variations:
        # Skip if this is the original keyword (already checked above)
        if variation == keyword_norm:
            continue

        # Word boundary match - variation must be a complete word
        # This prevents "user" from matching "VerifiedUserIcon"
        pattern = rf'\b{re.escape(variation)}\b'
        if re.search(pattern, text_norm, re.I):
            return True, 0.90

        # Only allow substring match if variation is majority of text
        if variation in text_norm and len(variation) >= len(text_norm) * 0.5:
            return True, 0.85

        # Fuzzy match if enabled
        if fuzzy:
            for word in text_norm.split():
                match, score = fuzzy_match(variation, word)
                if match and score > best_score:
                    best_score = score

    if best_score >= 0.8:
        return True, best_score

    return False, best_score


class ResolutionTier(Enum):
    """Which tier resolved the selector"""
    KNOWLEDGE_BASE = "knowledge_base"
    FRAMEWORK_RULES = "framework_rules"
    HEURISTICS = "heuristics"
    AI_DECISION = "ai_decision"
    VISUAL_INTELLIGENCE = "visual_intelligence"  # Screenshot-based AI analysis
    FALLBACK = "fallback"
    FAILED = "failed"


@dataclass
class SelectorResult:
    """Result of selector resolution"""
    selector: str
    selector_type: str  # css, xpath, text, label, placeholder, role
    confidence: float
    tier: ResolutionTier
    alternatives: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class SelectorService:
    """
    Intelligent selector resolution service.

    This is the "brain" that decides how to locate elements.
    It tries multiple strategies in order of reliability and
    speed, learning from every interaction.
    """

    # Minimum confidence to use a selector
    MIN_CONFIDENCE = 0.5

    # AI timeout in seconds
    AI_TIMEOUT = 5.0

    def __init__(
        self,
        knowledge_index: KnowledgeIndex,
        learning_engine: Optional[LearningEngine] = None,
        detected_framework: Optional[str] = None,
        ai_callback: Optional[Callable] = None
    ):
        """
        Initialize selector service.

        Args:
            knowledge_index: KnowledgeIndex for learned selectors
            learning_engine: LearningEngine for recording results
            detected_framework: Detected UI framework (mui, bootstrap, etc.)
            ai_callback: Optional callback for AI decisions
        """
        self.knowledge_index = knowledge_index
        self.learning_engine = learning_engine
        self.detected_framework = detected_framework
        self.ai_callback = ai_callback

        # Semantic Element Intelligence for advanced element understanding
        self.semantic_intelligence = get_semantic_intelligence()

        # Stats tracking
        self._tier_hits: Dict[ResolutionTier, int] = {tier: 0 for tier in ResolutionTier}
        self._total_resolutions = 0
        self._semantic_assists = 0  # Track how often SEI helped

    def set_framework(self, framework: str):
        """Set the detected framework"""
        self.detected_framework = framework

    def set_ai_callback(self, callback: Callable):
        """Set the AI decision callback"""
        self.ai_callback = callback

    def resolve(
        self,
        intent: str,
        domain: str,
        page: str,
        page_html: Optional[str] = None,
        dom_elements: Optional[List[Dict]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SelectorResult:
        """
        Resolve an element intent to a selector.

        This is the main entry point. It tries each tier in order
        until it finds a suitable selector.

        Priority Order:
        1. Knowledge Base (learned selectors) - O(1) lookup
        2. Heuristics (when HTML available) - finds actual elements in page
        3. Framework Rules (generic patterns) - pre-seeded patterns
        4. AI Decision (LLM-powered) - External call
        5. Fallback (generous matching)

        Args:
            intent: What element to find (e.g., "login button", "email input")
            domain: Website domain
            page: Page path/identifier
            page_html: Optional HTML for heuristic analysis
            dom_elements: Optional DOM element list
            context: Additional context (form name, section, etc.)

        Returns:
            SelectorResult with best selector and metadata
        """
        self._total_resolutions += 1
        context = context or {}

        # Normalize intent
        intent_normalized = self._normalize_intent(intent)

        # Tier 1: Knowledge Base (always first - learned selectors are best)
        result = self._try_knowledge_base(intent_normalized, domain, page)
        if result:
            self._tier_hits[ResolutionTier.KNOWLEDGE_BASE] += 1
            return result

        # When we have actual page HTML, try heuristics BEFORE framework rules
        # because heuristics can find the actual elements in the page
        if page_html or dom_elements:
            # Try Semantic Element Intelligence first - understands element PURPOSE
            semantic_result = self._try_semantic_resolution(intent, page_html, dom_elements, context)
            if semantic_result and semantic_result.confidence >= 0.7:
                logger.info(f"SEI resolved '{intent}' with confidence {semantic_result.confidence:.2f}")
                self._tier_hits[ResolutionTier.HEURISTICS] += 1
                return semantic_result

            # Tier 2: Heuristic Engine (analyze actual page content)
            # Pass original intent (before normalization) for better matching
            result = self._try_heuristics(intent, page_html, dom_elements, context)
            if result and result.confidence >= 0.6:
                # High confidence from heuristics - use it
                self._tier_hits[ResolutionTier.HEURISTICS] += 1
                return result

            # Tier 3: Framework Rules (generic patterns)
            framework_result = self._try_framework_rules(intent_normalized, context)

            # If we have both, prefer the heuristic result if it has test attributes
            if result and framework_result:
                # Prefer heuristics if it found test attributes (data-test, data-testid, etc.)
                if any(attr in result.selector for attr in ['data-test', 'data-testid', 'data-cy', 'data-qa']):
                    self._tier_hits[ResolutionTier.HEURISTICS] += 1
                    return result
                # Otherwise use framework result if higher confidence
                if framework_result.confidence > result.confidence:
                    self._tier_hits[ResolutionTier.FRAMEWORK_RULES] += 1
                    return framework_result
                self._tier_hits[ResolutionTier.HEURISTICS] += 1
                return result
            elif result:
                self._tier_hits[ResolutionTier.HEURISTICS] += 1
                return result
            elif framework_result:
                self._tier_hits[ResolutionTier.FRAMEWORK_RULES] += 1
                return framework_result
        else:
            # No page HTML available - try framework rules first
            # Tier 2: Framework Rules
            result = self._try_framework_rules(intent_normalized, context)
            if result:
                self._tier_hits[ResolutionTier.FRAMEWORK_RULES] += 1
                return result

            # Tier 3: Heuristic Engine (won't have much to work with)
            # Pass original intent for better matching
            result = self._try_heuristics(intent, page_html, dom_elements, context)
            if result:
                self._tier_hits[ResolutionTier.HEURISTICS] += 1
                return result

        # Tier 4: AI Decision
        if self.ai_callback:
            result = self._try_ai_decision(intent, page_html, dom_elements, context)
            if result:
                self._tier_hits[ResolutionTier.AI_DECISION] += 1
                # Record for future use
                if self.learning_engine:
                    self.learning_engine.record_element_mapping(
                        domain=domain,
                        page=page,
                        element_key=intent_normalized,
                        selectors=[{
                            "selector": result.selector,
                            "type": result.selector_type,
                            "confidence": result.confidence
                        }],
                        element_attributes=result.metadata.get("attributes", {}),
                        ai_assisted=True
                    )
                return result

        # Tier 5: Graceful Degradation
        logger.info(f"Falling back to tier 5 for intent '{intent}'")
        result = self._try_fallback(intent_normalized, context)
        if result:
            logger.info(f"Fallback result: {result.selector}")
            self._tier_hits[ResolutionTier.FALLBACK] += 1
            return result

        # Failed
        self._tier_hits[ResolutionTier.FAILED] += 1
        return SelectorResult(
            selector="",
            selector_type="none",
            confidence=0.0,
            tier=ResolutionTier.FAILED,
            alternatives=[],
            metadata={"error": "Could not resolve selector", "intent": intent}
        )

    # ==================== Semantic Intelligence Integration ====================

    def _try_semantic_resolution(
        self,
        intent: str,
        page_html: Optional[str],
        dom_elements: Optional[List[Dict]],
        context: Dict[str, Any]
    ) -> Optional[SelectorResult]:
        """
        Use Semantic Element Intelligence for advanced element resolution.

        This understands the PURPOSE of elements, not just their attributes.
        For example: "enter username" -> finds USERNAME_INPUT semantic type
        """
        try:
            # First, resolve the intent to a semantic type
            semantic_type, intent_confidence = IntentResolver.resolve_intent(intent)

            if not semantic_type or intent_confidence < 0.5:
                logger.debug(f"SEI: No semantic type matched for '{intent}'")
                return None

            logger.info(f"SEI: Intent '{intent}' -> {semantic_type.value} (confidence: {intent_confidence:.2f})")

            # If we have page HTML, use SEI to find matching elements
            if page_html:
                # Analyze the page context
                url = context.get("url", "")
                title = context.get("title", "")
                page_analysis = self.semantic_intelligence.analyze_page(url, title, page_html)

                logger.debug(f"SEI: Page type: {page_analysis.get('page_type')}")

                # Look for elements matching the semantic type in the HTML
                candidates = self._find_semantic_candidates(semantic_type, page_html, page_analysis)

                if candidates:
                    self._semantic_assists += 1
                    best = candidates[0]

                    # Adjust confidence using predictive confidence
                    adjusted_confidence = PredictiveConfidence.adjust_confidence(
                        best["confidence"],
                        best["selector"],
                        best.get("selector_type", "css")
                    )

                    return SelectorResult(
                        selector=best["selector"],
                        selector_type=best.get("type", "css"),
                        confidence=adjusted_confidence,
                        tier=ResolutionTier.HEURISTICS,  # Counts as heuristics
                        alternatives=candidates[1:5],
                        metadata={
                            "semantic_type": semantic_type.value,
                            "intent_confidence": intent_confidence,
                            "page_type": page_analysis.get("page_type"),
                            "source": "semantic_intelligence"
                        }
                    )

            return None

        except Exception as e:
            logger.warning(f"SEI resolution error: {e}")
            return None

    def _find_semantic_candidates(
        self,
        semantic_type: SemanticType,
        page_html: str,
        page_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find elements matching a semantic type in the page HTML.
        """
        candidates = []

        # Define semantic type to attribute patterns mapping
        SEMANTIC_SEARCH_PATTERNS = {
            SemanticType.USERNAME_INPUT: {
                "test_attrs": ["username", "user-name", "user_name", "login-username", "email", "userid"],
                "names": ["username", "user", "email", "login"],
                "ids": ["username", "user-name", "user_name", "email", "login-email"],
                "placeholders": ["username", "user name", "email", "enter username"],
                "types": ["text", "email"],
                "autocomplete": ["username", "email"],
            },
            SemanticType.PASSWORD_INPUT: {
                "test_attrs": ["password", "pass", "pwd", "login-password"],
                "names": ["password", "pass", "pwd"],
                "ids": ["password", "pass", "pwd", "login-password"],
                "placeholders": ["password", "enter password"],
                "types": ["password"],
                "autocomplete": ["current-password", "new-password"],
            },
            SemanticType.LOGIN_BUTTON: {
                "test_attrs": ["login", "login-button", "signin", "sign-in", "submit-login"],
                "ids": ["login", "login-button", "signin", "sign-in", "btnLogin"],
                "values": ["log in", "login", "sign in", "signin", "submit"],
                "text_content": ["log in", "login", "sign in", "signin"],
            },
            SemanticType.SEARCH_INPUT: {
                "test_attrs": ["search", "search-input", "search-box", "query"],
                "names": ["search", "query", "q", "s"],
                "ids": ["search", "search-input", "searchbox"],
                "placeholders": ["search", "find", "look for"],
                "types": ["search", "text"],
                "roles": ["searchbox"],
            },
            SemanticType.ADD_TO_CART: {
                "test_attrs": ["add-to-cart", "addtocart", "add-cart", "buy-now"],
                "ids": ["add-to-cart", "addToCart", "buyNow"],
                "text_content": ["add to cart", "add to bag", "buy now"],
                "classes": ["add-to-cart", "addToCart", "buy-button"],
            },
            SemanticType.CHECKOUT_BUTTON: {
                "test_attrs": ["checkout", "checkout-button", "proceed-checkout"],
                "ids": ["checkout", "checkoutButton"],
                "text_content": ["checkout", "proceed to checkout", "check out"],
            },
            SemanticType.SUBMIT_BUTTON: {
                "types": ["submit"],
                "text_content": ["submit", "send", "save", "continue", "next", "done"],
            },
            SemanticType.CLOSE_BUTTON: {
                "test_attrs": ["close", "close-button", "dismiss"],
                "aria_labels": ["close", "dismiss", "close dialog"],
                "text_content": ["×", "x", "close"],
                "classes": ["close", "close-button", "modal-close"],
            },
        }

        patterns = SEMANTIC_SEARCH_PATTERNS.get(semantic_type, {})
        if not patterns:
            return candidates

        # Search for test attributes first (highest priority)
        for test_attr in patterns.get("test_attrs", []):
            for attr_name in ["data-testid", "data-test", "data-cy", "data-qa"]:
                pattern = rf'{attr_name}=["\']([^"\']*{re.escape(test_attr)}[^"\']*)["\']'
                for match in re.finditer(pattern, page_html, re.I):
                    attr_value = match.group(1)
                    candidates.append({
                        "selector": f'[{attr_name}="{attr_value}"]',
                        "type": "css",
                        "confidence": 0.98,
                        "method": "semantic_test_attr",
                        "semantic_type": semantic_type.value
                    })

        # Search by name attribute
        for name in patterns.get("names", []):
            pattern = rf'name=["\']([^"\']*{re.escape(name)}[^"\']*)["\']'
            for match in re.finditer(pattern, page_html, re.I):
                attr_value = match.group(1)
                candidates.append({
                    "selector": f'[name="{attr_value}"]',
                    "type": "css",
                    "confidence": 0.88,
                    "method": "semantic_name",
                    "semantic_type": semantic_type.value
                })

        # Search by id attribute
        for id_val in patterns.get("ids", []):
            pattern = rf'\bid=["\']([^"\']*{re.escape(id_val)}[^"\']*)["\']'
            for match in re.finditer(pattern, page_html, re.I):
                attr_value = match.group(1)
                candidates.append({
                    "selector": f'#{attr_value}',
                    "type": "css",
                    "confidence": 0.92,
                    "method": "semantic_id",
                    "semantic_type": semantic_type.value
                })

        # Search by placeholder
        for placeholder in patterns.get("placeholders", []):
            pattern = rf'placeholder=["\']([^"\']*{re.escape(placeholder)}[^"\']*)["\']'
            for match in re.finditer(pattern, page_html, re.I):
                attr_value = match.group(1)
                candidates.append({
                    "selector": f'[placeholder="{attr_value}"]',
                    "type": "css",
                    "confidence": 0.82,
                    "method": "semantic_placeholder",
                    "semantic_type": semantic_type.value
                })

        # Search by input type (for password, search, etc.)
        for input_type in patterns.get("types", []):
            pattern = rf'type=["\']({re.escape(input_type)})["\']'
            if re.search(pattern, page_html, re.I):
                candidates.append({
                    "selector": f'input[type="{input_type}"]',
                    "type": "css",
                    "confidence": 0.75 if input_type != "password" else 0.95,  # Password is very specific
                    "method": "semantic_type",
                    "semantic_type": semantic_type.value
                })

        # Search by text content for buttons
        for text in patterns.get("text_content", []):
            # Button text
            pattern = rf'<button[^>]*>([^<]*{re.escape(text)}[^<]*)</button>'
            for match in re.finditer(pattern, page_html, re.I):
                text_content = match.group(1).strip()
                candidates.append({
                    "selector": f'button:has-text("{text_content}")',
                    "type": "css",
                    "confidence": 0.85,
                    "method": "semantic_button_text",
                    "semantic_type": semantic_type.value
                })

            # Input value
            pattern = rf'value=["\']([^"\']*{re.escape(text)}[^"\']*)["\']'
            for match in re.finditer(pattern, page_html, re.I):
                value = match.group(1)
                candidates.append({
                    "selector": f'[value="{value}"]',
                    "type": "css",
                    "confidence": 0.80,
                    "method": "semantic_value",
                    "semantic_type": semantic_type.value
                })

        # Remove duplicates, keeping highest confidence
        seen = {}
        for c in candidates:
            key = c["selector"]
            if key not in seen or seen[key]["confidence"] < c["confidence"]:
                seen[key] = c

        result = list(seen.values())
        result.sort(key=lambda x: x["confidence"], reverse=True)

        return result

    # ==================== Tier 1: Knowledge Base ====================

    def _try_knowledge_base(
        self,
        intent: str,
        domain: str,
        page: str
    ) -> Optional[SelectorResult]:
        """Try to find selector from learned knowledge"""
        # Direct lookup with exact domain/page
        knowledge = self.knowledge_index.lookup(domain, page, intent)
        if knowledge and knowledge.selectors:
            best = max(knowledge.selectors, key=lambda s: s.confidence)
            if best.confidence >= self.MIN_CONFIDENCE:
                logger.info(f"KB direct hit: '{intent}' -> '{best.value}'")
                return SelectorResult(
                    selector=best.value,
                    selector_type=best.selector_type,
                    confidence=best.confidence,
                    tier=ResolutionTier.KNOWLEDGE_BASE,
                    alternatives=[
                        {"selector": s.value, "type": s.selector_type, "confidence": s.confidence}
                        for s in knowledge.selectors if s != best
                    ],
                    metadata={"element_key": intent}
                )

        # Fuzzy search by intent with domain/page filtering
        matches = self.knowledge_index.find_by_intent(intent, domain, page)
        if matches:
            best_match = matches[0]
            if best_match.confidence >= self.MIN_CONFIDENCE:
                logger.info(f"KB fuzzy hit: '{intent}' -> '{best_match.selector}' (key: {best_match.element_key})")
                return SelectorResult(
                    selector=best_match.selector,
                    selector_type=best_match.selector_type,
                    confidence=best_match.confidence,
                    tier=ResolutionTier.KNOWLEDGE_BASE,
                    alternatives=[
                        {"selector": m.selector, "type": m.selector_type, "confidence": m.confidence}
                        for m in matches[1:5]
                    ],
                    metadata={"matched_key": best_match.element_key}
                )

        # DISABLED: Cross-domain matching pollutes selectors between projects
        # (Sauce Demo selectors were returned for Foundry Test - BAD!)
        # Keeping selectors domain-isolated for now
        pass  # Skip global search

        return None

    # ==================== Tier 2: Framework Rules ====================

    def _try_framework_rules(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> Optional[SelectorResult]:
        """Try to find selector from framework patterns"""
        selectors = []

        # Check framework-specific patterns
        if self.detected_framework and self.detected_framework in FRAMEWORK_SELECTORS:
            framework_patterns = FRAMEWORK_SELECTORS[self.detected_framework]
            selectors.extend(
                self._match_framework_patterns(intent, framework_patterns)
            )

        # Check universal patterns
        selectors.extend(self._match_universal_patterns(intent, context))

        if selectors:
            # Sort by relevance
            selectors.sort(key=lambda x: x["relevance"], reverse=True)
            best = selectors[0]

            return SelectorResult(
                selector=best["selector"],
                selector_type=best.get("type", "css"),
                confidence=0.75,  # Framework patterns are moderately confident
                tier=ResolutionTier.FRAMEWORK_RULES,
                alternatives=selectors[1:5],
                metadata={"pattern_source": best.get("source", "universal")}
            )

        return None

    def _match_framework_patterns(
        self,
        intent: str,
        patterns: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """Match intent against framework patterns"""
        matches = []
        intent_lower = intent.lower()

        # Common element type keywords
        element_types = {
            "button": ["button", "btn", "submit"],
            "input": ["input", "field", "text", "textbox"],
            "select": ["select", "dropdown", "combo"],
            "checkbox": ["checkbox", "check"],
            "radio": ["radio"],
            "switch": ["switch", "toggle"],
            "dialog": ["dialog", "modal", "popup"],
            "menu": ["menu"],
            "tab": ["tab"],
            "table": ["table", "grid"],
            "date_picker": ["date", "calendar"],
            "autocomplete": ["autocomplete", "typeahead"]
        }

        # Find matching element type
        matched_type = None
        for elem_type, keywords in element_types.items():
            if any(kw in intent_lower for kw in keywords):
                matched_type = elem_type
                break

        if matched_type and matched_type in patterns:
            for selector in patterns[matched_type]:
                matches.append({
                    "selector": selector,
                    "type": "css",
                    "relevance": 0.8,
                    "source": self.detected_framework
                })

        return matches

    def _match_universal_patterns(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Match intent against universal patterns"""
        matches = []
        intent_lower = intent.lower()

        # Check common actions
        if "common_actions" in UNIVERSAL_PATTERNS:
            for action, selectors in UNIVERSAL_PATTERNS["common_actions"].items():
                if action in intent_lower:
                    for sel in selectors:
                        matches.append({
                            "selector": sel,
                            "type": "css",
                            "relevance": 0.7,
                            "source": "universal_action"
                        })

        # Check button patterns
        if any(kw in intent_lower for kw in ["button", "btn", "click"]):
            if "buttons" in UNIVERSAL_PATTERNS:
                # By text
                for pattern in UNIVERSAL_PATTERNS["buttons"].get("by_text", []):
                    matches.append({
                        "selector": pattern,
                        "type": "css",
                        "relevance": 0.6,
                        "source": "universal_button"
                    })

        # Check input patterns
        if any(kw in intent_lower for kw in ["input", "field", "enter", "type"]):
            if "inputs" in UNIVERSAL_PATTERNS:
                for pattern in UNIVERSAL_PATTERNS["inputs"].get("by_type", {}).values():
                    matches.append({
                        "selector": pattern,
                        "type": "css",
                        "relevance": 0.6,
                        "source": "universal_input"
                    })

        # Check form field patterns
        if "form_elements" in UNIVERSAL_PATTERNS:
            for field_name, selectors in UNIVERSAL_PATTERNS["form_elements"].items():
                if field_name.replace("_", " ") in intent_lower or field_name in intent_lower:
                    for sel in selectors:
                        matches.append({
                            "selector": sel,
                            "type": "css",
                            "relevance": 0.75,
                            "source": "universal_form"
                        })

        return matches

    # ==================== Tier 3: Heuristics ====================

    def _try_heuristics(
        self,
        intent: str,
        page_html: Optional[str],
        dom_elements: Optional[List[Dict]],
        context: Dict[str, Any]
    ) -> Optional[SelectorResult]:
        """Try heuristic-based selector generation"""
        candidates = []

        # Extract keywords from intent
        keywords = self._extract_keywords(intent)
        logger.debug(f"Heuristics for '{intent}': keywords={keywords}, has_html={page_html is not None and len(page_html) > 0}, has_dom={dom_elements is not None}")

        # Try DOM elements if available
        if dom_elements:
            candidates.extend(
                self._heuristic_from_dom(keywords, dom_elements, context)
            )

        # Try HTML parsing if available - pass original intent for compound matching
        if page_html and not candidates:
            html_candidates = self._heuristic_from_html(keywords, page_html, context, original_intent=intent)
            logger.debug(f"HTML heuristics found {len(html_candidates)} candidates: {[c.get('selector') for c in html_candidates[:5]]}")
            candidates.extend(html_candidates)

        if candidates:
            # Sort by score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            best = candidates[0]

            if best["score"] >= 0.5:
                # Use actual score for confidence - test attributes should get high confidence
                method = best.get("method", "unknown")
                is_test_attr = method in ("html_testid", "html_datatest", "html_datacy", "html_dataqa")

                # Test attributes keep their high scores, others capped at 0.8
                if is_test_attr:
                    confidence = best["score"]
                else:
                    confidence = min(0.8, best["score"])

                return SelectorResult(
                    selector=best["selector"],
                    selector_type=best.get("type", "css"),
                    confidence=confidence,
                    tier=ResolutionTier.HEURISTICS,
                    alternatives=candidates[1:8],
                    metadata={"heuristic_method": method}
                )

        return None

    def _extract_keywords(self, intent: str) -> List[str]:
        """Extract meaningful keywords from intent"""
        # Remove common words
        stop_words = {
            "the", "a", "an", "to", "for", "of", "on", "in", "and", "or",
            "click", "type", "enter", "select", "find", "locate", "get"
        }

        # Split on spaces, underscores, and hyphens to handle normalized intents
        # For example: "login_button" -> ["login", "button"]
        # And "login-button" -> ["login", "button"]
        intent_split = re.sub(r'[-_]', ' ', intent.lower())
        words = re.findall(r'\w+', intent_split)
        return [w for w in words if w not in stop_words and len(w) > 1]

    def _heuristic_from_dom(
        self,
        keywords: List[str],
        dom_elements: List[Dict],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate selectors from DOM elements using heuristics"""
        candidates = []

        for elem in dom_elements:
            score = self._score_element(elem, keywords, context)
            if score > 0.3:
                selectors = self._generate_selectors_for_element(elem)
                for sel in selectors:
                    sel["score"] = score * sel.get("confidence", 0.5)
                    candidates.append(sel)

        return candidates

    def _score_element(
        self,
        elem: Dict,
        keywords: List[str],
        context: Dict[str, Any]
    ) -> float:
        """Score an element based on keyword match"""
        score = 0.0
        attrs = elem.get("attributes", {})
        text = elem.get("textContent", "").lower()
        tag = elem.get("tagName", "").lower()

        # High-priority test attributes
        test_attrs = {"data-testid", "data-test", "data-cy", "data-qa", "data-automation-id"}
        # Standard identification attributes
        id_attrs = {"id", "name"}
        # Accessibility and semantic attributes
        semantic_attrs = {"aria-label", "title", "placeholder", "alt", "role"}

        for keyword in keywords:
            kw_lower = keyword.lower()

            # Text content match
            if kw_lower in text:
                score += 0.35

            # Attribute matches with tiered scoring
            for attr_name, attr_value in attrs.items():
                if isinstance(attr_value, str) and kw_lower in attr_value.lower():
                    if attr_name in test_attrs:
                        # Test attributes get highest score
                        score += 0.6
                    elif attr_name in id_attrs:
                        # ID and name are highly reliable
                        score += 0.5
                    elif attr_name in semantic_attrs:
                        # Semantic attributes are good
                        score += 0.4
                    elif attr_name == "value":
                        # Value attribute (for buttons)
                        score += 0.35
                    elif attr_name == "class":
                        # Class names are less reliable but still useful
                        score += 0.2
                    elif attr_name.startswith("data-"):
                        # Other data attributes
                        score += 0.3
                    else:
                        score += 0.15

            # Tag match
            if kw_lower == tag:
                score += 0.2

        # Normalize score
        if keywords:
            score = score / len(keywords)

        # Context bonuses
        if context.get("element_type"):
            if context["element_type"] == tag:
                score += 0.1

        return min(1.0, score)

    def _generate_selectors_for_element(self, elem: Dict) -> List[Dict[str, Any]]:
        """Generate multiple selectors for an element"""
        selectors = []
        attrs = elem.get("attributes", {})
        tag = elem.get("tagName", "").lower()
        text = elem.get("textContent", "").strip()

        # data-testid (highest priority test attribute)
        if attrs.get("data-testid"):
            selectors.append({
                "selector": f'[data-testid="{attrs["data-testid"]}"]',
                "type": "css",
                "confidence": 0.98,
                "method": "test_id"
            })

        # data-test (common variation, e.g., Sauce Labs)
        if attrs.get("data-test"):
            selectors.append({
                "selector": f'[data-test="{attrs["data-test"]}"]',
                "type": "css",
                "confidence": 0.98,
                "method": "data_test"
            })

        # data-cy (Cypress convention)
        if attrs.get("data-cy"):
            selectors.append({
                "selector": f'[data-cy="{attrs["data-cy"]}"]',
                "type": "css",
                "confidence": 0.98,
                "method": "data_cy"
            })

        # data-qa (QA convention)
        if attrs.get("data-qa"):
            selectors.append({
                "selector": f'[data-qa="{attrs["data-qa"]}"]',
                "type": "css",
                "confidence": 0.98,
                "method": "data_qa"
            })

        # ID
        if attrs.get("id"):
            selectors.append({
                "selector": f'#{attrs["id"]}',
                "type": "css",
                "confidence": 0.9,
                "method": "id"
            })

        # Name
        if attrs.get("name"):
            selectors.append({
                "selector": f'{tag}[name="{attrs["name"]}"]',
                "type": "css",
                "confidence": 0.85,
                "method": "name"
            })
            # Also add without tag for flexibility
            selectors.append({
                "selector": f'[name="{attrs["name"]}"]',
                "type": "css",
                "confidence": 0.8,
                "method": "name_only"
            })

        # aria-label
        if attrs.get("aria-label"):
            selectors.append({
                "selector": f'[aria-label="{attrs["aria-label"]}"]',
                "type": "css",
                "confidence": 0.85,
                "method": "aria_label"
            })

        # Placeholder (for inputs)
        if attrs.get("placeholder"):
            selectors.append({
                "selector": f'[placeholder="{attrs["placeholder"]}"]',
                "type": "css",
                "confidence": 0.8,
                "method": "placeholder_attr"
            })
            # Also return as placeholder type for special handling
            selectors.append({
                "selector": attrs["placeholder"],
                "type": "placeholder",
                "confidence": 0.8,
                "method": "placeholder"
            })

        # Value attribute (for buttons/inputs)
        if attrs.get("value"):
            selectors.append({
                "selector": f'{tag}[value="{attrs["value"]}"]',
                "type": "css",
                "confidence": 0.75,
                "method": "value"
            })

        # Title attribute
        if attrs.get("title"):
            selectors.append({
                "selector": f'[title="{attrs["title"]}"]',
                "type": "css",
                "confidence": 0.7,
                "method": "title"
            })

        # Text content
        if text and len(text) < 50:
            selectors.append({
                "selector": text,
                "type": "text",
                "confidence": 0.75,
                "method": "text"
            })

        # Role attribute (accessibility)
        if attrs.get("role"):
            role = attrs["role"]
            if text:
                selectors.append({
                    "selector": f'[role="{role}"]',
                    "type": "css",
                    "confidence": 0.65,
                    "method": "role"
                })

        return selectors

    def _heuristic_from_html(
        self,
        keywords: List[str],
        page_html: str,
        context: Dict[str, Any],
        original_intent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate selectors from HTML using intelligent heuristics.

        Uses keyword variations, synonyms, and fuzzy matching to find elements.
        """
        candidates = []

        # Get all variations of all keywords (including synonyms)
        all_variations = set()
        for keyword in keywords:
            variations = get_keyword_variations(keyword)
            all_variations.update(variations)

        # IMPORTANT: Also add the original intent and its variations
        # This handles cases like "login-button" where we need to search for the whole term
        # not just "login" and "button" separately
        if original_intent:
            # Add original intent with different separators
            intent_lower = original_intent.lower()
            all_variations.add(intent_lower)
            all_variations.add(intent_lower.replace(' ', '-'))
            all_variations.add(intent_lower.replace(' ', '_'))
            all_variations.add(intent_lower.replace('-', ' '))
            all_variations.add(intent_lower.replace('_', ' '))
            all_variations.add(intent_lower.replace('-', '_'))
            all_variations.add(intent_lower.replace('_', '-'))
            # Also add without any separators
            all_variations.add(intent_lower.replace('-', '').replace('_', '').replace(' ', ''))

        logger.info(f"HTML Heuristics: Searching with {len(all_variations)} variations: {list(all_variations)[:15]}")
        logger.info(f"HTML length: {len(page_html)} chars")

        # Search for each variation in attributes
        for variation in all_variations:
            variation_escaped = re.escape(variation)

            # Define attribute patterns with their scores
            attribute_patterns = [
                # Test attributes (highest priority)
                ("data-testid", 0.98, "html_testid"),
                ("data-test", 0.98, "html_datatest"),
                ("data-cy", 0.98, "html_datacy"),
                ("data-qa", 0.98, "html_dataqa"),
                # Identification attributes
                ("id", 0.9, "html_id"),
                ("name", 0.85, "html_name"),
                # Semantic attributes
                ("aria-label", 0.85, "html_arialabel"),
                ("placeholder", 0.8, "html_placeholder"),
                ("value", 0.8, "html_value"),
                ("title", 0.75, "html_title"),
                ("alt", 0.7, "html_alt"),
            ]

            for attr_name, base_score, method in attribute_patterns:
                # Pattern to find attribute values containing the variation
                pattern = rf'{attr_name}=["\']([^"\']*)["\']'
                for match in re.finditer(pattern, page_html, re.I):
                    attr_value = match.group(1)

                    # Check if variation is in the attribute value
                    found, match_score = text_contains_keyword(attr_value, variation)
                    if found:
                        # Calculate final score based on match quality
                        final_score = base_score * match_score

                        # Build selector based on attribute type
                        if attr_name == "id":
                            selector = f'#{attr_value}'
                        else:
                            selector = f'[{attr_name}="{attr_value}"]'

                        logger.info(f"HTML Match: {attr_name}='{attr_value}' matched variation '{variation}' -> {selector} (score={final_score:.2f})")

                        candidates.append({
                            "selector": selector,
                            "type": "css",
                            "score": final_score,
                            "method": method,
                            "matched_variation": variation
                        })

            # Find by class containing variation
            class_pattern = rf'class=["\']([^"\']+)["\']'
            for match in re.finditer(class_pattern, page_html, re.I):
                class_value = match.group(1)
                for cls in class_value.split():
                    found, match_score = text_contains_keyword(cls, variation)
                    if found:
                        candidates.append({
                            "selector": f'.{cls}',
                            "type": "css",
                            "score": 0.6 * match_score,
                            "method": "html_class",
                            "matched_variation": variation
                        })

        # Also search for text content within buttons, links, and other clickable elements
        # This helps find buttons like <button>Log In</button> or <input type="submit" value="Login">
        self._find_elements_by_text_content(page_html, keywords, candidates)

        # Remove duplicates while preserving order and highest scores
        seen = {}
        for c in candidates:
            key = c["selector"]
            if key not in seen or seen[key]["score"] < c["score"]:
                seen[key] = c

        unique_candidates = list(seen.values())

        # Sort by score descending
        unique_candidates.sort(key=lambda x: x["score"], reverse=True)

        logger.debug(f"Found {len(unique_candidates)} candidates from HTML heuristics")
        return unique_candidates

    def _find_elements_by_text_content(
        self,
        page_html: str,
        keywords: List[str],
        candidates: List[Dict[str, Any]]
    ):
        """Find elements by their text content (for buttons, links, etc.)"""
        # Pattern to find button/input/a elements with their content
        element_patterns = [
            # Buttons with text content
            (r'<button[^>]*>([^<]+)</button>', 'button', 0.85),
            # Links with text content
            (r'<a[^>]*>([^<]+)</a>', 'a', 0.8),
            # Spans that might be clickable
            (r'<span[^>]*>([^<]+)</span>', 'span', 0.6),
            # Divs with role="button"
            (r'<div[^>]*role=["\']button["\'][^>]*>([^<]+)</div>', 'div[role="button"]', 0.75),
        ]

        # Get all keyword variations
        all_variations = set()
        for keyword in keywords:
            all_variations.update(get_keyword_variations(keyword))

        for pattern, tag_selector, base_score in element_patterns:
            for match in re.finditer(pattern, page_html, re.I):
                text_content = match.group(1).strip()
                if not text_content or len(text_content) > 50:
                    continue

                # Check if any keyword variation is in the text
                for variation in all_variations:
                    found, match_score = text_contains_keyword(text_content, variation)
                    if found:
                        # Use Playwright's text selector
                        candidates.append({
                            "selector": f'{tag_selector}:has-text("{text_content}")',
                            "type": "css",
                            "score": base_score * match_score,
                            "method": "text_content",
                            "matched_text": text_content,
                            "matched_variation": variation
                        })

                        # Also add a pure text selector as alternative
                        candidates.append({
                            "selector": text_content,
                            "type": "text",
                            "score": (base_score - 0.1) * match_score,
                            "method": "text_only",
                            "matched_text": text_content
                        })
                        break  # Found a match, don't need to check other variations

        # Also look for input type="submit" with value attribute
        submit_pattern = r'<input[^>]*type=["\']submit["\'][^>]*value=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(submit_pattern, page_html, re.I):
            value = match.group(1).strip()
            for variation in all_variations:
                found, match_score = text_contains_keyword(value, variation)
                if found:
                    candidates.append({
                        "selector": f'input[type="submit"][value="{value}"]',
                        "type": "css",
                        "score": 0.9 * match_score,
                        "method": "submit_button",
                        "matched_value": value
                    })
                    break

        # Pattern for value attribute appearing before type
        submit_pattern2 = r'<input[^>]*value=["\']([^"\']+)["\'][^>]*type=["\']submit["\'][^>]*>'
        for match in re.finditer(submit_pattern2, page_html, re.I):
            value = match.group(1).strip()
            for variation in all_variations:
                found, match_score = text_contains_keyword(value, variation)
                if found:
                    candidates.append({
                        "selector": f'input[type="submit"][value="{value}"]',
                        "type": "css",
                        "score": 0.9 * match_score,
                        "method": "submit_button",
                        "matched_value": value
                    })

    # ==================== Tier 4: AI Decision ====================

    def _try_ai_decision(
        self,
        intent: str,
        page_html: Optional[str],
        dom_elements: Optional[List[Dict]],
        context: Dict[str, Any]
    ) -> Optional[SelectorResult]:
        """Use AI to determine the selector"""
        if not self.ai_callback:
            return None

        try:
            # Prepare context for AI
            ai_context = {
                "intent": intent,
                "page_snippet": page_html[:5000] if page_html else None,
                "element_count": len(dom_elements) if dom_elements else 0,
                "available_ids": self._extract_ids_from_html(page_html) if page_html else [],
                "context": context
            }

            # Call AI
            result = self.ai_callback(ai_context)

            if result and result.get("selector"):
                return SelectorResult(
                    selector=result["selector"],
                    selector_type=result.get("type", "css"),
                    confidence=result.get("confidence", 0.6),
                    tier=ResolutionTier.AI_DECISION,
                    alternatives=result.get("alternatives", []),
                    metadata={
                        "ai_reasoning": result.get("reasoning", ""),
                        "attributes": result.get("attributes", {})
                    }
                )

        except Exception as e:
            logger.error(f"AI decision failed: {e}")

        return None

    def _extract_ids_from_html(self, html: str) -> List[str]:
        """Extract all IDs from HTML for AI context"""
        ids = re.findall(r'id=["\']([^"\']+)["\']', html)
        return list(set(ids))[:50]  # Limit to 50

    # ==================== Tier 5: Fallback ====================

    def _try_fallback(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> Optional[SelectorResult]:
        """Try fallback strategies when all else fails"""
        keywords = self._extract_keywords(intent)

        if not keywords:
            return None

        fallback_selectors = []

        # Generate generic selectors based on intent
        primary_keyword = keywords[0]

        # Try all test attribute patterns first (highest priority)
        fallback_selectors.extend([
            {"selector": f'[data-test*="{primary_keyword}"]', "type": "css", "score": 0.55},
            {"selector": f'[data-testid*="{primary_keyword}"]', "type": "css", "score": 0.55},
            {"selector": f'[data-cy*="{primary_keyword}"]', "type": "css", "score": 0.55},
            {"selector": f'[data-qa*="{primary_keyword}"]', "type": "css", "score": 0.55},
        ])

        # Try common attribute patterns
        fallback_selectors.extend([
            {"selector": f'[id*="{primary_keyword}"]', "type": "css", "score": 0.5},
            {"selector": f'[name*="{primary_keyword}"]', "type": "css", "score": 0.45},
            {"selector": f'[aria-label*="{primary_keyword}"]', "type": "css", "score": 0.45},
            {"selector": f'[placeholder*="{primary_keyword}"]', "type": "css", "score": 0.4},
            {"selector": f'[value*="{primary_keyword}"]', "type": "css", "score": 0.35},
            {"selector": f'[title*="{primary_keyword}"]', "type": "css", "score": 0.35},
        ])

        # Add element type specific fallbacks
        if any(kw in intent.lower() for kw in ["button", "submit", "click", "login", "sign"]):
            fallback_selectors.extend([
                {"selector": f'button:has-text("{primary_keyword}")', "type": "css", "score": 0.45},
                {"selector": f'input[type="submit"][value*="{primary_keyword}" i]', "type": "css", "score": 0.45},
                {"selector": f'[role="button"]:has-text("{primary_keyword}")', "type": "css", "score": 0.4},
                {"selector": f'.btn:has-text("{primary_keyword}")', "type": "css", "score": 0.35},
            ])

        if any(kw in intent.lower() for kw in ["input", "field", "enter", "type", "username", "password", "email"]):
            fallback_selectors.extend([
                {"selector": f'input[placeholder*="{primary_keyword}" i]', "type": "css", "score": 0.45},
                {"selector": f'input[name*="{primary_keyword}" i]', "type": "css", "score": 0.45},
                {"selector": f'input[id*="{primary_keyword}" i]', "type": "css", "score": 0.45},
                {"selector": f'input[aria-label*="{primary_keyword}" i]', "type": "css", "score": 0.4},
            ])

        if any(kw in intent.lower() for kw in ["link", "navigate", "href"]):
            fallback_selectors.extend([
                {"selector": f'a:has-text("{primary_keyword}")', "type": "css", "score": 0.4},
                {"selector": f'a[href*="{primary_keyword}"]', "type": "css", "score": 0.35},
            ])

        if any(kw in intent.lower() for kw in ["select", "dropdown", "combo"]):
            fallback_selectors.extend([
                {"selector": f'select[name*="{primary_keyword}" i]', "type": "css", "score": 0.45},
                {"selector": f'select[id*="{primary_keyword}" i]', "type": "css", "score": 0.45},
            ])

        if any(kw in intent.lower() for kw in ["checkbox", "check"]):
            fallback_selectors.extend([
                {"selector": f'input[type="checkbox"][name*="{primary_keyword}" i]', "type": "css", "score": 0.45},
                {"selector": f'input[type="checkbox"][id*="{primary_keyword}" i]', "type": "css", "score": 0.45},
            ])

        # Sort by score
        fallback_selectors.sort(key=lambda x: x.get("score", 0.3), reverse=True)

        if fallback_selectors:
            return SelectorResult(
                selector=fallback_selectors[0]["selector"],
                selector_type=fallback_selectors[0]["type"],
                confidence=fallback_selectors[0].get("score", 0.4),
                tier=ResolutionTier.FALLBACK,
                alternatives=fallback_selectors[1:8],
                metadata={"fallback_keyword": primary_keyword}
            )

        return None

    # ==================== Utility Methods ====================

    def _normalize_intent(self, intent: str) -> str:
        """Normalize an intent string for matching"""
        # Lowercase and remove extra spaces
        normalized = intent.lower().strip()
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        return normalized

    def get_smart_alternatives(
        self,
        intent: str,
        failed_selector: str,
        page_html: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get smart alternative selectors when one fails.

        Uses Semantic Element Intelligence to understand what the element
        IS and generate better alternatives based on element DNA.
        """
        alternatives = []
        context = context or {}

        if page_html:
            # Use SEI to get semantic alternatives
            sei_alternatives = self.semantic_intelligence.get_smart_alternatives(
                element_key=intent,
                primary_selector=failed_selector,
                page_html=page_html
            )
            alternatives.extend(sei_alternatives)

            # Also try semantic resolution for fresh alternatives
            semantic_result = self._try_semantic_resolution(intent, page_html, None, context)
            if semantic_result and semantic_result.selector != failed_selector:
                alternatives.append({
                    "selector": semantic_result.selector,
                    "type": semantic_result.selector_type,
                    "confidence": semantic_result.confidence,
                    "source": "semantic_re_resolution"
                })
                alternatives.extend(semantic_result.alternatives)

        # Sort by confidence and deduplicate
        seen = set()
        unique_alternatives = []
        for alt in sorted(alternatives, key=lambda x: x.get("confidence", 0), reverse=True):
            selector = alt.get("selector", "")
            if selector and selector not in seen and selector != failed_selector:
                seen.add(selector)
                unique_alternatives.append(alt)

        return unique_alternatives[:8]  # Return top 8 alternatives

    def record_result(
        self,
        intent: str,
        domain: str,
        page: str,
        selector: str,
        selector_type: str,
        success: bool
    ):
        """Record the result of using a selector"""
        if self.learning_engine:
            self.learning_engine.record_selector_result(
                domain=domain,
                page=page,
                element_key=self._normalize_intent(intent),
                selector=selector,
                success=success,
                selector_type=selector_type
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get selector service statistics"""
        return {
            "total_resolutions": self._total_resolutions,
            "tier_hits": {tier.value: count for tier, count in self._tier_hits.items()},
            "tier_percentages": {
                tier.value: (count / self._total_resolutions * 100) if self._total_resolutions > 0 else 0
                for tier, count in self._tier_hits.items()
            },
            "ai_dependency": (
                self._tier_hits[ResolutionTier.AI_DECISION] / self._total_resolutions * 100
                if self._total_resolutions > 0 else 0
            ),
            "semantic_intelligence": {
                "assists": self._semantic_assists,
                "assist_rate": (
                    self._semantic_assists / self._total_resolutions * 100
                    if self._total_resolutions > 0 else 0
                ),
                "description": "Elements resolved by understanding PURPOSE, not just attributes"
            }
        }
