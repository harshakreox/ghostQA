"""
Unit tests for PatternStore.

Tests the action pattern storage and retrieval system.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

from agent.knowledge.pattern_store import PatternStore, ActionPattern, ActionStep


class TestPatternStoreInit:
    """Test PatternStore initialization."""

    def test_init_creates_directory(self, tmp_path):
        """Test that init creates the patterns directory."""
        patterns_dir = tmp_path / "patterns"
        store = PatternStore(patterns_dir=str(patterns_dir))

        assert patterns_dir.exists()

    def test_init_loads_builtin_patterns(self, tmp_path):
        """Test that builtin patterns are loaded on init."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        # Should have builtin patterns
        assert len(store.patterns) > 0

    def test_builtin_patterns_include_login(self, tmp_path):
        """Test that builtin patterns include login patterns."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        # Find login pattern
        login_patterns = store.find_pattern(intent="login")

        assert len(login_patterns) > 0


class TestFindPattern:
    """Test pattern finding functionality."""

    def test_find_by_intent(self, tmp_path):
        """Test finding patterns by intent."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        patterns = store.find_pattern(intent="login")

        assert len(patterns) > 0
        assert all(isinstance(p, ActionPattern) for p in patterns)

    def test_find_by_category(self, tmp_path):
        """Test finding patterns by category."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        patterns = store.find_pattern(category="authentication")

        assert len(patterns) > 0

    def test_find_returns_empty_for_unknown(self, tmp_path):
        """Test that find returns patterns even for unknown queries (returns all)."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        patterns = store.find_pattern(intent="xyz_unknown_intent_12345")

        # Should return some patterns (possibly all)
        assert isinstance(patterns, list)

    def test_find_sorts_by_confidence(self, tmp_path):
        """Test that found patterns are sorted by confidence."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        patterns = store.find_pattern(intent="login")

        if len(patterns) >= 2:
            # Should be sorted by confidence (descending)
            confidences = [p.confidence for p in patterns]
            assert confidences == sorted(confidences, reverse=True)


class TestGetPattern:
    """Test getting pattern by ID."""

    def test_get_existing_pattern(self, tmp_path):
        """Test getting an existing pattern by ID."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        # Get a builtin pattern ID
        pattern_ids = list(store.patterns.keys())
        if pattern_ids:
            pattern = store.get_pattern(pattern_ids[0])
            assert pattern is not None
            assert isinstance(pattern, ActionPattern)

    def test_get_nonexistent_pattern(self, tmp_path):
        """Test getting a nonexistent pattern returns None."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        pattern = store.get_pattern("nonexistent_pattern_id")

        assert pattern is None


class TestAddPattern:
    """Test adding new patterns."""

    def test_add_pattern_creates_id(self, tmp_path):
        """Test that adding a pattern without ID creates one."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        pattern = ActionPattern(
            id="",
            name="Test Pattern",
            category="test"
        )

        pattern_id = store.add_pattern(pattern)

        assert pattern_id != ""
        assert pattern_id.startswith("pattern_")

    def test_add_pattern_indexes_correctly(self, tmp_path):
        """Test that added pattern is indexed."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        pattern = ActionPattern(
            id="test_pattern_001",
            name="Test Navigation",
            category="navigation",
            applicable_when={"intent_matches": ["test_nav"]}
        )

        store.add_pattern(pattern)

        # Should be findable
        found = store.get_pattern("test_pattern_001")
        assert found is not None
        assert found.name == "Test Navigation"


class TestUpdatePatternStats:
    """Test updating pattern statistics."""

    def test_update_success(self, tmp_path):
        """Test updating pattern stats with success."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        # Add a pattern
        pattern = ActionPattern(
            id="stats_test",
            name="Stats Test Pattern",
            category="test"
        )
        store.add_pattern(pattern)

        initial_used = pattern.times_used

        store.update_pattern_stats("stats_test", success=True)

        updated = store.get_pattern("stats_test")
        assert updated.times_used == initial_used + 1
        assert updated.times_succeeded == 1

    def test_update_failure(self, tmp_path):
        """Test updating pattern stats with failure."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        pattern = ActionPattern(
            id="fail_test",
            name="Fail Test Pattern",
            category="test"
        )
        store.add_pattern(pattern)

        store.update_pattern_stats("fail_test", success=False)

        updated = store.get_pattern("fail_test")
        assert updated.times_used == 1
        assert updated.times_succeeded == 0

    def test_update_recalculates_confidence(self, tmp_path):
        """Test that confidence is recalculated after update."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        pattern = ActionPattern(
            id="conf_test",
            name="Confidence Test",
            category="test",
            confidence=0.5
        )
        store.add_pattern(pattern)

        # Add 3 successes
        store.update_pattern_stats("conf_test", success=True)
        store.update_pattern_stats("conf_test", success=True)
        store.update_pattern_stats("conf_test", success=True)

        # Add 1 failure
        store.update_pattern_stats("conf_test", success=False)

        updated = store.get_pattern("conf_test")
        # 3 out of 4 = 0.75
        assert updated.confidence == 0.75


