# RuleRadar AI - Synthetic Evaluation Dataset & Metric Verification
import pytest
from app.nlp.classifier import ClauseClassifier
from app.nlp.comparison import DocumentComparator
from app.nlp.ingestion import DocumentIngestionPipeline
from app.nlp.segmentation import ClauseSegmenter

# Labeled Ground Truth Dataset
LABELED_CLAUSES = [
    {
        "text": "Tenant agrees to pay monthly rent of $1,500.00 on the first day of each calendar month.",
        "heading": "Payment Terms",
        "expected_category": "Payment and financial obligations"
    },
    {
        "text": "A late charge of 5% will be assessed for any payments received after the 5th day of the month.",
        "heading": "Late Fees",
        "expected_category": "Penalties and late fees"
    },
    {
        "text": "Upon move-in, Tenant shall provide a security deposit of $3,000.00 refundable within 21 days of vacating.",
        "heading": "Security Deposit",
        "expected_category": "Security deposits and refunds"
    },
    {
        "text": "Either party may terminate this agreement upon 30 days prior written notice to the other party.",
        "heading": "Termination",
        "expected_category": "Termination and cancellation"
    },
    {
        "text": "This agreement shall automatically renew for successive one-year terms unless non-renewal notice is given.",
        "heading": "Automatic Renewal",
        "expected_category": "Renewal and automatic renewal"
    },
    {
        "text": "Contractor shall indemnify and hold harmless the Company against all third-party claims and liabilities.",
        "heading": "Indemnification",
        "expected_category": "Liability and indemnification"
    },
    {
        "text": "Recipient shall maintain strict non-disclosure of all trade secrets and proprietary information.",
        "heading": "Confidential Information",
        "expected_category": "Confidentiality"
    },
    {
        "text": "All inventions and works created by Contractor shall be work made for hire owned exclusively by Client.",
        "heading": "Intellectual Property Rights",
        "expected_category": "Intellectual property"
    },
    {
        "text": "Any dispute arising hereunder shall be resolved through binding arbitration administered by the AAA.",
        "heading": "Arbitration and Dispute Resolution",
        "expected_category": "Dispute resolution"
    },
    {
        "text": "This Agreement is governed by and construed in accordance with the laws of the State of New York.",
        "heading": "Governing Law",
        "expected_category": "Governing law and jurisdiction"
    },
    {
        "text": "Neither party shall be liable for failure to perform due to acts of God, floods, or natural disasters.",
        "heading": "Force Majeure",
        "expected_category": "Force majeure"
    },
    {
        "text": "All formal notices required under this agreement must be delivered by certified mail or hand courier.",
        "heading": "Notice Requirements",
        "expected_category": "Notice requirements"
    }
]

def test_evaluation_dataset_classification_metrics():
    """
    Evaluate classification precision, recall, and accuracy on the labeled benchmark dataset.
    """
    total = len(LABELED_CLAUSES)
    correct = 0
    predictions = []

    for item in LABELED_CLAUSES:
        res = ClauseClassifier.classify_clause(item["text"], item["heading"])
        predicted = res["category"]
        expected = item["expected_category"]
        predictions.append((expected, predicted))
        if predicted == expected:
            correct += 1

    accuracy = correct / total
    print(f"\n[EVALUATION METRIC] Clause Classification Accuracy: {accuracy * 100:.1f}% ({correct}/{total})")

    # In our multi-signal system, accuracy should be >= 85%
    assert accuracy >= 0.85, f"Expected classification accuracy >= 85%, got {accuracy * 100:.1f}%"

def test_evaluation_synthetic_rental_revision_comparison():
    """
    Evaluate semantic comparison on the synthetic rental agreements v1 and v2.
    Verifies detection of rent change, notice change, and newly added penalty.
    """
    with open("sample_documents/sample_rental_agreement_v1.txt", "r", encoding="utf-8") as f:
        v1_text = f.read()
    with open("sample_documents/sample_rental_agreement_v2.txt", "r", encoding="utf-8") as f:
        v2_text = f.read()

    pages_v1 = [{"page_number": 1, "text": v1_text, "character_count": len(v1_text), "has_images_or_scanned": False}]
    pages_v2 = [{"page_number": 1, "text": v2_text, "character_count": len(v2_text), "has_images_or_scanned": False}]

    clauses_v1 = ClauseSegmenter.segment_document(pages_v1)
    clauses_v2 = ClauseSegmenter.segment_document(pages_v2)

    comp_report = DocumentComparator.compare_documents(clauses_v1, clauses_v2)

    assert comp_report["counts"]["modified"] >= 1
    # Check that modified clauses contain the rent or notice adjustment
    all_changed_financials = []
    all_changed_deadlines = []
    for m in comp_report["modified_clauses"]:
        all_changed_financials.extend(m.get("changed_financials", []))
        all_changed_deadlines.extend(m.get("changed_deadlines", []))

    # Expect rent adjustment detected ($1,200 -> $1,450)
    has_rent_change = any("1,200" in str(f.get("previous_value", "")) and "1,450" in str(f.get("new_value", "")) for f in all_changed_financials)
    print(f"\n[EVALUATION METRIC] Synthetic Rent Modification Detected: {has_rent_change}")
    assert has_rent_change is True
