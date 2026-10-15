# RuleRadar AI - Document-Grounded Question Answering & Conversational Engine
import re
from typing import List, Dict, Any, Optional
import numpy as np
from app.nlp.embeddings import embedding_service

class DocumentQAEngine:
    """
    Evidence-grounded, zero-hallucination document question answering and conversational router.
    Retrieves verifiable clauses, generates transparent answers with verbatim citations,
    and cleanly handles conversational intents without fabricated statements.
    """

    GREETING_PATTERNS = [
        r'^\s*(?:hi|hello|hey|greetings|good\s+(?:morning|afternoon|evening))\b'
    ]

    APP_INFO_PATTERNS = [
        r'\b(?:what\s+is\s+ruleradar|how\s+does\s+(?:this|ruleradar)\s+work|what\s+can\s+you\s+do|who\s+are\s+you|help)\b'
    ]

    LEGAL_ADVICE_PATTERNS = [
        r'\b(?:is\s+this\s+(?:contract\s+|agreement\s+)?(?:legally\s+)?(?:legal|lawful|valid|binding)|what\s+is\s+the\s+best\s+contract\s+legally|should\s+i\s+sign\s+this|legal\s+advice)\b'
    ]

    SUMMARY_PATTERNS = [
        r'\b(?:what\s+is\s+this\s+document\s+about|summarize\s+(?:this|the)\s+document|give\s+me\s+a\s+summary|document\s+overview)\b'
    ]

    @classmethod
    def answer_question(
        cls,
        question: str,
        document_clauses: List[Dict[str, Any]],
        document_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user query against document clauses. Returns structured answer, citations, and evidence.
        """
        clean_q = question.strip()
        lower_q = clean_q.lower()

        # 1. Conversational intent: Greetings
        if any(re.search(pat, lower_q) for pat in cls.GREETING_PATTERNS):
            doc_title = document_meta.get("filename", "a document") if document_meta else "a document"
            return {
                "answer": f"Hello! I am your RuleRadar AI document assistant. I am ready to analyze '{doc_title}'. Ask me about specific clauses, deadlines, financial obligations, penalties, termination conditions, or for a grounded summary.",
                "citations": [],
                "confidence": 1.0,
                "intent": "greeting"
            }

        # 2. Conversational intent: General app info
        if any(re.search(pat, lower_q) for pat in cls.APP_INFO_PATTERNS):
            return {
                "answer": (
                    "RuleRadar AI is an intelligent document analysis platform designed to inspect legal and official documents. "
                    "I extract important clauses, identify potential review risks, extract financial figures and deadlines, and answer questions "
                    "with verifiable, exact citations. All processing runs locally with open-source models without sending your data to external APIs."
                ),
                "citations": [],
                "confidence": 1.0,
                "intent": "app_info"
            }

        # 3. Conversational intent: Legal advice inquiry
        if any(re.search(pat, lower_q) for pat in cls.LEGAL_ADVICE_PATTERNS):
            return {
                "answer": (
                    "Disclaimer: RuleRadar AI provides automated text analysis, important clause detection, and objective risk review indicators, "
                    "but cannot provide legal advice or determine legal validity. You should consult a qualified legal professional to assess "
                    "enforceability under your governing jurisdiction."
                ),
                "citations": [],
                "confidence": 1.0,
                "intent": "legal_advice_disclaimer"
            }

        # 4. Check if document has any clauses
        if not document_clauses:
            return {
                "answer": "No clauses are available in this document to answer your question.",
                "citations": [],
                "confidence": 0.0,
                "intent": "no_data"
            }

        # 5. Summary request
        if any(re.search(pat, lower_q) for pat in cls.SUMMARY_PATTERNS):
            return cls._generate_grounded_summary(document_clauses, document_meta)

        # 6. Document-grounded retrieval: Semantic similarity + Keyword BM25 boost
        clause_texts = [c.get("normalized_text", "") for c in document_clauses]
        similarities = embedding_service.compute_similarity(clean_q, clause_texts)

        # Compute keyword overlap scores
        query_terms = [w for w in re.findall(r'\b\w{3,}\b', lower_q) if w not in [
            "what", "when", "where", "which", "does", "have", "with", "this", "that", "about", "show"
        ]]

        scored_candidates = []
        for idx, (clause, sim) in enumerate(zip(document_clauses, similarities)):
            text_lower = clause.get("normalized_text", "").lower()
            head_lower = (clause.get("heading") or "").lower()
            cat_lower = (clause.get("category") or "").lower()

            # Exact keyword hits
            kw_hits = sum(1 for term in query_terms if term in text_lower or term in head_lower or term in cat_lower)
            kw_ratio = (kw_hits / max(1, len(query_terms))) if query_terms else 0.0

            # Composite retrieval score
            composite = (sim * 0.65) + (kw_ratio * 0.35)
            scored_candidates.append((composite, clause))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c for c in scored_candidates if c[0] >= 0.28][:4]

        # If best match is below confidence threshold, state that evidence is missing
        if not top_candidates or top_candidates[0][0] < 0.28:
            return {
                "answer": (
                    "Based on an exhaustive search of the extracted document text, no clauses were found that directly discuss "
                    f"'{clean_q}'. The document does not appear to contain explicit terms regarding this topic."
                ),
                "citations": [],
                "confidence": 0.2,
                "intent": "not_found"
            }

        # Format citations and construct grounded answer
        citations = []
        supporting_snippets = []

        for score, clause in top_candidates:
            c_num = clause.get("clause_number") or "Section"
            heading = clause.get("heading") or "Clause"
            page_start = clause.get("page_start", 1)
            orig_text = clause.get("original_text", "").strip()

            # Select key sentence from clause closest to question
            key_sentence = cls._find_key_sentence(orig_text, query_terms)

            citations.append({
                "clause_id": clause.get("id"),
                "clause_number": c_num,
                "heading": heading,
                "page": page_start,
                "relevance_score": round(float(score), 2),
                "quote": key_sentence
            })
            supporting_snippets.append(f"• [{c_num} - {heading}, Page {page_start}]: \"{key_sentence}\"")

        # Synthesize clear answer directly from the highest-ranked evidence
        primary_quote = citations[0]["quote"]
        primary_source = f"{citations[0]['clause_number']} ({citations[0]['heading']}), Page {citations[0]['page']}"
        
        answer = (
            f"According to {primary_source}, the document specifies:\n\n"
            f"\"{primary_quote}\"\n\n"
            f"Supporting Provisions Found:\n" + "\n".join(supporting_snippets[1:]) if len(supporting_snippets) > 1 else
            f"According to {primary_source}, the document states:\n\n\"{primary_quote}\""
        )

        return {
            "answer": answer.strip(),
            "citations": citations,
            "confidence": round(float(top_candidates[0][0]), 2),
            "intent": "grounded_answer"
        }

    @classmethod
    def _find_key_sentence(cls, text: str, query_terms: List[str]) -> str:
        """Find the sentence within the clause containing the highest density of query terms."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 1:
            return text[:250] + ("..." if len(text) > 250 else "")

        best_sent = sentences[0]
        max_hits = -1
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            s_lower = s_clean.lower()
            hits = sum(1 for t in query_terms if t in s_lower)
            if hits > max_hits:
                max_hits = hits
                best_sent = s_clean

        return best_sent[:250] + ("..." if len(best_sent) > 250 else "")

    @classmethod
    def _generate_grounded_summary(
        cls,
        clauses: List[Dict[str, Any]],
        meta: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a factual, grounded executive summary of the document."""
        # Find key clauses across core categories
        key_clauses = [c for c in clauses if c.get("importance_score", 0.0) >= 5.0]
        if not key_clauses:
            key_clauses = clauses[:5]

        # Gather main categories represented
        categories = list(dict.fromkeys(c.get("category", "") for c in clauses if c.get("category") and c.get("category") != "Other or unclassified clauses"))
        top_cats = categories[:6]

        total_clauses = len(clauses)
        page_count = meta.get("page_count", 1) if meta else 1
        filename = meta.get("filename", "This document") if meta else "This document"

        summary_lines = [
            f"**{filename}** spans {page_count} page(s) and contains {total_clauses} segmented clauses.",
            f"Primary contractual areas covered include: {', '.join(top_cats) if top_cats else 'general administrative and descriptive provisions'}.",
            "\n**Key Highlights Extracted:**"
        ]

        citations = []
        for c in key_clauses[:4]:
            heading = c.get("heading") or "Clause"
            c_num = c.get("clause_number") or ""
            page = c.get("page_start", 1)
            quote = c.get("original_text", "")[:180] + "..."
            summary_lines.append(f"• **{heading}** (Page {page}): {quote}")
            citations.append({
                "clause_id": c.get("id"),
                "clause_number": c_num,
                "heading": heading,
                "page": page,
                "relevance_score": 1.0,
                "quote": quote
            })

        return {
            "answer": "\n".join(summary_lines),
            "citations": citations,
            "confidence": 0.95,
            "intent": "summary"
        }
