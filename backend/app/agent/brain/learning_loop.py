"""
Learning Loop for QA Brain
===========================

Continuously improves the brain based on execution outcomes.
Every action, success, or failure is a learning opportunity.

Learning happens:
- After every action (immediate feedback)
- After test completion (workflow learning)
- During idle time (memory consolidation)

This makes the system smarter over time.
"""

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from .memory import (
    PageMemory, ActionMemory, ErrorMemory, WorkflowMemory,
    PageSignature
)

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of learning events"""
    ACTION_SUCCESS = "action_success"
    ACTION_FAILURE = "action_failure"
    ELEMENT_FOUND = "element_found"
    ELEMENT_NOT_FOUND = "element_not_found"
    PAGE_LOADED = "page_loaded"
    ERROR_OCCURRED = "error_occurred"
    ERROR_RECOVERED = "error_recovered"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"


@dataclass
class LearningEvent:
    """An event that triggers learning"""
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningSession:
    """Tracks learning during a test session"""
    session_id: str
    started_at: float = field(default_factory=time.time)
    events: List[LearningEvent] = field(default_factory=list)
    page_sequence: List[str] = field(default_factory=list)
    action_sequence: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)
    total_actions: int = 0
    successful_actions: int = 0
    recovered_actions: int = 0


class LearningLoop:
    """
    The learning engine that makes the brain smarter over time.

    Responsibilities:
    - Process learning events
    - Update memory systems
    - Consolidate knowledge
    - Decay stale information
    """

    def __init__(
        self,
        page_memory: PageMemory,
        action_memory: ActionMemory,
        error_memory: ErrorMemory,
        workflow_memory: WorkflowMemory
    ):
        self.page_memory = page_memory
        self.action_memory = action_memory
        self.error_memory = error_memory
        self.workflow_memory = workflow_memory

        # Event queue for async processing
        self.event_queue: deque = deque(maxlen=1000)
        self._processing = False
        self._lock = threading.Lock()

        # Current session tracking
        self.current_session: Optional[LearningSession] = None

        # Learning statistics
        self.events_processed = 0
        self.patterns_learned = 0
        self.patterns_reinforced = 0

        # Callbacks
        self._on_learn: Optional[Callable[[str, Dict], None]] = None

    def start_session(self, session_id: str) -> LearningSession:
        """Start a new learning session"""
        self.current_session = LearningSession(session_id=session_id)
        logger.info(f"[LEARNING] Started session: {session_id}")
        return self.current_session

    def end_session(self, success: bool = True):
        """End the current learning session and consolidate learning"""
        if not self.current_session:
            return

        session = self.current_session

        # Learn workflow pattern
        if len(session.page_sequence) > 1:
            self.workflow_memory.remember_workflow(
                name=session.session_id,
                page_sequence=session.page_sequence,
                action_sequence=session.action_sequence,
                duration_ms=int((time.time() - session.started_at) * 1000),
                completed=success,
                failure_step=session.total_actions - 1 if not success else None
            )

        # Flush all memories to disk
        self.page_memory.flush()
        self.action_memory.flush()
        self.error_memory.flush()
        self.workflow_memory.flush()

        logger.info(f"[LEARNING] Ended session: {session.session_id} "
                   f"({session.successful_actions}/{session.total_actions} successful)")

        self.current_session = None

    def record_event(self, event: LearningEvent):
        """Record a learning event for processing"""
        with self._lock:
            self.event_queue.append(event)

        # Process immediately if not in batch mode
        self._process_event(event)

        # Update session if active
        if self.current_session:
            self.current_session.events.append(event)

            if event.event_type in (EventType.ACTION_SUCCESS, EventType.ACTION_FAILURE):
                self.current_session.total_actions += 1
                if event.event_type == EventType.ACTION_SUCCESS:
                    self.current_session.successful_actions += 1

                # Track action sequence
                action = event.data.get("action_type", "unknown")
                self.current_session.action_sequence.append(action)

            elif event.event_type == EventType.PAGE_LOADED:
                page_type = event.data.get("page_type", "unknown")
                self.current_session.page_sequence.append(page_type)

            elif event.event_type == EventType.ERROR_OCCURRED:
                error_msg = event.data.get("error_message", "")
                self.current_session.errors_encountered.append(error_msg)

            elif event.event_type == EventType.ERROR_RECOVERED:
                self.current_session.recovered_actions += 1

    def _process_event(self, event: LearningEvent):
        """Process a single learning event"""
        self.events_processed += 1

        try:
            if event.event_type == EventType.ACTION_SUCCESS:
                self._learn_from_success(event)
            elif event.event_type == EventType.ACTION_FAILURE:
                self._learn_from_failure(event)
            elif event.event_type == EventType.ELEMENT_FOUND:
                self._learn_element(event)
            elif event.event_type == EventType.PAGE_LOADED:
                self._learn_page(event)
            elif event.event_type == EventType.ERROR_OCCURRED:
                self._learn_error(event)
            elif event.event_type == EventType.ERROR_RECOVERED:
                self._learn_recovery(event)

        except Exception as e:
            logger.error(f"[LEARNING] Error processing event: {e}")

    def _learn_from_success(self, event: LearningEvent):
        """Learn from a successful action"""
        data = event.data
        context = event.context

        action_type = data.get("action_type", "")
        target = data.get("target", "")
        selector = data.get("selector", "")
        page_type = context.get("page_type", "unknown")
        url = context.get("url", "")

        if selector and target:
            # Remember this action pattern
            entry = self.action_memory.remember_action(
                action_type=action_type,
                target_intent=target,
                selector=selector,
                page_type=page_type,
                execution_time_ms=data.get("execution_time_ms"),
                success=True
            )

            # Also store in page memory
            if url:
                page_entry = self.page_memory.find_by_url(url)
                if page_entry:
                    page_entry.known_elements[target] = selector
                    page_entry.record_success()

            self.patterns_reinforced += 1

            if self._on_learn:
                self._on_learn("action_success", {
                    "target": target,
                    "selector": selector,
                    "confidence": entry.confidence
                })

    def _learn_from_failure(self, event: LearningEvent):
        """Learn from a failed action"""
        data = event.data
        context = event.context

        target = data.get("target", "")
        selector = data.get("selector", "")
        error_message = data.get("error_message", "")
        page_type = context.get("page_type", "unknown")

        if selector and target:
            # Record failure for this selector
            self.action_memory.remember_action(
                action_type=data.get("action_type", ""),
                target_intent=target,
                selector=selector,
                page_type=page_type,
                success=False
            )

        # Learn the error pattern
        if error_message:
            self.error_memory.remember_error(
                error_type="action_failure",
                message=error_message,
                field_hint=target
            )

    def _learn_element(self, event: LearningEvent):
        """Learn a newly discovered element"""
        data = event.data
        context = event.context

        intent = data.get("intent", "")
        selector = data.get("selector", "")
        url = context.get("url", "")
        page_type = context.get("page_type", "unknown")

        if intent and selector:
            # Store in action memory
            self.action_memory.remember_action(
                action_type="found",
                target_intent=intent,
                selector=selector,
                page_type=page_type,
                success=True
            )

            # Store in page memory
            if url:
                page_entry = self.page_memory.find_by_url(url)
                if page_entry:
                    page_entry.known_elements[intent] = selector

            self.patterns_learned += 1
            logger.debug(f"[LEARNING] Learned element: {intent} -> {selector}")

    def _learn_page(self, event: LearningEvent):
        """Learn about a page"""
        data = event.data
        context = event.context

        signature = data.get("signature")
        load_time_ms = data.get("load_time_ms", 1000)

        if signature:
            self.page_memory.remember_page(
                signature=signature,
                load_time_ms=load_time_ms
            )
            logger.debug(f"[LEARNING] Learned page: {signature.url_pattern}")

    def _learn_error(self, event: LearningEvent):
        """Learn about an error"""
        data = event.data

        error_type = data.get("error_type", "unknown")
        message = data.get("error_message", "")
        field_hint = data.get("field_hint")

        if message:
            self.error_memory.remember_error(
                error_type=error_type,
                message=message,
                field_hint=field_hint
            )

    def _learn_recovery(self, event: LearningEvent):
        """Learn from successful error recovery"""
        data = event.data

        error_message = data.get("error_message", "")
        recovery_action = data.get("recovery_action", "")

        if error_message and recovery_action:
            self.error_memory.remember_error(
                error_type="recovered",
                message=error_message,
                recovery_action=recovery_action,
                recovery_worked=True
            )

    # =========================================================================
    # KNOWLEDGE MAINTENANCE
    # =========================================================================

    def decay_old_knowledge(self, max_age_days: int = 30):
        """Remove old/unreliable knowledge"""
        self.page_memory.decay(max_age_days)
        self.action_memory.decay(max_age_days)
        self.error_memory.decay(max_age_days)
        self.workflow_memory.decay(max_age_days)

        logger.info("[LEARNING] Completed knowledge decay")

    def consolidate(self):
        """Consolidate learning - flush to disk"""
        self.page_memory.flush()
        self.action_memory.flush()
        self.error_memory.flush()
        self.workflow_memory.flush()

        logger.info(f"[LEARNING] Consolidated - {self.patterns_learned} new, "
                   f"{self.patterns_reinforced} reinforced")

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    def learn_successful_action(
        self,
        action_type: str,
        target: str,
        selector: str,
        page_type: str = "unknown",
        url: str = "",
        execution_time_ms: int = 500
    ):
        """Convenience method to record a successful action"""
        self.record_event(LearningEvent(
            event_type=EventType.ACTION_SUCCESS,
            data={
                "action_type": action_type,
                "target": target,
                "selector": selector,
                "execution_time_ms": execution_time_ms
            },
            context={
                "page_type": page_type,
                "url": url
            }
        ))

    def learn_failed_action(
        self,
        action_type: str,
        target: str,
        selector: str,
        error_message: str,
        page_type: str = "unknown"
    ):
        """Convenience method to record a failed action"""
        self.record_event(LearningEvent(
            event_type=EventType.ACTION_FAILURE,
            data={
                "action_type": action_type,
                "target": target,
                "selector": selector,
                "error_message": error_message
            },
            context={
                "page_type": page_type
            }
        ))

    def learn_page(self, signature: PageSignature, load_time_ms: int = 1000):
        """Convenience method to record a page load"""
        self.record_event(LearningEvent(
            event_type=EventType.PAGE_LOADED,
            data={
                "signature": signature,
                "load_time_ms": load_time_ms
            }
        ))

    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics"""
        return {
            "events_processed": self.events_processed,
            "patterns_learned": self.patterns_learned,
            "patterns_reinforced": self.patterns_reinforced,
            "page_memories": self.page_memory.get_stats(),
            "action_memories": self.action_memory.get_stats(),
            "error_memories": self.error_memory.get_stats(),
            "workflow_memories": self.workflow_memory.get_stats()
        }

    def set_callback(self, callback: Callable[[str, Dict], None]):
        """Set callback for learning events"""
        self._on_learn = callback
