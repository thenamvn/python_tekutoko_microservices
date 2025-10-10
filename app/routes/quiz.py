from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import uuid
import json
import os

from app.models.database import get_db
from app.services.database_service import DatabaseService

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

class QuizWithExamInfoResponse(BaseModel):
    exam_uuid: str
    title: Optional[str]
    username: str
    created_at: str
    questions: List[QuizQuestion]

class UserAnswer(BaseModel):
    question_id: int
    selected_option: str

class ActivityLogEntry(BaseModel):
    type: str
    details: str
    timestamp: str
    questionIndex: int
    sessionId: str

class SuspiciousActivity(BaseModel):
    tabSwitches: int
    devToolsAttempts: int
    copyAttempts: int
    screenshotAttempts: int
    contextMenuAttempts: int
    keyboardShortcuts: int

class CheckAnswersRequest(BaseModel):
    quiz_uuid: str
    student_username: str
    answers: List[UserAnswer]
    cheating_detected: Optional[bool] = False
    cheating_reason: Optional[str] = None
    activity_log: Optional[List[ActivityLogEntry]] = []
    suspicious_activity: Optional[SuspiciousActivity] = None
    security_violation_detected: Optional[bool] = False

class QuestionResult(BaseModel):
    question_id: int
    user_answer: str
    correct_answer: str
    is_correct: bool

class CheckAnswersResponse(BaseModel):
    total_questions: int
    correct_answers: int
    incorrect_answers: int  # Add this field
    score_percentage: float
    results: List[QuestionResult]
    security_notes: Optional[str] = None
    exam_status: str  # "completed", "cancelled", "flagged"

class CancelExamRequest(BaseModel):
    quiz_uuid: str
    student_username: str
    reason: str

