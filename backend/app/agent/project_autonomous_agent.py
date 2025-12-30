"""
Project Autonomous Agent
========================
An intelligent agent that takes complete ownership of testing a project.

When triggered (user clicks "Run"), this agent:
1. DISCOVERS - Finds all features and test cases for the project
2. PLANS - Creates an intelligent execution strategy
3. EXECUTES - Runs tests autonomously, handling failures
4. LEARNS - Updates knowledge base from results
5. REPORTS - Provides comprehensive results

This is designed to be "another Claude" - you trigger it and it handles everything.

Author: GhostQA Autonomous Agent System
"""

import asyncio
import json
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import uuid

logger = logging.getLogger("ProjectAutonomousAgent")


class AgentPhase(Enum):
    """Current phase of the autonomous agent"""
    INITIALIZING = "initializing"
    DISCOVERING = "discovering"
    PLANNING = "planning"
    EXECUTING = "executing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class TestPriority(Enum):
    """Test priority levels for intelligent ordering"""
    SMOKE = 1        # Run first - quick validation
    CRITICAL = 2     # Core functionality
    HIGH = 3         # Important features
    NORMAL = 4       # Regular tests
    LOW = 5          # Edge cases, optional
    EXPLORATORY = 6  # AI-discovered tests


@dataclass
class DiscoveredTest:
    """A test discovered by the agent"""
    id: str
    name: str
    type: str  # "gherkin" or "traditional"
    feature_id: Optional[str] = None
    feature_name: Optional[str] = None
    scenario_name: Optional[str] = None
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    priority: TestPriority = TestPriority.NORMAL
    estimated_duration_seconds: float = 30.0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TestExecutionResult:
    """Result of executing a single test"""
    test_id: str
    test_name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration_seconds: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    steps_completed: int = 0
    steps_total: int = 0
    retry_count: int = 0


