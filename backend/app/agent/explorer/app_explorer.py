"""
Application Explorer

Automatically crawls and maps web applications to build
comprehensive knowledge without human intervention.

This is the "curiosity" component - it explores like an experienced
tester would, finding all interactive elements and understanding
the application structure.
"""

import asyncio
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Callable, Tuple
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse, urljoin
from enum import Enum

from .page_analyzer import PageAnalyzer, PageAnalysis, PageType, FrameworkType
from .element_extractor import ElementExtractor, ExtractedElement

# Configure logging
logger = logging.getLogger(__name__)


class ExplorationStrategy(Enum):
    """How to explore the application"""
    BREADTH_FIRST = "breadth_first"  # Explore all pages at current depth first
    DEPTH_FIRST = "depth_first"  # Follow links deeply before backtracking
    PRIORITY = "priority"  # Explore high-priority pages first (forms, auth)
    RANDOM = "random"  # Random exploration (good for finding edge cases)


@dataclass
class ExplorationConfig:
    """Configuration for exploration session"""
    max_pages: int = 50
    max_depth: int = 5
    max_time_seconds: int = 300  # 5 minutes default
    strategy: ExplorationStrategy = ExplorationStrategy.PRIORITY
    include_patterns: List[str] = field(default_factory=list)  # URL patterns to include
    exclude_patterns: List[str] = field(default_factory=list)  # URL patterns to exclude
    require_same_domain: bool = True
    explore_forms: bool = True
    capture_screenshots: bool = False
    wait_for_network_idle: bool = True
    click_timeout_ms: int = 5000


@dataclass
class ExploredPage:
    """Information about an explored page"""
    url: str
    title: str
    page_type: PageType
    depth: int
    elements: List[ExtractedElement]
    analysis: PageAnalysis
    screenshot_path: Optional[str] = None
    explored_at: str = ""
    exploration_time_ms: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class ExplorationResult:
    """Complete result of an exploration session"""
    start_url: str
    domain: str
    total_pages: int
    total_elements: int
    total_forms: int
    total_links: int
    detected_frameworks: List[str]
    page_types_found: Dict[str, int]
    pages: List[ExploredPage]
    sitemap: Dict[str, List[str]]  # URL -> outgoing URLs
    started_at: str
    completed_at: str
    duration_seconds: float
    errors: List[str]


