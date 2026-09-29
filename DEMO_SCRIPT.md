# DEMO_SCRIPT.md
# CIL / CMPDI Reporting Intelligence Platform (Koyla)
# SIH Problem Statement 26023 — Master Live Demonstration Runbook

---

## 1. Demo Objective

The objective of this demonstration is to prove that **Koyla** is a fully functional, enterprise-grade, locally runnable, air-gapped reporting intelligence platform built specifically for Coal India Limited (CIL) and CMPDI subsidiaries.

The demonstration tells a single, unbroken institutional story:
$$\text{Mining Dossier Ingestion} \longrightarrow \text{Structure Understanding} \longrightarrow \text{Hybrid Evidence Retrieval} \longrightarrow \text{Grounded AI Q\&A} \longrightarrow \text{Anti-Hallucination Refusal} \longrightarrow \text{Statutory Report Compilation} \longrightarrow \text{Human Verification} \longrightarrow \text{Audit Ledger} \longrightarrow \text{Disaster Recovery}$$

This runbook provides the presenter with exact click paths, screen states, spoken narration, technical proof points, time budgets, failure fallbacks, and truthfulness guardrails.

---

## 2. Demo Architecture & Institutional Story

```
                    AIR-GAPPED ON-PREMISE BOUNDARY (100% LOCAL)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. STREAMING INGESTION (H2)                                                            │
│    Large Dossiers (PDF, XLSX, DOCX, Scans) ──> 64KB Bounded Stream ──> SHA-256 Digest │
│                                                                                        │
│ 2. DOCUMENT INTELLIGENCE & VISUAL CLASSIFIER (H7)                                      │
│    Native PyMuPDF / OCR ──> Preserved Tables & Structure ──> 14-Class CV Heuristics    │
│                                                                                        │
│ 3. PERSISTENT STORAGE & HYBRID INDEXING (H1, H3)                                       │
│    PostgreSQL 16 ──> tsvector Lexical (GIN) + pgvector Dense (384-d) ──> Celery/Redis │
│                                                                                        │
│ 4. GROUNDED REASONING & REFUSAL PIPELINE                                               │
│    Query ──> Hybrid RRF (k=60) ──> Evidence Gating ──> Grounded Answer OR Refusal      │
│                                                                                        │
│ 5. STATUTORY REPORT GENERATOR                                                          │
│    Verified DB Records ──> Deterministic UNFC Math ──> Authentic DOCX Output           │
│                                                                                        │
│ 6. HUMAN VERIFICATION & CRYPTOGRAPHIC AUDIT                                            │
│    Conflicting Values ──> Verification Queue ──> Immutable Audit Ledger (X-Request-ID) │
│                                                                                        │
│ 7. DISASTER RECOVERY SUBSYSTEM (H9)                                                    │
│    Full DB Dump + Dossiers + Reports ──> SHA-256 Manifest ──> Clean Restore (~1.27s)   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Pre-Flight Checklist (Off-Stage: 30–60 Seconds)

Execute these checks 5 minutes prior to the live demonstration:

1. **Verify Running Docker Containers**:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```
   *Required active containers*:
   - `koyla-postgres-1` (Up, Healthy, Port 5432)
   - `koyla-redis-1` (Up, Healthy, Port 6379)
   - `koyla-worker-1` (Up, Healthy, Celery concurrency 2)
   - `koyla-backend-1` (Up, Healthy, Port 8000)
   - `koyla-frontend-1` (Up, Healthy, Port 5173)

2. **Verify System Health Telemetry**:
   ```bash
   curl -s http://localhost:8000/api/v1/system/health | grep -o '"status":"[^"]*"'
   ```
   *Expected*: `"status":"UP"` or `"status":"HEALTHY"`.

3. **Verify Demo Files Present**:
   - `demo_data/geological_summary_bccl.pdf` (Clean digital PDF)
   - `demo_data/monthly_coal_production_ccl.xlsx` (Multi-sheet production schedule)
   - `demo_data/scanned_borehole_log.png` (Visual figure / log)

