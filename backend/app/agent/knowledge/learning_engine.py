"""
Learning Engine

Processes test execution results to continuously improve the knowledge base.
This is the "brain" that learns from every interaction.

Learning Sources:
1. Execution Results - Learn from successful/failed selectors
2. Recovery Actions - Learn what fixes work for what problems
3. Pattern Recognition - Identify common action sequences
4. Cross-App Learning - Apply learnings across similar apps
"""

import json
import hashlib
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import threading
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class LearningType(Enum):
    """Types of learnings the engine can process"""
    SELECTOR_SUCCESS = "selector_success"
    SELECTOR_FAILURE = "selector_failure"
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAILURE = "recovery_failure"
    PATTERN_DISCOVERED = "pattern_discovered"
    ELEMENT_MAPPING = "element_mapping"


@dataclass
class LearningEvent:
    """Single learning event to be processed"""
    type: LearningType
    timestamp: str
    domain: str
    page: str
    element_key: str
    selector: str
    selector_type: str = "css"  # css, xpath, text, role
    context: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    execution_time_ms: int = 0
    ai_assisted: bool = False
    confidence: float = 1.0


@dataclass
class SelectorEvolution:
    """Tracks how a selector has evolved over time"""
    original_selector: str
    current_selector: str
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)
    total_attempts: int = 0
    total_successes: int = 0
    average_execution_time: float = 0.0


@dataclass
class PatternCandidate:
    """Potential pattern identified from action sequences"""
    action_sequence: List[Dict[str, Any]]
    occurrences: int = 1
    domains: List[str] = field(default_factory=list)
    pages: List[str] = field(default_factory=list)
    success_rate: float = 1.0
    first_seen: str = ""
    last_seen: str = ""


