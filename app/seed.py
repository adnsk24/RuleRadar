# RuleRadar AI - Database Seeder for Complete Demonstration Suite
import os
from app.db import SessionLocal, init_db
from app.services.document_service import DocumentService

def seed_sample_documents():
    """Seed synthetic sample documents across PDF, DOCX, and TXT into the database."""
    init_db()
    db = SessionLocal()
    try:
        sample_files = [
            ("Rental_Agreement_v1.pdf", "rental"),
            ("Rental_Agreement_v2_Revised.pdf", "rental"),
            ("Employment_Agreement_Executive.docx", "employment"),
            ("Freelance_Consulting_Agreement.pdf", "freelance"),
            ("College_Academic_Policy_Circular.pdf", "college_circular")
        ]

        sample_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_documents")

        for fname, cat in sample_files:
            fpath = os.path.join(sample_dir, fname)
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    content = f.read()
                print(f"Seeding '{fname}' ({cat})...")
                doc = DocumentService.process_and_save_document(
                    db=db,
                    file_bytes=content,
                    original_filename=fname,
                    category=cat
                )
                print(f"  -> Successfully seeded: {doc.filename} (ID: {doc.id})")
        print("Seeding completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_sample_documents()