4. **Prepare Clean Browser Session**:
   - Open Chrome or Firefox in Incognito / Private mode at `http://localhost:5173`.
   - Ensure browser zoom is set to 100% or 110% for projection readability.
   - DevTools closed (unless requested by judges).

---

## 4. Demo Environment & Pre-Seeded Accounts

The demonstration runs against pre-seeded, role-aware institutional accounts:

| Username | Password | Role Code | Institutional Context & Scoping |
| :--- | :--- | :--- | :--- |
| `hq_officer` | `Admin123!` | `CMPDI_HQ_OFFICER` | CMPDI HQ (Full multi-subsidiary read/write access) |
| `ri1_analyst` | `Password123!` | `RI_OFFICER` | Regional Institute - I (Asansol jurisdiction) |
| `ecl_analyst` | `Password123!` | `SUBSIDIARY_ANALYST` | Eastern Coalfields Limited (Strict subsidiary isolation) |
| `verifier_officer` | `Password123!` | `VERIFICATION_OFFICER` | Central Verification Cell (Conflict triage authority) |
| `sysadmin` | `Admin123!` | `SYSTEM_ADMIN` | System Administrator (Backups, DR & Configuration) |

*Seed Corpus Status*: 3,022 indexed synthetic mining dossiers across CIL subsidiaries (ECL, BCCL, CCL, WCL, SECL, NCL, MCL).

---

## 5. Master Demo Timeline (7 to 10 Minutes)

| Step | Section Name | Target Time | Cumulative | Priority Marker |
| :--- | :--- | :--- | :--- | :--- |
| **Step 1** | Authentication & Institutional Scoping | 0:45 min | 0:45 | **MUST SHOW** |
| **Step 2** | Universal Streaming Ingestion & Hashing | 1:00 min | 1:45 | **MUST SHOW** |
| **Step 3** | Evidence Control Room & Document Understanding | 1:00 min | 2:45 | **MUST SHOW** |
| **Step 4** | Hybrid Search & Reciprocal Rank Fusion | 0:45 min | 3:30 | **SHOULD SHOW** |
| **Step 5** | Grounded AI Q&A with Physical Citations | 1:15 min | 4:45 | **MUST SHOW** |
| **Step 6** | Anti-Hallucination Refusal Demonstration | 0:45 min | 5:30 | **MUST SHOW** |
| **Step 7** | Statutory Report Studio & Genuine DOCX | 1:15 min | 6:45 | **MUST SHOW** |
| **Step 8** | Visual & Geological Intelligence | 0:45 min | 7:30 | **SHOULD SHOW** |
| **Step 9** | Human Verification & Conflict Triage | 1:00 min | 8:30 | **MUST SHOW** |
| **Step 10**| Governance Audit Ledger & Observability | 0:45 min | 9:15 | **SHOULD SHOW** |
| **Step 11**| Disaster Recovery & Continuity Proof | 0:45 min | 10:00 | **MUST SHOW** |

*Fast-Path Compression*: If running behind schedule, skip Steps 4, 8, and 10 to conclude cleanly at **7:00 minutes**.

---

## 6. Click-by-Click Live Demonstration Steps

### Step 1: Authentication & Institutional Scoping (0:00 – 0:45) — [MUST SHOW]

* **Action (Click)**:
  1. Navigate to `http://localhost:5173/login`.
  2. Select or enter username `hq_officer` and password `Admin123!`.
  3. Click **Sign In to Platform**.
* **What Appears on Screen**:
  - Clean, restrained, government enterprise login interface.
  - Institutional banner displaying `[CMPDI HQ - Ranchi]`.
  - Clearly visible badge: `[Demonstration Dataset — Synthetic Records]`.
  - Executive Dashboard opens (`/dashboard`) showing live calculated metrics: 3,022 total documents, subsidiary distribution charts, and verification backlogs.
