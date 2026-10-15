# RuleRadar AI - Structured Information & Entity Extraction
import re
from typing import List, Dict, Any, Optional
import spacy
import logging

logger = logging.getLogger(__name__)

class InformationExtractor:
    """
    Extracts structured entities, dates/deadlines, financial sums,
    parties, and itemized contractual obligations with high precision.
    """

    _nlp = None

    @classmethod
    def get_spacy(cls):
        """Lazy load spaCy model en_core_web_sm."""
        if cls._nlp is None:
            try:
                cls._nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.warning(f"Could not load en_core_web_sm: {e}. Fallback to pattern NER.")
                cls._nlp = False
        return cls._nlp

    @classmethod
    def extract_financials(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extract currencies, monetary amounts, percentages, and frequencies.
        Preserves original textual format without fabricated interpretations.
        """
        results = []
        # Matches e.g. "$1,500.00", "USD 50,000", "€200", "₹ 25,000", "5% per annum"
        patterns = [
            r'(?P<amount>(?:[$€£₹]|USD|EUR|INR|GBP|\bRs\.?)\s*[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*(?P<freq>per\s+(?:month|annum|year|hour|week|day|diem)|monthly|annually|bi-?weekly|one-?time)?',
            r'(?P<amount>[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?\s*(?:dollars|euros|rupees|pounds))\s*(?P<freq>per\s+(?:month|annum|year)|monthly|annually)?',
            r'(?P<amount>[0-9]+(?:\.[0-9]+)?%)\s*(?P<freq>interest|late\s+fee|penalty|per\s+month|per\s+annum)?'
        ]

        seen = set()
        for pat in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                val = match.group("amount").strip()
                freq = match.group("freq")
                freq_val = freq.strip() if freq else "one-time / specified in text"
                key = (val.lower(), match.start())
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "raw_text": match.group(0).strip(),
                        "amount_or_percentage": val,
                        "frequency": freq_val,
                        "start_char": match.start(),
                        "end_char": match.end()
                    })
        return results

    @classmethod
    def extract_deadlines(cls, text: str, page_num: int = 1) -> List[Dict[str, Any]]:
        """
        Detect explicit dates, time windows, and notice requirements.
        """
        deadlines = []
        patterns = [
            # Timeframes: "within 30 days", "within ten (10) business days"
            (r'\bwithin\s+(?:[0-9]+|\w+\s*\([0-9]+\))\s+(?:business\s+)?(?:days?|weeks?|months?|hours?)\b', "Time Limit / Action Window"),
            # Notice periods: "30 days' written notice", "prior written notice of 60 days"
            (r'\b(?:[0-9]+|\w+\s*\([0-9]+\))\s+days?(?:\'|\s+written)?\s+notice\b', "Notice Period"),
            # Absolute dates: "January 15, 2027", "15th of each month", "31/12/2026"
            (r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{1,2}(?:st|nd|rd|th)?,?\s+[2][0-9]{3}\b', "Specific Calendar Date"),
            (r'\b[0-3]?[0-9][\/\-\.][0-1]?[0-9][\/\-\.][2][0-9]{3}\b', "Calendar Date"),
            (r'\b(?:1st|2nd|3rd|[0-9]{1,2}th)\s+day\s+of\s+(?:each|every)\s+month\b', "Recurring Due Date")
        ]

        seen = set()
        for pat, d_type in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                snippet = match.group(0).strip()
                if snippet.lower() in seen:
                    continue
                seen.add(snippet.lower())
                # Context snippet around match
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 60)
                context = text[start:end].replace("\n", " ").strip()

                deadlines.append({
                    "date_or_period": snippet,
                    "deadline_type": d_type,
                    "context": f"...{context}...",
                    "page_number": page_num
                })
        return deadlines

    @classmethod
    def extract_parties_and_entities(cls, text: str, page_num: int = 1) -> List[Dict[str, Any]]:
        """
        Extract defined contractual entities (e.g. Landlord, Tenant, Client)
        and spaCy named entities (ORG, PERSON, GPE, MONEY, DATE).
        """
        entities = []
        seen = set()

        # 1. Contractual defined roles
        role_patterns = [
            r'\b(?:hereinafter\s+(?:referred\s+to\s+as\s+)?[\'"](?P<role>[A-Za-z0-9\s]+)[\'"])',
            r'\b(?:the\s+[\'"](?P<role>Landlord|Tenant|Employer|Employee|Client|Contractor|Company|Consultant|Licensee|Licensor|Buyer|Seller)[\'"])',
            r'\b(?P<role>Landlord|Tenant|Employer|Employee|Client|Contractor)\s+shall\b'
        ]

        for pat in role_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                role = m.group("role").strip()
                if role.lower() not in seen:
                    seen.add(role.lower())
                    entities.append({
                        "entity_type": "ROLE",
                        "entity_text": role,
                        "page_number": page_num,
                        "start_offset": m.start(),
                        "end_offset": m.end()
                    })

        # 2. spaCy NER
        nlp = cls.get_spacy()
        if nlp and len(text) < 100000:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["ORG", "PERSON", "GPE", "DATE", "MONEY"]:
                    val = ent.text.strip()
                    if len(val) > 2 and val.lower() not in seen:
                        seen.add(val.lower())
                        entities.append({
                            "entity_type": ent.label_,
                            "entity_text": val,
                            "page_number": page_num,
                            "start_offset": ent.start_char,
                            "end_offset": ent.end_char
                        })

        return entities

    @classmethod
    def extract_obligations(cls, clause_text: str) -> List[Dict[str, Any]]:
        """
        Extract actionable obligations by identifying the responsible party,
        modal command ('shall', 'must', 'agrees to'), action predicate, and triggering conditions.
        """
        obligations = []
        # Sentences containing strong obligation markers
        sentences = re.split(r'(?<=[.!?])\s+', clause_text)

        obligation_pattern = re.compile(
            r'(?P<party>\b[A-Z][A-Za-z0-9_\s]{2,25}?\b)?\s*(?P<modal>shall|must|agrees?\s+to|is\s+required\s+to|will)\s+(?P<action>[^;,\.]{5,150})',
            re.IGNORECASE
        )

        for sent in sentences:
            sent_str = sent.strip()
            if not sent_str:
                continue

            match = obligation_pattern.search(sent_str)
            if match:
                party_raw = match.group("party")
                action_raw = match.group("action")
                modal = match.group("modal")

                # Clean party
                party = "Not specified"
                if party_raw:
                    clean_p = party_raw.strip()
                    if clean_p.lower() in ["the", "this", "that", "it", "which", "and"]:
                        clean_p = "Not specified"
                    party = clean_p

                # Detect conditions: "if", "provided that", "in the event of"
                cond_match = re.search(r'\b(?:in\s+the\s+event\s+that|provided\s+that|if|upon)\s+([^,\.]{5,80})', sent_str, re.IGNORECASE)
                trigger_cond = cond_match.group(0).strip() if cond_match else None

                # Detect deadline inside sentence
                deadline_match = re.search(r'\b(?:within\s+[0-9]+\s+days?|by\s+[A-Z][a-z]+\s+[0-9]{1,2}|prior\s+to\s+[^\,\.]{3,30})\b', sent_str, re.IGNORECASE)
                deadline = deadline_match.group(0).strip() if deadline_match else None

                # Detect consequence: "or this agreement may be terminated", "failing which"
                consequence_match = re.search(r'\b(?:failing\s+which|otherwise\s+[^\.\,]+|failure\s+to\s+comply\s+shall\s+[^\.\,]+)\b', sent_str, re.IGNORECASE)
                consequence = consequence_match.group(0).strip() if consequence_match else None

                obligations.append({
                    "responsible_party": party,
                    "required_action": f"{modal.lower()} {action_raw.strip()}",
                    "trigger_condition": trigger_cond,
                    "deadline": deadline,
                    "consequence": consequence,
                    "confidence": 0.85
                })

        return obligations
