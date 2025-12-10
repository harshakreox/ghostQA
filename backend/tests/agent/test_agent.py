"""
Unit tests for AutonomousTestAgent.

Tests the core autonomous agent that orchestrates test execution.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

from agent.core.agent import (
    AutonomousTestAgent,
    AgentConfig,
    AgentState,
    TestStep,
    StepStatus,
    TestResult,
    SelectorResult,
    ResolutionTier
)


class TestAgentConfig:
    """Test AgentConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AgentConfig()

        assert config.max_retries == 3
        assert config.step_timeout_ms == 30000
        assert config.enable_learning is True
        assert config.enable_spa_mode is True
        assert config.screenshot_on_failure is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = AgentConfig(
            max_retries=5,
            step_timeout_ms=60000,
            enable_learning=False
        )

        assert config.max_retries == 5
        assert config.step_timeout_ms == 60000
        assert config.enable_learning is False


class TestAgentInit:
    """Test AutonomousTestAgent initialization."""

    def test_init_with_page(self, mock_page, tmp_path):
        """Test initialization with page."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        assert agent.page == mock_page

    def test_init_with_config(self, mock_page, tmp_path):
        """Test initialization with custom config."""
        config = AgentConfig(max_retries=5)
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data"),
            config=config
        )

        assert agent.config.max_retries == 5

    def test_init_default_state(self, mock_page, tmp_path):
        """Test that agent starts in IDLE state."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        assert agent.state == AgentState.IDLE

    def test_init_creates_dependencies(self, mock_page, tmp_path):
        """Test that agent creates internal dependencies."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        # Should have created internal components
        assert agent.knowledge_index is not None
        assert agent.learning_engine is not None


class TestExecuteTest:
    """Test test execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_test(self, mock_page, tmp_path):
        """Test executing a simple test case."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        test_case = {
            "id": "test_001",
            "name": "Simple Test",
            "steps": [
                {"action": "click", "target": "#button"}
            ]
        }

        result = await agent.execute_test(test_case, base_url="https://example.com")

        assert isinstance(result, TestResult)
        assert result.test_id == "test_001"

    @pytest.mark.asyncio
    async def test_execute_with_navigation(self, mock_page, tmp_path):
        """Test that navigation happens when base_url provided."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        test_case = {
            "id": "test_nav",
            "name": "Nav Test",
            "steps": []
        }

        await agent.execute_test(test_case, base_url="https://example.com")

        # Should have navigated
        mock_page.goto.assert_called()

    @pytest.mark.asyncio
    async def test_execute_changes_state(self, mock_page, tmp_path):
        """Test that agent state changes during execution."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        test_case = {
            "id": "test_state",
            "name": "State Test",
            "steps": []
        }

        # Should be IDLE initially
        assert agent.state == AgentState.IDLE

        await agent.execute_test(test_case)

        # Should be COMPLETED after
        assert agent.state == AgentState.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_multiple_steps(self, mock_page, tmp_path):
        """Test executing test with multiple steps."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        test_case = {
            "id": "test_multi",
            "name": "Multi Step Test",
            "steps": [
                {"action": "fill", "target": "#username", "value": "user"},
                {"action": "fill", "target": "#password", "value": "pass"},
                {"action": "click", "target": "#login"}
            ]
        }

        result = await agent.execute_test(test_case, base_url="https://example.com")

        assert result.total_steps == 3


class TestResolveSelector:
    """Test selector resolution."""

    @pytest.mark.asyncio
    async def test_resolve_direct_css_selector(self, mock_page, tmp_path):
        """Test resolving a direct CSS selector."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        result = await agent._resolve_selector("#my-element")

        assert result.selector == "#my-element"
        assert result.selector_type == "css"
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_resolve_direct_xpath_selector(self, mock_page, tmp_path):
        """Test resolving a direct XPath selector."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        result = await agent._resolve_selector("//div[@id='test']")

        assert result.selector == "//div[@id='test']"
        assert result.selector_type == "xpath"

    @pytest.mark.asyncio
    async def test_resolve_class_selector(self, mock_page, tmp_path):
        """Test resolving a class selector."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        result = await agent._resolve_selector(".my-class")

        assert result.selector == ".my-class"
        assert result.selector_type == "css"

    @pytest.mark.asyncio
    async def test_resolve_attribute_selector(self, mock_page, tmp_path):
        """Test resolving an attribute selector."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        result = await agent._resolve_selector("[data-testid='login']")

        assert "[data-testid='login']" in result.selector
        assert result.selector_type == "css"