class LearningEngine:
    """
    Central learning engine that processes all learnings.

    Features:
    - Batch processing for efficiency
    - Confidence decay for stale learnings
    - Cross-domain knowledge transfer
    - Pattern mining from action sequences
    - Automatic cleanup of low-quality learnings
    """

    # Minimum confidence to keep a selector
    MIN_CONFIDENCE_THRESHOLD = 0.3

    # How much confidence decays per day without use
    CONFIDENCE_DECAY_RATE = 0.01

    # Minimum occurrences to promote a pattern
    PATTERN_PROMOTION_THRESHOLD = 3

    # Maximum events to batch before processing
    BATCH_SIZE = 100

    def __init__(self, knowledge_index, pattern_store, data_dir: str = "data/agent_knowledge"):
        """
        Initialize learning engine.

        Args:
            knowledge_index: KnowledgeIndex instance for storing learnings
            pattern_store: PatternStore instance for action patterns
            data_dir: Directory for persisting learning data
        """
        self.knowledge_index = knowledge_index
        self.pattern_store = pattern_store
        self.data_dir = Path(data_dir)

        # Pending events queue (thread-safe)
        self._pending_events: List[LearningEvent] = []
        self._lock = threading.Lock()

        # In-memory tracking structures
        self._selector_evolution: Dict[str, SelectorEvolution] = {}
        self._action_buffer: List[Dict[str, Any]] = []
        self._pattern_candidates: Dict[str, PatternCandidate] = defaultdict(PatternCandidate)

        # Session tracking
        self._session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self._session_learnings = 0

        # Load existing evolution data
        self._load_evolution_data()

    def _load_evolution_data(self):
        """Load selector evolution history from disk"""
        evolution_file = self.data_dir / "metrics" / "selector_evolution.json"
        if evolution_file.exists():
            try:
                with open(evolution_file, 'r') as f:
                    data = json.load(f)
                    for key, evo_data in data.items():
                        self._selector_evolution[key] = SelectorEvolution(
                            original_selector=evo_data.get("original_selector", ""),
                            current_selector=evo_data.get("current_selector", ""),
                            evolution_history=evo_data.get("evolution_history", []),
                            total_attempts=evo_data.get("total_attempts", 0),
                            total_successes=evo_data.get("total_successes", 0),
                            average_execution_time=evo_data.get("average_execution_time", 0.0)
                        )
            except Exception:
                pass

    def _save_evolution_data(self):
        """Save selector evolution history to disk"""
        evolution_file = self.data_dir / "metrics" / "selector_evolution.json"
        evolution_file.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for key, evo in self._selector_evolution.items():
            data[key] = {
                "original_selector": evo.original_selector,
                "current_selector": evo.current_selector,
                "evolution_history": evo.evolution_history,
                "total_attempts": evo.total_attempts,
                "total_successes": evo.total_successes,
                "average_execution_time": evo.average_execution_time
            }

        with open(evolution_file, 'w') as f:
            json.dump(data, f, indent=2)

    # ==================== Event Recording ====================

    def record_selector_result(
        self,
        domain: str,
        page: str,
        element_key: str,
        selector: str,
        success: bool,
        selector_type: str = "css",
        execution_time_ms: int = 0,
        ai_assisted: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Record the result of using a selector.

        Args:
            domain: Website domain
            page: Page identifier or URL path
            element_key: Element key/intent
            selector: The selector that was used
            success: Whether it worked
            selector_type: Type of selector (css, xpath, text, role)
            execution_time_ms: How long the action took
            ai_assisted: Whether AI was used to find this selector
            context: Additional context (element attributes, page state, etc.)
        """
        event = LearningEvent(
            type=LearningType.SELECTOR_SUCCESS if success else LearningType.SELECTOR_FAILURE,
            timestamp=datetime.utcnow().isoformat(),
            domain=domain,
            page=page,
            element_key=element_key,
            selector=selector,
            selector_type=selector_type,
            success=success,
            execution_time_ms=execution_time_ms,
            ai_assisted=ai_assisted,
            context=context or {}
        )

        self._queue_event(event)

        # Also record in action buffer for pattern mining
        self._action_buffer.append({
            "timestamp": event.timestamp,
            "domain": domain,
            "page": page,
            "action": "interact",
            "element": element_key,
            "selector": selector,
            "success": success
        })

    def record_recovery_attempt(
        self,
        domain: str,
        page: str,
        problem_type: str,
        recovery_action: str,
        success: bool,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Record a recovery attempt result.

        Args:
            domain: Website domain
            page: Page identifier
            problem_type: Type of problem encountered (stale_element, not_found, etc.)
            recovery_action: The recovery action taken
            success: Whether recovery worked
            context: Additional context
        """
        event = LearningEvent(
            type=LearningType.RECOVERY_SUCCESS if success else LearningType.RECOVERY_FAILURE,
            timestamp=datetime.utcnow().isoformat(),
            domain=domain,
            page=page,
            element_key=problem_type,
            selector=recovery_action,
            success=success,
            context=context or {}
        )

        self._queue_event(event)

    def record_element_mapping(
        self,
        domain: str,
        page: str,
        element_key: str,
        selectors: List[Dict[str, Any]],
        element_attributes: Dict[str, Any],
        ai_assisted: bool = False
    ):
        """
        Record a new element mapping (multiple selectors for one element).

        Args:
            domain: Website domain
            page: Page identifier
            element_key: Element key/intent
            selectors: List of selector dicts with 'selector', 'type', 'confidence'
            element_attributes: Element attributes for future reference
            ai_assisted: Whether AI was used
        """
        for sel_info in selectors:
            event = LearningEvent(
                type=LearningType.ELEMENT_MAPPING,
                timestamp=datetime.utcnow().isoformat(),
                domain=domain,
                page=page,
                element_key=element_key,
                selector=sel_info.get("selector", ""),
                selector_type=sel_info.get("type", "css"),
                confidence=sel_info.get("confidence", 0.8),
                ai_assisted=ai_assisted,
                context={"attributes": element_attributes}
            )
            self._queue_event(event)

    def record_action(
        self,
        domain: str,
        page: str,
        action_type: str,
        element_key: str,
        value: Optional[str] = None,
        success: bool = True
    ):
        """
        Record an action for pattern mining.

        Args:
            domain: Website domain
            page: Page identifier
            action_type: Type of action (click, type, select, etc.)
            element_key: Element interacted with
            value: Value typed/selected if applicable
            success: Whether action succeeded
        """
        self._action_buffer.append({
            "timestamp": datetime.utcnow().isoformat(),
            "domain": domain,
            "page": page,
            "action": action_type,
            "element": element_key,
            "value": value,
            "success": success
        })

        # Trigger pattern mining when buffer is large enough
        if len(self._action_buffer) >= 50:
            self._mine_patterns()

    def _queue_event(self, event: LearningEvent):
        """Add event to processing queue"""
        with self._lock:
            self._pending_events.append(event)

            # Auto-process when batch is full
            if len(self._pending_events) >= self.BATCH_SIZE:
                self._process_batch()

    # ==================== Batch Processing ====================

    def _process_batch(self):
        """Process all pending events"""
        with self._lock:
            events = self._pending_events.copy()
            self._pending_events.clear()

        if not events:
            return

        # Group events by type for efficient processing
        by_type: Dict[LearningType, List[LearningEvent]] = defaultdict(list)
        for event in events:
            by_type[event.type].append(event)

        # Process each type
        for event_type, type_events in by_type.items():
            if event_type in (LearningType.SELECTOR_SUCCESS, LearningType.SELECTOR_FAILURE):
                self._process_selector_events(type_events)
            elif event_type in (LearningType.RECOVERY_SUCCESS, LearningType.RECOVERY_FAILURE):
                self._process_recovery_events(type_events)
            elif event_type == LearningType.ELEMENT_MAPPING:
                self._process_mapping_events(type_events)

        self._session_learnings += len(events)

    def _process_selector_events(self, events: List[LearningEvent]):
        """Process selector success/failure events"""
        for event in events:
            # Update knowledge index
            self.knowledge_index.add_learning(
                domain=event.domain,
                page=event.page,
                element_key=event.element_key,
                selector=event.selector,
                selector_type=event.selector_type,
                success=event.success,
                ai_assisted=event.ai_assisted,
                context=event.context
            )

            # Update evolution tracking
            self._update_evolution(event)

            # If this was AI-assisted and successful, mark for cross-domain promotion
            if event.ai_assisted and event.success:
                self._consider_cross_domain_learning(event)

    def _process_recovery_events(self, events: List[LearningEvent]):
        """Process recovery attempt events"""
        for event in events:
            recovery_key = f"{event.element_key}:{event.selector}"

            # Load or create recovery data
            recovery_file = self.data_dir / "recovery" / f"{event.domain}_recovery.json"
            recovery_data = {}

            if recovery_file.exists():
                try:
                    with open(recovery_file, 'r') as f:
                        recovery_data = json.load(f)
                except Exception:
                    pass

            # Update recovery statistics
            if recovery_key not in recovery_data:
                recovery_data[recovery_key] = {
                    "problem_type": event.element_key,
                    "recovery_action": event.selector,
                    "attempts": 0,
                    "successes": 0,
                    "last_used": "",
                    "contexts": []
                }

            recovery_data[recovery_key]["attempts"] += 1
            if event.success:
                recovery_data[recovery_key]["successes"] += 1
            recovery_data[recovery_key]["last_used"] = event.timestamp

            # Keep last 5 contexts
            recovery_data[recovery_key]["contexts"].append(event.context)
            recovery_data[recovery_key]["contexts"] = recovery_data[recovery_key]["contexts"][-5:]

            # Save
            recovery_file.parent.mkdir(parents=True, exist_ok=True)
            with open(recovery_file, 'w') as f:
                json.dump(recovery_data, f, indent=2)

    def _process_mapping_events(self, events: List[LearningEvent]):
        """Process element mapping events"""
        for event in events:
            # Add to knowledge index with initial confidence
            self.knowledge_index.add_learning(
                domain=event.domain,
                page=event.page,
                element_key=event.element_key,
                selector=event.selector,
                selector_type=event.selector_type,
                success=True,  # New mappings are assumed correct
                ai_assisted=event.ai_assisted,
                context=event.context
            )

    def _update_evolution(self, event: LearningEvent):
        """Track how selectors evolve over time"""
        key = f"{event.domain}:{event.page}:{event.element_key}"

        if key not in self._selector_evolution:
            self._selector_evolution[key] = SelectorEvolution(
                original_selector=event.selector,
                current_selector=event.selector
            )

        evo = self._selector_evolution[key]
        evo.total_attempts += 1

        if event.success:
            evo.total_successes += 1
            evo.current_selector = event.selector

            # Update average execution time
            if event.execution_time_ms > 0:
                evo.average_execution_time = (
                    (evo.average_execution_time * (evo.total_attempts - 1) + event.execution_time_ms)
                    / evo.total_attempts
                )
        else:
            # Track evolution when selector changes
            if event.selector != evo.current_selector:
                evo.evolution_history.append({
                    "timestamp": event.timestamp,
                    "from": evo.current_selector,
                    "to": event.selector,
                    "reason": "failure_recovery"
                })

    def _consider_cross_domain_learning(self, event: LearningEvent):
        """
        Consider promoting a learning to global/cross-domain knowledge.

        AI-discovered selectors that work well are candidates for
        cross-domain patterns (e.g., common login patterns).
        """
        # Check if this matches a common pattern type
        element_lower = event.element_key.lower()

        common_patterns = [
            "login", "logout", "submit", "search", "cancel", "close",
            "save", "delete", "edit", "next", "prev", "back", "menu"
        ]

        matching_pattern = None
        for pattern in common_patterns:
            if pattern in element_lower:
                matching_pattern = pattern
                break

        if matching_pattern:
            # Save to global patterns
            global_file = self.data_dir / "global" / f"{matching_pattern}_patterns.json"
            global_patterns = {}

            if global_file.exists():
                try:
                    with open(global_file, 'r') as f:
                        global_patterns = json.load(f)
                except Exception:
                    pass

            # Add this selector
            selector_hash = hashlib.md5(event.selector.encode()).hexdigest()[:8]

            if selector_hash not in global_patterns:
                global_patterns[selector_hash] = {
                    "selector": event.selector,
                    "selector_type": event.selector_type,
                    "discovered_from": event.domain,
                    "first_seen": event.timestamp,
                    "domains_used": [event.domain],
                    "success_count": 0,
                    "failure_count": 0
                }

            global_patterns[selector_hash]["success_count"] += 1
            if event.domain not in global_patterns[selector_hash]["domains_used"]:
                global_patterns[selector_hash]["domains_used"].append(event.domain)

            # Save
            global_file.parent.mkdir(parents=True, exist_ok=True)
            with open(global_file, 'w') as f:
                json.dump(global_patterns, f, indent=2)

    # ==================== Pattern Mining ====================

    def _mine_patterns(self):
        """Mine action buffer for recurring patterns"""
        if len(self._action_buffer) < 10:
            return

        # Find sequences of 2-5 actions that repeat
        for seq_len in range(2, 6):
            self._find_sequences(seq_len)

        # Trim buffer to last 100 actions
        self._action_buffer = self._action_buffer[-100:]

        # Promote high-occurrence patterns
        self._promote_patterns()

    def _find_sequences(self, length: int):
        """Find repeating sequences of given length"""
        sequences: Dict[str, List[List[Dict]]] = defaultdict(list)

        for i in range(len(self._action_buffer) - length + 1):
            seq = self._action_buffer[i:i + length]

            # Create sequence fingerprint (action types + element intents)
            fingerprint = "|".join([
                f"{a['action']}:{self._normalize_element(a['element'])}"
                for a in seq
            ])

            sequences[fingerprint].append(seq)

        # Record sequences that occur multiple times
        for fingerprint, occurrences in sequences.items():
            if len(occurrences) >= 2:
                # Use first occurrence as canonical
                canonical = occurrences[0]

                if fingerprint not in self._pattern_candidates:
                    self._pattern_candidates[fingerprint] = PatternCandidate(
                        action_sequence=canonical,
                        first_seen=canonical[0]["timestamp"]
                    )

                candidate = self._pattern_candidates[fingerprint]
                candidate.occurrences = len(occurrences)
                candidate.last_seen = occurrences[-1][-1]["timestamp"]

                # Track domains and pages
                for occ in occurrences:
                    for action in occ:
                        if action["domain"] not in candidate.domains:
                            candidate.domains.append(action["domain"])
                        if action["page"] not in candidate.pages:
                            candidate.pages.append(action["page"])

    def _normalize_element(self, element: str) -> str:
        """Normalize element key for pattern matching"""
        # Remove specific IDs, just keep semantic meaning
        normalized = element.lower()
        normalized = re.sub(r'[0-9]+', '', normalized)  # Remove numbers
        normalized = re.sub(r'[-_]+', '_', normalized)  # Normalize separators
        return normalized.strip('_')

    def _promote_patterns(self):
        """Promote recurring patterns to the pattern store"""
        for fingerprint, candidate in list(self._pattern_candidates.items()):
            if candidate.occurrences >= self.PATTERN_PROMOTION_THRESHOLD:
                # Calculate success rate
                success_count = sum(
                    1 for a in candidate.action_sequence if a.get("success", True)
                )
                candidate.success_rate = success_count / len(candidate.action_sequence)

                # Only promote if success rate is good
                if candidate.success_rate >= 0.8:
                    self._create_pattern_from_candidate(fingerprint, candidate)

    def _create_pattern_from_candidate(self, fingerprint: str, candidate: PatternCandidate):
        """Create a pattern in the pattern store from a candidate"""
        # Generate pattern ID
        pattern_id = f"learned_{hashlib.md5(fingerprint.encode()).hexdigest()[:12]}"

        # Check if already exists
        if self.pattern_store.get_pattern(pattern_id):
            return

        # Convert action sequence to pattern steps
        steps = []
        variables = []

        for action in candidate.action_sequence:
            step = {
                "action": action["action"],
                "target": action.get("element"),
                "selectors": [action.get("selector")] if action.get("selector") else []
            }

            # If action has a value, make it a variable
            if action.get("value"):
                var_name = f"{action['action']}_{action['element']}_value".replace(" ", "_")
                step["value"] = f"${{{var_name}}}"
                variables.append(var_name)

            steps.append(step)

        # Infer pattern name and category
        name, category = self._infer_pattern_metadata(candidate.action_sequence)

        # Create the pattern
        pattern_data = {
            "id": pattern_id,
            "name": name,
            "category": category,
            "applicable_when": {
                "domains": candidate.domains[:5],  # Limit to 5 domains
                "learned": True
            },
            "steps": steps,
            "variables": variables,
            "success_indicators": [],
            "failure_indicators": [],
            "confidence": candidate.success_rate,
            "metadata": {
                "learned_from": candidate.domains[0] if candidate.domains else "unknown",
                "first_seen": candidate.first_seen,
                "occurrences": candidate.occurrences
            }
        }

        # Add to pattern store
        self.pattern_store.add_pattern(pattern_data)

        # Remove from candidates
        del self._pattern_candidates[fingerprint]

    def _infer_pattern_metadata(self, actions: List[Dict]) -> Tuple[str, str]:
        """Infer pattern name and category from actions"""
        action_types = [a["action"] for a in actions]
        elements = [a.get("element", "").lower() for a in actions]

        # Check for login pattern
        if any("login" in e or "username" in e or "email" in e for e in elements):
            if any("password" in e for e in elements):
                return "Learned Login Flow", "login"

        # Check for form submission
        if "click" in action_types and any("submit" in e or "save" in e for e in elements):
            return "Learned Form Submit", "form"

        # Check for search
        if any("search" in e for e in elements):
            return "Learned Search Flow", "search"

        # Check for navigation
        if any("nav" in e or "menu" in e for e in elements):
            return "Learned Navigation", "navigation"

        # Default
        return f"Learned Pattern ({len(actions)} steps)", "general"

    # ==================== Maintenance ====================

    def flush(self):
        """Force process all pending events"""
        self._process_batch()
        self._mine_patterns()
        self._save_evolution_data()

    def apply_confidence_decay(self, max_age_days: int = 90):
        """
        Apply confidence decay to old, unused selectors.

        This helps the system "forget" stale learnings over time.
        """
        self.knowledge_index.apply_confidence_decay(
            decay_rate=self.CONFIDENCE_DECAY_RATE,
            max_age_days=max_age_days
        )

    def cleanup_low_quality(self):
        """Remove learnings below minimum confidence threshold"""
        self.knowledge_index.cleanup_below_threshold(self.MIN_CONFIDENCE_THRESHOLD)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for current session"""
        return {
            "session_id": self._session_id,
            "total_learnings": self._session_learnings,
            "pending_events": len(self._pending_events),
            "pattern_candidates": len(self._pattern_candidates),
            "action_buffer_size": len(self._action_buffer),
            "evolution_entries": len(self._selector_evolution)
        }

    def get_learning_summary(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of learnings.

        Args:
            domain: Optional domain to filter by

        Returns:
            Summary statistics
        """
        summary = {
            "total_elements_known": 0,
            "total_selectors": 0,
            "average_confidence": 0.0,
            "ai_discovered_percentage": 0.0,
            "patterns_learned": 0,
            "recovery_strategies": 0
        }

        # Get from knowledge index (get_stats takes no arguments)
        try:
            index_stats = self.knowledge_index.get_stats()
            # Map field names correctly
            summary["total_elements_known"] = index_stats.get("total_elements", 0)
            summary["total_domains"] = index_stats.get("total_domains", 0)
            summary["cache_hit_rate"] = index_stats.get("cache_hit_rate", "0%")
            summary["total_lookups"] = index_stats.get("total_lookups", 0)
            summary["cache_hits"] = index_stats.get("cache_hits", 0)
            summary["cache_misses"] = index_stats.get("cache_misses", 0)
        except Exception as e:
            logger.warning(f"Could not get index stats: {e}")

        # Count learned patterns
        all_patterns = self.pattern_store.get_all_patterns()
        summary["patterns_learned"] = sum(
            1 for p in all_patterns
            if p.get("metadata", {}).get("learned_from")
        )

        # Count recovery strategies
        recovery_dir = self.data_dir / "recovery"
        if recovery_dir.exists():
            summary["recovery_strategies"] = len(list(recovery_dir.glob("*.json")))

        # Calculate AI dependency from recent execution stats if available
        # This tracks how many resolutions needed AI vs. were handled by KB/heuristics
        stats_file = self.data_dir / "execution_stats.json"
        if stats_file.exists():
            try:
                import json
                with open(stats_file) as f:
                    exec_stats = json.load(f)
                total_resolutions = exec_stats.get("total_resolutions", 0)
                ai_resolutions = exec_stats.get("ai_resolutions", 0)
                if total_resolutions > 0:
                    summary["ai_discovered_percentage"] = (ai_resolutions / total_resolutions) * 100
            except Exception:
                pass

        return summary

    def export_learnings(self, output_file: str, domain: Optional[str] = None):
        """
        Export all learnings to a file for backup or transfer.

        Args:
            output_file: Path to output file
            domain: Optional domain to filter by
        """
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0",
            "knowledge": self.knowledge_index.export_domain(domain) if domain else self.knowledge_index.export_all(),
            "patterns": [
                p for p in self.pattern_store.get_all_patterns()
                if not domain or domain in p.get("applicable_when", {}).get("domains", [])
            ],
            "evolution": {
                k: {
                    "original": v.original_selector,
                    "current": v.current_selector,
                    "attempts": v.total_attempts,
                    "successes": v.total_successes
                }
                for k, v in self._selector_evolution.items()
                if not domain or k.startswith(domain)
            }
        }

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

    def import_learnings(self, input_file: str, merge: bool = True):
        """
        Import learnings from a file.

        Args:
            input_file: Path to input file
            merge: If True, merge with existing. If False, replace.
        """
        with open(input_file, 'r') as f:
            import_data = json.load(f)

        # Import knowledge
        if "knowledge" in import_data:
            self.knowledge_index.import_data(import_data["knowledge"], merge=merge)

        # Import patterns
        if "patterns" in import_data:
            for pattern in import_data["patterns"]:
                if merge:
                    existing = self.pattern_store.get_pattern(pattern["id"])
                    if not existing:
                        self.pattern_store.add_pattern(pattern)
                else:
                    self.pattern_store.add_pattern(pattern)