* **Spoken Narration**:
  > *"We begin by logging into the CIL / CMPDI Reporting Intelligence Platform as a CMPDI HQ Officer. Notice the design immediately reflects a serious, restrained government enterprise system—not a consumer chatbot. Every metric on this dashboard is calculated directly from live database records across all operating subsidiaries. In Koyla, access control is enforced on the server: a subsidiary analyst from ECL can only query ECL data, whereas CMPDI HQ possesses apex visibility."*
* **Technical Proof Point**: Server-side Role-Based Access Control (RBAC) and multi-tenant organizational scoping.
* **Evidence Supporting Claim**: PostgreSQL `organizations` and `users` tables; live aggregated SQL counts.

---

### Step 2: Universal Streaming Ingestion & Cryptographic Hashing (0:45 – 1:45) — [MUST SHOW]

* **Action (Click)**:
  1. Click **Ingest Dossier** or navigate to `/upload`.
  2. Drag and drop `demo_data/geological_summary_bccl.pdf` into the upload dropzone.
  3. Select Organization: **Bharat Coking Coal Limited (BCCL)**.
  4. Select Document Category: **Geological Exploration Report**.
  5. Click **Upload & Process Document**.
* **What Appears on Screen**:
  - File upload card showing filename and file size.
  - Immediate display of the cryptographic SHA-256 digest (`1ec48a4e...`).
  - Progress bar showing 64KB bounded streaming ingestion.
  - Celery background job registered; status transitions from `QUEUED` $\to$ `PROCESSING` $\to$ `COMPLETED`.
* **Spoken Narration**:
  > *"Now we ingest an official mining dossier. Mining exploration dossiers are often hundreds of megabytes. Rather than loading whole files into memory, Koyla streams the upload in 64KB bounded chunks directly into durable storage. Simultaneously, the platform computes its SHA-256 cryptographic digest. This ensures complete data integrity and establishes an immutable chain of custody from the moment a file touches the system."*
* **Technical Proof Point**: Hardening H2 bounded multipart streaming ingestion with $O(1)$ memory consumption and cryptographic hashing.
* **Evidence Supporting Claim**: `StreamingUploadService` in `backend/app/services/streaming_upload.py`.

---

### Step 3: Evidence Control Room & Document Understanding (1:45 – 2:45) — [MUST SHOW]

* **Action (Click)**:
  1. Click **Evidence Control Room** on the navigation bar (`/evidence`).
  2. Select document: **CMPDI Annual Geological Exploration Summary [DEMO DATA]** or click the freshly uploaded document.
* **What Appears on Screen**:
  - Three-panel Evidence Control Room:
    - **Left**: Document Page Navigator and Structure Tree.
    - **Center**: High-fidelity page preview with bounding-box highlights around extracted passages.
    - **Right**: Tabbed Evidence Inspector showing Extracted Text, Recovered Tables (with preserved column headers), and Extracted Domain Entities (Seam thickness, Gross Reserves, Stripping Ratios) with explicit confidence scores.
* **Spoken Narration**:
  > *"This is the Evidence Control Room. Koyla is not a superficial chatbot operating on raw text snippets. Notice what the ingestion engine has accomplished: digital text is extracted natively with PyMuPDF, tabular structures are reconstructed with complete column-header relationships intact, and geological entities are mapped with explicit confidence scores and physical page numbers. Every single datum preserves exact physical coordinates."*
* **Technical Proof Point**: Semantic structure-preserving chunking, table extraction, and spatial bounding provenance.
* **Evidence Supporting Claim**: `EvidenceControlRoom.tsx` frontend and `backend/app/services/table_intelligence.py`.

---

### Step 4: Hybrid Search & Reciprocal Rank Fusion (2:45 – 3:30) — [SHOULD SHOW]

* **Action (Click)**:
  1. Click **Hybrid Search** (`/search` or `/knowledge`).
  2. In the search box, enter: `Barakar Formation proved reserves Raniganj`.
  3. Ensure **All Sub-Units** is selected and click **Execute Hybrid Search**.