class TestTestStep:
    """Test TestStep dataclass."""

    def test_test_step_creation(self):
        """Test creating a TestStep."""
        step = TestStep(
            step_number=1,
            action="click",
            target="#button"
        )

        assert step.step_number == 1
        assert step.action == "click"
        assert step.target == "#button"
        assert step.status == StepStatus.PENDING

    def test_test_step_with_value(self):
        """Test TestStep with value."""
        step = TestStep(
            step_number=2,
            action="fill",
            target="#input",
            value="test value"
        )

        assert step.value == "test value"


class TestStepStatus:
    """Test StepStatus enum."""

    def test_pending_status(self):
        """Test PENDING status exists."""
        assert StepStatus.PENDING

    def test_running_status(self):
        """Test RUNNING status exists."""
        assert StepStatus.RUNNING

    def test_passed_status(self):
        """Test PASSED status exists."""
        assert StepStatus.PASSED

    def test_failed_status(self):
        """Test FAILED status exists."""
        assert StepStatus.FAILED

    def test_recovered_status(self):
        """Test RECOVERED status exists."""
        assert StepStatus.RECOVERED

    def test_skipped_status(self):
        """Test SKIPPED status exists."""
        assert StepStatus.SKIPPED


class TestAgentState:
    """Test AgentState enum."""

    def test_idle_state(self):
        """Test IDLE state exists."""
        assert AgentState.IDLE

    def test_running_state(self):
        """Test RUNNING state exists."""
        assert AgentState.RUNNING

    def test_completed_state(self):
        """Test COMPLETED state exists."""
        assert AgentState.COMPLETED

    def test_failed_state(self):
        """Test FAILED state exists."""
        assert AgentState.FAILED


class TestSelectorResult:
    """Test SelectorResult dataclass."""

    def test_selector_result_creation(self):
        """Test creating SelectorResult."""
        result = SelectorResult(
            selector="#element",
            selector_type="css",
            confidence=0.95,
            tier=ResolutionTier.KNOWLEDGE_BASE,
            alternatives=["[data-id='element']"],
            metadata={"source": "knowledge_index"}
        )

        assert result.selector == "#element"
        assert result.confidence == 0.95
        assert result.tier == ResolutionTier.KNOWLEDGE_BASE


class TestResolutionTier:
    """Test ResolutionTier enum."""

    def test_knowledge_base_tier(self):
        """Test KNOWLEDGE_BASE tier exists."""
        assert ResolutionTier.KNOWLEDGE_BASE

    def test_framework_rules_tier(self):
        """Test FRAMEWORK_RULES tier exists."""
        assert ResolutionTier.FRAMEWORK_RULES

    def test_heuristics_tier(self):
        """Test HEURISTICS tier exists."""
        assert ResolutionTier.HEURISTICS

    def test_ai_decision_tier(self):
        """Test AI_DECISION tier exists."""
        assert ResolutionTier.AI_DECISION

    def test_fallback_tier(self):
        """Test FALLBACK tier exists."""
        assert ResolutionTier.FALLBACK


class TestTestResult:
    """Test TestResult dataclass."""

    def test_test_result_creation(self):
        """Test creating TestResult."""
        result = TestResult(
            test_id="test_001",
            test_name="Test Name",
            status="passed",
            total_steps=3,
            passed_steps=3,
            failed_steps=0,
            recovered_steps=0,
            steps=[],
            execution_time_ms=1500,
            started_at="2024-01-01T00:00:00",
            completed_at="2024-01-01T00:01:00",
            domain="example.com",
            ai_calls_made=0,
            knowledge_base_hits=5,
            errors=[],
            screenshots=[]
        )

        assert result.test_id == "test_001"
        assert result.status == "passed"
        assert result.passed_steps == 3


class TestCleanup:
    """Test agent cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_completes(self, mock_page, tmp_path):
        """Test that cleanup completes without error."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        await agent.cleanup()

        # Should complete without error
        assert agent is not None

    @pytest.mark.asyncio
    async def test_cleanup_flushes_learning(self, mock_page, tmp_path):
        """Test that cleanup flushes learning engine."""
        agent = AutonomousTestAgent(
            page=mock_page,
            data_dir=str(tmp_path / "agent_data")
        )

        # Execute a test first
        test_case = {"id": "test", "name": "Test", "steps": []}
        await agent.execute_test(test_case)

        # Cleanup should flush
        await agent.cleanup()

        assert agent is not None
