"""
Memory Systems for QA Brain
============================

Four specialized memory systems that store learned patterns:

1. PageMemory: Remembers page layouts, element positions, page types
2. ActionMemory: Remembers action sequences, what works where
3. ErrorMemory: Remembers error patterns, recovery strategies
4. WorkflowMemory: Remembers complete test flows, predicts next steps

Each memory uses:
- Fingerprinting: Create unique signatures for fast matching
- Similarity Search: Find similar patterns without AI
- Confidence Scoring: Track reliability of each memory
- Decay: Older/unused memories fade over time
"""

import hashlib
import json
import logging
import math
import os
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# BASE CLASSES
# =============================================================================

@dataclass
class MemoryEntry:
    """Base class for all memory entries"""
    id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    confidence: float = 0.5  # 0.0 to 1.0
    success_count: int = 0
    failure_count: int = 0

    def access(self):
        """Record an access to this memory"""
        self.last_accessed = time.time()
        self.access_count += 1

    def record_success(self):
        """Record a successful use"""
        self.success_count += 1
        self.confidence = min(1.0, self.confidence + 0.05)
        self.access()

    def record_failure(self):
        """Record a failed use"""
        self.failure_count += 1
        self.confidence = max(0.0, self.confidence - 0.1)
        self.access()

    def get_reliability(self) -> float:
        """Calculate reliability based on success/failure ratio"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total

    def should_decay(self, max_age_days: int = 30) -> bool:
        """Check if this memory should decay due to age/non-use"""
        age_days = (time.time() - self.last_accessed) / 86400
        return age_days > max_age_days and self.confidence < 0.7


class BaseMemory:
    """Base class for all memory systems"""

    def __init__(self, data_dir: str, name: str):
        self.data_dir = Path(data_dir)
        self.name = name
        self.data_file = self.data_dir / f"{name}_memory.json"
        self.entries: Dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        self._dirty = False

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load memory from disk"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self._deserialize(data)
                logger.info(f"[MEMORY] Loaded {len(self.entries)} entries from {self.name}")
            except Exception as e:
                logger.error(f"[MEMORY] Failed to load {self.name}: {e}")

    def _save(self):
        """Save memory to disk"""
        if not self._dirty:
            return
        try:
            with self._lock:
                data = self._serialize()
                with open(self.data_file, 'w') as f:
                    json.dump(data, f, indent=2)
                self._dirty = False
        except Exception as e:
            logger.error(f"[MEMORY] Failed to save {self.name}: {e}")

    def _serialize(self) -> Dict:
        """Serialize memory to dict - override in subclass"""
        return {"entries": {}}

    def _deserialize(self, data: Dict):
        """Deserialize memory from dict - override in subclass"""
        pass

    def decay(self, max_age_days: int = 30):
        """Remove old/unreliable entries"""
        to_remove = []
        with self._lock:
            for key, entry in self.entries.items():
                if entry.should_decay(max_age_days):
                    to_remove.append(key)

            for key in to_remove:
                del self.entries[key]

            if to_remove:
                self._dirty = True
                logger.info(f"[MEMORY] Decayed {len(to_remove)} entries from {self.name}")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if not self.entries:
            return {"count": 0, "avg_confidence": 0, "avg_reliability": 0}

        return {
            "count": len(self.entries),
            "avg_confidence": sum(e.confidence for e in self.entries.values()) / len(self.entries),
            "avg_reliability": sum(e.get_reliability() for e in self.entries.values()) / len(self.entries)
        }

    def flush(self):
        """Force save to disk"""
        self._dirty = True
        self._save()


# =============================================================================
# PAGE MEMORY
# =============================================================================

@dataclass
class PageSignature:
    """Unique signature/fingerprint for a page"""
    url_pattern: str  # URL with dynamic parts normalized
    title_hash: str  # Hash of page title
    element_hash: str  # Hash of key element structure
    page_type: str  # login, form, list, etc.
    form_count: int = 0
    input_count: int = 0
    button_count: int = 0
    link_count: int = 0

    def to_fingerprint(self) -> str:
        """Create a unique fingerprint for matching"""
        data = f"{self.url_pattern}|{self.page_type}|{self.form_count}|{self.input_count}"
        return hashlib.md5(data.encode()).hexdigest()[:16]


@dataclass
class PageMemoryEntry(MemoryEntry):
    """Memory entry for a page"""
    signature: PageSignature = None
    known_elements: Dict[str, str] = field(default_factory=dict)  # intent -> selector
    typical_load_time_ms: int = 1000
    common_errors: List[str] = field(default_factory=list)
    navigation_targets: Dict[str, str] = field(default_factory=dict)  # target_page -> how_to_get_there


class PageMemory(BaseMemory):
    """
    Remembers page layouts, elements, and behaviors.

    Enables:
    - Quick page type detection
    - Known element lookup
    - Load time prediction
    - Navigation path prediction
    """

    def __init__(self, data_dir: str):
        super().__init__(data_dir, "page")
        self._url_index: Dict[str, str] = {}  # url_pattern -> entry_id
        self._fingerprint_index: Dict[str, str] = {}  # fingerprint -> entry_id

    def _serialize(self) -> Dict:
        entries_data = {}
        for key, entry in self.entries.items():
            entries_data[key] = {
                "id": entry.id,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "confidence": entry.confidence,
                "success_count": entry.success_count,
                "failure_count": entry.failure_count,
                "signature": asdict(entry.signature) if entry.signature else None,
                "known_elements": entry.known_elements,
                "typical_load_time_ms": entry.typical_load_time_ms,
                "common_errors": entry.common_errors,
                "navigation_targets": entry.navigation_targets
            }
        return {"entries": entries_data}

    def _deserialize(self, data: Dict):
        for key, entry_data in data.get("entries", {}).items():
            sig_data = entry_data.get("signature")
            signature = PageSignature(**sig_data) if sig_data else None

            entry = PageMemoryEntry(
                id=entry_data["id"],
                created_at=entry_data.get("created_at", time.time()),
                last_accessed=entry_data.get("last_accessed", time.time()),
                access_count=entry_data.get("access_count", 0),
                confidence=entry_data.get("confidence", 0.5),
                success_count=entry_data.get("success_count", 0),
                failure_count=entry_data.get("failure_count", 0),
                signature=signature,
                known_elements=entry_data.get("known_elements", {}),
                typical_load_time_ms=entry_data.get("typical_load_time_ms", 1000),
                common_errors=entry_data.get("common_errors", []),
                navigation_targets=entry_data.get("navigation_targets", {})
            )
            self.entries[key] = entry

            if signature:
                self._url_index[signature.url_pattern] = key
                self._fingerprint_index[signature.to_fingerprint()] = key

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL by removing dynamic parts"""
        # Remove query params
        url = re.sub(r'\?.*$', '', url)
        # Replace numeric IDs with placeholder
        url = re.sub(r'/\d+', '/:id', url)
        # Replace UUIDs
        url = re.sub(r'/[a-f0-9-]{36}', '/:uuid', url)
        return url

    async def create_signature(self, page) -> PageSignature:
        """Create a signature for the current page"""
        try:
            url = self.normalize_url(page.url)
            title = await page.title()

            # Count elements
            forms = await page.query_selector_all('form')
            inputs = await page.query_selector_all('input:not([type="hidden"])')
            buttons = await page.query_selector_all('button, input[type="submit"]')
            links = await page.query_selector_all('a[href]')

            # Detect page type
            page_type = await self._detect_page_type(page, url, title, len(inputs))

            # Create element structure hash
            element_structure = f"f{len(forms)}i{len(inputs)}b{len(buttons)}l{len(links)}"
            element_hash = hashlib.md5(element_structure.encode()).hexdigest()[:8]

            return PageSignature(
                url_pattern=url,
                title_hash=hashlib.md5(title.encode()).hexdigest()[:8],
                element_hash=element_hash,
                page_type=page_type,
                form_count=len(forms),
                input_count=len(inputs),
                button_count=len(buttons),
                link_count=len(links)
            )
        except Exception as e:
            logger.error(f"[PAGE-MEMORY] Failed to create signature: {e}")
            return PageSignature(
                url_pattern=self.normalize_url(page.url),
                title_hash="",
                element_hash="",
                page_type="unknown"
            )

    async def _detect_page_type(self, page, url: str, title: str, input_count: int) -> str:
        """Detect page type from URL and content"""
        combined = f"{url} {title}".lower()

        if any(x in combined for x in ['login', 'signin', 'sign-in']):
            return "login"
        if any(x in combined for x in ['register', 'signup', 'sign-up', 'create-account']):
            return "register"
        if any(x in combined for x in ['checkout', 'payment', 'cart']):
            return "checkout"
        if any(x in combined for x in ['dashboard', 'home', 'overview']):
            return "dashboard"
        if any(x in combined for x in ['search', 'find', 'results']):
            return "search"
        if any(x in combined for x in ['settings', 'profile', 'account']):
            return "settings"
        if any(x in combined for x in ['error', '404', '500']):
            return "error"

        # Check for password field
        try:
            pw_field = await page.query_selector('input[type="password"]')
            if pw_field:
                if input_count > 3:
                    return "register"
                return "login"
        except:
            pass

        if input_count > 2:
            return "form"

        return "unknown"

    def find_by_url(self, url: str) -> Optional[PageMemoryEntry]:
        """Find page memory by URL"""
        normalized = self.normalize_url(url)
        entry_id = self._url_index.get(normalized)
        if entry_id and entry_id in self.entries:
            entry = self.entries[entry_id]
            entry.access()
            return entry
        return None

    def find_by_signature(self, signature: PageSignature) -> Optional[PageMemoryEntry]:
        """Find page memory by signature"""
        fingerprint = signature.to_fingerprint()
        entry_id = self._fingerprint_index.get(fingerprint)
        if entry_id and entry_id in self.entries:
            entry = self.entries[entry_id]
            entry.access()
            return entry
        return None

    def remember_page(
        self,
        signature: PageSignature,
        elements: Dict[str, str] = None,
        load_time_ms: int = None
    ) -> PageMemoryEntry:
        """Store or update page memory"""
        fingerprint = signature.to_fingerprint()

        with self._lock:
            if fingerprint in self._fingerprint_index:
                entry_id = self._fingerprint_index[fingerprint]
                entry = self.entries[entry_id]

                # Update existing entry
                if elements:
                    entry.known_elements.update(elements)
                if load_time_ms:
                    # Moving average for load time
                    entry.typical_load_time_ms = int(
                        0.7 * entry.typical_load_time_ms + 0.3 * load_time_ms
                    )
                entry.access()
            else:
                # Create new entry
                entry_id = fingerprint
                entry = PageMemoryEntry(
                    id=entry_id,
                    signature=signature,
                    known_elements=elements or {},
                    typical_load_time_ms=load_time_ms or 1000
                )
                self.entries[entry_id] = entry
                self._url_index[signature.url_pattern] = entry_id
                self._fingerprint_index[fingerprint] = entry_id

            self._dirty = True

        return entry

    def get_known_element(self, url: str, intent: str) -> Optional[str]:
        """Get a known element selector for an intent on a page"""
        entry = self.find_by_url(url)
        if entry and intent in entry.known_elements:
            return entry.known_elements[intent]
        return None


