"""
QA Brain - Neural Network-Inspired Decision System for GhostQA
================================================================

This module implements a self-learning "brain" for the QA agent that:
1. Learns from every test execution
2. Makes intelligent decisions with minimal AI usage
3. Predicts outcomes based on past experience
4. Gets smarter over time

Architecture:
- Memory Systems: Store learned patterns (pages, actions, errors, workflows)
- Decision Engine: Make decisions using pattern matching
- Learning Loop: Continuously improve from successes/failures
- AI Gateway: Fallback to AI only when confidence is low

Token Efficiency:
- 95%+ of decisions made locally (0 tokens)
- AI called only for novel situations
- All AI responses cached and learned
"""

from .qa_brain import QABrain
from .memory import (
    PageMemory, ActionMemory, ErrorMemory, WorkflowMemory,
    MemoryEntry, PageSignature, ActionPattern, ErrorPattern, WorkflowPattern
)
from .decision_engine import DecisionEngine, Decision, DecisionType
from .learning_loop import LearningLoop, LearningEvent, EventType
from .ai_gateway import AIGateway, AIRequest, AIResponse

__all__ = [
    'QABrain',
    'PageMemory', 'ActionMemory', 'ErrorMemory', 'WorkflowMemory',
    'MemoryEntry', 'PageSignature', 'ActionPattern', 'ErrorPattern', 'WorkflowPattern',
    'DecisionEngine', 'Decision', 'DecisionType',
    'LearningLoop', 'LearningEvent', 'EventType',
    'AIGateway', 'AIRequest', 'AIResponse'
]
