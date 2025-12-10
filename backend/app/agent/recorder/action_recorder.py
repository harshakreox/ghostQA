"""
Action Recorder

Records human interactions with web applications to learn
element selectors and action patterns from demonstrations.

This is the "learning by watching" component - it observes
human testers and learns their techniques.
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of recordable actions"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    CLEAR = "clear"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    HOVER = "hover"
    SCROLL = "scroll"
    DRAG = "drag"
    DROP = "drop"
    UPLOAD = "upload"
    NAVIGATE = "navigate"
    BACK = "back"
    FORWARD = "forward"
    REFRESH = "refresh"
    WAIT = "wait"
    ASSERT = "assert"
    SCREENSHOT = "screenshot"
    KEY_PRESS = "key_press"
    FOCUS = "focus"
    BLUR = "blur"


@dataclass
class ElementSnapshot:
    """Snapshot of element state at time of interaction"""
    tag_name: str
    element_type: str
    text_content: str
    attributes: Dict[str, str]
    bounding_box: Optional[Dict[str, float]]
    is_visible: bool
    is_enabled: bool
    computed_styles: Dict[str, str] = field(default_factory=dict)
    parent_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordedAction:
    """A single recorded action"""
    action_id: str
    action_type: ActionType
    timestamp: str
    url: str
    page_title: str

    # Element information
    element_snapshot: Optional[ElementSnapshot]
    selectors: List[Dict[str, Any]]  # Multiple selector strategies

    # Action-specific data
    value: Optional[str] = None  # For type, select actions
    key: Optional[str] = None  # For key_press
    coordinates: Optional[Dict[str, float]] = None  # For click, scroll
    scroll_delta: Optional[Dict[str, float]] = None  # For scroll

    # Timing
    time_since_last_action_ms: int = 0
    action_duration_ms: int = 0

    # Context
    before_screenshot: Optional[str] = None
    after_screenshot: Optional[str] = None
    dom_change_detected: bool = False
    navigation_occurred: bool = False

    # Metadata
    confidence: float = 1.0
    notes: str = ""


@dataclass
class RecordingSession:
    """A complete recording session"""
    session_id: str
    name: str
    description: str
    start_url: str
    domain: str
    started_at: str
    completed_at: Optional[str]
    actions: List[RecordedAction]
    total_duration_ms: int
    page_visits: List[str]
    detected_framework: Optional[str]
    tags: List[str] = field(default_factory=list)
    status: str = "recording"  # recording, completed, cancelled


class ActionRecorder:
    """
    Records human interactions with web applications.

    Features:
    - Multi-selector generation for each interaction
    - Timing capture for realistic playback
    - Screenshot capture at key moments
    - Automatic pattern detection
    - Session management and export
    """

    def __init__(
        self,
        knowledge_index=None,
        learning_engine=None,
        data_dir: str = "data/agent_knowledge"
    ):
        """
        Initialize action recorder.

        Args:
            knowledge_index: KnowledgeIndex for storing learned selectors
            learning_engine: LearningEngine for processing learnings
            data_dir: Directory for storing recordings
        """
        self.knowledge_index = knowledge_index
        self.learning_engine = learning_engine
        self.data_dir = Path(data_dir)

        # Current session
        self._current_session: Optional[RecordingSession] = None
        self._last_action_time: Optional[datetime] = None

        # Browser integration callbacks
        self._get_element_info_callback: Optional[Callable] = None
        self._screenshot_callback: Optional[Callable] = None
        self._get_url_callback: Optional[Callable] = None
        self._get_title_callback: Optional[Callable] = None

        # Action counter for ID generation
        self._action_counter = 0

    def set_browser_callbacks(
        self,
        get_element_info: Callable[[Any], Dict[str, Any]],
        screenshot: Optional[Callable[[str], None]] = None,
        get_url: Optional[Callable[[], str]] = None,
        get_title: Optional[Callable[[], str]] = None
    ):
        """
        Set callbacks for browser interaction.

        Args:
            get_element_info: Function to get element information from browser
            screenshot: Optional function to capture screenshot
            get_url: Optional function to get current URL
            get_title: Optional function to get page title
        """
        self._get_element_info_callback = get_element_info
        self._screenshot_callback = screenshot
        self._get_url_callback = get_url
        self._get_title_callback = get_title

    # ==================== Session Management ====================

    def start_session(
        self,
        name: str,
        start_url: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Start a new recording session.

        Args:
            name: Name for the recording
            start_url: Starting URL
            description: Optional description
            tags: Optional tags for categorization

        Returns:
            Session ID
        """
        session_id = f"rec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(name.encode()).hexdigest()[:6]}"

        parsed = urlparse(start_url)
        domain = parsed.netloc

        self._current_session = RecordingSession(
            session_id=session_id,
            name=name,
            description=description,
            start_url=start_url,
            domain=domain,
            started_at=datetime.utcnow().isoformat(),
            completed_at=None,
            actions=[],
            total_duration_ms=0,
            page_visits=[start_url],
            detected_framework=None,
            tags=tags or [],
            status="recording"
        )

        self._last_action_time = datetime.utcnow()
        self._action_counter = 0

        logger.info(f"Started recording session: {session_id}")
        return session_id

    def end_session(self) -> Optional[RecordingSession]:
        """
        End the current recording session.

        Returns:
            Completed session or None if no active session
        """
        if not self._current_session:
            return None

        session = self._current_session
        session.completed_at = datetime.utcnow().isoformat()
        session.status = "completed"

        # Calculate total duration
        if session.actions:
            session.total_duration_ms = sum(
                a.time_since_last_action_ms + a.action_duration_ms
                for a in session.actions
            )

        # Save session
        self._save_session(session)

        # Process learnings
        self._process_session_learnings(session)

        self._current_session = None
        self._last_action_time = None

        logger.info(f"Completed recording session: {session.session_id}")
        return session

    def cancel_session(self):
        """Cancel the current recording session without saving"""
        if self._current_session:
            logger.info(f"Cancelled recording session: {self._current_session.session_id}")
            self._current_session = None
            self._last_action_time = None

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._current_session is not None

    def get_current_session(self) -> Optional[RecordingSession]:
        """Get the current recording session"""
        return self._current_session

    # ==================== Action Recording ====================

    def record_action(
        self,
        action_type: ActionType,
        element_data: Optional[Dict[str, Any]] = None,
        value: Optional[str] = None,
        key: Optional[str] = None,
        coordinates: Optional[Dict[str, float]] = None,
        url: Optional[str] = None,
        page_title: Optional[str] = None,
        capture_screenshot: bool = False,
        notes: str = ""
    ) -> Optional[RecordedAction]:
        """
        Record an action.

        Args:
            action_type: Type of action
            element_data: Element information (from browser)
            value: Value for type/select actions
            key: Key for key_press actions
            coordinates: Click coordinates
            url: Current URL
            page_title: Current page title
            capture_screenshot: Whether to capture screenshots
            notes: Optional notes

        Returns:
            Recorded action or None if not recording
        """
        if not self._current_session:
            logger.warning("No active recording session")
            return None

        now = datetime.utcnow()

        # Calculate timing
        time_since_last = 0
        if self._last_action_time:
            time_since_last = int((now - self._last_action_time).total_seconds() * 1000)
        self._last_action_time = now

        # Get URL and title
        current_url = url
        current_title = page_title
        if not current_url and self._get_url_callback:
            try:
                current_url = self._get_url_callback()
            except Exception:
                current_url = self._current_session.start_url

        if not current_title and self._get_title_callback:
            try:
                current_title = self._get_title_callback()
            except Exception:
                current_title = ""

        # Track page visits
        if current_url and current_url not in self._current_session.page_visits:
            self._current_session.page_visits.append(current_url)

        # Generate action ID
        self._action_counter += 1
        action_id = f"{self._current_session.session_id}_{self._action_counter:04d}"

        # Process element data
        element_snapshot = None
        selectors = []

        if element_data:
            element_snapshot = self._create_element_snapshot(element_data)
            selectors = self._generate_selectors_from_element(element_data)

        # Capture screenshots
        before_screenshot = None
        after_screenshot = None

        if capture_screenshot and self._screenshot_callback:
            try:
                before_path = str(self.data_dir / "screenshots" / f"{action_id}_before.png")
                self._screenshot_callback(before_path)
                before_screenshot = before_path
            except Exception as e:
                logger.warning(f"Failed to capture before screenshot: {e}")

        # Create action record
        action = RecordedAction(
            action_id=action_id,
            action_type=action_type,
            timestamp=now.isoformat(),
            url=current_url or "",
            page_title=current_title or "",
            element_snapshot=element_snapshot,
            selectors=selectors,
            value=value,
            key=key,
            coordinates=coordinates,
            time_since_last_action_ms=time_since_last,
            before_screenshot=before_screenshot,
            after_screenshot=after_screenshot,
            notes=notes
        )

        # Add to session
        self._current_session.actions.append(action)

        logger.debug(f"Recorded action: {action_type.value} on {element_snapshot.tag_name if element_snapshot else 'page'}")

        return action

    def record_click(
        self,
        element_data: Dict[str, Any],
        coordinates: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> Optional[RecordedAction]:
        """Record a click action"""
        return self.record_action(
            action_type=ActionType.CLICK,
            element_data=element_data,
            coordinates=coordinates,
            **kwargs
        )

    def record_type(
        self,
        element_data: Dict[str, Any],
        value: str,
        **kwargs
    ) -> Optional[RecordedAction]:
        """Record a type action"""
        return self.record_action(
            action_type=ActionType.TYPE,
            element_data=element_data,
            value=value,
            **kwargs
        )

    def record_select(
        self,
        element_data: Dict[str, Any],
        value: str,
        **kwargs
    ) -> Optional[RecordedAction]:
        """Record a select action"""
        return self.record_action(
            action_type=ActionType.SELECT,
            element_data=element_data,
            value=value,
            **kwargs
        )

    def record_navigation(
        self,
        url: str,
        **kwargs
    ) -> Optional[RecordedAction]:
        """Record a navigation action"""
        return self.record_action(
            action_type=ActionType.NAVIGATE,
            url=url,
            **kwargs
        )

    def record_key_press(
        self,
        key: str,
        element_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[RecordedAction]:
        """Record a key press action"""
        return self.record_action(
            action_type=ActionType.KEY_PRESS,
            element_data=element_data,
            key=key,
            **kwargs
        )

    def record_scroll(
        self,
        delta_x: float,
        delta_y: float,
        element_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[RecordedAction]:
        """Record a scroll action"""
        action = self.record_action(
            action_type=ActionType.SCROLL,
            element_data=element_data,
            **kwargs
        )
        if action:
            action.scroll_delta = {"x": delta_x, "y": delta_y}
        return action

    def record_assertion(
        self,
        assertion_type: str,
        expected_value: str,
        element_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[RecordedAction]:
        """Record an assertion"""
        return self.record_action(
            action_type=ActionType.ASSERT,
            element_data=element_data,
            value=f"{assertion_type}:{expected_value}",
            **kwargs
        )

    # ==================== Element Processing ====================

    def _create_element_snapshot(self, element_data: Dict[str, Any]) -> ElementSnapshot:
        """Create a snapshot of element state"""
        return ElementSnapshot(
            tag_name=element_data.get("tagName", "").lower(),
            element_type=element_data.get("type", ""),
            text_content=element_data.get("textContent", "")[:200],
            attributes=element_data.get("attributes", {}),
            bounding_box=element_data.get("boundingBox"),
            is_visible=element_data.get("isVisible", True),
            is_enabled=not element_data.get("disabled", False),
            computed_styles=element_data.get("computedStyles", {}),
            parent_info=element_data.get("parentInfo", {})
        )

    def _generate_selectors_from_element(
        self,
        element_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate multiple selector strategies for an element"""
        selectors = []
        attrs = element_data.get("attributes", {})
        tag = element_data.get("tagName", "").lower()
        text = element_data.get("textContent", "").strip()

        # 1. data-testid (highest priority)
        test_id = attrs.get("data-testid") or attrs.get("data-test-id") or attrs.get("data-cy")
        if test_id:
            selectors.append({
                "selector": f'[data-testid="{test_id}"]',
                "type": "css",
                "strategy": "test_id",
                "confidence": 0.95,
                "priority": 1
            })

        # 2. ID
        elem_id = attrs.get("id")
        if elem_id and not self._is_dynamic_id(elem_id):
            selectors.append({
                "selector": f'#{elem_id}',
                "type": "css",
                "strategy": "id",
                "confidence": 0.9,
                "priority": 2
            })

        # 3. Role + aria-label
        role = attrs.get("role")
        aria_label = attrs.get("aria-label")
        if role and aria_label:
            selectors.append({
                "selector": f'[role="{role}"][aria-label="{aria_label}"]',
                "type": "css",
                "strategy": "role_aria",
                "confidence": 0.88,
                "priority": 3
            })

        # 4. Name attribute
        name = attrs.get("name")
        if name:
            selectors.append({
                "selector": f'[name="{name}"]',
                "type": "css",
                "strategy": "name",
                "confidence": 0.85,
                "priority": 4
            })

        # 5. Playwright text locator
        if text and len(text) < 80:
            selectors.append({
                "selector": text,
                "type": "text",
                "strategy": "text_content",
                "confidence": 0.8,
                "priority": 5
            })

        # 6. Label text (for form inputs)
        label_text = element_data.get("labelText")
        if label_text:
            selectors.append({
                "selector": label_text,
                "type": "label",
                "strategy": "label",
                "confidence": 0.85,
                "priority": 4
            })

        # 7. Placeholder
        placeholder = attrs.get("placeholder")
        if placeholder:
            selectors.append({
                "selector": f'[placeholder="{placeholder}"]',
                "type": "css",
                "strategy": "placeholder",
                "confidence": 0.75,
                "priority": 6
            })
            selectors.append({
                "selector": placeholder,
                "type": "placeholder",
                "strategy": "playwright_placeholder",
                "confidence": 0.8,
                "priority": 5
            })

        # 8. Type-specific
        input_type = attrs.get("type")
        if tag == "input" and input_type:
            if input_type == "submit":
                selectors.append({
                    "selector": f'input[type="submit"]',
                    "type": "css",
                    "strategy": "input_type",
                    "confidence": 0.6,
                    "priority": 8
                })
            elif input_type in ("email", "password"):
                selectors.append({
                    "selector": f'input[type="{input_type}"]',
                    "type": "css",
                    "strategy": "input_type",
                    "confidence": 0.65,
                    "priority": 7
                })

        # 9. XPath from browser (if available)
        xpath = element_data.get("xpath")
        if xpath:
            selectors.append({
                "selector": xpath,
                "type": "xpath",
                "strategy": "xpath",
                "confidence": 0.5,
                "priority": 10
            })

        # Sort by priority
        selectors.sort(key=lambda x: x.get("priority", 99))

        return selectors

    def _is_dynamic_id(self, elem_id: str) -> bool:
        """Check if an ID looks dynamically generated"""
        import re

        # Common patterns for dynamic IDs
        dynamic_patterns = [
            r'^[a-f0-9]{8,}',  # UUID-like
            r'^:r\d+:',  # React generated
            r'^\d+$',  # Pure numbers
            r'^[a-z]+\d+$',  # Letters followed by numbers
            r'^ng-\d+',  # Angular generated
            r'^ember\d+',  # Ember generated
        ]

        for pattern in dynamic_patterns:
            if re.match(pattern, elem_id, re.I):
                return True

        return False

    # ==================== Session Storage ====================

    def _save_session(self, session: RecordingSession):
        """Save a recording session to disk"""
        output_dir = self.data_dir / "recordings"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{session.session_id}.json"

        # Convert to serializable format
        session_dict = {
            "session_id": session.session_id,
            "name": session.name,
            "description": session.description,
            "start_url": session.start_url,
            "domain": session.domain,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "total_duration_ms": session.total_duration_ms,
            "page_visits": session.page_visits,
            "detected_framework": session.detected_framework,
            "tags": session.tags,
            "status": session.status,
            "action_count": len(session.actions),
            "actions": [
                {
                    "action_id": a.action_id,
                    "action_type": a.action_type.value,
                    "timestamp": a.timestamp,
                    "url": a.url,
                    "page_title": a.page_title,
                    "element": {
                        "tag_name": a.element_snapshot.tag_name,
                        "element_type": a.element_snapshot.element_type,
                        "text_content": a.element_snapshot.text_content,
                        "attributes": a.element_snapshot.attributes,
                        "is_visible": a.element_snapshot.is_visible,
                        "is_enabled": a.element_snapshot.is_enabled
                    } if a.element_snapshot else None,
                    "selectors": a.selectors,
                    "value": a.value,
                    "key": a.key,
                    "coordinates": a.coordinates,
                    "scroll_delta": a.scroll_delta,
                    "time_since_last_action_ms": a.time_since_last_action_ms,
                    "action_duration_ms": a.action_duration_ms,
                    "notes": a.notes
                }
                for a in session.actions
            ]
        }

        with open(output_dir / filename, 'w') as f:
            json.dump(session_dict, f, indent=2)

        logger.info(f"Saved recording session to {filename}")

    def load_session(self, session_id: str) -> Optional[RecordingSession]:
        """Load a recording session from disk"""
        file_path = self.data_dir / "recordings" / f"{session_id}.json"

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            data = json.load(f)

        # Reconstruct session
        actions = []
        for a_data in data.get("actions", []):
            element_snapshot = None
            if a_data.get("element"):
                elem = a_data["element"]
                element_snapshot = ElementSnapshot(
                    tag_name=elem.get("tag_name", ""),
                    element_type=elem.get("element_type", ""),
                    text_content=elem.get("text_content", ""),
                    attributes=elem.get("attributes", {}),
                    bounding_box=elem.get("bounding_box"),
                    is_visible=elem.get("is_visible", True),
                    is_enabled=elem.get("is_enabled", True)
                )

            action = RecordedAction(
                action_id=a_data["action_id"],
                action_type=ActionType(a_data["action_type"]),
                timestamp=a_data["timestamp"],
                url=a_data.get("url", ""),
                page_title=a_data.get("page_title", ""),
                element_snapshot=element_snapshot,
                selectors=a_data.get("selectors", []),
                value=a_data.get("value"),
                key=a_data.get("key"),
                coordinates=a_data.get("coordinates"),
                scroll_delta=a_data.get("scroll_delta"),
                time_since_last_action_ms=a_data.get("time_since_last_action_ms", 0),
                action_duration_ms=a_data.get("action_duration_ms", 0),
                notes=a_data.get("notes", "")
            )
            actions.append(action)

        return RecordingSession(
            session_id=data["session_id"],
            name=data["name"],
            description=data.get("description", ""),
            start_url=data["start_url"],
            domain=data["domain"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            actions=actions,
            total_duration_ms=data.get("total_duration_ms", 0),
            page_visits=data.get("page_visits", []),
            detected_framework=data.get("detected_framework"),
            tags=data.get("tags", []),
            status=data.get("status", "completed")
        )

    def list_sessions(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all recorded sessions"""
        recordings_dir = self.data_dir / "recordings"

        if not recordings_dir.exists():
            return []

        sessions = []
        for file in recordings_dir.glob("rec_*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)

                if domain and data.get("domain") != domain:
                    continue

                sessions.append({
                    "session_id": data["session_id"],
                    "name": data["name"],
                    "domain": data["domain"],
                    "started_at": data["started_at"],
                    "action_count": data.get("action_count", len(data.get("actions", []))),
                    "status": data.get("status", "completed"),
                    "tags": data.get("tags", [])
                })
            except Exception as e:
                logger.warning(f"Failed to load session {file}: {e}")

        return sorted(sessions, key=lambda x: x["started_at"], reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """Delete a recording session"""
        file_path = self.data_dir / "recordings" / f"{session_id}.json"

        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted recording session: {session_id}")
            return True

        return False

    # ==================== Learning Processing ====================

    def _process_session_learnings(self, session: RecordingSession):
        """Process learnings from a completed session"""
        if not self.knowledge_index and not self.learning_engine:
            logger.warning("No knowledge index or learning engine configured")
            return

        domain = session.domain

        for action in session.actions:
            if not action.selectors:
                continue

            # Extract page path
            page = urlparse(action.url).path or "/"

            # Generate element key from snapshot
            element_key = self._generate_element_key(action)

            if not element_key:
                continue

            # Record each selector
            for selector_info in action.selectors:
                if self.learning_engine:
                    self.learning_engine.record_element_mapping(
                        domain=domain,
                        page=page,
                        element_key=element_key,
                        selectors=[selector_info],
                        element_attributes=action.element_snapshot.attributes if action.element_snapshot else {},
                        ai_assisted=False
                    )
                elif self.knowledge_index:
                    self.knowledge_index.add_learning(
                        domain=domain,
                        page=page,
                        element_key=element_key,
                        selector=selector_info["selector"],
                        selector_type=selector_info.get("type", "css"),
                        success=True,
                        ai_assisted=False,
                        context={
                            "source": "recording",
                            "session_id": session.session_id,
                            "strategy": selector_info.get("strategy", "unknown")
                        }
                    )

        # Detect and record patterns
        self._detect_patterns_in_session(session)

        logger.info(f"Processed {len(session.actions)} actions from recording session")

    def _generate_element_key(self, action: RecordedAction) -> Optional[str]:
        """Generate a semantic key for the element"""
        if not action.element_snapshot:
            return None

        snapshot = action.element_snapshot
        attrs = snapshot.attributes

        # Priority order for key generation
        key_sources = [
            attrs.get("aria-label"),
            attrs.get("name"),
            attrs.get("data-testid"),
            attrs.get("placeholder"),
            snapshot.text_content[:50] if snapshot.text_content else None,
            attrs.get("id")
        ]

        for source in key_sources:
            if source:
                # Normalize key
                import re
                key = source.lower()
                key = re.sub(r'[^a-z0-9]+', '_', key)
                key = key.strip('_')
                if key:
                    return key

        # Fallback to tag + type
        return f"{snapshot.tag_name}_{snapshot.element_type or 'element'}"

    def _detect_patterns_in_session(self, session: RecordingSession):
        """Detect action patterns in a recording session"""
        if not self.learning_engine:
            return

        # Look for common patterns
        actions = session.actions

        # Login pattern: email/username input -> password input -> submit
        for i in range(len(actions) - 2):
            if (actions[i].action_type == ActionType.TYPE and
                actions[i+1].action_type == ActionType.TYPE and
                actions[i+2].action_type == ActionType.CLICK):

                elem1 = actions[i].element_snapshot
                elem2 = actions[i+1].element_snapshot

                if elem1 and elem2:
                    attrs1 = elem1.attributes
                    attrs2 = elem2.attributes

                    is_email = attrs1.get("type") in ("email", "text") or "email" in attrs1.get("name", "").lower()
                    is_password = attrs2.get("type") == "password"

                    if is_email and is_password:
                        # Record login pattern
                        self.learning_engine.record_action(
                            domain=session.domain,
                            page=urlparse(actions[i].url).path or "/",
                            action_type="login_flow",
                            element_key="login_pattern",
                            value=json.dumps({
                                "email_selector": actions[i].selectors[0] if actions[i].selectors else None,
                                "password_selector": actions[i+1].selectors[0] if actions[i+1].selectors else None,
                                "submit_selector": actions[i+2].selectors[0] if actions[i+2].selectors else None
                            }),
                            success=True
                        )

    # ==================== Playback Generation ====================

    def generate_playwright_script(
        self,
        session: RecordingSession,
        include_comments: bool = True
    ) -> str:
        """
        Generate a Playwright test script from a recording.

        Args:
            session: Recording session
            include_comments: Whether to include comments

        Returns:
            Playwright test script as string
        """
        lines = []

        # Header
        lines.append("import { test, expect } from '@playwright/test';")
        lines.append("")
        lines.append(f"test('{session.name}', async ({{ page }}) => {{")

        # Navigate to start URL
        lines.append(f"  await page.goto('{session.start_url}');")
        lines.append("")

        # Actions
        for action in session.actions:
            if include_comments and action.notes:
                lines.append(f"  // {action.notes}")

            playwright_code = self._action_to_playwright(action)
            if playwright_code:
                # Add wait if significant time between actions
                if action.time_since_last_action_ms > 1000:
                    lines.append(f"  await page.waitForTimeout({min(action.time_since_last_action_ms, 5000)});")

                lines.append(f"  {playwright_code}")
                lines.append("")

        lines.append("});")

        return "\n".join(lines)

    def _action_to_playwright(self, action: RecordedAction) -> Optional[str]:
        """Convert a recorded action to Playwright code"""
        if not action.selectors:
            return None

        # Get best selector
        selector_info = action.selectors[0]
        selector = selector_info["selector"]
        selector_type = selector_info.get("type", "css")

        # Build locator
        if selector_type == "text":
            locator = f"page.getByText('{selector}')"
        elif selector_type == "label":
            locator = f"page.getByLabel('{selector}')"
        elif selector_type == "placeholder":
            locator = f"page.getByPlaceholder('{selector}')"
        elif selector_type == "xpath":
            locator = f"page.locator('xpath={selector}')"
        else:
            locator = f"page.locator('{selector}')"

        # Build action
        if action.action_type == ActionType.CLICK:
            return f"await {locator}.click();"
        elif action.action_type == ActionType.DOUBLE_CLICK:
            return f"await {locator}.dblclick();"
        elif action.action_type == ActionType.TYPE:
            value = action.value or ""
            return f"await {locator}.fill('{value}');"
        elif action.action_type == ActionType.CLEAR:
            return f"await {locator}.clear();"
        elif action.action_type == ActionType.SELECT:
            value = action.value or ""
            return f"await {locator}.selectOption('{value}');"
        elif action.action_type == ActionType.CHECK:
            return f"await {locator}.check();"
        elif action.action_type == ActionType.UNCHECK:
            return f"await {locator}.uncheck();"
        elif action.action_type == ActionType.HOVER:
            return f"await {locator}.hover();"
        elif action.action_type == ActionType.KEY_PRESS:
            key = action.key or "Enter"
            return f"await page.keyboard.press('{key}');"
        elif action.action_type == ActionType.NAVIGATE:
            return f"await page.goto('{action.url}');"
        elif action.action_type == ActionType.BACK:
            return "await page.goBack();"
        elif action.action_type == ActionType.FORWARD:
            return "await page.goForward();"
        elif action.action_type == ActionType.REFRESH:
            return "await page.reload();"

        return None

    def generate_test_steps(
        self,
        session: RecordingSession
    ) -> List[Dict[str, Any]]:
        """
        Generate test steps from a recording (for test case format).

        Returns list of step dictionaries compatible with test execution.
        """
        steps = []

        for action in session.actions:
            step = {
                "action": action.action_type.value,
                "target": action.selectors[0]["selector"] if action.selectors else None,
                "target_type": action.selectors[0].get("type", "css") if action.selectors else None,
                "value": action.value,
                "alternative_selectors": action.selectors[1:] if len(action.selectors) > 1 else []
            }

            if action.element_snapshot:
                step["element_info"] = {
                    "tag": action.element_snapshot.tag_name,
                    "text": action.element_snapshot.text_content
                }

            steps.append(step)

        return steps
