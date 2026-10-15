# RuleRadar AI - Question Answering API Routes
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import uuid
from app.db import get_db, Document, Clause, QASession
from app.nlp.qa_engine import DocumentQAEngine

router = APIRouter(prefix="/api/qa", tags=["Question Answering"])

@router.post("")
def ask_question(
    document_id: str = Body(..., embed=True),
    question: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Ask a question regarding a specific document.
    Returns evidence-grounded answer with verbatim quotations and source citations.
    """
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    clauses_db = db.query(Clause).filter(Clause.document_id == document_id).order_by(Clause.page_start, Clause.start_char).all()
    clauses = [{
        "id": c.id,
        "clause_number": c.clause_number,
        "heading": c.heading,
        "page_start": c.page_start,
        "page_end": c.page_end,
        "original_text": c.original_text,
        "normalized_text": c.normalized_text,
        "category": c.category,
        "importance_score": c.importance_score
    } for c in clauses_db]

    doc_meta = {
        "id": doc.id,
        "filename": doc.filename,
        "page_count": doc.page_count,
        "category": doc.category
    }

    qa_result = DocumentQAEngine.answer_question(question, clauses, doc_meta)

    # Save session
    session_id = str(uuid.uuid4())
    qa_record = QASession(
        id=session_id,
        document_id=document_id,
        question=question,
        answer=qa_result["answer"],
        citations_json=json.dumps(qa_result.get("citations", []), default=str),
        confidence=qa_result.get("confidence", 0.0)
    )
    db.add(qa_record)
    db.commit()

    return {
        "session_id": session_id,
        "question": question,
        "answer": qa_result["answer"],
        "citations": qa_result.get("citations", []),
        "confidence": qa_result.get("confidence", 0.0),
        "intent": qa_result.get("intent", "answer")
    }

@router.get("/{document_id}/history")
def get_qa_history(document_id: str, db: Session = Depends(get_db)):
    """Retrieve question and answer history for a document."""
    records = db.query(QASession).filter(QASession.document_id == document_id).order_by(QASession.created_at.asc()).all()
    return {
        "history": [{
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "citations": json.loads(r.citations_json) if r.citations_json else [],
            "confidence": r.confidence,
            "created_at": r.created_at.isoformat()
        } for r in records]
    }
