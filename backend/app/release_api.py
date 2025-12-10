"""
Release Management API Endpoints
Handles releases, environments, iterations, and metrics
"""

from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
import os
import json

from release_models import (
    Release, Environment, ReleaseProject, ReleaseIteration,
    CreateReleaseRequest, UpdateReleaseRequest, AddEnvironmentRequest,
    AddProjectToReleaseRequest, RunReleaseTestsRequest, ReleaseMetrics,
    ReleaseStatus, EnvironmentType
)
from models import TestCase
from storage import Storage

router = APIRouter(prefix="/api/releases", tags=["releases"])

# Simple JSON storage for releases
RELEASES_FILE = "data/releases.json"


def load_releases() -> List[Release]:
    """Load releases from JSON file"""
    if not os.path.exists(RELEASES_FILE):
        os.makedirs(os.path.dirname(RELEASES_FILE), exist_ok=True)
        return []
    
    try:
        with open(RELEASES_FILE, 'r') as f:
            data = json.load(f)
            return [Release(**r) for r in data]
    except:
        return []


def save_releases(releases: List[Release]):
    """Save releases to JSON file"""
    os.makedirs(os.path.dirname(RELEASES_FILE), exist_ok=True)
    with open(RELEASES_FILE, 'w') as f:
        json.dump([r.dict() for r in releases], f, indent=2)


def get_release_by_id(release_id: str) -> Release:
    """Get release by ID"""
    releases = load_releases()
    release = next((r for r in releases if r.id == release_id), None)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


def update_release_metrics(release: Release):
    """Calculate and update release metrics"""
    if not release.iterations:
        release.overall_pass_rate = 0.0
        release.deployment_ready = False
        return
    
    # Calculate overall pass rate
    total_passed = sum(i.passed for i in release.iterations)
    total_tests = sum(i.total_tests for i in release.iterations)
    release.overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0
    
    # Check deployment readiness (all environments must have 100% pass rate in latest iteration)
    env_ready = {}
    for env in release.environments:
        env_iterations = [i for i in release.iterations if i.environment_id == env.id]
        if env_iterations:
            latest = max(env_iterations, key=lambda x: x.iteration_number)
            env_ready[env.id] = latest.pass_rate >= 100.0
        else:
            env_ready[env.id] = False
    
    release.deployment_ready = all(env_ready.values()) and len(env_ready) > 0


# ============ Release CRUD ============

@router.post("", response_model=Release)
async def create_release(request: CreateReleaseRequest):
    """Create a new release"""
    releases = load_releases()
    
    release = Release(
        id=str(uuid.uuid4()),
        name=request.name,
        version=request.version,
        description=request.description,
        target_date=request.target_date,
        status=ReleaseStatus.DRAFT,
        environments=[],
        projects=[],
        iterations=[],
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        total_iterations=0,
        overall_pass_rate=0.0,
        deployment_ready=False
    )
    
    releases.append(release)
    save_releases(releases)
    return release


@router.get("", response_model=List[Release])
async def get_releases():
    """Get all releases"""
    return load_releases()


@router.get("/{release_id}", response_model=Release)
async def get_release(release_id: str):
    """Get a specific release"""
    return get_release_by_id(release_id)


@router.put("/{release_id}", response_model=Release)
async def update_release(release_id: str, request: UpdateReleaseRequest):
    """Update a release"""
    releases = load_releases()
    release = next((r for r in releases if r.id == release_id), None)
    
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    if request.name:
        release.name = request.name
    if request.version:
        release.version = request.version
    if request.description is not None:
        release.description = request.description
    if request.status:
        release.status = request.status
    if request.target_date is not None:
        release.target_date = request.target_date
    
    release.updated_at = datetime.now().isoformat()
    
    save_releases(releases)
    return release


@router.delete("/{release_id}")
async def delete_release(release_id: str):
    """Delete a release"""
    releases = load_releases()
    releases = [r for r in releases if r.id != release_id]
    save_releases(releases)
    return {"message": "Release deleted successfully"}


# ============ Environment Management ============

@router.post("/{release_id}/environments", response_model=Environment)
async def add_environment(release_id: str, request: AddEnvironmentRequest):
    """Add environment to release"""
    releases = load_releases()
    release = next((r for r in releases if r.id == release_id), None)
    
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    environment = Environment(
        id=str(uuid.uuid4()),
        name=request.name,
        type=request.type,
        base_url=request.base_url,
        description=request.description,
        config=request.config
    )
    
    release.environments.append(environment)
    release.updated_at = datetime.now().isoformat()
    
    save_releases(releases)
    return environment


