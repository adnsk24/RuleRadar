# RuleRadar AI - Database Models
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.db.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, txt
    file_size = Column(Integer, nullable=False)     # in bytes
    file_hash = Column(String(64), nullable=False, index=True) # SHA-256
    stored_path = Column(String(512), nullable=False)
    category = Column(String(50), default="general") # rental, employment, freelance, business, terms, college_circular, gov_policy, general
    page_count = Column(Integer, default=1)
    status = Column(String(30), default="uploaded", index=True) # uploaded, processing, completed, failed
    error_message = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    scanned_warning = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships with cascade delete
    pages = relationship("ExtractedPage", back_populates="document", cascade="all, delete-orphan")
    clauses = relationship("Clause", back_populates="document", cascade="all, delete-orphan")
    risk_findings = relationship("RiskFinding", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("ExtractedEntity", back_populates="document", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="document", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="document", cascade="all, delete-orphan")
    qa_sessions = relationship("QASession", back_populates="document", cascade="all, delete-orphan")

class ExtractedPage(Base):
    __tablename__ = "extracted_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    character_count = Column(Integer, default=0)
    has_images_or_scanned = Column(Boolean, default=False)

    document = relationship("Document", back_populates="pages")

class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_number = Column(String(50), nullable=True) # e.g. "1.1", "Section 4"
    heading = Column(String(255), nullable=True)
    page_start = Column(Integer, default=1)
    page_end = Column(Integer, default=1)
    start_char = Column(Integer, default=0)
    end_char = Column(Integer, default=0)
    
    original_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    
    category = Column(String(100), default="Other or unclassified clauses", index=True)
    category_confidence = Column(Float, default=0.0)
    category_explanation = Column(Text, nullable=True)
    
    importance_score = Column(Float, default=0.0) # 0.0 - 10.0
    importance_category = Column(String(20), default="Low") # High, Medium, Low
    importance_explanation = Column(Text, nullable=True)
    
    is_reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    document = relationship("Document", back_populates="clauses")
    risk_findings = relationship("RiskFinding", back_populates="clause", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="clause", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="clause", cascade="all, delete-orphan")

class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(String(36), ForeignKey("clauses.id", ondelete="CASCADE"), nullable=True, index=True)
    
    risk_level = Column(String(30), nullable=False, index=True) # High attention, Needs review, Informational, Uncertain
    trigger_type = Column(String(100), nullable=False)
    rule_name = Column(String(150), nullable=False)
    explanation = Column(Text, nullable=False)
    evidence_quote = Column(Text, nullable=False)
    surrounding_context = Column(Text, nullable=True)
    suggested_question = Column(Text, nullable=False)
    uncertainty_note = Column(Text, nullable=True)
    
    # Granular scoring dimensions
    financial_impact_score = Column(Float, default=0.0)
    obligation_severity_score = Column(Float, default=0.0)
    ambiguity_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    
    is_reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    document = relationship("Document", back_populates="risk_findings")
    clause = relationship("Clause", back_populates="risk_findings")

class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(String(36), ForeignKey("clauses.id", ondelete="SET NULL"), nullable=True)
    
    entity_type = Column(String(50), nullable=False) # PARTY, PERSON, ORG, GPE, DATE, MONEY, PERCENT, LAW, ROLE
    entity_text = Column(String(255), nullable=False)
    page_number = Column(Integer, default=1)
    start_offset = Column(Integer, default=0)
    end_offset = Column(Integer, default=0)

    document = relationship("Document", back_populates="entities")

class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(String(36), ForeignKey("clauses.id", ondelete="CASCADE"), nullable=True)
    
    responsible_party = Column(String(100), default="Not specified")
    required_action = Column(Text, nullable=False)
    trigger_condition = Column(Text, nullable=True)
    deadline = Column(String(200), nullable=True)
    consequence = Column(Text, nullable=True)
    confidence = Column(Float, default=0.8)

    document = relationship("Document", back_populates="obligations")
    clause = relationship("Clause", back_populates="obligations")

class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(String(36), ForeignKey("clauses.id", ondelete="CASCADE"), nullable=True)
    
    date_or_period = Column(String(255), nullable=False)
    context = Column(Text, nullable=False)
    deadline_type = Column(String(100), default="Notice / Action Deadline")
    page_number = Column(Integer, default=1)

    document = relationship("Document", back_populates="deadlines")
    clause = relationship("Clause", back_populates="deadlines")

class ComparisonReport(Base):
    __tablename__ = "comparison_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    doc_a_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_b_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    added_clauses_count = Column(Integer, default=0)
    removed_clauses_count = Column(Integer, default=0)
    modified_clauses_count = Column(Integer, default=0)
    identical_clauses_count = Column(Integer, default=0)
    summary_text = Column(Text, nullable=True)
    details_json = Column(Text, nullable=False) # JSON list of clause comparisons & detected substantive changes
    
    created_at = Column(DateTime, default=utc_now)

class QASession(Base):
    __tablename__ = "qa_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]") # JSON list of citations
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)

    document = relationship("Document", back_populates="qa_sessions")

# Create composite indexes for fast querying
Index("ix_clauses_doc_importance", Clause.document_id, Clause.importance_score)
Index("ix_risks_doc_level", RiskFinding.document_id, RiskFinding.risk_level)
