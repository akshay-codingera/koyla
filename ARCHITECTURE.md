# ARCHITECTURE.md
# CIL / CMPDI AI Reporting & Intelligence Platform
# System Architecture Specification

## 1. Architectural Philosophy & Deployment Topology
The platform is an air-gapped, on-premise capable government enterprise intelligence application designed for Coal India Limited (CIL) and CMPDI.

```
                    AIR-GAPPED ON-PREMISE BOUNDARY
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   Web Browser (Client)                                                 │
│   └── React 19 + TypeScript + Vite + Tailwind CSS                      │
│       ├── Organization-Scoped Context & RBAC Views                     │
│       ├── Document Inspection & Evidence Viewers                       │
│       └── Report Studio & Triage Verification Queue                    │
│                            │                                           │
│                            ▼ HTTPS / REST (JSON)                       │
│   FastAPI Core Gateway (:8000)                                         │
│   ├── Authentication & Middleware (JWT, Org Scoping, Audit Logger)    │
│   ├── Document Management & Storage Engine                             │
│   ├── Hybrid Retrieval & Grounded Q&A Orchestrator                     │
│   ├── Template-Driven Report Generator (python-docx)                   │
│   ├── Deterministic Domain Validation Engine                           │
│   └── Multi-Node Federation Gateway (Simulated)                        │
│            │                       │                      │            │
│            ▼                       ▼                      ▼            │
│   Local Intelligence Engine    Data Layer         Local File System    │
│   ├── Local Embedding Service  ├── PostgreSQL 16  ├── /storage/docs    │
│   │   (sentence-transformers)  │   + pgvector     ├── /storage/docx    │
│   ├── Local OCR Pipeline       │   (or SQLite     └── /storage/ocr     │
│   │   (OpenCV + PaddleOCR/     │   local fallback)                     │
│   │    Tesseract)              └── FTS5 / BM25                         │
│   └── Local LLM Service                                                │
│       (Ollama / vLLM /                                                 │
│        Deterministic Rules)                                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion & Document Intelligence Architecture

### 2.1 File Ingestion
- Supported Formats: `.pdf` (digital & scanned), `.docx`, `.xlsx`, `.xls`, `.png`, `.jpg`, `.txt`, `.csv`.
- Cryptographic Hashing: Every uploaded file is digested via SHA-256 immediately upon streaming into buffer. The hash is compared against the database to identify exact duplicates or register incremental versions (`supersedes_doc_id`).

### 2.2 Routing & Parsing Pipeline
- **Digital PDF:** Evaluated first via PyMuPDF (`fitz`). If text density and character distribution meet extraction thresholds ($> 50$ printable characters per page), text and bounding blocks are extracted directly without OCR overhead.
- **Scanned PDF / Images:** Pages are rendered to raster images and routed through OpenCV preprocessing:
  1. Grayscale conversion & Gaussian denoising.
  2. Binarization (Otsu adaptive thresholding).
  3. Deskew calculation via minimum area bounding rectangle.
  4. OCR via PaddleOCR / Tesseract with confidence scores per word/line.
- **Spreadsheets (`.xlsx`, `.xls`):** Processed via `openpyxl`. Sheet names, column headers, cell formulas, and row groupings are indexed with explicit cell coordinate provenance (`Sheet1!B4`).
- **Word Documents (`.docx`):** Parsed with `python-docx`. Preserves heading hierarchy (H1, H2, H3), table grids, and bullet hierarchies.

### 2.3 Structure-Preserving Chunking
Unlike naive token-window chunkers that slice tabular data arbitrarily, this system implements semantic structure chunking:
- Tables are kept whole as discrete chunk units with serialized markdown formatting and explicit column header references.
- Headings demarcate section boundaries.
- Borehole logs and stratum layers are bundled as unified geological records.

---

## 3. Storage & Search Architecture

### 3.1 Dual-Database Strategy
- **Production Target:** PostgreSQL 16 with the `pgvector` extension enabled for HNSW / IVFFlat vector indexing. Full-text search handled via PostgreSQL `tsvector` / GIN indexing.
- **Local Workstation Fallback:** To allow immediate local execution without requiring Docker or a running PostgreSQL daemon, the application provides an in-process SQLAlchemy fallback utilizing SQLite + NumPy vector cosine similarity + SQLite FTS5.
- Both configurations share identical SQLAlchemy ORM models and Pydantic schemas.

### 3.2 Hybrid Search with Reciprocal Rank Fusion (RRF)
Search queries undergo:
1. **Metadata Pre-Filtering:** Filter by `organization_id`, `subsidiary_code`, `ri_code`, `fiscal_year`, `document_type`, `trust_tier`.
2. **Dense Semantic Retrieval:** Query embedding generated via local `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dims, or `bge-small-en-v1.5`), queried against vector store.
3. **Lexical Retrieval:** Exact BM25 / FTS keyword search matching mining codes, seam identifiers, and borehole designations.
4. **Rank Fusion:** Candidates combined via standard Reciprocal Rank Fusion:
   $$RRF(d) = \sum_{m \in \{dense, lexical\}} \frac{1}{60 + r_m(d)}$$