@router.delete("/{release_id}/environments/{environment_id}")
async def remove_environment(release_id: str, environment_id: str):
    """Remove environment from release"""
    releases = load_releases()
    release = next((r for r in releases if r.id == release_id), None)
    
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    release.environments = [e for e in release.environments if e.id != environment_id]
    # Also remove related iterations
    release.iterations = [i for i in release.iterations if i.environment_id != environment_id]
    release.updated_at = datetime.now().isoformat()
    
    save_releases(releases)
    return {"message": "Environment removed successfully"}


# ============ Project Management ============

@router.post("/{release_id}/projects", response_model=ReleaseProject)
async def add_project_to_release(release_id: str, request: AddProjectToReleaseRequest):
    """Add project to release"""
    releases = load_releases()
    release = next((r for r in releases if r.id == release_id), None)
    
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    # Get project details
    storage = Storage()
    project = storage.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    release_project = ReleaseProject(
        project_id=project.id,
        project_name=project.name,
        test_case_ids=request.test_case_ids if request.test_case_ids else [tc.id for tc in project.test_cases]
    )
    
    # Check if project already exists
    existing = next((p for p in release.projects if p.project_id == request.project_id), None)
    if existing:
        # Update test cases
        existing.test_case_ids = release_project.test_case_ids
    else:
        release.projects.append(release_project)
    
    release.updated_at = datetime.now().isoformat()
    save_releases(releases)
    return release_project


@router.delete("/{release_id}/projects/{project_id}")
async def remove_project_from_release(release_id: str, project_id: str):
    """Remove project from release"""
    releases = load_releases()
    release = next((r for r in releases if r.id == release_id), None)
    
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    release.projects = [p for p in release.projects if p.project_id != project_id]
    release.updated_at = datetime.now().isoformat()
    
    save_releases(releases)
    return {"message": "Project removed successfully"}


# ============ Test Execution ============

@router.post("/{release_id}/run", response_model=ReleaseIteration)
async def run_release_tests(release_id: str, request: RunReleaseTestsRequest):
    """Run tests for a release in a specific environment"""
    import asyncio
    import sys
    from concurrent.futures import ThreadPoolExecutor

    releases = load_releases()
    release = next((r for r in releases if r.id == release_id), None)

    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    environment = next((e for e in release.environments if e.id == request.environment_id), None)
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    # Get all test cases from release projects
    storage = Storage()
    all_test_cases = []

    for release_project in release.projects:
        project = storage.get_project(release_project.project_id)
        if project:
            if release_project.test_case_ids:
                # Specific test cases
                test_cases = [tc for tc in project.test_cases if tc.id in release_project.test_case_ids]
            else:
                # All test cases
                test_cases = project.test_cases
            all_test_cases.extend(test_cases)

    if not all_test_cases:
        raise HTTPException(status_code=400, detail="No test cases found for this release")

    # Create report directory
    report_id = f"release_{release_id[:8]}_{request.environment_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_dir = f"reports/{report_id}"
    os.makedirs(report_dir, exist_ok=True)

    # Calculate iteration number
    env_iterations = [i for i in release.iterations if i.environment_id == request.environment_id]
    iteration_number = len(env_iterations) + 1

    # Create iteration record
    iteration_id = str(uuid.uuid4())
    iteration = ReleaseIteration(
        id=iteration_id,
        release_id=release_id,
        environment_id=request.environment_id,
        iteration_number=iteration_number,
        report_id=report_id,
        executed_at=datetime.now().isoformat(),
        duration=0.0,
        total_tests=len(all_test_cases),
        passed=0,
        failed=0,
        skipped=0,
        pass_rate=0.0,
        status="in_progress",
        notes=request.notes
    )

    release.iterations.append(iteration)
    release.total_iterations = len(release.iterations)
    release.status = ReleaseStatus.TESTING
    release.updated_at = datetime.now().isoformat()

    save_releases(releases)

    # Run tests in background
    async def execute_release_tests():
        try:
            start_time = datetime.now()

            # Use environment base URL for tests
            base_url = environment.base_url

            # Import the appropriate test runner
            if sys.platform == 'win32':
                from windows_test_runner_debug import run_tests_windows_safe
                loop = asyncio.get_event_loop()

                # Run tests using Windows-safe runner
                report = await loop.run_in_executor(
                    None,
                    run_tests_windows_safe,
                    all_test_cases,
                    base_url,
                    report_dir,
                    request.headless if hasattr(request, 'headless') else True,
                    loop,
                    lambda msg: print(f"[Release Test] {msg}")
                )
            else:
                from test_engine import TestEngine
                engine = TestEngine(log_callback=lambda msg: print(f"[Release Test] {msg}"))
                report = await engine.run_tests(
                    test_cases=all_test_cases,
                    base_url=base_url,
                    report_dir=report_dir,
                    headless=request.headless if hasattr(request, 'headless') else True
                )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Update iteration with results
            releases_updated = load_releases()
            release_updated = next((r for r in releases_updated if r.id == release_id), None)

            if release_updated:
                for i in release_updated.iterations:
                    if i.id == iteration_id:
                        i.passed = report.passed
                        i.failed = report.failed
                        i.skipped = report.skipped if hasattr(report, 'skipped') else 0
                        i.duration = duration
                        i.pass_rate = (report.passed / report.total_tests * 100) if report.total_tests > 0 else 0.0
                        i.status = "completed"
                        break

                # Update metrics
                update_release_metrics(release_updated)
                release_updated.updated_at = datetime.now().isoformat()

                # Update status based on results
                if release_updated.deployment_ready:
                    release_updated.status = ReleaseStatus.APPROVED
                elif any(i.status == "in_progress" for i in release_updated.iterations):
                    release_updated.status = ReleaseStatus.TESTING
                else:
                    release_updated.status = ReleaseStatus.ACTIVE

                save_releases(releases_updated)

            # Save report to storage
            report.id = report_id
            report.project_id = release_id
            report.project_name = f"Release: {release.name} - {environment.name}"
            storage.save_report(report)

            print(f"[Release Test] Completed: {report.passed} passed, {report.failed} failed")

        except Exception as e:
            print(f"[Release Test] Error: {str(e)}")
            import traceback
            traceback.print_exc()

            # Update iteration status to failed
            releases_updated = load_releases()
            release_updated = next((r for r in releases_updated if r.id == release_id), None)

            if release_updated:
                for i in release_updated.iterations:
                    if i.id == iteration_id:
                        i.status = "failed"
                        i.notes = f"{i.notes or ''}\nError: {str(e)}"
                        break
                save_releases(releases_updated)

    # Start test execution in background
    asyncio.create_task(execute_release_tests())

    return iteration


