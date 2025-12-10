"""
Autonomous Agent API

Unified API endpoints for the autonomous test agent.
Provides consistent interface for both Traditional and Gherkin tests.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel, Field

from agent import (
    UnifiedTestExecutor,
    UnifiedTestCase,
    TestFormat,
    ExecutionMode,
    TrainingDataCollector,
    KnowledgeImportExport,
    AgentConfig
)
from agent.knowledge.knowledge_index import KnowledgeIndex
from agent.knowledge.learning_engine import LearningEngine
from agent.knowledge.pattern_store import PatternStore
from gherkin_storage import get_gherkin_storage

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/agent", tags=["Autonomous Agent"])

# Global instances
_executor: Optional[UnifiedTestExecutor] = None
_training_collector: Optional[TrainingDataCollector] = None
_knowledge_io: Optional[KnowledgeImportExport] = None

# WebSocket connections for logs
_log_connections: List[WebSocket] = []

# Track running execution for stop functionality
_current_execution: Dict[str, Any] = {
    "running": False,
    "should_stop": False,
    "report_id": None,
    "partial_results": [],
    "start_time": None
}


def get_executor() -> UnifiedTestExecutor:
    """Get or create unified executor instance"""
    global _executor
    if _executor is None:
        _executor = UnifiedTestExecutor(
            data_dir="data/agent_knowledge",
            config=AgentConfig(
                enable_spa_mode=True,
                enable_recovery=True,
                enable_learning=True
            )
        )
    return _executor


def get_training_collector() -> TrainingDataCollector:
    """Get or create training data collector instance"""
    global _training_collector
    if _training_collector is None:
        executor = get_executor()
        _training_collector = TrainingDataCollector(
            knowledge_index=executor.knowledge_index,
            learning_engine=executor.learning_engine,
            pattern_store=executor.pattern_store,
            data_dir="data/agent_knowledge"
        )
    return _training_collector


def get_knowledge_io() -> KnowledgeImportExport:
    """Get or create knowledge import/export instance"""
    global _knowledge_io
    if _knowledge_io is None:
        _knowledge_io = KnowledgeImportExport(data_dir="data/agent_knowledge")
    return _knowledge_io


# ==================== Request/Response Models ====================

class UnifiedRunRequest(BaseModel):
    """Unified test execution request"""
    project_id: str
    project_name: str
    base_url: str
    headless: bool = False
    execution_mode: str = "guided"  # autonomous, guided, strict

    # For traditional tests
    test_case_ids: Optional[List[str]] = None
    test_cases: Optional[List[Dict[str, Any]]] = None

    # For Gherkin tests
    feature_id: Optional[str] = None
    feature: Optional[Dict[str, Any]] = None
    scenario_filter: Optional[List[str]] = None
    tag_filter: Optional[List[str]] = None

    # Optional credentials
    credentials: Optional[Dict[str, str]] = None


class ExploreRequest(BaseModel):
    """Application exploration request"""
    base_url: str
    max_pages: int = 20
    max_depth: int = 3
    headless: bool = True


class TrainingImportRequest(BaseModel):
    """Training data import request"""
    source_type: str  # file, url, historical
    source_path: Optional[str] = None
    merge: bool = True


class KnowledgeExportRequest(BaseModel):
    """Knowledge export request"""
    export_type: str = "full"  # full, domain, patterns
    domain: Optional[str] = None
    include_training: bool = False


class TrainingStatsResponse(BaseModel):
    """Training statistics response"""
    total_elements: int
    total_patterns: int
    total_batches: int
    by_source: Dict[str, Dict[str, int]]
    recommendations: List[str]


# ==================== Unified Execution Endpoints ====================

@router.post("/run")
async def run_unified_tests(
    request: UnifiedRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Unified test execution endpoint.

    Works with both Traditional and Gherkin tests using the autonomous agent.
    Returns consistent result format regardless of test type.
    """
    executor = get_executor()

    # Determine test format and convert tests
    test_cases: List[UnifiedTestCase] = []
    test_format = TestFormat.TRADITIONAL

    if request.feature or request.feature_id:
        # Gherkin execution
        test_format = TestFormat.GHERKIN

        if request.feature:
            test_cases = executor.convert_gherkin_feature(request.feature)
        elif request.feature_id:
            # Load feature from storage
            feature = await _load_feature(request.feature_id)
            if not feature:
                raise HTTPException(status_code=404, detail="Feature not found")
            test_cases = executor.convert_gherkin_feature(feature)

        # Apply filters
        if request.scenario_filter:
            test_cases = [tc for tc in test_cases if tc.scenario_name in request.scenario_filter]
        if request.tag_filter:
            test_cases = [tc for tc in test_cases if any(t in tc.tags for t in request.tag_filter)]

    elif request.test_cases or request.test_case_ids:
        # Traditional execution
        test_format = TestFormat.TRADITIONAL

        if request.test_cases:
            test_cases = [executor.convert_traditional_test(tc) for tc in request.test_cases]
        elif request.test_case_ids:
            # Load test cases from storage
            loaded_tests = await _load_test_cases(request.project_id, request.test_case_ids)
            test_cases = [executor.convert_traditional_test(tc) for tc in loaded_tests]

    if not test_cases:
        raise HTTPException(status_code=400, detail="No test cases provided")

    # Parse execution mode
    try:
        exec_mode = ExecutionMode(request.execution_mode)
    except ValueError:
        exec_mode = ExecutionMode.GUIDED

    # Set up log callback
    async def broadcast_log(message: str):
        for ws in _log_connections:
            try:
                await ws.send_text(message)
            except Exception:
                pass

    executor.set_callbacks(
        log_callback=lambda msg: asyncio.create_task(broadcast_log(msg))
    )

    # Set stop check callback so executor can check for stop requests
    executor.set_stop_callback(lambda: _current_execution.get("should_stop", False))

    # Set up execution tracking
    global _current_execution
    report_id = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    _current_execution = {
        "running": True,
        "should_stop": False,
        "report_id": report_id,
        "partial_results": [],
        "start_time": datetime.utcnow().isoformat(),
        "project_id": request.project_id,
        "project_name": request.project_name
    }

    # Execute tests
    try:
        report = await executor.execute(
            test_cases=test_cases,
            base_url=request.base_url,
            project_id=request.project_id,
            project_name=request.project_name,
            headless=request.headless,
            execution_mode=exec_mode,
            credentials=request.credentials
        )

        # Save report
        report_path = await _save_report(report)

        return {
            "success": True,
            "report_id": report.id,
            "report_path": report_path,
            "summary": {
                "total": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "pass_rate": report.pass_rate,
                "duration_seconds": report.duration_seconds,
                "ai_dependency_percent": report.ai_dependency_percent,
                "new_selectors_learned": report.new_selectors_learned
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "error_message": r.error_message,
                    "ai_calls": r.ai_calls_made,
                    "kb_hits": r.knowledge_base_hits
                }
                for r in report.results
            ]
        }

    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        # Save partial report if we have any results
        if _current_execution["partial_results"]:
            try:
                await _save_partial_report(
                    _current_execution["report_id"],
                    _current_execution["partial_results"],
                    _current_execution.get("project_id"),
                    _current_execution.get("project_name"),
                    stopped=False
                )
            except Exception as save_error:
                logger.error(f"Error saving partial report: {save_error}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Reset execution state
        _current_execution = {
            "running": False,
            "should_stop": False,
            "report_id": None,
            "partial_results": [],
            "start_time": None
        }


@router.get("/run/{report_id}")
async def get_execution_report(report_id: str):
    """Get a specific execution report"""
    # Reports are saved in data/reports/{report_id}.json (matching storage.py)
    report_path = Path("data/reports") / f"{report_id}.json"

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(report_path, 'r') as f:
        return json.load(f)


@router.post("/stop")
async def stop_execution():
    """
    Stop the currently running test execution IMMEDIATELY.

    This will:
    1. Force close the browser to stop execution immediately
    2. Save a partial report with completed results
    3. Clean up all browser resources
    """
    global _current_execution

    if not _current_execution["running"]:
        return {
            "success": False,
            "message": "No test execution is currently running"
        }

    # Signal stop to both the tracking state and the executor
    _current_execution["should_stop"] = True

    # Broadcast stop message to WebSocket clients
    for ws in _log_connections:
        try:
            await ws.send_text("[SYSTEM] STOPPING IMMEDIATELY - closing browser...")
        except Exception:
            pass

    # FORCE STOP - close browser immediately to interrupt execution
    executor = get_executor()
    try:
        await executor.force_stop()
    except Exception as e:
        logger.warning(f"Force stop error (may be expected): {e}")
        # Even if force_stop fails, continue with cleanup
        executor.request_stop()

    # Save partial report if we have results
    partial_report_id = None
    if _current_execution["partial_results"]:
        try:
            partial_report_id = await _save_partial_report(
                _current_execution["report_id"],
                _current_execution["partial_results"],
                _current_execution.get("project_id"),
                _current_execution.get("project_name"),
                stopped=True
            )
        except Exception as e:
            logger.error(f"Error saving partial report: {e}")

    return {
        "success": True,
        "message": "Stop signal sent. Test will stop after current step completes.",
        "partial_report_id": partial_report_id
    }


@router.get("/status")
async def get_execution_status():
    """Get current execution status"""
    return {
        "running": _current_execution["running"],
        "should_stop": _current_execution["should_stop"],
        "report_id": _current_execution["report_id"],
        "completed_tests": len(_current_execution["partial_results"]),
        "start_time": _current_execution["start_time"]
    }


async def _save_partial_report(
    report_id: str,
    partial_results: List[Any],
    project_id: str,
    project_name: str,
    stopped: bool = False
) -> str:
    """Save a partial report when execution is stopped or interrupted"""
    # Use data/reports to match storage.py
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Calculate summary from partial results
    passed = sum(1 for r in partial_results if r.get("status") == "passed")
    failed = sum(1 for r in partial_results if r.get("status") == "failed")
    total = len(partial_results)

    report_dict = {
        "id": report_id or f"partial_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "project_id": project_id or "unknown",
        "project_name": project_name or "Unknown Project",
        "executed_at": _current_execution.get("start_time") or datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "status": "stopped" if stopped else "incomplete",
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "skipped": 0,
        "duration": (datetime.utcnow() - datetime.fromisoformat(_current_execution["start_time"])).total_seconds() if _current_execution.get("start_time") else 0,
        "results": partial_results,
        "partial": True,
        "stopped_by_user": stopped
    }

    report_path = reports_dir / f"{report_dict['id']}.json"
    with open(report_path, 'w') as f:
        json.dump(report_dict, f, indent=2, default=str)

    logger.info(f"Saved partial report: {report_path}")
    return report_dict['id']


# ==================== Training Data Endpoints ====================

@router.post("/training/explore")
async def explore_for_training(request: ExploreRequest):
    """
    Explore an application to gather training data.

    This crawls the app and builds the knowledge base.
    """
    from playwright.async_api import async_playwright

    collector = get_training_collector()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=request.headless)
            page = await browser.new_page()

            batch = await collector.collect_from_exploration(
                base_url=request.base_url,
                max_pages=request.max_pages,
                page=page
            )

            await browser.close()

        return {
            "success": True,
            "batch_id": batch.id,
            "elements_collected": batch.elements_count,
            "patterns_collected": batch.patterns_count
        }

    except Exception as e:
        logger.error(f"Exploration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/import-historical")
