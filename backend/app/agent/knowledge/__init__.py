"""
Knowledge Base System

Stores and retrieves learned element selectors, action patterns,
and recovery strategies with O(1) lookup performance.
"""

from .knowledge_index import KnowledgeIndex
from .framework_selectors import FRAMEWORK_SELECTORS, UNIVERSAL_PATTERNS
from .pattern_store import PatternStore
from .learning_engine import LearningEngine

__all__ = [
    "KnowledgeIndex",
    "FRAMEWORK_SELECTORS",
    "UNIVERSAL_PATTERNS",
    "PatternStore",
    "LearningEngine"
]
