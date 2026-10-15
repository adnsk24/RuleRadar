# RuleRadar AI - Risk & Importance Engine Unit Tests
import pytest
from app.nlp.risk_engine import RiskEngine
from app.nlp.importance_engine import ImportanceEngine

def test_detect_unilateral_modification():
    text = "Company reserves the right to modify these terms and pricing at any time without prior notice."
    findings = RiskEngine.analyze_clause(text)
    assert len(findings) >= 1
    assert any(f["trigger_type"] == "unilateral_modification" for f in findings)
    f = next(f for f in findings if f["trigger_type"] == "unilateral_modification")
    assert f["risk_level"] == "High attention"
    assert "evidence_quote" in f
    assert "suggested_question" in f
    assert f["overall_score"] >= 0.60

def test_detect_broad_indemnity():
    text = "Contractor agrees to indemnify and hold harmless the Client against all claims and damages arising from the project."
    findings = RiskEngine.analyze_clause(text)
    assert any(f["trigger_type"] == "broad_indemnification" for f in findings)

def test_detect_excessive_penalty():
    text = "In the event of default, Tenant shall forfeit the entire deposit and pay liquidated damages of $5,000."
    findings = RiskEngine.analyze_clause(text)
    assert any(f["trigger_type"] == "excessive_penalty" for f in findings)

def test_detect_auto_renewal_trap():
    text = "This contract automatically renews unless written non-renewal notice is delivered 90 days prior to term expiration."
    findings = RiskEngine.analyze_clause(text)
    assert any(f["trigger_type"] == "auto_renewal_trap" for f in findings)

def test_safe_clause_no_false_alarm():
    # A standard reasonable termination clause should not trigger unilateral modification or broad indemnity
    text = "Either party may terminate this agreement upon 30 days mutual written notice."
    findings = RiskEngine.analyze_clause(text)
    # Should not trigger unilateral modification or excessive penalties
    assert not any(f["trigger_type"] in ["unilateral_modification", "excessive_penalty"] for f in findings)

def test_importance_scoring():
    text = "Tenant shall pay monthly rent of $1,500.00 within 5 days of invoice."
    imp = ImportanceEngine.calculate_importance(text, "Payment and financial obligations")
    assert imp["importance_score"] >= 6.0
    assert imp["importance_category"] in ["Medium", "High"]
    assert "financial value" in imp["explanation"].lower()
