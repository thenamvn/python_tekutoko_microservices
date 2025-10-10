# DOCX Processor Microservice

This is a Python backend microservice using FastAPI to process DOCX files, extract quiz questions, options, and images, and return JSON output. It supports creating exam rooms, retrieving quiz data for taking exams, checking answers with security features, and retrieving results.

## Features

- Accepts DOCX file uploads with UUID, username, and optional title to create exam rooms
- Extracts and converts images (WMF to WebP)
- Converts DOCX to LaTeX using Pandoc
- Parses LaTeX to structured JSON
- Saves outputs in UUID-specific directories
- Provides quiz data without correct answers for exam taking, including exam room info
- Checks user answers and provides scoring results with security monitoring
- Supports cancelling exams due to violations
- Retrieves leaderboard and individual student results

## Setup
0. Install Pandoc and ImageMagick
1. Install dependencies: `pip install -r requirements.txt`
2. Set up database (MySQL or other) and configure DATABASE_URL in .env
3. Run locally: `uvicorn app.main:app --reload`
4. Or use Docker: `docker-compose up`

## API

### POST `/api/v1/process-docx`

Uploads a DOCX file, processes it to extract quiz questions, and creates an exam room.

#### Request
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameters**:
  - `file` (required): DOCX file upload (only .docx files allowed)
  - `request_uuid` (optional): UUID string for request identification (if not provided, a new UUID is generated)
  - `username` (required): Username of the creator
  - `title` (optional): Title of the exam

#### Response
- **Status**: 200 OK
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "uuid": "12345678-1234-5678-9012-123456789012",
    "status": "success",
    "message": "DOCX processed and exam room created successfully"
  }
   ```

#### Error Responses
- **400 Bad Request**: Invalid file type or missing file
- **500 Internal Server Error**: Processing failed

#### Example Request (using curl)
```bash
curl -X POST "http://localhost:8000/api/v1/process-docx" \
  -F "file=@test.docx" \
  -F "username=creator@example.com" \
  -F "title=Sample Exam"
```

### GET `/api/v1/quiz/{quiz_uuid}`

Retrieves quiz data by UUID without correct answers for exam taking, including exam room information.

#### Request
- **Method**: GET
- **Parameters**:
  - `quiz_uuid` (required): UUID string of the processed quiz

#### Response
- **Status**: 200 OK
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "exam_uuid": "12345678-1234-5678-9012-123456789012",
    "title": "Sample Exam",
    "username": "creator@example.com",
    "created_at": "2025-10-10T12:00:00.000000",
    "questions": [
      {
        "id": 1,
        "blocks": [
          {
            "type": "text",
            "content": "Question text here"
          },
          {
            "type": "image",
            "src": "http://localhost:8000/outputs/12345678-1234-5678-9012-123456789012/media/image1.webp"
          }
        ],
        "options": [
          {
            "label": "A",
            "blocks": [
              {
                "type": "text",
                "content": "Option A text"
              }
            ]
          },
          {
            "label": "B",
            "blocks": [
              {
                "type": "text",
                "content": "Option B text"
              }
            ]
          }
        ]
      }
    ]
  }
  ```

#### Error Responses
- **400 Bad Request**: Invalid UUID format
- **404 Not Found**: Quiz not found or quiz data not found
- **500 Internal Server Error**: Failed to read quiz data

#### Example Request (using curl)
```bash
curl -X GET "http://localhost:8000/api/v1/quiz/12345678-1234-5678-9012-123456789012"
```

#### Notes
- Returns quiz data without the `correct` field to prevent cheating
- Includes exam room details like title, creator username, and creation time
- Reads from the previously processed outputs/{uuid}/output.json file
- UUID must be from a previously processed DOCX file

### POST `/api/v1/quiz/check-answers`

Checks user's quiz answers against correct answers and returns scoring results, including security analysis.

#### Request
- **Method**: POST
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "quiz_uuid": "12345678-1234-5678-9012-123456789012",
    "student_username": "student@example.com",
    "answers": [
      {
        "question_id": 1,
        "selected_option": "A"
      },
      {
        "question_id": 2,
        "selected_option": "C"
      },
      {
        "question_id": 3,
        "selected_option": "B"
      }
    ],
    "cheating_detected": false,
    "cheating_reason": null,
    "activity_log": [],
    "suspicious_activity": {
      "tabSwitches": 0,
      "devToolsAttempts": 0,
      "copyAttempts": 0,
      "screenshotAttempts": 0,
      "contextMenuAttempts": 0,
      "keyboardShortcuts": 0
    },
    "security_violation_detected": false
  }
  ```

#### Response
- **Status**: 200 OK
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "total_questions": 3,
    "correct_answers": 2,
    "incorrect_answers": 1,
    "score_percentage": 66.67,
    "results": [
      {
        "question_id": 1,
        "user_answer": "A",
        "correct_answer": "A",
        "is_correct": true
      },
      {
        "question_id": 2,
        "user_answer": "C",
        "correct_answer": "B",
        "is_correct": false
      },
      {
        "question_id": 3,
        "user_answer": "B",
        "correct_answer": "B",
        "is_correct": true
      }
    ],
    "security_notes": null,
    "exam_status": "completed"
  }
  ```

