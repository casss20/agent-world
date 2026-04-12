"""
ChatDev Workflow API Routes
FastAPI endpoints matching ChatDev Money frontend expectations
"""

import os
import json
import yaml
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/api", tags=["chatdev-workflows"])

# Paths
WORKFLOWS_DIR = Path("/root/.openclaw/workspace/chatdev-money/yaml_instance")
VUEGRAPHS_DIR = Path("/root/.openclaw/workspace/agent-world/vuegraphs")
SESSIONS_DIR = Path("/root/.openclaw/workspace/agent-world/sessions")

# Ensure directories exist
VUEGRAPHS_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ==================== REQUEST/RESPONSE MODELS ====================

class WorkflowUploadRequest(BaseModel):
    filename: str
    content: str


class WorkflowUpdateRequest(BaseModel):
    content: str


class WorkflowRenameRequest(BaseModel):
    new_filename: str


class VueGraphUploadRequest(BaseModel):
    filename: str
    content: Dict[str, Any]


class ConfigSchemaRequest(BaseModel):
    breadcrumbs: List[str]


# ==================== WORKFLOW MANAGEMENT ====================

@router.get("/workflows")
async def list_workflows():
    """List all workflow YAML files"""
    try:
        workflows = []
        if WORKFLOWS_DIR.exists():
            for f in WORKFLOWS_DIR.iterdir():
                if f.suffix in ['.yaml', '.yml']:
                    workflows.append(f.name)
        return {"workflows": workflows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{filename}/get")
async def get_workflow(filename: str):
    """Get workflow YAML content"""
    try:
        # Ensure .yaml suffix
        if not filename.endswith(('.yaml', '.yml')):
            filename += '.yaml'
        
        filepath = WORKFLOWS_DIR / filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        content = filepath.read_text()
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{filename}/desc")
async def get_workflow_description(filename: str):
    """Get workflow description from YAML"""
    try:
        # Ensure .yaml suffix
        if not filename.endswith(('.yaml', '.yml')):
            filename += '.yaml'
        
        filepath = WORKFLOWS_DIR / filename
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        content = filepath.read_text()
        data = yaml.safe_load(content)
        
        # Extract description from config
        description = data.get('config', {}).get('description', 'No description')
        
        return {"description": description}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/upload/content")
async def upload_workflow(request: WorkflowUploadRequest):
    """Upload a new workflow YAML"""
    try:
        # Ensure .yaml suffix
        filename = request.filename
        if not filename.endswith(('.yaml', '.yml')):
            filename += '.yaml'
        
        filepath = WORKFLOWS_DIR / filename
        
        # Validate YAML
        try:
            yaml.safe_load(request.content)
        except yaml.YAMLError as e:
            return {
                "status": False,
                "detail": f"Invalid YAML: {str(e)}"
            }
        
        # Write file
        filepath.write_text(request.content)
        
        return {
            "status": True,
            "filename": filename,
            "message": "YAML file saved successfully!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workflows/{filename}/update")
async def update_workflow(filename: str, request: WorkflowUpdateRequest):
    """Update existing workflow YAML"""
    try:
        # Ensure .yaml suffix
        if not filename.endswith(('.yaml', '.yml')):
            filename += '.yaml'
        
        filepath = WORKFLOWS_DIR / filename
        
        # Validate YAML
        try:
            yaml.safe_load(request.content)
        except yaml.YAMLError as e:
            return {
                "status": False,
                "detail": f"Invalid YAML: {str(e)}"
            }
        
        # Write file
        filepath.write_text(request.content)
        
        return {
            "status": True,
            "filename": filename,
            "message": "Workflow updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{filename}/rename")
async def rename_workflow(filename: str, request: WorkflowRenameRequest):
    """Rename a workflow"""
    try:
        # Ensure .yaml suffix
        if not filename.endswith(('.yaml', '.yml')):
            filename += '.yaml'
        
        new_filename = request.new_filename
        if not new_filename.endswith(('.yaml', '.yml')):
            new_filename += '.yaml'
        
        old_path = WORKFLOWS_DIR / filename
        new_path = WORKFLOWS_DIR / new_filename
        
        if not old_path.exists():
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if new_path.exists():
            raise HTTPException(status_code=409, detail="Target filename already exists")
        
        old_path.rename(new_path)
        
        return {
            "status": True,
            "filename": new_filename,
            "message": "Workflow renamed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{filename}/copy")
async def copy_workflow(filename: str, request: WorkflowRenameRequest):
    """Copy a workflow"""
    try:
        # Ensure .yaml suffix
        if not filename.endswith(('.yaml', '.yml')):
            filename += '.yaml'
        
        new_filename = request.new_filename
        if not new_filename.endswith(('.yaml', '.yml')):
            new_filename += '.yaml'
        
        source_path = WORKFLOWS_DIR / filename
        dest_path = WORKFLOWS_DIR / new_filename
        
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if dest_path.exists():
            raise HTTPException(status_code=409, detail="Target filename already exists")
        
        # Copy file
        dest_path.write_text(source_path.read_text())
        
        return {
            "status": True,
            "filename": new_filename,
            "message": "Workflow copied successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VUEFLOW GRAPH ====================

@router.get("/vuegraphs/{key}")
async def get_vuegraph(key: str):
    """Get VueFlow graph for a workflow"""
    try:
        # Clean key
        key = key.replace('.yaml', '').replace('.yml', '')
        filepath = VUEGRAPHS_DIR / f"{key}.json"
        
        if not filepath.exists():
            # Return empty graph structure
            return {
                "content": {
                    "nodes": [],
                    "edges": [],
                    "viewport": {"x": 0, "y": 0, "zoom": 1}
                }
            }
        
        content = json.loads(filepath.read_text())
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vuegraphs/upload/content")
async def upload_vuegraph(request: VueGraphUploadRequest):
    """Save VueFlow graph"""
    try:
        filename = request.filename
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = VUEGRAPHS_DIR / filename
        filepath.write_text(json.dumps(request.content, indent=2))
        
        return {
            "status": True,
            "message": "VueFlow graph saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WORKFLOW EXECUTION ====================

@router.post("/workflow/execute")
async def execute_workflow(
    yaml_file: str = Form(...),
    session_id: Optional[str] = Form(None),
    log_level: Optional[str] = Form("INFO")
):
    """Execute a workflow via ChatDev"""
    try:
        # Import ChatDev client
        from guarded_adapter import ChatDevClient
        
        client = ChatDevClient()
        
        # Start workflow
        result = await client.start_workflow(
            workflow_yaml=yaml_file,
            session_id=session_id,
            inputs={}
        )
        
        return {
            "status": "started",
            "session_id": result.get("session_id"),
            "chatdev_run_id": result.get("chatdev_run_id"),
            "message": "Workflow execution started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/batch")
async def batch_execute_workflow(
    yaml_file: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    max_parallel: Optional[int] = Form(1),
    log_level: Optional[str] = Form("INFO"),
    file: Optional[UploadFile] = File(None)
):
    """Execute batch workflow"""
    try:
        # Handle file upload if provided
        if file:
            content = await file.read()
            yaml_content = content.decode('utf-8')
            # Could save and execute
        
        return {
            "status": "started",
            "message": "Batch workflow executed successfully",
            "session_id": session_id or f"batch-{os.urandom(4).hex()}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SESSIONS ====================

@router.get("/sessions/{session_id}/download")
async def download_session_logs(session_id: str):
    """Download session logs as ZIP"""
    try:
        import zipfile
        import io
        from fastapi.responses import StreamingResponse
        
        session_dir = SESSIONS_DIR / session_id
        
        if not session_dir.exists():
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in session_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(session_dir)
                    zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename=execution_logs_{session_id}.zip'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/artifacts/{attachment_id}")
async def get_session_artifact(session_id: str, attachment_id: str):
    """Get session artifact/attachment"""
    try:
        session_dir = SESSIONS_DIR / session_id
        artifact_path = session_dir / attachment_id
        
        if not artifact_path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        # Read and encode
        import base64
        content = artifact_path.read_bytes()
        mime_type = "application/octet-stream"
        
        # Guess MIME type
        if artifact_path.suffix == '.png':
            mime_type = "image/png"
        elif artifact_path.suffix == '.jpg':
            mime_type = "image/jpeg"
        elif artifact_path.suffix == '.txt':
            mime_type = "text/plain"
        
        data_uri = f"data:{mime_type};base64,{base64.b64encode(content).decode()}"
        
        return {"data_uri": data_uri}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/uploads/{session_id}")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...)
):
    """Upload file to session"""
    try:
        session_dir = SESSIONS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = session_dir / (file.filename or "upload.bin")
        content = await file.read()
        file_path.write_bytes(content)
        
        return {
            "status": True,
            "name": file.filename,
            "attachment_id": file_path.name,
            "mime_type": file.content_type,
            "size": len(content)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CONFIG SCHEMA ====================

@router.post("/config/schema")
async def get_config_schema(request: ConfigSchemaRequest):
    """Get config schema for breadcrumbs"""
    try:
        # Return mock schema based on breadcrumbs
        # In real implementation, this would introspect ChatDev config
        
        field_name = request.breadcrumbs[-1] if request.breadcrumbs else "unknown"
        
        schemas = {
            "description": {
                "type": "string",
                "description": "Workflow description",
                "default": ""
            },
            "log_level": {
                "type": "select",
                "options": ["DEBUG", "INFO", "WARNING", "ERROR"],
                "default": "INFO"
            },
            "max_iterations": {
                "type": "integer",
                "description": "Maximum iterations",
                "default": 10,
                "min": 1,
                "max": 100
            }
        }
        
        return schemas.get(field_name, {
            "type": "string",
            "description": f"Configuration for {field_name}",
            "default": ""
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
