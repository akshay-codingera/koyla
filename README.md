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

## 3. Implemented Modules & Enterprise Hardening (Phases 1 through H10)

| Module / Hardening Layer | Route / Subsystem | Capabilities & Features |
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
| **Persistent Workers (H1)** | Celery / Redis | Background document processing, OCR, chunking, and topic training with task persistence and retry policies. |
| **Streaming Ingestion (H2)** | `/api/v1/documents/upload` | Chunked 64KB multi-part streaming ingestion for large mining dossiers with memory bounding. |
| **Lexical Search (H3)** | PostgreSQL tsvector/GIN | Server-side full-text search with ranking, stemming, and Boolean querying integrated into hybrid search. |
| **Security Hardening (H4)** | App Middleware | ClamAV antivirus integration, HTTP security headers (CSP, HSTS, X-Frame-Options), and production secret enforcement. |
| **Enterprise Identity (H5)** | `/api/v1/auth/ldap` | Abstract identity provider interface with pluggable LDAP/Active Directory adapter and local fallback. |
| **Enterprise Adapters (H6)** | `/api/v1/adapters` | Modular adapters for SAP PM/MM, CoalNet production, and DMS with deterministic mock fallbacks. |
| **Visual Classifier (H7)** | Feature Extractor | Computer-vision assisted geological diagram, map, and stratigraphic column classification. |
| **Observability (H8)** | Structured Logging | JSON logging, `X-Request-ID` correlation, millisecond stage timing, and Prometheus `/metrics` endpoint. |
| **Backup & Disaster Recovery (H9)** | `/api/v1/admin/backup` | Local/on-premise database and document backups with SHA-256 manifests, retention pruning, and clean-environment restoration. |
| **Release Readiness & E2E (H10)** | Multi-Stage CI/CD | Full-lifecycle E2E testing validating all 5 operational flows across isolated clean PostgreSQL instances. |

---

## 4. Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy ORM, Pydantic v2, Uvicorn, Celery, Redis.
- **Database & Search**: PostgreSQL 16 with `pgvector` 0.8.6 extension; tsvector / GIN lexical search; hybrid RRF retrieval.
- **Document Processing**: PyMuPDF (`fitz`), `python-docx`, `openpyxl`, OpenCV, Tesseract OCR.
- **AI & Embeddings**: `sentence-transformers` (`BAAI/bge-small-en-v1.5`), scikit-learn, c-TF-IDF, Ollama / vLLM local daemon adapter.
- **Security & Identity**: Passlib (bcrypt), PyJWT, python-ldap, ClamAV daemon connector, secure HTTP headers.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons.
- **Containerization & Orchestration**: Docker, Docker Compose, Multi-stage production builds.

---

## 5. Quickstart & Local Execution

### Option A: Docker Compose (Recommended)
Launch the complete stack (PostgreSQL + pgvector, Redis, Celery Worker, Backend API, Frontend Web) with a single command:
```bash
docker compose up --build
```
- Frontend Web App: `http://localhost:5173`
- Backend REST API & Docs: `http://localhost:8000/docs`
- Prometheus Metrics: `http://localhost:8000/metrics`
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

The entire backend test suite spans 28 test suites and 341 automated tests:
```bash
docker exec -e PYTHONPATH=. koyla-backend-1 pytest -q
```
**Latest Enterprise Test Matrix Results**:
- **Baseline Foundation & Domain Extraction**: **205 passed**
- **Hardening H1–H7 (Workers, Streaming, Lexical, Security, LDAP, Adapters, Visual)**: **80 passed**
- **Hardening H8 (Observability & Stage Timing)**: **36 passed**
- **Hardening H9 (Backup, Cryptographic Integrity & Clean PostgreSQL DR)**: **19 passed**
- **Hardening H10 (Unified Full-Lifecycle Enterprise E2E)**: **1 passed**
- **Overall Total: 341 / 341 passed (100% green, 0 failures, 0 errors, 0 regressions)**.

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
