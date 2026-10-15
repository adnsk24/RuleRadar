import pytest
import io
import pymupdf as fitz
from docx import Document as DocxDoc
from app.nlp.ingestion import DocumentIngestionPipeline, IngestionError

def test_validate_and_extract_txt():
    content = "SECTION 1. TERM\nThis lease shall commence on Jan 1, 2026.\n\nSECTION 2. RENT\nRent is $1000.".encode('utf-8')
    res = DocumentIngestionPipeline.process_document(content, "test_agreement.txt")
    assert res["file_type"] == "txt"
    assert res["page_count"] >= 1
    assert "Rent is $1000" in res["full_text"]
    assert res["scanned_warning"] is False

def test_validate_and_extract_pdf():
    # Create an in-memory PDF using PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "SECTION 1. CONFIDENTIALITY\nThe recipient shall maintain strict secrecy.")
    pdf_bytes = doc.tobytes()
    doc.close()

    res = DocumentIngestionPipeline.process_document(pdf_bytes, "test_nda.pdf")
    assert res["file_type"] == "pdf"
    assert res["page_count"] == 1
    assert "maintain strict secrecy" in res["full_text"]
    assert res["scanned_warning"] is False

def test_validate_and_extract_docx():
    # Create an in-memory DOCX
    docx_doc = DocxDoc()
    docx_doc.add_heading("1. Payment Terms", level=1)
    docx_doc.add_paragraph("Payment is due within 30 days of invoice.")
    buffer = io.BytesIO()
    docx_doc.save(buffer)
    docx_bytes = buffer.getvalue()

    res = DocumentIngestionPipeline.process_document(docx_bytes, "invoice_terms.docx")
    assert res["file_type"] == "docx"
    assert "Payment is due within 30 days" in res["full_text"]

def test_reject_empty_file():
    with pytest.raises(IngestionError, match="empty"):
        DocumentIngestionPipeline.validate_file(b"", "empty.txt")

def test_reject_unsupported_format():
    with pytest.raises(IngestionError, match="Unsupported file extension"):
        DocumentIngestionPipeline.validate_file(b"test", "script.exe")

def test_reject_spoofed_pdf():
    fake_pdf = b"This is not a real pdf file"
    with pytest.raises(IngestionError, match="lacks valid PDF signature"):
        DocumentIngestionPipeline.validate_file(fake_pdf, "malicious.pdf")

def test_scanned_pdf_heuristic():
    # PDF with an image and no text
    doc = fitz.open()
    page = doc.new_page()
    # Insert a 10x10 pixmap
    pix = fitz.Pixmap(fitz.csRGB, (0, 0, 10, 10), 1)
    page.insert_image(page.rect, pixmap=pix)
    pdf_bytes = doc.tobytes()
    doc.close()

    res = DocumentIngestionPipeline.process_document(pdf_bytes, "scanned_doc.pdf")
    assert res["scanned_warning"] is True
