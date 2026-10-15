# RuleRadar AI - Documents API Routes
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import get_db, Document, Clause, RiskFinding, Deadline
from app.services.document_service import DocumentService
from app.nlp.ingestion import IngestionError

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    db: Session = Depends(get_db)
):
    """
    Upload and analyze a PDF, DOCX, or TXT document.
    Validates file integrity, extracts text page-by-page, classifies clauses,
    scores importance, checks review risks, and extracts obligations and deadlines.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename in upload.")

    try:
        content = await file.read()
        doc = DocumentService.process_and_save_document(
            db=db,
            file_bytes=content,
            original_filename=file.filename,
            category=category
        )
        return {
            "status": "success",
            "message": "Document ingested and analyzed successfully.",
            "document": {
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "category": doc.category,
                "page_count": doc.page_count,
                "status": doc.status,
                "scanned_warning": doc.scanned_warning,
                "summary": doc.summary,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
        }
    except IngestionError as ie:
        raise HTTPException(status_code=400, detail=str(ie))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")

@router.get("")
def list_documents(db: Session = Depends(get_db)):
    """List all analyzed documents with summary metrics."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    results = []
    for d in docs:
        c_count = db.query(Clause).filter(Clause.document_id == d.id).count()
        r_count = db.query(RiskFinding).filter(RiskFinding.document_id == d.id).count()
        d_count = db.query(Deadline).filter(Deadline.document_id == d.id).count()
        results.append({
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "category": d.category,
            "page_count": d.page_count,
            "status": d.status,
            "scanned_warning": d.scanned_warning,
            "summary": d.summary,
            "clause_count": c_count,
            "risk_count": r_count,
            "deadline_count": d_count,
            "created_at": d.created_at.isoformat() if d.created_at else None
        })
    return {"documents": results}

@router.get("/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Retrieve complete structured document analysis by ID."""
    details = DocumentService.get_document_details(db, doc_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found.")
    return details

@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Permanently delete a document and all related analysis records."""
    success = DocumentService.delete_document(db, doc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document with ID '{doc_id}' not found.")
    return {"status": "success", "message": f"Document '{doc_id}' permanently deleted."}
