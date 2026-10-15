# RuleRadar AI - Grounded Q&A Unit Tests
import pytest
from app.nlp.qa_engine import DocumentQAEngine

def test_qa_answer_with_exact_citation():
    clauses = [
        {
            "id": "c1",
            "clause_number": "Section 4",
            "heading": "Security Deposit",
            "page_start": 2,
            "original_text": "Tenant shall deposit $2,400.00 as a security deposit refundable within 30 days after vacancy.",
            "normalized_text": "Tenant shall deposit $2,400.00 as a security deposit refundable within 30 days after vacancy."
        },
        {
            "id": "c2",
            "clause_number": "Section 5",
            "heading": "Pet Policy",
            "page_start": 3,
            "original_text": "No pets of any kind shall be permitted on the premises.",
            "normalized_text": "No pets of any kind shall be permitted on the premises."
        }
    ]

    res = DocumentQAEngine.answer_question("What is the security deposit amount?", clauses)
    assert res["intent"] == "grounded_answer"
    assert "$2,400.00" in res["answer"]
    assert len(res["citations"]) >= 1
    assert res["citations"][0]["page"] == 2
    assert "Section 4" in res["citations"][0]["clause_number"]

def test_qa_unanswered_topic():
    clauses = [
        {
            "id": "c1",
            "clause_number": "Section 1",
            "heading": "Term",
            "page_start": 1,
            "original_text": "The lease term commences February 1, 2026.",
            "normalized_text": "The lease term commences February 1, 2026."
        }
    ]

    res = DocumentQAEngine.answer_question("What are the intellectual property guidelines for software code?", clauses)
    assert res["intent"] == "not_found"
    assert "no clauses were found" in res["answer"].lower()
    assert len(res["citations"]) == 0

def test_qa_conversational_greetings():
    res = DocumentQAEngine.answer_question("Hello there!", [])
    assert res["intent"] == "greeting"
    assert "RuleRadar AI" in res["answer"]

def test_qa_legal_advice_disclaimer():
    res = DocumentQAEngine.answer_question("Is this contract legally valid in court?", [])
    assert res["intent"] == "legal_advice_disclaimer"
    assert "Disclaimer" in res["answer"]
