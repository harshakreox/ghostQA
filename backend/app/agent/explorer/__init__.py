"""
Application Explorer Module

Automatically crawls and maps web applications to build
the knowledge base without human intervention.
"""

from .app_explorer import ApplicationExplorer
from .page_analyzer import PageAnalyzer
from .element_extractor import ElementExtractor

__all__ = [
    "ApplicationExplorer",
    "PageAnalyzer",
    "ElementExtractor"
]
