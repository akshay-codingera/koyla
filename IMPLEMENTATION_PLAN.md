# IMPLEMENTATION_PLAN.md
# CIL / CMPDI AI Reporting & Intelligence Platform
# Master Technical Implementation Plan

## 1. Executive Summary & Problem Context
**Problem Statement:** SIH 26023 — "AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries"
**Target System:** Internal enterprise reporting intelligence platform for Coal India Limited (CIL) and Central Mine Planning & Design Institute (CMPDI).
**Core Value Proposition:** Transforms heterogeneous, multi-format mining documents (geological survey reports, borehole stratigraphy logs, monthly production bulletins, overburden stripping returns, statutory safety filings) into a verifiable, audit-backed knowledge repository featuring:
1. Native parsing & local OCR with table structure recovery
2. Structure-preserving chunking and hybrid semantic/lexical indexing
3. Grounded Q&A with strict evidence extraction, zero external cloud dependencies, and clear refusal mechanics
4. Deterministic template-driven report generation producing genuine editable `.docx` files
5. Quantitative topic modeling, c-TF-IDF keyword extraction, and word clouds
6. Human-in-the-loop verification triage queue
7. Immutable audit logging and multi-node simulated federation

---

## 2. Non-Negotiable Architecture Constraints
1. **Zero External Runtime AI APIs:** No runtime calls to OpenAI, Anthropic, Gemini, Pinecone, or any external hosted services. System operates fully inside a local / air-gapped government network.
2. **Local AI Toolchain:**
   - LLM: Local Ollama / vLLM / OpenAI-compatible local server adapter (`http://localhost:11434/v1` or `http://localhost:8000/v1`) with deterministic extractive rule fallback when running without GPU.
   - Embeddings: Local `sentence-transformers` (`all-MiniLM-L6-v2` or `bge-small-en-v1.5`).
   - OCR: Local `PaddleOCR` with `Tesseract` fallback and `OpenCV` image preprocessing (deskew, denoise, binarization).
   - Document Parsing: `PyMuPDF` / `pdfplumber` for digital PDFs, `openpyxl` for spreadsheets, `python-docx` for Word documents.
   - Report Rendering: Deterministic `python-docx` rendering based on validated structured records.
3. **Multi-Database Support (Production + Standalone Local Dev):**
   - Production Target: PostgreSQL 16+ with `pgvector`.
   - Standalone Local Dev Fallback: SQLite with NumPy vector cosine similarity and SQLite FTS5 for full-text search, ensuring 100% out-of-the-box local execution on any Windows/Linux workstation without requiring a running Docker or PostgreSQL service.
   - Containerization: Production-grade `docker-compose.yml` defining frontend, backend, worker, postgres+pgvector, and redis.
4. **Anti-Hallucination & Anti-Fake Guardrails:**
   - Extract-then-compose Q&A pipeline: Composition model only sees verbatim extracted evidence snippets.
   - Clear refusal threshold: Returns *"Insufficient verified evidence found in the indexed sources"* when similarity or evidence score is below threshold.
   - Real calculated KPIs: Dashboard metrics are computed from actual database records.
   - Prominent UI badge: `"Prototype / Demo Dataset"` displayed on all synthetic seed records.
5. **No Dead UI:** All 14 routes, modals, tables, and actions are backed by real FastAPI endpoints with loading, empty, and error states.

---

## 3. Institutional Hierarchy & Organizational Model
The platform models Coal India Limited's operational and planning structure:
```
Coal India Limited (Apex Holding Company)
└── CMPDI (Central Mine Planning & Design Institute - Ranchi HQ)
    ├── Regional Institute - I (Asansol)        <---> ECL (Eastern Coalfields Limited)
    ├── Regional Institute - II (Dhanbad)       <---> BCCL (Bharat Coking Coal Limited)
    ├── Regional Institute - III (Ranchi)       <---> CCL (Central Coalfields Limited)
    ├── Regional Institute - IV (Nagpur)        <---> WCL (Western Coalfields Limited)
    ├── Regional Institute - V (Bilaspur)       <---> SECL (South Eastern Coalfields Limited)
    ├── Regional Institute - VI (Singrauli)     <---> NCL (Northern Coalfields Limited)
    ├── Regional Institute - VII (Bhubaneswar)  <---> MCL (Mahanadi Coalfields Limited)
    └── HQ-served / Non-RI Mapping              <---> NEC (North Eastern Coalfields)
```
Lower-level organizational units: Areas (e.g., Korba, Dipka, Kusmunda, Rajmahal), Mines/Collieries (Open Cast, Underground), and Exploration Blocks.

---

## 4. Role-Based Access Control (RBAC)
Configurable role definitions enforced strictly at the FastAPI middleware/dependency level:
1. **Ministry Officer / Cross-Organization Viewer:** Read-only access across all subsidiaries and RIs; views national summaries, executive dashboards, and approved briefs.
2. **CMPDI HQ Officer:** Cross-subsidiary and cross-RI visibility for planning, survey digestion, cross-validation, and high-level report approval.
3. **RI Analyst:** Scoped to designated Regional Institute and associated subsidiary; manages geological survey ingestions, borehole stratigraphy, and exploration data.
4. **Subsidiary Analyst:** Scoped to designated operating subsidiary (e.g. SECL, ECL); ingests mine production figures, monthly returns, and stripping ratios.
5. **Verification Officer:** Triage authority to review low-confidence OCR, reconcile conflicting cross-document values, and approve/reject drafted reports.
6. **System Administrator:** Manages users, organization trees, trust tiers, validation rules, and system health.