@router.get("/quiz/{quiz_uuid}", response_model=QuizWithExamInfoResponse)
async def get_quiz_data(quiz_uuid: str, db: Session = Depends(get_db)):
    """Get quiz data from output.json without correct answers"""
    try:
        uuid.UUID(quiz_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    # Check if exam room exists in database
    db_service = DatabaseService(db)
    exam_room = db_service.get_test_exam_room_by_uuid(quiz_uuid)
    if not exam_room:
        raise HTTPException(status_code=404, detail="Exam room not found")
    
    # Read questions from output.json file
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(project_root, "outputs", quiz_uuid, "output.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Quiz data not found")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Filter out correct answers for exam taking
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
        
        return QuizWithExamInfoResponse(
            exam_uuid=exam_room.uuid,
            title=exam_room.title,
            username=exam_room.username,
            created_at=exam_room.created_at.isoformat(),
            questions=quiz_questions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read quiz data: {str(e)}")

@router.post("/quiz/check-answers", response_model=CheckAnswersResponse)
async def check_quiz_answers(
    request: CheckAnswersRequest, 
    client_request: Request,
    db: Session = Depends(get_db)
):
    """Check answers from output.json and save score to database"""
    try:
        uuid.UUID(request.quiz_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    db_service = DatabaseService(db)
    
    # Check if exam room exists
    exam_room = db_service.get_test_exam_room_by_uuid(request.quiz_uuid)
    if not exam_room:
        raise HTTPException(status_code=404, detail="Exam room not found")
    
    # Check if student already submitted
    if db_service.check_student_submitted(request.quiz_uuid, request.student_username):
        raise HTTPException(status_code=400, detail="test.submittedBefore")
    
    # Read correct answers from output.json
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(project_root, "outputs", request.quiz_uuid, "output.json")
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Quiz data not found")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Create mapping of question_id to correct answer
        correct_answers_map = {}
        for question in data.get("questions", []):
            correct_answers_map[question["id"]] = question.get("correct", "")
        
        # Check each user answer
        results = []
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
        incorrect_count = total_questions - correct_count  # Calculate incorrect answers
        score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        # Prepare security notes and determine exam status
        security_notes = None
        exam_status = "completed"
        exam_cancelled = False
        
        if request.cheating_detected:
            exam_status = "flagged"
            security_notes = f"Security violation detected: {request.cheating_reason}"
            
            # Check if should cancel exam based on severity
            if request.suspicious_activity:
                sa = request.suspicious_activity
                total_violations = (sa.tabSwitches + sa.devToolsAttempts + 
                                  sa.copyAttempts + sa.contextMenuAttempts + 
                                  sa.keyboardShortcuts)
                
                # Cancel exam if too many violations (threshold: 10)
                if total_violations >= 10:
                    exam_cancelled = True
                    exam_status = "cancelled"
                    security_notes = f"Exam cancelled due to excessive violations: {request.cheating_reason}"
                
                activity_summary = []
                if sa.tabSwitches > 0:
                    activity_summary.append(f"Tab switches: {sa.tabSwitches}")
                if sa.devToolsAttempts > 0:
                    activity_summary.append(f"DevTools attempts: {sa.devToolsAttempts}")
                if sa.copyAttempts > 0:
                    activity_summary.append(f"Copy attempts: {sa.copyAttempts}")
                if sa.contextMenuAttempts > 0:
                    activity_summary.append(f"Context menu attempts: {sa.contextMenuAttempts}")
                if sa.keyboardShortcuts > 0:
                    activity_summary.append(f"Keyboard shortcuts: {sa.keyboardShortcuts}")
                
                if activity_summary:
                    security_notes += f" | Activity: {', '.join(activity_summary)}"
        
        # Convert activity log to dict format for database storage
        activity_log_dict = None
        if request.activity_log:
            activity_log_dict = [log.dict() for log in request.activity_log]
        
        # Convert suspicious activity to dict format
        suspicious_activity_dict = None
        if request.suspicious_activity:
            suspicious_activity_dict = request.suspicious_activity.dict()
        
        # Save score to database with security information
        ip_address = client_request.client.host
        db_service.create_exam_result(
            test_exam_uuid=request.quiz_uuid,
            student_username=request.student_username,
            total_questions=total_questions,
            correct_answers=correct_count,
            score_percentage=score_percentage,
            ip_address=ip_address,
            cheating_detected=request.cheating_detected or False,
            cheating_reason=request.cheating_reason,
            exam_cancelled=exam_cancelled,
            security_violation_detected=request.security_violation_detected or False,
            activity_log=activity_log_dict,
            suspicious_activity=suspicious_activity_dict
        )
        
        return CheckAnswersResponse(
            total_questions=total_questions,
            correct_answers=correct_count,
            incorrect_answers=incorrect_count,  # Add this field to response
            score_percentage=round(score_percentage, 2),
            results=results,
            security_notes=security_notes,
            exam_status=exam_status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check answers: {str(e)}")

@router.post("/quiz/cancel-exam")
async def cancel_exam(
    request: CancelExamRequest,
    db: Session = Depends(get_db)
):
    """Cancel exam submission due to security violations"""
    try:
        uuid.UUID(request.quiz_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    db_service = DatabaseService(db)
    
    # Check if exam room exists
    exam_room = db_service.get_test_exam_room_by_uuid(request.quiz_uuid)
    if not exam_room:
        raise HTTPException(status_code=404, detail="Exam room not found")
    
    # Cancel exam
    result = db_service.cancel_exam_submission(
        request.quiz_uuid, 
        request.student_username, 
        request.reason
    )
    
    if result:
        return {"message": "Exam cancelled successfully", "status": "cancelled"}
    else:
        return {"message": "No submission found to cancel", "status": "not_found"}

@router.get("/quiz/{quiz_uuid}/results")
async def get_exam_results(quiz_uuid: str, db: Session = Depends(get_db)):
    """Get all exam results for a quiz from database"""
    try:
        uuid.UUID(quiz_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    db_service = DatabaseService(db)
    results = db_service.get_exam_results_by_uuid(quiz_uuid)
    
    return {
        "exam_uuid": quiz_uuid,
        "total_submissions": len(results),
        "results": [
            {
                "student_username": result.student_username,
                "score_percentage": result.score_percentage,
                "correct_answers": result.correct_answers,
                "total_questions": result.total_questions,
                "completed_at": result.completed_at,
                "ip_address": result.ip_address,
                "cheating_detected": result.cheating_detected,
                "cheating_reason": result.cheating_reason,
                "exam_cancelled": result.exam_cancelled,
                "security_violation_detected": result.security_violation_detected,
                "suspicious_activity": result.suspicious_activity
            }
            for result in results
        ]
    }

@router.get("/quiz/{quiz_uuid}/{student_username}/results")
async def get_student_exam_result(quiz_uuid: str, student_username: str, db: Session = Depends(get_db)):
    """Get a specific student's exam result for a quiz from database"""
    try:
        uuid.UUID(quiz_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    
    db_service = DatabaseService(db)
    result = db_service.get_student_exam_result(quiz_uuid, student_username)
    
    if not result:
        raise HTTPException(status_code=404, detail="Exam result not found")
    
    return {
        "student_username": result.student_username,
        "score_percentage": result.score_percentage,
        "correct_answers": result.correct_answers,
        "total_questions": result.total_questions,
        "completed_at": result.completed_at,
        "ip_address": result.ip_address,
        "cheating_detected": result.cheating_detected,
        "cheating_reason": result.cheating_reason,
        "exam_cancelled": result.exam_cancelled,
        "security_violation_detected": result.security_violation_detected,
        "suspicious_activity": result.suspicious_activity,
        "activity_log": result.activity_log
    }