from fastapi import APIRouter, UploadFile, Form, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, UUID4
from typing import List, Optional
import uuid
import os
from app.services.docx_service import DocxService

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

@router.post("/process-docx", response_model=ProcessResponse)
async def process_docx(
    file: UploadFile = File(...),
    request_uuid: UUID4 = Form(None),
    service: DocxService = Depends()
):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only DOCX files are allowed")
    
    if request_uuid is None:
        request_uuid = uuid.uuid4()
    
    try:
        result = await service.process_docx(file, str(request_uuid))
        return JSONResponse(content=result.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")