---

## 5. End-to-End Processing & Intelligence Pipeline
```
[Document Upload (PDF, XLSX, DOCX, IMG)]
                  │
                  ▼
         [SHA-256 Hash & MIME Check]
                  │
                  ▼
         [Processing Job Queued]
                  │
                  ▼
  ┌───────────────┴───────────────┐
  │                               │
  ▼                               ▼
[Digital PDF / DOCX / XLSX]    [Scanned PDF / Images]
(PyMuPDF, python-docx, openpyxl) (OpenCV Deskew/Denoise + PaddleOCR)
  │                               │
  └───────────────┬───────────────┘
                  │
                  ▼
    [Table & Structure Recovery]
                  │
                  ▼
    [Structure-Preserving Chunking]
                  │
                  ▼
   [Local Embeddings (sentence-transformers)]
                  │
                  ▼
    [Hybrid Indexing: Dense + BM25]
                  │
                  ▼
  [Domain Extraction & Deterministic Validation]
                  │
                  ▼
    [Conflict Detection & Review Flagging]
```

---

## 6. Phased Implementation Roadmap

### Phase 0: System Architecture & Design Documentation (Immediate)
- Complete design documents in project root:
  - `IMPLEMENTATION_PLAN.md`
  - `ARCHITECTURE.md`
  - `DATABASE_SCHEMA.md`
  - `API_CONTRACT.md`
  - `UI_MAP.md`
  - `SECURITY_MODEL.md`
  - `TEST_PLAN.md`
  - `DEMO_SCRIPT.md`

### Phase 1: Repository Foundation, Database, RBAC & Audit
- Backend directory scaffolding: `backend/app/api`, `backend/app/core`, `backend/app/db`, `backend/app/models`, `backend/app/schemas`, `backend/app/services`.
- Database engine setup: SQLAlchemy 2.0 with PostgreSQL+pgvector engine and standalone SQLite/NumPy fallback.
- Database tables creation & migrations.
- Seed master data: CIL, CMPDI, 7 RIs, 8 Subsidiaries, Areas, Mines.
- User authentication (JWT tokens, password hashing) and RBAC middleware.
- Immutable audit trail logging service.

### Phase 3: Document Intelligence & Multi-Page Table Continuity (ACCEPTED)
- Native parsers for digital PDF (`PyMuPDF`), spreadsheets (`openpyxl`), and documents (`python-docx`).
- Local OCR pipeline with image preprocessing and Tesseract fallback.
- Physical & logical multi-page table preservation with deterministic continuation scoring formula.
- Structure-preserving chunking preserving exact page provenance and repeated headers.

### Phase 4: Structured Extraction, Validation, Provenance & Verification (ACCEPTED)
- Mining domain schema: mine name, coal seam, seam thickness, stripping ratio, coal production, ash content, fiscal year.
- Deterministic regex & table extractor services with field-level provenance (`TableRow.source_page`).
- Deterministic domain boundary validation (stripping ratio non-negative, ash content 0-100%, units, FY format).
- Cross-document reconciliation engine with configurable prototype policy threshold (`settings.RECONCILIATION_VARIANCE_THRESHOLD`).
- Human verification queue (`/verification`) with `APPROVE`, `CORRECT`, `REJECT`, `DEFER` actions and audit trail.

### Phase 5: Hybrid Retrieval, pgvector Indexing, Reranking & Knowledge Explorer (ACTIVE)
- Local embedding service (`EmbeddingProvider`) with `LocalSentenceTransformerProvider` and `DeterministicLocalEmbeddingProvider` (384-d normalized vectors).
- Database pgvector schema extensions on `embeddings` (vector index, unique constraints, metadata).
- PostgreSQL full-text search (`tsvector` / `plainto_tsquery` / `ts_rank_cd`) + exact substring lexical matching.
- Query normalization engine detecting entities (mines, subsidiaries), metrics, and fiscal periods (`period_start`, `period_end`).
- Server-side organization scoping and metadata filtering (FY, doc type, source tier).
- Reciprocal Rank Fusion (RRF) combining lexical and semantic rankings ($k=60$).
- Local cross-encoder reranker with graceful fallback when disabled/offline.
- Reusable `RetrievalResult` and `RetrievalTrace` contracts preserving full provenance.
- Incremental and batch chunk indexing pipeline integrated into ingestion jobs.
- Knowledge Explorer UI (`/knowledge` and `/search`) with multi-modal search, filters, provenance modal, and document viewer navigation.

