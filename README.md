# Koyla

Koyla is an intelligent document analysis platform that transforms unstructured documents into useful insights. It provides intelligent document ingestion, automated report generation, word-cloud visualization, topic identification, and contextual query-response chat, helping users understand and retrieve information efficiently for fast insights.

---

## CIL / CMPDI Reporting Intelligence Platform
**AI-Assisted Geological, Mining & Statutory Reporting Intelligence**  
*Built for SIH Problem Statement 26023: "AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries"*

---

## 1. Executive Summary & Mission

KOYLA is an enterprise-grade, air-gapped, on-premise capable reporting intelligence platform designed specifically for **Coal India Limited (CIL)** and the **Central Mine Planning & Design Institute (CMPDI)**. 

The platform transforms heterogeneous, unstructured mining dossiers—such as Geological Exploration Reports, Mine Plans, Progressive Mine Closure Plans, and Environmental Impact Statements—into a structured, cross-searchable, audit-verified knowledge base.

### The Unified Intelligence Pipeline
$$\text{Documents} \longrightarrow \text{OCR / Extraction} \longrightarrow \text{Validation Engine} \longrightarrow \text{Hybrid Retrieval} \longrightarrow \text{Grounded Q&A} \longrightarrow \text{Topic Intelligence} \longrightarrow \text{Statutory Reports} \longrightarrow \text{Audit Ledger}$$

Every insight, number, trend, and generated statutory report is traceable to verifiable physical page evidence with zero reliance on external cloud AI APIs.

---

## 2. Core Architectural Principles (Non-Negotiable)

1. **Air-Gapped Local Execution**: Runs entirely on-premise without external internet access. Embeddings (`BAAI/bge-small-en-v1.5`), OCR (Tesseract / PyMuPDF), search (pgvector + BM25), and local inference run self-hosted.
2. **Deterministic Mathematical Formulations**: Calculations for statutory reserve deductions, mine closure escrows, c-TF-IDF keyword weights, and temporal percentage-point changes are executed via deterministic code—never delegated to an LLM.
3. **Traceability & Physical Evidence Grounding**: Every answer, topic term, and extracted field preserves deep physical provenance (`[Doc #ID, Page #P, Chunk #C]`).
4. **Anti-Hallucination Refusal**: When evidence is missing or below safety confidence thresholds, the system explicitly refuses rather than speculating.
5. **Minimum-Evidence Gate**: Sample sizes are strictly gated; topics with insufficient longitudinal history are categorized as `INSUFFICIENT_HISTORY` to prevent misleading percentage fluctuations.
6. **Statutory Report Compliance**: Analytical topic briefs attach as optional annexures, keeping official chapter hierarchies and statutory tables completely untouched.
7. **Genuine Operational Telemetry**: System health probes perform real live capability checks (`SELECT 1`, pgvector `<->` operator, local model weights)—no cosmetic or fake green statuses.

---

## 3. Implemented Modules (Phases 1 through 8.5)

| Module | Route | Capabilities & Features |
|---|---|---|
| **Executive Dashboard** | `/dashboard` | Calculated KPI telemetry, document volumes, verification queue backlog, distribution across subsidiaries, and processing status. |
| **Organization Network** | `/organizations` | Hierarchical governance tree (CIL $\to$ CMPDI $\to$ Regional Institutes $\to$ Subsidiaries $\to$ Areas $\to$ Mines) with strict server-side RBAC scoping. |
| **Document Intelligence** | `/documents`, `/upload` | Ingestion of PDF, DOCX, XLSX, images; SHA-256 cryptographic hashing; native PyMuPDF extraction; local OpenCV deskewing/denoising; OCR. |
| **Extraction & Validation** | `/documents/:id` | Automated field extraction, domain range sanity checks, cross-document reconciliation, and provenance inspector with deep page highlighting. |
| **Hybrid Search & Grounded Q&A** | `/search`, `/ask` | Dense vector retrieval (pgvector) combined with lexical BM25 via Reciprocal Rank Fusion (RRF); grounded extract-then-compose Q&A with refusal. |
| **Topic Intelligence Control Room** | `/topics` | Single global topic model, c-TF-IDF Word Cloud, longitudinal temporal trends ($\Delta_{\text{abs}}$, $\Delta_{\text{pp}}$, $g_{\text{rel}}$), multi-dimensional comparison, and local AI summary. |
| **Statutory Report Studio** | `/reports`, `/reports/:id` | Template-driven generator (`python-docx`), UNFC reserve deduction hierarchy, 25% mine closure escrow validation, and Topic Brief annexure inspector. |
| **Verification Queue** | `/verification` | Human-in-the-loop triage for low-confidence extractions, conflicting source records, and suspicious values with full audit trail. |
| **Audit & Governance** | `/audit` | Immutable SQL event ledger tracking user actions, hashes, timestamps, and organization scopes. |
| **System Health & Telemetry** | `/system` | Real-time capability check probing all 9 subsystems (Backend, API, DB, pgvector, OCR, Embeddings, LLM, Topics, Reports). |
| **Multi-Node Federation** | `/federation` | Simulated distributed query gateway across `node-cmpdi`, `node-secl`, and `node-ecl`. |

