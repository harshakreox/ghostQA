"""
QA Brain - The Neural Core (Integrated with Knowledge Systems)
================================================================

The brain that coordinates all cognitive functions:
- Uses EXISTING knowledge systems (no duplication)
- Adds NEW capabilities (page awareness, error handling, AI budget)
- Makes intelligent decisions with minimal AI usage

Architecture:
    Brain (this) ──uses──> Knowledge (existing)
         │                      │
         │                      ├── KnowledgeIndex (selector storage)
         │                      ├── LearningEngine (learning from actions)
         │                      └── PatternStore (action patterns)
         │
         └── Adds NEW:
              ├── PageMemory (page types, layouts)
              ├── ErrorMemory (error patterns, recovery)
              ├── WorkflowMemory (test flows, predictions)
              ├── DecisionEngine (intelligent decisions)
              └── AIGateway (token budget management)
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Use EXISTING knowledge systems
from ..knowledge.knowledge_index import KnowledgeIndex, SelectorMatch
from ..knowledge.learning_engine import LearningEngine
from ..knowledge.pattern_store import PatternStore

# Use NEW brain components
from .memory import PageMemory, ErrorMemory, WorkflowMemory, PageSignature
from .decision_engine import DecisionEngine, Decision, DecisionType, DecisionSource, DecisionRequest
from .ai_gateway import AIGateway, AIRequest, AIResponse, AIProvider, RequestPriority

logger = logging.getLogger(__name__)


@dataclass
class BrainConfig:
    """Configuration for the QA Brain"""
    data_dir: str = "data/agent_knowledge"
    ai_provider: str = "anthropic"
    enable_learning: bool = True
    enable_ai_fallback: bool = True
    min_confidence_threshold: float = 0.5
    high_confidence_threshold: float = 0.8
    daily_token_budget: int = 50000
    per_test_token_budget: int = 2000


class QABrain:
    """
    The Neural Core of GhostQA.

    Integrates with existing knowledge systems and adds new capabilities
    for intelligent, self-learning test automation.

    Body Parts:
        - Knowledge (existing): Long-term memory for selectors/patterns
        - Brain (this): Decision making, specialized memories, AI budget
        - Core: Execution (uses brain for decisions)
    """

    def __init__(
        self,
        config: BrainConfig = None,
        knowledge_index: KnowledgeIndex = None,
        learning_engine: LearningEngine = None,
        pattern_store: PatternStore = None
    ):
        """
        Initialize the brain.

        Args:
            config: Brain configuration
            knowledge_index: Existing knowledge index (shared with core)
            learning_engine: Existing learning engine (shared with core)
            pattern_store: Existing pattern store (shared with core)
        """
        self.config = config or BrainConfig()
        self.data_dir = Path(self.config.data_dir)
        self.brain_dir = self.data_dir / "brain"
        self.brain_dir.mkdir(parents=True, exist_ok=True)

        # =====================================================================
        # USE EXISTING KNOWLEDGE SYSTEMS (shared with core)
        # =====================================================================
        self.knowledge_index = knowledge_index or KnowledgeIndex(str(self.data_dir))
        self.learning_engine = learning_engine
        self.pattern_store = pattern_store or PatternStore(str(self.data_dir / "patterns"))

        # =====================================================================
        # ADD NEW BRAIN CAPABILITIES
        # =====================================================================

        # Specialized memories (NEW - not in knowledge/)
        self.page_memory = PageMemory(str(self.brain_dir / "memory"))
        self.error_memory = ErrorMemory(str(self.brain_dir / "memory"))
        self.workflow_memory = WorkflowMemory(str(self.brain_dir / "memory"))

        # Decision engine (uses all memory systems)
        self.decision_engine = DecisionEngine(
            page_memory=self.page_memory,
            action_memory=None,  # Use knowledge_index instead
            error_memory=self.error_memory,
            workflow_memory=self.workflow_memory,
            knowledge_index=self.knowledge_index  # Pass existing knowledge
        )

        # AI Gateway with token budgeting (NEW)
        provider = AIProvider(self.config.ai_provider)
        self.ai_gateway = AIGateway(str(self.brain_dir), provider)
        self.ai_gateway.set_budget(
            daily_limit=self.config.daily_token_budget,
            per_test_limit=self.config.per_test_token_budget
        )

        # State tracking
        self._initialized = False
        self._current_page_type = "unknown"
        self._current_url = ""
        self._current_domain = ""
        self._session_active = False
        self._test_id: Optional[str] = None

        # Statistics
        self.decisions_made = 0
        self.ai_calls_avoided = 0
        self.knowledge_hits = 0

        logger.info("[BRAIN] QA Brain initialized (integrated with knowledge systems)")

    def set_learning_engine(self, learning_engine: LearningEngine):
        """Set the learning engine (called by agent after init)"""
        self.learning_engine = learning_engine

    async def initialize(self):
        """Initialize the brain"""
        if self._initialized:
            return

        self._initialized = True
        logger.info(f"[BRAIN] Page memories: {self.page_memory.get_stats()['count']}")
        logger.info(f"[BRAIN] Error memories: {self.error_memory.get_stats()['count']}")
        logger.info(f"[BRAIN] Workflow memories: {self.workflow_memory.get_stats()['count']}")

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    def start_test_session(self, test_id: str, domain: str = ""):
        """Start a new test session"""
        self._session_active = True
        self._test_id = test_id
        self._current_domain = domain
        self.ai_gateway.start_test()
        logger.info(f"[BRAIN] Started test session: {test_id}")

    def end_test_session(self, success: bool = True):
        """End the current test session"""
        if self._session_active:
            # Save workflow if we tracked pages
            if hasattr(self, '_page_sequence') and len(self._page_sequence) > 1:
                self.workflow_memory.remember_workflow(
                    name=self._test_id or "unknown",
                    page_sequence=self._page_sequence,
                    action_sequence=getattr(self, '_action_sequence', []),
                    duration_ms=int((time.time() - getattr(self, '_session_start', time.time())) * 1000),
                    completed=success
                )

            # Flush memories
            self.page_memory.flush()
            self.error_memory.flush()
            self.workflow_memory.flush()

            self._session_active = False
            logger.info(f"[BRAIN] Ended test session: {self._test_id}")

    # =========================================================================
    # CORE DECISION METHODS
    # =========================================================================

    async def find_element(
        self,
        intent: str,
        page=None,
        allow_ai: bool = True
    ) -> Tuple[Optional[str], float, str]:
        """
        Find the best selector for an element.

        Uses the integrated approach:
        1. Check knowledge_index (existing selectors)
        2. Check page_memory (page-specific elements)
        3. Use heuristics
        4. AI fallback (if budget allows)

        Returns:
            Tuple of (selector, confidence, source)
        """
        self.decisions_made += 1

        # 1. Check existing knowledge index first (O(1) lookup)
        knowledge_result = self._check_knowledge_index(intent)
        if knowledge_result:
            self.knowledge_hits += 1
            self.ai_calls_avoided += 1
            return knowledge_result

        # 2. Check page-specific memory
        page_selector = self.page_memory.get_known_element(self._current_url, intent)
        if page_selector:
            self.ai_calls_avoided += 1
            return (page_selector, 0.8, "page_memory")

        # 3. Use decision engine (heuristics)
        request = DecisionRequest(
            decision_type=DecisionType.FIND_ELEMENT,
            context={
                "intent": intent,
                "page_type": self._current_page_type,
                "url": self._current_url,
                "domain": self._current_domain
            },
            min_confidence=self.config.min_confidence_threshold,
            allow_ai_fallback=allow_ai
        )

        decision = self.decision_engine.decide(request)

        if decision.source in (DecisionSource.MEMORY, DecisionSource.HEURISTIC):
            if decision.confidence >= self.config.min_confidence_threshold:
                self.ai_calls_avoided += 1
                return (decision.value, decision.confidence, decision.source.value)

        # 4. AI fallback (token-budgeted)
        if allow_ai and self.config.enable_ai_fallback and page:
            ai_response = await self.ai_gateway.find_element(
                intent=intent,
                page_context=f"Page: {self._current_page_type}, URL: {self._current_url}"
            )

            if ai_response.success:
                selector = ai_response.content.strip()
                # Learn for next time
                self._learn_element(intent, selector)
                return (selector, 0.9, "ai")

        # Return best we have
        if decision.value:
            return (decision.value, decision.confidence, decision.source.value)

        return (None, 0.0, "none")

    def _check_knowledge_index(self, intent: str) -> Optional[Tuple[str, float, str]]:
        """Check the existing knowledge index for a selector"""
        if not self.knowledge_index:
            return None

        # Try to find in knowledge index
        try:
            match = self.knowledge_index.find_best_selector(
                domain=self._current_domain,
                page=self._current_url,
                element_key=intent
            )
            if match and match.confidence >= self.config.min_confidence_threshold:
                return (match.selector, match.confidence, "knowledge_index")
        except Exception as e:
            logger.debug(f"[BRAIN] Knowledge lookup failed: {e}")

        return None

    async def handle_error(
        self,
        error_message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Decide how to handle an error.

        Uses error memory to find known recovery strategies.
        """
        self.decisions_made += 1

        # Check error memory first
        error_entry = self.error_memory.find_matching_error(error_message)
        if error_entry and error_entry.pattern.recovery_action:
            self.ai_calls_avoided += 1
            return {
                "error_type": error_entry.pattern.error_type,
                "recovery_action": error_entry.pattern.recovery_action,
                "confidence": error_entry.recovery_success_rate,
                "source": "error_memory"
            }

        # Use decision engine
        request = DecisionRequest(
            decision_type=DecisionType.HANDLE_ERROR,
            context={"error_message": error_message, **(context or {})}
        )

        decision = self.decision_engine.decide(request)

        if decision.value:
            self.ai_calls_avoided += 1
            return decision.value

        # AI fallback for unknown errors
        if self.config.enable_ai_fallback:
            ai_response = await self.ai_gateway.analyze_error(
                error_message=error_message,
                page_context=f"Page: {self._current_page_type}"
            )

            if ai_response.success:
                try:
                    import json
                    result = json.loads(ai_response.content)
                    # Learn this error
                    self.error_memory.remember_error(
                        error_type=result.get("error_type", "unknown"),
                        message=error_message,
                        recovery_action=result.get("recovery")
                    )
                    return result
                except:
                    pass

        return {"error_type": "unknown", "recovery_action": "retry"}

    def predict_next_page(self, last_action: str = "") -> Optional[str]:
        """Predict what page type comes next"""
        self.decisions_made += 1

        prediction = self.workflow_memory.predict_next_page(
            self._current_page_type,
            last_action
        )

        if prediction:
            self.ai_calls_avoided += 1

        return prediction

    def get_expected_wait_time(self, action: str = "navigate") -> int:
        """Get expected wait time based on learned patterns"""
        self.decisions_made += 1

        # Check page memory for this URL's typical load time
        page_entry = self.page_memory.find_by_url(self._current_url)
        if page_entry:
            self.ai_calls_avoided += 1
            return page_entry.typical_load_time_ms

        # Default waits
        defaults = {"navigate": 2000, "click": 500, "type": 200, "submit": 3000}
        return defaults.get(action, 1000)

    # =========================================================================
    # PAGE AWARENESS
    # =========================================================================

    async def observe_page(self, page) -> Dict[str, Any]:
        """
        Observe and learn from the current page.

        Call this when navigating to a new page.
        """
        try:
            start = time.time()

            # Create page signature
            signature = await self.page_memory.create_signature(page)
            load_time = int((time.time() - start) * 1000)

            # Update state
            self._current_page_type = signature.page_type
            self._current_url = self.page_memory.normalize_url(page.url)

            # Track page sequence for workflow learning
            if not hasattr(self, '_page_sequence'):
                self._page_sequence = []
                self._session_start = time.time()
            self._page_sequence.append(signature.page_type)

            # Remember this page
            if self.config.enable_learning:
                self.page_memory.remember_page(signature, load_time_ms=load_time)

            # Check if we know this page
            known = self.page_memory.find_by_signature(signature)

            return {
                "page_type": signature.page_type,
                "url_pattern": signature.url_pattern,
                "known": known is not None,
                "confidence": known.confidence if known else 0.5,
                "known_elements": known.known_elements if known else {},
                "typical_load_time": known.typical_load_time_ms if known else load_time
            }

        except Exception as e:
            logger.error(f"[BRAIN] Failed to observe page: {e}")
            return {"page_type": "unknown", "known": False}

    def set_context(self, page_type: str = None, url: str = None, domain: str = None):
        """Manually set context"""
        if page_type:
            self._current_page_type = page_type
        if url:
            self._current_url = url
        if domain:
            self._current_domain = domain

    # =========================================================================
    # LEARNING (Integrated with existing LearningEngine)
    # =========================================================================

    def learn_action_success(
        self,
        action_type: str,
        target: str,
        selector: str,
        execution_time_ms: int = 500
    ):
        """Learn from a successful action"""
        if not self.config.enable_learning:
            return

        # Use EXISTING learning engine if available
        if self.learning_engine:
            self.learning_engine.record_selector_result(
                domain=self._current_domain,
                page=self._current_url,
                element_key=target,
                selector=selector,
                success=True,
                execution_time_ms=execution_time_ms
            )

        # Also store in page memory for page-specific lookup
        self.page_memory.remember_page(
            signature=PageSignature(
                url_pattern=self._current_url,
                title_hash="",
                element_hash="",
                page_type=self._current_page_type
            ),
            elements={target: selector}
        )

    def learn_action_failure(
        self,
        action_type: str,
        target: str,
        selector: str,
        error_message: str
    ):
        """Learn from a failed action"""
        if not self.config.enable_learning:
            return

        # Use EXISTING learning engine
        if self.learning_engine:
            self.learning_engine.record_selector_result(
                domain=self._current_domain,
                page=self._current_url,
                element_key=target,
                selector=selector,
                success=False
            )

        # Store error pattern
        self.error_memory.remember_error(
            error_type="action_failure",
            message=error_message,
            field_hint=target
        )

    def _learn_element(self, intent: str, selector: str):
        """Learn a newly discovered element"""
        if not self.config.enable_learning:
            return

        # Store in page memory
        page_entry = self.page_memory.find_by_url(self._current_url)
        if page_entry:
            page_entry.known_elements[intent] = selector

        # Store in knowledge index
        if self.knowledge_index:
            try:
                self.knowledge_index.store_selector(
                    domain=self._current_domain,
                    page=self._current_url,
                    element_key=intent,
                    selector=selector,
                    selector_type="css",
                    learned_from="ai"
                )
            except Exception as e:
                logger.debug(f"[BRAIN] Failed to store in knowledge: {e}")

    def learn_error_recovery(self, error_message: str, recovery_action: str, success: bool):
        """Learn from error recovery"""
        if not self.config.enable_learning:
            return

        self.error_memory.remember_error(
            error_type="recovered" if success else "failed_recovery",
            message=error_message,
            recovery_action=recovery_action,
            recovery_worked=success
        )

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive brain statistics"""
        total = self.decisions_made or 1

        return {
            "summary": {
                "decisions_made": self.decisions_made,
                "ai_calls_avoided": self.ai_calls_avoided,
                "knowledge_hits": self.knowledge_hits,
                "ai_avoidance_rate": (self.ai_calls_avoided / total) * 100
            },
            "memories": {
                "pages": self.page_memory.get_stats(),
                "errors": self.error_memory.get_stats(),
                "workflows": self.workflow_memory.get_stats()
            },
            "decision_engine": self.decision_engine.get_stats(),
            "ai_gateway": self.ai_gateway.get_stats()
        }

    def get_token_usage(self) -> Dict[str, Any]:
        """Get token usage statistics"""
        return self.ai_gateway.get_stats()["budget"]

    def consolidate(self):
        """Save all memories to disk"""
        self.page_memory.flush()
        self.error_memory.flush()
        self.workflow_memory.flush()
        logger.info("[BRAIN] Consolidated all memories")

    def decay_old_knowledge(self, max_age_days: int = 30):
        """Remove old/unreliable knowledge"""
        self.page_memory.decay(max_age_days)
        self.error_memory.decay(max_age_days)
        self.workflow_memory.decay(max_age_days)


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_brain: Optional[QABrain] = None


def get_brain(config: BrainConfig = None) -> QABrain:
    """Get or create the global brain instance"""
    global _brain
    if _brain is None:
        _brain = QABrain(config)
    return _brain
