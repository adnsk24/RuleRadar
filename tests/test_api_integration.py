# RuleRadar AI - End-to-End API Integration Tests
import pytest
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_health_check():
    res = client.get("/api/system/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data
    assert "database" in data["components"]

def test_api_dashboard_stats():
    res = client.get("/api/system/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_documents" in data
    assert "important_clauses" in data

def test_api_upload_and_full_workflow():
    # 1. Upload a document
    doc_content = (
        "SECTION 1. TERM\n"
        "This agreement shall commence on April 1, 2026 for a term of 1 year.\n\n"
        "SECTION 2. COMPENSATION\n"
        "Client shall pay Contractor $5,000.00 upon milestone completion.\n\n"
        "SECTION 3. TERMINATION\n"
        "Either party may terminate immediately without cause. Company reserves the right to modify terms at any time without prior notice."
    ).encode('utf-8')

    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("integration_test_agreement.txt", doc_content, "text/plain")},
        data={"category": "business"}
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()["document"]
    doc_id = doc_data["id"]
    assert doc_id is not None

    # 2. Get document details
    get_res = client.get(f"/api/documents/{doc_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert len(detail["clauses"]) >= 2
    assert len(detail["risk_findings"]) >= 1

    # 3. Ask question via QA
    qa_res = client.post(
        "/api/qa",
        json={"document_id": doc_id, "question": "What is the compensation?"}
    )
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert "$5,000.00" in qa_data["answer"]
    assert len(qa_data["citations"]) >= 1

    # 4. Export PDF report
    pdf_res = client.get(f"/api/export/{doc_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 500

    # 5. Export DOCX report
    docx_res = client.get(f"/api/export/{doc_id}/docx")
    assert docx_res.status_code == 200
    assert "wordprocessingml" in docx_res.headers["content-type"]
    assert len(docx_res.content) > 500

    # 6. Delete document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200

    # Verify deleted
    verify_res = client.get(f"/api/documents/{doc_id}")
    assert verify_res.status_code == 404
