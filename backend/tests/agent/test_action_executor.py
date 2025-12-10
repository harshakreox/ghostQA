"""
Unit tests for ActionExecutor.

Tests the action execution system that performs browser actions.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

from agent.core.action_executor import ActionExecutor, ActionResult, ActionStatus


class TestActionExecutorInit:
    """Test ActionExecutor initialization."""

    def test_init_with_page(self, mock_page):
        """Test initialization with page."""
        executor = ActionExecutor(page=mock_page)

        assert executor.page == mock_page

    def test_init_defaults(self):
        """Test initialization default values."""
        executor = ActionExecutor()

        assert executor.timeout == ActionExecutor.DEFAULT_TIMEOUT
        assert executor.wait_after_action == ActionExecutor.DEFAULT_WAIT_AFTER_ACTION
        assert executor.capture_screenshots is False
        assert executor.highlight_elements is False

    def test_set_page(self, mock_page):
        """Test setting page after init."""
        executor = ActionExecutor()
        executor.set_page(mock_page)

        assert executor.page == mock_page


class TestClickAction:
    """Test click action execution."""

    @pytest.mark.asyncio
    async def test_click_success(self, mock_page):
        """Test successful click action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.click("#button", selector_type="css")

        assert result.status == ActionStatus.SUCCESS
        assert result.action == "click"

    @pytest.mark.asyncio
    async def test_click_with_alternatives(self, mock_page):
        """Test click with alternative selectors."""
        executor = ActionExecutor(page=mock_page)

        alternatives = [
            {"selector": ".btn-primary", "type": "css"},
            {"selector": "button[type='submit']", "type": "css"}
        ]

        result = await executor.click("#button", alternatives=alternatives)

        assert result.status == ActionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_click_timeout(self, mock_page):
        """Test click action with timeout."""
        # Make wait_for raise timeout
        mock_page.locator.return_value.wait_for = AsyncMock(
            side_effect=Exception("Timeout 10000ms exceeded")
        )

        executor = ActionExecutor(page=mock_page)

        result = await executor.click("#nonexistent")

        assert result.status == ActionStatus.ELEMENT_NOT_FOUND


class TestFillAction:
    """Test fill action execution."""

    @pytest.mark.asyncio
    async def test_fill_success(self, mock_page):
        """Test successful fill action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.fill("#input", "test value")

        assert result.status == ActionStatus.SUCCESS
        assert result.action == "fill"

    @pytest.mark.asyncio
    async def test_fill_clears_first(self, mock_page):
        """Test that fill clears input first by default."""
        executor = ActionExecutor(page=mock_page)

        await executor.fill("#input", "new value", clear_first=True)

        mock_page.locator.return_value.clear.assert_called()
        mock_page.locator.return_value.fill.assert_called_with("new value")

    @pytest.mark.asyncio
    async def test_fill_without_clear(self, mock_page):
        """Test fill without clearing first."""
        executor = ActionExecutor(page=mock_page)

        await executor.fill("#input", "appended", clear_first=False)

        mock_page.locator.return_value.clear.assert_not_called()


class TestTypeAction:
    """Test type action execution."""

    @pytest.mark.asyncio
    async def test_type_success(self, mock_page):
        """Test successful type action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.type_text("#input", "typed text", delay=50)

        assert result.status == ActionStatus.SUCCESS
        mock_page.locator.return_value.type.assert_called_with("typed text", delay=50)


class TestSelectAction:
    """Test select option action."""

    @pytest.mark.asyncio
    async def test_select_by_value(self, mock_page):
        """Test selecting by value."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.select_option("#dropdown", "option1", by="value")

        assert result.status == ActionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_select_by_label(self, mock_page):
        """Test selecting by label."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.select_option("#dropdown", "Option Label", by="label")

        assert result.status == ActionStatus.SUCCESS


class TestNavigationActions:
    """Test navigation actions."""

    @pytest.mark.asyncio
    async def test_navigate_success(self, mock_page):
        """Test successful navigation."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.navigate("https://example.com")

        assert result.status == ActionStatus.SUCCESS
        assert result.navigation_occurred is True
        mock_page.goto.assert_called_with("https://example.com", wait_until="load")

    @pytest.mark.asyncio
    async def test_go_back(self, mock_page):
        """Test go back action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.go_back()

        assert result.status == ActionStatus.SUCCESS
        mock_page.go_back.assert_called()

    @pytest.mark.asyncio
    async def test_go_forward(self, mock_page):
        """Test go forward action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.go_forward()

        assert result.status == ActionStatus.SUCCESS
        mock_page.go_forward.assert_called()

    @pytest.mark.asyncio
    async def test_refresh(self, mock_page):
        """Test refresh action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.refresh()

        assert result.status == ActionStatus.SUCCESS
        mock_page.reload.assert_called()