# =============================================================================
# ACTION MEMORY
# =============================================================================

@dataclass
class ActionPattern:
    """Pattern for a successful action"""
    action_type: str  # click, type, etc.
    target_intent: str  # what we're trying to interact with
    selector: str  # the selector that worked
    page_type: str  # type of page this works on
    context_hints: List[str] = field(default_factory=list)  # other elements present


@dataclass
class ActionMemoryEntry(MemoryEntry):
    """Memory entry for an action pattern"""
    pattern: ActionPattern = None
    avg_execution_time_ms: int = 500
    preconditions: List[str] = field(default_factory=list)  # what must be true before
    postconditions: List[str] = field(default_factory=list)  # what should be true after


class ActionMemory(BaseMemory):
    """
    Remembers successful action patterns.

    Enables:
    - Quick selector lookup for intents
    - Action timing prediction
    - Pre/post condition validation
    """

    def __init__(self, data_dir: str):
        super().__init__(data_dir, "action")
        self._intent_index: Dict[str, List[str]] = defaultdict(list)  # intent -> [entry_ids]
        self._selector_index: Dict[str, str] = {}  # selector -> entry_id

    def _serialize(self) -> Dict:
        entries_data = {}
        for key, entry in self.entries.items():
            entries_data[key] = {
                "id": entry.id,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "confidence": entry.confidence,
                "success_count": entry.success_count,
                "failure_count": entry.failure_count,
                "pattern": asdict(entry.pattern) if entry.pattern else None,
                "avg_execution_time_ms": entry.avg_execution_time_ms,
                "preconditions": entry.preconditions,
                "postconditions": entry.postconditions
            }
        return {"entries": entries_data}

    def _deserialize(self, data: Dict):
        for key, entry_data in data.get("entries", {}).items():
            pattern_data = entry_data.get("pattern")
            pattern = ActionPattern(**pattern_data) if pattern_data else None

            entry = ActionMemoryEntry(
                id=entry_data["id"],
                created_at=entry_data.get("created_at", time.time()),
                last_accessed=entry_data.get("last_accessed", time.time()),
                access_count=entry_data.get("access_count", 0),
                confidence=entry_data.get("confidence", 0.5),
                success_count=entry_data.get("success_count", 0),
                failure_count=entry_data.get("failure_count", 0),
                pattern=pattern,
                avg_execution_time_ms=entry_data.get("avg_execution_time_ms", 500),
                preconditions=entry_data.get("preconditions", []),
                postconditions=entry_data.get("postconditions", [])
            )
            self.entries[key] = entry

            if pattern:
                self._intent_index[pattern.target_intent].append(key)
                self._selector_index[pattern.selector] = key

    @staticmethod
    def normalize_intent(intent: str) -> str:
        """Normalize intent for matching"""
        intent = intent.lower().strip()
        # Remove common prefixes
        for prefix in ['click on ', 'click ', 'tap ', 'press ', 'the ', 'a ', 'an ']:
            if intent.startswith(prefix):
                intent = intent[len(prefix):]
        # Remove quotes
        intent = intent.strip('"\'')
        return intent

    def find_by_intent(
        self,
        intent: str,
        page_type: str = None,
        min_confidence: float = 0.3
    ) -> List[ActionMemoryEntry]:
        """Find action memories matching an intent"""
        normalized = self.normalize_intent(intent)
        results = []

        # Direct match
        if normalized in self._intent_index:
            for entry_id in self._intent_index[normalized]:
                if entry_id in self.entries:
                    entry = self.entries[entry_id]
                    if entry.confidence >= min_confidence:
                        if page_type is None or entry.pattern.page_type == page_type:
                            results.append(entry)

        # Fuzzy match - check for word overlap
        if not results:
            intent_words = set(normalized.split())
            for stored_intent, entry_ids in self._intent_index.items():
                stored_words = set(stored_intent.split())
                overlap = len(intent_words & stored_words)
                if overlap > 0 and overlap >= len(intent_words) * 0.5:
                    for entry_id in entry_ids:
                        if entry_id in self.entries:
                            entry = self.entries[entry_id]
                            if entry.confidence >= min_confidence:
                                results.append(entry)

        # Sort by confidence
        results.sort(key=lambda e: e.confidence, reverse=True)
        return results

    def remember_action(
        self,
        action_type: str,
        target_intent: str,
        selector: str,
        page_type: str,
        execution_time_ms: int = None,
        success: bool = True
    ) -> ActionMemoryEntry:
        """Store or update action memory"""
        normalized_intent = self.normalize_intent(target_intent)
        entry_id = hashlib.md5(f"{normalized_intent}|{selector}".encode()).hexdigest()[:16]

        with self._lock:
            if entry_id in self.entries:
                entry = self.entries[entry_id]
                if success:
                    entry.record_success()
                else:
                    entry.record_failure()

                if execution_time_ms:
                    entry.avg_execution_time_ms = int(
                        0.7 * entry.avg_execution_time_ms + 0.3 * execution_time_ms
                    )
            else:
                pattern = ActionPattern(
                    action_type=action_type,
                    target_intent=normalized_intent,
                    selector=selector,
                    page_type=page_type
                )
                entry = ActionMemoryEntry(
                    id=entry_id,
                    pattern=pattern,
                    avg_execution_time_ms=execution_time_ms or 500
                )
                if success:
                    entry.record_success()

                self.entries[entry_id] = entry
                self._intent_index[normalized_intent].append(entry_id)
                self._selector_index[selector] = entry_id

            self._dirty = True

        return entry


