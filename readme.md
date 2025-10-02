# DOCX Processor Microservice

This is a Python backend microservice using FastAPI to process DOCX files, extract quiz questions, options, and images, and return JSON output.

## Features

- Accepts DOCX file uploads with UUID
- Extracts and converts images (WMF to WebP)
- Converts DOCX to LaTeX using Pandoc
- Parses LaTeX to structured JSON
- Saves outputs in UUID-specific directories
- Provides quiz data without correct answers for exam taking
- Checks user answers and provides scoring results

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run locally: `uvicorn app.main:app --reload`
3. Or use Docker: `docker-compose up`

## API

### POST `/api/v1/process-docx`

Uploads a DOCX file, processes it to extract quiz questions, and returns the structured JSON output.

#### Request
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameters**:
  - `file` (required): DOCX file upload (only .docx files allowed)
  - `request_uuid` (optional): UUID string for request identification (if not provided, a new UUID is generated)

#### Response
- **Status**: 200 OK
- **Content-Type**: application/json
- **Body**:

  ```json
  {
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
            "src": "path/to/image.webp"
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
          }
        ],
        "correct": "A"
      }
    ]
  }
   ```

#### Error Responses
- **400 Bad Request**: Invalid file type or missing file
- **500 Internal Server Error**: Processing failed

#### Example Request (using curl)
```bash
curl -X POST "http://localhost:8000/api/v1/process-docx" \
  -F "file=@test.docx" \
  -F "request_uuid=12345678-1234-5678-9012-123456789012"
```

### GET `/api/v1/quiz/{quiz_uuid}`

Retrieves quiz data by UUID without correct answers for exam taking.

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
            "src": "path/to/image.webp"
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
- Reads from the previously processed outputs/{uuid}/output.json file
- UUID must be from a previously processed DOCX file

### POST `/api/v1/quiz/check-answers`

Checks user's quiz answers against correct answers and returns scoring results.

#### Request
- **Method**: POST
- **Content-Type**: application/json
- **Body**:

  ```json
  {
    "quiz_uuid": "12345678-1234-5678-9012-123456789012",
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
    ]
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
    ]
  }
  ```

#### Error Responses
- **400 Bad Request**: Invalid UUID format
- **404 Not Found**: Quiz not found or quiz data not found
- **500 Internal Server Error**: Failed to check answers

#### Example Request (using curl)
```bash
curl -X POST "http://localhost:8000/api/v1/quiz/check-answers" \
  -H "Content-Type: application/json" \
  -d '{
    "quiz_uuid": "12345678-1234-5678-9012-123456789012",
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
- Reads from the previously processed outputs/{uuid}/output.json file

#### General Notes
- Outputs are saved in `outputs/{uuid}/` directory.
- Images are converted to WebP format.
- UUID is used to organize outputs per request.