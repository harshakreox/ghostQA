"""
Pytest configuration and shared fixtures for GhostQA tests.
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


# ==================== Event Loop Fixture ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Mock Page Fixture ====================

@pytest.fixture
def mock_page():
    """Create a mock Playwright page object."""
    page = AsyncMock()

    # Basic properties
    page.url = "https://example.com/test"

    # Navigation
    page.goto = AsyncMock(return_value=None)
    page.reload = AsyncMock(return_value=None)
    page.go_back = AsyncMock(return_value=None)
    page.go_forward = AsyncMock(return_value=None)

    # Content
    page.content = AsyncMock(return_value="<html><body><div id='test'>Test</div></body></html>")
    page.title = AsyncMock(return_value="Test Page")

    # Evaluation
    page.evaluate = AsyncMock(return_value={})

    # Locators
    mock_locator = AsyncMock()
    mock_locator.click = AsyncMock()
    mock_locator.fill = AsyncMock()
    mock_locator.clear = AsyncMock()
    mock_locator.type = AsyncMock()
    mock_locator.press = AsyncMock()
    mock_locator.check = AsyncMock()
    mock_locator.uncheck = AsyncMock()
    mock_locator.hover = AsyncMock()
    mock_locator.dblclick = AsyncMock()
    mock_locator.wait_for = AsyncMock()
    mock_locator.is_visible = AsyncMock(return_value=True)
    mock_locator.text_content = AsyncMock(return_value="Test Content")
    mock_locator.input_value = AsyncMock(return_value="test value")
    mock_locator.select_option = AsyncMock()
    mock_locator.set_input_files = AsyncMock()
    mock_locator.evaluate = AsyncMock()

    page.locator = Mock(return_value=mock_locator)
    page.get_by_text = Mock(return_value=mock_locator)
    page.get_by_label = Mock(return_value=mock_locator)
    page.get_by_placeholder = Mock(return_value=mock_locator)
    page.get_by_role = Mock(return_value=mock_locator)
    page.get_by_test_id = Mock(return_value=mock_locator)

    # Keyboard
    page.keyboard = AsyncMock()
    page.keyboard.press = AsyncMock()

    # Wait
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock(return_value=mock_locator)

    # Screenshot
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")

    return page


# ==================== Mock Browser Fixture ====================

@pytest.fixture
def mock_browser(mock_page):
    """Create a mock Playwright browser object."""
    browser = AsyncMock()
    context = AsyncMock()

    context.new_page = AsyncMock(return_value=mock_page)
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()

    return browser


# ==================== Knowledge Index Fixture ====================

@pytest.fixture
def mock_knowledge_index():
    """Create a mock knowledge index."""
    from unittest.mock import MagicMock

    index = MagicMock()
    index.lookup = Mock(return_value=None)
    index.add_learning = Mock()
    index.get_stats = Mock(return_value={
        "total_elements": 0,
        "domains": [],
        "selectors_by_type": {}
    })
    index.force_save = Mock()

    return index


# ==================== Learning Engine Fixture ====================

@pytest.fixture
def mock_learning_engine():
    """Create a mock learning engine."""
    engine = MagicMock()
    engine.record_selector_result = Mock()
    engine.flush = Mock()
    engine.get_learning_summary = Mock(return_value={
        "total_learnings": 0,
        "success_rate": 0.0
    })

    return engine


# ==================== Pattern Store Fixture ====================

@pytest.fixture
def mock_pattern_store():
    """Create a mock pattern store."""
    store = MagicMock()
    store.find_pattern = Mock(return_value=[])
    store.get_pattern = Mock(return_value=None)
    store.add_pattern = Mock(return_value="pattern_123")
    store.update_pattern_stats = Mock()
    store.get_stats = Mock(return_value={"total_patterns": 0})
    store.get_all_patterns = Mock(return_value=[])

    return store


# ==================== Sample Test Data ====================

@pytest.fixture
def sample_test_case() -> Dict[str, Any]:
    """Sample test case for testing."""
    return {
        "id": "test_login_001",
        "name": "Login Test",
        "steps": [
            {
                "action": "fill",
                "target": "#username",
                "value": "testuser"
            },
            {
                "action": "fill",
                "target": "#password",
                "value": "testpass"
            },
            {
                "action": "click",
                "target": "#login-button"
            }
        ]
    }


@pytest.fixture
def sample_traditional_test() -> Dict[str, Any]:
    """Sample traditional test case."""
    return {
        "id": "trad_test_001",
        "name": "Traditional Login Test",
        "actions": [
            {
                "action": "type",
                "selector": "#user-name",
                "value": "standard_user"
            },
            {
                "action": "type",
                "selector": "#password",
                "value": "secret_sauce"
            },
            {
                "action": "click",
                "selector": "#login-button"
            }
        ]
    }


@pytest.fixture
def sample_gherkin_feature() -> Dict[str, Any]:
    """Sample Gherkin feature for testing."""
    return {
        "id": "feature_001",
        "name": "User Authentication",
        "description": "Test user login functionality",
        "background": {
            "steps": [
                {"keyword": "Given", "text": "I am on the login page"}
            ]
        },
        "scenarios": [
            {
                "name": "Successful Login",
                "steps": [
                    {"keyword": "When", "text": "I enter username 'testuser'"},
                    {"keyword": "And", "text": "I enter password 'testpass'"},
                    {"keyword": "And", "text": "I click the login button"},
                    {"keyword": "Then", "text": "I should see the dashboard"}
                ]
            }
        ]
    }


# ==================== Temp Directory Fixture ====================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data" / "agent_knowledge"
    data_dir.mkdir(parents=True)
    return data_dir
