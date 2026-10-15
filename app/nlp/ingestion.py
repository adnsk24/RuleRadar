import os
import io
import re
import zipfile
import unicodedata
from typing import List, Dict, Any, Tuple
import pymupdf as fitz  # PyMuPDF
from docx import Document as DocxDocument
from app.config import settings

class IngestionError(Exception):
    """Custom exception for ingestion and validation failures."""
    pass

class DocumentIngestionPipeline:
    """Robust document ingestion pipeline supporting PDF, DOCX, and TXT with security validation."""

    MAGIC_BYTES = {
        "pdf": b"%PDF",
        "zip": b"PK\x03\x04"  # DOCX is a zipped XML package
    }

    @classmethod
    def validate_file(cls, file_bytes: bytes, original_filename: str) -> str:
        """
        Validate file format, magic bytes, file size, and reject dangerous or corrupt files.
        Returns the confirmed file extension ('pdf', 'docx', 'txt').
        """
        # 1. Size check
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > settings.MAX_FILE_SIZE_MB:
            raise IngestionError(f"File size ({size_mb:.1f} MB) exceeds maximum allowed limit of {settings.MAX_FILE_SIZE_MB} MB.")
        
        if len(file_bytes) == 0:
            raise IngestionError("Uploaded file is completely empty (0 bytes).")

        # 2. Extract and sanitize extension
        _, ext = os.path.splitext(original_filename.lower())
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise IngestionError(f"Unsupported file extension '{ext}'. Supported formats: {', '.join(settings.ALLOWED_EXTENSIONS)}.")

        clean_type = ext.lstrip(".")

        # 3. Magic number verification
        if clean_type == "pdf":
            if not file_bytes.startswith(cls.MAGIC_BYTES["pdf"]):
                raise IngestionError("File has .pdf extension but lacks valid PDF signature (magic bytes). Potential corrupted or spoofed file.")
        elif clean_type == "docx":
            if not file_bytes.startswith(cls.MAGIC_BYTES["zip"]):
                raise IngestionError("File has .docx extension but is not a valid OpenXML Zip container.")
            # Verify internal structure
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    names = zf.namelist()
                    if "word/document.xml" not in names:
                        raise IngestionError("Invalid DOCX format: missing word/document.xml.")
            except zipfile.BadZipFile:
                raise IngestionError("Corrupted DOCX file: unable to read zip structure.")
        elif clean_type == "txt":
            # Test encoding decoding without crash
            decoded = False
            for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                try:
                    file_bytes.decode(encoding)
                    decoded = True
                    break
                except UnicodeDecodeError:
                    continue
            if not decoded:
                raise IngestionError("Unable to decode text file. Ensure it is encoded in UTF-8 or standard Latin text.")

        return clean_type

    @classmethod
    def extract_from_pdf(cls, file_bytes: bytes) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Extract text page-by-page from PDF using PyMuPDF.
        Preserves page numbers, paragraph blocks, and checks for scanned/low-text pages.
        Returns: (pages_data, scanned_warning)
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise IngestionError(f"PyMuPDF failed to parse PDF document: {str(e)}")

        page_count = len(doc)
        if page_count == 0:
            raise IngestionError("PDF contains 0 pages.")
        if page_count > settings.MAX_PDF_PAGES:
            raise IngestionError(f"PDF page count ({page_count}) exceeds limit of {settings.MAX_PDF_PAGES} pages.")

        pages_data = []
        total_text_length = 0
        total_image_count = 0

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]
            
            # Extract text via structured layout blocks to preserve natural paragraph boundaries
            blocks = page.get_text("blocks")
            text_blocks = [b[4].strip() for b in blocks if len(b) > 4 and b[6] == 0 and b[4].strip()]
            if text_blocks:
                page_text = "\n\n".join(text_blocks)
            else:
                page_text = page.get_text("text") or ""

            images = page.get_images()
            total_image_count += len(images)
            
            # Normalize whitespace
            norm_text = cls.normalize_text(page_text)
            char_count = len(norm_text)
            total_text_length += char_count

            is_scanned_candidate = (char_count < 30 and len(images) > 0)

            pages_data.append({
                "page_number": page_num,
                "text": norm_text,
                "original_text": page_text,
                "character_count": char_count,
                "has_images_or_scanned": is_scanned_candidate
            })

        doc.close()

        # Scanned document heuristic: very low text density across document while images are present
        avg_chars_per_page = total_text_length / max(1, page_count)
        scanned_warning = False
        if avg_chars_per_page < 40 and (total_image_count > 0 or total_text_length < 100):
            scanned_warning = True

        return pages_data, scanned_warning

    @classmethod
    def extract_from_docx(cls, file_bytes: bytes) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Extract text from DOCX preserving paragraphs, headings, and tables.
        Returns: (pages_data, scanned_warning)
        """
        try:
            doc = DocxDocument(io.BytesIO(file_bytes))
        except Exception as e:
            raise IngestionError(f"python-docx failed to open document: {str(e)}")

        extracted_lines = []

        # 1. Process paragraphs
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            # Check if paragraph has heading style
            style_name = (p.style.name or "").lower()
            if "heading" in style_name or "title" in style_name:
                extracted_lines.append(f"### {text}")
            else:
                extracted_lines.append(text)

        # 2. Process tables
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                # Avoid duplicate adjacent cells from merged table cells
                dedup_cells = []
                for c in cells:
                    if not dedup_cells or dedup_cells[-1] != c:
                        dedup_cells.append(c)
                if any(dedup_cells):
                    table_rows.append(" | ".join(dedup_cells))
            if table_rows:
                extracted_lines.append("\n[TABLE]\n" + "\n".join(table_rows) + "\n[/TABLE]\n")

        full_text = "\n\n".join(extracted_lines)
        norm_text = cls.normalize_text(full_text)

        if not norm_text.strip():
            raise IngestionError("The DOCX document contains no readable text.")

        # Estimate virtual pages (approx 2500 characters per page)
        pages_data = cls._paginate_text(norm_text)
        return pages_data, False

    @classmethod
    def extract_from_txt(cls, file_bytes: bytes) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Extract text from plain text file with automatic encoding detection.
        Returns: (pages_data, scanned_warning)
        """
        raw_text = None
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252", "utf-16"]:
            try:
                raw_text = file_bytes.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if raw_text is None:
            raise IngestionError("Failed to decode text file with standard encodings.")

        norm_text = cls.normalize_text(raw_text)
        if not norm_text.strip():
            raise IngestionError("The TXT document is empty or contains only whitespace.")

        pages_data = cls._paginate_text(norm_text)
        return pages_data, False

    @classmethod
    def _paginate_text(cls, text: str, chars_per_page: int = 2500) -> List[Dict[str, Any]]:
        """Split unpaginated text (DOCX/TXT) into structured virtual pages for uniform handling."""
        paragraphs = text.split("\n\n")
        pages = []
        current_page_lines = []
        current_char_count = 0
        current_page_num = 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_len = len(para)
            if current_char_count + para_len > chars_per_page and current_page_lines:
                page_content = "\n\n".join(current_page_lines)
                pages.append({
                    "page_number": current_page_num,
                    "text": page_content,
                    "original_text": page_content,
                    "character_count": len(page_content),
                    "has_images_or_scanned": False
                })
                current_page_num += 1
                current_page_lines = [para]
                current_char_count = para_len
            else:
                current_page_lines.append(para)
                current_char_count += para_len + 2

        if current_page_lines:
            page_content = "\n\n".join(current_page_lines)
            pages.append({
                "page_number": current_page_num,
                "text": page_content,
                "original_text": page_content,
                "character_count": len(page_content),
                "has_images_or_scanned": False
            })

        return pages if pages else [{
            "page_number": 1,
            "text": text,
            "original_text": text,
            "character_count": len(text),
            "has_images_or_scanned": False
        }]

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Normalize Unicode (NFKC), clean Windows line returns, collapse excessive blank lines
        while strictly preserving original textual content and paragraph integrity.
        """
        if not text:
            return ""
        # 1. Unicode normalization
        text = unicodedata.normalize("NFKC", text)
        # 2. Line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 3. Clean trailing whitespace per line
        lines = [line.strip() for line in text.split("\n")]
        # 4. Collapse consecutive empty lines (max 2)
        collapsed = []
        consecutive_empty = 0
        for line in lines:
            if not line:
                consecutive_empty += 1
                if consecutive_empty <= 2:
                    collapsed.append("")
            else:
                consecutive_empty = 0
                collapsed.append(line)
        return "\n".join(collapsed).strip()

    @classmethod
    def process_document(cls, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Complete ingestion orchestrator: validates, extracts, and paginates.
        """
        clean_type = cls.validate_file(file_bytes, filename)
        
        if clean_type == "pdf":
            pages, scanned_warning = cls.extract_from_pdf(file_bytes)
        elif clean_type == "docx":
            pages, scanned_warning = cls.extract_from_docx(file_bytes)
        elif clean_type == "txt":
            pages, scanned_warning = cls.extract_from_txt(file_bytes)
        else:
            raise IngestionError(f"Unhandled file type: {clean_type}")

        full_text = "\n\n".join(p["text"] for p in pages)
        total_chars = sum(p["character_count"] for p in pages)

        return {
            "file_type": clean_type,
            "page_count": len(pages),
            "total_characters": total_chars,
            "pages": pages,
            "full_text": full_text,
            "scanned_warning": scanned_warning
        }