# =============================================================================
# ERROR MEMORY
# =============================================================================

@dataclass
class ErrorPattern:
    """Pattern for a recognized error"""
    error_type: str  # validation, server, network, etc.
    message_pattern: str  # regex pattern for error message
    field_hint: Optional[str] = None  # which field caused it
    recovery_action: Optional[str] = None  # how to recover


@dataclass
class ErrorMemoryEntry(MemoryEntry):
    """Memory entry for an error pattern"""
    pattern: ErrorPattern = None
    recovery_success_rate: float = 0.0
    common_causes: List[str] = field(default_factory=list)


class ErrorMemory(BaseMemory):
    """
    Remembers error patterns and recovery strategies.

    Enables:
    - Quick error classification
    - Recovery strategy selection
    - Error prediction
    """

    def __init__(self, data_dir: str):
        super().__init__(data_dir, "error")
        self._pattern_index: List[Tuple[str, str]] = []  # [(regex, entry_id)]

    def _serialize(self) -> Dict:
        entries_data = {}
        for key, entry in self.entries.items():
            entries_data[key] = {
                "id": entry.id,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "confidence": entry.confidence,
                "success_count": entry.success_count,
                "failure_count": entry.failure_count,
                "pattern": asdict(entry.pattern) if entry.pattern else None,
                "recovery_success_rate": entry.recovery_success_rate,
                "common_causes": entry.common_causes
            }
        return {"entries": entries_data}

    def _deserialize(self, data: Dict):
        for key, entry_data in data.get("entries", {}).items():
            pattern_data = entry_data.get("pattern")
            pattern = ErrorPattern(**pattern_data) if pattern_data else None

            entry = ErrorMemoryEntry(
                id=entry_data["id"],
                created_at=entry_data.get("created_at", time.time()),
                last_accessed=entry_data.get("last_accessed", time.time()),
                access_count=entry_data.get("access_count", 0),
                confidence=entry_data.get("confidence", 0.5),
                success_count=entry_data.get("success_count", 0),
                failure_count=entry_data.get("failure_count", 0),
                pattern=pattern,
                recovery_success_rate=entry_data.get("recovery_success_rate", 0.0),
                common_causes=entry_data.get("common_causes", [])
            )
            self.entries[key] = entry

            if pattern:
                self._pattern_index.append((pattern.message_pattern, key))

    def find_matching_error(self, error_message: str) -> Optional[ErrorMemoryEntry]:
        """Find error memory matching a message"""
        error_lower = error_message.lower()

        for pattern, entry_id in self._pattern_index:
            try:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    if entry_id in self.entries:
                        entry = self.entries[entry_id]
                        entry.access()
                        return entry
            except re.error:
                # Invalid regex - skip
                pass

        return None

    def remember_error(
        self,
        error_type: str,
        message: str,
        field_hint: str = None,
        recovery_action: str = None,
        recovery_worked: bool = None
    ) -> ErrorMemoryEntry:
        """Store or update error memory"""
        # Create pattern from message
        pattern_text = self._create_pattern(message)
        entry_id = hashlib.md5(pattern_text.encode()).hexdigest()[:16]

        with self._lock:
            if entry_id in self.entries:
                entry = self.entries[entry_id]
                entry.access()

                if recovery_worked is not None:
                    if recovery_worked:
                        entry.record_success()
                    else:
                        entry.record_failure()
                    entry.recovery_success_rate = entry.get_reliability()
            else:
                pattern = ErrorPattern(
                    error_type=error_type,
                    message_pattern=pattern_text,
                    field_hint=field_hint,
                    recovery_action=recovery_action
                )
                entry = ErrorMemoryEntry(
                    id=entry_id,
                    pattern=pattern
                )
                self.entries[entry_id] = entry
                self._pattern_index.append((pattern_text, entry_id))

            self._dirty = True

        return entry

    @staticmethod
    def _create_pattern(message: str) -> str:
        """Create a regex pattern from an error message"""
        # Escape special regex chars
        pattern = re.escape(message.lower())
        # Replace common variable parts
        pattern = re.sub(r'\\\d+', r'\\d+', pattern)  # numbers
        pattern = re.sub(r'\\".+?\\"', r'.+?', pattern)  # quoted strings
        return pattern


