# RuleRadar AI - Document Ingestion & Analysis Orchestrator Service
import os
import hashlib
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.db import (
    Document, ExtractedPage, Clause, RiskFinding,
    ExtractedEntity, Obligation, Deadline, ComparisonReport
)
from app.nlp import (
    DocumentIngestionPipeline, ClauseSegmenter, ClauseClassifier,
    RiskEngine, ImportanceEngine, InformationExtractor, IngestionError
)

class DocumentService:
    """
    End-to-end service coordinating file validation, text extraction,
    clause segmentation, classification, risk scoring, information extraction,
    and database transactions.
    """

    @classmethod
    def process_and_save_document(
        cls,
        db: Session,
        file_bytes: bytes,
        original_filename: str,
        category: str = "general"
    ) -> Document:
        """
        Ingest, analyze, and persist a document in a single atomic transaction.
        """
        # 1. Compute SHA-256 hash for deduplication and auditability
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing_doc and existing_doc.status == "completed":
            return existing_doc

        # 2. Extract and validate document content
        ingest_result = DocumentIngestionPipeline.process_document(file_bytes, original_filename)
        clean_ext = ingest_result["file_type"]
        pages_data = ingest_result["pages"]
        scanned_warning = ingest_result["scanned_warning"]

        # 3. Save physical file safely
        doc_id = str(uuid.uuid4())
        safe_filename = f"{doc_id}_{os.path.basename(original_filename)}"
        saved_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        # 4. Create database Document record
        doc = Document(
            id=doc_id,
            filename=original_filename,
            file_type=clean_ext,
            file_size=len(file_bytes),
            file_hash=file_hash,
            stored_path=saved_path,
            category=category,
            page_count=len(pages_data),
            status="processing",
            scanned_warning=scanned_warning
        )
        db.add(doc)
        db.flush()

        try:
            # 5. Persist extracted pages
            for p in pages_data:
                db_page = ExtractedPage(
                    document_id=doc_id,
                    page_number=p["page_number"],
                    text_content=p["text"],
                    character_count=p["character_count"],
                    has_images_or_scanned=p["has_images_or_scanned"]
                )
                db.add(db_page)
            db.flush()

            # 6. Segment clauses
            raw_clauses = ClauseSegmenter.segment_document(pages_data)
            if not raw_clauses:
                # Fallback single clause if text was too brief
                raw_clauses = [{
                    "clause_number": "1.0",
                    "heading": "General Document Text",
                    "page_start": 1,
                    "page_end": 1,
                    "start_char": 0,
                    "end_char": len(ingest_result["full_text"]),
                    "original_text": ingest_result["full_text"],
                    "normalized_text": ingest_result["full_text"],
                    "segmentation_confidence": 0.50
                }]

            # 7. Analyze each clause: classify, risk review, importance, obligations
            all_db_clauses: List[Clause] = []
            total_high_risks = 0

            for rc in raw_clauses:
                orig_text = rc["original_text"]
                heading = rc["heading"] or ""

                # Classification
                class_res = ClauseClassifier.classify_clause(orig_text, heading)
                
                # Risk Analysis
                risk_results = RiskEngine.analyze_clause(orig_text, heading, ingest_result["full_text"])
                
                # Importance Scoring
                imp_res = ImportanceEngine.calculate_importance(
                    orig_text,
                    class_res["category"],
                    risk_count=len(risk_results)
                )

                clause_id = str(uuid.uuid4())
                db_clause = Clause(
                    id=clause_id,
                    document_id=doc_id,
                    clause_number=rc["clause_number"],
                    heading=rc["heading"],
                    page_start=rc["page_start"],
                    page_end=rc["page_end"],
                    start_char=rc["start_char"],
                    end_char=rc["end_char"],
                    original_text=orig_text,
                    normalized_text=rc["normalized_text"],
                    category=class_res["category"],
                    category_confidence=class_res["confidence"],
                    category_explanation=class_res["explanation"],
                    importance_score=imp_res["importance_score"],
                    importance_category=imp_res["importance_category"],
                    importance_explanation=imp_res["explanation"],
                    is_reviewed=False
                )
                db.add(db_clause)
                all_db_clauses.append(db_clause)

                # Persist risk findings for this clause
                for rf in risk_results:
                    if rf["risk_level"] == "High attention":
                        total_high_risks += 1
                    db_risk = RiskFinding(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        clause_id=clause_id,
                        risk_level=rf["risk_level"],
                        trigger_type=rf["trigger_type"],
                        rule_name=rf["rule_name"],
                        explanation=rf["explanation"],
                        evidence_quote=rf["evidence_quote"],
                        surrounding_context=rf["surrounding_context"],
                        suggested_question=rf["suggested_question"],
                        uncertainty_note=rf["uncertainty_note"],
                        financial_impact_score=rf["financial_impact_score"],
                        obligation_severity_score=rf["obligation_severity_score"],
                        ambiguity_score=rf["ambiguity_score"],
                        overall_score=rf["overall_score"]
                    )
                    db.add(db_risk)

                # Extract obligations for this clause
                obligations = InformationExtractor.extract_obligations(orig_text)
                for ob in obligations:
                    db_ob = Obligation(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        clause_id=clause_id,
                        responsible_party=ob["responsible_party"],
                        required_action=ob["required_action"],
                        trigger_condition=ob["trigger_condition"],
                        deadline=ob["deadline"],
                        consequence=ob["consequence"],
                        confidence=ob["confidence"]
                    )
                    db.add(db_ob)

                # Extract deadlines for this clause
                deadlines = InformationExtractor.extract_deadlines(orig_text, page_num=rc["page_start"])
                for dl in deadlines:
                    db_dl = Deadline(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        clause_id=clause_id,
                        date_or_period=dl["date_or_period"],
                        context=dl["context"],
                        deadline_type=dl["deadline_type"],
                        page_number=dl["page_number"]
                    )
                    db.add(db_dl)

            # 8. Document-wide entity extraction
            for p in pages_data:
                entities = InformationExtractor.extract_parties_and_entities(p["text"], page_num=p["page_number"])
                for ent in entities:
                    db_ent = ExtractedEntity(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        clause_id=None,
                        entity_type=ent["entity_type"],
                        entity_text=ent["entity_text"],
                        page_number=ent["page_number"],
                        start_offset=ent["start_offset"],
                        end_offset=ent["end_offset"]
                    )
                    db.add(db_ent)

            # 9. Formulate grounded summary
            top_headings = [c.heading for c in all_db_clauses if c.heading][:5]
            summary_text = (
                f"Document '{original_filename}' analyzed successfully. Identified {len(all_db_clauses)} clauses "
                f"across {len(pages_data)} page(s). Key sections include: {', '.join(top_headings) if top_headings else 'General provisions'}."
            )
            if total_high_risks > 0:
                summary_text += f" Flagged {total_high_risks} potential high-attention risk indicator(s) requiring closer review."

            doc.summary = summary_text
            doc.status = "completed"
            db.commit()
            db.refresh(doc)
            return doc

        except Exception as e:
            db.rollback()
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()
            raise

    @classmethod
    def get_document_details(cls, db: Session, doc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full document details with pages, clauses, risks, obligations, and deadlines."""
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return None

        clauses = db.query(Clause).filter(Clause.document_id == doc_id).order_by(Clause.page_start, Clause.start_char).all()
        risks = db.query(RiskFinding).filter(RiskFinding.document_id == doc_id).all()
        entities = db.query(ExtractedEntity).filter(ExtractedEntity.document_id == doc_id).all()
        obligations = db.query(Obligation).filter(Obligation.document_id == doc_id).all()
        deadlines = db.query(Deadline).filter(Deadline.document_id == doc_id).all()
        pages = db.query(ExtractedPage).filter(ExtractedPage.document_id == doc_id).order_by(ExtractedPage.page_number).all()

        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "category": doc.category,
            "page_count": doc.page_count,
            "status": doc.status,
            "summary": doc.summary,
            "scanned_warning": doc.scanned_warning,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "pages": [{
                "page_number": p.page_number,
                "text": p.text_content,
                "character_count": p.character_count,
                "has_images_or_scanned": p.has_images_or_scanned
            } for p in pages],
            "clauses": [{
                "id": c.id,
                "clause_number": c.clause_number,
                "heading": c.heading,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "original_text": c.original_text,
                "category": c.category,
                "category_confidence": c.category_confidence,
                "category_explanation": c.category_explanation,
                "importance_score": c.importance_score,
                "importance_category": c.importance_category,
                "importance_explanation": c.importance_explanation,
                "is_reviewed": c.is_reviewed
            } for c in clauses],
            "risk_findings": [{
                "id": r.id,
                "clause_id": r.clause_id,
                "risk_level": r.risk_level,
                "trigger_type": r.trigger_type,
                "rule_name": r.rule_name,
                "explanation": r.explanation,
                "evidence_quote": r.evidence_quote,
                "surrounding_context": r.surrounding_context,
                "suggested_question": r.suggested_question,
                "uncertainty_note": r.uncertainty_note,
                "overall_score": r.overall_score,
                "is_reviewed": r.is_reviewed
            } for r in risks],
            "obligations": [{
                "id": o.id,
                "clause_id": o.clause_id,
                "responsible_party": o.responsible_party,
                "required_action": o.required_action,
                "trigger_condition": o.trigger_condition,
                "deadline": o.deadline,
                "consequence": o.consequence
            } for o in obligations],
            "deadlines": [{
                "id": d.id,
                "clause_id": d.clause_id,
                "date_or_period": d.date_or_period,
                "context": d.context,
                "deadline_type": d.deadline_type,
                "page_number": d.page_number
            } for d in deadlines],
            "entities": [{
                "id": e.id,
                "entity_type": e.entity_type,
                "entity_text": e.entity_text,
                "page_number": e.page_number
            } for e in entities]
        }

    @classmethod
    def delete_document(cls, db: Session, doc_id: str) -> bool:
        """Permanently delete document, database relations, and physical file."""
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return False

        # Remove physical file if exists
        if doc.stored_path and os.path.exists(doc.stored_path):
            try:
                os.remove(doc.stored_path)
            except OSError:
                pass

        db.delete(doc)
        db.commit()
        return True
