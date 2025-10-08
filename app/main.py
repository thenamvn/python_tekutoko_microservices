from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes import docx_processor, quiz
#cron task cleanup
from app.services.cleanup_service import CleanupService
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

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

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Add cleanup job to run every 24 hours
cleanup_service = CleanupService()
scheduler.add_job(
    cleanup_service.cleanup_extra_folders,
    trigger=IntervalTrigger(hours=24),
    id="cleanup_extra_folders",
    name="Cleanup extra output folders",
    replace_existing=True
)

@app.on_event("startup")
async def startup_event():
    """Start the scheduler when the app starts"""
    print("Starting scheduler for cleanup tasks...")
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the scheduler when the app shuts down"""
    print("Shutting down scheduler for cleanup tasks...")
    scheduler.shutdown()


@app.get("/")
async def root():
    return {"message": "DOCX Processor Microservice"}