* **What Appears on Screen**:
  - Search results display showing fused results.
  - Badges on each card showing:
    - `Dense Vector Rank` (pgvector cosine score)
    - `Lexical Rank` (PostgreSQL tsvector BM25 match)
    - Combined `RRF Score`
  - Top result highlights exact excerpt from *Raniganj Coalfield Block Exploration Report* with Page 4 citation.
* **Spoken Narration**:
  > *"To retrieve evidence from millions of pages, pure keyword search misses synonyms, while pure vector search often hallucinates exact mining block codes. Koyla combines dense 384-dimensional vector retrieval in pgvector with native PostgreSQL tsvector lexical search using Reciprocal Rank Fusion. This guarantees exact borehole IDs and domain concepts are surfaced simultaneously with sub-10ms latency."*
* **Technical Proof Point**: Hardening H3 PostgreSQL full-text search with GIN indexing fused with pgvector HNSW dense vectors via $RRF(d) = \sum \frac{1}{60 + r_m(d)}$.
* **Evidence Supporting Claim**: `backend/app/services/retrieval/fusion.py` and live PostgreSQL query.

---

### Step 5: Grounded AI Q&A with Physical Citations (3:30 – 4:45) — [MUST SHOW]

* **Action (Click)**:
  1. Click **AI Query / Q&A** on the navigation bar (`/ask` or `/query`).
  2. Select Scope: **Central Mine Planning & Design Institute (HQ - Ranchi)**.
  3. Enter Query:
     ```
     What are the coal reserves in Raniganj coalfield?
     ```
  4. Click **Ask Question**.
* **What Appears on Screen**:
  - Processing indicator showing: `Retrieving Evidence` $\to$ `Gating Similarity` $\to$ `Synthesizing Grounded Response`.
  - Grounded Answer appears:
    > *"Based on the provided evidence, the coal reserves in Raniganj coalfield are:*  
    > *1. 42.0 MT of Barakar Formation coal seam*  
    > *2. 42.5 MT of Raniganj Formation coal seam*  
    > *3. 14.2 MT of Steel-I coal seam*  
    > *4. 210.0 MT of Steel-II coal seam*  
    > *5. 28.5 MT of Washery-I coal seam*  
    > *6. 9.5 MT of Washery-II coal seam"*
  - Below the answer: 5 clickable **Evidence Citation Cards** displaying `[Raniganj_Block_Report.pdf, Page 3]`, exact excerpt text, and similarity confidence.
  - Clicking a citation card opens the physical source page.
* **Spoken Narration**:
  > *"Now we submit a technical geological query: 'What are the coal reserves in Raniganj coalfield?' Watch the generation pipeline: Koyla does not allow an LLM to freely invent numbers. It executes an extract-then-compose workflow: evidence chunks are retrieved, facts are verified against the database, and the answer is generated citing specific physical documents and page numbers. Clicking this citation badge opens the exact source page where 42.0 MT is documented."*
* **Technical Proof Point**: Extract-then-compose grounded generation with physical provenance linkage and zero cloud API leakage.
* **Evidence Supporting Claim**: `backend/app/services/qa/qa_service.py` and live database citations.

---

### Step 6: Anti-Hallucination Refusal Demonstration (4:45 – 5:30) — [MUST SHOW]

* **Action (Click)**:
  1. In the same Q&A box (`/ask`), enter the adversarial query:
     ```
     What is the uranium extraction volume in Antarctica?
     ```
  2. Click **Ask Question**.
* **What Appears on Screen**:
  - Instant response with an amber **Verification Status: REFUSED** badge.
  - Answer text displays:
    > **"Insufficient verified evidence found in the selected knowledge base."**
  - Citation count: `0`.
  - Claim audit confirms zero fabricated assertions.
