import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_process_docx():
    # Mock a DOCX file upload with UUID
    with open("code/test.docx", "rb") as f:
        response = client.post("/api/v1/process-docx", files={"file": ("test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}, data={"request_uuid": "test-uuid-123"})
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert len(data["questions"]) > 0