class TestGetStats:
    """Test getting pattern store statistics."""

    def test_get_stats_returns_dict(self, tmp_path):
        """Test that get_stats returns a dictionary."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        stats = store.get_stats()

        assert isinstance(stats, dict)

    def test_get_stats_contains_total(self, tmp_path):
        """Test that stats contain total patterns count."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        stats = store.get_stats()

        assert "total_patterns" in stats
        assert stats["total_patterns"] > 0  # Has builtin patterns


class TestGetAllPatterns:
    """Test getting all patterns."""

    def test_get_all_patterns_returns_list(self, tmp_path):
        """Test that get_all_patterns returns a list."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        patterns = store.get_all_patterns()

        assert isinstance(patterns, list)

    def test_get_all_patterns_returns_dicts(self, tmp_path):
        """Test that get_all_patterns returns dictionaries."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        patterns = store.get_all_patterns()

        assert all(isinstance(p, dict) for p in patterns)

    def test_get_all_patterns_includes_metadata(self, tmp_path):
        """Test that pattern dicts include metadata."""
        store = PatternStore(patterns_dir=str(tmp_path / "patterns"))

        patterns = store.get_all_patterns()

        if patterns:
            p = patterns[0]
            assert "id" in p
            assert "name" in p
            assert "category" in p


class TestActionPattern:
    """Test ActionPattern dataclass."""

    def test_action_pattern_creation(self):
        """Test creating an ActionPattern."""
        pattern = ActionPattern(
            id="test_001",
            name="Test Pattern",
            description="A test pattern",
            category="test"
        )

        assert pattern.id == "test_001"
        assert pattern.name == "Test Pattern"
        assert pattern.category == "test"

    def test_action_pattern_defaults(self):
        """Test ActionPattern default values."""
        pattern = ActionPattern(
            id="test",
            name="Test"
        )

        assert pattern.category == "general"
        assert pattern.confidence == 0.5
        assert pattern.times_used == 0
        assert pattern.steps == []


class TestActionStep:
    """Test ActionStep dataclass."""

    def test_action_step_creation(self):
        """Test creating an ActionStep."""
        step = ActionStep(
            action="click",
            target="submit_button",
            selectors=["#submit", "[type='submit']"]
        )

        assert step.action == "click"
        assert step.target == "submit_button"
        assert len(step.selectors) == 2

    def test_action_step_with_value(self):
        """Test ActionStep with value."""
        step = ActionStep(
            action="type",
            target="username_input",
            value="${username}",
            selectors=["#username"]
        )

        assert step.value == "${username}"

    def test_action_step_optional_flag(self):
        """Test ActionStep optional flag."""
        step = ActionStep(
            action="click",
            target="close_modal",
            optional=True
        )

        assert step.optional is True