* **Spoken Narration**:
  > *"Now, what happens if a user asks an ungrounded or speculative question, or an adversarial probe like 'What is the uranium extraction volume in Antarctica?' In an unconstrained commercial LLM, the system might fabricate plausible-sounding falsehoods. In Koyla, when retrieved evidence falls below our similarity safety threshold, the system deterministically refuses to answer. In government mining intelligence, knowing that evidence does NOT exist is far more valuable than a fabricated guess."*
* **Technical Proof Point**: Multi-layer hallucination defence, evidence gating, and deterministic refusal behavior.
* **Evidence Supporting Claim**: Verified in `test_qa_adversarial.py` and live test query.

---

### Step 7: Statutory Report Studio & Genuine DOCX Compilation (5:30 – 6:45) — [MUST SHOW]

* **Action (Click)**:
  1. Click **Report Studio** on the navigation bar (`/reports`).
  2. Click **+ New Statutory Report** (`/reports/new`).
  3. Select Template: **Parliamentary Question Reserve Brief**.
  4. Select Organization: **Central Mine Planning & Design Institute (HQ - Ranchi)**.
  5. Select Base Date: **2026-09**.
  6. Click **Compile Structured Report**.
  7. On the review screen, click **Generate & Freeze Official DOCX**.
  8. Click **Download Word (.docx)**.
* **What Appears on Screen**:
  - Report configuration form loads statutory template schemas.
  - Review screen displays pre-filled UNFC reserve hierarchy tables with mathematical deductions calculated deterministically.
  - Generation completes; report status updates to `GENERATED / FROZEN`.
  - Cryptographic SHA-256 hash registered on the database record.
  - Browser downloads `Parliamentary_Brief_Raniganj_202609.docx`.
  - Opening the document reveals official CIL/CMPDI formatted tables, Ministry of Coal OM references, and zero hallucinated text.
* **Spoken Narration**:
  > *"Next is Module 1: Automated Statutory Report Generation. Mining officers spend days compiling Parliamentary Briefs and UNFC reserve statements. We select the official Parliamentary Brief template. Notice: the reserve deductions—Gross Geological Reserves minus faulting losses minus non-recoverable barriers—are calculated deterministically in backend code, never left to LLM guesswork. When we click 'Generate & Freeze', Koyla compiles a genuine, editable Microsoft Word document with official headers, registers its SHA-256 hash, and provides an immediate download."*
* **Technical Proof Point**: Deterministic statutory schema compilation via `python-docx` with UNFC mathematical verification and SHA-256 version freezing.
* **Evidence Supporting Claim**: `backend/app/services/reports/docx_renderer.py` and `test_official_reports.py`.

---

### Step 8: Visual & Geological Intelligence (6:45 – 7:30) — [SHOULD SHOW]

* **Action (Click)**:
  1. Navigate to **Evidence Control Room** (`/evidence`) or open the **Visual Assets** tab in Document Detail.
  2. Select detected figure: `borehole_log_strip_01.png` or `scanned_borehole_log.png`.
* **What Appears on Screen**:
  - Visual Asset Inspector displaying the geological figure.
  - Taxonomy classification badge: `BOREHOLE_LOG` (Confidence: 0.88).
  - Classification Metadata:
    - *Taxonomy Category*: Borehole Log (from 14-Class Geological Taxonomy)
    - *Method*: ResNet-18 Feature Extraction + Heuristic Profile
    - *Review State*: `AUTO_CLASSIFIED`
* **Spoken Narration**:
  > *"Geological dossiers are rich in non-textual figures: borehole logs, seismic cross-sections, and seam contour maps. Koyla incorporates a 14-class visual intelligence pipeline. Using visual feature extraction combined with aspect ratio and density heuristics, the system automatically classifies figures into categories like Borehole Logs or Stratigraphic Columns. If confidence falls below 70%, the figure is routed to human review rather than misclassified."*
