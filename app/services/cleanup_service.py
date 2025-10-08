import os
import shutil
from typing import List
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, TestExamRoom

class CleanupService:
    def __init__(self):
        self.outputs_dir = "outputs"

    def get_db_uuids(self, db: Session) -> List[str]:
        """Get all UUIDs from TestExamRoom table"""
        rooms = db.query(TestExamRoom.uuid).all()
        return [room.uuid for room in rooms]

    def get_output_folders(self) -> List[str]:
        """Get all folder names in outputs directory"""
        if not os.path.exists(self.outputs_dir):
            return []
        return [f for f in os.listdir(self.outputs_dir) if os.path.isdir(os.path.join(self.outputs_dir, f))]

    def cleanup_extra_folders(self):
        """Check and delete folders that don't have corresponding UUID in database"""
        db = SessionLocal()
        try:
            db_uuids = set(self.get_db_uuids(db))
            output_folders = set(self.get_output_folders())
            
            # Find folders that exist in outputs but not in db
            extra_folders = output_folders - db_uuids
            
            for folder in extra_folders:
                folder_path = os.path.join(self.outputs_dir, folder)
                try:
                    shutil.rmtree(folder_path)
                    print(f"Deleted extra folder: {folder_path}")
                except Exception as e:
                    print(f"Error deleting folder {folder_path}: {e}")
                    
        finally:
            db.close()