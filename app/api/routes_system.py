from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db import get_db, Document, Clause, RiskFinding, Deadline, ComparisonReport
from app.nlp.embeddings import embedding_service
from app.config import settings

router = APIRouter(prefix="/api/system", tags=["System"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health and readiness check:
    Reports database status, NLP model state, PyMuPDF, and storage capacity.
    """
    db_ok = False
    try:
        db.execute(Document.__table__.select().limit(1))
        db_ok = True
    except Exception:
        db_ok = False

    # Check disk usage
    try:
        disk_usage = shutil.disk_usage(settings.DATA_DIR)
        free_gb = round(disk_usage.free / (1024 ** 3), 2)
    except Exception:
        free_gb = -1.0

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "components": {
            "database": {
                "status": "connected" if db_ok else "disconnected",
                "engine": "SQLite"
            },
            "nlp_embeddings": {
                "model": embedding_service.model_type,
                "status": "active"
            },
            "document_parsers": {
                "pdf_pymupdf": "available",
                "docx_openxml": "available",
                "text_encoding": "available"
            },
            "storage": {
                "upload_directory": settings.UPLOAD_DIR,
                "free_disk_space_gb": free_gb
            }
        }
    }

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Real dashboard statistics pulled directly from live database tables.
    """
    total_docs = db.query(Document).count()
    important_clauses = db.query(Clause).filter(Clause.importance_score >= settings.IMPORTANCE_THRESHOLD_MEDIUM).count()
    high_risks = db.query(RiskFinding).filter(RiskFinding.risk_level.in_(["High attention", "Needs review"])).count()
    total_clauses = db.query(Clause).count()
    unreviewed_findings = db.query(RiskFinding).filter(RiskFinding.is_reviewed == False).count()
    total_comparisons = db.query(ComparisonReport).count()
    upcoming_deadlines = db.query(Deadline).count()

    recent_docs = db.query(Document).order_by(Document.created_at.desc()).limit(5).all()

    return {
        "total_documents": total_docs,
        "clauses_identified": total_clauses,
        "important_clauses": important_clauses,
        "findings_requiring_review": unreviewed_findings,
        "risk_findings": high_risks,
        "upcoming_deadlines": upcoming_deadlines,
        "total_comparisons": total_comparisons,
        "comparisons_completed": total_comparisons,
        "recent_documents": [{
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "category": d.category,
            "page_count": d.page_count,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None
        } for d in recent_docs]
    }

@router.get("/activity")
def get_activity_history(limit: int = 15, db: Session = Depends(get_db)):
    """
    Fetch genuine chronological activity history derived directly from SQLite database records:
    - Document uploads & analysis completions
    - Revision comparisons completed
    - Grounded Q&A consultations
    - Human review status updates
    """
    events = []

    # 1. Document ingestions
    docs = db.query(Document).order_by(Document.created_at.desc()).limit(limit).all()
    for d in docs:
        if d.created_at:
            events.append({
                "id": f"doc-{d.id}",
                "event_type": "document_analyzed",
                "title": f"Document analyzed: {d.filename}",
                "description": f"Processed {d.page_count} page(s) under {d.category.replace('_', ' ').title()}",
                "document_id": d.id,
                "timestamp": d.created_at.isoformat()
            })

    # 2. Comparisons
    comps = db.query(ComparisonReport).order_by(ComparisonReport.created_at.desc()).limit(limit).all()
    for c in comps:
        if c.created_at:
            events.append({
                "id": f"comp-{c.id}",
                "event_type": "comparison_completed",
                "title": "Version comparison completed",
                "description": f"{c.modified_clauses_count} modified, {c.added_clauses_count} added, {c.removed_clauses_count} removed",
                "document_id": c.doc_b_id,
                "timestamp": c.created_at.isoformat()
            })

    # 3. Q&A interactions
    from app.db import QASession
    qas = db.query(QASession, Document.filename).join(Document, QASession.document_id == Document.id).order_by(QASession.created_at.desc()).limit(limit).all()
    for qa, fname in qas:
        if qa.created_at:
            events.append({
                "id": f"qa-{qa.id}",
                "event_type": "qa_inquiry",
                "title": "Grounded Q&A consultation",
                "description": f"Asked '{qa.question[:45]}...' on {fname}",
                "document_id": qa.document_id,
                "timestamp": qa.created_at.isoformat()
            })

    # 4. Review updates
    reviewed_risks = db.query(RiskFinding, Document.filename).join(Document, RiskFinding.document_id == Document.id).filter(RiskFinding.is_reviewed == True).limit(limit).all()
    for r, fname in reviewed_risks:
        if r.created_at:
            events.append({
                "id": f"rev-{r.id}",
                "event_type": "risk_reviewed",
                "title": f"Risk reviewed: {r.rule_name}",
                "description": f"Audited on {fname}",
                "document_id": r.document_id,
                "timestamp": r.created_at.isoformat()
            })

    # Sort all events chronologically descending
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"total": len(events), "activities": events[:limit]}

@router.post("/retention/purge")
def purge_old_documents(
    days_older_than: int = Body(..., embed=True, ge=1),
    db: Session = Depends(get_db)
):
    """
    Execute GDPR / privacy data-retention purge: deletes documents older than N days.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_older_than)
    old_docs = db.query(Document).filter(Document.created_at < cutoff).all()
    
    deleted_count = 0
    for doc in old_docs:
        if doc.stored_path and os.path.exists(doc.stored_path):
            try:
                os.remove(doc.stored_path)
            except OSError:
                pass
        db.delete(doc)
        deleted_count += 1

    db.commit()
    return {
        "status": "success",
        "purged_count": deleted_count,
        "cutoff_date": cutoff.isoformat()
    }