@dataclass
class AgentExecutionState:
    """Current state of the agent's execution"""
    session_id: str
    project_id: str
    project_name: str
    phase: AgentPhase = AgentPhase.INITIALIZING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Discovery results
    discovered_tests: List[DiscoveredTest] = field(default_factory=list)
    total_features: int = 0
    total_scenarios: int = 0
    total_traditional_tests: int = 0

    # Execution state
    current_test_index: int = 0
    current_test_name: str = ""

    # Results
    results: List[TestExecutionResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0

    # Progress
    progress_percent: float = 0.0
    estimated_remaining_seconds: float = 0.0

    # Messages for UI
    status_message: str = "Initializing..."
    detailed_log: List[str] = field(default_factory=list)

    # Control
    stop_requested: bool = False


class ProjectAutonomousAgent:
    """
    The Autonomous Project Testing Agent

    This agent is designed to think and act like an intelligent tester.
    When you give it a project, it:

    1. Explores the project to understand what needs testing
    2. Creates a smart test plan (smoke tests first, then critical paths, etc.)
    3. Executes tests while adapting to failures
    4. Learns from results to improve future runs
    5. Provides comprehensive feedback

    Usage:
        agent = ProjectAutonomousAgent(project_id, broadcast_callback)
        await agent.run()
    """

    def __init__(
        self,
        project_id: str,
        broadcast_callback: Optional[Callable[[str], Any]] = None,
        headless: bool = True,
        execution_mode: str = "guided",  # Smart mode - brain optimizes AI usage
    ):
        self.project_id = project_id
        self.broadcast = broadcast_callback or self._default_broadcast
        self.headless = headless
        self.execution_mode = execution_mode

        # Session
        self.session_id = str(uuid.uuid4())
        self.state = AgentExecutionState(
            session_id=self.session_id,
            project_id=project_id,
            project_name="",
        )

        # Dependencies (lazy loaded)
        self._storage = None
        self._gherkin_storage = None
        self._executor = None
        self._learning_engine = None

    def _default_broadcast(self, message: str):
        """Default broadcast - just log"""
        logger.info(message)

    async def _broadcast(self, message: str, event_type: str = "log"):
        """Send message to UI via callback"""
        self.state.detailed_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

        # Create structured message for WebSocket
        ws_message = json.dumps({
            "type": event_type,
            "session_id": self.session_id,
            "phase": self.state.phase.value,
            "message": message,
            "progress": self.state.progress_percent,
            "passed": self.state.passed,
            "failed": self.state.failed,
            "current_test": self.state.current_test_name,
            "timestamp": datetime.now().isoformat(),
        })

        if asyncio.iscoroutinefunction(self.broadcast):
            await self.broadcast(ws_message)
        else:
            self.broadcast(ws_message)

    def _get_storage(self):
        if self._storage is None:
            from storage import Storage
            self._storage = Storage()
        return self._storage

    def _get_gherkin_storage(self):
        if self._gherkin_storage is None:
            from gherkin_storage import get_gherkin_storage
            self._gherkin_storage = get_gherkin_storage()
        return self._gherkin_storage

    def _get_executor(self):
        if self._executor is None:
            from agent.unified_executor import UnifiedTestExecutor
            self._executor = UnifiedTestExecutor()
        return self._executor

    def _get_learning_engine(self):
        if self._learning_engine is None:
            try:
                from agent.knowledge.learning_engine import LearningEngine
                self._learning_engine = LearningEngine()
            except Exception:
                self._learning_engine = None
        return self._learning_engine

    # =========================================================================
    # MAIN EXECUTION FLOW
    # =========================================================================

    async def run(self) -> AgentExecutionState:
        """
        Main entry point - runs the complete autonomous testing cycle.

        Returns the final execution state with all results.
        """
        self.state.started_at = datetime.now()

        try:
            # Phase 1: Initialize and load project
            await self._phase_initialize()
            if self.state.stop_requested:
                return await self._handle_stop()

            # Phase 2: Discover all tests
            await self._phase_discover()
            if self.state.stop_requested:
                return await self._handle_stop()

            # Phase 3: Plan execution strategy
            await self._phase_plan()
            if self.state.stop_requested:
                return await self._handle_stop()

            # Phase 4: Execute tests
            await self._phase_execute()
            if self.state.stop_requested:
                return await self._handle_stop()

            # Phase 5: Analyze results
            await self._phase_analyze()

            # Complete
            self.state.phase = AgentPhase.COMPLETED
            self.state.completed_at = datetime.now()

            duration = (self.state.completed_at - self.state.started_at).total_seconds()
            await self._broadcast(
                f"Autonomous execution completed in {duration:.1f}s. "
                f"Passed: {self.state.passed}, Failed: {self.state.failed}",
                "complete"
            )

        except Exception as e:
            self.state.phase = AgentPhase.FAILED
            self.state.status_message = f"Agent failed: {str(e)}"
            await self._broadcast(f"AGENT ERROR: {str(e)}", "error")
            logger.exception("Agent execution failed")

        return self.state

    def stop(self):
        """Request the agent to stop gracefully"""
        self.state.stop_requested = True
        self.state.status_message = "Stop requested, finishing current test..."

    async def _handle_stop(self) -> AgentExecutionState:
        """Handle graceful stop"""
        self.state.phase = AgentPhase.STOPPED
        self.state.completed_at = datetime.now()
        await self._broadcast("Agent stopped by user request", "stopped")
        return self.state

    # =========================================================================
    # PHASE 1: INITIALIZE
    # =========================================================================

    async def _phase_initialize(self):
        """Initialize the agent and load project data"""
        self.state.phase = AgentPhase.INITIALIZING
        await self._broadcast("Initializing autonomous agent...", "phase")

        # Load project
        storage = self._get_storage()
        project = storage.get_project(self.project_id)

        if not project:
            raise ValueError(f"Project {self.project_id} not found")

        self.state.project_name = project.name
        self.project = project

        # Get credentials
        self.credentials = {
            "username": getattr(project, 'test_username', '') or
                       getattr(project, 'test_admin_username', ''),
            "password": getattr(project, 'test_password', '') or
                       getattr(project, 'test_admin_password', ''),
        }

        self.base_url = project.base_url or ""

        await self._broadcast(
            f"Project loaded: {project.name} ({self.base_url})",
            "info"
        )

    # =========================================================================
    # PHASE 2: DISCOVER
    # =========================================================================

    async def _phase_discover(self):
        """Discover all tests in the project"""
        self.state.phase = AgentPhase.DISCOVERING
        self.state.status_message = "Discovering tests..."
        await self._broadcast("Starting test discovery...", "phase")

        discovered = []

        # Discover Gherkin features
        gherkin_tests = await self._discover_gherkin_features()
        discovered.extend(gherkin_tests)

        # Discover Traditional test cases
        traditional_tests = await self._discover_traditional_tests()
        discovered.extend(traditional_tests)

        self.state.discovered_tests = discovered

        await self._broadcast(
            f"Discovery complete: {len(discovered)} tests found "
            f"({self.state.total_features} features, "
            f"{self.state.total_scenarios} scenarios, "
            f"{self.state.total_traditional_tests} traditional tests)",
            "discovery_complete"
        )

    async def _discover_gherkin_features(self) -> List[DiscoveredTest]:
        """Discover all Gherkin features and scenarios"""
        discovered = []

        try:
            gherkin_storage = self._get_gherkin_storage()
            features = gherkin_storage.list_features(project_id=self.project_id) or []

            self.state.total_features = len(features)

            for feature_info in features:
                feature_id = feature_info.get('id')
                if not feature_id:
                    continue

                # Load full feature data
                feature_data = gherkin_storage.load_feature_dict(feature_id)
                if not feature_data:
                    continue

                feature_name = feature_data.get('name', 'Unknown Feature')
                scenarios = feature_data.get('scenarios', [])

                await self._broadcast(
                    f"Found feature: {feature_name} ({len(scenarios)} scenarios)"
                )

                for scenario in scenarios:
                    scenario_name = scenario.get('name', 'Unnamed Scenario')
                    tags = scenario.get('tags', [])
                    steps = scenario.get('steps', [])

                    # Determine priority from tags
                    priority = self._determine_priority_from_tags(tags)

                    # Create discovered test - convert steps to proper format
                    converted_steps = []
                    for s in steps:
                        keyword = (s.get('keyword', {}).get('value', 'Given')
                                   if isinstance(s.get('keyword'), dict)
                                   else s.get('keyword', 'Given'))
                        text = s.get('text', '')
                        converted_steps.append({
                            "action": "gherkin_step",
                            "keyword": keyword,
                            "text": text,
                            "target": text,  # Use text as target for selector matching
                            "value": "",
                            "description": f"{keyword} {text}"
                        })

                    test = DiscoveredTest(
                        id=f"{feature_id}::{scenario_name}",
                        name=scenario_name,
                        type="gherkin",
                        feature_id=feature_id,
                        feature_name=feature_name,
                        scenario_name=scenario_name,
                        steps=converted_steps,
                        tags=tags,
                        priority=priority,
                        estimated_duration_seconds=len(steps) * 5.0,  # ~5s per step
                    )
                    discovered.append(test)
                    self.state.total_scenarios += 1

        except Exception as e:
            await self._broadcast(f"Warning: Error discovering Gherkin features: {e}")
            logger.exception("Gherkin discovery error")

        return discovered

    async def _discover_traditional_tests(self) -> List[DiscoveredTest]:
        """Discover all Traditional test cases"""
        discovered = []

        try:
            test_cases = getattr(self.project, 'test_cases', []) or []
            self.state.total_traditional_tests = len(test_cases)

            for tc in test_cases:
                actions = getattr(tc, 'actions', []) or []
                tags = getattr(tc, 'tags', []) or []

                # Determine priority
                priority = self._determine_priority_from_tags(tags)

                test = DiscoveredTest(
                    id=tc.id,
                    name=tc.name,
                    type="traditional",
                    steps=[{
                        "action": getattr(a, 'action', 'click'),
                        "selector": getattr(a, 'selector', ''),
                        "value": getattr(a, 'value', ''),
                        "url": getattr(a, 'url', ''),
                        "description": getattr(a, 'description', ''),
                    } for a in actions],
                    tags=tags,
                    priority=priority,
                    estimated_duration_seconds=len(actions) * 3.0,  # ~3s per action
                )
                discovered.append(test)

            if test_cases:
                await self._broadcast(
                    f"Found {len(test_cases)} traditional test cases"
                )

        except Exception as e:
            await self._broadcast(f"Warning: Error discovering traditional tests: {e}")
            logger.exception("Traditional test discovery error")

        return discovered

    def _determine_priority_from_tags(self, tags: List[str]) -> TestPriority:
        """Determine test priority based on tags"""
        tags_lower = [t.lower() for t in tags]

        if any('@smoke' in t for t in tags_lower):
            return TestPriority.SMOKE
        if any('@critical' in t or '@blocker' in t for t in tags_lower):
            return TestPriority.CRITICAL
        if any('@high' in t or '@important' in t for t in tags_lower):
            return TestPriority.HIGH
        if any('@low' in t or '@edge' in t for t in tags_lower):
            return TestPriority.LOW
        if any('@exploratory' in t for t in tags_lower):
            return TestPriority.EXPLORATORY

        return TestPriority.NORMAL

    # =========================================================================
    # PHASE 3: PLAN
    # =========================================================================

    async def _phase_plan(self):
        """Create an intelligent execution plan"""
        self.state.phase = AgentPhase.PLANNING
        self.state.status_message = "Planning execution strategy..."
        await self._broadcast("Creating execution plan...", "phase")

        # Sort tests by priority
        self.state.discovered_tests.sort(key=lambda t: t.priority.value)

        # Group by priority for reporting
        priority_counts = {}
        for test in self.state.discovered_tests:
            priority_name = test.priority.name
            priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1

        # Estimate total time
        total_estimated = sum(t.estimated_duration_seconds for t in self.state.discovered_tests)
        self.state.estimated_remaining_seconds = total_estimated

        # Build plan message
        plan_msg = "Execution Plan:\n"
        for priority, count in sorted(priority_counts.items(), key=lambda x: TestPriority[x[0]].value):
            plan_msg += f"  - {priority}: {count} tests\n"
        plan_msg += f"  Estimated time: {total_estimated/60:.1f} minutes"

        await self._broadcast(plan_msg, "plan")

        # Log individual test order (first 10)
        await self._broadcast("Test order (first 10):")
        for i, test in enumerate(self.state.discovered_tests[:10]):
            await self._broadcast(f"  {i+1}. [{test.priority.name}] {test.name}")

        if len(self.state.discovered_tests) > 10:
            await self._broadcast(f"  ... and {len(self.state.discovered_tests) - 10} more")

    # =========================================================================
    # PHASE 4: EXECUTE
    # =========================================================================

    async def _phase_execute(self):
        """Execute all tests"""
        self.state.phase = AgentPhase.EXECUTING
        self.state.status_message = "Executing tests..."
        await self._broadcast("Starting test execution...", "phase")

        total_tests = len(self.state.discovered_tests)

        if total_tests == 0:
            await self._broadcast("No tests to execute!", "warning")
            return

        # Get executor
        executor = self._get_executor()

        # Execute each test
        for i, test in enumerate(self.state.discovered_tests):
            if self.state.stop_requested:
                await self._broadcast("Stop requested, aborting execution...")
                break

            self.state.current_test_index = i
            self.state.current_test_name = test.name
            self.state.progress_percent = (i / total_tests) * 100

            # Update remaining time estimate
            remaining_tests = self.state.discovered_tests[i:]
            self.state.estimated_remaining_seconds = sum(
                t.estimated_duration_seconds for t in remaining_tests
            )

            await self._broadcast(
                f"[{i+1}/{total_tests}] Executing: {test.name}",
                "test_start"
            )

            # Execute the test
            result = await self._execute_single_test(test, executor)
            self.state.results.append(result)

            # Update counts
            if result.status == "passed":
                self.state.passed += 1
                await self._broadcast(f"PASSED: {test.name}", "test_passed")
            elif result.status == "failed":
                self.state.failed += 1
                await self._broadcast(
                    f"FAILED: {test.name} - {result.error_message}",
                    "test_failed"
                )
            elif result.status == "skipped":
                self.state.skipped += 1
                await self._broadcast(f"SKIPPED: {test.name}", "test_skipped")
            else:
                self.state.errors += 1
                await self._broadcast(
                    f"ERROR: {test.name} - {result.error_message}",
                    "test_error"
                )

        self.state.progress_percent = 100
        self.state.current_test_name = ""

    async def _execute_single_test(
        self,
        test: DiscoveredTest,
        executor
    ) -> TestExecutionResult:
        """Execute a single test and return the result"""
        start_time = time.time()

        try:
            # Build unified test case
            from agent.unified_executor import UnifiedTestCase, TestFormat

            if test.type == "gherkin":
                unified_case = UnifiedTestCase(
                    id=test.id,
                    name=test.name,
                    description="",
                    format=TestFormat.GHERKIN,
                    steps=test.steps,
                    tags=test.tags,
                    feature_name=test.feature_name,
                    scenario_name=test.scenario_name,
                )
            else:
                unified_case = UnifiedTestCase(
                    id=test.id,
                    name=test.name,
                    description="",
                    format=TestFormat.TRADITIONAL,
                    steps=test.steps,
                    tags=test.tags,
                )

            # Execute using the correct method signature
            from agent.unified_executor import ExecutionMode

            # Map execution mode string to enum
            mode_map = {
                "autonomous": ExecutionMode.AUTONOMOUS,
                "guided": ExecutionMode.GUIDED,
                "strict": ExecutionMode.STRICT,
            }
            exec_mode = mode_map.get(self.execution_mode, ExecutionMode.GUIDED)

            result = await executor.execute(
                test_cases=[unified_case],
                base_url=self.base_url,
                project_id=self.project_id,
                project_name=self.state.project_name,
                headless=self.headless,
                execution_mode=exec_mode,
                credentials=self.credentials,
            )

            duration = time.time() - start_time

            # Parse result - UnifiedExecutionReport has passed/failed counts
            if hasattr(result, 'passed') and result.passed > 0:
                return TestExecutionResult(
                    test_id=test.id,
                    test_name=test.name,
                    status="passed",
                    duration_seconds=duration,
                    steps_completed=len(test.steps),
                    steps_total=len(test.steps),
                )
            else:
                # Get error message from result
                error_msg = "Test failed"
                if hasattr(result, 'errors') and result.errors:
                    error_msg = result.errors[0] if result.errors else "Test failed"
                elif hasattr(result, 'results') and result.results:
                    for r in result.results:
                        if hasattr(r, 'error') and r.error:
                            error_msg = r.error
                            break

                return TestExecutionResult(
                    test_id=test.id,
                    test_name=test.name,
                    status="failed",
                    duration_seconds=duration,
                    error_message=error_msg,
                    steps_completed=0,
                    steps_total=len(test.steps),
                )

        except Exception as e:
            duration = time.time() - start_time
            return TestExecutionResult(
                test_id=test.id,
                test_name=test.name,
                status="error",
                duration_seconds=duration,
                error_message=str(e),
            )

    # =========================================================================
    # PHASE 5: ANALYZE
    # =========================================================================

    async def _phase_analyze(self):
        """Analyze results and update knowledge base"""
        self.state.phase = AgentPhase.ANALYZING
        self.state.status_message = "Analyzing results..."
        await self._broadcast("Analyzing execution results...", "phase")

        # Calculate statistics
        total = len(self.state.results)
        pass_rate = (self.state.passed / total * 100) if total > 0 else 0

        # Find patterns in failures
        failed_tests = [r for r in self.state.results if r.status == "failed"]

        # Generate summary
        summary = f"""
═══════════════════════════════════════════════════════════════
                    AUTONOMOUS EXECUTION COMPLETE
═══════════════════════════════════════════════════════════════

Project: {self.state.project_name}
Duration: {(datetime.now() - self.state.started_at).total_seconds():.1f}s

RESULTS:
  Total Tests: {total}
  ✓ Passed:    {self.state.passed} ({pass_rate:.1f}%)
  ✗ Failed:    {self.state.failed}
  ⊘ Skipped:   {self.state.skipped}
  ⚠ Errors:    {self.state.errors}

"""

        if failed_tests:
            summary += "FAILED TESTS:\n"
            for r in failed_tests[:10]:  # Show first 10
                summary += f"  - {r.test_name}: {r.error_message}\n"
            if len(failed_tests) > 10:
                summary += f"  ... and {len(failed_tests) - 10} more\n"

        summary += "\n═══════════════════════════════════════════════════════════════"

        await self._broadcast(summary, "summary")

        # Update learning engine
        await self._update_learning_engine()

    async def _update_learning_engine(self):
        """Update the knowledge base with execution results"""
        try:
            learning_engine = self._get_learning_engine()
            if not learning_engine:
                return

            # Record learnings from this execution
            for result in self.state.results:
                if hasattr(learning_engine, 'record_execution'):
                    learning_engine.record_execution(
                        test_id=result.test_id,
                        success=result.status == "passed",
                        duration=result.duration_seconds,
                        error=result.error_message,
                    )

            await self._broadcast("Knowledge base updated with execution results")

        except Exception as e:
            logger.warning(f"Could not update learning engine: {e}")

    # =========================================================================
    # STATE ACCESS
    # =========================================================================

    def get_state(self) -> Dict[str, Any]:
        """Get current state as a dictionary (for API responses)"""
        return {
            "session_id": self.state.session_id,
            "project_id": self.state.project_id,
            "project_name": self.state.project_name,
            "phase": self.state.phase.value,
            "status_message": self.state.status_message,
            "progress_percent": self.state.progress_percent,
            "current_test": self.state.current_test_name,
            "started_at": self.state.started_at.isoformat() if self.state.started_at else None,
            "completed_at": self.state.completed_at.isoformat() if self.state.completed_at else None,
            "discovered_tests_count": len(self.state.discovered_tests),
            "total_features": self.state.total_features,
            "total_scenarios": self.state.total_scenarios,
            "total_traditional_tests": self.state.total_traditional_tests,
            "passed": self.state.passed,
            "failed": self.state.failed,
            "skipped": self.state.skipped,
            "errors": self.state.errors,
            "estimated_remaining_seconds": self.state.estimated_remaining_seconds,
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "status": r.status,
                    "duration": r.duration_seconds,
                    "error": r.error_message,
                }
                for r in self.state.results
            ],
            "log": self.state.detailed_log[-50:],  # Last 50 log entries
        }


# =========================================================================
# ACTIVE SESSIONS MANAGEMENT
# =========================================================================

_active_sessions: Dict[str, ProjectAutonomousAgent] = {}


def get_active_session(session_id: str) -> Optional[ProjectAutonomousAgent]:
    """Get an active agent session"""
    return _active_sessions.get(session_id)


def get_project_session(project_id: str) -> Optional[ProjectAutonomousAgent]:
    """Get active session for a project (if any)"""
    for agent in _active_sessions.values():
        if agent.project_id == project_id and agent.state.phase not in [
            AgentPhase.COMPLETED, AgentPhase.FAILED, AgentPhase.STOPPED
        ]:
            return agent
    return None


def register_session(agent: ProjectAutonomousAgent):
    """Register an agent session"""
    _active_sessions[agent.session_id] = agent


def unregister_session(session_id: str):
    """Unregister an agent session"""
    if session_id in _active_sessions:
        del _active_sessions[session_id]


def get_all_sessions() -> List[Dict[str, Any]]:
    """Get status of all active sessions"""
    return [agent.get_state() for agent in _active_sessions.values()]
