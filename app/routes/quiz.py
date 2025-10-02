from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
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

class UserAnswer(BaseModel):
    question_id: int
    selected_option: str  # "A", "B", "C", "D"

class CheckAnswersRequest(BaseModel):
    quiz_uuid: str
    answers: List[UserAnswer]

class QuestionResult(BaseModel):
    question_id: int
    user_answer: str
    correct_answer: str
    is_correct: bool

class CheckAnswersResponse(BaseModel):
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    score_percentage: float
    results: List[QuestionResult]

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

@router.post("/quiz/check-answers", response_model=CheckAnswersResponse)
async def check_quiz_answers(request: CheckAnswersRequest):
    """
    Check user's quiz answers against correct answers
    """
    try:
        # Validate UUID format
        uuid.UUID(request.quiz_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Check if output directory exists
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(project_root, "outputs", request.quiz_uuid)
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Check if JSON file exists
    json_path = os.path.join(output_dir, "output.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Quiz data not found")
    
    try:
        # Read JSON file with correct answers
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Create mapping of question_id to correct answer
        correct_answers_map: Dict[int, str] = {}
        for question in data.get("questions", []):
            correct_answers_map[question["id"]] = question.get("correct", "")
        
        # Check each user answer
        results: List[QuestionResult] = []
        correct_count = 0
        
        for user_answer in request.answers:
            question_id = user_answer.question_id
            user_selected = user_answer.selected_option
            correct_answer = correct_answers_map.get(question_id, "")
            
            is_correct = user_selected.upper() == correct_answer.upper()
            if is_correct:
                correct_count += 1
            
            results.append(QuestionResult(
                question_id=question_id,
                user_answer=user_selected,
                correct_answer=correct_answer,
                is_correct=is_correct
            ))
        
        total_questions = len(request.answers)
        incorrect_count = total_questions - correct_count
        score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        return CheckAnswersResponse(
            total_questions=total_questions,
            correct_answers=correct_count,
            incorrect_answers=incorrect_count,
            score_percentage=round(score_percentage, 2),
            results=results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check answers: {str(e)}")