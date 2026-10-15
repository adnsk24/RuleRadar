# RuleRadar AI - Transparent Evidence-Based Risk Review Engine
import re
from typing import List, Dict, Any, Optional

class RiskEngine:
    """
    Transparent, explainable risk review engine.
    Flags clauses requiring human legal attention based on structured risk patterns,
    synthesizing evidence quotes, contextual limitations, and investigative questions.
    """

    RULES = [
        {
            "id": "unilateral_modification",
            "name": "Unilateral Modification Right",
            "risk_level": "High attention",
            "patterns": [
                r'(?:reserves?\s+the\s+right\s+to\s+(?:modify|amend|alter|change)\b[^\.\;]*without\s+(?:prior\s+)?notice)',
                r'(?:may\s+change\s+(?:these\s+terms|the\s+agreement|prices|rates)\s+at\s+any\s+time\s+at\s+its\s+sole\s+discretion)',
                r'(?:unilaterally\s+(?:alter|modify|amend)\s+the\s+terms)'
            ],
            "explanation": "One party reserves the right to unilaterally alter contract terms or fees without prior notice or consent.",
            "suggested_question": "Does the contract require written mutual agreement for amendments, or can the counterparty alter terms unilaterally?",
            "fin_score": 0.6,
            "sev_score": 0.8,
            "amb_score": 0.5
        },
        {
            "id": "broad_indemnification",
            "name": "Broad or Unlimited Indemnification",
            "risk_level": "High attention",
            "patterns": [
                r'(?:indemnify[^\.\;]*hold\s+harmless[^\.\;]*(?:from\s+any\s+and\s+all|against\s+all)\s+claims)',
                r'(?:waives?\s+all\s+claims\s+against)',
                r'(?:unlimited\s+liability\s+for\s+any\s+damages)',
                r'(?:defend\s+and\s+hold\s+harmless\s+regardless\s+of\s+fault)'
            ],
            "explanation": "Imposes broad indemnification or liability, potentially holding one party accountable for claims beyond standard direct negligence.",
            "suggested_question": "Is indemnification capped, and does it exclude losses arising from the counterparty's gross negligence or willful misconduct?",
            "fin_score": 0.9,
            "sev_score": 0.85,
            "amb_score": 0.4
        },
        {
            "id": "excessive_penalty",
            "name": "Disproportionate Penalty or Forfeiture",
            "risk_level": "High attention",
            "patterns": [
                r'(?:forfeit(?:s|ure)?\s+(?:of\s+)?(?:the\s+)?entire\s+deposit)',
                r'(?:liquidated\s+damages\s+(?:of|exceeding)\b)',
                r'(?:penalty\s+(?:of|interest)\s+(?:at\s+)?(?:[2-9][0-9]%|[1-9][0-9]{2}%|(?:[1-9]%?\s+per\s+day)))',
                r'(?:immediate\s+forfeiture\s+without\s+recourse)'
            ],
            "explanation": "Specifies strict forfeiture or severe liquidated damages without requiring demonstration of actual suffered loss.",
            "suggested_question": "Are the liquidated damages or forfeiture amounts proportional to actual documented losses under governing contract law?",
            "fin_score": 0.85,
            "sev_score": 0.75,
            "amb_score": 0.3
        },
        {
            "id": "unclear_deposit_refund",
            "name": "Non-Refundable or Ambiguous Deposit",
            "risk_level": "Needs review",
            "patterns": [
                r'(?:non-?refundable\s+(?:security\s+)?deposit)',
                r'(?:deposit\s+shall\s+be\s+retained\s+at\s+sole\s+discretion)',
                r'(?:no\s+portion\s+of\s+the\s+deposit\s+shall\s+be\s+returned)',
                r'(?:refund\s+(?:shall\s+be\s+)?subject\s+to\s+unspecified\s+deductions)'
            ],
            "explanation": "Identifies conditions where a deposit is declared non-refundable or returned under discretionary criteria.",
            "suggested_question": "Under what specific, objective inspection criteria and statutory deadlines will the deposit be returned?",
            "fin_score": 0.7,
            "sev_score": 0.6,
            "amb_score": 0.6
        },
        {
            "id": "auto_renewal_trap",
            "name": "Auto-Renewal with Strenuous Notice Window",
            "risk_level": "Needs review",
            "patterns": [
                r'(?:automatically\s+renews?\s+unless[^\.\;]*(?:60|90|120|180)\s+days?\s+prior)',
                r'(?:perpetual\s+renewal\s+unless\s+terminated)',
                r'(?:automatic\s+extension\s+without\s+affirmative\s+confirmation)'
            ],
            "explanation": "Contract automatically extends for a long period unless notice is provided exceptionally far in advance.",
            "suggested_question": "What is the exact deadline to provide cancellation notice to prevent automatic renewal for another term?",
            "fin_score": 0.6,
            "sev_score": 0.65,
            "amb_score": 0.3
        },
        {
            "id": "immediate_unilateral_termination",
            "name": "Immediate Asymmetric Termination",
            "risk_level": "High attention",
            "patterns": [
                r'(?:may\s+terminate\s+(?:this\s+agreement\s+)?immediately\s+without\s+cause)',
                r'(?:terminate\s+at\s+any\s+time\s+without\s+notice\s+or\s+penalty)',
                r'(?:sole\s+and\s+absolute\s+discretion\s+to\s+terminate\s+forthwith)'
            ],
            "explanation": "Allows one party to terminate immediately without cause, while reciprocal termination rights may be limited or absent.",
            "suggested_question": "Is there a reasonable cure period (e.g. 15-30 days written notice) required before termination can occur?",
            "fin_score": 0.6,
            "sev_score": 0.85,
            "amb_score": 0.4
        },
        {
            "id": "vague_financial_obligations",
            "name": "Vague or Discretionary Fees",
            "risk_level": "Needs review",
            "patterns": [
                r'(?:additional\s+(?:unspecified\s+)?fees\s+may\s+apply)',
                r'(?:charges\s+to\s+be\s+determined\s+at\s+the\s+sole\s+discretion\s+of)',
                r'(?:reimburse\s+all\s+costs\s+without\s+limitation)',
                r'(?:administrative\s+charges\s+as\s+deemed\s+necessary)'
            ],
            "explanation": "Open-ended or unspecified financial obligations that can be levied without fixed caps or itemized justification.",
            "suggested_question": "Can all billable fees, charges, and pass-through expenses be capped or exhaustively defined in a schedule?",
            "fin_score": 0.75,
            "sev_score": 0.5,
            "amb_score": 0.8
        },
        {
            "id": "restrictive_covenant",
            "name": "Burdensome Non-Compete or Exclusivity",
            "risk_level": "Needs review",
            "patterns": [
                r'(?:shall\s+not\s+(?:engage\s+in|work\s+for)[^\.\;]*(?:competitor|competing\s+business)[^\.\;]*(?:2|3|5)\s+years)',
                r'(?:worldwide\s+non-?compete\s+restriction)',
                r'(?:exclusive\s+restriction\s+from\s+accepting\s+any\s+other\s+employment)'
            ],
            "explanation": "Imposes geographically or temporally expansive restrictions on future employment, freelance activities, or contracting.",
            "suggested_question": "Are the geographic scope, temporal duration, and industry definitions of the non-compete reasonable and enforceable?",
            "fin_score": 0.7,
            "sev_score": 0.8,
            "amb_score": 0.5
        },
        {
            "id": "subjective_satisfaction",
            "name": "Subjective Satisfaction Standard",
            "risk_level": "Informational",
            "patterns": [
                r'(?:to\s+the\s+sole\s+satisfaction\s+of\s+(?:the\s+)?(?:company|client|landlord))',
                r'(?:as\s+determined\s+in\s+the\s+absolute\s+judgment\s+of)',
                r'(?:satisfactory\s+in\s+all\s+respects\s+to\s+management)'
            ],
            "explanation": "Performance approval depends on subjective counterparty satisfaction rather than objective deliverables or industry standards.",
            "suggested_question": "Can the performance standard be modified to an objective 'reasonable professional standard' or clear acceptance criteria?",
            "fin_score": 0.4,
            "sev_score": 0.5,
            "amb_score": 0.75
        }
    ]

    @classmethod
    def analyze_clause(cls, clause_text: str, heading: str = "", full_doc_text: str = "") -> List[Dict[str, Any]]:
        """
        Evaluate a clause against transparent risk review rules.
        Considers mutual/bilateral provisions, limiting carve-outs, and document-level context.
        Returns a list of structured RiskFinding records.
        """
        findings = []
        norm_text = clause_text.strip()
        if not norm_text:
            return findings

        # Check for mutual / bilateral provisions
        is_bilateral = bool(re.search(r'\b(?:either\s+party|each\s+party|both\s+parties|mutually\s+agreed|mutual\s+written\s+agreement)\b', norm_text, re.IGNORECASE))

        # Check if full document text contains a global liability cap or dispute resolution clause
        doc_liability_cap = False
        if full_doc_text:
            doc_liability_cap = bool(re.search(r'\b(?:total\s+liability\s+(?:shall\s+not|in\s+no\s+event)\s+exceed|aggregate\s+liability\s+(?:is\s+limited|capped))\b', full_doc_text, re.IGNORECASE))

        for rule in cls.RULES:
            # Skip unilateral modification flags if clause explicitly mandates mutual agreement
            if rule["id"] == "unilateral_modification" and re.search(r'\b(?:mutual\s+written\s+consent|mutually\s+agreed\s+in\s+writing)\b', norm_text, re.IGNORECASE):
                continue

            matched_quote = None
            for pattern in rule["patterns"]:
                match = re.search(pattern, norm_text, re.IGNORECASE)
                if match:
                    matched_quote = match.group(0)
                    break

            if matched_quote:
                # Check for explicit limiting exceptions / statutory bounds
                limitation_found = bool(re.search(
                    r'\b(?:except\s+(?:in\s+the\s+event\s+of|for)|unless\s+mutually\s+agreed|subject\s+to\s+applicable\s+statute|in\s+accordance\s+with\s+law|to\s+the\s+extent\s+permitted\s+by\s+law|capped\s+at)\b',
                    norm_text,
                    re.IGNORECASE
                ))
                
                uncertainty_note = None
                related_clause = None
                level = rule["risk_level"]
                overall_score = (rule["fin_score"] * 0.35 + rule["sev_score"] * 0.45 + rule["amb_score"] * 0.20)

                # Contextual adjustments
                if is_bilateral and rule["id"] in ["immediate_unilateral_termination"]:
                    level = "Needs review"
                    uncertainty_note = "Termination condition applies reciprocally to both parties, but lacks a standard cure window."
                    overall_score = max(0.3, overall_score - 0.20)

                if limitation_found:
                    level = "Needs review" if level == "High attention" else "Informational"
                    uncertainty_note = "A limiting carve-out or statutory exception was recognized within the provision that narrows exposure."
                    overall_score = max(0.2, overall_score - 0.25)

                if rule["id"] == "broad_indemnification" and doc_liability_cap:
                    related_clause = "Document contains an overall aggregate liability cap that may bound this indemnity."
                    overall_score = max(0.25, overall_score - 0.15)

                findings.append({
                    "trigger_type": rule["id"],
                    "rule_name": rule["name"],
                    "risk_level": level,
                    "explanation": rule["explanation"],
                    "evidence_quote": matched_quote,
                    "surrounding_context": norm_text[:300] + ("..." if len(norm_text) > 300 else ""),
                    "suggested_question": rule["suggested_question"],
                    "uncertainty_note": uncertainty_note,
                    "related_clause_context": related_clause,
                    "financial_impact_score": rule["fin_score"],
                    "obligation_severity_score": rule["sev_score"],
                    "ambiguity_score": rule["amb_score"],
                    "overall_score": round(overall_score, 2),
                    "is_reviewed": False
                })

        return findings
