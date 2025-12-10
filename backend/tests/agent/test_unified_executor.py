"""
Unit tests for UnifiedTestExecutor.

Tests the unified test execution system that handles both Traditional and Gherkin tests.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

from agent.unified_executor import (
    UnifiedTestExecutor,
    UnifiedTestCase,
    UnifiedTestResult,
    UnifiedExecutionReport,
    TestFormat,
    ExecutionMode
)


class TestUnifiedTestExecutorInit:
    """Test UnifiedTestExecutor initialization."""

    def test_init_with_default_dir(self, tmp_path):
        """Test initialization with default directory."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        assert executor is not None

    def test_init_creates_dependencies(self, tmp_path):
        """Test that initialization creates required dependencies."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        assert executor.knowledge_index is not None
        assert executor.learning_engine is not None
        assert executor.pattern_store is not None

    def test_init_with_config(self, tmp_path):
        """Test initialization with custom config."""
        from agent.core.agent import AgentConfig

        config = AgentConfig(max_retries=5)
        executor = UnifiedTestExecutor(
            data_dir=str(tmp_path / "data"),
            config=config
        )

        assert executor is not None


class TestConvertTraditionalTest:
    """Test converting traditional test cases."""

    def test_convert_simple_test(self, tmp_path):
        """Test converting a simple traditional test."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        traditional_test = {
            "id": "test_001",
            "name": "Login Test",
            "actions": [
                {"action": "type", "selector": "#username", "value": "user"},
                {"action": "type", "selector": "#password", "value": "pass"},
                {"action": "click", "selector": "#login"}
            ]
        }

        unified = executor.convert_traditional_test(traditional_test)

        assert isinstance(unified, UnifiedTestCase)
        assert unified.id == "test_001"
        assert unified.name == "Login Test"
        assert unified.format == TestFormat.TRADITIONAL
        assert len(unified.steps) == 3

    def test_convert_preserves_selectors(self, tmp_path):
        """Test that conversion preserves selectors."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        traditional_test = {
            "id": "test_sel",
            "name": "Selector Test",
            "actions": [
                {"action": "click", "selector": "#my-button"}
            ]
        }

        unified = executor.convert_traditional_test(traditional_test)

        assert unified.steps[0]["target"] == "#my-button"

    def test_convert_handles_action_types(self, tmp_path):
        """Test conversion handles various action types."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        traditional_test = {
            "id": "test_actions",
            "name": "Action Types Test",
            "actions": [
                {"action": "navigate", "url": "https://example.com"},
                {"action": "type", "selector": "#input", "value": "text"},
                {"action": "click", "selector": "#btn"},
                {"action": "select", "selector": "#dropdown", "value": "option1"},
                {"action": "wait", "value": "1000"}
            ]
        }

        unified = executor.convert_traditional_test(traditional_test)

        assert len(unified.steps) == 5


class TestConvertGherkinFeature:
    """Test converting Gherkin features."""

    def test_convert_simple_feature(self, tmp_path):
        """Test converting a simple Gherkin feature."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        feature = {
            "id": "feature_001",
            "name": "Login Feature",
            "scenarios": [
                {
                    "name": "Successful Login",
                    "steps": [
                        {"keyword": "Given", "text": "I am on the login page"},
                        {"keyword": "When", "text": "I enter valid credentials"},
                        {"keyword": "Then", "text": "I should see the dashboard"}
                    ]
                }
            ]
        }

        unified_cases = executor.convert_gherkin_feature(feature)

        assert len(unified_cases) == 1
        assert unified_cases[0].format == TestFormat.GHERKIN
        assert unified_cases[0].scenario_name == "Successful Login"

    def test_convert_feature_with_background(self, tmp_path):
        """Test converting feature with background."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        feature = {
            "id": "feature_bg",
            "name": "Feature with Background",
            "background": {
                "steps": [
                    {"keyword": "Given", "text": "I am logged in"}
                ]
            },
            "scenarios": [
                {
                    "name": "Test Scenario",
                    "steps": [
                        {"keyword": "When", "text": "I do something"},
                        {"keyword": "Then", "text": "I see results"}
                    ]
                }
            ]
        }

        unified_cases = executor.convert_gherkin_feature(feature)

        assert len(unified_cases[0].background_steps) == 1


