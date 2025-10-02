from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes import docx_processor, quiz

app = FastAPI(title="DOCX Processor Microservice", version="1.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Static files for serving outputs
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Include routers
app.include_router(docx_processor.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "DOCX Processor Microservice"}