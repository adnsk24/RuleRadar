# RuleRadar AI

**AI-Powered Document Intelligence, Important Clause Identification, Risk Analysis & Semantic Comparison System**

RuleRadar AI is a production-oriented, open-source document intelligence system built for analyzing complex agreements, discovering concerning conditions, extracting obligations and deadlines, comparing document versions, and answering questions grounded in verifiable citations.

---

## 🌟 Key Capabilities

1. **Document Ingestion & Multi-Format Parsing**
   - Supports **PDF** (via PyMuPDF / fitz), **DOCX** (via python-docx), and **TXT** files.
   - Preserves page numbers, paragraph integrity, character offsets, and bounding metadata.
   - Detects low-text / scanned PDFs (< 40 characters per page with embedded images) and issues transparent warnings.
   - Strictly validates magic bytes, file extensions, and limits (25 MB max, 150 pages max).

2. **20-Category Clause Classification**
   - Classifies contractual provisions across 20 distinct legal taxonomies:
     1. Payment and financial obligations
     2. Penalties and late fees
     3. Security deposits and refunds
     4. Termination and cancellation
     5. Renewal and automatic renewal
     6. Liability and indemnification
     7. Confidentiality
     8. Intellectual property
     9. Privacy and data handling
     10. Dispute resolution
     11. Governing law and jurisdiction
     12. Eligibility requirements
     13. Deadlines and time limits
     14. Duties and responsibilities
     15. Restrictions and prohibitions
     16. Conditions and exceptions
     17. Warranties and guarantees
     18. Force majeure
     19. Notice requirements
     20. Other or unclassified clauses
   - Uses multi-signal scoring combining semantic anchor vectors, structural pattern recognition, and calibrated confidence (uncertain clauses cleanly fall back to "Other or unclassified clauses").

3. **Transparent Risk Review Engine**
   - Flags clauses requiring human review without presenting probabilistic model outputs as legal advice.
   - Detects:
     - Unilateral modification rights
     - Broad or unlimited indemnification / waivers
     - Disproportionate forfeiture and severe penalties
     - Non-refundable deposits or discretionary return conditions
     - Auto-renewal traps with tight cancellation windows
     - Immediate asymmetric termination without cause
     - Vague, open-ended fees
     - Burdensome non-compete covenants
     - Subjective performance satisfaction standards
   - Generates granular scores across Financial Impact, Obligation Severity, and Ambiguity.
   - Synthesizes verbatim evidence quotations and suggested investigative questions for users.

4. **Clause Importance Scoring**
   - Separate from risk: evaluates structural significance based on mandatory language, specific monetary sums, deadlines, and core covenants.
   - Scored from 0.0 to 10.0 and categorized as `High` (≥ 7.0), `Medium` (≥ 4.0), or `Low` (< 4.0).

5. **Structured Information Extraction**
   - **Dates and Deadlines**: Notice windows ("within 30 days", "60 days written notice"), calendar dates, recurring due dates.
   - **Financials**: Currencies ($, €, £, ₹, USD, EUR, INR), numbers, percentages, payment frequencies.
   - **Parties & Entities**: Defined roles (Landlord, Tenant, Client, Contractor) + spaCy NER (ORG, PERSON, GPE, MONEY, DATE).
   - **Obligations**: Identifies responsible party, modal verb ("shall", "must"), action predicate, triggering conditions, and consequences.

6. **Semantic Revision Comparison & Visual Diff**
   - Aligns clauses between two versions using section numbers, structural headings, token overlap, and sentence embeddings.
   - Highlights:
     - Substantively modified provisions with word-level HTML diffs (`<del>` and `<ins>`).
     - Changed monetary values (e.g. $1,200.00 ➔ $1,450.00).
     - Changed deadlines (e.g. 30 days ➔ 60 days).
     - Obligation modal shifts (e.g. "may" escalated to "shall").
     - Newly added provisions with plain-English rationales.
     - Removed provisions with plain-English rationales.