5. **Cross-Encoder Reranking:** Top 20 candidates scored for final evidence selection.

---

## 4. Grounded AI Q&A & Anti-Hallucination Pipeline
To prevent hallucinations and guarantee auditability:
1. **Extract-Then-Compose Pattern:**
   - **Step 1 (Evidence Extraction):** Only retrieved chunks with high similarity ($score > 0.60$) are selected.
   - **Step 2 (Verbatim Fact Selection):** Key factual spans (tonnages, stripping ratios, seam names, dates) are isolated from the evidence text.
   - **Step 3 (Constrained Generation):** The composition model is prompted with a strict system constraint: *Answer solely using the provided evidence facts. For every claim, append the citation tag `[Doc <ID>, Page <P>]`.*
2. **Refusal Mechanism:** If no retrieved chunk exceeds the confidence threshold, the pipeline automatically aborts generation and returns:
   *"Insufficient verified evidence found in the indexed sources for the selected organization scope."*
3. **Traceability:** Every answer object references specific `answer_citations` linked to `chunk_id`, `document_id`, and `page_number`.

---

## 5. Report Generation Architecture
The Report Studio avoids unconstrained LLM writing. Reports are structured compilations:
1. **Template Definition:** Registered schemas defining required fields (e.g. `total_production_mt`, `overburden_stripped_m3`, `stripping_ratio`, `seam_classification`, `safety_incidents`).
2. **Data Aggregation & Validation:** Values are pulled from verified `extracted_fields` in the database. Validation rules check for numeric sanity and period consistency.
3. **Review & Approval Gate:** Generated reports enter `draft` status; a Verification Officer or HQ Officer must review and approve before finalization.
4. **Deterministic Rendering:** The approved dataset is injected into a pre-formatted `.docx` template via `python-docx`, with standardized CIL/CMPDI typography, tables, and signature blocks. A frozen JSON snapshot and SHA-256 hash are recorded.

---

## 6. Simulated Multi-Node Federation
To demonstrate cross-subsidiary governance without violating data boundaries:
- 3 logical nodes: `node-cmpdi` (HQ & Geological master data), `node-secl` (Bilaspur/Chhattisgarh operational data), `node-ecl` (Asansol/West Bengal operational data).
---

## 7. Prototype vs Production Implementation Mapping

In compliance with the SIH requirement for verifiable local enterprise execution vs. future scale-out, all major components are categorized as follows:

| Component | Status Category | Detail |
|---|---|---|
| **Document Ingestion & File Parsing** | IMPLEMENTED IN PROTOTYPE | Full native parsing (PyMuPDF, openpyxl, python-docx). |
| **Local OCR (PaddleOCR/Tesseract)** | IMPLEMENTED IN PROTOTYPE | Executed locally via OpenCV preprocessing without external APIs. |
| **Hybrid Search (pgvector + BM25)** | IMPLEMENTED IN PROTOTYPE | Local sentence-transformers and SQL-based dense/lexical ranking. |
| **Grounded AI Q&A & Refusal** | IMPLEMENTED IN PROTOTYPE | Local LLM adapter (Ollama/vLLM) performing extract-then-compose. |
| **Report DOCX Generation** | IMPLEMENTED IN PROTOTYPE | Native editable DOCX output generated via python-docx. |
| **Topic Intelligence & Word Cloud**| IMPLEMENTED IN PROTOTYPE | Local c-TF-IDF, clustering, grounded evidence, and Word Cloud. |
| **Temporal & Comparative Analytics**| IMPLEMENTED IN PROTOTYPE | Period shifts ($\Delta_{abs}$, $\Delta_{pp}$, $g_{rel}$), multi-dimensional comparisons, and sample gate. |
| **System Health Probes** | IMPLEMENTED IN PROTOTYPE | Genuine live capability verification across all 9 subsystems. |
| **RBAC & Governance Audit** | IMPLEMENTED IN PROTOTYPE | Immutable SQL ledger and server-side organization scope enforcement. |
| **Federated Sub-Nodes** | PROTOTYPE SIMULATION | 3 logical nodes simulated within the same prototype infrastructure to demonstrate gateway aggregation. |
| **Active Directory / LDAP** | FUTURE PRODUCTION INTEGRATION | Prototype uses local JWT auth; LDAPS module is stubbed for future enterprise bind. |
| **External SIEM Integration** | FUTURE PRODUCTION INTEGRATION | Audit logs are stored in PostgreSQL; future push to enterprise Splunk/SIEM. |
| **Live Sensor/IoT Ingestion** | ROADMAP / NOT YET IMPLEMENTED | Out of scope for current document-focused intelligence module. |

