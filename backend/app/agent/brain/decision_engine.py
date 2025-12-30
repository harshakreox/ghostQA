"""
Decision Engine for QA Brain
=============================

The "neural network" that makes decisions based on memory patterns.
Uses similarity matching and confidence scoring to decide actions
WITHOUT calling AI for most cases.

Decision Flow:
1. Receive decision request (e.g., "find login button")
2. Search memory systems for matching patterns
3. Score matches by confidence and relevance
4. If confidence >= threshold: return local decision
5. If confidence < threshold: request AI fallback

This is the core that makes the system token-efficient.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .memory import (
    PageMemory, ErrorMemory, WorkflowMemory,
    PageSignature, ErrorMemoryEntry
)

# Import existing knowledge systems
try:
    from ..knowledge.knowledge_index import KnowledgeIndex, SelectorMatch
except ImportError:
    KnowledgeIndex = None
    SelectorMatch = None

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions the engine can make"""
    FIND_ELEMENT = "find_element"  # Find an element on page
    CHOOSE_ACTION = "choose_action"  # What action to take
    HANDLE_ERROR = "handle_error"  # How to handle an error
    PREDICT_NEXT = "predict_next"  # What happens next
    WAIT_TIME = "wait_time"  # How long to wait
    PAGE_TYPE = "page_type"  # What type of page this is
    RECOVERY = "recovery"  # How to recover from failure


class DecisionSource(Enum):
    """Source of the decision"""
    MEMORY = "memory"  # From learned memory
    HEURISTIC = "heuristic"  # From built-in rules
    AI = "ai"  # From AI fallback
    DEFAULT = "default"  # Fallback default


@dataclass
class Decision:
    """A decision made by the engine"""
    decision_type: DecisionType
    source: DecisionSource
    confidence: float  # 0.0 to 1.0
    value: Any  # The actual decision value
    alternatives: List[Any] = field(default_factory=list)
    reasoning: str = ""
    memory_id: Optional[str] = None  # ID of memory entry used


@dataclass
class DecisionRequest:
    """Request for a decision"""
    decision_type: DecisionType
    context: Dict[str, Any]  # Context for the decision
    min_confidence: float = 0.5  # Minimum confidence to accept
    allow_ai_fallback: bool = True


