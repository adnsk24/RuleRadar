# RuleRadar AI - Semantic Document Comparison & Diff Engine
import re
import difflib
from typing import List, Dict, Any, Tuple
import numpy as np
from app.nlp.embeddings import embedding_service
from app.nlp.extractor import InformationExtractor

class DocumentComparator:
    """
    Robust multi-criteria semantic comparison engine.
    Matches clauses using section numbers, structural headings, token overlap,
    and sentence embeddings to detect additions, removals, and substantive modifications.
    """

    SIMILARITY_THRESHOLD = 0.65
    IDENTICAL_THRESHOLD = 0.98

    @classmethod
    def compare_documents(
        cls,
        doc_a_clauses: List[Dict[str, Any]],
        doc_b_clauses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare Document A (Previous version) with Document B (New version).
        Returns structured report containing categorized differences, metrics, and side-by-side evidence.
        """
        if not doc_a_clauses and not doc_b_clauses:
            return {
                "added_clauses": [],
                "removed_clauses": [],
                "modified_clauses": [],
                "identical_clauses": [],
                "summary": "Both documents are empty."
            }

        texts_a = [c.get("normalized_text", "") for c in doc_a_clauses]
        texts_b = [c.get("normalized_text", "") for c in doc_b_clauses]

        # 1. Compute pairwise similarity matrix
        sim_matrix = embedding_service.pairwise_similarity(texts_a, texts_b)

        matched_b_indices = set()
        matched_pairs: List[Tuple[int, int, float]] = []

        # 2. Multi-criterion matching: Section numbers / Headings take priority
        for idx_a, clause_a in enumerate(doc_a_clauses):
            best_idx_b = -1
            best_score = -1.0

            num_a = clause_a.get("clause_number")
            head_a = (clause_a.get("heading") or "").strip().lower()

            for idx_b, clause_b in enumerate(doc_b_clauses):
                if idx_b in matched_b_indices:
                    continue

                num_b = clause_b.get("clause_number")
                head_b = (clause_b.get("heading") or "").strip().lower()

                # Structural match boost
                structural_boost = 0.0
                if num_a and num_b and num_a.lower() == num_b.lower():
                    structural_boost += 0.35
                if head_a and head_b and (head_a in head_b or head_b in head_a):
                    structural_boost += 0.25

                # Text similarity
                sem_sim = sim_matrix[idx_a, idx_b] if sim_matrix.size > 0 else 0.0
                
                # Token lexical overlap (Jaccard)
                tokens_a = set(texts_a[idx_a].lower().split())
                tokens_b = set(texts_b[idx_b].lower().split())
                jaccard = len(tokens_a & tokens_b) / max(1, len(tokens_a | tokens_b))

                composite_score = (sem_sim * 0.50) + (jaccard * 0.30) + structural_boost

                if composite_score > best_score:
                    best_score = composite_score
                    best_idx_b = idx_b

            if best_idx_b != -1 and best_score >= cls.SIMILARITY_THRESHOLD:
                matched_pairs.append((idx_a, best_idx_b, best_score))
                matched_b_indices.add(best_idx_b)

        # 3. Classify matches into Identical, Modified, Removed, Added
        identical_clauses = []
        modified_clauses = []
        matched_a_indices = set()

        for idx_a, idx_b, match_score in matched_pairs:
            matched_a_indices.add(idx_a)
            clause_a = doc_a_clauses[idx_a]
            clause_b = doc_b_clauses[idx_b]

            text_a = clause_a.get("original_text", "")
            text_b = clause_b.get("original_text", "")

            # Exact or near-exact match
            clean_a = re.sub(r'\s+', ' ', text_a).strip()
            clean_b = re.sub(r'\s+', ' ', text_b).strip()

            if clean_a == clean_b:
                identical_clauses.append({
                    "clause_a": clause_a,
                    "clause_b": clause_b,
                    "similarity": 1.0
                })
            else:
                # Substantive modification analysis
                sem_sim = sim_matrix[idx_a, idx_b] if sim_matrix.size > 0 else 0.0
                mod_detail = cls._analyze_modification(clause_a, clause_b, float(sem_sim))
                modified_clauses.append(mod_detail)

        # Removed clauses (in A but no match found in B)
        removed_clauses = []
        for idx_a, clause_a in enumerate(doc_a_clauses):
            if idx_a not in matched_a_indices:
                removed_clauses.append({
                    "clause": clause_a,
                    "reason": "This provision was present in the previous version but removed from the new version."
                })

        # Added clauses (in B but no match found in A)
        added_clauses = []
        for idx_b, clause_b in enumerate(doc_b_clauses):
            if idx_b not in matched_b_indices:
                added_clauses.append({
                    "clause": clause_b,
                    "reason": "This provision was introduced in the new version and has no precedent in the previous version."
                })

        # Generate executive summary
        summary = (
            f"Comparison completed: {len(modified_clauses)} modified clause(s), "
            f"{len(added_clauses)} newly added clause(s), {len(removed_clauses)} removed clause(s), "
            f"and {len(identical_clauses)} unchanged clause(s)."
        )

        return {
            "summary": summary,
            "counts": {
                "added": len(added_clauses),
                "removed": len(removed_clauses),
                "modified": len(modified_clauses),
                "identical": len(identical_clauses)
            },
            "added_clauses": added_clauses,
            "removed_clauses": removed_clauses,
            "modified_clauses": modified_clauses,
            "identical_clauses": identical_clauses
        }

    @classmethod
    def _analyze_modification(
        cls,
        clause_a: Dict[str, Any],
        clause_b: Dict[str, Any],
        similarity_score: float
    ) -> Dict[str, Any]:
        """
        Inspect specific field changes between two matched clauses:
        financial amounts, notice/deadlines, obligation strength, and generate inline word diff.
        """
        text_a = clause_a.get("original_text", "")
        text_b = clause_b.get("original_text", "")

        # 1. Financial values comparison
        fin_a = InformationExtractor.extract_financials(text_a)
        fin_b = InformationExtractor.extract_financials(text_b)
        vals_a = [f["amount_or_percentage"] for f in fin_a]
        vals_b = [f["amount_or_percentage"] for f in fin_b]

        changed_financials = []
        if vals_a != vals_b and (vals_a or vals_b):
            changed_financials.append({
                "field": "Monetary / Financial Amount",
                "previous_value": ", ".join(vals_a) if vals_a else "None",
                "new_value": ", ".join(vals_b) if vals_b else "None",
                "explanation": f"Financial terms adjusted from '{', '.join(vals_a) or 'None'}' to '{', '.join(vals_b) or 'None'}'."
            })

        # 2. Deadlines / Notice periods comparison
        deadlines_a = InformationExtractor.extract_deadlines(text_a)
        deadlines_b = InformationExtractor.extract_deadlines(text_b)
        d_vals_a = [d["date_or_period"] for d in deadlines_a]
        d_vals_b = [d["date_or_period"] for d in deadlines_b]

        changed_deadlines = []
        if d_vals_a != d_vals_b and (d_vals_a or d_vals_b):
            changed_deadlines.append({
                "field": "Deadline / Notice Period",
                "previous_value": ", ".join(d_vals_a) if d_vals_a else "None",
                "new_value": ", ".join(d_vals_b) if d_vals_b else "None",
                "explanation": f"Timeframe changed from '{', '.join(d_vals_a) or 'None'}' to '{', '.join(d_vals_b) or 'None'}'."
            })

        # 3. Obligation modal shift ("may" -> "shall", "shall" -> "must", etc.)
        modals_a = set(re.findall(r'\b(shall|must|may|will|can)\b', text_a, re.IGNORECASE))
        modals_b = set(re.findall(r'\b(shall|must|may|will|can)\b', text_b, re.IGNORECASE))
        obligation_shift = None
        if "may" in modals_a and ("shall" in modals_b or "must" in modals_b):
            obligation_shift = "Permissive language ('may') escalated to mandatory obligation ('shall'/'must')."
        elif ("shall" in modals_a or "must" in modals_a) and "may" in modals_b and not ("shall" in modals_b):
            obligation_shift = "Mandatory obligation ('shall'/'must') softened to permissive option ('may')."

        # 4. Generate word-level HTML diff
        words_a = text_a.split()
        words_b = text_b.split()
        matcher = difflib.SequenceMatcher(None, words_a, words_b)

        diff_html_a = []
        diff_html_b = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                diff_html_a.append(" ".join(words_a[i1:i2]))
                diff_html_b.append(" ".join(words_b[j1:j2]))
            elif tag == 'delete':
                diff_html_a.append(f"<del class='diff-del'>{' '.join(words_a[i1:i2])}</del>")
            elif tag == 'insert':
                diff_html_b.append(f"<ins class='diff-ins'>{' '.join(words_b[j1:j2])}</ins>")
            elif tag == 'replace':
                diff_html_a.append(f"<del class='diff-del'>{' '.join(words_a[i1:i2])}</del>")
                diff_html_b.append(f"<ins class='diff-ins'>{' '.join(words_b[j1:j2])}</ins>")

        # Synthesis explanation
        explanation_parts = []
        if changed_financials:
            explanation_parts.append(changed_financials[0]["explanation"])
        if changed_deadlines:
            explanation_parts.append(changed_deadlines[0]["explanation"])
        if obligation_shift:
            explanation_parts.append(obligation_shift)
        if not explanation_parts:
            explanation_parts.append("Wording updated with textual changes, preserving the core provision structure.")

        return {
            "clause_a": clause_a,
            "clause_b": clause_b,
            "similarity": round(float(similarity_score), 2),
            "explanation": " ".join(explanation_parts),
            "changed_financials": changed_financials,
            "changed_deadlines": changed_deadlines,
            "obligation_shift": obligation_shift,
            "diff_html_previous": " ".join(diff_html_a),
            "diff_html_current": " ".join(diff_html_b)
        }