### Phase 6: Grounded AI Q&A Engine & Citation (COMPLETED)
- Extract-then-compose Q&A pipeline calling Phase 5 retrieval engine.
- Local LLM answer composition strictly grounded in retrieved evidence chunks.
- Refusal mechanism: "Insufficient verified evidence found in the selected knowledge base."
- Entailment check and verbatim citations with physical page links.
- Interactive Q&A UI (`/ask`) with query history, evidence cards, citations, and confidence badges.

### Phase 7: Prescribed Official Report Formats & Statutory Report Studio (COMPLETED)
- Authoritative statutory schema conforming strictly to Ministry of Coal / CCO OM F.No. CPAM-34011/28/2019-CPAM [E-343762] dated 31 January 2025, Appendix-I ("DETAILS TO BE FURNISHED IN THE MINING PLANS FOR COAL/LIGNITE BLOCKS").
- Automated statutory inventory verification (`schema_audit.py`): 184 total nodes, 136 actionable statutory requirements, 12 prescribed tables, 9 technical plates (with OC/UG conditionality), 13 statutory annexures, 4 certifications/undertakings, zero invented IDs.
- Deterministic calculations: 7-step ISP/UNFC geological-to-extractable reserve deduction cascade, stripping ratio ($m^3/t$), Life of Mine (LOM), and mandatory 2025 Just Transition minimum 25% escrow rule (Section 8.4.2).
- Strict safeguards: missing data rendered strictly as `DATA NOT AVAILABLE IN VERIFIED KNOWLEDGE BASE`, unattached plates rendered as `NOT GENERATED — SOURCE DATA REQUIRED`.
- Statutory review & digital signing workflow: Qualified Person (Rule 22C MCR 1960) inline review/correction preserving original and revised values, digital execution of statutory certificates (`AUTHORIZED_SIGNED`), and immutable version freezing with SHA-256 fingerprinting.
- Submission readiness engine: distinguishes `DRAFT_INCOMPLETE` from `READY_FOR_AUTHORIZED_SUBMISSION` (never claiming CCO approval).
- Native DOCX generator: produces physical format-conforming DOCX files with real tables, metadata headers, undertakings, and cryptographic hashes.
- Full UI suite: `/reports`, `/reports/new`, and `/reports/:id` (Report Studio) with multi-tab statutory workbench.
- Verification: 13/13 Phase 7 tests passed, 86/86 full backend regression tests passed, 0 frontend build errors, and 8 live Playwright browser acceptance screenshots captured.

### Phase 8: Topic Identification & Word Cloud Analytics
- Topic clustering engine using document embeddings and c-TF-IDF keyword extraction.
- Trend analysis across fiscal years and subsidiaries.
- Topic Analytics UI (`/topics`) with topic ranking, term distributions, and interactive Word Cloud.

### Phase 8: Human Verification Center & Executive Dashboard
- Verification Queue UI (`/verification`) with tri-pane layout (source preview, extracted value, approval/correction actions).
- Executive Dashboard UI (`/dashboard`) computing live calculated metrics directly from database queries.
- Prominent `"Prototype / Demo Dataset"` banner.

### Phase 9: Multi-Node Federation Simulator
- 3 isolated simulated data nodes (`node-cmpdi`, `node-secl`, `node-ecl`).
- Federation gateway API routing queries to relevant nodes, merging ranked evidence, and preserving node provenance.
- Organization explorer & federation UI (`/organization`).

### Phase 10: Governance, System Health, E2E Testing & Demo Dataset
- System Health UI (`/system`) with real ping checks for API, DB, Vector Index, OCR, and LLM services.
- Governance & Audit UI (`/governance`) with immutable event log and SHA-256 file integrity verification.
- Administration UI (`/administration`) for managing users, roles, organizations, and validation rules.
- Synthetic demonstration dataset (25+ realistic mining & geological reports, clean PDFs, scanned reports, spreadsheets, conflicting source pairs).
- Automated test suite (Pytest backend unit/integration tests, frontend build, and Playwright E2E browser tests).
- UI polishing following government portal visual standards.

---

## 7. Technology Stack Summary
- **Backend:** Python 3.14 / 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, PyMuPDF, python-docx, openpyxl, OpenCV, sentence-transformers, NumPy.
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Lucide Icons, Chart.js / Recharts.
- **Data Layer:** PostgreSQL 16 + pgvector (with zero-dependency local SQLite/NumPy fallback).
- **Deployment:** Multi-container `docker-compose.yml` (frontend, backend, worker, postgres+pgvector, redis) and local direct CLI runner.

---

## 8. Definition of Done
The system is considered production-prototype complete when:
1. User logs in with assigned role and organization scope.
2. Ingests PDF/DOCX/XLSX/Image; SHA-256 hash is computed; parser/OCR executes locally.
3. Extracted fields and detected tables are stored with page/span provenance.
4. Deterministic validation flags cross-document conflicts into the Verification Queue.
5. Hybrid search retrieves relevant chunks with RRF.
6. Grounded Q&A answers questions with source citations or cleanly refuses when ungrounded.
7. Report Studio generates and downloads an actual `.docx` file from validated records.
8. Human verification approves/corrects pending items with audit logging.
9. Executive dashboard updates live from actual database calculations.
10. All 14 routes are fully functional with zero dead buttons or placeholder UI.