class TestInterpretGherkinStep:
    """Test Gherkin step interpretation."""

    def test_interpret_given_step(self, tmp_path):
        """Test interpreting 'Given' step."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        step = {
            "action": "gherkin_step",
            "keyword": "Given",
            "text": "I am on the login page"
        }

        interpreted = executor._interpret_gherkin_step(step)

        # Should return a dict with action
        assert isinstance(interpreted, dict)
        assert "action" in interpreted

    def test_interpret_when_click(self, tmp_path):
        """Test interpreting 'When I click' step."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        step = {
            "action": "gherkin_step",
            "keyword": "When",
            "text": "I click the submit button"
        }

        interpreted = executor._interpret_gherkin_step(step)

        assert interpreted["action"] == "click"

    def test_interpret_when_enter(self, tmp_path):
        """Test interpreting 'When I enter' step."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        step = {
            "action": "gherkin_step",
            "keyword": "When",
            "text": "I enter 'testuser' in the username field"
        }

        interpreted = executor._interpret_gherkin_step(step)

        assert interpreted["action"] == "fill"

    def test_interpret_then_see(self, tmp_path):
        """Test interpreting 'Then I should see' step."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        step = {
            "action": "gherkin_step",
            "keyword": "Then",
            "text": "I should see the dashboard"
        }

        interpreted = executor._interpret_gherkin_step(step)

        # Should be some kind of assertion
        assert "action" in interpreted


class TestExecutionModes:
    """Test different execution modes."""

    def test_autonomous_mode_exists(self):
        """Test that AUTONOMOUS mode exists."""
        assert ExecutionMode.AUTONOMOUS

    def test_guided_mode_exists(self):
        """Test that GUIDED mode exists."""
        assert ExecutionMode.GUIDED

    def test_strict_mode_exists(self):
        """Test that STRICT mode exists."""
        assert ExecutionMode.STRICT


class TestTestFormat:
    """Test TestFormat enum."""

    def test_traditional_format_exists(self):
        """Test that TRADITIONAL format exists."""
        assert TestFormat.TRADITIONAL

    def test_gherkin_format_exists(self):
        """Test that GHERKIN format exists."""
        assert TestFormat.GHERKIN


class TestUnifiedTestCase:
    """Test UnifiedTestCase dataclass."""

    def test_unified_test_case_creation(self):
        """Test creating UnifiedTestCase."""
        case = UnifiedTestCase(
            id="test_001",
            name="Test Case",
            format=TestFormat.TRADITIONAL,
            steps=[{"action": "click", "target": "#btn"}]
        )

        assert case.id == "test_001"
        assert case.format == TestFormat.TRADITIONAL

    def test_unified_test_case_gherkin(self):
        """Test UnifiedTestCase for Gherkin."""
        case = UnifiedTestCase(
            id="gherkin_001",
            name="Gherkin Test",
            format=TestFormat.GHERKIN,
            steps=[],
            feature_name="Login Feature",
            scenario_name="Successful Login",
            tags=["@smoke", "@login"]
        )

        assert case.format == TestFormat.GHERKIN
        assert case.scenario_name == "Successful Login"


class TestUnifiedTestResult:
    """Test UnifiedTestResult dataclass."""

    def test_unified_result_creation(self):
        """Test creating UnifiedTestResult."""
        result = UnifiedTestResult(
            test_id="test_001",
            test_name="Test",
            format=TestFormat.TRADITIONAL,
            status="passed",
            total_steps=3,
            passed_steps=3,
            failed_steps=0,
            recovered_steps=0,
            duration_ms=1500,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:00:01",
            step_results=[]
        )

        assert result.status == "passed"
        assert result.passed_steps == 3


class TestUnifiedExecutionReport:
    """Test UnifiedExecutionReport dataclass."""

    def test_report_creation(self):
        """Test creating UnifiedExecutionReport."""
        report = UnifiedExecutionReport(
            id="report_001",
            project_id="proj_001",
            project_name="Test Project",
            format=TestFormat.TRADITIONAL,
            execution_mode=ExecutionMode.GUIDED,
            executed_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:01:00",
            duration_seconds=60,
            total_tests=5,
            passed=4,
            failed=1,
            skipped=0,
            pass_rate=80.0,
            results=[]
        )

        assert report.pass_rate == 80.0
        assert report.failed == 1


class TestGetLearningStats:
    """Test getting learning statistics."""

    def test_get_learning_stats(self, tmp_path):
        """Test get_learning_stats returns dict."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        stats = executor.get_learning_stats()

        assert isinstance(stats, dict)


class TestCallbacks:
    """Test executor callbacks."""

    def test_set_callbacks(self, tmp_path):
        """Test setting callbacks."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        log_callback = Mock()
        progress_callback = Mock()

        executor.set_callbacks(
            log_callback=log_callback,
            progress_callback=progress_callback
        )

        # Internal state should be set
        assert executor._log_callback == log_callback
        assert executor._progress_callback == progress_callback


class TestLogging:
    """Test internal logging."""

    def test_log_calls_callback(self, tmp_path):
        """Test that _log calls the callback."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        callback = Mock()
        executor.set_callbacks(log_callback=callback)

        executor._log("Test message")

        callback.assert_called_with("Test message")

    def test_log_without_callback(self, tmp_path):
        """Test that _log works without callback."""
        executor = UnifiedTestExecutor(data_dir=str(tmp_path / "data"))

        # Should not raise
        executor._log("Test message")

        assert executor is not None
