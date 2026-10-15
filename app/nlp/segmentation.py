# RuleRadar AI - Clause and Heading Segmentation Engine
import re
from typing import List, Dict, Any, Optional

class ClauseSegmenter:
    """
    Intelligent clause segmentation engine that detects numbered sections,
    articles, headings, bullet-points, and contractual paragraphs.
    Preserves page boundaries, source character offsets, and traceability.
    """

    # Heading / Section match patterns
    SECTION_PATTERNS = [
        # E.g. "Section 1.2", "SECTION 4", "Section 12 - Termination"
        r'^(?P<prefix>SECTION|Section|ARTICLE|Article|CLAUSE|Clause)\s+(?P<num>[0-9IVXLCDM]+(?:\.[0-9a-zA-Z]+)*)(?:\s*[:.\-—]\s*(?P<title>.*))?$',
        # E.g. "1. Term and Termination", "2.3 Rent Amount", "IV. Confidentiality"
        r'^(?P<num>[0-9IVXLCDM]+(?:\.[0-9a-zA-Z]+)*)\.\s+(?P<title>[A-Z][A-Za-z0-9\s,\-_/&\'\(\)]+)$',
        # E.g. "### 3. Payment Terms" (Markdown/DOCX heading)
        r'^#{1,4}\s*(?:(?P<num>[0-9IVXLCDM]+(?:\.[0-9a-zA-Z]+)*)\.?)?\s*(?P<title>.*)$',
        # E.g. ALL CAPS heading: "TERMINATION OF AGREEMENT", "GOVERNING LAW"
        r'^(?P<title>[A-Z0-9\s,\-_/&]{4,60})$'
    ]

    # Sub-clause / Bullet point patterns
    BULLET_PATTERNS = [
        r'^\s*(?:\([a-zA-Z0-9]+\)|[a-zA-Z0-9]+\))\s+', # e.g. "(a)", "(1)", "a)"
        r'^\s*[-*•–—]\s+'                               # e.g. "- ", "* ", "• "
    ]

    @classmethod
    def segment_document(cls, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Segment a multi-page document into structured clauses with page references and character offsets.
        """
        clauses = []
        current_heading: Optional[str] = None
        current_clause_num: Optional[str] = None
        current_clause_lines: List[str] = []
        current_page_start = 1
        current_page_end = 1
        global_char_offset = 0
        clause_start_char = 0

        for page in pages:
            page_num = page["page_number"]
            page_text = page["text"]
            lines = page_text.split("\n")

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    # Paragraph break: if current clause is sufficiently long, or has empty boundary
                    continue

                # Check if this line is a section heading
                heading_match = cls._match_heading(stripped)

                if heading_match:
                    # If we already have accumulated lines for a clause, commit it
                    if current_clause_lines:
                        clause_obj = cls._build_clause_object(
                            lines=current_clause_lines,
                            heading=current_heading,
                            clause_num=current_clause_num,
                            page_start=current_page_start,
                            page_end=current_page_end,
                            start_char=clause_start_char,
                            end_char=global_char_offset
                        )
                        if clause_obj:
                            clauses.append(clause_obj)
                        current_clause_lines = []

                    # Start new section
                    current_heading = heading_match.get("title") or heading_match.get("raw")
                    current_clause_num = heading_match.get("num")
                    current_page_start = page_num
                    current_page_end = page_num
                    clause_start_char = global_char_offset
                    
                    # If the heading line itself contains substantive text after the title, include it
                    body_text = heading_match.get("body")
                    if body_text:
                        current_clause_lines.append(body_text)

                elif cls._is_new_clause_starter(stripped) and current_clause_lines:
                    # New numbered or lettered bullet / clause starts
                    clause_obj = cls._build_clause_object(
                        lines=current_clause_lines,
                        heading=current_heading,
                        clause_num=current_clause_num,
                        page_start=current_page_start,
                        page_end=current_page_end,
                        start_char=clause_start_char,
                        end_char=global_char_offset
                    )
                    if clause_obj:
                        clauses.append(clause_obj)

                    current_clause_lines = [stripped]
                    current_page_start = page_num
                    current_page_end = page_num
                    clause_start_char = global_char_offset
                    # Check if line starts with an explicit bullet or subnumber
                    sub_match = cls._extract_subnumber(stripped)
                    if sub_match:
                        current_clause_num = sub_match
                else:
                    # Append line to current clause
                    if not current_clause_lines:
                        current_page_start = page_num
                        clause_start_char = global_char_offset
                    current_clause_lines.append(stripped)
                    current_page_end = page_num

                global_char_offset += len(line) + 1

        # Commit final clause
        if current_clause_lines:
            clause_obj = cls._build_clause_object(
                lines=current_clause_lines,
                heading=current_heading,
                clause_num=current_clause_num,
                page_start=current_page_start,
                page_end=current_page_end,
                start_char=clause_start_char,
                end_char=global_char_offset
            )
            if clause_obj:
                clauses.append(clause_obj)

        # Fallback if document has very few structural markers: chunk into logical paragraphs
        if len(clauses) <= 1 and sum(p["character_count"] for p in pages) > 500:
            return cls._fallback_paragraph_segmentation(pages)

        return clauses

    @classmethod
    def _match_heading(cls, line: str) -> Optional[Dict[str, Any]]:
        """Check if line matches any known heading or section pattern."""
        # Avoid treating very long sentences (> 80 chars) as headings unless strictly prefixed with Section/Article
        is_long = len(line) > 80

        for pattern in cls.SECTION_PATTERNS:
            match = re.match(pattern, line)
            if match:
                groups = match.groupdict()
                title = groups.get("title", "")
                num = groups.get("num", "")
                if is_long and not groups.get("prefix"):
                    continue
                # Reject titles that look like ordinary sentences ending in a period or lowercase
                if title and title.endswith(".") and len(title.split()) > 7:
                    continue
                return {
                    "num": num.strip() if num else None,
                    "title": title.strip() if title else line,
                    "raw": line
                }
        return None

    @classmethod
    def _is_new_clause_starter(cls, line: str) -> bool:
        """Determine if a line marks the beginning of a new sub-clause or itemized obligation."""
        # e.g., "(a)", "1.", "2.4", "(1)"
        if re.match(r'^(?:\([a-zA-Z0-9]+\)|[0-9]+\.[0-9]+|[0-9]+\))\s+[A-Z]', line):
            return True
        # e.g. "Provided however that" or "Notwithstanding the foregoing"
        if re.match(r'^(?:Provided however|Notwithstanding the foregoing|In the event that)\b', line, re.IGNORECASE):
            return True
        return False

    @classmethod
    def _extract_subnumber(cls, line: str) -> Optional[str]:
        """Extract prefix numbering if present at start of line."""
        m = re.match(r'^((?:\([a-zA-Z0-9]+\)|[0-9]+\.[0-9]+|[0-9]+\.))\s+', line)
        if m:
            return m.group(1).strip()
        return None

    @classmethod
    def _build_clause_object(
        cls, lines: List[str], heading: Optional[str],
        clause_num: Optional[str], page_start: int, page_end: int,
        start_char: int, end_char: int
    ) -> Optional[Dict[str, Any]]:
        """Assemble structured clause record with confidence and text normalization."""
        raw_text = " ".join(lines).strip()
        # Filter out tiny noise (e.g. single page numbers or empty bullets)
        if len(raw_text) < 15:
            return None

        normalized = re.sub(r'\s+', ' ', raw_text)
        
        # Calculate segmentation confidence based on structural indicators
        confidence = 0.70
        if heading:
            confidence += 0.15
        if clause_num:
            confidence += 0.10
        if len(raw_text) > 50:
            confidence = min(0.98, confidence + 0.05)

        return {
            "clause_number": clause_num,
            "heading": heading,
            "page_start": page_start,
            "page_end": page_end,
            "start_char": start_char,
            "end_char": end_char,
            "original_text": raw_text,
            "normalized_text": normalized,
            "segmentation_confidence": round(confidence, 2)
        }

    @classmethod
    def _fallback_paragraph_segmentation(cls, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback segmentation for continuous unstructured text."""
        clauses = []
        global_char = 0
        for page in pages:
            paragraphs = page["text"].split("\n\n")
            for idx, p in enumerate(paragraphs):
                p_clean = p.strip()
                if len(p_clean) < 20:
                    continue
                start_c = global_char
                end_c = global_char + len(p_clean)
                global_char = end_c + 2

                clauses.append({
                    "clause_number": f"P{page['page_number']}.{idx + 1}",
                    "heading": f"Page {page['page_number']} - Section {idx + 1}",
                    "page_start": page["page_number"],
                    "page_end": page["page_number"],
                    "start_char": start_c,
                    "end_char": end_c,
                    "original_text": p_clean,
                    "normalized_text": re.sub(r'\s+', ' ', p_clean),
                    "segmentation_confidence": 0.65
                })
        return clauses
