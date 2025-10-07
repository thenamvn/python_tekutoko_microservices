from fastapi import APIRouter, UploadFile, Form, File, HTTPException, Depends
from pydantic import BaseModel, UUID4
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
from app.services.docx_service import DocxService
from app.models.database import get_db
from app.services.database_service import DatabaseService

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