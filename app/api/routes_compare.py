# RuleRadar AI - Document Semantic Comparison API Routes
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import json
import uuid
from app.db import get_db, Document, Clause, ComparisonReport
from app.nlp.comparison import DocumentComparator
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/compare", tags=["Comparison"])

@router.post("")
def compare_documents(
    doc_a_id: str = Body(..., embed=True),
    doc_b_id: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Compare Document A (Previous version) with Document B (New version) by their IDs.
    Returns categorized changes: additions, removals, modifications, unchanged, with diffs.
    """
    doc_a = db.query(Document).filter(Document.id == doc_a_id).first()
    doc_b = db.query(Document).filter(Document.id == doc_b_id).first()

    if not doc_a or not doc_b:
        raise HTTPException(status_code=404, detail="One or both document IDs could not be found.")

    clauses_a_db = db.query(Clause).filter(Clause.document_id == doc_a_id).order_by(Clause.page_start, Clause.start_char).all()
    clauses_b_db = db.query(Clause).filter(Clause.document_id == doc_b_id).order_by(Clause.page_start, Clause.start_char).all()

    clauses_a = [{
        "id": c.id,
        "clause_number": c.clause_number,
        "heading": c.heading,
        "page_start": c.page_start,
        "original_text": c.original_text,
        "normalized_text": c.normalized_text,
        "category": c.category
    } for c in clauses_a_db]

    clauses_b = [{
        "id": c.id,
        "clause_number": c.clause_number,
        "heading": c.heading,
        "page_start": c.page_start,
        "original_text": c.original_text,
        "normalized_text": c.normalized_text,
        "category": c.category
    } for c in clauses_b_db]

    report = DocumentComparator.compare_documents(clauses_a, clauses_b)

    # Persist report for future retrieval
    db_report = ComparisonReport(
        id=str(uuid.uuid4()),
        doc_a_id=doc_a_id,
        doc_b_id=doc_b_id,
        added_clauses_count=report["counts"]["added"],
        removed_clauses_count=report["counts"]["removed"],
        modified_clauses_count=report["counts"]["modified"],
        identical_clauses_count=report["counts"]["identical"],
        summary_text=report["summary"],
        details_json=json.dumps(report, default=str)
    )
    db.add(db_report)
    db.commit()

    return {
        "report_id": db_report.id,
        "doc_a": {"id": doc_a.id, "filename": doc_a.filename},
        "doc_b": {"id": doc_b.id, "filename": doc_b.filename},
        "comparison": report
    }

@router.get("/{report_id}")
def get_comparison_report(report_id: str, db: Session = Depends(get_db)):
    """Fetch previously generated comparison report."""
    rep = db.query(ComparisonReport).filter(ComparisonReport.id == report_id).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Comparison report not found.")

    doc_a = db.query(Document).filter(Document.id == rep.doc_a_id).first()
    doc_b = db.query(Document).filter(Document.id == rep.doc_b_id).first()

    return {
        "report_id": rep.id,
        "doc_a": {"id": rep.doc_a_id, "filename": doc_a.filename if doc_a else "Document A"},
        "doc_b": {"id": rep.doc_b_id, "filename": doc_b.filename if doc_b else "Document B"},
        "created_at": rep.created_at.isoformat(),
        "comparison": json.loads(rep.details_json)
    }
