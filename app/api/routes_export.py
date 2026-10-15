# RuleRadar AI - Export API Routes
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.document_service import DocumentService
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["Export"])

@router.get("/{doc_id}/pdf")
def export_pdf_report(doc_id: str, db: Session = Depends(get_db)):
    """Generate and download styled PDF report."""
    doc_data = DocumentService.get_document_details(db, doc_id)
    if not doc_data:
        raise HTTPException(status_code=404, detail="Document not found.")

    pdf_bytes = ExportService.generate_pdf_report(doc_data)
    safe_name = f"RuleRadar_Report_{doc_id[:8]}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"}
    )

@router.get("/{doc_id}/docx")
def export_docx_report(doc_id: str, db: Session = Depends(get_db)):
    """Generate and download editable Microsoft Word (.docx) report."""
    doc_data = DocumentService.get_document_details(db, doc_id)
    if not doc_data:
        raise HTTPException(status_code=404, detail="Document not found.")

    docx_bytes = ExportService.generate_docx_report(doc_data)
    safe_name = f"RuleRadar_Report_{doc_id[:8]}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"}
    )

@router.get("/{doc_id}/json")
def export_json_report(doc_id: str, db: Session = Depends(get_db)):
    """Download full structured analysis data as JSON."""
    doc_data = DocumentService.get_document_details(db, doc_id)
    if not doc_data:
        raise HTTPException(status_code=404, detail="Document not found.")

    json_str = ExportService.generate_json_report(doc_data)
    safe_name = f"RuleRadar_Report_{doc_id[:8]}.json"

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={safe_name}"}
    )