class TestWaitActions:
    """Test wait actions."""

    @pytest.mark.asyncio
    async def test_wait_for_element(self, mock_page):
        """Test wait for element action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.wait_for_element("#element", state="visible")

        assert result.status == ActionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_wait_fixed_time(self, mock_page):
        """Test wait for fixed time."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.wait(100)  # 100ms

        assert result.status == ActionStatus.SUCCESS
        assert result.action == "wait"


class TestAssertActions:
    """Test assertion actions."""

    @pytest.mark.asyncio
    async def test_assert_visible_success(self, mock_page):
        """Test assert visible when element is visible."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.assert_visible("#visible-element")

        assert result.status == ActionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_assert_text_success(self, mock_page):
        """Test assert text when text matches."""
        mock_page.locator.return_value.text_content = AsyncMock(return_value="Expected Text")

        executor = ActionExecutor(page=mock_page)

        result = await executor.assert_text("#element", "Expected Text")

        assert result.status == ActionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_assert_text_failure(self, mock_page):
        """Test assert text when text doesn't match."""
        mock_page.locator.return_value.text_content = AsyncMock(return_value="Different Text")

        executor = ActionExecutor(page=mock_page)

        result = await executor.assert_text("#element", "Expected Text")

        assert result.status == ActionStatus.ERROR
        assert "Expected" in result.error_message


class TestPressKeyAction:
    """Test press key action."""

    @pytest.mark.asyncio
    async def test_press_key_on_page(self, mock_page):
        """Test pressing key on page."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.press_key("Enter")

        assert result.status == ActionStatus.SUCCESS
        mock_page.keyboard.press.assert_called_with("Enter")

    @pytest.mark.asyncio
    async def test_press_key_on_element(self, mock_page):
        """Test pressing key on specific element."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.press_key("Tab", selector="#input")

        assert result.status == ActionStatus.SUCCESS


class TestScrollAction:
    """Test scroll action."""

    @pytest.mark.asyncio
    async def test_scroll_down(self, mock_page):
        """Test scroll down action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.scroll(direction="down", amount=300)

        assert result.status == ActionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_scroll_up(self, mock_page):
        """Test scroll up action."""
        executor = ActionExecutor(page=mock_page)

        result = await executor.scroll(direction="up", amount=200)

        assert result.status == ActionStatus.SUCCESS


class TestActionResult:
    """Test ActionResult dataclass."""

    def test_action_result_creation(self):
        """Test creating ActionResult."""
        result = ActionResult(
            status=ActionStatus.SUCCESS,
            action="click",
            selector="#button",
            selector_type="css",
            execution_time_ms=150
        )

        assert result.status == ActionStatus.SUCCESS
        assert result.action == "click"
        assert result.execution_time_ms == 150

    def test_action_result_with_error(self):
        """Test ActionResult with error."""
        result = ActionResult(
            status=ActionStatus.ELEMENT_NOT_FOUND,
            action="fill",
            selector="#missing",
            selector_type="css",
            execution_time_ms=5000,
            error_message="Element not found"
        )

        assert result.status == ActionStatus.ELEMENT_NOT_FOUND
        assert result.error_message == "Element not found"


class TestActionStatus:
    """Test ActionStatus enum."""

    def test_status_values_exist(self):
        """Test that expected status values exist."""
        assert ActionStatus.SUCCESS
        assert ActionStatus.ELEMENT_NOT_FOUND
        assert ActionStatus.ELEMENT_NOT_VISIBLE
        assert ActionStatus.TIMEOUT
        assert ActionStatus.ERROR
        assert ActionStatus.RECOVERED


class TestCallbacks:
    """Test action callbacks."""

    @pytest.mark.asyncio
    async def test_before_action_callback(self, mock_page):
        """Test that before action callback is called."""
        callback = AsyncMock()
        executor = ActionExecutor(page=mock_page)
        executor.set_callbacks(before_action=callback)

        await executor.click("#button")

        callback.assert_called()

    @pytest.mark.asyncio
    async def test_after_action_callback(self, mock_page):
        """Test that after action callback is called."""
        callback = AsyncMock()
        executor = ActionExecutor(page=mock_page)
        executor.set_callbacks(after_action=callback)

        await executor.click("#button")

        callback.assert_called()
