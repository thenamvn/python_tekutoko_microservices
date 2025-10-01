from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes.docx_processor import router as docx_router

app = FastAPI(title="DOCX Processor Microservice", version="1.0.0")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.include_router(docx_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "DOCX Processor Microservice"}