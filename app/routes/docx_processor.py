from fastapi import APIRouter, UploadFile, Form, File, HTTPException, Depends
from pydantic import BaseModel, UUID4
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
from app.services.docx_service import DocxService
from app.models.database import get_db
from app.services.database_service import DatabaseService
import shutil
import os

router = APIRouter()

class Block(BaseModel):
    type: str
    content: Optional[str] = None
    src: Optional[str] = None

class Option(BaseModel):
    label: str
    blocks: List[Block]

class Question(BaseModel):
    id: int
    blocks: List[Block]
    options: List[Option]
    correct: Optional[str] = None

class ProcessResponse(BaseModel):
    questions: List[Question]

class ProcessDocxResponse(BaseModel):
    uuid: str
    status: str
    message: str

@router.post("/process-docx", response_model=ProcessDocxResponse)
async def process_docx(
    file: UploadFile = File(...),
    request_uuid: UUID4 = Form(None),
    username: str = Form(...),
    title: str = Form(None),
    service: DocxService = Depends(),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only DOCX files are allowed")
    
    if request_uuid is None:
        request_uuid = uuid.uuid4()
    
    try:
        # Process DOCX file (questions/answers stored in output.json)
        await service.process_docx(file, str(request_uuid))
        
        # Only save basic exam room info to database
        db_service = DatabaseService(db)
        db_service.create_test_exam_room(
            uuid=str(request_uuid),
            username=username,
            title=title or file.filename
        )
        
        return ProcessDocxResponse(
            uuid=str(request_uuid), 
            status="success", 
            message="DOCX processed and exam room created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.delete("/test-room/{test_uuid}/{username}")
async def delete_test_room(
    test_uuid: str,
    username: str,  # Path parameter for ownership verification
    db: Session = Depends(get_db)
):
    """
    Delete test exam room and all associated data (DB + files)
    Only the creator (username) can delete
    """
    try:
        uuid.UUID(test_uuid)  # Validate UUID format
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    db_service = DatabaseService(db)
    
    # Delete from database (with ownership check)
    deleted = db_service.delete_test_exam_room(test_uuid, username)
    
    if not deleted:
        raise HTTPException(
            status_code=404, 
            detail="Test room not found or you are not authorized to delete it"
        )
    
    # Delete output files/folder
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, "outputs", test_uuid)
    
    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
        except Exception as e:
            # Log error but don't fail the request (DB already deleted)
            print(f"Warning: Failed to delete output directory {output_dir}: {e}")
    
    return {
        "status": "success",
        "message": f"Test room {test_uuid} deleted successfully",
        "uuid": test_uuid
    }