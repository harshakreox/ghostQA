"""
Context Module

Provides project-level context and navigation intelligence
to help the agent think and navigate like a manual tester.
"""

from .project_context import (
    ProjectContext,
    PageInfo,
    PageType,
    PageSignature,
    NavigationElement,
    NavigationPath,
    get_project_context
)

from .navigation_intelligence import (
    NavigationIntelligence,
    NavigationStrategy,
    NavigableElement,
    NavigationResult
)

__all__ = [
    'ProjectContext',
    'PageInfo',
    'PageType',
    'PageSignature',
    'NavigationElement',
    'NavigationPath',
    'get_project_context',
    'NavigationIntelligence',
    'NavigationStrategy',
    'NavigableElement',
    'NavigationResult'
]