---

## 8. Topic Intelligence & Temporal Analytics Architecture

KOYLA's Topic Intelligence module delivers automated theme discovery, vocabulary weighting, temporal trend tracking, and multi-dimensional comparisons over unstructured mining dossiers:

### 8.1 Single Global Topic Model Alignment
- To prevent topic drift across multi-year analyses, exactly one global topic model is trained over the complete scoped corpus.
- Chunks are vectorized using local `BAAI/bge-small-en-v1.5` embeddings (384 dimensions) and clustered.
- Term representations are calculated via class-based TF-IDF (c-TF-IDF):
  $$W_{t, c} = \text{tf}_{t, c} \times \log\left(1 + \frac{A}{f_t}\right)$$
  where $\text{tf}_{t, c}$ is the frequency of term $t$ in class $c$, $f_t$ is total term frequency, and $A$ is the average number of words per class.

### 8.2 Disaggregated Temporal Formulation & Minimum-Evidence Gate
- **Metrics Disaggregation**: All period shifts strictly distinguish absolute document change ($\Delta_{\text{abs}}$), percentage-point change ($\Delta_{\text{pp}}$), and relative growth ($g_{\text{rel}}$), with explicit denominator reporting $(d / D)$.
- **Minimum-Evidence Gate**: Small sample sizes (e.g. $< 5$ period documents or $< 2$ topic documents) are assigned `INSUFFICIENT_HISTORY` to prevent erratic percentage shifts on thin evidence.
- **Trend Taxonomy**: Strict classifications (`GROWING`, `DECLINING`, `STABLE`, `EMERGING`, `DISAPPEARING`, `RECURRING`) driven purely by empirical metrics with zero speculative causal claims.

### 8.3 Cross-Module Evidence Integration
- **Physical Evidence Navigation**: Topic evidence cards deep-link directly into native document viewing (`/documents/:id?page=P&chunk=C`), auto-navigating to the physical source page.
- **Statutory Report Attachment**: Operators can attach complete topic analysis briefs into target statutory reports in Report Studio as optional analytical annexures (`requirement_type="OPTIONAL"`), leaving statutory chapter numbering intact.

---

## 9. Genuine System Health Architecture

Health telemetry at `/api/v1/system/health` performs genuine operational checks across all 9 core subsystems:
1. **Backend / API**: Verifies FastAPI request-response loop and version telemetry.
2. **Database (PostgreSQL)**: Executes live `SELECT 1` query to verify active connection pool.
3. **Vector Store (pgvector)**: Executes genuine vector distance query (`SELECT '[1,2,3]'::vector <-> '[1,2,3]'::vector`) to verify extension installation and vector indexing.
4. **OCR Engine**: Verifies local Tesseract and PyMuPDF binaries without cloud dependencies.
5. **Embedding Service**: Verifies local `BAAI/bge-small-en-v1.5` weights and sentence-transformers inference capability.
6. **LLM Service**: Probes local Ollama / vLLM daemon port (11434); reports `OFFLINE` when daemon is unstarted (no fake green statuses).
7. **Topic Engine**: Validates clustering and c-TF-IDF mathematical runtime.
8. **Temporal Analytics**: Validates trend calculation and cache lookup engine.
9. **Report Engine**: Validates `python-docx` rendering pipeline and template store.

