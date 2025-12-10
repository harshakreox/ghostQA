"""
Pattern Store - Stores and retrieves successful action patterns

Patterns are sequences of actions that achieve a specific goal,
like "login flow" or "fill form and submit".
"""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ActionStep:
    """A single action in a pattern"""
    action: str  # click, type, wait, scroll, etc.
    target: Optional[str] = None  # element key or selector
    value: Optional[str] = None  # text to type, etc.
    selectors: List[str] = field(default_factory=list)  # fallback selectors
    wait_after: int = 0  # ms to wait after action
    optional: bool = False  # if true, failure doesn't break pattern
    notes: Optional[str] = None


@dataclass
class ActionPattern:
    """A reusable pattern of actions"""
    id: str
    name: str
    description: Optional[str] = None
    category: str = "general"  # login, form, navigation, etc.

    # When to use this pattern
    applicable_when: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"page_has": ["input[type='email']"], "intent_matches": ["login"]}

    # The action sequence
    steps: List[ActionStep] = field(default_factory=list)

    # Variables that can be substituted
    variables: List[str] = field(default_factory=list)
    # e.g., ["username", "password"]

    # Success/failure indicators
    success_indicators: List[str] = field(default_factory=list)
    failure_indicators: List[str] = field(default_factory=list)

    # Statistics
    times_used: int = 0
    times_succeeded: int = 0
    confidence: float = 0.5
    last_used: Optional[str] = None
    created_at: Optional[str] = None
    learned_from: str = "manual"  # manual, recording, ai


