from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.database import TestExamRoom, ExamResult

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_test_exam_room(self, uuid: str, username: str, title: Optional[str] = None) -> TestExamRoom:
        """Create a new test exam room record"""
        db_exam_room = TestExamRoom(
            uuid=uuid,
            username=username,
            title=title
        )
        self.db.add(db_exam_room)
        self.db.commit()
        self.db.refresh(db_exam_room)
        return db_exam_room
    
    def get_test_exam_room_by_uuid(self, uuid: str) -> Optional[TestExamRoom]:
        """Get test exam room by UUID"""
        return self.db.query(TestExamRoom).filter(TestExamRoom.uuid == uuid).first()
    
    def create_exam_result(
        self, 
        test_exam_uuid: str, 
        student_username: str, 
        total_questions: int, 
        correct_answers: int, 
        score_percentage: float, 
        ip_address: Optional[str] = None,
        cheating_detected: bool = False,
        cheating_reason: Optional[str] = None,
        exam_cancelled: bool = False,
        security_violation_detected: bool = False,
        activity_log: Optional[List[Dict[str, Any]]] = None,
        suspicious_activity: Optional[Dict[str, int]] = None
    ) -> ExamResult:
        """Create a new exam result record with security information"""
        db_exam_result = ExamResult(
            test_exam_uuid=test_exam_uuid,
            student_username=student_username,
            total_questions=total_questions,
            correct_answers=correct_answers,
            score_percentage=score_percentage,
            ip_address=ip_address,
            cheating_detected=cheating_detected,
            cheating_reason=cheating_reason,
            exam_cancelled=exam_cancelled,
            security_violation_detected=security_violation_detected,
            activity_log=activity_log,
            suspicious_activity=suspicious_activity
        )
        self.db.add(db_exam_result)
        self.db.commit()
        self.db.refresh(db_exam_result)
        return db_exam_result

    def delete_test_exam_room(self, uuid: str, username: str) -> bool:
        """
        Delete test exam room and all related results
        Only owner (username) can delete
        Returns True if deleted, False if not found or unauthorized
        """
        exam_room = self.db.query(TestExamRoom).filter(
            TestExamRoom.uuid == uuid,
            TestExamRoom.username == username  # Verify ownership
        ).first()
        
        if not exam_room:
            return False
        
        # Delete all related exam results first (cascade should handle this, but explicit is better)
        self.db.query(ExamResult).filter(ExamResult.test_exam_uuid == uuid).delete()
        
        # Delete the exam room
        self.db.delete(exam_room)
        self.db.commit()
        return True
    
    def get_exam_results_by_uuid(self, test_exam_uuid: str) -> List[ExamResult]:
        """Get all exam results for a test"""
        return self.db.query(ExamResult).filter(ExamResult.test_exam_uuid == test_exam_uuid).all()

    def get_student_exam_result(self, test_exam_uuid: str, student_username: str) -> Optional[ExamResult]:
        """Get a specific student's exam result"""
        return self.db.query(ExamResult).filter(
            ExamResult.test_exam_uuid == test_exam_uuid,
            ExamResult.student_username == student_username
        ).first()
    
    def check_student_submitted(self, test_exam_uuid: str, student_username: str) -> bool:
        """Check if student already submitted"""
        result = self.db.query(ExamResult).filter(
            ExamResult.test_exam_uuid == test_exam_uuid,
            ExamResult.student_username == student_username
        ).first()
        return result is not None
    
    def cancel_exam_submission(self, test_exam_uuid: str, student_username: str, reason: str) -> Optional[ExamResult]:
        """Cancel/mark exam as cancelled for security reasons"""
        result = self.db.query(ExamResult).filter(
            ExamResult.test_exam_uuid == test_exam_uuid,
            ExamResult.student_username == student_username
        ).first()
        
        if result:
            result.exam_cancelled = True
            result.cheating_detected = True
            result.cheating_reason = reason
            self.db.commit()
            self.db.refresh(result)
        
        return result