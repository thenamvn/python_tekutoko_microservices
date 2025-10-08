import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# For MySQL, need to specify the driver
if DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class TestExamRoom(Base):
    __tablename__ = "test_exam_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ExamResult(Base):
    __tablename__ = "exam_results"
    
    id = Column(Integer, primary_key=True, index=True)
    test_exam_uuid = Column(String(36), ForeignKey("test_exam_rooms.uuid", ondelete="CASCADE"), nullable=False)
    student_username = Column(String(255), nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    score_percentage = Column(Float, nullable=False)
    ip_address = Column(String(45), nullable=True)
    
    # Security fields
    cheating_detected = Column(Boolean, default=False, nullable=False)
    cheating_reason = Column(Text, nullable=True)
    exam_cancelled = Column(Boolean, default=False, nullable=False)
    security_violation_detected = Column(Boolean, default=False, nullable=False)
    activity_log = Column(JSON, nullable=True)  # Store activity log as JSON
    suspicious_activity = Column(JSON, nullable=True)  # Store suspicious activity counts as JSON
    
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()