class PatternStore:
    """
    Stores and retrieves action patterns

    Patterns are grouped by category and can be matched by:
    - Exact intent match
    - Page element presence
    - Fuzzy intent matching
    """

    def __init__(self, patterns_dir: str = "data/agent_knowledge/patterns"):
        self.patterns_dir = Path(patterns_dir)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)

        # In-memory pattern storage
        self.patterns: Dict[str, ActionPattern] = {}
        self.by_category: Dict[str, List[str]] = {}
        self.by_intent: Dict[str, List[str]] = {}  # intent keywords → pattern IDs

        self._lock = threading.Lock()

        # Load existing patterns
        self._load_all_patterns()

        # Load built-in patterns
        self._load_builtin_patterns()

    def _load_all_patterns(self):
        """Load all patterns from disk"""
        for pattern_file in self.patterns_dir.glob("*.json"):
            try:
                data = json.loads(pattern_file.read_text(encoding='utf-8'))

                if "patterns" in data:
                    # File contains multiple patterns
                    for pattern_data in data["patterns"]:
                        self._add_pattern_from_dict(pattern_data)
                else:
                    # Single pattern file
                    self._add_pattern_from_dict(data)

            except Exception as e:
                print(f"[WARN] Error loading pattern file {pattern_file}: {e}")

    def _add_pattern_from_dict(self, data: dict):
        """Add a pattern from dictionary data"""
        steps = [
            ActionStep(**step) if isinstance(step, dict) else step
            for step in data.get("steps", [])
        ]

        pattern = ActionPattern(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            category=data.get("category", "general"),
            applicable_when=data.get("applicable_when", {}),
            steps=steps,
            variables=data.get("variables", []),
            success_indicators=data.get("success_indicators", []),
            failure_indicators=data.get("failure_indicators", []),
            times_used=data.get("times_used", 0),
            times_succeeded=data.get("times_succeeded", 0),
            confidence=data.get("confidence", 0.5),
            last_used=data.get("last_used"),
            created_at=data.get("created_at"),
            learned_from=data.get("learned_from", "unknown")
        )

        self._index_pattern(pattern)

    def _index_pattern(self, pattern: ActionPattern):
        """Add pattern to indexes"""
        with self._lock:
            self.patterns[pattern.id] = pattern

            # Index by category
            if pattern.category not in self.by_category:
                self.by_category[pattern.category] = []
            if pattern.id not in self.by_category[pattern.category]:
                self.by_category[pattern.category].append(pattern.id)

            # Index by intent keywords
            intent_matches = pattern.applicable_when.get("intent_matches", [])
            for intent in intent_matches:
                intent_lower = intent.lower()
                if intent_lower not in self.by_intent:
                    self.by_intent[intent_lower] = []
                if pattern.id not in self.by_intent[intent_lower]:
                    self.by_intent[intent_lower].append(pattern.id)

    def _load_builtin_patterns(self):
        """Load built-in common patterns"""
        builtin = [
            ActionPattern(
                id="builtin_login_email_password",
                name="Standard Email/Password Login",
                description="Login using email and password fields",
                category="authentication",
                applicable_when={
                    "page_has": ["input[type='email']", "input[type='password']"],
                    "intent_matches": ["login", "sign in", "log in", "authenticate"]
                },
                steps=[
                    ActionStep(
                        action="find_and_type",
                        target="email_input",
                        value="${username}",
                        selectors=[
                            "input[type='email']",
                            "input[name*='email']",
                            "input[placeholder*='email']",
                            "input[autocomplete='email']"
                        ]
                    ),
                    ActionStep(
                        action="find_and_type",
                        target="password_input",
                        value="${password}",
                        selectors=[
                            "input[type='password']",
                            "input[name*='password']"
                        ]
                    ),
                    ActionStep(
                        action="find_and_click",
                        target="submit_button",
                        selectors=[
                            "button[type='submit']",
                            "button:has-text('Log in')",
                            "button:has-text('Login')",
                            "button:has-text('Sign in')",
                            "input[type='submit']"
                        ]
                    ),
                    ActionStep(
                        action="wait",
                        value="navigation_or_error",
                        wait_after=5000
                    )
                ],
                variables=["username", "password"],
                success_indicators=[
                    "url_changed",
                    "dashboard_visible",
                    "logout_button_visible"
                ],
                failure_indicators=[
                    "error_message_visible",
                    "still_on_login_page"
                ],
                confidence=0.9,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_login_username_password",
                name="Standard Username/Password Login",
                description="Login using username and password fields",
                category="authentication",
                applicable_when={
                    "page_has": ["input[name*='user']", "input[type='password']"],
                    "page_lacks": ["input[type='email']"],
                    "intent_matches": ["login", "sign in", "log in"]
                },
                steps=[
                    ActionStep(
                        action="find_and_type",
                        target="username_input",
                        value="${username}",
                        selectors=[
                            "input[name*='username']",
                            "input[name*='user']",
                            "input[placeholder*='username']",
                            "input[autocomplete='username']",
                            "input[type='text']:first-of-type"
                        ]
                    ),
                    ActionStep(
                        action="find_and_type",
                        target="password_input",
                        value="${password}",
                        selectors=[
                            "input[type='password']",
                            "input[name*='password']"
                        ]
                    ),
                    ActionStep(
                        action="find_and_click",
                        target="submit_button",
                        selectors=[
                            "button[type='submit']",
                            "button:has-text('Log in')",
                            "button:has-text('Login')",
                            "input[type='submit']"
                        ]
                    ),
                    ActionStep(
                        action="wait",
                        value="navigation_or_error",
                        wait_after=5000
                    )
                ],
                variables=["username", "password"],
                success_indicators=["url_changed", "logout_button_visible"],
                failure_indicators=["error_message_visible"],
                confidence=0.85,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_form_submit",
                name="Generic Form Submit",
                description="Fill form fields and submit",
                category="forms",
                applicable_when={
                    "page_has": ["form", "button[type='submit']"],
                    "intent_matches": ["submit", "fill form", "complete form"]
                },
                steps=[
                    ActionStep(
                        action="fill_form_fields",
                        target="form",
                        value="${form_data}",
                        notes="Fill all matching form fields from form_data"
                    ),
                    ActionStep(
                        action="find_and_click",
                        target="submit_button",
                        selectors=[
                            "button[type='submit']",
                            "button:has-text('Submit')",
                            "button:has-text('Save')",
                            "input[type='submit']"
                        ]
                    ),
                    ActionStep(
                        action="wait",
                        value="response",
                        wait_after=3000
                    )
                ],
                variables=["form_data"],
                success_indicators=["success_message", "redirect"],
                failure_indicators=["validation_error", "error_message"],
                confidence=0.8,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_search",
                name="Search Action",
                description="Enter search query and submit",
                category="search",
                applicable_when={
                    "page_has": ["input[type='search']", "input[placeholder*='search']"],
                    "intent_matches": ["search", "find", "look for"]
                },
                steps=[
                    ActionStep(
                        action="find_and_type",
                        target="search_input",
                        value="${query}",
                        selectors=[
                            "input[type='search']",
                            "input[name*='search']",
                            "input[placeholder*='search']",
                            "input[role='searchbox']",
                            "[aria-label*='search'] input"
                        ]
                    ),
                    ActionStep(
                        action="press_key",
                        value="Enter",
                        wait_after=2000
                    )
                ],
                variables=["query"],
                success_indicators=["results_visible", "url_contains_query"],
                failure_indicators=["no_results_message"],
                confidence=0.85,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_dismiss_modal",
                name="Dismiss Modal/Popup",
                description="Close any modal, dialog, or popup",
                category="recovery",
                applicable_when={
                    "page_has": ["[role='dialog']", ".modal", ".popup"],
                    "intent_matches": ["dismiss", "close", "cancel"]
                },
                steps=[
                    ActionStep(
                        action="find_and_click",
                        target="close_button",
                        selectors=[
                            "button[aria-label='Close']",
                            "button[aria-label='close']",
                            ".modal-close",
                            ".close-button",
                            "[role='dialog'] button:has-text('Close')",
                            "[role='dialog'] button:has-text('×')",
                            ".modal button:has-text('Cancel')"
                        ],
                        optional=True
                    ),
                    ActionStep(
                        action="press_key",
                        value="Escape",
                        optional=True,
                        notes="Fallback if no close button found"
                    )
                ],
                success_indicators=["modal_gone", "dialog_closed"],
                confidence=0.9,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_dismiss_cookie_banner",
                name="Dismiss Cookie Banner",
                description="Accept or dismiss cookie consent banner",
                category="recovery",
                applicable_when={
                    "page_has": [".cookie", "[class*='cookie']", "[class*='consent']"],
                    "intent_matches": ["dismiss cookie", "accept cookies"]
                },
                steps=[
                    ActionStep(
                        action="find_and_click",
                        target="accept_button",
                        selectors=[
                            "button:has-text('Accept')",
                            "button:has-text('Accept all')",
                            "button:has-text('I agree')",
                            "button:has-text('OK')",
                            "button:has-text('Got it')",
                            ".cookie-accept",
                            "[class*='cookie'] button:first-of-type"
                        ]
                    )
                ],
                success_indicators=["cookie_banner_gone"],
                confidence=0.85,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_navigate_to_page",
                name="Navigate to Page",
                description="Click a link or button to navigate",
                category="navigation",
                applicable_when={
                    "intent_matches": ["go to", "navigate to", "open", "click on"]
                },
                steps=[
                    ActionStep(
                        action="find_and_click",
                        target="${target}",
                        selectors=[
                            "a:has-text('${target}')",
                            "button:has-text('${target}')",
                            "[role='link']:has-text('${target}')",
                            "[role='button']:has-text('${target}')"
                        ]
                    ),
                    ActionStep(
                        action="wait",
                        value="navigation",
                        wait_after=3000
                    )
                ],
                variables=["target"],
                success_indicators=["url_changed", "page_loaded"],
                confidence=0.8,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_select_dropdown",
                name="Select from Dropdown",
                description="Open dropdown and select an option",
                category="forms",
                applicable_when={
                    "intent_matches": ["select", "choose", "pick"]
                },
                steps=[
                    ActionStep(
                        action="find_and_click",
                        target="dropdown_trigger",
                        selectors=[
                            "select",
                            "[role='combobox']",
                            ".select-trigger",
                            "[aria-haspopup='listbox']"
                        ]
                    ),
                    ActionStep(
                        action="wait",
                        value="dropdown_open",
                        wait_after=500
                    ),
                    ActionStep(
                        action="find_and_click",
                        target="option",
                        selectors=[
                            "option:has-text('${option}')",
                            "[role='option']:has-text('${option}')",
                            ".dropdown-item:has-text('${option}')"
                        ]
                    )
                ],
                variables=["option"],
                success_indicators=["option_selected", "dropdown_closed"],
                confidence=0.8,
                learned_from="builtin"
            ),

            ActionPattern(
                id="builtin_pagination_next",
                name="Go to Next Page",
                description="Click next/pagination button",
                category="navigation",
                applicable_when={
                    "page_has": [".pagination", "[aria-label*='pagination']"],
                    "intent_matches": ["next page", "next", "paginate"]
                },
                steps=[
                    ActionStep(
                        action="find_and_click",
                        target="next_button",
                        selectors=[
                            "button:has-text('Next')",
                            "a:has-text('Next')",
                            "[aria-label='Next']",
                            "[aria-label='next']",
                            ".pagination-next",
                            ".next-page"
                        ]
                    ),
                    ActionStep(
                        action="wait",
                        value="content_updated",
                        wait_after=2000
                    )
                ],
                success_indicators=["page_changed", "new_content_visible"],
                confidence=0.85,
                learned_from="builtin"
            )
        ]

        for pattern in builtin:
            pattern.created_at = datetime.now().isoformat()
            self._index_pattern(pattern)

    def find_pattern(
        self,
        intent: Optional[str] = None,
        category: Optional[str] = None,
        page_elements: Optional[List[str]] = None
    ) -> List[ActionPattern]:
        """
        Find patterns matching criteria

        Args:
            intent: Intent string to match
            category: Category to filter by
            page_elements: Elements present on page

        Returns:
            List of matching patterns, sorted by confidence
        """
        candidates = []

        # Find by intent
        if intent:
            intent_lower = intent.lower()

            # Check each word in intent
            for word in intent_lower.split():
                if word in self.by_intent:
                    candidates.extend(self.by_intent[word])

        # Find by category
        if category and category in self.by_category:
            candidates.extend(self.by_category[category])

        # If no candidates yet, check all patterns
        if not candidates:
            candidates = list(self.patterns.keys())

        # Deduplicate
        candidates = list(set(candidates))

        # Score and filter patterns
        scored = []
        for pattern_id in candidates:
            pattern = self.patterns.get(pattern_id)
            if not pattern:
                continue

            score = pattern.confidence

            # Boost if page elements match
            if page_elements:
                required = pattern.applicable_when.get("page_has", [])
                matches = sum(1 for r in required if any(r in e for e in page_elements))
                if required:
                    score *= (1 + matches / len(required))

            # Boost if intent matches well
            if intent:
                intent_keywords = pattern.applicable_when.get("intent_matches", [])
                for keyword in intent_keywords:
                    if keyword.lower() in intent.lower():
                        score *= 1.2
                        break

            scored.append((pattern, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        return [p for p, _ in scored]

    def get_pattern(self, pattern_id: str) -> Optional[ActionPattern]:
        """Get a pattern by ID"""
        return self.patterns.get(pattern_id)

    def add_pattern(self, pattern: ActionPattern) -> str:
        """Add a new pattern"""
        if not pattern.id:
            pattern.id = f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if not pattern.created_at:
            pattern.created_at = datetime.now().isoformat()

        self._index_pattern(pattern)
        self._save_pattern(pattern)

        return pattern.id

    def update_pattern_stats(
        self,
        pattern_id: str,
        success: bool
    ):
        """Update pattern statistics after use"""
        pattern = self.patterns.get(pattern_id)
        if not pattern:
            return

        pattern.times_used += 1
        if success:
            pattern.times_succeeded += 1

        pattern.confidence = pattern.times_succeeded / pattern.times_used
        pattern.last_used = datetime.now().isoformat()

        self._save_pattern(pattern)

    def _save_pattern(self, pattern: ActionPattern):
        """Save pattern to disk"""
        # Convert to dict
        data = {
            "id": pattern.id,
            "name": pattern.name,
            "description": pattern.description,
            "category": pattern.category,
            "applicable_when": pattern.applicable_when,
            "steps": [
                {
                    "action": s.action,
                    "target": s.target,
                    "value": s.value,
                    "selectors": s.selectors,
                    "wait_after": s.wait_after,
                    "optional": s.optional,
                    "notes": s.notes
                }
                for s in pattern.steps
            ],
            "variables": pattern.variables,
            "success_indicators": pattern.success_indicators,
            "failure_indicators": pattern.failure_indicators,
            "times_used": pattern.times_used,
            "times_succeeded": pattern.times_succeeded,
            "confidence": pattern.confidence,
            "last_used": pattern.last_used,
            "created_at": pattern.created_at,
            "learned_from": pattern.learned_from
        }

        # Save to category file
        category_file = self.patterns_dir / f"{pattern.category}_patterns.json"

        # Load existing
        existing = {"patterns": []}
        if category_file.exists():
            try:
                existing = json.loads(category_file.read_text(encoding='utf-8'))
            except:
                pass

        # Update or add
        found = False
        for i, p in enumerate(existing.get("patterns", [])):
            if p.get("id") == pattern.id:
                existing["patterns"][i] = data
                found = True
                break

        if not found:
            existing.setdefault("patterns", []).append(data)

        # Save
        category_file.write_text(
            json.dumps(existing, indent=2),
            encoding='utf-8'
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get pattern store statistics"""
        return {
            "total_patterns": len(self.patterns),
            "categories": list(self.by_category.keys()),
            "patterns_by_category": {
                cat: len(patterns)
                for cat, patterns in self.by_category.items()
            },
            "most_used": sorted(
                [(p.id, p.times_used) for p in self.patterns.values()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def get_all_patterns(self) -> List[Dict[str, Any]]:
        """Get all patterns as a list of dictionaries"""
        result = []
        for pattern in self.patterns.values():
            result.append({
                "id": pattern.id,
                "name": pattern.name,
                "description": pattern.description,
                "category": pattern.category,
                "applicable_when": pattern.applicable_when,
                "steps": [
                    {
                        "action": s.action,
                        "target": s.target,
                        "value": s.value,
                        "selectors": s.selectors,
                        "wait_after": s.wait_after,
                        "optional": s.optional,
                        "notes": s.notes
                    }
                    for s in pattern.steps
                ],
                "variables": pattern.variables,
                "success_indicators": pattern.success_indicators,
                "failure_indicators": pattern.failure_indicators,
                "times_used": pattern.times_used,
                "times_succeeded": pattern.times_succeeded,
                "confidence": pattern.confidence,
                "last_used": pattern.last_used,
                "created_at": pattern.created_at,
                "learned_from": pattern.learned_from,
                "metadata": {
                    "learned_from": pattern.learned_from
                }
            })
        return result