#### Error Responses
- **400 Bad Request**: Invalid UUID format or already submitted
- **404 Not Found**: Quiz not found or quiz data not found
- **500 Internal Server Error**: Failed to check answers

#### Example Request (using curl)
```bash
curl -X POST "http://localhost:8000/api/v1/quiz/check-answers" \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_uuid": "12345678-1234-5678-9012-123456789012",
    "student_username": "student@example.com",
    "answers": [
      {"question_id": 1, "selected_option": "A"},
      {"question_id": 2, "selected_option": "C"}
    ]
  }'
```

#### Notes
- Compares user answers with correct answers from the original quiz data
- Returns detailed results for each question including correctness
- Calculates overall score percentage
- Includes security monitoring: flags or cancels exams based on violations
- Exam status can be "completed", "flagged", or "cancelled"
- Saves results to database with IP address and activity logs
- Prevents duplicate submissions

### POST `/api/v1/quiz/cancel-exam`

Cancels an exam for a student due to violations.

#### Request
- **Method**: POST
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "quiz_uuid": "12345678-1234-5678-9012-123456789012",
    "student_username": "student@example.com",
    "reason": "Excessive security violations"
  }
  ```

#### Response
- **Status**: 200 OK
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "message": "Exam cancelled successfully"
  }
  ```

#### Error Responses
- **400 Bad Request**: Invalid request
- **404 Not Found**: Exam or student not found
- **500 Internal Server Error**: Failed to cancel exam

### GET `/api/v1/quiz/{quiz_uuid}/results`

Retrieves leaderboard scores for all submissions to the exam.

#### Request
- **Method**: GET
- **Parameters**:
  - `quiz_uuid` (required): UUID string of the exam

#### Response
- **Status**: 200 OK
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "exam_uuid": "12345678-1234-5678-9012-123456789012",
    "total_submissions": 25,
    "results": [
      {
        "student_username": "student1@example.com",
        "score_percentage": 85.5,
        "correct_answers": 43,
        "total_questions": 50,
        "completed_at": "2025-10-07T10:30:45.123456",
        "ip_address": "192.168.1.100",
        "cheating_detected": false,
        "cheating_reason": null,
        "exam_cancelled": false,
        "security_violation_detected": false,
        "suspicious_activity": {
          "tabSwitches": 2,
          "devToolsAttempts": 0,
          "copyAttempts": 0,
          "contextMenuAttempts": 0,
          "keyboardShortcuts": 1
        },
        "activity_log": []
      },
      {
        "student_username": "student2@example.com",
        "score_percentage": 62.0,
        "correct_answers": 31,
        "total_questions": 50,
        "completed_at": "2025-10-07T11:15:30.654321",
        "ip_address": "192.168.1.101",
        "cheating_detected": true,
        "cheating_reason": "Quá nhiều vi phạm bảo mật",
        "exam_cancelled": true,
        "security_violation_detected": true,
        "suspicious_activity": {
          "tabSwitches": 15,
          "devToolsAttempts": 5,
          "copyAttempts": 3,
          "contextMenuAttempts": 8,
          "keyboardShortcuts": 12
        },
        "activity_log": []
      }
    ]
  }
  ```

#### Error Responses
- **400 Bad Request**: Invalid UUID format
- **404 Not Found**: Exam not found
- **500 Internal Server Error**: Failed to retrieve results

#### Example Request (using curl)
```bash
curl -X GET "http://localhost:8000/api/v1/quiz/12345678-1234-5678-9012-123456789012/results"
```

### GET `/api/v1/quiz/{quiz_uuid}/{student_username}/results`

Retrieves individual student results for the exam.

#### Request
- **Method**: GET
- **Parameters**:
  - `quiz_uuid` (required): UUID string of the exam
  - `student_username` (required): Username of the student

#### Response
- **Status**: 200 OK
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "student_username": "student1@example.com",
    "score_percentage": 85.5,
    "correct_answers": 43,
    "total_questions": 50,
    "completed_at": "2025-10-07T10:30:45.123456",
    "ip_address": "192.168.1.100",
    "cheating_detected": false,
    "cheating_reason": null,
    "exam_cancelled": false,
    "security_violation_detected": false,
    "suspicious_activity": {
      "tabSwitches": 2,
      "devToolsAttempts": 0,
      "copyAttempts": 0,
      "contextMenuAttempts": 0,
      "keyboardShortcuts": 1
    },
    "activity_log": []
  }
  ```

#### Error Responses
- **400 Bad Request**: Invalid UUID format
- **404 Not Found**: Exam or student result not found
- **500 Internal Server Error**: Failed to retrieve results

#### Example Request (using curl)
```bash
curl -X GET "http://localhost:8000/api/v1/quiz/12345678-1234-5678-9012-123456789012/student1@example.com/results"
```

#### General Notes
- Outputs are saved in `outputs/{uuid}/` directory.
- Images are converted to WebP format and served via static files.
- UUID is used to organize outputs per request.
- Database stores exam rooms and results with security data.
- Security features include activity logging, violation detection, and exam cancellation.
