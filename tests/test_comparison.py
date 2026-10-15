# RuleRadar AI - Semantic Document Comparison Unit Tests
import pytest
from app.nlp.comparison import DocumentComparator

def test_compare_modified_provisions_with_deadlines_and_amounts():
    doc_a = [
        {
            "id": "c1",
            "clause_number": "Section 2",
            "heading": "Notice Period",
            "original_text": "The employee must provide 30 days notice before resignation.",
            "normalized_text": "The employee must provide 30 days notice before resignation."
        },
        {
            "id": "c2",
            "clause_number": "Section 3",
            "heading": "Rent",
            "original_text": "Monthly rent shall be $1,200.00 due on the first day.",
            "normalized_text": "Monthly rent shall be $1,200.00 due on the first day."
        }
    ]

    doc_b = [
        {
            "id": "c1_b",
            "clause_number": "Section 2",
            "heading": "Notice Period",
            "original_text": "The employee must provide 60 days notice before resignation.",
            "normalized_text": "The employee must provide 60 days notice before resignation."
        },
        {
            "id": "c2_b",
            "clause_number": "Section 3",
            "heading": "Rent",
            "original_text": "Monthly rent shall be $1,450.00 due on the first day.",
            "normalized_text": "Monthly rent shall be $1,450.00 due on the first day."
        },
        {
            "id": "c3_b",
            "clause_number": "Section 4",
            "heading": "New Penalty",
            "original_text": "A late penalty of $100 shall apply.",
            "normalized_text": "A late penalty of $100 shall apply."
        }
    ]

    result = DocumentComparator.compare_documents(doc_a, doc_b)
    
    assert result["counts"]["modified"] == 2
    assert result["counts"]["added"] == 1
    assert result["counts"]["removed"] == 0

    # Verify notice period modification was captured
    mod_notice = next(m for m in result["modified_clauses"] if "Notice" in m["clause_a"]["heading"])
    assert len(mod_notice["changed_deadlines"]) >= 1
    assert "30 days" in mod_notice["changed_deadlines"][0]["previous_value"]
    assert "60 days" in mod_notice["changed_deadlines"][0]["new_value"]

    # Verify rent modification was captured
    mod_rent = next(m for m in result["modified_clauses"] if "Rent" in m["clause_a"]["heading"])
    assert len(mod_rent["changed_financials"]) >= 1
    assert "$1,200.00" in mod_rent["changed_financials"][0]["previous_value"]
    assert "$1,450.00" in mod_rent["changed_financials"][0]["new_value"]
