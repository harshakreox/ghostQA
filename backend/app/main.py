from dotenv import load_dotenv
import pathlib

# Load .env from backend folder (parent of app)
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional
import asyncio
import os
import sys
import uuid
from datetime import datetime
from ai_api import router as ai_router
# Autonomous Agent API
from agent_api import router as agent_router
# Authentication
from auth_api import router as auth_router, get_current_user, get_current_admin, get_optional_current_user
from auth_models import TokenData, UserRole
# Gherkin imports
from ai_gherkin_generator import AIGherkinGenerator, extract_text_from_file
from gherkin_storage import get_gherkin_storage
from folder_storage import get_folder_storage
from models_folder import (
    Folder, CreateFolderRequest, UpdateFolderRequest,
    MoveFeatureToFolderRequest, BulkMoveFeaturesToFolderRequest
)
from gherkin_executor import GherkinExecutor
from models_gherkin import GherkinFeature
from pydantic import BaseModel
from fastapi.responses import Response, StreamingResponse
import io
import zipfile
from pathlib import Path
import json


# Release Management
from release_models import (
    Release, Environment, ReleaseProject, ReleaseIteration,
    CreateReleaseRequest, UpdateReleaseRequest, AddEnvironmentRequest,
    AddProjectToReleaseRequest, RunReleaseTestsRequest, ReleaseMetrics,
    ReleaseStatus, EnvironmentType
)
from release_api import router as releases_router
# Folder Management
from folder_api import router as folder_router
# Organization Management
from org_api import router as org_router

# ===== WINDOWS FIX FOR PLAYWRIGHT =====
# Fix for Windows: Playwright needs ProactorEventLoop on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ======================================

from models import (
    Project, TestCase, TestReport, TestResult, CreateProjectRequest,
    CreateTestCaseRequest, RunTestRequest, TestAction, UIFrameworkConfig
)
from storage import Storage
from framework_library import get_all_frameworks

# Import Windows-safe test runner
if sys.platform == 'win32':
    from windows_test_runner import run_tests_windows_safe
else:
    from test_engine import TestEngine

# Try to import HTML reporter (optional - requires pandas)
try:
    from html_reporter import generate_html_report
    HTML_REPORTS_ENABLED = True
except ImportError:
    HTML_REPORTS_ENABLED = False
    print("[WARNING] HTML reports disabled (pandas not installed)")

app = FastAPI(title="Autonomous Test Automation Framework")

storage = Storage()
gherkin_storage = get_gherkin_storage()
folder_storage = get_folder_storage() 

# CORS Configuration
# In production, set CORS_ORIGINS environment variable to comma-separated allowed origins
# Example: CORS_ORIGINS=https://app.example.com,https://admin.example.com
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    # Development defaults - localhost only
    allowed_origins = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

class RunAutonomousTestRequest(BaseModel):
    feature_id: str
    project_id: Optional[str] = None
    headless: bool = False
    scenario_filter: Optional[List[str]] = None

class MoveTestCaseToFolderRequest(BaseModel):
    """Request to move a test case to a folder"""
    folder_id: Optional[str] = None  # None means move to root

class MoveTraditionalSuiteToFolderRequest(BaseModel):
    """Request to move a traditional suite to a folder"""
    folder_id: Optional[str] = None  # None means move to root


# Include routers
app.include_router(auth_router)  # Authentication
app.include_router(org_router)  # Organizations
app.include_router(releases_router)
app.include_router(ai_router)
# Include autonomous agent router
app.include_router(agent_router)
# Include folder router
app.include_router(folder_router)

# Initialize storage
storage = Storage()

# WebSocket connections for real-time logging
active_connections: List[WebSocket] = []


# ============ WebSocket Logging ============
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_log(message: str):
    """Send log message to all connected WebSocket clients"""
    # Also print to console for debugging
    print(f"[LOG] {message}")

    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception as e:
            print(f"[WS ERROR] Failed to send to client: {e}")
            disconnected.append(connection)

    # Clean up disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


# ============ Project Management ============
@app.post("/api/projects", response_model=Project)
async def create_project(
    request: CreateProjectRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Create a new test project"""
    project = Project(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        base_url=request.base_url,
        test_cases=[],
        owner_id=current_user.user_id,  # Track owner
        credentials=request.credentials,  # New: Multiple credential sets
        test_username=request.test_username,
        test_password=request.test_password,
        test_admin_username=request.test_admin_username,
        test_admin_password=request.test_admin_password,
        auto_test_data=request.auto_test_data,
        ui_config=request.ui_config
    )
    storage.save_project(project)
    return project


@app.get("/api/projects", response_model=List[Project])
async def get_projects(current_user: TokenData = Depends(get_current_user)):
    """Get projects - Admin sees all, User sees only their own"""
    all_projects = storage.get_all_projects()

    # Admin sees all projects
    if current_user.role == UserRole.ADMIN:
        return all_projects

    # User sees only their own projects
    return [p for p in all_projects if p.owner_id == current_user.user_id]


@app.get("/api/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get a specific project - Admin can see all, User can only see their own"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return project


@app.put("/api/projects/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    request: CreateProjectRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Update a project - Admin can update all, User can only update their own"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    project.name = request.name
    project.description = request.description
    project.base_url = request.base_url
    project.credentials = request.credentials  # New: Multiple credential sets
    project.test_username = request.test_username
    project.test_password = request.test_password
    project.test_admin_username = request.test_admin_username
    project.test_admin_password = request.test_admin_password
    project.auto_test_data = request.auto_test_data
    project.ui_config = request.ui_config
    storage.save_project(project)
    return project


@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Delete a project - Admin can delete all, User can only delete their own"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check access permission
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    storage.delete_project(project_id)
    return {"message": "Project deleted successfully"}


# ============ Test Case Management ============
@app.post("/api/projects/{project_id}/test-cases", response_model=TestCase)
async def create_test_case(project_id: str, request: CreateTestCaseRequest):
    """Create a new test case"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    test_case = TestCase(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        actions=request.actions
    )
    
    project.test_cases.append(test_case)
    storage.save_project(project)
    return test_case


@app.get("/api/projects/{project_id}/test-cases/{test_case_id}", response_model=TestCase)
async def get_test_case(project_id: str, test_case_id: str):
    """Get a specific test case"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    test_case = next((tc for tc in project.test_cases if tc.id == test_case_id), None)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case


@app.put("/api/projects/{project_id}/test-cases/{test_case_id}", response_model=TestCase)
async def update_test_case(project_id: str, test_case_id: str, request: CreateTestCaseRequest):
    """Update a test case"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    test_case = next((tc for tc in project.test_cases if tc.id == test_case_id), None)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    
    test_case.name = request.name
    test_case.description = request.description
    test_case.actions = request.actions
    storage.save_project(project)
    return test_case