7. **Document-Grounded Q&A & Conversational Assistant**
   - Evidence-grounded retrieval combining semantic similarity and keyword BM25 filtering.
   - Zero hallucination guarantee: Cites exact clause number, section heading, page number, and verbatim quotation.
   - States explicitly when a document lacks sufficient evidence instead of fabricating facts.
   - Distinguishes conversational greetings, application help requests, and legal advice inquiries (providing appropriate statutory disclaimers).

8. **Multi-Format Export & Data Management**
   - Download styled, printable **PDF** reports (via ReportLab).
   - Download editable Microsoft Word **DOCX** reports (via python-docx).
   - Download structured **JSON** exports.
   - Data retention controls: Purge documents older than N days.
   - Permanent document deletion with cascade cleanup of physical files and database rows.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.10+ / 3.14+, FastAPI, Pydantic v2, Pydantic-Settings |
| **Database** | SQLAlchemy 2.0 ORM with SQLite (thread-safe, PostgreSQL ready) |
| **PDF Extraction** | PyMuPDF (`pymupdf`) with page tracking and scanned-image heuristics |
| **DOCX Extraction** | `python-docx` for paragraphs, headings, and table cells |
| **NLP & Entities** | spaCy (`en_core_web_sm`), scikit-learn (TF-IDF, Cosine Similarity, N-grams) |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) with automatic TF-IDF CPU fallback |
| **Report Generation** | ReportLab (styled PDF generation) and `python-docx` (DOCX reports) |
| **Frontend UI** | HTML5, Vanilla CSS3 (Custom SaaS Design System), Vanilla ES6 JavaScript |
| **Testing** | `pytest`, `httpx` (TestClient) |

---

## 📂 Project Structure

```
d:/NLP/Project/
├── app/
│   ├── main.py                     # FastAPI application setup, routes & static mounting
│   ├── config.py                   # Pydantic BaseSettings, paths, thresholds, and limits
│   ├── seed.py                     # Database seeder for synthetic demo documents
│   ├── db/
│   │   ├── database.py             # SQLAlchemy engine & session maker
│   │   └── models.py               # Document, Page, Clause, RiskFinding, Entity, Obligation, etc.
│   ├── nlp/
│   │   ├── ingestion.py            # PDF, DOCX, TXT validation, extraction & pagination
│   │   ├── segmentation.py         # Numbered sections, headings & clause segmentation
│   │   ├── embeddings.py           # SentenceTransformer with TF-IDF fallback
│   │   ├── classifier.py           # 20-category clause classifier & explanation engine
│   │   ├── risk_engine.py          # Evidence-based review rules, scores & suggested questions
│   │   ├── importance_engine.py    # Independent importance scoring engine (0-10)
│   │   ├── extractor.py            # Dates, deadlines, financial sums, entities, obligations
│   │   ├── comparison.py           # Semantic comparison, field change detection & inline diff
│   │   └── qa_engine.py            # Grounded extractive Q&A & conversational router
│   ├── services/
│   │   ├── document_service.py     # Orchestrator for ingestion, NLP analysis & DB transactions
│   │   └── export_service.py       # PDF (ReportLab), DOCX & JSON report generators
│   ├── api/
│   │   ├── routes_documents.py     # Upload, list, inspect, and delete endpoints
│   │   ├── routes_analysis.py      # Clause explorer and review status toggling
│   │   ├── routes_compare.py       # Version comparison endpoints
│   │   ├── routes_qa.py            # Grounded Q&A and history endpoints
│   │   ├── routes_export.py        # PDF, DOCX, JSON report downloads
│   │   └── routes_system.py        # Health check, dashboard stats, retention purge
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Modern SaaS stylesheet (Inter font, responsive, tokens)
│   │   └── js/
│   │       ├── app.js              # Application state and navigation router
│   │       ├── dashboard.js        # Live statistics and documents repository controller
│   │       ├── upload.js           # Drag-and-drop validation & upload controller
│   │       ├── workspace.js        # Two-panel document viewer & highlight controller
│   │       ├── compare.js          # Version comparison controller
│   │       └── qa.js               # Q&A assistant, clause explorer & settings controller
│   └── templates/
│       └── index.html              # Single-page SaaS interface
├── sample_documents/               # Synthetic evaluation and demo agreements
│   ├── sample_rental_agreement_v1.txt
│   ├── sample_rental_agreement_v2.txt
│   └── sample_employment_contract.txt
├── tests/
│   ├── test_ingestion.py           # PDF, DOCX, TXT parsing and validation tests
│   ├── test_classifier.py          # 20-category classification tests
│   ├── test_risk_engine.py         # Risk review rules and importance scoring tests
│   ├── test_extractor.py           # Financial, deadline, and obligation extraction tests
│   ├── test_comparison.py          # Semantic version comparison tests
│   ├── test_qa.py                  # Grounded Q&A and citation verification tests
│   ├── test_api_integration.py     # Full end-to-end API integration tests
│   └── test_evaluation_dataset.py  # Precision, recall, and revision diff metrics
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart & Installation

### 1. Clone or Open the Repository
```bash
cd d:/NLP/Project
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Optional) Download the lightweight spaCy English model if not already present:*
```bash
python -m spacy download en_core_web_sm
```

