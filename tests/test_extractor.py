# RuleRadar AI - Structured Information Extractor Unit Tests
import pytest
from app.nlp.extractor import InformationExtractor

def test_extract_financials():
    text = "The monthly rent is $1,450.00 per month, plus a security deposit of USD 2,900 and a 5% late fee."
    fin = InformationExtractor.extract_financials(text)
    assert len(fin) >= 2
    amounts = [f["amount_or_percentage"] for f in fin]
    assert any("$1,450.00" in a or "1,450" in a for a in amounts)
    assert any("2,900" in a for a in amounts)
    assert any("5%" in a for a in amounts)

def test_extract_deadlines():
    text = "Tenant must provide 60 days' written notice prior to departure, and payment is due within 10 business days."
    deadlines = InformationExtractor.extract_deadlines(text, page_num=1)
    assert len(deadlines) >= 1
    d_texts = [d["date_or_period"].lower() for d in deadlines]
    assert any("60 days" in d for d in d_texts) or any("within 10 business days" in d for d in d_texts)

def test_extract_obligations():
    text = "Tenant shall maintain the leased premises in good repair and must notify Landlord within 48 hours of any leaks."
    obs = InformationExtractor.extract_obligations(text)
    assert len(obs) >= 1
    assert any("maintain" in o["required_action"] or "notify" in o["required_action"] for o in obs)
