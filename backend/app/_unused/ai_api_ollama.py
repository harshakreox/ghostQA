"""
AI Test Case Generation API Endpoints (with Ollama support)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import os
import tempfile
import uuid

from ai_test_generator_ollama import (
    get_test_case_generator,
    GenerateTestCasesRequest,
    GenerateTestCasesResponse,
    GeneratedTestCase,
    extract_text_from_file
)
from models import TestCase
from storage import Storage

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/generate-from-text", response_model=GenerateTestCasesResponse)
async def generate_from_text(request: GenerateTestCasesRequest):
    """
    Generate test cases from BRD text content
    Works with both Ollama (local) and Anthropic (API)
    """
    
    try:
        # Get appropriate generator (auto-detects Ollama or Anthropic)
        generator = get_test_case_generator()
        
        # Get project context if project_id provided
        project_context = None
        base_url = None
        
        if request.project_id:
            storage = Storage()
            project = storage.get_project(request.project_id)
            if project:
                project_context = f"Project: {project.name}\nDescription: {project.description}"
                base_url = project.base_url
        
        # Override with provided context/url if present
        if request.project_context:
            project_context = request.project_context
        if request.base_url:
            base_url = request.base_url
        
        # Generate test cases
        response = generator.generate_test_cases(
            brd_content=request.brd_content,
            project_context=project_context,
            base_url=base_url
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating test cases: {str(e)}"
        )


@router.post("/generate-from-file", response_model=GenerateTestCasesResponse)
async def generate_from_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    project_context: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None)
):
    """
    Generate test cases from uploaded BRD file (PDF, DOCX, TXT)
    Works with both Ollama (local) and Anthropic (API)
    """
    
    # Validate file type
    allowed_extensions = ['.txt', '.pdf', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    temp_file_path = None
    
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        # Extract text from file
        try:
            brd_content = extract_text_from_file(temp_file_path)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error extracting text from file: {str(e)}"
            )
        
        # Validate content
        if not brd_content or len(brd_content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="File content is too short or empty. Please provide a valid BRD document."
            )
        
        # Get appropriate generator (auto-detects Ollama or Anthropic)
        generator = get_test_case_generator()
        
        # Get project context if project_id provided
        proj_context = None
        proj_base_url = None
        
        if project_id:
            storage = Storage()
            project = storage.get_project(project_id)
            if project:
                proj_context = f"Project: {project.name}\nDescription: {project.description}"
                proj_base_url = project.base_url
        
        # Override with provided values
        if project_context:
            proj_context = project_context
        if base_url:
            proj_base_url = base_url
        
        # Generate test cases
        response = generator.generate_test_cases(
            brd_content=brd_content,
            project_context=proj_context,
            base_url=proj_base_url
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )
    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass


@router.post("/add-to-project/{project_id}")
async def add_generated_tests_to_project(
    project_id: str,
    test_cases: list[GeneratedTestCase]
):
    """
    Add generated test cases to a project
    """
    
    try:
        storage = Storage()
        project = storage.get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Convert GeneratedTestCase to TestCase and add to project
        added_count = 0
        
        for generated_tc in test_cases:
            test_case = TestCase(
                id=str(uuid.uuid4()),
                name=generated_tc.name,
                description=generated_tc.description,
                actions=generated_tc.actions,
                created_at="",
                updated_at=""
            )
            
            project.test_cases.append(test_case)
            added_count += 1
        
        # Save project
        storage.save_project(project)
        
        return {
            "message": f"Successfully added {added_count} test cases to project",
            "project_id": project_id,
            "added_count": added_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding test cases to project: {str(e)}"
        )


@router.get("/check-api-key")
async def check_api_key():
    """
    Check if AI service is available (Ollama or Anthropic)
    """
    
    status = {
        "configured": False,
        "service": None,
        "message": ""
    }
    
    # Check Ollama first
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            status["configured"] = True
            status["service"] = "ollama"
            status["message"] = f"✅ Ollama is running with {len(models)} model(s): {', '.join(model_names[:3])}"
            status["models"] = model_names
            return status
    except:
        pass
    
    # Check Anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        status["configured"] = True
        status["service"] = "anthropic"
        status["message"] = "✅ Anthropic API key is configured"
        return status
    
    # Neither available
    status["message"] = (
        "❌ No AI service available. Please either:\n"
        "1. Install and start Ollama: https://ollama.ai\n"
        "2. Set ANTHROPIC_API_KEY environment variable"
    )
    return status


@router.get("/ollama/models")
async def get_ollama_models():
    """
    Get list of available Ollama models
    """
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        
        if response.status_code == 200:
            models = response.json().get('models', [])
            return {
                "available": True,
                "models": [
                    {
                        "name": m['name'],
                        "size": m.get('size', 0),
                        "modified": m.get('modified_at', '')
                    }
                    for m in models
                ]
            }
        else:
            raise Exception("Ollama not responding")
            
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama not available: {str(e)}"
        )