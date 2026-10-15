# RuleRadar AI - Main FastAPI Application
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.api import (
    documents_router, analysis_router, compare_router,
    qa_router, export_router, system_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing DB tables, auto-seeding, and model pre-warming."""
    import logging
    logger = logging.getLogger("uvicorn")
    
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    db_file = os.path.join(settings.DATA_DIR, "ruleradar.db")
    backup_zip = os.path.join(settings.BASE_DIR, "ruleradar_data_latest.zip")
    
    # Auto-restore pre-packaged dataset on fresh cloud deployment if database does not exist
    if os.path.exists(backup_zip) and (not os.path.exists(db_file) or os.path.getsize(db_file) < 4096):
        try:
            import zipfile
            with zipfile.ZipFile(backup_zip, "r") as zipf:
                zipf.extractall(settings.DATA_DIR)
            logger.info("RuleRadar AI: Successfully pre-populated database from ruleradar_data_latest.zip")
        except Exception as e:
            logger.warning(f"RuleRadar AI: Auto-restore error: {e}")

    init_db()
    
    # Pre-warm embedding service so the first API request has zero model initialization latency
    try:
        from app.nlp.embeddings import EmbeddingService
        EmbeddingService()
    except Exception as e:
        logger.warning(f"Embedding model pre-warm notice: {e}")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Document Intelligence, Important Clause Identification, Risk Analysis & Semantic Comparison System",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(documents_router)
app.include_router(analysis_router)
app.include_router(compare_router)
app.include_router(qa_router)
app.include_router(export_router)
app.include_router(system_router)

# Mount Static Files & Templates
STATIC_DIR = os.path.join(settings.BASE_DIR, "app", "static")
TEMPLATES_DIR = os.path.join(settings.BASE_DIR, "app", "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve the single-page responsive web application."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Structured JSON error responses for unhandled server exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc),
            "type": exc.__class__.__name__
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