### 3. Initialize & Seed Database (Optional for Demo Data)
```bash
python -m app.seed
```
This populates the local SQLite database with synthetic Rental Agreement v1, Rental Agreement v2, and Employment Contract samples.

### 4. Start the Application Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access the Web Interface
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 🧪 Running the Automated Test Suite

To run all 32 unit, integration, and evaluation tests:
```bash
python -m pytest -v
```

To run the labeled evaluation dataset and view measured metrics:
```bash
python -m pytest tests/test_evaluation_dataset.py -s
```

**Measured Benchmark Metrics:**
- **Clause Classification Accuracy**: `91.7%` (11/12 on labeled ground truth benchmark)
- **Synthetic Revision Diff Accuracy**: `100%` (Correctly detected rent change `$1,200.00` ➔ `$1,450.00`, notice window change `30 days` ➔ `60 days`, and new unilateral modification risk)
- **Test Pass Rate**: `32 passed, 0 failed (100%)`

---

## 🔒 Security & Privacy Guarantees

- **No Remote AI Transmission**: Analyzed documents and extracted clauses remain strictly inside the local SQLite database and uploads folder.
- **Untrusted File Protections**: Safe UUID-based filename sanitization, protection against path traversal via `os.path.abspath` bounds checking, and strict magic-byte validation.
- **No Execution**: Document text is never evaluated or executed in any shell or script context.
- **GDPR Retention Controls**: Includes an automated purge endpoint (`POST /api/system/retention/purge`) to permanently scrub documents older than N days.

---

## ☁️ Free-Tier Public Deployment Guide

RuleRadar AI is designed to run efficiently on low-resource, free-tier hosting environments (such as Render, Railway, Hugging Face Spaces, or Fly.io) with 512 MB to 1 GB RAM:

### Deployment on Render / Railway:
1. **Build Command**:
   ```bash
   pip install -r requirements.txt && python -m spacy download en_core_web_sm
   ```
2. **Start Command**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
3. **Environment Variables**:
   ```env
   OFFLINE_MODE=False
   DATABASE_URL=sqlite:///data/ruleradar.db
   ```
4. **Persistent Disks**: If deploying to an ephemeral container, mount a persistent volume at `/data` to persist documents and SQLite across restarts.

---

## ⚠️ Known Limitations & Disclaimers

1. **Scanned Images**: Optical Character Recognition (OCR) for scanned PDFs without an underlying text layer is flagged via a warning badge (`⚠️ Low-Text PDF`). Native OCR requires external system binaries (`tesseract-ocr`), which are not bundled by default to maintain lightweight zero-dependency deployment.
2. **Legal Advice Disclaimer**: Automated risk indicators and importance scores are prioritization aids to facilitate human document review. They do not constitute formal legal counsel or statutory legal validity.
