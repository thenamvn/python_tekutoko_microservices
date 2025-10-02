from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import os

router = APIRouter()

class Block(BaseModel):
    type: str
    content: Optional[str] = None
    src: Optional[str] = None

class QuizOption(BaseModel):
    label: str
    blocks: List[Block]

class QuizQuestion(BaseModel):
    id: int
    blocks: List[Block]
    options: List[QuizOption]

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

@router.get("/quiz/{quiz_uuid}", response_model=QuizResponse)
async def get_quiz_data(quiz_uuid: str):
    """
    Get quiz data by UUID without correct answers for exam taking
    """
    try:
        # Validate UUID format
        uuid.UUID(quiz_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Check if output directory exists (go up to project root first)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, "outputs", quiz_uuid)
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Check if JSON file exists
    json_path = os.path.join(output_dir, "output.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Quiz data not found")
    
    try:
        # Read JSON file
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Filter out correct answers
        quiz_questions = []
        for question in data.get("questions", []):
            quiz_options = []
            for option in question.get("options", []):
                quiz_options.append(QuizOption(
                    label=option["label"],
                    blocks=[Block(**block) for block in option["blocks"]]
                ))
            
            quiz_questions.append(QuizQuestion(
                id=question["id"],
                blocks=[Block(**block) for block in question["blocks"]],
                options=quiz_options
            ))
        
        return QuizResponse(questions=quiz_questions)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read quiz data: {str(e)}")