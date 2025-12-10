"""
Core Agent Module

The main autonomous test agent that orchestrates all components
to execute tests like an experienced human tester.

Supports both Single Page Applications (SPAs) and Multi-Page Applications (MPAs).
"""

from .agent import AutonomousTestAgent
from .selector_service import SelectorService
from .action_executor import ActionExecutor
from .recovery_handler import RecoveryHandler
from .spa_handler import SPAHandler, SPAFramework, SPAState

__all__ = [
    "AutonomousTestAgent",
    "SelectorService",
    "ActionExecutor",
    "RecoveryHandler",
    "SPAHandler",
    "SPAFramework",
    "SPAState"
]