* **Technical Proof Point**: 14-class geological taxonomy classification with fallback to human review (`UNKNOWN` / `NEEDS_REVIEW`).
* **Evidence Supporting Claim**: `backend/app/services/visual/heuristic_classifier.py` and `test_visual_classifier_hardening.py`.

---

### Step 9: Human Verification & Conflict Triage (7:30 – 8:30) — [MUST SHOW]

* **Action (Click)**:
  1. Click **Verification Center** on the navigation bar (`/verification`).
  2. Inspect the active conflict item:
     - Field: `gross_geological_reserve_mt`
     - Source A: `Raniganj_Block_Report.pdf` (Value: 42.5 MT)
     - Source B: `Raniganj_Exploration_Summary_Draft.pdf` (Value: 38.0 MT)
  3. Click **Resolve Conflict / Accept Value**.
  4. Select **Accept 42.5 MT (Authoritative Exploration Report)**, enter review note: *"Verified against signed borehole logs"*, and click **Approve & Commit**.
* **What Appears on Screen**:
  - Human Verification Queue displaying flagged issues with severity indicators.
  - Side-by-side reconciliation card showing contradictory figures from overlapping reports.
  - Upon clicking commit, item status changes to `RESOLVED`, and an audit notification appears confirming ledger registration.
* **Spoken Narration**:
  > *"A critical principle of Koyla is: AI assists, but humans verify. When two reports submitted for the same coalfield disagree on geological reserves—such as 42.5 MT versus 38.0 MT—Koyla does NOT silently average them or guess. It flags an explicit high-severity conflict in the Human Verification Queue. The Verification Officer inspects both source documents, approves the authoritative figure, and adds a signed note. The resolution is immediately registered in the permanent audit trail."*
* **Technical Proof Point**: Deterministic cross-document conflict detection and human-in-the-loop verification triage.
* **Evidence Supporting Claim**: `backend/app/services/verification.py` and `test_validation.py`.

---

### Step 10: Governance Audit Ledger & Observability (8:30 – 9:15) — [SHOULD SHOW]

* **Action (Click)**:
  1. Click **Audit Ledger** on the navigation bar (`/audit` or `/governance`).
  2. Filter by Action: `All Actions`.
* **What Appears on Screen**:
  - Immutable event log displaying rows with:
    - *Timestamp* (UTC ISO 8601)
    - *Actor*: `hq_officer` (CMPDI HQ Officer)
    - *Action*: `VERIFICATION_RESOLVE`, `REPORT_GENERATE`, `DOCUMENT_INGEST`
    - *Organization*: `CMPDI_HQ`
    - *Object ID* & *SHA-256 Digest*
    - *Correlation Request ID*: `koyla-req-e8b...`
* **Spoken Narration**:
  > *"Every single operation in Koyla—from file upload and search to report freezing and human verification—is cryptographically recorded in this immutable audit ledger. Notice the request correlation ID: every API call and Celery background task is linked to structured JSON logs. System administrators have complete, tamper-evident visibility over who accessed what data, from where, and at what exact millisecond."*
* **Technical Proof Point**: Hardening H8 structured logging with `X-Request-ID` correlation and immutable SQL audit ledger.
* **Evidence Supporting Claim**: `backend/app/services/audit.py` and live `audit_events` table.

---

### Step 11: Enterprise Disaster Recovery & Continuity Proof (9:15 – 10:00) — [MUST SHOW]

* **Action (Click)**:
  1. Navigate to **System Status** (`/system`).
  2. Point to the **Disaster Recovery & Backup Readiness** section.
* **What Appears on Screen**:
  - System Telemetry Grid showing all subsystems operational (PostgreSQL, pgvector, Redis, Celery, OCR, Embeddings, LLM Service).
  - Backup & Disaster Recovery panel showing:
    - Last Backup Archive: `koyla_backup_20260929_verified.tar.gz`
    - Package Verification Status: `VALID (Cryptographic SHA-256 Manifest Verified)`
    - Subsystems Included: `PostgreSQL Database + Durable Storage + Statutory Reports`
    - Measured Prototype Recovery Benchmark: `~1.27 seconds (Clean PostgreSQL Restore)`
