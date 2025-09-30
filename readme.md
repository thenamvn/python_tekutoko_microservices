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

- POST `/api/v1/process-docx`: Upload DOCX file and get JSON response
```
python_tekutoko
├─ app
│  ├─ init.py
│  ├─ main.py
│  ├─ routes
│  │  ├─ docx_processor.py
│  │  └─ init.py
│  ├─ services
│  │  ├─ docx_service.py
│  │  └─ init.py
│  └─ utils
│     ├─ image_utils.py
│     └─ init.py
├─ code
│  ├─ lib.py
│  ├─ output.json
│  ├─ pandoc-3.8.1-windows-x86_64.msi
│  ├─ test copy.ipynb
│  ├─ test.docx
│  └─ test.py
├─ docker-compose.yml
├─ Dockerfile
├─ readme.md
├─ requirements.txt
└─ tests
   ├─ init.py
   └─ test_docx_processor.py

```