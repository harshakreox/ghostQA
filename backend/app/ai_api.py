"""
AI Test Case Generation API Endpoints
Works with universal LLM support (Ollama, LM Studio, Anthropic, etc.)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import os
import tempfile
import uuid

from ai_test_generator import (
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
    Works with any configured LLM (Ollama, LM Studio, Anthropic, etc.)
    """
    
    try:
        # Get configured generator
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating test cases: {str(e)}")


@router.post("/generate-from-file", response_model=GenerateTestCasesResponse)
async def generate_from_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    project_context: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None)
):
    """
    Generate test cases from uploaded BRD file (PDF, DOCX, TXT)
    Works with any configured LLM
    """
    
    # Validate file type
    allowed_extensions = ['.txt', '.pdf', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )
    
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
            raise HTTPException(status_code=400, detail=f"Error extracting text: {str(e)}")
        
        # Validate content
        if not brd_content or len(brd_content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="File content too short. Please provide a valid BRD document."
            )
        
        # Get configured generator
        generator = get_test_case_generator()
        
        # Get project context
        proj_context = None
        proj_base_url = None
        
        if project_id:
            storage = Storage()
            project = storage.get_project(project_id)
            if project:
                proj_context = f"Project: {project.name}\nDescription: {project.description}"
                proj_base_url = project.base_url
        
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
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
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
    """Add generated test cases to a project"""
    
    try:
        storage = Storage()
        project = storage.get_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
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
        
        storage.save_project(project)
        
        return {
            "message": f"Successfully added {added_count} test cases to project",
            "project_id": project_id,
            "added_count": added_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding test cases: {str(e)}")


@router.get("/check-api-key")
async def check_api_key():
    """
    Check if AI service is available
    Returns info about which service is configured
    """
    
    try:
        generator = get_test_case_generator()
        
        response_data = {
            "configured": True,
            "service": generator.api_type,
            "model": generator.model,
            "url": generator.api_url if generator.api_type != "anthropic" else "cloud",
            "message": f"[OK] Using {generator.api_type}: {generator.model}"
        }
        
        # If Ollama, add list of available models
        if generator.api_type == "ollama":
            try:
                import requests
                resp = requests.get("http://localhost:11434/api/tags", timeout=2)
                if resp.status_code == 200:
                    models = resp.json().get('models', [])
                    response_data["available_models"] = [m['name'] for m in models]
            except:
                pass
        
        return response_data
        
    except ValueError as e:
        return {
            "configured": False,
            "service": None,
            "message": str(e)
        }
    except Exception as e:
        return {
            "configured": False,
            "service": None,
            "message": f"Error checking AI service: {str(e)}"
        }


@router.get("/ollama/models")
async def list_ollama_models():
    """
    List all available Ollama models
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
                        "modified": m.get('modified_at', ''),
                        "details": m.get('details', {})
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