---

## 4. Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy ORM, Pydantic v2, Uvicorn.
- **Database & Search**: PostgreSQL 16 with `pgvector` extension; SQLite + NumPy cosine fallback for standalone local execution; FTS5 / BM25 lexical search.
- **Document Processing**: PyMuPDF (`fitz`), `python-docx`, `openpyxl`, OpenCV, Tesseract OCR.
- **AI & Embeddings**: `sentence-transformers` (`BAAI/bge-small-en-v1.5`), scikit-learn, c-TF-IDF, Ollama / vLLM local daemon adapter.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons.
- **Containerization**: Multi-stage Dockerfiles and Docker Compose.

---

## 5. Quickstart & Local Execution

### Option A: Docker Compose (Recommended)
Launch the complete stack (PostgreSQL + pgvector, Backend, Frontend) with a single command:
```bash
docker compose up --build
```
- Frontend Web App: `http://localhost:5173`
- Backend REST API & Docs: `http://localhost:8000/docs`
- System Health Telemetry: `http://localhost:8000/api/v1/system/health`

### Option B: Local Workstation Execution

#### 1. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows (or source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 6. Default Demonstration Credentials

The database is pre-seeded with role-aware demonstration accounts:

| Username | Password | Role | Organization Context |
|---|---|---|---|
| `hq_officer` | `Admin123!` | `CMPDI_HQ_OFFICER` | CMPDI HQ (Full Multi-Subsidiary Access) |
| `ri1_officer` | `Password123!` | `RI_OFFICER` | Regional Institute - I (Asansol) |
| `ecl_analyst` | `Password123!` | `SUBSIDIARY_ANALYST` | Eastern Coalfields Limited (ECL) |
| `secl_analyst` | `Password123!` | `SUBSIDIARY_ANALYST` | South Eastern Coalfields Limited (SECL) |
| `verifier` | `Password123!` | `VERIFICATION_OFFICER` | Central Verification Cell |
| `admin` | `Admin123!` | `SYSTEM_ADMIN` | System Administrator |

---

## 7. Verification & Test Suite

The entire backend test suite spans 12 suites and 144 automated tests:
```bash
cd backend
pytest tests/ -v
```
**Latest Regression Suite Results**:
- `test_topic_hardening.py` (Phase 8.5 Hardening): **10 / 10 passed**
- `test_topic_temporal.py` (Phase 8.3 Temporal Analytics): **26 / 26 passed**
- `test_topic_engine.py` (Phase 8.2 Topic Engine): **11 / 11 passed**
- `test_topic_foundation.py` (Phase 8.1 Topic Foundation): **10 / 10 passed**
- `test_official_reports.py` (Phase 7 Statutory Reports): **14 / 14 passed**
- Core Document, OCR & Extraction: **41 / 41 passed**
- Retrieval, Q&A & Anti-Hallucination: **32 / 32 passed**
- **Total: 144 / 144 passed (100% green, 0 failures, 0 regressions)**.

---

## 8. Repository Structure

```
koyla/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # FastAPI REST versioned endpoints
│   │   ├── core/           # Config, security, JWT, RBAC
│   │   ├── db/             # Database connection & session management
│   │   ├── models/         # SQLAlchemy ORM schemas
│   │   ├── schemas/        # Pydantic request/response models
│   │   └── services/       # Domain business logic (ingestion, OCR, extraction,
│   │                       # retrieval, topics, reports, verification)
│   └── tests/              # 144 automated unit and integration tests
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI controls, drawers, modals
│   │   ├── context/        # Auth, Organization, and Theme providers
│   │   ├── pages/          # All 15+ production routes
│   │   └── services/       # Typed Axios API clients
│   └── package.json
├── demo_data/              # Synthetic demonstration dossiers (PDF, XLSX, DOCX)
├── docker/                 # Container Dockerfiles
├── docker-compose.yml      # Air-gapped single-command orchestration
├── ARCHITECTURE.md         # Full system architecture document
├── DATABASE_SCHEMA.md      # Relational entity-relationship specification
├── API_CONTRACT.md         # Comprehensive REST API contract
└── README.md               # Product overview and run guide
```
