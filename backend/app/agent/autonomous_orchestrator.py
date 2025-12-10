"""
Autonomous Test Orchestrator
============================
This is the brain of the autonomous testing agent. It continuously:
1. Discovers feature files and test cases
2. Queues tests for execution
3. Executes tests using the unified executor
4. Learns from results
5. Self-manages execution cycles (NEVER idles)

Author: GhostQA Autonomous Agent System
"""

import asyncio
import threading
import time
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutonomousOrchestrator")


class ExecutionPriority(Enum):
    """Priority levels for test execution"""
    CRITICAL = 1      # Smoke tests, blocking issues
    HIGH = 2          # Core functionality
    NORMAL = 3        # Regular tests
    LOW = 4           # Edge cases, exploratory
    BACKGROUND = 5    # Continuous regression


class ExecutionStatus(Enum):
    """Status of a queued test"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


@dataclass
class QueuedTest:
    """A test queued for autonomous execution"""
    id: str
    project_id: str
    project_name: str
    base_url: str
    test_type: str  # "gherkin" or "traditional"
    feature_id: Optional[str] = None
    feature_name: Optional[str] = None
    scenario_names: List[str] = field(default_factory=list)
    test_case_ids: List[str] = field(default_factory=list)
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    status: ExecutionStatus = ExecutionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 2
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    credentials: Dict[str, str] = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    """Configuration for the autonomous orchestrator"""
    enabled: bool = True
    max_concurrent_executions: int = 1
    poll_interval_seconds: int = 30
    discovery_interval_seconds: int = 300  # 5 minutes
    min_time_between_runs_seconds: int = 60
    auto_discover_new_features: bool = True
    auto_run_on_feature_change: bool = True
    continuous_regression_enabled: bool = True
    regression_interval_hours: int = 24
    max_queue_size: int = 1000
    headless_mode: bool = True
    execution_mode: str = "autonomous"  # autonomous, guided, strict


class AutonomousOrchestrator:
    """
    The Autonomous Test Orchestrator - Never Idles

    This class is the core of the autonomous testing agent. It runs as a
    background service and continuously manages test execution without
    requiring human intervention.

    Key behaviors:
    1. ALWAYS RUNNING - Never enters idle state
    2. SELF-DISCOVERING - Finds new tests automatically
    3. SELF-SCHEDULING - Queues and prioritizes work
    4. SELF-HEALING - Retries failures, learns from errors
    5. SELF-LEARNING - Improves over time via knowledge base
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - only one orchestrator per process"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.config = OrchestratorConfig()

        # Execution state
        self._running = False
        self._paused = False
        self._execution_thread: Optional[threading.Thread] = None
        self._discovery_thread: Optional[threading.Thread] = None

        # Work queue (priority queue using deque for each priority)
        self._queues: Dict[ExecutionPriority, deque] = {
            priority: deque() for priority in ExecutionPriority
        }
        self._queue_lock = threading.Lock()

        # Tracking state
        self._current_execution: Optional[QueuedTest] = None
        self._executed_tests: Dict[str, QueuedTest] = {}  # id -> result
        self._known_features: Set[str] = set()  # track discovered features
        self._last_discovery_time: Optional[datetime] = None
        self._last_regression_time: Optional[datetime] = None

        # Statistics
        self._stats = {
            "total_queued": 0,
            "total_executed": 0,
            "total_passed": 0,
            "total_failed": 0,
            "total_retried": 0,
            "uptime_seconds": 0,
            "started_at": None,
        }

        # Import dependencies lazily to avoid circular imports
        self._executor = None
        self._storage = None
        self._learning_engine = None

        logger.info("AutonomousOrchestrator initialized")

    def _get_executor(self):
        """Lazy load the unified executor"""
        if self._executor is None:
            from agent.unified_executor import UnifiedTestExecutor
            self._executor = UnifiedTestExecutor()
        return self._executor

    def _get_storage(self):
        """Lazy load storage"""
        if self._storage is None:
            from storage import Storage
            self._storage = Storage()
        return self._storage

    def _get_learning_engine(self):
        """Lazy load learning engine"""
        if self._learning_engine is None:
            from agent.knowledge.learning_engine import LearningEngine
            self._learning_engine = LearningEngine()
        return self._learning_engine

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    def start(self):
        """Start the autonomous orchestrator - begins continuous execution"""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        logger.info("=" * 60)
        logger.info("AUTONOMOUS ORCHESTRATOR STARTING")
        logger.info("=" * 60)

        self._running = True
        self._paused = False
        self._stats["started_at"] = datetime.now()

        # Start the main execution loop in a background thread
        self._execution_thread = threading.Thread(
            target=self._execution_loop,
            name="AutonomousExecutionLoop",
            daemon=True
        )
        self._execution_thread.start()

        # Start the discovery loop in a background thread
        self._discovery_thread = threading.Thread(
            target=self._discovery_loop,
            name="AutonomousDiscoveryLoop",
            daemon=True
        )
        self._discovery_thread.start()

        logger.info("Orchestrator started - entering autonomous mode")

    def stop(self):
        """Stop the autonomous orchestrator gracefully"""
        logger.info("Stopping autonomous orchestrator...")
        self._running = False

        # Wait for threads to finish
        if self._execution_thread and self._execution_thread.is_alive():
            self._execution_thread.join(timeout=30)
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=10)

        logger.info("Orchestrator stopped")

    def pause(self):
        """Pause execution (but keep monitoring)"""
        self._paused = True
        logger.info("Orchestrator paused")

    def resume(self):
        """Resume execution after pause"""
        self._paused = False
        logger.info("Orchestrator resumed")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    # =========================================================================
    # MAIN EXECUTION LOOP - NEVER IDLES
    # =========================================================================

    def _execution_loop(self):
        """
        Main execution loop - THE HEART OF AUTONOMOUS OPERATION

        This loop runs continuously and:
        1. Checks for queued tests
        2. Executes highest priority test
        3. Processes results and learns
        4. Immediately looks for more work
        5. If no work, triggers discovery or schedules regression

        CRITICAL: This loop NEVER terminates while running=True
        """
        logger.info("Execution loop started - entering continuous mode")

        while self._running:
            try:
                # Update uptime stats
                if self._stats["started_at"]:
                    self._stats["uptime_seconds"] = (
                        datetime.now() - self._stats["started_at"]
                    ).total_seconds()

                # If paused, just sleep and continue
                if self._paused:
                    time.sleep(1)
                    continue

                # Get next test from queue
                next_test = self._get_next_test()

                if next_test:
                    # Execute the test
                    logger.info(f"Executing: {next_test.feature_name or next_test.id}")
                    self._execute_test(next_test)
                else:
                    # No tests in queue - but DON'T IDLE!
                    # Instead, check if we should:
                    # 1. Run scheduled regression tests
                    # 2. Re-discover features
                    # 3. Re-run failed tests

                    self._handle_idle_state()

                # Small sleep to prevent CPU spinning
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                time.sleep(5)  # Brief pause on error, then continue

        logger.info("Execution loop terminated")

    def _handle_idle_state(self):
        """
        Handle when queue is empty - NEVER truly idle

        Instead of idling, the agent:
        1. Checks for scheduled regression tests
        2. Re-runs failed tests that may now pass
        3. Triggers feature discovery
        4. Waits briefly then checks again
        """
        now = datetime.now()

        # Check if regression tests are due
        if self.config.continuous_regression_enabled:
            if (self._last_regression_time is None or
                (now - self._last_regression_time).total_seconds() >
                self.config.regression_interval_hours * 3600):

                logger.info("Scheduling regression tests...")
                self._schedule_regression_tests()
                self._last_regression_time = now
                return

        # Check for failed tests that can be retried
        retry_candidates = [
            test for test in self._executed_tests.values()
            if test.status == ExecutionStatus.FAILED
            and test.retry_count < test.max_retries
            and test.completed_at
            and (now - test.completed_at).total_seconds() > 300  # 5 min cooldown
        ]

        if retry_candidates:
            logger.info(f"Retrying {len(retry_candidates)} failed tests...")
            for test in retry_candidates:
                test.status = ExecutionStatus.RETRYING
                test.retry_count += 1
                self._stats["total_retried"] += 1
                self._enqueue_test(test)
            return

        # If nothing else, just wait for new work
        logger.debug("Queue empty, waiting for new tests...")
        time.sleep(self.config.poll_interval_seconds)

    # =========================================================================
    # DISCOVERY LOOP - AUTO-DISCOVERS NEW TESTS
    # =========================================================================

    def _discovery_loop(self):
        """
        Discovery loop - continuously finds new features and tests

        Runs in parallel with execution loop to ensure we always
        know about new tests that need to run.
        """
        logger.info("Discovery loop started")

        while self._running:
            try:
                if not self._paused and self.config.auto_discover_new_features:
                    self._discover_and_queue_tests()
                    self._last_discovery_time = datetime.now()

                # Wait before next discovery cycle
                time.sleep(self.config.discovery_interval_seconds)

            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                time.sleep(30)

        logger.info("Discovery loop terminated")

    def _discover_and_queue_tests(self):
        """
        Discover all projects, features, and tests - queue new ones

        This method scans the storage for:
        1. All projects with features
        2. Features that haven't been run recently
        3. New features that were just added
        """
        logger.info("Discovering tests...")

        try:
            storage = self._get_storage()
            projects = storage.get_projects()

            for project in projects:
                project_id = project.id
                project_data = storage.get_project(project_id)

                if not project_data:
                    continue

                # Get project credentials
                credentials = {
                    "username": getattr(project_data, 'test_username', '') or
                               getattr(project_data, 'test_admin_username', ''),
                    "password": getattr(project_data, 'test_password', '') or
                               getattr(project_data, 'test_admin_password', ''),
                }

                # Discover Gherkin features
                self._discover_gherkin_features(project_data, credentials)

                # Discover Traditional test cases
                self._discover_traditional_tests(project_data, credentials)

            logger.info(f"Discovery complete. Queue size: {self.get_queue_size()}")

        except Exception as e:
            logger.error(f"Discovery error: {e}")

    def _discover_gherkin_features(self, project, credentials: Dict[str, str]):
        """Discover and queue Gherkin features for a project"""
        try:
            # Get Gherkin features for project
            storage = self._get_storage()
            features = storage.get_gherkin_features(project.id)

            if not features:
                return

            for feature in features:
                feature_id = feature.get('id') or feature.get('feature_id')

                if not feature_id:
                    continue

                # Check if this is a new or updated feature
                feature_key = f"{project.id}:{feature_id}"

                if feature_key not in self._known_features:
                    self._known_features.add(feature_key)

                    # Queue this feature for execution
                    queued_test = QueuedTest(
                        id=f"auto_{feature_id}_{int(time.time())}",
                        project_id=project.id,
                        project_name=project.name,
                        base_url=project.base_url or "",
                        test_type="gherkin",
                        feature_id=feature_id,
                        feature_name=feature.get('name', 'Unknown Feature'),
                        scenario_names=[],  # Run all scenarios
                        priority=ExecutionPriority.NORMAL,
                        credentials=credentials,
                    )

                    self._enqueue_test(queued_test)
                    logger.info(f"Queued new feature: {queued_test.feature_name}")

        except Exception as e:
            logger.error(f"Error discovering Gherkin features: {e}")

    def _discover_traditional_tests(self, project, credentials: Dict[str, str]):
        """Discover and queue Traditional test cases for a project"""
        try:
            test_cases = getattr(project, 'test_cases', []) or []

            if not test_cases:
                return

            # Check if we have new test cases
            project_key = f"traditional:{project.id}"
            current_test_ids = {tc.id for tc in test_cases if hasattr(tc, 'id')}

            if project_key not in self._known_features:
                self._known_features.add(project_key)

                # Queue all test cases for this project
                if current_test_ids:
                    queued_test = QueuedTest(
                        id=f"auto_trad_{project.id}_{int(time.time())}",
                        project_id=project.id,
                        project_name=project.name,
                        base_url=project.base_url or "",
                        test_type="traditional",
                        test_case_ids=list(current_test_ids),
                        priority=ExecutionPriority.NORMAL,
                        credentials=credentials,
                    )

                    self._enqueue_test(queued_test)
                    logger.info(f"Queued {len(current_test_ids)} traditional tests for {project.name}")

        except Exception as e:
            logger.error(f"Error discovering traditional tests: {e}")

    def _schedule_regression_tests(self):
        """Schedule regression tests for all known features"""
        logger.info("Scheduling regression tests for all features...")

        try:
            storage = self._get_storage()
            projects = storage.get_projects()

            for project in projects:
                project_data = storage.get_project(project.id)
                if not project_data:
                    continue

                credentials = {
                    "username": getattr(project_data, 'test_username', '') or
                               getattr(project_data, 'test_admin_username', ''),
                    "password": getattr(project_data, 'test_password', '') or
                               getattr(project_data, 'test_admin_password', ''),
                }

                # Queue Gherkin features for regression
                features = storage.get_gherkin_features(project.id)
                for feature in (features or []):
                    feature_id = feature.get('id')
                    if feature_id:
                        queued_test = QueuedTest(
                            id=f"regression_{feature_id}_{int(time.time())}",
                            project_id=project.id,
                            project_name=project.name,
                            base_url=project.base_url or "",
                            test_type="gherkin",
                            feature_id=feature_id,
                            feature_name=feature.get('name', 'Unknown'),
                            priority=ExecutionPriority.BACKGROUND,
                            credentials=credentials,
                        )
                        self._enqueue_test(queued_test)

                # Queue traditional tests for regression
                test_cases = getattr(project_data, 'test_cases', []) or []
                if test_cases:
                    queued_test = QueuedTest(
                        id=f"regression_trad_{project.id}_{int(time.time())}",
                        project_id=project.id,
                        project_name=project.name,
                        base_url=project.base_url or "",
                        test_type="traditional",
                        test_case_ids=[tc.id for tc in test_cases if hasattr(tc, 'id')],
                        priority=ExecutionPriority.BACKGROUND,
                        credentials=credentials,
                    )
                    self._enqueue_test(queued_test)

            logger.info(f"Regression tests scheduled. Queue size: {self.get_queue_size()}")

        except Exception as e:
            logger.error(f"Error scheduling regression tests: {e}")

    # =========================================================================
    # QUEUE MANAGEMENT
    # =========================================================================

    def _enqueue_test(self, test: QueuedTest):
        """Add a test to the execution queue"""
        with self._queue_lock:
            # Check queue size limit
            total_queued = sum(len(q) for q in self._queues.values())
            if total_queued >= self.config.max_queue_size:
                logger.warning("Queue full, dropping lowest priority tests")
                # Remove from lowest priority queue
                for priority in reversed(list(ExecutionPriority)):
                    if self._queues[priority]:
                        self._queues[priority].pop()
                        break

            self._queues[test.priority].append(test)
            self._stats["total_queued"] += 1

        logger.debug(f"Enqueued test: {test.id} (priority: {test.priority.name})")

    def _get_next_test(self) -> Optional[QueuedTest]:
        """Get the next test to execute (highest priority first)"""
        with self._queue_lock:
            for priority in ExecutionPriority:
                if self._queues[priority]:
                    test = self._queues[priority].popleft()
                    test.status = ExecutionStatus.RUNNING
                    test.started_at = datetime.now()
                    self._current_execution = test
                    return test
        return None

    def get_queue_size(self) -> int:
        """Get total number of tests in queue"""
        with self._queue_lock:
            return sum(len(q) for q in self._queues.values())

    def get_queue_status(self) -> Dict[str, Any]:
        """Get detailed queue status"""
        with self._queue_lock:
            return {
                "total": sum(len(q) for q in self._queues.values()),
                "by_priority": {
                    priority.name: len(queue)
                    for priority, queue in self._queues.items()
                },
                "current_execution": self._current_execution.id if self._current_execution else None,
            }

    # =========================================================================
    # TEST EXECUTION
    # =========================================================================

    def _execute_test(self, test: QueuedTest):
        """Execute a single queued test"""
        logger.info(f"[EXECUTE] Starting: {test.feature_name or test.id}")
        logger.info(f"  Project: {test.project_name}")
        logger.info(f"  Type: {test.test_type}")
        logger.info(f"  Priority: {test.priority.name}")

        try:
            executor = self._get_executor()
            storage = self._get_storage()

            if test.test_type == "gherkin":
                result = self._execute_gherkin_test(test, executor, storage)
            else:
                result = self._execute_traditional_test(test, executor, storage)

            # Update test status
            test.completed_at = datetime.now()
            test.result = result

            if result.get("success") or result.get("passed", 0) > 0:
                test.status = ExecutionStatus.COMPLETED
                self._stats["total_passed"] += result.get("passed", 1)
                logger.info(f"[PASS] {test.feature_name or test.id}")
            else:
                test.status = ExecutionStatus.FAILED
                test.error_message = result.get("error") or "Unknown error"
                self._stats["total_failed"] += result.get("failed", 1)
                logger.warning(f"[FAIL] {test.feature_name or test.id}: {test.error_message}")

            self._stats["total_executed"] += 1

        except Exception as e:
            test.status = ExecutionStatus.FAILED
            test.error_message = str(e)
            test.completed_at = datetime.now()
            self._stats["total_failed"] += 1
            logger.error(f"[ERROR] {test.id}: {e}")

        finally:
            # Store result and clear current execution
            self._executed_tests[test.id] = test
            self._current_execution = None

            # Trigger learning from this execution
            self._learn_from_execution(test)

    def _execute_gherkin_test(self, test: QueuedTest, executor, storage) -> Dict[str, Any]:
        """Execute a Gherkin feature test"""
        # Get full feature data
        feature_data = storage.get_gherkin_feature(test.feature_id)

        if not feature_data:
            return {"success": False, "error": "Feature not found"}

        # Build execution request
        from agent.unified_executor import UnifiedTestCase, TestFormat

        # Convert feature scenarios to unified format
        unified_cases = []
        scenarios = feature_data.get('scenarios', [])

        for scenario in scenarios:
            # Skip if we have a filter and this scenario isn't in it
            if test.scenario_names and scenario.get('name') not in test.scenario_names:
                continue

            steps = []
            for step in scenario.get('steps', []):
                steps.append({
                    "keyword": step.get('keyword', {}).get('value', 'Given') if isinstance(step.get('keyword'), dict) else step.get('keyword', 'Given'),
                    "text": step.get('text', ''),
                })

            unified_case = UnifiedTestCase(
                id=f"{test.feature_id}_{scenario.get('name', 'unnamed')}",
                name=scenario.get('name', 'Unnamed Scenario'),
                description=scenario.get('description', ''),
                format=TestFormat.GHERKIN,
                steps=steps,
                tags=scenario.get('tags', []),
                feature_name=feature_data.get('name'),
                scenario_name=scenario.get('name'),
            )
            unified_cases.append(unified_case)

        if not unified_cases:
            return {"success": False, "error": "No scenarios to execute"}

        # Execute using unified executor
        import asyncio

        async def run_tests():
            return await executor.execute_tests(
                test_cases=unified_cases,
                project_name=test.project_name,
                base_url=test.base_url,
                headless=self.config.headless_mode,
                execution_mode=self.config.execution_mode,
                credentials=test.credentials,
            )

        # Run in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(run_tests())
        return result

    def _execute_traditional_test(self, test: QueuedTest, executor, storage) -> Dict[str, Any]:
        """Execute traditional test cases"""
        # Get project and test cases
        project = storage.get_project(test.project_id)

        if not project:
            return {"success": False, "error": "Project not found"}

        test_cases = getattr(project, 'test_cases', []) or []

        # Filter test cases if specific IDs provided
        if test.test_case_ids:
            test_cases = [tc for tc in test_cases if tc.id in test.test_case_ids]

        if not test_cases:
            return {"success": False, "error": "No test cases to execute"}

        # Build execution request
        from agent.unified_executor import UnifiedTestCase, TestFormat

        unified_cases = []
        for tc in test_cases:
            steps = []
            for action in getattr(tc, 'actions', []) or []:
                steps.append({
                    "action": getattr(action, 'action', 'click'),
                    "selector": getattr(action, 'selector', ''),
                    "value": getattr(action, 'value', ''),
                    "url": getattr(action, 'url', ''),
                    "description": getattr(action, 'description', ''),
                })

            unified_case = UnifiedTestCase(
                id=tc.id,
                name=tc.name,
                description=getattr(tc, 'description', ''),
                format=TestFormat.TRADITIONAL,
                steps=steps,
            )
            unified_cases.append(unified_case)

        # Execute using unified executor
        import asyncio

        async def run_tests():
            return await executor.execute_tests(
                test_cases=unified_cases,
                project_name=test.project_name,
                base_url=test.base_url,
                headless=self.config.headless_mode,
                execution_mode=self.config.execution_mode,
                credentials=test.credentials,
            )

        # Run in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(run_tests())
        return result

    def _learn_from_execution(self, test: QueuedTest):
        """Feed execution results to the learning engine"""
        try:
            if not test.result:
                return

            learning_engine = self._get_learning_engine()

            # Learn from the execution results
            # This improves selector confidence, discovers patterns, etc.
            if hasattr(learning_engine, 'learn_from_execution'):
                learning_engine.learn_from_execution(
                    test_id=test.id,
                    success=test.status == ExecutionStatus.COMPLETED,
                    result=test.result,
                )

        except Exception as e:
            logger.error(f"Learning error: {e}")

    # =========================================================================
    # EXTERNAL API - For manual queue additions and status checks
    # =========================================================================

    def queue_feature(
        self,
        project_id: str,
        feature_id: str,
        priority: ExecutionPriority = ExecutionPriority.HIGH
    ) -> str:
        """Manually queue a specific feature for execution"""
        storage = self._get_storage()
        project = storage.get_project(project_id)
        feature = storage.get_gherkin_feature(feature_id)

        if not project or not feature:
            raise ValueError("Project or feature not found")

        credentials = {
            "username": getattr(project, 'test_username', '') or
                       getattr(project, 'test_admin_username', ''),
            "password": getattr(project, 'test_password', '') or
                       getattr(project, 'test_admin_password', ''),
        }

        queued_test = QueuedTest(
            id=f"manual_{feature_id}_{int(time.time())}",
            project_id=project_id,
            project_name=project.name,
            base_url=project.base_url or "",
            test_type="gherkin",
            feature_id=feature_id,
            feature_name=feature.get('name', 'Unknown'),
            priority=priority,
            credentials=credentials,
        )

        self._enqueue_test(queued_test)
        return queued_test.id

    def queue_project_tests(
        self,
        project_id: str,
        priority: ExecutionPriority = ExecutionPriority.NORMAL
    ) -> List[str]:
        """Queue all tests for a project"""
        storage = self._get_storage()
        project = storage.get_project(project_id)

        if not project:
            raise ValueError("Project not found")

        queued_ids = []

        credentials = {
            "username": getattr(project, 'test_username', '') or
                       getattr(project, 'test_admin_username', ''),
            "password": getattr(project, 'test_password', '') or
                       getattr(project, 'test_admin_password', ''),
        }

        # Queue Gherkin features
        features = storage.get_gherkin_features(project_id)
        for feature in (features or []):
            feature_id = feature.get('id')
            if feature_id:
                test_id = self.queue_feature(project_id, feature_id, priority)
                queued_ids.append(test_id)

        # Queue traditional tests
        test_cases = getattr(project, 'test_cases', []) or []
        if test_cases:
            queued_test = QueuedTest(
                id=f"manual_trad_{project_id}_{int(time.time())}",
                project_id=project_id,
                project_name=project.name,
                base_url=project.base_url or "",
                test_type="traditional",
                test_case_ids=[tc.id for tc in test_cases if hasattr(tc, 'id')],
                priority=priority,
                credentials=credentials,
            )
            self._enqueue_test(queued_test)
            queued_ids.append(queued_test.id)

        return queued_ids

    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            **self._stats,
            "is_running": self._running,
            "is_paused": self._paused,
            "queue_size": self.get_queue_size(),
            "current_execution": self._current_execution.id if self._current_execution else None,
            "known_features": len(self._known_features),
            "executed_tests": len(self._executed_tests),
        }

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        executions = sorted(
            self._executed_tests.values(),
            key=lambda x: x.completed_at or datetime.min,
            reverse=True
        )[:limit]

        return [
            {
                "id": e.id,
                "feature_name": e.feature_name,
                "project_name": e.project_name,
                "status": e.status.value,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "error_message": e.error_message,
                "retry_count": e.retry_count,
            }
            for e in executions
        ]


# =========================================================================
# GLOBAL ORCHESTRATOR INSTANCE
# =========================================================================

_orchestrator: Optional[AutonomousOrchestrator] = None


def get_orchestrator() -> AutonomousOrchestrator:
    """Get the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AutonomousOrchestrator()
    return _orchestrator


def start_autonomous_mode():
    """Start the autonomous orchestrator"""
    orchestrator = get_orchestrator()
    orchestrator.start()
    return orchestrator


def stop_autonomous_mode():
    """Stop the autonomous orchestrator"""
    global _orchestrator
    if _orchestrator:
        _orchestrator.stop()