# =============================================================================
# WORKFLOW MEMORY
# =============================================================================

@dataclass
class WorkflowPattern:
    """Pattern for a workflow (sequence of pages/actions)"""
    name: str
    page_sequence: List[str]  # sequence of page types
    action_sequence: List[str]  # sequence of action intents
    typical_duration_ms: int = 0


@dataclass
class WorkflowMemoryEntry(MemoryEntry):
    """Memory entry for a workflow pattern"""
    pattern: WorkflowPattern = None
    completion_rate: float = 0.0
    common_failure_points: List[int] = field(default_factory=list)  # step indices


class WorkflowMemory(BaseMemory):
    """
    Remembers complete test workflows.

    Enables:
    - Workflow prediction (what comes next?)
    - Failure point prediction
    - Test completion estimation
    """

    def __init__(self, data_dir: str):
        super().__init__(data_dir, "workflow")
        self._sequence_index: Dict[str, List[str]] = defaultdict(list)  # first_page -> [entry_ids]

    def _serialize(self) -> Dict:
        entries_data = {}
        for key, entry in self.entries.items():
            entries_data[key] = {
                "id": entry.id,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "confidence": entry.confidence,
                "success_count": entry.success_count,
                "failure_count": entry.failure_count,
                "pattern": asdict(entry.pattern) if entry.pattern else None,
                "completion_rate": entry.completion_rate,
                "common_failure_points": entry.common_failure_points
            }
        return {"entries": entries_data}

    def _deserialize(self, data: Dict):
        for key, entry_data in data.get("entries", {}).items():
            pattern_data = entry_data.get("pattern")
            pattern = WorkflowPattern(**pattern_data) if pattern_data else None

            entry = WorkflowMemoryEntry(
                id=entry_data["id"],
                created_at=entry_data.get("created_at", time.time()),
                last_accessed=entry_data.get("last_accessed", time.time()),
                access_count=entry_data.get("access_count", 0),
                confidence=entry_data.get("confidence", 0.5),
                success_count=entry_data.get("success_count", 0),
                failure_count=entry_data.get("failure_count", 0),
                pattern=pattern,
                completion_rate=entry_data.get("completion_rate", 0.0),
                common_failure_points=entry_data.get("common_failure_points", [])
            )
            self.entries[key] = entry

            if pattern and pattern.page_sequence:
                self._sequence_index[pattern.page_sequence[0]].append(key)

    def predict_next_page(self, current_page_type: str, action_performed: str) -> Optional[str]:
        """Predict what page type comes next"""
        # Find workflows starting with current page type
        if current_page_type not in self._sequence_index:
            return None

        for entry_id in self._sequence_index[current_page_type]:
            if entry_id in self.entries:
                entry = self.entries[entry_id]
                pattern = entry.pattern

                # Find current position in sequence
                if current_page_type in pattern.page_sequence:
                    idx = pattern.page_sequence.index(current_page_type)
                    if idx + 1 < len(pattern.page_sequence):
                        return pattern.page_sequence[idx + 1]

        return None

    def remember_workflow(
        self,
        name: str,
        page_sequence: List[str],
        action_sequence: List[str],
        duration_ms: int,
        completed: bool,
        failure_step: int = None
    ) -> WorkflowMemoryEntry:
        """Store or update workflow memory"""
        entry_id = hashlib.md5(f"{name}|{'->'.join(page_sequence)}".encode()).hexdigest()[:16]

        with self._lock:
            if entry_id in self.entries:
                entry = self.entries[entry_id]

                if completed:
                    entry.record_success()
                else:
                    entry.record_failure()
                    if failure_step is not None:
                        entry.common_failure_points.append(failure_step)

                entry.completion_rate = entry.get_reliability()
                entry.pattern.typical_duration_ms = int(
                    0.7 * entry.pattern.typical_duration_ms + 0.3 * duration_ms
                )
            else:
                pattern = WorkflowPattern(
                    name=name,
                    page_sequence=page_sequence,
                    action_sequence=action_sequence,
                    typical_duration_ms=duration_ms
                )
                entry = WorkflowMemoryEntry(
                    id=entry_id,
                    pattern=pattern
                )
                if completed:
                    entry.record_success()

                self.entries[entry_id] = entry
                if page_sequence:
                    self._sequence_index[page_sequence[0]].append(entry_id)

            self._dirty = True

        return entry