class DecisionEngine:
    """
    Makes intelligent decisions based on memory patterns.

    This is the "brain" that:
    - Searches memories for relevant patterns
    - Scores matches by confidence
    - Returns decisions without AI when possible
    - Tracks decision accuracy for learning
    """

    def __init__(
        self,
        page_memory: PageMemory,
        action_memory=None,  # Deprecated - use knowledge_index
        error_memory: ErrorMemory = None,
        workflow_memory: WorkflowMemory = None,
        knowledge_index=None  # Use existing knowledge system
    ):
        self.page_memory = page_memory
        self.error_memory = error_memory
        self.workflow_memory = workflow_memory
        self.knowledge_index = knowledge_index  # Use existing knowledge

        # Decision thresholds
        self.high_confidence_threshold = 0.8
        self.medium_confidence_threshold = 0.5
        self.low_confidence_threshold = 0.3

        # Statistics
        self.decisions_made = 0
        self.memory_hits = 0
        self.heuristic_hits = 0
        self.ai_fallbacks = 0

    def decide(self, request: DecisionRequest) -> Decision:
        """
        Make a decision based on the request.

        This is the main entry point. It will:
        1. Try memory lookup first
        2. Fall back to heuristics
        3. Request AI only if needed
        """
        self.decisions_made += 1

        # Route to appropriate decision method
        if request.decision_type == DecisionType.FIND_ELEMENT:
            return self._decide_find_element(request)
        elif request.decision_type == DecisionType.CHOOSE_ACTION:
            return self._decide_choose_action(request)
        elif request.decision_type == DecisionType.HANDLE_ERROR:
            return self._decide_handle_error(request)
        elif request.decision_type == DecisionType.PREDICT_NEXT:
            return self._decide_predict_next(request)
        elif request.decision_type == DecisionType.WAIT_TIME:
            return self._decide_wait_time(request)
        elif request.decision_type == DecisionType.PAGE_TYPE:
            return self._decide_page_type(request)
        elif request.decision_type == DecisionType.RECOVERY:
            return self._decide_recovery(request)
        else:
            return Decision(
                decision_type=request.decision_type,
                source=DecisionSource.DEFAULT,
                confidence=0.0,
                value=None,
                reasoning="Unknown decision type"
            )

    def _decide_find_element(self, request: DecisionRequest) -> Decision:
        """Decide how to find an element"""
        context = request.context
        intent = context.get("intent", "")
        page_type = context.get("page_type", "")
        url = context.get("url", "")
        domain = context.get("domain", "")

        # 1. Try knowledge index first (existing system)
        if self.knowledge_index:
            try:
                # Try direct lookup first
                knowledge = self.knowledge_index.lookup(domain, url, intent)
                if knowledge and knowledge.selectors:
                    best = max(knowledge.selectors, key=lambda s: s.confidence)
                    if best.confidence >= request.min_confidence:
                        self.memory_hits += 1
                        logger.debug(f"[DECISION] Found in knowledge index: {best.value}")
                        return Decision(
                            decision_type=DecisionType.FIND_ELEMENT,
                            source=DecisionSource.MEMORY,
                            confidence=best.confidence,
                            value=best.value,
                            reasoning="Found in knowledge index (direct lookup)"
                        )

                # Try fuzzy search by intent
                matches = self.knowledge_index.find_by_intent(intent, domain, url)
                if matches:
                    best_match = matches[0]
                    if best_match.confidence >= request.min_confidence:
                        self.memory_hits += 1
                        logger.debug(f"[DECISION] Found in knowledge index: {best_match.selector}")
                        return Decision(
                            decision_type=DecisionType.FIND_ELEMENT,
                            source=DecisionSource.MEMORY,
                            confidence=best_match.confidence,
                            value=best_match.selector,
                            reasoning="Found in knowledge index (fuzzy match)"
                        )
            except Exception as e:
                logger.debug(f"[DECISION] Knowledge index lookup failed: {e}")

        # 2. Try page memory for known elements
        page_entry = self.page_memory.find_by_url(url)
        if page_entry:
            # Check if this intent is known for this page
            selector = page_entry.known_elements.get(intent)
            if selector:
                self.memory_hits += 1
                return Decision(
                    decision_type=DecisionType.FIND_ELEMENT,
                    source=DecisionSource.MEMORY,
                    confidence=page_entry.confidence,
                    value=selector,
                    reasoning=f"Found in page memory",
                    memory_id=page_entry.id
                )

        # 3. Try heuristic selectors
        heuristic_selector = self._heuristic_selector(intent, page_type)
        if heuristic_selector:
            self.heuristic_hits += 1
            return Decision(
                decision_type=DecisionType.FIND_ELEMENT,
                source=DecisionSource.HEURISTIC,
                confidence=0.6,
                value=heuristic_selector,
                reasoning="Using heuristic selector pattern"
            )

        # 4. Need AI fallback
        self.ai_fallbacks += 1
        return Decision(
            decision_type=DecisionType.FIND_ELEMENT,
            source=DecisionSource.AI,
            confidence=0.0,
            value=None,
            reasoning="No memory or heuristic match - AI needed"
        )

    def _decide_choose_action(self, request: DecisionRequest) -> Decision:
        """Decide what action to take"""
        context = request.context
        page_type = context.get("page_type", "")
        step_text = context.get("step_text", "")

        # Parse action from step text
        action = self._parse_action_from_text(step_text)

        if action:
            self.heuristic_hits += 1
            return Decision(
                decision_type=DecisionType.CHOOSE_ACTION,
                source=DecisionSource.HEURISTIC,
                confidence=0.8,
                value=action,
                reasoning=f"Parsed action '{action['type']}' from step text"
            )

        # Need AI for complex interpretation
        self.ai_fallbacks += 1
        return Decision(
            decision_type=DecisionType.CHOOSE_ACTION,
            source=DecisionSource.AI,
            confidence=0.0,
            value=None,
            reasoning="Could not parse action - AI needed"
        )

    def _decide_handle_error(self, request: DecisionRequest) -> Decision:
        """Decide how to handle an error"""
        context = request.context
        error_message = context.get("error_message", "")

        # Look up error in memory
        error_entry = self.error_memory.find_matching_error(error_message)

        if error_entry and error_entry.pattern.recovery_action:
            self.memory_hits += 1
            return Decision(
                decision_type=DecisionType.HANDLE_ERROR,
                source=DecisionSource.MEMORY,
                confidence=error_entry.recovery_success_rate,
                value={
                    "error_type": error_entry.pattern.error_type,
                    "recovery_action": error_entry.pattern.recovery_action,
                    "field_hint": error_entry.pattern.field_hint
                },
                reasoning=f"Known error pattern with {error_entry.recovery_success_rate:.0%} recovery rate",
                memory_id=error_entry.id
            )

        # Try heuristic error handling
        heuristic = self._heuristic_error_handler(error_message)
        if heuristic:
            self.heuristic_hits += 1
            return Decision(
                decision_type=DecisionType.HANDLE_ERROR,
                source=DecisionSource.HEURISTIC,
                confidence=0.5,
                value=heuristic,
                reasoning="Using heuristic error handler"
            )

        self.ai_fallbacks += 1
        return Decision(
            decision_type=DecisionType.HANDLE_ERROR,
            source=DecisionSource.AI,
            confidence=0.0,
            value=None,
            reasoning="Unknown error pattern - AI needed"
        )

    def _decide_predict_next(self, request: DecisionRequest) -> Decision:
        """Predict what happens next in the workflow"""
        context = request.context
        current_page = context.get("current_page_type", "")
        last_action = context.get("last_action", "")

        prediction = self.workflow_memory.predict_next_page(current_page, last_action)

        if prediction:
            self.memory_hits += 1
            return Decision(
                decision_type=DecisionType.PREDICT_NEXT,
                source=DecisionSource.MEMORY,
                confidence=0.7,
                value=prediction,
                reasoning=f"Workflow pattern predicts '{prediction}' next"
            )

        # Use heuristic predictions
        heuristic = self._heuristic_next_page(current_page, last_action)
        if heuristic:
            self.heuristic_hits += 1
            return Decision(
                decision_type=DecisionType.PREDICT_NEXT,
                source=DecisionSource.HEURISTIC,
                confidence=0.5,
                value=heuristic,
                reasoning="Heuristic workflow prediction"
            )

        return Decision(
            decision_type=DecisionType.PREDICT_NEXT,
            source=DecisionSource.DEFAULT,
            confidence=0.3,
            value="unknown",
            reasoning="No prediction available"
        )

    def _decide_wait_time(self, request: DecisionRequest) -> Decision:
        """Decide how long to wait"""
        context = request.context
        url = context.get("url", "")
        action = context.get("action", "")

        # Check page memory for typical load time
        page_entry = self.page_memory.find_by_url(url)
        if page_entry:
            self.memory_hits += 1
            return Decision(
                decision_type=DecisionType.WAIT_TIME,
                source=DecisionSource.MEMORY,
                confidence=0.8,
                value=page_entry.typical_load_time_ms,
                reasoning=f"Based on {page_entry.access_count} previous visits",
                memory_id=page_entry.id
            )

        # Heuristic waits
        default_waits = {
            "navigate": 2000,
            "click": 500,
            "type": 200,
            "submit": 3000
        }
        wait_time = default_waits.get(action, 1000)

        self.heuristic_hits += 1
        return Decision(
            decision_type=DecisionType.WAIT_TIME,
            source=DecisionSource.HEURISTIC,
            confidence=0.6,
            value=wait_time,
            reasoning=f"Default wait for '{action}' action"
        )

    def _decide_page_type(self, request: DecisionRequest) -> Decision:
        """Decide what type of page this is"""
        context = request.context
        url = context.get("url", "")
        title = context.get("title", "")
        signature = context.get("signature")

        # Check page memory
        if signature:
            page_entry = self.page_memory.find_by_signature(signature)
            if page_entry:
                self.memory_hits += 1
                return Decision(
                    decision_type=DecisionType.PAGE_TYPE,
                    source=DecisionSource.MEMORY,
                    confidence=page_entry.confidence,
                    value=page_entry.signature.page_type,
                    reasoning=f"Recognized page from memory",
                    memory_id=page_entry.id
                )

        # Heuristic detection from URL/title
        page_type = self._heuristic_page_type(url, title)
        self.heuristic_hits += 1

        return Decision(
            decision_type=DecisionType.PAGE_TYPE,
            source=DecisionSource.HEURISTIC,
            confidence=0.7,
            value=page_type,
            reasoning="Detected from URL/title patterns"
        )

    def _decide_recovery(self, request: DecisionRequest) -> Decision:
        """Decide how to recover from a failure"""
        context = request.context
        failure_type = context.get("failure_type", "")
        element = context.get("element", "")

        # Built-in recovery strategies
        strategies = {
            "element_not_found": [
                {"action": "wait", "value": 2000},
                {"action": "scroll", "value": "down"},
                {"action": "retry", "value": None}
            ],
            "element_not_visible": [
                {"action": "scroll_into_view", "value": element},
                {"action": "wait", "value": 1000},
                {"action": "dismiss_overlay", "value": None}
            ],
            "element_not_clickable": [
                {"action": "dismiss_overlay", "value": None},
                {"action": "force_click", "value": element},
                {"action": "js_click", "value": element}
            ],
            "timeout": [
                {"action": "wait", "value": 5000},
                {"action": "refresh", "value": None},
                {"action": "retry", "value": None}
            ]
        }

        if failure_type in strategies:
            self.heuristic_hits += 1
            return Decision(
                decision_type=DecisionType.RECOVERY,
                source=DecisionSource.HEURISTIC,
                confidence=0.7,
                value=strategies[failure_type],
                reasoning=f"Standard recovery for {failure_type}"
            )

        return Decision(
            decision_type=DecisionType.RECOVERY,
            source=DecisionSource.DEFAULT,
            confidence=0.3,
            value=[{"action": "retry", "value": None}],
            reasoning="Default retry strategy"
        )

    # =========================================================================
    # HEURISTIC METHODS
    # =========================================================================

    def _heuristic_selector(self, intent: str, page_type: str) -> Optional[str]:
        """
        Generate heuristic selector based on intent.

        DESIGN: No hardcoded field patterns - every app is different.
        The brain should LEARN selectors from actual interactions.
        
        Only handles universal patterns (button/link text matching).
        For inputs/fields, returns None to trigger AI lookup + learning.
        """
        intent_lower = intent.lower()

        # Button text matching - works on ANY app
        if 'button' in intent_lower or 'submit' in intent_lower:
            import re
            match = re.search(r'(?:click|press|tap)\s+(?:the\s+)?(.+?)\s*(?:button)?$', intent_lower)
            if match:
                text = match.group(1).strip()
                if text and text not in ('the', 'a', 'an', 'button', 'on'):
                    return f'button:has-text("{text.title()}")'

        # Link text matching - works on ANY app
        if 'link' in intent_lower:
            import re
            match = re.search(r'(?:click|follow)\s+(?:the\s+)?(.+?)\s*(?:link)?$', intent_lower)
            if match:
                text = match.group(1).strip()
                if text and text not in ('the', 'a', 'an', 'link'):
                    return f'a:has-text("{text}")'

        # For inputs/fields - return None to trigger AI + learning
        return None

    def _heuristic_error_handler(self, error_message: str) -> Optional[Dict[str, Any]]:
        """Generate heuristic error handling"""
        error_lower = error_message.lower()

        if 'required' in error_lower:
            return {
                "error_type": "validation",
                "recovery_action": "fill_required_fields",
                "field_hint": None
            }

        if 'password' in error_lower and any(x in error_lower for x in ['short', 'weak', 'length']):
            return {
                "error_type": "validation",
                "recovery_action": "use_stronger_password",
                "field_hint": "password"
            }

        if 'email' in error_lower and any(x in error_lower for x in ['invalid', 'format', 'valid']):
            return {
                "error_type": "validation",
                "recovery_action": "use_valid_email",
                "field_hint": "email"
            }

        if any(x in error_lower for x in ['exists', 'taken', 'registered']):
            return {
                "error_type": "conflict",
                "recovery_action": "use_different_value",
                "field_hint": None
            }

        if any(x in error_lower for x in ['timeout', 'timed out']):
            return {
                "error_type": "timeout",
                "recovery_action": "retry_with_wait",
                "field_hint": None
            }

        return None

    def _heuristic_next_page(self, current_page: str, last_action: str) -> Optional[str]:
        """Predict next page based on heuristics"""
        transitions = {
            ("login", "submit"): "dashboard",
            ("login", "click_register"): "register",
            ("register", "submit"): "login",
            ("checkout", "submit"): "confirmation",
            ("search", "submit"): "search_results",
            ("form", "submit"): "confirmation",
        }

        return transitions.get((current_page, last_action))

    def _heuristic_page_type(self, url: str, title: str) -> str:
        """Detect page type from URL and title"""
        combined = f"{url} {title}".lower()

        patterns = [
            (["login", "signin", "sign-in"], "login"),
            (["register", "signup", "sign-up", "create-account"], "register"),
            (["checkout", "payment"], "checkout"),
            (["cart", "basket"], "cart"),
            (["dashboard", "home", "overview"], "dashboard"),
            (["search", "results"], "search"),
            (["settings", "profile", "account"], "settings"),
            (["error", "404", "500"], "error"),
        ]

        for keywords, page_type in patterns:
            if any(kw in combined for kw in keywords):
                return page_type

        return "unknown"

    def _parse_action_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse action from natural language text"""
        text_lower = text.lower()

        # Click patterns
        if any(x in text_lower for x in ['click', 'tap', 'press']):
            import re
            match = re.search(r'(?:click|tap|press)\s+(?:on\s+)?(?:the\s+)?["\']?(.+?)["\']?$', text_lower)
            if match:
                return {
                    "type": "click",
                    "target": match.group(1).strip()
                }

        # Type patterns
        if any(x in text_lower for x in ['type', 'enter', 'input', 'fill']):
            import re
            match = re.search(r'(?:type|enter|input|fill)\s+["\']?(.+?)["\']?\s+(?:in|into)\s+(.+?)$', text_lower)
            if match:
                return {
                    "type": "type",
                    "value": match.group(1).strip(),
                    "target": match.group(2).strip()
                }

        # Navigate patterns
        if any(x in text_lower for x in ['navigate', 'go to', 'open', 'visit']):
            import re
            match = re.search(r'(?:navigate|go)\s+to\s+(.+?)$', text_lower)
            if match:
                return {
                    "type": "navigate",
                    "target": match.group(1).strip()
                }

        return None

    # =========================================================================
    # FEEDBACK & LEARNING
    # =========================================================================

    def record_decision_outcome(
        self,
        decision: Decision,
        success: bool,
        actual_value: Any = None
    ):
        """Record the outcome of a decision for learning"""
        if decision.memory_id:
            # Update memory entry
            if decision.decision_type == DecisionType.FIND_ELEMENT:
                if decision.memory_id in self.action_memory.entries:
                    entry = self.action_memory.entries[decision.memory_id]
                    if success:
                        entry.record_success()
                    else:
                        entry.record_failure()

            elif decision.decision_type == DecisionType.HANDLE_ERROR:
                if decision.memory_id in self.error_memory.entries:
                    entry = self.error_memory.entries[decision.memory_id]
                    if success:
                        entry.record_success()
                    else:
                        entry.record_failure()

    def get_stats(self) -> Dict[str, Any]:
        """Get decision statistics"""
        total = self.decisions_made or 1
        return {
            "decisions_made": self.decisions_made,
            "memory_hits": self.memory_hits,
            "heuristic_hits": self.heuristic_hits,
            "ai_fallbacks": self.ai_fallbacks,
            "memory_hit_rate": self.memory_hits / total * 100,
            "heuristic_hit_rate": self.heuristic_hits / total * 100,
            "ai_fallback_rate": self.ai_fallbacks / total * 100,
            "local_decision_rate": (self.memory_hits + self.heuristic_hits) / total * 100
        }
