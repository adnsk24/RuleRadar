# RuleRadar AI - Clause Classifier Unit Tests
import pytest
from app.nlp.classifier import ClauseClassifier

def test_classify_governing_law():
    text = "This Agreement shall be governed by and construed in accordance with the laws of the State of California."
    res = ClauseClassifier.classify_clause(text, heading="GOVERNING LAW")
    assert res["category"] == "Governing law and jurisdiction"
    assert res["confidence"] >= 0.70
    assert "explanation" in res

def test_classify_confidentiality():
    text = "Recipient agrees to maintain the strict confidentiality of all proprietary technical secrets and undisclosed data."
    res = ClauseClassifier.classify_clause(text, heading="Non-Disclosure")
    assert res["category"] == "Confidentiality"
    assert res["confidence"] >= 0.60

def test_classify_penalties():
    text = "Failure to submit payment on time incurs a late fee of 5% and liquidated damages of $100 per day of delay."
    res = ClauseClassifier.classify_clause(text, heading="Penalties and Late Charges")
    assert res["category"] == "Penalties and late fees"

def test_classify_termination():
    text = "Either party may terminate this agreement at any time by providing at least 30 days written notice to the other party."
    res = ClauseClassifier.classify_clause(text, heading="Termination")
    assert res["category"] == "Termination and cancellation"

def test_classify_force_majeure():
    text = "Neither party shall be liable for delay caused by acts of God, war, epidemic, earthquake, or unforeseeable events beyond reasonable control."
    res = ClauseClassifier.classify_clause(text, heading="Force Majeure")
    assert res["category"] == "Force majeure"

def test_classify_unclassified_fallback():
    # Gibberish or irrelevant text
    text = "The quick brown fox jumps over the lazy dog without any legal relevance."
    res = ClauseClassifier.classify_clause(text)
    assert res["category"] == "Other or unclassified clauses"
    assert res["confidence"] <= 0.50