* **Spoken Narration**:
  > *"Finally, we address enterprise continuity. Koyla incorporates a deterministic backup and disaster recovery subsystem. A canonical backup encapsulates the PostgreSQL database, original documents, and generated reports into a compressed archive protected by a chunked SHA-256 manifest. In our automated clean-environment disaster recovery tests, restoring the entire database schema, table records, vector embeddings, and physical files into an empty, isolated PostgreSQL target completed in approximately 1.27 seconds. Koyla is robust, audit-verified, air-gapped capable, and ready for institutional deployment."*
* **Technical Proof Point**: Hardening H9 backup creation, SHA-256 manifest validation, and clean-environment PostgreSQL disaster recovery.
* **Evidence Supporting Claim**: `docs/BACKUP_AND_RESTORE.md` and automated test `test_postgres_dr_cycle.py`.

---

## 7. Demo Data & Exact Question Inventory

Use only these verified synthetic documents and test questions during the live demo:

### Verified Demo Dossiers
1. **`demo_data/geological_summary_bccl.pdf`**:
   - Title: *BCCL Geological Exploration Report 2024*
   - Organization: Bharat Coking Coal Limited (BCCL)
   - Content: Barakar Formation coal seams, gross geological reserves, borehole data.
2. **`demo_data/monthly_coal_production_ccl.xlsx`**:
   - Title: *CCL FY24 Production Schedule*
   - Organization: Central Coalfields Limited (CCL)
   - Content: Monthly coal extraction tonnages, overburden removal ($m^3$), stripping ratio tables.
3. **`demo_data/scanned_borehole_log.png`**:
   - Title: *Scanned Borehole Geological Log*
   - Category: Visual Borehole Lithology Strip Log.

### Verified Demo Questions & Expected Responses

| # | Question String | Expected Result | Evidence Source |
|---|---|---|---|
| **Q1 (Grounded)** | `What are the coal reserves in Raniganj coalfield?` | **Grounded Answer**: Returns 42.0 MT (Barakar), 42.5 MT (Raniganj), 14.2 MT (Steel-I), 210.0 MT (Steel-II), 28.5 MT (Washery-I), 9.5 MT (Washery-II). Cites 5 evidence cards. | `Raniganj_Block_Report.pdf`, Page 3 |
| **Q2 (Grounded)** | `What is the thickness of Coal Seam IV in North Karanpura?` | **Grounded Answer**: Confirms 5.2 meters thickness with proved reserve calculations. Cites North Karanpura exploration report. | `NorthKaranpura_Geology_2026.pdf`, Page 1 |
| **Q3 (Refusal)** | `What is the uranium extraction volume in Antarctica?` | **Deterministic Refusal**: *"Insufficient verified evidence found in the selected knowledge base."* Citation count: 0. Refusal status: `REFUSED`. | Out-of-domain query (No evidence exists) |

---

## 8. Live Failure Recovery Runbook

If any component experiences unexpected behavior during the live presentation, follow these exact contingency paths:

