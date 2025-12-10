"""
Training Data Collector

Collects training data from multiple sources to build
the knowledge base. This is critical for reducing AI dependency.

Training Sources:
1. Test Execution Results - Learn from actual test runs
2. Application Exploration - Crawl apps to discover elements
3. Human Recording Sessions - Watch humans test
4. Import from External - Import patterns/selectors
5. Synthetic Generation - Generate variations from known patterns
6. Historical Test Reports - Learn from past executions
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio

# Configure logging
logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Sources of training data"""
    TEST_EXECUTION = "test_execution"
    APP_EXPLORATION = "app_exploration"
    HUMAN_RECORDING = "human_recording"
    EXTERNAL_IMPORT = "external_import"
    SYNTHETIC = "synthetic"
    HISTORICAL = "historical"
    COMMUNITY = "community"


@dataclass
class TrainingBatch:
    """A batch of training data"""
    id: str
    source: DataSource
    domain: str
    collected_at: str
    elements_count: int
    patterns_count: int
    data: List[Dict[str, Any]]


class TrainingDataCollector:
    """
    Collects and manages training data from multiple sources.

    This is the key to reducing AI dependency over time.
    The more training data collected, the less AI is needed.
    """

    def __init__(
        self,
        knowledge_index,
        learning_engine,
        pattern_store,
        data_dir: str = "data/agent_knowledge"
    ):
        """
        Initialize training data collector.

        Args:
            knowledge_index: KnowledgeIndex for storing learned selectors
            learning_engine: LearningEngine for processing learnings
            pattern_store: PatternStore for action patterns
            data_dir: Directory for training data storage
        """
        self.knowledge_index = knowledge_index
        self.learning_engine = learning_engine
        self.pattern_store = pattern_store
        self.data_dir = Path(data_dir)

        # Training data storage
        self.training_dir = self.data_dir / "training"
        self.training_dir.mkdir(parents=True, exist_ok=True)

        # Collection stats
        self._collection_stats = {
            source.value: {"batches": 0, "elements": 0, "patterns": 0}
            for source in DataSource
        }

        # Load existing stats
        self._load_stats()

    def _load_stats(self):
        """Load collection statistics"""
        stats_file = self.training_dir / "collection_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    self._collection_stats = json.load(f)
            except Exception:
                pass

    def _save_stats(self):
        """Save collection statistics"""
        stats_file = self.training_dir / "collection_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(self._collection_stats, f, indent=2)

    # ==================== Source 1: Test Execution ====================

    def collect_from_test_execution(
        self,
        test_result: Dict[str, Any],
        domain: str
    ) -> TrainingBatch:
        """
        Collect training data from a test execution result.

        This is automatic - every test run teaches the system.

        Args:
            test_result: Test execution result with steps
            domain: Website domain

        Returns:
            TrainingBatch with collected data
        """
        elements = []
        patterns = []

        for step in test_result.get("steps", []):
            # Only learn from successful steps
            if step.get("status") != "passed":
                continue

            selector = step.get("selector_used")
            if selector:
                elements.append({
                    "action": step.get("action"),
                    "target": step.get("target"),
                    "selector": selector,
                    "selector_type": step.get("selector_type", "css"),
                    "page": step.get("page", "/"),
                    "success": True
                })

        # Detect patterns in step sequences
        step_sequence = [
            {"action": s.get("action"), "target": s.get("target")}
            for s in test_result.get("steps", [])
            if s.get("status") == "passed"
        ]

        if len(step_sequence) >= 2:
            patterns.append({
                "type": "sequence",
                "steps": step_sequence,
                "test_name": test_result.get("test_name"),
                "success": test_result.get("status") == "passed"
            })

        batch = self._create_batch(
            source=DataSource.TEST_EXECUTION,
            domain=domain,
            elements=elements,
            patterns=patterns
        )

        # Process into knowledge base
        self._process_batch(batch)

        return batch

    # ==================== Source 2: App Exploration ====================

    async def collect_from_exploration(
        self,
        base_url: str,
        max_pages: int = 20,
        page=None,
        progress_callback: Optional[Callable] = None
    ) -> TrainingBatch:
        """
        Collect training data by exploring an application.

        This builds initial knowledge without any test runs.

        Args:
            base_url: Application URL
            max_pages: Maximum pages to explore
            page: Playwright page object
            progress_callback: Progress update callback

        Returns:
            TrainingBatch with discovered elements
        """
        from ..explorer.app_explorer import ApplicationExplorer, ExplorationConfig
        from urllib.parse import urlparse

        domain = urlparse(base_url).netloc
        elements = []
        patterns = []

        explorer = ApplicationExplorer(
            knowledge_index=self.knowledge_index,
            learning_engine=self.learning_engine
        )

        if page:
            explorer.set_browser_callbacks(
                navigate=lambda url: page.goto(url),
                get_html=lambda: page.content(),
                get_dom=self._create_dom_extractor(page)
            )

            result = await explorer.explore(
                base_url,
                ExplorationConfig(
                    max_pages=max_pages,
                    max_depth=3,
                    capture_screenshots=False
                )
            )

            # Extract elements from exploration
            for explored_page in result.pages:
                for element in explored_page.elements:
                    for selector_info in element.selectors:
                        elements.append({
                            "element_key": element.element_key,
                            "element_type": element.element_type.value,
                            "selector": selector_info["selector"],
                            "selector_type": selector_info.get("type", "css"),
                            "page": explored_page.url,
                            "confidence": selector_info.get("confidence", 0.8)
                        })

            # Extract patterns from forms
            for explored_page in result.pages:
                if explored_page.analysis and explored_page.analysis.forms:
                    for form in explored_page.analysis.forms:
                        patterns.append({
                            "type": "form",
                            "form_name": form.form_name or form.form_id,
                            "fields": form.fields,
                            "page": explored_page.url
                        })

            if progress_callback:
                progress_callback({
                    "pages_explored": result.total_pages,
                    "elements_found": len(elements)
                })

        batch = self._create_batch(
            source=DataSource.APP_EXPLORATION,
            domain=domain,
            elements=elements,
            patterns=patterns
        )

        self._process_batch(batch)

        return batch

    def _create_dom_extractor(self, page):
        """Create DOM extraction function"""
        async def extract_dom():
            return await page.evaluate("""
                () => {
                    const interactive = document.querySelectorAll(
                        'button, a, input, select, textarea, [role="button"], [onclick]'
                    );
                    return Array.from(interactive).slice(0, 200).map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            tagName: el.tagName,
                            attributes: Object.fromEntries(
                                Array.from(el.attributes).map(a => [a.name, a.value])
                            ),
                            textContent: el.textContent?.substring(0, 100),
                            boundingBox: {
                                x: rect.x, y: rect.y,
                                width: rect.width, height: rect.height
                            },
                            isVisible: rect.width > 0 && rect.height > 0
                        };
                    });
                }
            """)
        return extract_dom

    # ==================== Source 3: Human Recording ====================

    def collect_from_recording(
        self,
        recording_session: Dict[str, Any]
    ) -> TrainingBatch:
        """
        Collect training data from a human recording session.

        Humans demonstrate the best selectors and patterns.

        Args:
            recording_session: Recording session data

        Returns:
            TrainingBatch with recorded data
        """
        elements = []
        patterns = []
        domain = recording_session.get("domain", "")

        actions = recording_session.get("actions", [])

        for action in actions:
            selectors = action.get("selectors", [])
            if selectors:
                best_selector = selectors[0]  # First is usually best
                elements.append({
                    "action": action.get("action_type"),
                    "element_key": self._generate_element_key(action),
                    "selector": best_selector.get("selector"),
                    "selector_type": best_selector.get("type", "css"),
                    "page": action.get("url", "/"),
                    "all_selectors": selectors,
                    "confidence": 0.95  # Human-verified = high confidence
                })

        # Extract action sequences as patterns
        if len(actions) >= 2:
            sequence = [
                {
                    "action": a.get("action_type"),
                    "element_key": self._generate_element_key(a)
                }
                for a in actions
            ]
            patterns.append({
                "type": "recorded_sequence",
                "name": recording_session.get("name"),
                "steps": sequence,
                "confidence": 0.95
            })

        batch = self._create_batch(
            source=DataSource.HUMAN_RECORDING,
            domain=domain,
            elements=elements,
            patterns=patterns
        )

        self._process_batch(batch)

        return batch

    def _generate_element_key(self, action: Dict) -> str:
        """Generate element key from action data"""
        element = action.get("element", {}) or action.get("element_snapshot", {})
        attrs = element.get("attributes", {})

        # Priority: aria-label > name > id > text
        key = (
            attrs.get("aria-label") or
            attrs.get("name") or
            attrs.get("id") or
            element.get("text_content", "")[:30]
        )

        if key:
            import re
            key = re.sub(r'[^a-z0-9]+', '_', key.lower()).strip('_')
            return key

        return f"{element.get('tag_name', 'element')}_{action.get('action_type', 'unknown')}"

    # ==================== Source 4: External Import ====================

    def collect_from_import(
        self,
        import_data: Dict[str, Any],
        source_name: str = "external"
    ) -> TrainingBatch:
        """
        Import training data from external sources.

        Formats supported:
        - GhostQA export format
        - Selenium IDE recordings
        - Playwright codegen output
        - Custom JSON format

        Args:
            import_data: Imported data
            source_name: Name of the source

        Returns:
            TrainingBatch with imported data
        """
        elements = []
        patterns = []
        domain = import_data.get("domain", "unknown")

        # Handle different formats
        if "selectors" in import_data:
            # GhostQA format
            for page, page_data in import_data.get("selectors", {}).items():
                for elem_key, elem_data in page_data.items():
                    for sel in elem_data.get("selectors", []):
                        elements.append({
                            "element_key": elem_key,
                            "selector": sel.get("value") or sel.get("selector"),
                            "selector_type": sel.get("selector_type") or sel.get("type", "css"),
                            "page": page,
                            "confidence": sel.get("confidence", 0.7)
                        })

        if "patterns" in import_data:
            for pattern in import_data.get("patterns", []):
                patterns.append(pattern)

        # Handle Selenium IDE format
        if "tests" in import_data and "commands" in str(import_data):
            for test in import_data.get("tests", []):
                for cmd in test.get("commands", []):
                    if cmd.get("target"):
                        elements.append({
                            "action": cmd.get("command"),
                            "selector": cmd.get("target"),
                            "selector_type": "css",  # Selenium uses CSS by default
                            "value": cmd.get("value"),
                            "confidence": 0.6
                        })

        batch = self._create_batch(
            source=DataSource.EXTERNAL_IMPORT,
            domain=domain,
            elements=elements,
            patterns=patterns,
            metadata={"source_name": source_name}
        )

        self._process_batch(batch)

        return batch

    # ==================== Source 5: Synthetic Generation ====================

    def collect_from_synthetic(
        self,
        base_patterns: List[Dict[str, Any]],
        domain: str
    ) -> TrainingBatch:
        """
        Generate synthetic training data from known patterns.

        Creates variations of known selectors to improve robustness.

        Args:
            base_patterns: Known patterns to expand
            domain: Target domain

        Returns:
            TrainingBatch with synthetic data
        """
        elements = []
        patterns = []

        for pattern in base_patterns:
            selector = pattern.get("selector", "")
            selector_type = pattern.get("selector_type", "css")

            # Generate variations
            variations = self._generate_selector_variations(selector, selector_type)

            for var in variations:
                elements.append({
                    "element_key": pattern.get("element_key"),
                    "selector": var["selector"],
                    "selector_type": var["type"],
                    "page": pattern.get("page", "/"),
                    "confidence": var["confidence"],
                    "synthetic": True,
                    "derived_from": selector
                })

        batch = self._create_batch(
            source=DataSource.SYNTHETIC,
            domain=domain,
            elements=elements,
            patterns=patterns
        )

        # Don't auto-process synthetic - needs verification
        self._save_batch(batch)

        return batch

    def _generate_selector_variations(
        self,
        selector: str,
        selector_type: str
    ) -> List[Dict[str, Any]]:
        """Generate variations of a selector"""
        variations = []

        if selector_type == "css":
            # If ID-based, also create attribute selector
            if selector.startswith("#"):
                elem_id = selector[1:]
                variations.append({
                    "selector": f'[id="{elem_id}"]',
                    "type": "css",
                    "confidence": 0.8
                })

            # If class-based, create more specific versions
            if "." in selector and not selector.startswith("["):
                parts = selector.split(".")
                if len(parts) >= 2:
                    variations.append({
                        "selector": f'[class*="{parts[-1]}"]',
                        "type": "css",
                        "confidence": 0.6
                    })

            # Create data-testid variation if possible
            if "[data-testid" not in selector:
                import re
                # Extract meaningful name from selector
                name_match = re.search(r'[#.]?([a-z_-]+)', selector, re.I)
                if name_match:
                    variations.append({
                        "selector": f'[data-testid*="{name_match.group(1)}"]',
                        "type": "css",
                        "confidence": 0.5
                    })

        return variations

    # ==================== Source 6: Historical Reports ====================

    def collect_from_historical_reports(
        self,
        reports_dir: str = "reports"
    ) -> TrainingBatch:
        """
        Collect training data from historical test reports.

        This mines existing test results for selectors that worked.

        Args:
            reports_dir: Directory containing test reports

        Returns:
            TrainingBatch with historical data
        """
        elements = []
        patterns = []

        reports_path = Path(reports_dir)
        if not reports_path.exists():
            logger.warning(f"Reports directory not found: {reports_dir}")
            return self._create_batch(
                source=DataSource.HISTORICAL,
                domain="unknown",
                elements=[],
                patterns=[]
            )

        # Find all report JSON files
        for report_file in reports_path.rglob("*.json"):
            try:
                with open(report_file, 'r') as f:
                    report = json.load(f)

                # Extract domain from URL if available
                domain = "unknown"
                if "base_url" in report:
                    from urllib.parse import urlparse
                    domain = urlparse(report["base_url"]).netloc

                # Extract successful selectors
                for result in report.get("results", []):
                    if result.get("status") != "passed":
                        continue

                    for step in result.get("steps", []):
                        if step.get("status") == "passed" and step.get("selector"):
                            elements.append({
                                "action": step.get("action"),
                                "selector": step.get("selector"),
                                "selector_type": step.get("selector_type", "css"),
                                "test_name": result.get("test_case_name"),
                                "confidence": 0.85,  # Historical success = good confidence
                                "source_report": report_file.name
                            })

            except Exception as e:
                logger.warning(f"Failed to parse report {report_file}: {e}")

        batch = self._create_batch(
            source=DataSource.HISTORICAL,
            domain="mixed",  # Multiple domains possible
            elements=elements,
            patterns=patterns
        )

        self._process_batch(batch)

        return batch

    # ==================== Batch Management ====================

    def _create_batch(
        self,
        source: DataSource,
        domain: str,
        elements: List[Dict],
        patterns: List[Dict],
        metadata: Optional[Dict] = None
    ) -> TrainingBatch:
        """Create a training batch"""
        batch_id = f"batch_{source.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        data = {
            "elements": elements,
            "patterns": patterns,
            "metadata": metadata or {}
        }

        batch = TrainingBatch(
            id=batch_id,
            source=source,
            domain=domain,
            collected_at=datetime.utcnow().isoformat(),
            elements_count=len(elements),
            patterns_count=len(patterns),
            data=[data]
        )

        # Update stats
        stats = self._collection_stats.get(source.value, {"batches": 0, "elements": 0, "patterns": 0})
        stats["batches"] += 1
        stats["elements"] += len(elements)
        stats["patterns"] += len(patterns)
        self._collection_stats[source.value] = stats
        self._save_stats()

        return batch

    def _save_batch(self, batch: TrainingBatch):
        """Save a batch to disk"""
        batch_file = self.training_dir / f"{batch.id}.json"
        with open(batch_file, 'w') as f:
            json.dump({
                "id": batch.id,
                "source": batch.source.value,
                "domain": batch.domain,
                "collected_at": batch.collected_at,
                "elements_count": batch.elements_count,
                "patterns_count": batch.patterns_count,
                "data": batch.data
            }, f, indent=2)

    def _process_batch(self, batch: TrainingBatch):
        """Process a batch into the knowledge base"""
        # Save batch first
        self._save_batch(batch)

        # Process elements
        for data in batch.data:
            for element in data.get("elements", []):
                if self.learning_engine:
                    self.learning_engine.record_element_mapping(
                        domain=batch.domain,
                        page=element.get("page", "/"),
                        element_key=element.get("element_key", element.get("action", "unknown")),
                        selectors=[{
                            "selector": element.get("selector"),
                            "type": element.get("selector_type", "css"),
                            "confidence": element.get("confidence", 0.7)
                        }],
                        element_attributes={},
                        ai_assisted=False
                    )

            # Process patterns
            for pattern in data.get("patterns", []):
                if self.pattern_store and pattern.get("steps"):
                    self.pattern_store.add_pattern({
                        "id": f"collected_{batch.id}_{len(data.get('patterns', []))}",
                        "name": pattern.get("name", "Collected Pattern"),
                        "category": pattern.get("type", "general"),
                        "steps": pattern.get("steps"),
                        "confidence": pattern.get("confidence", 0.7)
                    })

        # Flush learnings
        if self.learning_engine:
            self.learning_engine.flush()

        logger.info(f"Processed batch {batch.id}: {batch.elements_count} elements, {batch.patterns_count} patterns")

    # ==================== Statistics & Reporting ====================

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        total_elements = sum(s["elements"] for s in self._collection_stats.values())
        total_patterns = sum(s["patterns"] for s in self._collection_stats.values())
        total_batches = sum(s["batches"] for s in self._collection_stats.values())

        return {
            "total_elements": total_elements,
            "total_patterns": total_patterns,
            "total_batches": total_batches,
            "by_source": self._collection_stats,
            "knowledge_base_stats": self.knowledge_index.get_stats() if self.knowledge_index else {}
        }

    def get_collection_recommendations(self) -> List[str]:
        """Get recommendations for improving training data"""
        recommendations = []
        stats = self.get_collection_stats()

        # Check overall data
        if stats["total_elements"] < 100:
            recommendations.append(
                "Run application exploration on your main apps to quickly build initial knowledge"
            )

        # Check by source
        by_source = stats["by_source"]

        if by_source.get(DataSource.TEST_EXECUTION.value, {}).get("elements", 0) < 50:
            recommendations.append(
                "Execute more tests - every test run teaches the system new selectors"
            )

        if by_source.get(DataSource.HUMAN_RECORDING.value, {}).get("elements", 0) == 0:
            recommendations.append(
                "Record some human test sessions - humans find the best selectors"
            )

        if by_source.get(DataSource.HISTORICAL.value, {}).get("elements", 0) == 0:
            recommendations.append(
                "Import historical test reports to learn from past successes"
            )

        if by_source.get(DataSource.APP_EXPLORATION.value, {}).get("elements", 0) == 0:
            recommendations.append(
                "Run the app explorer on your applications to discover elements automatically"
            )

        return recommendations
