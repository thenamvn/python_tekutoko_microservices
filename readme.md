# DOCX Processor Microservice

This is a Python backend microservice using FastAPI to process DOCX files, extract quiz questions, options, and images, and return JSON output.

## Features

- Accepts DOCX file uploads with UUID
- Extracts and converts images (WMF to WebP)
- Converts DOCX to LaTeX using Pandoc
- Parses LaTeX to structured JSON
- Saves outputs in UUID-specific directories

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

#### Notes
- Outputs are saved in `outputs/{uuid}/` directory.
- Images are converted to WebP format.
- UUID is used to organize outputs per request.