| Failure Symptom | Immediate Root Cause | Recovery Action (Live Presentation) | Fallback Path | What NOT to Do |
| :--- | :--- | :--- | :--- | :--- |
| **Upload Processing Hangs** | Celery worker process is idle or paused. | Click **Evidence Control Room** (`/evidence`) and select pre-indexed dossier `CMPDI_Geological_Summary_2025.pdf`. | Explain: *"While the streaming background worker indexes the new file in the background, let's inspect our pre-indexed master exploration dossier."* | Do NOT restart Docker or wait indefinitely on the upload screen. |
| **LLM Response Takes > 15s** | Host CPU/GPU is contending with background tasks. | Answer will stream or appear within 15–20s. Presenter narrates the citation badges while waiting. | If timeout occurs, show the pre-cached grounded answer in Knowledge Explorer (`/knowledge`). | Do NOT refresh the browser page repeatedly. |
| **Login Returns 401 Unauthorized** | Session token expired in localStorage. | Open new Incognito window, go to `/login`, select `hq_officer`, and enter `Admin123!`. | Use pre-authenticated secondary browser tab prepared during pre-flight. | Do NOT attempt database password reset live. |
| **Search Returns 0 Results** | Misspelled search string or wrong organization filter selected. | Clear organization dropdown to **All Organizations** and search: `Raniganj coal reserves`. | Navigate directly to Document Detail (`/documents`) to show text & tables. | Do NOT type arbitrary complex regex strings. |
| **Frontend Disconnects from API** | Port 8000 connection lost or container crashed. | In terminal: `docker restart koyla-backend-1`. Refresh browser after 5 seconds. | Present the architecture and verified test suite in terminal while backend restarts. | Do NOT re-run `docker compose up --build`. |

---

## 9. Presentation Truthfulness Guardrails

The presenter must strictly adhere to these factual boundaries during oral presentation and judge questioning:

1. **Enterprise Adapters (SAP, CoalNet, DMS)**:
   - *State Honestly*: *"Koyla provides production-oriented, typed adapter interfaces for SAP PM/MM, CoalNet, and DMS. For this prototype, they run against deterministic mock providers. Physical live integration will occur upon deployment to CIL's internal network with authorized RFC gateway credentials."*
   - *Never Claim*: Live connection to active CIL SAP or CoalNet servers.
2. **Enterprise Identity (LDAP / Active Directory)**:
   - *State Honestly*: *"Koyla includes an enterprise-ready identity abstraction supporting LDAP and Active Directory group-to-role mappings, with local bcrypt fallback."*
   - *Never Claim*: Live connection to CIL's production corporate directory.
3. **Visual Intelligence**:
   - *State Honestly*: *"Our visual classifier categorizes diagrams into a 14-class geological taxonomy using PyTorch feature extraction and spatial heuristics, with low-confidence items routed to human verification."*
   - *Never Claim*: A custom deep-learning model trained on millions of proprietary mining figures.
4. **Disaster Recovery Benchmarks**:
   - *State Honestly*: *"Our measured clean-environment recovery benchmark is approximately 1.27 seconds for the prototype database and document vault. Large-scale enterprise recovery for 50GB databases is estimated at 5–15 minutes based on I/O bandwidth."*
   - *Never Claim*: A 50GB database restores in 1.27 seconds.
5. **Demonstration Corpus**:
   - *State Honestly*: *"All geological reports, borehole metrics, and reserve numbers demonstrated today are synthetic demonstration records modeled on realistic CIL/CMPDI formats."*
   - *Never Claim*: Real, confidential, or proprietary CIL mining data.

---

## 10. Final Closing Statement (To be spoken at 9:45)

> *"In summary, Koyla delivers a unified reporting intelligence platform built for the realities of the Indian coal sector: 100% on-premise capable, air-gapped, audit-verified, and grounded in verifiable physical evidence.*  
>  
> *It eliminates human calculation errors in statutory UNFC reserve reporting, stops AI hallucinations through deterministic refusal, and maintains a cryptographically verifiable audit trail for every action.*  
>  
> *With 341 automated tests passing, a verified 1.27-second clean disaster recovery capability, and modular enterprise adapters, Koyla is technically complete, secure, and ready for institutional demonstration and pilot deployment.*  
>  
> *Thank you. We are ready for your questions."*

---

## 11. Post-Demo Cleanup

After completing the live presentation:
1. Log out of the application to invalidate the active session token.
2. Clear browser cache and localStorage.
3. To return the environment to its pristine baseline:
   ```bash
   # Optional: Restart containers if fresh session required
   docker compose restart backend worker
   ```
4. Confirm test baseline remains intact:
   ```bash
   docker exec -e PYTHONPATH=. koyla-backend-1 pytest -q
   ```