async def import_historical_reports():
    """
    Import training data from historical test reports.

    Mines existing reports for successful selectors.
    """
    collector = get_training_collector()

    try:
        batch = collector.collect_from_historical_reports("reports")

        return {
            "success": True,
            "batch_id": batch.id,
            "elements_collected": batch.elements_count,
            "patterns_collected": batch.patterns_count
        }

    except Exception as e:
        logger.error(f"Historical import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/stats")
async def get_training_stats() -> TrainingStatsResponse:
    """Get training data collection statistics"""
    collector = get_training_collector()
    stats = collector.get_collection_stats()
    recommendations = collector.get_collection_recommendations()

    return TrainingStatsResponse(
        total_elements=stats["total_elements"],
        total_patterns=stats["total_patterns"],
        total_batches=stats["total_batches"],
        by_source=stats["by_source"],
        recommendations=recommendations
    )


@router.get("/training/recommendations")
async def get_training_recommendations():
    """Get recommendations for improving training data"""
    collector = get_training_collector()
    return {
        "recommendations": collector.get_collection_recommendations()
    }


# ==================== Knowledge Base Endpoints ====================

@router.post("/knowledge/export")
async def export_knowledge(request: KnowledgeExportRequest):
    """Export knowledge base"""
    knowledge_io = get_knowledge_io()

    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if request.export_type == "full":
            output_path = f"exports/knowledge_full_{timestamp}.json"
            stats = knowledge_io.export_full(output_path, request.include_training)
        elif request.export_type == "domain" and request.domain:
            output_path = f"exports/knowledge_{request.domain}_{timestamp}.json"
            stats = knowledge_io.export_domain(request.domain, output_path)
        elif request.export_type == "patterns":
            output_path = f"exports/patterns_{timestamp}.json"
            stats = knowledge_io.export_patterns_only(output_path)
        else:
            raise HTTPException(status_code=400, detail="Invalid export type")

        return {
            "success": True,
            "export_path": output_path,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/import")
async def import_knowledge(request: TrainingImportRequest):
    """Import knowledge from external file"""
    knowledge_io = get_knowledge_io()

    try:
        if not request.source_path:
            raise HTTPException(status_code=400, detail="source_path is required")

        stats = knowledge_io.import_knowledge(
            import_path=request.source_path,
            merge=request.merge
        )

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/stats")
async def get_knowledge_stats():
    """Get knowledge base statistics"""
    executor = get_executor()
    return executor.get_learning_stats()


# ==================== Learning Metrics Endpoints ====================

@router.get("/metrics/ai-dependency")
async def get_ai_dependency_metrics():
    """
    Get AI dependency metrics over time.

    Shows how the system is learning and reducing AI usage.
    """
    executor = get_executor()
    stats = executor.get_learning_stats()

    return {
        "current_ai_dependency_percent": stats.get("ai_discovered_percentage", 0),
        "total_elements_known": stats.get("total_elements_known", 0),
        "average_confidence": stats.get("average_confidence", 0),
        "patterns_learned": stats.get("patterns_learned", 0),
        "recommendation": _get_ai_reduction_recommendation(stats)
    }


def _get_ai_reduction_recommendation(stats: Dict) -> str:
    """Get recommendation for reducing AI dependency"""
    ai_pct = stats.get("ai_discovered_percentage", 0)
    elements = stats.get("total_elements_known", 0)

    if elements < 50:
        return "Run application exploration to quickly build initial knowledge base"
    elif ai_pct > 50:
        return "Continue running tests - the system is still learning"
    elif ai_pct > 20:
        return "Good progress! Consider recording human test sessions for hard-to-find elements"
    elif ai_pct > 5:
        return "Excellent! The system is mostly self-sufficient"
    else:
        return "Outstanding! AI dependency is minimal"


# ==================== WebSocket for Real-time Logs ====================

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time execution logs"""
    await websocket.accept()
    _log_connections.append(websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        _log_connections.remove(websocket)


# ==================== Helper Functions ====================

async def _load_feature(feature_id: str) -> Optional[Dict[str, Any]]:
    """Load Gherkin feature from storage"""
    # Use GherkinStorage to load the feature (ensures correct path)
    gherkin_storage = get_gherkin_storage()
    feature_dict = gherkin_storage.load_feature_dict(feature_id)

    if feature_dict:
        return feature_dict

    # Fallback: check legacy location
    legacy_path = Path("data/gherkin_features") / f"{feature_id}.json"
    if legacy_path.exists():
        with open(legacy_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return None


async def _load_test_cases(
    project_id: str,
    test_case_ids: List[str]
) -> List[Dict[str, Any]]:
    """Load test cases from project"""
    project_path = Path("data/projects") / f"{project_id}.json"

    if not project_path.exists():
        return []

    with open(project_path, 'r') as f:
        project = json.load(f)

    all_test_cases = project.get("test_cases", [])
    return [tc for tc in all_test_cases if tc.get("id") in test_case_ids]


async def _save_report(report) -> str:
    """Save execution report to disk in compatible format"""
    try:
        # Ensure reports directory exists - use data/reports to match storage.py
        reports_dir = Path("data/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Save in the format expected by the existing storage system
        # Format: data/reports/{report_id}.json (matching storage.py)
        report_path = reports_dir / f"{report.id}.json"

        logger.info(f"Saving report to: {report_path}")

        # Convert to format compatible with existing TestReport model
        results_list = []
        for r in report.results:
            try:
                result_dict = {
                    "test_case_id": r.test_id,
                    "test_case_name": r.test_name,
                    "status": r.status,
                    "duration": r.duration_ms / 1000 if r.duration_ms else 0,
                    "error_message": r.error_message,
                    "screenshot_path": r.screenshot_path,
                    "logs": r.logs if hasattr(r, 'logs') and r.logs else []
                }
                results_list.append(result_dict)
            except Exception as e:
                logger.error(f"Error converting result: {e}")
                results_list.append({
                    "test_case_id": getattr(r, 'test_id', 'unknown'),
                    "test_case_name": getattr(r, 'test_name', 'Unknown'),
                    "status": "error",
                    "duration": 0,
                    "error_message": str(e),
                    "screenshot_path": None,
                    "logs": []
                })

        report_dict = {
            "id": report.id,
            "project_id": report.project_id,
            "project_name": report.project_name,
            "executed_at": report.executed_at,
            "total_tests": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "duration": report.duration_seconds,
            "results": results_list,
            # Extended fields for unified executor
            "format": report.format.value if hasattr(report.format, 'value') else str(report.format),
            "execution_mode": report.execution_mode.value if hasattr(report.execution_mode, 'value') else str(report.execution_mode),
            "pass_rate": report.pass_rate,
            "total_ai_calls": report.total_ai_calls,
            "total_kb_hits": report.total_kb_hits,
            "ai_dependency_percent": report.ai_dependency_percent,
            "new_selectors_learned": report.new_selectors_learned,
            "errors": report.errors if hasattr(report, 'errors') else []
        }

        with open(report_path, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)

        logger.info(f"Report saved successfully: {report_path}")
        return str(report_path)

    except Exception as e:
        logger.error(f"Error saving report: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# ==================== PROJECT AUTONOMOUS AGENT ====================
# These endpoints trigger the intelligent agent that takes complete ownership
# of testing a project when the user clicks "Run"

from agent.project_autonomous_agent import (
    ProjectAutonomousAgent,
    get_active_session,
    get_project_session,
    register_session,
    unregister_session,
    get_all_sessions,
)


class AutonomousRunRequest(BaseModel):
    """Request to start autonomous agent for a project"""
    project_id: str
    headless: bool = True
    execution_mode: str = "autonomous"  # autonomous, guided, strict


class AutonomousSessionResponse(BaseModel):
    """Response with session information"""
    session_id: str
    project_id: str
    project_name: str
    status: str
    message: str


@router.post("/autonomous/run/{project_id}", response_model=AutonomousSessionResponse)
async def start_autonomous_run(
    project_id: str,
    background_tasks: BackgroundTasks,
    headless: bool = True,
    execution_mode: str = "autonomous"
):
    """
    Start the autonomous agent for a project.
    
    This is the main entry point when a user clicks "Run" on a project.
    The agent will:
    1. Discover all tests (Gherkin + Traditional)
    2. Create an intelligent execution plan
    3. Execute tests autonomously
    4. Report results in real-time via WebSocket
    
    The execution happens in the background - this endpoint returns immediately
    with a session_id that can be used to track progress.
    """
    # Check if there's already an active session for this project
    existing = get_project_session(project_id)
    if existing:
        return AutonomousSessionResponse(
            session_id=existing.session_id,
            project_id=project_id,
            project_name=existing.state.project_name,
            status="already_running",
            message=f"Agent already running for this project (phase: {existing.state.phase.value})"
        )
    
    # Create the autonomous agent
    agent = ProjectAutonomousAgent(
        project_id=project_id,
        broadcast_callback=broadcast_agent_log,
        headless=headless,
        execution_mode=execution_mode,
    )
    
    # Register the session
    register_session(agent)
    
    # Run in background
    background_tasks.add_task(run_autonomous_agent, agent)
    
    return AutonomousSessionResponse(
        session_id=agent.session_id,
        project_id=project_id,
        project_name="",  # Will be populated once agent initializes
        status="started",
        message="Autonomous agent started. Connect to WebSocket for real-time updates."
    )


async def run_autonomous_agent(agent: ProjectAutonomousAgent):
    """Background task to run the autonomous agent"""
    try:
        await agent.run()
    except Exception as e:
        logger.exception(f"Autonomous agent failed: {e}")
    finally:
        # Keep session for a while for result retrieval, then clean up
        await asyncio.sleep(300)  # Keep for 5 minutes
        unregister_session(agent.session_id)


async def broadcast_agent_log(message: str):
    """Broadcast agent log message to all connected WebSocket clients"""
    disconnected = []
    for ws in _log_connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    
    # Clean up disconnected
    for ws in disconnected:
        if ws in _log_connections:
            _log_connections.remove(ws)


@router.get("/autonomous/session/{session_id}")
async def get_session_status(session_id: str):
    """
    Get the current status of an autonomous agent session.
    
    Returns detailed information about:
    - Current phase (discovering, planning, executing, etc.)
    - Progress percentage
    - Test results so far
    - Logs
    """
    agent = get_active_session(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    return agent.get_state()


@router.post("/autonomous/session/{session_id}/stop")
async def stop_session(session_id: str):
    """
    Request the agent to stop gracefully.
    
    The agent will complete the current test and then stop.
    """
    agent = get_active_session(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent.stop()
    
    return {
        "success": True,
        "message": "Stop requested. Agent will finish current test and stop."
    }


@router.get("/autonomous/sessions")
async def list_sessions():
    """
    List all active autonomous agent sessions.
    """
    return {
        "sessions": get_all_sessions()
    }


@router.get("/autonomous/project/{project_id}/status")
async def get_project_agent_status(project_id: str):
    """
    Check if there's an autonomous agent running for a specific project.
    
    Useful for the UI to show the correct state.
    """
    agent = get_project_session(project_id)
    
    if agent:
        return {
            "running": True,
            "session_id": agent.session_id,
            "phase": agent.state.phase.value,
            "progress": agent.state.progress_percent,
            "passed": agent.state.passed,
            "failed": agent.state.failed,
            "current_test": agent.state.current_test_name,
        }
    else:
        return {
            "running": False,
            "session_id": None,
        }
