# GitHub Copilot Instructions

## Project Overview
This is a Python backend microservice project using:
- FastAPI framework
- Pydantic for data validation and serialization
- Uvicorn for ASGI server
- SQLAlchemy (optional, for future database integration)
- Pillow and ImageMagick for image processing
- Pandoc for DOCX to LaTeX conversion
- Concurrent.futures for multithreaded tasks
- UUID for request identification

The microservice processes DOCX files to extract quiz questions, options, and images, converting them to JSON output. It accepts DOCX uploads with a UUID, saves outputs (JSON and images) in a directory per UUID, and returns the JSON. Future extensions may include auto-grading from scanned images.

Follow the project structure and coding guidelines below when generating code.

---

## Project Structure
When creating new files, always place them inside the project root following this layout:

my-python-microservice/
  app/                      # Main application code
    __init__.py             # App initialization
    main.py                 # FastAPI app entry point
    routes/                 # API endpoints
      __init__.py
      docx_processor.py     # Endpoint for DOCX processing
    services/               # Business logic services
      __init__.py
      docx_service.py       # Core DOCX processing logic
    utils/                  # Shared utilities
      __init__.py
      image_utils.py        # Image extraction and conversion
  outputs/                  # Directory for generated outputs (JSON and images per UUID)
    .gitkeep
  tests/                    # Unit and integration tests
    __init__.py
    test_docx_processor.py
  requirements.txt          # Python dependencies
  Dockerfile                # Docker containerization
  docker-compose.yml        # Docker Compose for local dev
  README.md                 # Project documentation

---

## Coding Conventions
- Always use **Python** (`.py` files) with **type hints** (from typing).
- Use **FastAPI** for routing, **Pydantic** for models/DTOs (BaseModel for validation).
- Services handle business logic; routes handle HTTP requests/responses.
- Use **async/await** for I/O operations (e.g., file processing).
- Image processing: Extract from DOCX, convert WMF to WebP using ImageMagick, store in outputs/{uuid}/.
- Error handling: Use FastAPI's HTTPException for API errors.
- File uploads: Use FastAPI's UploadFile; validate file type (DOCX only).
- UUID: Use as request identifier; create subdirectories in outputs/.
- Multithreading: Use concurrent.futures for image conversions.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `kebab-case` for files.
- Imports: Use absolute imports (from app.routes import ...).
- Keep utilities in `utils/`; avoid duplicating code.
- Dependencies: List in requirements.txt; use virtualenv.
- Testing: Use pytest for unit tests.
- Logging: Use Python's logging module for debug/info.

---

## Output Format for Copilot
**Every time you generate code, you MUST:**
1. Clearly state the **full file path** where this code should be placed (relative to project root).
2. Provide only the code for that file in a fenced code block.
3. If multiple files are needed, list them in order with separate headings and fenced code blocks for each.
4. Do not include explanations outside of code unless explicitly asked.
5. Always follow the project folder structure when deciding file location.

**Example Output:**
File: "app/services/docx_service.py"
```python
# your code here
```
File: "app/utils/image_utils.py"
```python
# your code here
```

## Additional Notes
- Base logic on existing test.py: Extract images, convert DOCX to LaTeX, parse to JSON, update image paths.
- Use Pydantic models for request/response (e.g., Question, Option).
- For file handling, create utilities like `save_file`, `convert_image`.
- Keep services stateless; inject dependencies if needed.
- Validate inputs: DOCX file size, UUID format.
- Run with `uvicorn app.main:app --reload` for dev.
- Always add type hints for parameters, returns, and Pydantic models.