class ApplicationExplorer:
    """
    Explores web applications automatically.

    Features:
    - Intelligent crawling with multiple strategies
    - Framework detection
    - Element extraction with selector generation
    - Sitemap building
    - Change detection
    - Integration with knowledge index
    """

    # Page types to prioritize during exploration
    PRIORITY_PAGE_TYPES = [
        PageType.LOGIN,
        PageType.REGISTRATION,
        PageType.FORM,
        PageType.SEARCH,
        PageType.CHECKOUT
    ]

    def __init__(
        self,
        knowledge_index=None,
        learning_engine=None,
        framework_selectors: Optional[Dict] = None,
        data_dir: str = "data/agent_knowledge"
    ):
        """
        Initialize explorer.

        Args:
            knowledge_index: KnowledgeIndex for storing discovered selectors
            learning_engine: LearningEngine for recording learnings
            framework_selectors: Framework selector patterns
            data_dir: Directory for storing exploration results
        """
        self.knowledge_index = knowledge_index
        self.learning_engine = learning_engine
        self.data_dir = Path(data_dir)
        self.page_analyzer = PageAnalyzer()
        self.element_extractor = ElementExtractor(framework_selectors)

        # Exploration state
        self._visited_urls: Set[str] = set()
        self._url_queue: List[Tuple[str, int]] = []  # (url, depth)
        self._explored_pages: List[ExploredPage] = []
        self._sitemap: Dict[str, List[str]] = {}
        self._errors: List[str] = []

        # Callbacks for browser integration
        self._navigate_callback: Optional[Callable] = None
        self._get_html_callback: Optional[Callable] = None
        self._get_dom_callback: Optional[Callable] = None
        self._screenshot_callback: Optional[Callable] = None

    def set_browser_callbacks(
        self,
        navigate: Callable[[str], Any],
        get_html: Callable[[], str],
        get_dom: Callable[[], List[Dict]],
        screenshot: Optional[Callable[[str], None]] = None
    ):
        """
        Set callbacks for browser interaction.

        These callbacks are used to interact with the actual browser
        (e.g., Playwright page object).

        Args:
            navigate: Function to navigate to a URL
            get_html: Function to get current page HTML
            get_dom: Function to get DOM element information
            screenshot: Optional function to capture screenshot
        """
        self._navigate_callback = navigate
        self._get_html_callback = get_html
        self._get_dom_callback = get_dom
        self._screenshot_callback = screenshot

    async def explore(
        self,
        start_url: str,
        config: Optional[ExplorationConfig] = None
    ) -> ExplorationResult:
        """
        Explore an application starting from the given URL.

        Args:
            start_url: URL to start exploration from
            config: Exploration configuration

        Returns:
            Complete exploration results
        """
        config = config or ExplorationConfig()

        # Reset state
        self._visited_urls.clear()
        self._url_queue.clear()
        self._explored_pages.clear()
        self._sitemap.clear()
        self._errors.clear()

        # Parse start URL
        parsed = urlparse(start_url)
        domain = parsed.netloc
        self.page_analyzer.base_url = f"{parsed.scheme}://{domain}"

        # Initialize
        start_time = datetime.utcnow()
        self._url_queue.append((start_url, 0))

        # Explore loop
        while self._url_queue and len(self._explored_pages) < config.max_pages:
            # Check time limit
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > config.max_time_seconds:
                logger.info(f"Exploration time limit reached ({config.max_time_seconds}s)")
                break

            # Get next URL based on strategy
            url, depth = self._get_next_url(config.strategy)

            if url in self._visited_urls:
                continue

            if depth > config.max_depth:
                continue

            # Check URL patterns
            if not self._should_explore_url(url, domain, config):
                continue

            # Explore the page
            try:
                page = await self._explore_page(url, depth, config)
                if page:
                    self._explored_pages.append(page)

                    # Add discovered links to queue
                    for link in page.analysis.links:
                        if link.is_internal and link.url not in self._visited_urls:
                            self._url_queue.append((link.url, depth + 1))

                    # Track sitemap
                    self._sitemap[url] = [l.url for l in page.analysis.links if l.is_internal]

            except Exception as e:
                logger.error(f"Error exploring {url}: {e}")
                self._errors.append(f"{url}: {str(e)}")

        # Compile results
        end_time = datetime.utcnow()

        result = self._compile_results(
            start_url=start_url,
            domain=domain,
            started_at=start_time.isoformat(),
            completed_at=end_time.isoformat(),
            duration_seconds=(end_time - start_time).total_seconds()
        )

        # Save results
        self._save_exploration_results(result, domain)

        # Update knowledge index if available
        if self.knowledge_index:
            self._update_knowledge_index(result, domain)

        return result

    def _get_next_url(self, strategy: ExplorationStrategy) -> Tuple[str, int]:
        """Get the next URL to explore based on strategy"""
        if not self._url_queue:
            return ("", 0)

        if strategy == ExplorationStrategy.BREADTH_FIRST:
            return self._url_queue.pop(0)

        elif strategy == ExplorationStrategy.DEPTH_FIRST:
            return self._url_queue.pop()

        elif strategy == ExplorationStrategy.PRIORITY:
            # Prioritize URLs that look like forms, login, etc.
            priority_keywords = ["login", "register", "signup", "form", "search", "checkout", "cart"]

            for i, (url, depth) in enumerate(self._url_queue):
                url_lower = url.lower()
                if any(kw in url_lower for kw in priority_keywords):
                    return self._url_queue.pop(i)

            # No priority URLs, use breadth-first
            return self._url_queue.pop(0)

        else:  # RANDOM
            import random
            i = random.randint(0, len(self._url_queue) - 1)
            return self._url_queue.pop(i)

    def _should_explore_url(
        self,
        url: str,
        domain: str,
        config: ExplorationConfig
    ) -> bool:
        """Check if URL should be explored"""
        parsed = urlparse(url)

        # Check same domain
        if config.require_same_domain and parsed.netloc != domain:
            return False

        # Check exclude patterns
        import re
        for pattern in config.exclude_patterns:
            if re.search(pattern, url, re.I):
                return False

        # Check include patterns (if specified, URL must match at least one)
        if config.include_patterns:
            if not any(re.search(p, url, re.I) for p in config.include_patterns):
                return False

        # Skip common non-page URLs
        skip_extensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.zip']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False

        return True

    async def _explore_page(
        self,
        url: str,
        depth: int,
        config: ExplorationConfig
    ) -> Optional[ExploredPage]:
        """Explore a single page"""
        self._visited_urls.add(url)
        start_time = datetime.utcnow()
        errors = []

        logger.info(f"Exploring: {url} (depth: {depth})")

        # Navigate to page
        if self._navigate_callback:
            try:
                await self._navigate_callback(url)
            except Exception as e:
                errors.append(f"Navigation error: {str(e)}")
                return None
        else:
            # Mock mode for testing without browser
            logger.warning("No browser callbacks set, using mock exploration")
            return self._create_mock_page(url, depth)

        # Get page HTML
        html = ""
        if self._get_html_callback:
            try:
                html = await self._get_html_callback()
            except Exception as e:
                errors.append(f"HTML fetch error: {str(e)}")

        # Get DOM elements
        dom_elements = []
        if self._get_dom_callback:
            try:
                dom_elements = await self._get_dom_callback()
            except Exception as e:
                errors.append(f"DOM fetch error: {str(e)}")

        # Analyze page
        title = ""
        try:
            analysis = self.page_analyzer.analyze_page(html, url, title)
            title = analysis.title
        except Exception as e:
            errors.append(f"Analysis error: {str(e)}")
            analysis = None

        # Extract elements
        elements = []
        if dom_elements:
            try:
                framework = analysis.primary_framework.value if analysis and analysis.primary_framework else None
                elements = self.element_extractor.extract_from_dom(dom_elements, url, framework)
            except Exception as e:
                errors.append(f"Element extraction error: {str(e)}")
        elif html:
            try:
                elements = self.element_extractor.extract_from_html(html, url)
            except Exception as e:
                errors.append(f"HTML element extraction error: {str(e)}")

        # Capture screenshot
        screenshot_path = None
        if config.capture_screenshots and self._screenshot_callback:
            try:
                filename = f"{hashlib.md5(url.encode()).hexdigest()[:12]}.png"
                screenshot_path = str(self.data_dir / "screenshots" / filename)
                await self._screenshot_callback(screenshot_path)
            except Exception as e:
                errors.append(f"Screenshot error: {str(e)}")

        end_time = datetime.utcnow()

        return ExploredPage(
            url=url,
            title=title,
            page_type=analysis.page_type if analysis else PageType.UNKNOWN,
            depth=depth,
            elements=elements,
            analysis=analysis,
            screenshot_path=screenshot_path,
            explored_at=start_time.isoformat(),
            exploration_time_ms=int((end_time - start_time).total_seconds() * 1000),
            errors=errors
        )

    def _create_mock_page(self, url: str, depth: int) -> ExploredPage:
        """Create a mock page for testing without browser"""
        return ExploredPage(
            url=url,
            title=f"Mock Page - {url}",
            page_type=PageType.UNKNOWN,
            depth=depth,
            elements=[],
            analysis=PageAnalysis(
                url=url,
                title="",
                page_type=PageType.UNKNOWN,
                detected_frameworks=[],
                primary_framework=None,
                forms=[],
                links=[],
                interactive_elements_count=0,
                has_authentication=False,
                has_navigation=False,
                has_search=False,
                has_pagination=False,
                has_modals=False,
                has_tables=False,
                content_hash="",
                meta_info={}
            ),
            explored_at=datetime.utcnow().isoformat()
        )

    def _compile_results(
        self,
        start_url: str,
        domain: str,
        started_at: str,
        completed_at: str,
        duration_seconds: float
    ) -> ExplorationResult:
        """Compile exploration results"""
        # Count page types
        page_types: Dict[str, int] = {}
        for page in self._explored_pages:
            pt = page.page_type.value
            page_types[pt] = page_types.get(pt, 0) + 1

        # Collect frameworks
        frameworks: Set[str] = set()
        for page in self._explored_pages:
            if page.analysis and page.analysis.detected_frameworks:
                for fw in page.analysis.detected_frameworks:
                    if fw != FrameworkType.UNKNOWN:
                        frameworks.add(fw.value)

        # Count totals
        total_elements = sum(len(p.elements) for p in self._explored_pages)
        total_forms = sum(
            len(p.analysis.forms) if p.analysis else 0
            for p in self._explored_pages
        )
        total_links = sum(
            len(p.analysis.links) if p.analysis else 0
            for p in self._explored_pages
        )

        return ExplorationResult(
            start_url=start_url,
            domain=domain,
            total_pages=len(self._explored_pages),
            total_elements=total_elements,
            total_forms=total_forms,
            total_links=total_links,
            detected_frameworks=list(frameworks),
            page_types_found=page_types,
            pages=self._explored_pages,
            sitemap=self._sitemap,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            errors=self._errors
        )

    def _save_exploration_results(self, result: ExplorationResult, domain: str):
        """Save exploration results to disk"""
        # Create output directory
        output_dir = self.data_dir / "explorations"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{domain.replace('.', '_')}_{timestamp}.json"

        # Convert to serializable format
        result_dict = {
            "start_url": result.start_url,
            "domain": result.domain,
            "total_pages": result.total_pages,
            "total_elements": result.total_elements,
            "total_forms": result.total_forms,
            "total_links": result.total_links,
            "detected_frameworks": result.detected_frameworks,
            "page_types_found": result.page_types_found,
            "sitemap": result.sitemap,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
            "pages": [
                {
                    "url": p.url,
                    "title": p.title,
                    "page_type": p.page_type.value,
                    "depth": p.depth,
                    "element_count": len(p.elements),
                    "elements": [
                        {
                            "type": e.element_type.value,
                            "key": e.element_key,
                            "selectors": e.selectors,
                            "text": e.text_content[:100] if e.text_content else ""
                        }
                        for e in p.elements
                    ],
                    "explored_at": p.explored_at,
                    "exploration_time_ms": p.exploration_time_ms,
                    "errors": p.errors
                }
                for p in result.pages
            ]
        }

        with open(output_dir / filename, 'w') as f:
            json.dump(result_dict, f, indent=2)

        logger.info(f"Saved exploration results to {filename}")

    def _update_knowledge_index(self, result: ExplorationResult, domain: str):
        """Update knowledge index with discovered elements"""
        for page in result.pages:
            page_key = urlparse(page.url).path or "/"

            for element in page.elements:
                # Add each selector to knowledge index
                for selector_info in element.selectors:
                    self.knowledge_index.add_learning(
                        domain=domain,
                        page=page_key,
                        element_key=element.element_key,
                        selector=selector_info["selector"],
                        selector_type=selector_info.get("type", "css"),
                        success=True,  # New discoveries are assumed correct
                        ai_assisted=False,  # Explorer-discovered
                        context={
                            "element_type": element.element_type.value,
                            "strategy": selector_info.get("strategy", "unknown"),
                            "source": "explorer"
                        }
                    )

        logger.info(f"Updated knowledge index with {result.total_elements} elements from {domain}")

    # ==================== Utility Methods ====================

    def explore_sync(
        self,
        start_url: str,
        config: Optional[ExplorationConfig] = None
    ) -> ExplorationResult:
        """Synchronous wrapper for explore()"""
        return asyncio.run(self.explore(start_url, config))

    def get_exploration_history(self, domain: str) -> List[Dict[str, Any]]:
        """Get history of explorations for a domain"""
        output_dir = self.data_dir / "explorations"
        if not output_dir.exists():
            return []

        history = []
        pattern = f"{domain.replace('.', '_')}_*.json"

        for file in output_dir.glob(pattern):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    history.append({
                        "file": file.name,
                        "started_at": data.get("started_at"),
                        "total_pages": data.get("total_pages"),
                        "total_elements": data.get("total_elements"),
                        "duration_seconds": data.get("duration_seconds")
                    })
            except Exception:
                pass

        return sorted(history, key=lambda x: x["started_at"], reverse=True)

    def load_exploration(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load a previous exploration result"""
        file_path = self.data_dir / "explorations" / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None

    def get_page_summary(self, result: ExplorationResult) -> Dict[str, Any]:
        """Get a summary of explored pages"""
        summary = {
            "total_pages": result.total_pages,
            "by_type": result.page_types_found,
            "pages_with_forms": sum(
                1 for p in result.pages
                if p.analysis and p.analysis.forms
            ),
            "pages_with_auth": sum(
                1 for p in result.pages
                if p.analysis and p.analysis.has_authentication
            ),
            "average_elements_per_page": (
                result.total_elements / result.total_pages
                if result.total_pages > 0 else 0
            ),
            "high_priority_pages": [
                {
                    "url": p.url,
                    "type": p.page_type.value,
                    "elements": len(p.elements)
                }
                for p in result.pages
                if p.page_type in self.PRIORITY_PAGE_TYPES
            ]
        }
        return summary

    async def quick_scan(self, url: str) -> Dict[str, Any]:
        """
        Quick scan of a single page without full exploration.

        Useful for initial assessment or pre-test analysis.
        """
        config = ExplorationConfig(
            max_pages=1,
            max_depth=0,
            capture_screenshots=False
        )

        result = await self.explore(url, config)

        if result.pages:
            page = result.pages[0]
            return {
                "url": url,
                "title": page.title,
                "page_type": page.page_type.value,
                "frameworks": result.detected_frameworks,
                "element_count": len(page.elements),
                "form_count": len(page.analysis.forms) if page.analysis else 0,
                "has_auth": page.analysis.has_authentication if page.analysis else False,
                "elements": [
                    {
                        "type": e.element_type.value,
                        "key": e.element_key,
                        "best_selector": e.selectors[0] if e.selectors else None
                    }
                    for e in page.elements[:20]  # First 20 elements
                ]
            }

        return {"url": url, "error": "Failed to scan page"}