# ============ Metrics & Analytics ============

@router.get("/{release_id}/metrics", response_model=ReleaseMetrics)
async def get_release_metrics(release_id: str):
    """Get comprehensive metrics for a release"""
    release = get_release_by_id(release_id)
    
    # Calculate per-environment stats
    env_stats = {}
    for env in release.environments:
        env_iterations = [i for i in release.iterations if i.environment_id == env.id]
        
        if env_iterations:
            latest = max(env_iterations, key=lambda x: x.iteration_number)
            avg_pass_rate = sum(i.pass_rate for i in env_iterations) / len(env_iterations)
            
            env_stats[env.id] = {
                "name": env.name,
                "type": env.type,
                "total_iterations": len(env_iterations),
                "latest_pass_rate": latest.pass_rate,
                "average_pass_rate": avg_pass_rate,
                "latest_iteration": latest.iteration_number,
                "last_run": latest.executed_at,
                "status": "ready" if latest.pass_rate >= 100.0 else "blocked"
            }
    
    # Determine ready/blocked environments
    ready_envs = [env.name for env_id, stats in env_stats.items() if stats.get("status") == "ready"]
    blocked_envs = [env.name for env_id, stats in env_stats.items() if stats.get("status") == "blocked"]
    
    # Get trend data (last 5 iterations across all environments)
    recent_iterations = sorted(release.iterations, key=lambda x: x.executed_at, reverse=True)[:5]
    pass_rate_trend = [i.pass_rate for i in reversed(recent_iterations)]
    iteration_dates = [i.executed_at for i in reversed(recent_iterations)]
    
    # Calculate total test cases
    storage = Storage()
    total_test_cases = 0
    for rp in release.projects:
        project = storage.get_project(rp.project_id)
        if project:
            total_test_cases += len(rp.test_case_ids) if rp.test_case_ids else len(project.test_cases)
    
    update_release_metrics(release)
    
    metrics = ReleaseMetrics(
        release_id=release.id,
        total_environments=len(release.environments),
        total_projects=len(release.projects),
        total_test_cases=total_test_cases,
        total_iterations=len(release.iterations),
        environment_stats=env_stats,
        overall_pass_rate=release.overall_pass_rate,
        latest_iteration_date=release.iterations[-1].executed_at if release.iterations else None,
        deployment_ready=release.deployment_ready,
        ready_environments=ready_envs,
        blocked_environments=blocked_envs,
        pass_rate_trend=pass_rate_trend,
        iteration_dates=iteration_dates
    )
    
    return metrics