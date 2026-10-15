# RuleRadar AI - 20-Category Clause Classification Engine
import re
from typing import Dict, Any, List, Tuple
from app.nlp.embeddings import embedding_service

class ClauseClassifier:
    """
    Transparent, multi-signal clause classification engine for all 20 contractual categories.
    Combines curated semantic anchor vectors, structural pattern recognition, and calibrated confidence.
    """

    CATEGORIES = [
        "Payment and financial obligations",
        "Penalties and late fees",
        "Security deposits and refunds",
        "Termination and cancellation",
        "Renewal and automatic renewal",
        "Liability and indemnification",
        "Confidentiality",
        "Intellectual property",
        "Privacy and data handling",
        "Dispute resolution",
        "Governing law and jurisdiction",
        "Eligibility requirements",
        "Deadlines and time limits",
        "Duties and responsibilities",
        "Restrictions and prohibitions",
        "Conditions and exceptions",
        "Warranties and guarantees",
        "Force majeure",
        "Notice requirements",
        "Other or unclassified clauses"
    ]

    # Curated semantic anchors representing typical legal phrasing for each category
    CATEGORY_ANCHORS = {
        "Payment and financial obligations": (
            "Monthly rent payment, compensation, salary, hourly rate, invoice terms, wire transfer, billing schedule, "
            "due on the first of each month, consideration, fees payable, reimbursement of expenses"
        ),
        "Penalties and late fees": (
            "Late charge of five percent, penalty fee, liquidated damages, interest on overdue amounts, "
            "default penalty, forfeiture of payment, failure to pay on time incurs daily penalty"
        ),
        "Security deposits and refunds": (
            "Security deposit paid upon execution, refundable upon vacancy, deduction for damages, "
            "escrow account, deposit return within 30 days, refund policy, non-refundable deposit"
        ),
        "Termination and cancellation": (
            "Either party may terminate this agreement, notice of cancellation, termination for cause, "
            "immediate termination upon breach, cancellation clause, right to terminate with 30 days written notice"
        ),
        "Renewal and automatic renewal": (
            "This agreement shall automatically renew for successive one-year terms unless notice of non-renewal is provided, "
            "evergreen clause, lease renewal conditions, option to extend term"
        ),
        "Liability and indemnification": (
            "Hold harmless, indemnify and defend against all claims, limitation of liability, aggregate liability shall not exceed, "
            "consequential damages waiver, indemnification obligations for losses and legal fees"
        ),
        "Confidentiality": (
            "Non-disclosure of confidential information, proprietary information, trade secrets, "
            "recipient shall maintain secrecy, disclosure restrictions, standard of care for confidential materials"
        ),
        "Intellectual property": (
            "Work made for hire, assignment of inventions, patents, copyrights, trademarks, proprietary rights, "
            "moral rights waiver, all deliverables remain exclusive property of client"
        ),
        "Privacy and data handling": (
            "Protection of personal data, GDPR compliance, data processing addendum, user privacy, "
            "collection and storage of personal identifiable information, data breach notification"
        ),
        "Dispute resolution": (
            "Binding arbitration under AAA rules, mediation before litigation, dispute resolution procedure, "
            "negotiation in good faith, class action waiver, dispute escalation process"
        ),
        "Governing law and jurisdiction": (
            "Governed by and construed in accordance with the laws of, exclusive jurisdiction of the state courts, "
            "venue shall lie exclusively in, conflict of law principles"
        ),
        "Eligibility requirements": (
            "Qualifications, prerequisites, criteria for admission, enrollment eligibility, "
            "minimum qualifications, applicant must possess a valid degree or license"
        ),
        "Deadlines and time limits": (
            "Submission deadline, must be completed by date, time is of the essence, window of opportunity, "
            "milestone schedule, statutory limitation period, strictly by 5:00 PM"
        ),
        "Duties and responsibilities": (
            "Scope of work, services to be performed, duties of employee, tenant obligations to maintain premises, "
            "shall perform with reasonable diligence, core responsibilities and deliverables"
        ),
        "Restrictions and prohibitions": (
            "Non-compete covenant, non-solicitation of clients, prohibition on subletting, restriction on assignment, "
            "tenant shall not alter structure, prohibited activities and negative covenants"
        ),
        "Conditions and exceptions": (
            "Condition precedent, subject to approval, provided that, unless otherwise agreed, "
            "except as expressly set forth, contingent upon financing, exclusionary circumstances"
        ),
        "Warranties and guarantees": (
            "Represents and warrants, disclaimer of implied warranties, as-is where-is, merchantability, "
            "fitness for a particular purpose, guarantee of performance"
        ),
        "Force majeure": (
            "Acts of God, natural disasters, war, pandemic, strike, civil unrest, "
            "unforeseeable events beyond reasonable control, excused performance during emergency"
        ),
        "Notice requirements": (
            "All notices shall be in writing and delivered via certified mail or email, "
            "deemed received on date of delivery, notice address, formal communication requirements"
        )
    }

    # Deterministic lexical patterns for strong confidence boosting
    STRONG_PATTERNS = {
        "Governing law and jurisdiction": [
            r'\bgoverned\s+by\s+and\s+construed\s+in\s+accordance\s+with\b',
            r'\bexclusive\s+jurisdiction\s+of\s+the\s+courts\b',
            r'\bvenue\s+shall\s+lie\s+(?:exclusively\s+)?in\b'
        ],
        "Force majeure": [
            r'\bforce\s+majeure\b',
            r'\bacts?\s+of\s+god\b',
            r'\bunforeseeable\s+circumstances\s+beyond\s+(?:the\s+)?(?:reasonable\s+)?control\b'
        ],
        "Confidentiality": [
            r'\bconfidential\s+information\b',
            r'\bnon-?disclosure\b',
            r'\btrade\s+secrets?\b',
            r'\bproprietary\s+information\b'
        ],
        "Renewal and automatic renewal": [
            r'\bautomatically\s+renew(?:s|ed|ing)?\b',
            r'\bautomatic\s+renewal\b',
            r'\bsuccessive\s+(?:one[- ]year|monthly)\s+terms?\b'
        ],
        "Security deposits and refunds": [
            r'\bsecurity\s+deposit\b',
            r'\bdeposit\s+shall\s+be\s+returned\b',
            r'\bnon-?refundable\s+deposit\b'
        ],
        "Penalties and late fees": [
            r'\blate\s+fee\b',
            r'\blate\s+charge\b',
            r'\bliquidated\s+damages\b',
            r'\bpenalty\s+of\b',
            r'\bper\s+day\s+of\s+delay\b'
        ],
        "Notice requirements": [
            r'\bnotices?\s+(?:hereunder\s+)?shall\s+be\s+in\s+writing\b',
            r'\bdelivered\s+by\s+(?:certified\s+mail|hand\s+delivery|courier)\b',
            r'\bwritten\s+notice\s+addressed\s+to\b'
        ]
    }

    @classmethod
    def classify_clause(cls, text: str, heading: str = "") -> Dict[str, Any]:
        """
        Classifies clause into 1 of the 20 categories with confidence and human explanation.
        """
        norm_text = text.lower()
        norm_heading = (heading or "").lower()
        combined_text = f"{norm_heading} {norm_text}"

        scores: Dict[str, float] = {cat: 0.0 for cat in cls.CATEGORIES if cat != "Other or unclassified clauses"}

        # 1. Check strong deterministic patterns
        for cat, patterns in cls.STRONG_PATTERNS.items():
            for p in patterns:
                if re.search(p, combined_text):
                    scores[cat] += 0.45

        # 2. Heading alignment boost
        for cat in scores.keys():
            cat_words = [w for w in cat.lower().split() if len(w) > 3 and w not in ["and", "or", "clauses"]]
            heading_matches = sum(1 for w in cat_words if w in norm_heading)
            if heading_matches > 0:
                scores[cat] += 0.35 * (heading_matches / len(cat_words))

        # 3. Semantic similarity against category anchor texts
        candidate_cats = list(cls.CATEGORY_ANCHORS.keys())
        anchor_texts = [cls.CATEGORY_ANCHORS[c] for c in candidate_cats]
        sims = embedding_service.compute_similarity(text[:500], anchor_texts)

        for cat, sim in zip(candidate_cats, sims):
            scores[cat] += sim * 0.50

        # Sort categories by aggregate score
        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_cats[0]
        second_cat, second_score = sorted_cats[1] if len(sorted_cats) > 1 else ("", 0.0)

        # Confidence calibration
        confidence = min(0.98, max(0.20, top_score))

        # Threshold check: if top score is too weak (< 0.35), classify as "Other or unclassified clauses"
        if top_score < 0.35:
            return {
                "category": "Other or unclassified clauses",
                "confidence": round(0.40, 2),
                "explanation": "No distinct contractual category reached minimum confidence threshold.",
                "alternative_categories": [
                    {"category": c, "confidence": round(s, 2)} for c, s in sorted_cats[:3] if s > 0.15
                ]
            }

        # Build transparent explanation
        explanation_parts = []
        if top_score > 0.65:
            explanation_parts.append(f"Strong alignment with standard {top_cat.lower()} terminology.")
        elif top_score > 0.40:
            explanation_parts.append(f"Contains characteristic provisions typical of {top_cat.lower()}.")
        
        if heading and any(w in norm_heading for w in top_cat.lower().split() if len(w) > 4):
            explanation_parts.append(f"Section heading ('{heading}') explicitly indicates this classification.")

        explanation = " ".join(explanation_parts) or f"Classified as {top_cat} based on semantic phrasing and obligations."

        alternatives = []
        if second_score > 0.30:
            alternatives.append({"category": second_cat, "confidence": round(second_score, 2)})
            if len(sorted_cats) > 2 and sorted_cats[2][1] > 0.25:
                alternatives.append({"category": sorted_cats[2][0], "confidence": round(sorted_cats[2][1], 2)})

        return {
            "category": top_cat,
            "confidence": round(confidence, 2),
            "explanation": explanation,
            "alternative_categories": alternatives
        }