@app.delete("/api/projects/{project_id}/test-cases/{test_case_id}")
async def delete_test_case(project_id: str, test_case_id: str):
    """Delete a test case"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.test_cases = [tc for tc in project.test_cases if tc.id != test_case_id]
    storage.save_project(project)
    return {"message": "Test case deleted successfully"}


# ============ Test Case Folder Operations ============

@app.put("/api/projects/{project_id}/test-cases/{test_case_id}/move")
async def move_test_case_to_folder(
    project_id: str,
    test_case_id: str,
    request: MoveTestCaseToFolderRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Move a test case to a folder"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify permission
    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Find the test case
    test_case = None
    for tc in project.test_cases:
        if tc.id == test_case_id:
            test_case = tc
            break

    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")

    # Validate folder if specified
    if request.folder_id:
        folder = folder_storage.load_folder(request.folder_id)
        if not folder or folder.project_id != project_id:
            raise HTTPException(status_code=400, detail="Invalid folder")
        if folder.category != "action-based":
            raise HTTPException(status_code=400, detail="Folder is not for action-based test cases")

    # Update test case folder_id
    test_case.folder_id = request.folder_id
    storage.save_project(project)

    return {"message": "Test case moved successfully", "folder_id": request.folder_id}


@app.get("/api/projects/{project_id}/test-cases/by-folder/{folder_id}")
async def get_test_cases_by_folder(
    project_id: str,
    folder_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all test cases in a specific folder (use 'root' for uncategorized)"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Filter by folder_id
    actual_folder_id = None if folder_id == "root" else folder_id

    test_cases = [tc for tc in project.test_cases if tc.folder_id == actual_folder_id]

    return {"test_cases": [tc.model_dump() for tc in test_cases]}


@app.get("/api/projects/{project_id}/action-based-with-folders")
async def get_action_based_with_folders(
    project_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all action-based test cases organized by folders"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    folder_tree = folder_storage.get_folder_tree(project_id, "action-based")
    all_test_cases = project.test_cases

    test_cases_by_folder = {}
    root_test_cases = []

    for tc in all_test_cases:
        tc_dict = tc.model_dump()
        folder_id = tc.folder_id
        if folder_id:
            if folder_id not in test_cases_by_folder:
                test_cases_by_folder[folder_id] = []
            test_cases_by_folder[folder_id].append(tc_dict)
        else:
            root_test_cases.append(tc_dict)

    return {
        "folder_tree": folder_tree,
        "test_cases_by_folder": test_cases_by_folder,
        "root_test_cases": root_test_cases,
        "total_test_cases": len(all_test_cases),
        "total_folders": len(folder_storage.list_folders(project_id, "action-based"))
    }


# ============ Traditional Suite Folder Operations ============

@app.put("/api/traditional/suites/{suite_id}/move")
async def move_traditional_suite_to_folder(
    suite_id: str,
    request: MoveTraditionalSuiteToFolderRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Move a traditional suite to a folder"""
    from gherkin_storage import get_gherkin_storage
    traditional_storage = get_gherkin_storage()

    suite = traditional_storage.load_traditional_suite_dict(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")

    project_id = suite.get("project_id")

    # Validate folder if specified
    if request.folder_id:
        folder = folder_storage.load_folder(request.folder_id)
        if not folder:
            raise HTTPException(status_code=400, detail="Folder not found")
        if project_id and folder.project_id != project_id:
            raise HTTPException(status_code=400, detail="Folder belongs to different project")
        if folder.category != "traditional":
            raise HTTPException(status_code=400, detail="Folder is not for traditional test suites")

    # Update suite folder_id
    updated = traditional_storage.update_traditional_suite_folder(suite_id, request.folder_id)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update suite")

    return updated


@app.get("/api/projects/{project_id}/traditional-suites/by-folder/{folder_id}")
async def get_traditional_suites_by_folder(
    project_id: str,
    folder_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all traditional suites in a specific folder (use 'root' for uncategorized)"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from gherkin_storage import get_gherkin_storage
    traditional_storage = get_gherkin_storage()

    # Filter by folder_id
    actual_folder_id = None if folder_id == "root" else folder_id

    suites = traditional_storage.list_traditional_suites_by_folder(project_id, actual_folder_id)

    return {"suites": suites}


@app.get("/api/projects/{project_id}/traditional-with-folders")
async def get_traditional_with_folders(
    project_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get all traditional test suites organized by folders"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    from gherkin_storage import get_gherkin_storage
    traditional_storage = get_gherkin_storage()

    folder_tree = folder_storage.get_folder_tree(project_id, "traditional")
    all_suites = traditional_storage.list_traditional_suites(project_id)

    suites_by_folder = {}
    root_suites = []

    for suite in all_suites:
        folder_id = suite.get("folder_id")
        if folder_id:
            if folder_id not in suites_by_folder:
                suites_by_folder[folder_id] = []
            suites_by_folder[folder_id].append(suite)
        else:
            root_suites.append(suite)

    return {
        "folder_tree": folder_tree,
        "suites_by_folder": suites_by_folder,
        "root_suites": root_suites,
        "total_suites": len(all_suites),
        "total_folders": len(folder_storage.list_folders(project_id, "traditional"))
    }


# ============ Test Execution ============
@app.post("/api/run-tests")
async def run_tests(
    request: RunTestRequest,
    current_user: TokenData = Depends(get_current_admin)  # Admin only
):
    """Execute test cases - Admin only"""
    import sys as _sys
    print(f"\n{'='*60}", flush=True)
    print(f" RUN TESTS ENDPOINT CALLED", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"Project ID: {request.project_id}", flush=True)
    print(f"Test Case IDs: {request.test_case_ids}", flush=True)
    print(f"Headless: {request.headless}", flush=True)
    print(f"Platform: {_sys.platform}", flush=True)
    print(f"User: {current_user.username} (Admin)", flush=True)

    project = storage.get_project(request.project_id)
    if not project:
        print(f"[ERR] Project not found: {request.project_id}", flush=True)
        raise HTTPException(status_code=404, detail="Project not found")

    print(f"[OK] Project found: {project.name}", flush=True)
    print(f"   Base URL: {project.base_url}", flush=True)
    print(f"   Total test cases: {len(project.test_cases)}", flush=True)

    # Filter selected test cases
    if request.test_case_ids:
        test_cases = [tc for tc in project.test_cases if tc.id in request.test_case_ids]
    else:
        test_cases = project.test_cases

    if not test_cases:
        print(f"[ERR] No test cases to run", flush=True)
        raise HTTPException(status_code=400, detail="No test cases to run")

    print(f"[OK] Selected {len(test_cases)} test cases to run", flush=True)

    # Create report directory (use data/reports for consistency with Storage)
    report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_dir = f"data/reports/{report_id}"
    os.makedirs(report_dir, exist_ok=True)
    print(f"[OK] Report directory created: {report_dir}", flush=True)

    # Get the main event loop for WebSocket broadcasting
    main_loop = asyncio.get_event_loop()

    # Run tests in background thread (required for Windows + Playwright)
    async def run_test_suite():
        try:
            print(f"\n Starting test suite execution...")

            await broadcast_log(" Starting test execution...")
            await broadcast_log(f" Project: {project.name}")
            await broadcast_log(f" Base URL: {project.base_url or 'Not set'}")
            await broadcast_log(f" Tests to run: {len(test_cases)}")

            if sys.platform == 'win32':
                # Windows: Use thread-based runner with separate event loop
                print(f" Using Windows-safe test runner...")
                await broadcast_log(" Using Windows-compatible test runner...")

                from concurrent.futures import ThreadPoolExecutor

                def run_in_thread():
                    """Run tests in separate thread with its own event loop"""
                    try:
                        print(f"[THREAD] Starting test execution thread...")

                        # Set Windows event loop policy for this thread
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                        print(f"[THREAD] Event loop policy set")

                        # Create new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        print(f"[THREAD] New event loop created")

                        try:
                            from test_engine import TestEngine
                            print(f"[THREAD] TestEngine imported")

                            def thread_log(message: str):
                                """Thread-safe logging that broadcasts to WebSocket"""
                                print(f"[TEST] {message}")
                                try:
                                    asyncio.run_coroutine_threadsafe(
                                        broadcast_log(message),
                                        main_loop
                                    )
                                except Exception as e:
                                    print(f"[BROADCAST ERROR] {e}")

                            engine = TestEngine(log_callback=thread_log)
                            print(f"[THREAD] TestEngine instance created")

                            thread_log(" Launching browser...")

                            # Run tests in the thread's event loop
                            print(f"[THREAD] About to run tests...")
                            report = loop.run_until_complete(
                                engine.run_tests(
                                    test_cases=test_cases,
                                    base_url=project.base_url,
                                    report_dir=report_dir,
                                    headless=request.headless
                                )
                            )
                            print(f"[THREAD] Tests completed!")

                            thread_log(f"[OK] Tests completed! Passed: {report.passed}, Failed: {report.failed}")
                            return report

                        except Exception as inner_e:
                            import traceback
                            print(f"[THREAD] [ERR] Inner exception: {inner_e}")
                            print(f"[THREAD] Traceback:\n{traceback.format_exc()}")
                            raise

                        finally:
                            print(f"[THREAD] Closing event loop...")
                            loop.close()

                    except Exception as e:
                        import traceback
                        print(f"[THREAD] [ERR] Thread execution error: {e}")
                        print(f"[THREAD] Full traceback:\n{traceback.format_exc()}")
                        raise

                # Execute in thread pool - use run_in_executor for non-blocking
                print(f" Submitting to thread pool...")
                loop = asyncio.get_event_loop()
                report = await loop.run_in_executor(None, run_in_thread)
                print(f"[OK] Thread execution returned")

            else:
                # Non-Windows: Direct async execution
                from test_engine import TestEngine

                def sync_log(message: str):
                    print(f"[TEST] {message}")
                    try:
                        asyncio.ensure_future(broadcast_log(message))
                    except Exception as e:
                        print(f"[BROADCAST ERROR] {e}")

                engine = TestEngine(log_callback=sync_log)
                await broadcast_log(" Launching browser...")

                report = await engine.run_tests(
                    test_cases=test_cases,
                    base_url=project.base_url,
                    report_dir=report_dir,
                    headless=request.headless
                )

            print(f"[OK] Tests completed!")
            print(f"   Passed: {report.passed}")
            print(f"   Failed: {report.failed}")

            await broadcast_log(f"[OK] Test execution completed!")
            await broadcast_log(f"   Passed: {report.passed}, Failed: {report.failed}")

            # Add metadata
            report.id = report_id
            report.project_id = project.id
            report.project_name = project.name
            report.executed_at = datetime.now().isoformat()

            # Save report
            storage.save_report(report)
            print(f"[OK] Report saved: {report_id}")

            # Generate HTML report if enabled
            if HTML_REPORTS_ENABLED:
                try:
                    html_path = f"{report_dir}/report.html"
                    generate_html_report(report, html_path)
                    await broadcast_log(f" HTML report generated")
                except Exception as e:
                    print(f"[WARN] HTML report generation failed: {e}")
                    await broadcast_log(f"[WARN] HTML report generation failed: {e}")

            await broadcast_log(f" Report ID: {report_id}")

        except Exception as e:
            import traceback
            error_msg = str(e)
            tb = traceback.format_exc()
            print(f"\n{'='*60}")
            print(f"[ERR] TEST EXECUTION FAILED")
            print(f"{'='*60}")
            print(f"Error: {error_msg}")
            print(f"Traceback:\n{tb}")
            print(f"{'='*60}\n")

            await broadcast_log(f"[ERR] Test execution failed: {error_msg}")
            await broadcast_log(f"Check server console for full error details")

            # Save a failed report so the user can see what happened
            try:
                failed_report = TestReport(
                    id=report_id,
                    project_id=project.id,
                    project_name=project.name,
                    executed_at=datetime.now().isoformat(),
                    total_tests=len(test_cases),
                    passed=0,
                    failed=len(test_cases),
                    skipped=0,
                    duration=0,
                    results=[
                        TestResult(
                            test_case_id=tc.id,
                            test_case_name=tc.name,
                            status="failed",
                            duration=0,
                            error_message=f"Execution error: {error_msg}",
                            screenshot_path=None,
                            logs=[f"Error: {error_msg}"]
                        ) for tc in test_cases
                    ]
                )
                storage.save_report(failed_report)
                print(f"[OK] Failed report saved: {report_id}")
                await broadcast_log(f" Failed report saved: {report_id}")
            except Exception as save_err:
                print(f"[ERR] Could not save failed report: {save_err}")


    # Start test execution in background
    print(f" Creating background task for test execution...", flush=True)
    asyncio.create_task(run_test_suite())
    print(f"[OK] Background task created, returning response...", flush=True)

    return {
        "message": "Test execution started",
        "report_id": report_id
    }


# ============ Reports ============
@app.get("/api/reports", response_model=List[TestReport])
async def get_reports():
    """Get all test reports"""
    return storage.get_all_reports()


@app.get("/api/reports/{report_id}", response_model=TestReport)
async def get_report(report_id: str):
    """Get a specific report"""
    report = storage.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/reports/{report_id}/html")
async def get_html_report(report_id: str):
    """Get HTML report"""
    if not HTML_REPORTS_ENABLED:
        raise HTTPException(status_code=501, detail="HTML reports are disabled. Install pandas to enable.")
    
    html_path = f"data/reports/{report_id}/report.html"
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="HTML report not found")
    return FileResponse(html_path)


@app.get("/api/reports/{report_id}/screenshot/{filename:path}")
async def get_screenshot(report_id: str, filename: str):
    """Get screenshot from report - handles multiple screenshot locations"""
    # Get just the basename for checking multiple directories
    basename = os.path.basename(filename)

    # List of possible paths to check
    possible_paths = [
        f"data/reports/{report_id}/{filename}",  # Traditional path
        f"data/reports/{report_id}/{basename}",  # Traditional with basename
        filename,  # Full path stored in report
        f"data/agent_knowledge/screenshots/{basename}",  # Agent screenshots (from backend root)
        f"app/data/agent_knowledge/screenshots/{basename}",  # Agent screenshots (from backend/app)
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return FileResponse(path)

    # Log what we tried for debugging
    print(f"Screenshot not found for {filename}. Tried paths:")
    for p in possible_paths:
        print(f"  - {p} (exists: {os.path.exists(p)})")
    raise HTTPException(status_code=404, detail="Screenshot not found")


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: str):
    """Delete a test report"""
    report = storage.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete report from storage
    storage.delete_report(report_id)

    # Also delete report directory if it exists
    report_dir = f"data/reports/{report_id}"
    if os.path.exists(report_dir):
        import shutil
        shutil.rmtree(report_dir)

    return {"message": "Report deleted successfully", "report_id": report_id}


@app.get("/api/projects/{project_id}/test-cases", response_model=List[TestCase])
async def get_project_test_cases(project_id: str):
    """Get all test cases for a project"""
    project = storage.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.test_cases


@app.get("/api/projects/{project_id}/reports", response_model=List[TestReport])
async def get_project_reports(project_id: str):
    """Get all reports for a specific project"""
    all_reports = storage.get_all_reports()
    project_reports = [r for r in all_reports if r.project_id == project_id]
    return project_reports


# ============ GHERKIN GENERATION (NEW) ============

class GenerateGherkinTextRequest(BaseModel):
    brd_content: str
    project_id: Optional[str] = None
    project_context: Optional[str] = None
    end_to_end: bool = False
    folder_id: Optional[str] = None  # Optional folder to place generated feature

@app.post("/api/gherkin/generate-from-text")
async def generate_gherkin_from_text(request: GenerateGherkinTextRequest):
    """Generate Gherkin test scenarios from BRD text"""
    try:
        print(f" Mode: {'E2E (15-25)' if request.end_to_end else 'Focused (10-15)'}")

        # Fetch project UI config and credentials if project_id provided
        ui_config = None
        base_url = None
        credentials = None
        if request.project_id:
            project = storage.get_project(request.project_id)
            if project:
                ui_config = project.ui_config
                base_url = project.base_url
                # Get credentials list from project
                credentials = getattr(project, 'credentials', None)
                if ui_config and ui_config.frameworks:
                    print(f"   UI Frameworks: {', '.join(ui_config.frameworks)}")
                if credentials and len(credentials) > 0:
                    print(f"   Available Roles: {', '.join([c.role_name for c in credentials])}")

        generator = AIGherkinGenerator()
        response = generator.generate_gherkin(
            brd_content=request.brd_content,
            project_context=request.project_context,
            base_url=base_url,
            end_to_end=request.end_to_end,
            ui_config=ui_config,
            credentials=credentials
        )

        # Save to storage
        feature_dict = gherkin_storage.save_feature(response.feature, request.project_id, request.folder_id)

        return {
            "feature": feature_dict,
            "brd_summary": response.brd_summary,
            "suggestions": response.suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/gherkin/generate-from-file")
async def generate_gherkin_from_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    project_context: Optional[str] = Form(None),
    end_to_end: bool = Form(False),
    folder_id: Optional[str] = Form(None)
):
    """Generate Gherkin test scenarios from uploaded file"""
    try:
        import uuid as uuid_module

        print(f" Processing: {file.filename}")
        print(f"   Mode: {'End-to-End (15-25 scenarios)' if end_to_end else 'Focused (10-15 scenarios)'}")

        # Fetch project UI config and credentials if project_id provided
        ui_config = None
        base_url = None
        credentials = None
        if project_id:
            project = storage.get_project(project_id)
            if project:
                ui_config = project.ui_config
                base_url = project.base_url
                # Get credentials list from project
                credentials = getattr(project, 'credentials', None)
                if ui_config and ui_config.frameworks:
                    print(f"   UI Frameworks: {', '.join(ui_config.frameworks)}")
                if credentials and len(credentials) > 0:
                    print(f"   Available Roles: {', '.join([c.role_name for c in credentials])}")

        # Save temp file
        temp_file = f"temp_{uuid_module.uuid4()}_{file.filename}"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # Extract text
            brd_content = extract_text_from_file(temp_file)
            print(f"   Extracted {len(brd_content)} characters")

            # Generate
            generator = AIGherkinGenerator()
            response = generator.generate_gherkin(
                brd_content=brd_content,
                project_context=project_context,
                base_url=base_url,
                end_to_end=end_to_end,
                ui_config=ui_config,
                credentials=credentials
            )

            # Save
            feature_dict = gherkin_storage.save_feature(response.feature, project_id, folder_id)

            print(f"    Generated {len(response.feature.scenarios)} scenarios")

            return {
                "feature": feature_dict,
                "brd_summary": response.brd_summary,
                "suggestions": response.suggestions
            }
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    except Exception as e:
        print(f"[ERR] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ GHERKIN EXECUTION (NEW) ============

class ExecuteGherkinRequest(BaseModel):
    feature_id: str
    headless: bool = True
    tags: List[str] = None

@app.post("/api/gherkin/execute")
async def execute_gherkin_feature(request: ExecuteGherkinRequest):
    """Execute Gherkin feature with optional tag filtering"""
    try:
        # Load feature
        feature = gherkin_storage.load_feature(request.feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Get project for base URL
        feature_data = gherkin_storage.load_feature_dict(request.feature_id)
        project = None
        if feature_data and feature_data.get("project_id"):
            project = storage.get_project(feature_data["project_id"])
        
        base_url = project.base_url if project else ""
        
        # Create report directory (use data/reports for consistency with Storage)
        report_id = f"gherkin_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_dir = f"data/reports/{report_id}"
        os.makedirs(report_dir, exist_ok=True)
        
        # Log callback
        def log_callback(message: str):
            asyncio.create_task(broadcast_log(message))
        
        # Execute
        async def run_gherkin_suite():
            try:
                await broadcast_log(" Starting Gherkin test execution...")
                
                if sys.platform == 'win32':
                    # Windows execution
                    import concurrent.futures
                    loop = asyncio.get_event_loop()
                    
                    # Extract project credentials for Windows execution
                    project_creds_win = {}
                    auto_test_data_win = True
                    if project:
                        project_creds_win = {
                            'test_username': project.test_username,
                            'test_password': project.test_password,
                            'test_email': getattr(project, 'test_email', None),
                            'test_admin_username': project.test_admin_username,
                            'test_admin_password': project.test_admin_password,
                        }
                        auto_test_data_win = getattr(project, 'auto_test_data', True)
                    
                    result = await loop.run_in_executor(
                        None,
                        lambda: run_gherkin_windows_safe(
                            feature,
                            base_url,
                            request.headless,
                            request.tags,
                            loop,
                            broadcast_log,
                            project_creds_win,
                            auto_test_data_win
                        )
                    )
                else:
                    # Normal execution - extract project credentials
                    project_creds = {}
                    auto_test_data = True
                    if project:
                        project_creds = {
                            'test_username': project.test_username,
                            'test_password': project.test_password,
                            'test_email': getattr(project, 'test_email', None),
                            'test_admin_username': project.test_admin_username,
                            'test_admin_password': project.test_admin_password,
                        }
                        auto_test_data = getattr(project, 'auto_test_data', True)
                    
                    executor = GherkinExecutor(
                        base_url=base_url,
                        headless=request.headless,
                        project_credentials=project_creds,
                        auto_test_data=auto_test_data
                    )
                    executor.setup()
                    try:
                        result = executor.execute_feature(feature, tag_filter=request.tags)
                    finally:
                        executor.teardown()
                
                # Save result
                result_dict = result.to_dict()
                result_dict["feature_id"] = request.feature_id
                result_dict["report_id"] = report_id
                gherkin_storage.save_execution_result(result_dict)
                
                await broadcast_log(f"[OK] Execution complete! Passed: {result.passed}, Failed: {result.failed}")
                
            except Exception as e:
                await broadcast_log(f"[ERR] Execution failed: {str(e)}")
        
        asyncio.create_task(run_gherkin_suite())
        
        return {
            "message": "Gherkin test execution started",
            "report_id": report_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gherkin/features/{feature_id}/tags")
async def get_feature_tags(feature_id: str):
    """Get all tags from a feature"""
    try:
        feature = gherkin_storage.load_feature(feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Collect unique tags
        all_tags = set()
        for scenario in feature.scenarios:
            all_tags.update(scenario.tags)
        
        return {
            "feature_id": feature_id,
            "feature_name": feature.name,
            "tags": sorted(list(all_tags))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gherkin/features/{feature_id}")
async def get_gherkin_feature(feature_id: str):
    """Get a Gherkin feature"""
    feature_dict = gherkin_storage.load_feature_dict(feature_id)
    if not feature_dict:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature_dict


@app.put("/api/gherkin/features/{feature_id}")
async def update_gherkin_feature(feature_id: str, feature_data: dict):
    """Update a Gherkin feature (edit steps, scenarios, etc.)"""
    existing = gherkin_storage.load_feature_dict(feature_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Feature not found")

    project_id = existing.get('project_id')

    from models_gherkin import GherkinFeature, GherkinScenario, GherkinStep, StepKeyword

    scenarios = []
    for s in feature_data.get('scenarios', []):
        steps = []
        for step in s.get('steps', []):
            # Handle keyword as string or object {value: 'Given'}
            kw_raw = step.get('keyword', 'Given')
            if isinstance(kw_raw, dict):
                kw = kw_raw.get('value', 'Given').title()
            else:
                kw = str(kw_raw).title()
            keyword = StepKeyword(kw) if kw in ['Given', 'When', 'Then', 'And', 'But'] else StepKeyword.GIVEN
            steps.append(GherkinStep(keyword=keyword, text=step.get('text', '')))
        scenarios.append(GherkinScenario(
            name=s.get('name', ''),
            description=s.get('description', ''),
            tags=s.get('tags', []),
            steps=steps
        ))

    feature = GherkinFeature(
        id=feature_id,
        name=feature_data.get('name', existing.get('name')),
        description=feature_data.get('description', ''),
        scenarios=scenarios,
        background=None
    )

    saved = gherkin_storage.save_feature(feature, project_id)
    return saved


@app.get("/api/projects/{project_id}/gherkin-features")
async def get_project_gherkin_features(project_id: str):
    """Get all Gherkin features for a project"""
    features = gherkin_storage.list_features(project_id=project_id)
    return {"features": features}


# Helper for Windows Gherkin execution
def run_gherkin_windows_safe(feature, base_url, headless, tags, main_loop, broadcast_func,
                              project_credentials=None, auto_test_data=True):
    """Windows-safe Gherkin executor"""
    import queue
    
    def thread_safe_log(message: str):
        print(f"[GHERKIN] {message}")
        try:
            future = asyncio.run_coroutine_threadsafe(broadcast_func(message), main_loop)
        except:
            pass
    
    def execute_in_thread():
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            executor = GherkinExecutor(
                base_url=base_url,
                headless=headless,
                project_credentials=project_credentials or {},
                auto_test_data=auto_test_data
            )
            executor.setup()
            try:
                thread_safe_log(f"Running {len(feature.scenarios)} scenarios...")
                result = executor.execute_feature(feature, tag_filter=tags)
                return result
            finally:
                executor.teardown()
        finally:
            loop.close()
    
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(execute_in_thread)
        return future.result()
    
class LinkFeatureToProjectRequest(BaseModel):
    feature_id: str
    project_id: str
    folder_id: Optional[str] = None

@app.post("/api/gherkin/link-to-project")
async def link_feature_to_project(request: LinkFeatureToProjectRequest):
    """Link a Gherkin feature to a project"""
    try:
        # Load the feature
        feature_dict = gherkin_storage.load_feature_dict(request.feature_id)
        if not feature_dict:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Update project_id
        feature_dict['project_id'] = request.project_id
        
        # Save back with folder_id
        feature = gherkin_storage.load_feature(request.feature_id)
        gherkin_storage.save_feature(feature, request.project_id, request.folder_id)
        
        return {"message": "Feature linked to project successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    

def delete_feature(self, feature_id: str):
    """Delete a feature"""
    file_path = os.path.join(self.features_folder, f"{feature_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)


@app.get("/api/gherkin/features/{feature_id}/export")
async def export_feature(feature_id: str):
    """Export a single feature as .feature file"""
    try:
        feature = gherkin_storage.load_feature(feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Generate .feature file content
        gherkin_content = feature.to_gherkin()
        
        # Create filename
        filename = f"{feature.name.replace(' ', '_')}.feature"
        
        # Return as downloadable file
        return Response(
            content=gherkin_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gherkin/features/{feature_id}/export/json")
async def export_feature_json(feature_id: str):
    """Export a single feature as JSON"""
    try:
        feature_dict = gherkin_storage.load_feature_dict(feature_id)
        if not feature_dict:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        # Create filename
        filename = f"{feature_dict['name'].replace(' ', '_')}.json"
        
        # Return as JSON file
        import json
        json_content = json.dumps(feature_dict, indent=2, ensure_ascii=False)
        
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}/gherkin-features/export")
async def export_project_features(project_id: str, format: str = "zip"):
    """
    Export all Gherkin features for a project
    format: 'zip' (default) or 'json'
    """
    try:
        features = gherkin_storage.list_features(project_id=project_id)
        
        if not features:
            raise HTTPException(status_code=404, detail="No features found for this project")
        
        project = storage.get_project(project_id)
        project_name = project.name if project else "project"
        
        if format == "json":
            # Export as single JSON file with all features
            import json
            
            all_features = []
            for feature_info in features:
                feature_dict = gherkin_storage.load_feature_dict(feature_info['id'])
                if feature_dict:
                    all_features.append(feature_dict)
            
            json_content = json.dumps({
                "project_name": project_name,
                "project_id": project_id,
                "exported_at": datetime.now().isoformat(),
                "features": all_features
            }, indent=2, ensure_ascii=False)
            
            filename = f"{project_name.replace(' ', '_')}_features.json"
            
            return Response(
                content=json_content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        
        else:  # format == "zip"
            # Create ZIP file with all .feature files
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for feature_info in features:
                    feature = gherkin_storage.load_feature(feature_info['id'])
                    if feature:
                        gherkin_content = feature.to_gherkin()
                        filename = f"{feature.name.replace(' ', '_')}.feature"
                        zip_file.writestr(filename, gherkin_content)
                
                # Add a README
                readme_content = f"""# {project_name} - Gherkin Features

Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Features: {len(features)}

## Files Included:
{chr(10).join([f"- {f['name']}.feature ({f['scenario_count']} scenarios)" for f in features])}

## How to Use:
These .feature files can be used with:
- Cucumber (Java/JavaScript)
- Behave (Python)
- SpecFlow (.NET)
- Or any BDD testing framework

## GhostQA
Generated by GhostQA - AI-Powered BDD Test Generator
"""
                zip_file.writestr("README.md", readme_content)
            
            zip_buffer.seek(0)
            filename = f"{project_name.replace(' ', '_')}_features.zip"
            
            return StreamingResponse(
                io.BytesIO(zip_buffer.getvalue()),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DELETE endpoint 
@app.delete("/api/gherkin/features/{feature_id}")
async def delete_gherkin_feature(feature_id: str):
    """Delete a Gherkin feature - ultra simple"""
    try:
        # Try to find the features folder
        # Adjust this path based on your project structure
        possible_paths = [
            Path("data/features"),              # If running from project root
            Path("backend/data/features"),      # If in backend folder
            Path("./data/features"),            # Current directory
        ]
        
        features_folder = None
        for path in possible_paths:
            print(f" Checking: {path.absolute()}")
            if path.exists():
                features_folder = path
                print(f"[OK] Found features folder: {features_folder.absolute()}")
                break
        
        if not features_folder:
            raise HTTPException(
                status_code=500,
                detail="Could not find features folder"
            )
        
        # Construct feature file path
        feature_file = features_folder / f"{feature_id}.json"
        
        print(f" Looking for: {feature_file.absolute()}")
        
        # Check if exists
        if not feature_file.exists():
            # List what files DO exist
            print(f" Files in folder:")
            for f in features_folder.glob("*.json"):
                print(f"   - {f.name}")
            
            raise HTTPException(
                status_code=404,
                detail=f"Feature not found: {feature_id}"
            )
        
        # Get feature name before deleting
        feature_name = "Unknown"
        try:
            with open(feature_file, 'r', encoding='utf-8') as f:
                feature_data = json.load(f)
                feature_name = feature_data.get('name', 'Unknown')
        except Exception:
            pass
        
        # Delete the file
        feature_file.unlink()
        
        print(f"[OK] Deleted: {feature_id} ({feature_name})")
        
        return {
            "message": "Feature deleted successfully",
            "feature_id": feature_id,
            "feature_name": feature_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERR] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete feature: {str(e)}"
        )

# ============ TRADITIONAL TEST CASES (NEW) ============

class GenerateTraditionalTextRequest(BaseModel):
    brd_content: str
    project_id: Optional[str] = None
    project_context: Optional[str] = None
    end_to_end: bool = False


@app.post("/api/traditional/generate-from-text")
async def generate_traditional_from_text(request: GenerateTraditionalTextRequest):
    """Generate Traditional table format test cases from BRD text"""
    try:
        print(f" Mode: {'E2E (comprehensive)' if request.end_to_end else 'Focused (10-15)'}")

        # Fetch project UI config and credentials if project_id provided
        ui_config = None
        base_url = None
        credentials = None
        if request.project_id:
            project = storage.get_project(request.project_id)
            if project:
                ui_config = project.ui_config
                base_url = project.base_url
                # Get credentials list from project
                credentials = getattr(project, 'credentials', None)
                if ui_config and ui_config.frameworks:
                    print(f"   UI Frameworks: {', '.join(ui_config.frameworks)}")
                if credentials and len(credentials) > 0:
                    print(f"   Available Roles: {', '.join([c.role_name for c in credentials])}")

        generator = AIGherkinGenerator()
        response = generator.generate_traditional(
            brd_content=request.brd_content,
            project_context=request.project_context,
            base_url=base_url,
            end_to_end=request.end_to_end,
            ui_config=ui_config,
            credentials=credentials
        )

        # Save to storage
        suite_dict = gherkin_storage.save_traditional_suite(response["test_suite"], request.project_id)

        return {
            "test_suite": suite_dict,
            "brd_summary": response["brd_summary"],
            "suggestions": response["suggestions"]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/traditional/generate-from-file")
async def generate_traditional_from_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    project_context: Optional[str] = Form(None),
    end_to_end: bool = Form(False)
):
    """Generate Traditional table format test cases from uploaded file"""
    try:
        import uuid as uuid_module

        print(f" Processing: {file.filename}")
        print(f"   Mode: {'End-to-End (comprehensive)' if end_to_end else 'Focused (10-15 test cases)'}")

        # Fetch project UI config and credentials if project_id provided
        ui_config = None
        base_url = None
        credentials = None
        if project_id:
            project = storage.get_project(project_id)
            if project:
                ui_config = project.ui_config
                base_url = project.base_url
                # Get credentials list from project
                credentials = getattr(project, 'credentials', None)
                if ui_config and ui_config.frameworks:
                    print(f"   UI Frameworks: {', '.join(ui_config.frameworks)}")
                if credentials and len(credentials) > 0:
                    print(f"   Available Roles: {', '.join([c.role_name for c in credentials])}")

        # Save temp file
        temp_file = f"temp_{uuid_module.uuid4()}_{file.filename}"
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # Extract text
            brd_content = extract_text_from_file(temp_file)
            print(f"   Extracted {len(brd_content)} characters")

            # Generate
            generator = AIGherkinGenerator()
            response = generator.generate_traditional(
                brd_content=brd_content,
                project_context=project_context,
                base_url=base_url,
                end_to_end=end_to_end,
                ui_config=ui_config,
                credentials=credentials
            )

            # Save
            suite_dict = gherkin_storage.save_traditional_suite(response["test_suite"], project_id)

            print(f"    Generated {len(response['test_suite'].test_cases)} test cases")

            return {
                "test_suite": suite_dict,
                "brd_summary": response["brd_summary"],
                "suggestions": response["suggestions"]
            }
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    except Exception as e:
        print(f"[ERR] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/traditional/suites/{suite_id}")
async def get_traditional_suite(suite_id: str):
    """Get a Traditional test suite"""
    suite_dict = gherkin_storage.load_traditional_suite_dict(suite_id)
    if not suite_dict:
        raise HTTPException(status_code=404, detail="Test suite not found")
    return suite_dict


@app.get("/api/projects/{project_id}/traditional-suites")
async def get_project_traditional_suites(project_id: str):
    """Get all Traditional test suites for a project"""
    suites = gherkin_storage.list_traditional_suites(project_id=project_id)
    return {"suites": suites}


class LinkTraditionalToProjectRequest(BaseModel):
    suite_id: str
    project_id: str


@app.post("/api/traditional/link-to-project")
async def link_traditional_to_project(request: LinkTraditionalToProjectRequest):
    """Link a Traditional test suite to a project"""
    try:
        # Load the suite
        suite_dict = gherkin_storage.load_traditional_suite_dict(request.suite_id)
        if not suite_dict:
            raise HTTPException(status_code=404, detail="Test suite not found")

        # Update project_id
        suite_dict['project_id'] = request.project_id

        # Save back
        suite = gherkin_storage.load_traditional_suite(request.suite_id)
        gherkin_storage.save_traditional_suite(suite, request.project_id)

        return {"message": "Test suite linked to project successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/traditional/suites/{suite_id}/export/csv")
async def export_traditional_csv(suite_id: str):
    """Export a Traditional test suite as CSV"""
    try:
        suite = gherkin_storage.load_traditional_suite(suite_id)
        if not suite:
            raise HTTPException(status_code=404, detail="Test suite not found")

        # Generate CSV content
        csv_content = suite.to_csv()

        # Create filename
        filename = f"{suite.name.replace(' ', '_')}.csv"

        # Return as downloadable file
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/traditional/suites/{suite_id}/export/json")
async def export_traditional_json(suite_id: str):
    """Export a Traditional test suite as JSON"""
    try:
        suite_dict = gherkin_storage.load_traditional_suite_dict(suite_id)
        if not suite_dict:
            raise HTTPException(status_code=404, detail="Test suite not found")

        # Create filename
        filename = f"{suite_dict['name'].replace(' ', '_')}.json"

        # Return as JSON file
        json_content = json.dumps(suite_dict, indent=2, ensure_ascii=False)

        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}/traditional-suites/export")
async def export_project_traditional_suites(project_id: str, format: str = "csv"):
    """
    Export all Traditional test suites for a project
    format: 'csv' (default), 'json', or 'zip'
    """
    try:
        suites = gherkin_storage.list_traditional_suites(project_id=project_id)

        if not suites:
            raise HTTPException(status_code=404, detail="No test suites found for this project")

        project = storage.get_project(project_id)
        project_name = project.name if project else "project"

        if format == "json":
            # Export as single JSON file with all suites
            all_suites = []
            for suite_info in suites:
                suite_dict = gherkin_storage.load_traditional_suite_dict(suite_info['id'])
                if suite_dict:
                    all_suites.append(suite_dict)

            json_content = json.dumps({
                "project_name": project_name,
                "project_id": project_id,
                "exported_at": datetime.now().isoformat(),
                "test_suites": all_suites
            }, indent=2, ensure_ascii=False)

            filename = f"{project_name.replace(' ', '_')}_traditional_suites.json"

            return Response(
                content=json_content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

        elif format == "zip":
            # Create ZIP file with all CSV files
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for suite_info in suites:
                    suite = gherkin_storage.load_traditional_suite(suite_info['id'])
                    if suite:
                        csv_content = suite.to_csv()
                        filename = f"{suite.name.replace(' ', '_')}.csv"
                        zip_file.writestr(filename, csv_content)

                # Add a README
                readme_content = f"""# {project_name} - Traditional Test Cases

Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Test Suites: {len(suites)}

## Files Included:
{chr(10).join([f"- {s['name']}.csv ({s['test_case_count']} test cases)" for s in suites])}

## CSV Columns:
- Test Case No: Sequential identifier
- Scenario Name: Test scenario description
- Precondition: Prerequisites before test execution
- Steps: Test steps to execute
- Expected Outcome: Expected results
- Post Condition: System state after test
- Tags: Test categorization tags

## GhostQA
Generated by GhostQA - AI-Powered Test Case Generator
"""
                zip_file.writestr("README.md", readme_content)

            zip_buffer.seek(0)
            filename = f"{project_name.replace(' ', '_')}_traditional_suites.zip"

            return StreamingResponse(
                io.BytesIO(zip_buffer.getvalue()),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

        else:  # format == "csv" - combine all into single CSV
            import csv as csv_module
            output = io.StringIO()
            writer = csv_module.writer(output)

            # Header
            writer.writerow([
                'Suite Name',
                'Test Case No',
                'Scenario Name',
                'Precondition',
                'Steps',
                'Expected Outcome',
                'Post Condition',
                'Tags'
            ])

            # All test cases from all suites
            for suite_info in suites:
                suite = gherkin_storage.load_traditional_suite(suite_info['id'])
                if suite:
                    for tc in suite.test_cases:
                        writer.writerow([
                            suite.name,
                            tc.test_case_no,
                            tc.scenario_name,
                            tc.precondition,
                            tc.steps,
                            tc.expected_outcome,
                            tc.post_condition,
                            ', '.join(tc.tags)
                        ])

            csv_content = output.getvalue()
            filename = f"{project_name.replace(' ', '_')}_all_test_cases.csv"

            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/traditional/suites/{suite_id}")
async def delete_traditional_suite(suite_id: str):
    """Delete a Traditional test suite"""
    try:
        suite_dict = gherkin_storage.load_traditional_suite_dict(suite_id)
        if not suite_dict:
            raise HTTPException(status_code=404, detail="Test suite not found")

        suite_name = suite_dict.get('name', 'Unknown')

        # Delete the suite
        gherkin_storage.delete_traditional_suite(suite_id)

        return {
            "message": "Test suite deleted successfully",
            "suite_id": suite_id,
            "suite_name": suite_name
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERR] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete test suite: {str(e)}"
        )


# ============ DATA DICTIONARY VALIDATION ============

from data_dictionary_parser import parse_data_dictionary_file, parse_data_dictionary_raw, parse_csv_content, DataDictionary


@app.post("/api/data-dictionary/generate")
async def generate_from_data_dictionary(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    form_name: Optional[str] = Form(None),
    output_format: str = Form("gherkin")  # "gherkin" or "traditional"
):
    """
    Generate validation test scenarios from a data dictionary file (CSV/Excel).

    The data dictionary should have columns like:
    - field_name (required): Name of the field
    - data_type: string, number, email, date, boolean, etc.
    - required: yes/no, true/false
    - min_length, max_length: Length constraints
    - min_value, max_value: Value range constraints
    - allowed_values: Comma-separated list of valid options
    - pattern: Regex pattern for validation
    - description: Field description
    """
    import uuid as uuid_module
    import traceback as tb

    temp_file = None

    try:
        print(f"\n{'='*60}")
        print(f" DATA DICTIONARY UPLOAD")
        print(f"{'='*60}")
        print(f"File: {file.filename}")
        print(f"Output Format: {output_format}")
        print(f"Form Name: {form_name or 'Not specified'}")

        # Validate file type
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
            )

        # Save temp file
        temp_file = f"temp_{uuid_module.uuid4()}_{file.filename}"
        print(f"   Saving to: {temp_file}")

        content = await file.read()
        print(f"   Read {len(content)} bytes")

        with open(temp_file, "wb") as f:
            f.write(content)
        print(f"   Saved temp file")

        try:
            # Parse data dictionary using RAW mode - let AI interpret the structure
            print(f"   Parsing data dictionary (raw mode - AI interprets structure)...")
            data_dict = parse_data_dictionary_raw(temp_file)
            print(f"   Parsed: {len(data_dict.headers)} columns, {len(data_dict.raw_rows)} rows")
            print(f"   Headers: {data_dict.headers}")

            # Get project context if available
            project_context = None
            base_url = None
            if project_id:
                project = storage.get_project(project_id)
                if project:
                    project_context = f"Project: {project.name}\nDescription: {project.description}"
                    base_url = project.base_url

            # Generate validation scenarios
            print(f"   Initializing AI generator...")
            generator = AIGherkinGenerator()
            print(f"   AI service: {generator.api_type}")

            print(f"   Starting generation...")
            response = generator.generate_from_data_dictionary(
                data_dictionary=data_dict,
                form_name=form_name or data_dict.name,
                project_context=project_context,
                base_url=base_url,
                output_format=output_format
            )
            print(f"   Generation complete!")

            if output_format == "traditional":
                # Save traditional suite
                suite_dict = gherkin_storage.save_traditional_suite(response["test_suite"], project_id)
                print(f"    Generated {len(response['test_suite'].test_cases)} validation test cases")

                return {
                    "type": "traditional",
                    "test_suite": suite_dict,
                    "summary": response["summary"],
                    "suggestions": response["suggestions"],
                    "fields_count": len(data_dict.raw_rows),
                    "columns": data_dict.headers
                }
            else:
                # Save Gherkin feature
                feature_dict = gherkin_storage.save_feature(response["feature"], project_id)
                print(f"    Generated {len(response['feature'].scenarios)} validation scenarios")

                return {
                    "type": "gherkin",
                    "feature": feature_dict,
                    "summary": response["summary"],
                    "suggestions": response["suggestions"],
                    "fields_count": len(data_dict.raw_rows),
                    "columns": data_dict.headers
                }

        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"   Cleaned up temp file")
                except:
                    pass

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERR] Data Dictionary Error: {str(e)}")
        tb.print_exc()
        # Clean up temp file on error
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error processing data dictionary: {str(e)}")


@app.post("/api/data-dictionary/preview")
async def preview_data_dictionary(
    file: UploadFile = File(...)
):
    """
    Preview a data dictionary file to show detected columns and mapping.
    Helps users understand how their file will be interpreted.
    """
    import uuid as uuid_module

    temp_file = None

    try:
        # Validate file type
        allowed_extensions = ['.csv', '.xlsx', '.xls']
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
            )

        # Save temp file
        temp_file = f"temp_{uuid_module.uuid4()}_{file.filename}"
        content = await file.read()
        with open(temp_file, "wb") as f:
            f.write(content)

        try:
            # Parse to get preview using RAW mode
            data_dict = parse_data_dictionary_raw(temp_file)

            # Show first few rows as preview
            preview_rows = []
            for row in data_dict.raw_rows[:10]:
                row_dict = {}
                for i, header in enumerate(data_dict.headers):
                    if i < len(row):
                        row_dict[header] = row[i]
                preview_rows.append(row_dict)

            # Token estimation for user awareness
            estimated_tokens = data_dict.estimate_tokens()
            rows_count = len(data_dict.raw_rows)

            # Determine if batching will be needed:
            # - More than 15 rows = batch (output would be too large)
            # - Token count > 6000 = batch (input too large)
            batch_size = 15
            needs_batching = rows_count > batch_size or estimated_tokens > 6000
            batch_count = (rows_count + batch_size - 1) // batch_size if needs_batching else 1

            token_info = {
                "estimated_tokens": estimated_tokens,
                "needs_batching": needs_batching,
                "batch_count": batch_count,
                "batch_size": batch_size if needs_batching else rows_count,
                "expected_scenarios": f"{rows_count * 2}-{rows_count * 4}"
            }

            message = f"Detected {len(data_dict.headers)} columns and {rows_count} data rows (~{estimated_tokens:,} tokens). "
            if needs_batching:
                message += f"Will process in {batch_count} batches of {batch_size} fields each for optimal results."
            else:
                message += "AI will analyze the structure and generate appropriate validation scenarios."

            return {
                "success": True,
                "filename": file.filename,
                "columns": data_dict.headers,
                "rows_count": rows_count,
                "preview_rows": preview_rows,
                "token_info": token_info,
                "message": message
            }

        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    except HTTPException:
        raise
    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/data-dictionary/template")
async def get_data_dictionary_template():
    """Get a sample CSV template for data dictionary"""
    csv_content = """field_name,data_type,required,min_length,max_length,min_value,max_value,allowed_values,pattern,description
first_name,string,yes,2,50,,,,,"User's first name"
last_name,string,yes,2,50,,,,,"User's last name"
email,email,yes,5,100,,,,,"Email address"
age,number,no,,,18,120,,,"User's age"
phone,string,no,10,15,,,,"^[0-9]{10,15}$","Phone number"
gender,string,no,,,,,Male,Female,Other,,"Gender selection"
password,string,yes,8,128,,,,,"Account password"
"""

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="data_dictionary_template.csv"'
        }
    )


# ============ UI Frameworks ============
@app.get("/api/frameworks")
async def get_available_frameworks():
    """Get list of supported UI frameworks for test generation"""
    return {
        "frameworks": get_all_frameworks()
    }


# ============ Health Check ============
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "html_reports_enabled": HTML_REPORTS_ENABLED,
        "platform": sys.platform
    }

# Global executor reference for stop functionality
_current_executor = None

@app.post("/api/execution/stop")
async def stop_execution(
    force: bool = False,
    current_user: TokenData = Depends(get_current_admin)
):
    """Stop current test execution."""
    global _current_executor

    if _current_executor is None:
        return {"status": "no_execution", "message": "No execution in progress"}

    try:
        if force:
            await _current_executor.force_stop()
            message = "Execution force stopped - browser closed"
        else:
            _current_executor.request_stop()
            message = "Stop requested - will stop after current test"

        await broadcast_log(f"[STOP] {message}")
        return {"status": "stopped", "message": message}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/gherkin/run-autonomous")
async def run_autonomous_gherkin_test(
    request: RunAutonomousTestRequest,
    current_user: TokenData = Depends(get_current_admin)  # Admin only
):
    """
    UNIFIED AUTONOMOUS EXECUTION
    Run Gherkin tests using the unified executor with learning capabilities.
    This endpoint now uses the same execution path as traditional tests,
    enabling knowledge base learning and AI dependency reduction.
    """
    from agent_api import get_executor, _log_connections

    try:
        print(f"\n{'='*80}")
        print(f" UNIFIED AUTONOMOUS EXECUTION (with Learning)")
        print(f"{'='*80}")
        print(f"Feature ID: {request.feature_id}")
        print(f"Headless: {request.headless}")
        print(f"User: {current_user.username} (Admin)")

        # Load the feature
        feature_dict = gherkin_storage.load_feature_dict(request.feature_id)
        if not feature_dict:
            raise HTTPException(status_code=404, detail="Feature not found")

        feature_name = feature_dict.get('name', 'Unknown Feature')
        scenarios = feature_dict.get('scenarios', [])
        print(f"[OK] Loaded feature: {feature_name}")
        print(f"   Scenarios: {len(scenarios)}")

        # Get project details
        base_url = ""
        project_name = "Unknown Project"
        credentials = {}

        if request.project_id:
            project = storage.get_project(request.project_id)
            if project:
                base_url = project.base_url
                project_name = project.name
                print(f"   Base URL: {base_url}")

                # Extract credentials - check both new credentials list and legacy fields
                # First try the new credentials list (multiple roles)
                project_creds_list = getattr(project, 'credentials', [])
                if project_creds_list and len(project_creds_list) > 0:
                    # Use first credential set as default, or find admin/user role
                    for cred in project_creds_list:
                        role = (cred.role_name or '').lower()
                        if role in ['admin', 'administrator']:
                            credentials['admin_username'] = cred.username
                            credentials['admin_password'] = cred.password
                        elif role in ['user', 'standard', 'standard_user', 'test', 'default']:
                            credentials['username'] = cred.username
                            credentials['password'] = cred.password
                        # If no specific role, use as default
                        if not credentials.get('username') and cred.username:
                            credentials['username'] = cred.username
                            credentials['password'] = cred.password
                    print(f"   [OK] Using credentials list ({len(project_creds_list)} role(s))")

                # Fall back to legacy fields if no credentials from list
                if not credentials.get('username') and project.test_username:
                    credentials['username'] = project.test_username
                if not credentials.get('password') and project.test_password:
                    credentials['password'] = project.test_password
                if not credentials.get('admin_username') and project.test_admin_username:
                    credentials['admin_username'] = project.test_admin_username
                if not credentials.get('admin_password') and project.test_admin_password:
                    credentials['admin_password'] = project.test_admin_password

                if credentials:
                    uname = credentials.get('username') or credentials.get('admin_username', 'N/A')
                    print(f"   [OK] Credentials ready: {uname[:3] if uname else 'N/A'}***")
                else:
                    print(f"   [WARN] No credentials configured")

        # Get the unified executor (with knowledge base and learning)
        global _current_executor
        executor = get_executor()
        _current_executor = executor  # Store for stop functionality

        # Convert feature to unified test cases
        test_cases = executor.convert_gherkin_feature(feature_dict)

        # Apply scenario filter if provided
        if request.scenario_filter:
            test_cases = [tc for tc in test_cases if tc.scenario_name in request.scenario_filter]

        print(f"   Test cases to execute: {len(test_cases)}")

        # Set up log callback for WebSocket broadcasting
        # Use sync callback that schedules async broadcast
        def sync_log_callback(message: str):
            # Print to console for debugging
            print(f"[WS-LOG] {message}")
            # Schedule WebSocket broadcast
            async def send_to_clients():
                for ws in active_connections[:]:  # Copy list to avoid modification during iteration
                    try:
                        await ws.send_text(message)
                    except Exception:
                        pass
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(send_to_clients())
            except Exception as e:
                print(f"[WS-LOG-ERR] {e}")

        executor.set_callbacks(log_callback=sync_log_callback)

        # Create report ID and directory
        report_id = f"autonomous_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # Use same directory structure as Storage class for consistency
        report_dir = f"data/reports/{report_id}"
        os.makedirs(report_dir, exist_ok=True)
        print(f"   [OK] Report directory: {report_dir}")

        # Execute using the unified executor (with learning!)
        from agent import ExecutionMode
        report = await executor.execute(
            test_cases=test_cases,
            base_url=base_url,
            project_id=request.project_id or "gherkin_run",
            project_name=project_name,
            headless=request.headless,
            execution_mode=ExecutionMode.AUTONOMOUS,
            credentials=credentials if credentials else None
        )

        print(f"\n{'='*80}")
        print(f" EXECUTION COMPLETE (Knowledge Updated)")
        print(f"{'='*80}")
        print(f"Total: {report.total_tests}")
        print(f"Passed: {report.passed} [OK]")
        print(f"Failed: {report.failed} [ERR]")
        print(f"AI Dependency: {report.ai_dependency_percent:.1f}%")
        print(f"New Selectors Learned: {report.new_selectors_learned}")
        print(f"Duration: {report.duration_seconds:.2f}s")
        print(f"{'='*80}\n")

        # SAVE REPORT TO STORAGE
        try:
            # Convert UnifiedExecutionReport to TestReport format for storage
            test_report = TestReport(
                id=report_id,
                project_id=request.project_id or "gherkin_run",
                project_name=project_name,
                executed_at=report.executed_at,
                total_tests=report.total_tests,
                passed=report.passed,
                failed=report.failed,
                duration=report.duration_seconds,
                results=[
                    TestResult(
                        test_case_id=r.test_id,
                        test_case_name=r.test_name,
                        status=r.status,
                        duration=r.duration_ms / 1000.0,  # Convert ms to seconds
                        error_message=r.error_message,
                        screenshot_path=r.screenshot_path,
                        logs=r.logs or []
                    )
                    for r in report.results
                ]
            )
            storage.save_report(test_report)
            print(f"   [OK] Report saved to storage: {report_id}")
        except Exception as save_err:
            print(f"   [WARN] Could not save report: {save_err}")

        # Return in the expected format for backward compatibility
        return {
            "success": True,
            "report_id": report_id,
            "feature_name": feature_name,
            "total_scenarios": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "total_duration": report.duration_seconds,
            "ai_dependency_percent": report.ai_dependency_percent,
            "new_selectors_learned": report.new_selectors_learned,
            "scenario_results": [
                {
                    "scenario_name": r.test_name,
                    "status": r.status,
                    "duration": r.duration_ms / 1000,
                    "error_message": r.error_message,
                    "ai_decisions": []
                }
                for r in report.results
            ],
            "result": {
                "total_scenarios": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "total_duration": report.duration_seconds
            }
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERR] Unified autonomous execution error:")
        print(error_detail)
        raise HTTPException(
            status_code=500,
            detail=f"Autonomous execution failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
