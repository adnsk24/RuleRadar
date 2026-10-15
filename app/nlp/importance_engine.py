# RuleRadar AI - Clause Importance Scoring Engine
import re
from typing import Dict, Any, List

class ImportanceEngine:
    """
    Evaluates practical contractual significance independently from risk.
    Scores clauses from 0.0 to 10.0 based on actionable obligations,
    monetary sums, temporal deadlines, and core legal covenants.
    """

    CRITICAL_CATEGORIES = {
        "Payment and financial obligations": 3.0,
        "Termination and cancellation": 2.5,
        "Penalties and late fees": 2.5,
        "Liability and indemnification": 2.5,
        "Intellectual property": 2.0,
        "Renewal and automatic renewal": 2.0,
        "Deadlines and time limits": 2.0,
        "Security deposits and refunds": 2.0,
        "Restrictions and prohibitions": 1.5,
        "Governing law and jurisdiction": 1.0,
        "Confidentiality": 1.5
    }

    @classmethod
    def calculate_importance(cls, text: str, category: str, risk_count: int = 0) -> Dict[str, Any]:
        """
        Calculate transparent importance score (0.0 - 10.0) with contributing factors.
        """
        score = 1.0  # Baseline
        factors: List[str] = []

        # 1. Category relevance
        cat_weight = cls.CRITICAL_CATEGORIES.get(category, 0.5)
        score += cat_weight
        if cat_weight >= 2.0:
            factors.append(f"Core contractual area ({category})")

        # 2. Financial values present ($1,000, 5%, INR 50,000, etc.)
        money_match = re.search(r'([$€£₹]|USD|EUR|INR|GBP|\bRs\.?)\s*[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?', text)
        if money_match:
            score += 2.0
            factors.append(f"Contains specific financial value ({money_match.group(0)})")

        # 3. Explicit timeframes / deadlines ("within 30 days", "by October 15", "notice of 60 days")
        time_match = re.search(r'\b(?:within\s+[0-9]+\s+(?:days?|weeks?|months?|business\s+days?)|prior\s+to\s+[0-9]+\s+days?|by\s+[A-Z][a-z]+\s+[0-9]{1,2})\b', text, re.IGNORECASE)
        if time_match:
            score += 2.0
            factors.append(f"Imposes explicit time limit ({time_match.group(0)})")

        # 4. Mandatory imperative language ("shall", "must", "agrees that failure to")
        if re.search(r'\b(?:shall\s+immediately|must\s+provide|agrees\s+to\s+pay|is\s+strictly\s+required\s+to)\b', text, re.IGNORECASE):
            score += 1.5
            factors.append("Contains strict mandatory performance language ('shall' / 'must')")

        # 5. Presence of flagged risk review items
        if risk_count > 0:
            score += min(2.0, risk_count * 1.0)
            factors.append(f"Associated with {risk_count} potential risk review indicator(s)")

        # Cap score at 10.0
        final_score = round(min(10.0, max(0.5, score)), 1)

        if final_score >= 7.0:
            imp_category = "High"
        elif final_score >= 4.0:
            imp_category = "Medium"
        else:
            imp_category = "Low"

        explanation = "; ".join(factors) if factors else "Standard boilerplate or descriptive provision."

        return {
            "importance_score": final_score,
            "importance_category": imp_category,
            "explanation": explanation
        }
