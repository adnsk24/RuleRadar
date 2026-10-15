# RuleRadar AI - Analysis & Clause Explorer API Routes
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.db import get_db, Clause, RiskFinding, Document

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

@router.get("/clauses")
def explore_clauses(
    document_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    importance: Optional[str] = Query(None), # High, Medium, Low
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Search and filter clauses across one or all documents.
    """
    query = db.query(Clause, Document.filename).join(Document, Clause.document_id == Document.id)

    if document_id:
        query = query.filter(Clause.document_id == document_id)
    if category and category != "all":
        query = query.filter(Clause.category == category)
    if importance and importance != "all":
        query = query.filter(Clause.importance_category == importance)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(Clause.original_text.ilike(search_fmt) | Clause.heading.ilike(search_fmt))

    total = query.count()
    items = query.order_by(Clause.importance_score.desc()).offset(skip).limit(limit).all()

    results = []
    for clause, filename in items:
        results.append({
            "id": clause.id,
            "document_id": clause.document_id,
            "filename": filename,
            "clause_number": clause.clause_number,
            "heading": clause.heading,
            "page_start": clause.page_start,
            "page_end": clause.page_end,
            "category": clause.category,
            "category_confidence": clause.category_confidence,
            "category_explanation": clause.category_explanation,
            "importance_score": clause.importance_score,
            "importance_category": clause.importance_category,
            "importance_explanation": clause.importance_explanation,
            "original_text": clause.original_text,
            "is_reviewed": clause.is_reviewed
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "clauses": results
    }

@router.get("/review-queue")
def get_review_queue(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """
    Fetch prioritized findings requiring user review across all documents.
    Orders by high attention first, then by creation date.
    """
    findings = db.query(RiskFinding, Document.filename, Clause.page_start, Clause.category).join(
        Document, RiskFinding.document_id == Document.id
    ).outerjoin(
        Clause, RiskFinding.clause_id == Clause.id
    ).filter(
        RiskFinding.is_reviewed == False
    ).order_by(
        RiskFinding.overall_score.desc(),
        RiskFinding.created_at.desc()
    ).limit(limit).all()

    queue = []
    for risk, filename, page_start, category in findings:
        queue.append({
            "id": risk.id,
            "document_id": risk.document_id,
            "document_name": filename,
            "document_filename": filename,
            "clause_id": risk.clause_id,
            "category": category or "Contract Provision",
            "priority": risk.risk_level,
            "risk_level": risk.risk_level,
            "rule_name": risk.rule_name,
            "explanation": risk.explanation,
            "evidence_quote": risk.evidence_quote,
            "source_page": page_start or 1,
            "page_start": page_start or 1,
            "suggested_question": risk.suggested_question,
            "uncertainty_note": risk.uncertainty_note,
            "overall_score": risk.overall_score,
            "is_reviewed": risk.is_reviewed
        })

    return {
        "total": len(queue),
        "queue": queue,
        "findings": queue
    }

@router.get("/risks")
def list_risk_findings(
    document_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    List and filter risk analysis findings across all documents.
    """
    query = db.query(RiskFinding, Document.filename, Clause.page_start, Clause.category).join(
        Document, RiskFinding.document_id == Document.id
    ).outerjoin(
        Clause, RiskFinding.clause_id == Clause.id
    )

    if document_id:
        query = query.filter(RiskFinding.document_id == document_id)
    if risk_level and risk_level != "all":
        query = query.filter(RiskFinding.risk_level == risk_level)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            RiskFinding.explanation.ilike(search_fmt) | 
            RiskFinding.rule_name.ilike(search_fmt) |
            RiskFinding.evidence_quote.ilike(search_fmt)
        )

    total = query.count()
    items = query.order_by(RiskFinding.overall_score.desc()).offset(skip).limit(limit).all()

    results = []
    for risk, filename, page_start, category in items:
        results.append({
            "id": risk.id,
            "document_id": risk.document_id,
            "document_name": filename,
            "document_filename": filename,
            "clause_id": risk.clause_id,
            "category": category or "Contract Provision",
            "risk_level": risk.risk_level,
            "rule_name": risk.rule_name,
            "explanation": risk.explanation,
            "evidence_quote": risk.evidence_quote,
            "source_page": page_start or 1,
            "page_start": page_start or 1,
            "suggested_question": risk.suggested_question,
            "uncertainty_note": risk.uncertainty_note,
            "overall_score": risk.overall_score,
            "is_reviewed": risk.is_reviewed
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "risks": results,
        "findings": results
    }

@router.post("/clauses/{clause_id}/review")
def toggle_clause_review(clause_id: str, db: Session = Depends(get_db)):
    """Toggle human review status for a specific clause."""
    clause = db.query(Clause).filter(Clause.id == clause_id).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found.")
    clause.is_reviewed = not clause.is_reviewed
    db.commit()
    return {"status": "success", "clause_id": clause.id, "is_reviewed": clause.is_reviewed}

@router.post("/risks/{risk_id}/review")
def toggle_risk_review(risk_id: str, db: Session = Depends(get_db)):
    """Toggle human review status for a specific risk finding."""
    risk = db.query(RiskFinding).filter(RiskFinding.id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk finding not found.")
    risk.is_reviewed = not risk.is_reviewed
    db.commit()
    return {"status": "success", "risk_id": risk.id, "is_reviewed": risk.is_reviewed}
