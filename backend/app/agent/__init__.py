"""
Autonomous Test Agent System

A self-learning, AI-powered test execution framework that:
- Executes tests autonomously like an experienced QA tester
- Learns from every execution to reduce AI dependency
- Uses tiered decision making (Knowledge Base → Framework Rules → Heuristics → AI)
- Gracefully degrades when AI is unavailable
- Works with both Traditional and Gherkin test formats
- Supports SPAs and MPAs
"""

from .core.agent import AutonomousTestAgent, AgentConfig
from .core.selector_service import SelectorService
from .core.spa_handler import SPAHandler, SPAFramework
from .knowledge.knowledge_index import KnowledgeIndex
from .knowledge.learning_engine import LearningEngine
from .knowledge.pattern_store import PatternStore
from .explorer.app_explorer import ApplicationExplorer
from .recorder.action_recorder import ActionRecorder
from .unified_executor import (
    UnifiedTestExecutor,
    UnifiedTestCase,
    UnifiedTestResult,
    UnifiedExecutionReport,
    TestFormat,
    ExecutionMode
)
from .training.data_collector import TrainingDataCollector, DataSource
from .training.import_export import KnowledgeImportExport

__all__ = [
    # Core
    "AutonomousTestAgent",
    "AgentConfig",
    "SelectorService",
    "SPAHandler",
    "SPAFramework",
    # Knowledge
    "KnowledgeIndex",
    "LearningEngine",
    "PatternStore",
    # Exploration & Recording
    "ApplicationExplorer",
    "ActionRecorder",
    # Unified Execution
    "UnifiedTestExecutor",
    "UnifiedTestCase",
    "UnifiedTestResult",
    "UnifiedExecutionReport",
    "TestFormat",
    "ExecutionMode",
    # Training
    "TrainingDataCollector",
    "DataSource",
    "KnowledgeImportExport"
]

__version__ = "1.0.0"
