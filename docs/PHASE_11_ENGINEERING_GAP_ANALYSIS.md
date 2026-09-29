# Koyla — Phase 11 Engineering Gap Analysis & Product Completion Roadmap
# Technical Assessment of Implemented Systems, Production Readiness & Engineering Gaps
# Baseline: Commit 7fb0a425cf658985fe9b637808a5659dd113b2e8 | 341 Tests Passed

---

## 1. Executive Summary & Assessment Methodology

This document establishes the real engineering gap analysis for the **Koyla** platform under Phase 11. It moves beyond presentation and demonstration planning to examine the **actual codebase, database schemas, services, parsers, APIs, worker pipelines, and frontend interfaces**.

Every subsystem was evaluated against a strict standard:
> *"What is still missing, weak, incomplete, simulated, or insufficiently production-ready in Koyla itself to fulfill SIH Problem Statement 26023?"*

All findings are grounded in verified source code and categorized across 16 primary functional areas, prioritized into **P0 (Must Fix)**, **P1 (Important)**, **P2 (Enhancement)**, and **FUTURE (Enterprise Scale / Research)**.

---

## 2. Comprehensive Subsystem Gap Assessment (Areas 1 through 16)

### Area 1: Document Ingestion & Parsing

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Multi-Format Ingestion** | PDF, DOCX, XLSX, XLS, CSV, TXT, PNG/JPG supported. | `backend/app/services/parsers/` | Multi-page TIFF files (widely used in legacy CMPDI mine survey scans) are unsupported. | **MEDIUM** | Add TIFF/TIF parser using PIL/PyMuPDF to convert multi-frame TIFFs into page arrays. |
| **Bilingual OCR** | Tesseract OCR active with OpenCV preprocessing. | `backend/app/services/parsers/ocr_parser.py` | Hardcoded to English (`lang="eng"`). Many CIL circulars, mine plans, and gazettes have Hindi / Devanagari text. | **HIGH** | Support bilingual `lang="eng+hin"` with graceful fallback to `eng` if Devanagari language pack is missing. |
| **Batch Archive Ingestion** | Single file upload per request or multi-file selection. | `backend/app/services/streaming_upload.py` | Uploading a `.zip` or `.tar.gz` dossier archive fails validation (`UNSUPPORTED_FORMAT`). | **MEDIUM** | Implement safe in-memory archive unpacker extracting valid dossiers with quarantine checks. |
| **Duplicate & Versioning** | SHA-256 computed on stream; duplicates linked via `supersedes_id`. | `backend/app/services/ingestion.py` | No automated semantic deduplication (detecting nearly identical documents with different file headers). | **LOW** | Future cosine-similarity hash gate on document embeddings. |

---

### Area 2: Geological & Mining Intelligence

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Domain Entity Model** | Extracted fields capture seam, reserves, thickness, stripping ratio, overburden. | `backend/app/services/extraction/rule_based.py` | No normalized relational `lithological_strata` table. Borehole strata layers are stored as unstructured text chunks. | **HIGH** | Create a structured `BoreholeStratum` model (`borehole_id`, `depth_from`, `depth_to`, `lithology`, `thickness`, `seam_code`). |
| **Mine Block & Lease Spatial Context** | Mine and block names are stored as freeform strings. | `backend/app/models/report.py` | Lack of a dedicated `MineBlock` master entity linking coordinates, lease area (Ha), and subsidiary hierarchy. | **MEDIUM** | Introduce a normalized `mine_blocks` relational table to anchor extracted reports to physical blocks. |
| **UNFC Reserve Balance** | UNFC reserve categories modeled in statutory report schema. | `backend/app/services/reports/mining_plan_2025_schema.json` | Cross-document validation checks individual fields but lacks full multi-year UNFC balance sheet validation (Opening + Additions - Depletion = Closing). | **HIGH** | Implement automated UNFC reserve reconciliation engine computing depletion balances across fiscal years. |

---

### Area 3: AI & Hybrid RAG

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Context Window Bounding** | Top $k=5$ evidence chunks retrieved and compiled into LLM prompt. | `backend/app/services/qa/qa_service.py` (`MAX_EVIDENCE_CHUNKS=5`) | Queries requiring multi-document aggregation (e.g. "Total coal production across all 12 months") truncate evidence. | **CRITICAL** | Implement structured SQL aggregation path in `StructuredLookupService` to compute multi-document sums directly. |
| **Tabular Q&A Execution** | Tables serialized as Markdown inside text chunks. | `backend/app/services/retrieval/dense_search.py` | Complex tabular queries (e.g. "Which seam had ash content < 18% in Block B?") rely on text matching rather than structured cell queries. | **HIGH** | Introduce structured table-cell filtering querying `table_rows` directly when query matches column entities. |
| **Cross-Subsidiary Comparison** | Single-subsidiary Q&A works; comparative queries supported via topic engine. | `backend/app/services/topics/temporal_service.py` | Natural language comparison query (e.g. "Compare ECL vs BCCL stripping ratios in FY24") occasionally merges unrelated evidence chunks. | **MEDIUM** | Enhance `QueryNormalizer` to detect multi-subsidiary comparison intents and execute isolated dual-tenant retrieval. |

---

### Area 4: Multimodal & Visual Intelligence

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Visual Classification** | 14-class heuristic classifier inspecting captions, figure IDs, and OCR text. | `backend/app/services/visual/heuristic_classifier.py` | `DomainCVClassifier` is an unconfigured extension point. No actual image-pixel feature extraction runs on the image bytes. | **MEDIUM** | Equip heuristic classifier with basic PIL/OpenCV image aspect-ratio and vertical line-density profiling for borehole strips. |
| **Visual Provenance UI** | Cropped image previews display in Document Detail and Evidence Control Room. | `frontend/src/pages/EvidenceControlRoom.tsx` | No interactive bounding-box overlay directly on the full PDF page canvas in the browser viewer. | **LOW** | Render SVG / Canvas bounding-box overlays over PDF.js pages in the document inspector. |
| **Diagram Metric Extraction** | Visual figures classified and indexed. | `backend/app/services/parsers/visual_detector.py` | Text inside complex geological sections/maps is extracted via OCR but not geometrically linked to diagram axes. | **FUTURE** | Specialized coordinate digitization for geological cross-sections. |

---

### Area 5: Table & Spreadsheet Intelligence

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hierarchical Spreadsheets** | `SpreadsheetParser` streams rows, chunking sheets > 2000 rows. | `backend/app/services/parsers/spreadsheet_parser.py` | Complex multi-row merged headers (common in CIL production bulletins) lose parent category grouping. | **HIGH** | Implement multi-level header propagation forward-filling merged header coordinates across child columns. |
| **Spreadsheet Cell Formulas** | Loaded with `data_only=True` via openpyxl. | `backend/app/services/parsers/spreadsheet_parser.py` | If an Excel file was saved without cached formula calculations, cell values evaluate to `None`. | **MEDIUM** | Implement fallback formula detection alerting users that cached calculations are missing in uploaded file. |
| **Tabular Temporal Queries** | Monthly sheets are parsed as separate `ParsedPage` entries. | `backend/app/services/parsers/spreadsheet_parser.py` | Cross-sheet quarter aggregation (e.g. Q1 production = April + May + June) requires manual chunk synthesis. | **HIGH** | Bond sheet-level temporal metadata to extracted tabular records to allow programmatic multi-sheet aggregation. |

---

### Area 6: Statutory Report Studio

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Template Compilers** | Official 2025 Mining Plan schema, Parliamentary Brief, Production Summary. | `backend/app/services/reports/format_registry.py` | Generated reports compile to `.docx`, but in-browser PDF generation depends on external headless converters. | **MEDIUM** | Add headless PDF compilation service or browser-side print-to-PDF styles for generated reports. |
| **In-Browser Schema Grid Editor** | Form fields can be corrected prior to freezing report. | `frontend/src/pages/ReportStudio.tsx` | Statutory tables cannot be edited in a full interactive spreadsheet grid inside the browser prior to freezing. | **LOW** | Integrate lightweight interactive editable data grid for table chapters in `ReportStudio`. |
| **Report Verification Sign-Off** | Officer signs report; hash registered in database. | `backend/app/services/reports/review_service.py` | Lacks Qualified Person (QP) certificate number validation and registration field. | **LOW** | Add statutory QP registration ID and expiry date fields to `Report` metadata. |

---

### Area 7: Human Verification & Governance

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Conflict Triage Queue** | Single-reviewer `APPROVE`, `CORRECT`, `REJECT`, `DEFER` actions. | `backend/app/services/verification.py` | Lacks 4-eyes / two-tier approval workflow for high-severity statutory reserve modifications. | **HIGH** | Implement two-tier verification: Junior Analyst review $\to$ Senior Mining Officer co-signature for reserve changes. |
| **Bulk Verification Actions** | Each conflict/triage card must be opened and resolved individually. | `frontend/src/pages/VerificationQueue.tsx` | No bulk approval for low-severity, identical OCR warnings across batch-ingested files. | **MEDIUM** | Add batch selection and bulk-approval action for `LOW` severity triage items. |
| **Keyboard Accessibility** | Full mouse/click-driven triage UI. | `frontend/src/pages/VerificationQueue.tsx` | No keyboard shortcuts for high-throughput verification triage (e.g. `[A]` Approve, `[R]` Reject, `[C]` Correct). | **LOW** | Add hotkey listener in `VerificationQueue.tsx`. |

---

### Area 8: Enterprise Integration Adapters

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SAP Integration Protocol** | REST / OData HTTP adapter with deterministic mock fallback. | `backend/app/services/adapters/sap_adapter.py` | Legacy CIL SAP instances often require SAP RFC / PyRFC NetWeaver SDK rather than modern OData REST endpoints. | **FUTURE** | Author RFC connector abstraction requiring proprietary SAP NetWeaver SDK binaries when physically on-premise. |
| **Automated Background Sync** | Adapters query external systems synchronously on request. | `backend/app/services/adapters/manager.py` | No recurring Celery beat task that periodically synchronizes new dossiers from external DMS or CoalNet endpoints. | **HIGH** | Implement periodic Celery task (`sync_external_adapters_task`) pulling new external records into staging. |
| **Active Directory Integration** | `python-ldap` abstraction with StartTLS and group-to-role mapping. | `backend/app/services/identity/ldap_provider.py` | Active Directory Kerberos / SPNEGO single-sign-on (SSO) is not implemented; uses direct LDAP bind. | **MEDIUM** | Support SPNEGO / Kerberos SSO token authentication header in addition to direct username/password bind. |

---

### Area 9: Security & Tenancy

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Distributed Rate Limiting** | In-process rate limiting via SlowAPI / memory dictionary. | `backend/app/core/config.py` | In a multi-worker production deployment, in-memory rate limits are isolated per process, not shared via Redis. | **MEDIUM** | Configure Redis-backed storage for SlowAPI rate limiter (`storage_uri=settings.REDIS_URL`). |
| **Local Password Complexity** | Bcrypt hashing active; checks minimum length (8 chars). | `backend/app/api/v1/auth.py` | No enforcement of uppercase, lowercase, numbers, and special characters on local user password reset. | **LOW** | Add password complexity regex validator in Pydantic user registration/update schemas. |
| **Session Invalidation** | JWT expiration enforced (480 mins). | `backend/app/core/security.py` | No JWT revocation blacklist in Redis; logging out only clears client-side localStorage. | **MEDIUM** | Implement token blacklist in Redis with TTL matching remaining token lifespan upon logout. |

---

### Area 10: Reliability & Fault Tolerance

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stalled Ingestion Job Recovery** | Celery tasks retry on worker crash via `acks_late=True`. | `backend/app/tasks/ingestion_tasks.py` | If a task is killed by OS OOM killer, the document status in PostgreSQL can remain in `PROCESSING` indefinitely. | **CRITICAL** | Implement an automated background "Stuck Job Reaper" task that detects and resets jobs stuck in `PROCESSING` > 30 mins. |
| **Database Connection Recovery** | SQLAlchemy engine with pool pre-ping active. | `backend/app/db/database.py` | Transient database network drops during Celery batch jobs do not cleanly auto-reconnect without retrying the task. | **MEDIUM** | Configure `pool_recycle=1800` and `max_overflow=20` explicitly in production engine settings. |

---

### Area 11: Deployment & Infrastructure

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Host-Gateway Portability** | `extra_hosts: "host.docker.internal:host-gateway"` in compose. | `docker-compose.yml` | Linux installations without modern Docker engine (pre-20.10) fail on `host-gateway` resolution. | **HIGH** | Use environment variable `HOST_GATEWAY_IP` with conditional fallback in `docker-compose.yml`. |
| **Volume Path Consistency** | Reports volume mounted as `reports_data:/app/app/data/reports`. | `docker-compose.yml` line 61 | `config.py` default `REPORTS_DIR="data/reports"` resolves to `/app/data/reports` in container root. | **CRITICAL** | Harmonize volume mount in `docker-compose.yml` to `reports_data:/app/data/reports`. |
| **Model Pre-Provisioning Script** | Pre-warmed `model_cache` volume mount. | `backend/model_cache/` | Fresh clone on a clean machine without internet lacks an automated offline asset pre-fetch verification script. | **HIGH** | Create `scripts/prewarm_offline_assets.py` to bundle all weights and tokenizer files into `model_cache/`. |

---

### Area 12: Database Schema & Indexing

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Schema Migration Tracking** | `scripts/migrate.py` executes `Base.metadata.create_all()`. | `backend/scripts/migrate.py` | Lacks formal Alembic migration version history table (`alembic_version`) for incremental enterprise upgrades. | **HIGH** | Initialize Alembic migration environment to track schema revisions cleanly. |
| **Lexical Index Trigger** | Trigger keeps `content_tsv` synchronized on update. | `backend/scripts/init_lexical_search.sql` | `ix_chunks_content_tsv` GIN index is created on the main table without composite indexing on `organization_id`. | **MEDIUM** | Add composite index or partial GIN index on `(organization_id, content_tsv)` for multi-tenant search speedup. |
| **Database Partitioning** | Single `chunks` and `embeddings` table. | `backend/app/models/chunk.py` | Multi-million chunk production corpora will experience slow vacuuming and index bloat without partitioning. | **FUTURE** | Partition `chunks` and `embeddings` by `organization_id` or range hash in multi-year production roadmap. |

---

### Area 13: Frontend Product Completeness

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Executive Dashboard Filters** | Dashboard charts show aggregated totals across all subsidiaries. | `frontend/src/pages/Dashboard.tsx` | Dashboard lacks an interactive Subsidiary dropdown filter directly updating the KPI cards without page change. | **HIGH** | Add top-level Subsidiary and Fiscal Year dropdown selectors directly to `Dashboard.tsx`. |
| **Document Batch Deletion** | Documents can be inspected and downloaded individually. | `frontend/src/pages/DocumentList.tsx` | No multi-select checkbox to batch-delete or batch-reprocess failed documents from the UI. | **MEDIUM** | Add multi-select checkbox and batch action toolbar to `DocumentList.tsx`. |
| **Dark Mode / Theme Consistency** | UI is styled in dark-coal enterprise palette with Tailwind v4. | `frontend/src/index.css` | A few modals have hardcoded white backgrounds (`bg-white`) creating visual contrast seams in dark mode. | **LOW** | Standardize modal panels to use `bg-slate-900 border-slate-800` theme variables. |

---

### Area 14: API Completeness & OpenAPI Contract

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Batch Reprocessing Endpoint** | Single document reprocessing `/api/v1/documents/{id}/process`. | `backend/app/api/v1/documents.py` | Missing batch reprocessing endpoint for administrators to trigger mass re-indexing after OCR updates. | **MEDIUM** | Implement `POST /api/v1/documents/batch-reprocess` accepting a list of document IDs. |
| **Audit Export API** | Audit events viewable in UI table. | `backend/app/api/v1/audit.py` | Missing CSV/JSON export endpoint for external vigilance and statutory compliance auditors. | **HIGH** | Implement `GET /api/v1/audit/export?format=csv` with streaming response and administrator authorization. |

---

### Area 15: Observability & Diagnostics

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Structured Logging Output** | Custom JSON formatter writing to `stdout`/`stderr`. | `backend/app/core/logging_config.py` | Logs are not mirrored to a persistent rotating log file on disk inside the container volume. | **MEDIUM** | Add rotating file handler (`RotatingFileHandler`) writing to `/app/logs/koyla.log` with 50MB rotation. |
| **Prometheus Metric Labels** | Metrics at `/metrics` export latencies and status codes. | `backend/app/core/logging/timing.py` | Stage durations lack subsidiary labels, making it hard to diagnose if a specific subsidiary has slow OCR scans. | **LOW** | Add optional `subsidiary` label to Prometheus histogram metrics. |

---

### Area 16: Backup & Disaster Recovery

| Subsystem Component | Current State | Code Evidence | Identified Gap | Severity | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Automated Backup Scheduling** | Manual backup creation via REST API or CLI. | `backend/app/services/backup/backup.py` | No in-process scheduled backup cron inside Celery beat; requires host system crontab. | **HIGH** | Add Celery beat periodic task (`scheduled_backup_task`) running daily at 02:00 AM UTC. |
| **Point-In-Time-Recovery (PITR)** | Full snapshot dumps (`pg_dump`) with SHA-256 manifests. | `docs/BACKUP_AND_RESTORE.md` | Continuous Write-Ahead-Log (WAL) archiving is not configured; recovery point is limited to snapshot frequency. | **FUTURE** | Configure PostgreSQL `archive_mode = on` and WAL streaming to dedicated disaster recovery volume. |

---

## 3. Prioritized Engineering Action Matrix

### P0 — Must Fix (Release Blockers & Critical Product Deficiencies)
*These items address critical bugs, data truncation, or operational failures during genuine usage.*

1. **[P0-1] Harmonize Volume Mount Paths in `docker-compose.yml`**:
   - *Issue*: `reports_data:/app/app/data/reports` in `docker-compose.yml` mismatches `config.py` default `data/reports` (resolving to `/app/data/reports`). This causes generated `.docx` reports to be stored outside the named volume, risking data loss on container recreation.
   - *Fix*: Update `docker-compose.yml` to `reports_data:/app/data/reports`.
2. **[P0-2] Implement Automated Stuck-Job Janitor / Reaper Task**:
   - *Issue*: If a Celery worker is killed during OCR or document processing, the PostgreSQL `Document` and `ProcessingJob` remain in `PROCESSING` status permanently.
   - *Fix*: Create a scheduled janitor service in `backend/app/tasks/` that detects jobs stuck in `PROCESSING` > 30 minutes, resets status to `FAILED`, and logs diagnostic audit events.
3. **[P0-3] Multi-Document Structured Numerical Aggregator in Q&A**:
   - *Issue*: When answering questions requiring multi-document aggregation (e.g. "Total coal production across all quarters in FY24"), the 5-chunk text limit truncates data, causing incomplete answers.
   - *Fix*: Enhance `StructuredLookupService` to execute direct SQL `SUM()`, `AVG()`, and `GROUP BY` aggregations over `ExtractedField` when temporal or multi-document aggregation queries are detected.
4. **[P0-4] Bilingual Hindi/English OCR Support**:
   - *Issue*: Tesseract OCR is hardcoded to English (`lang="eng"`). Real CIL mining plans, exploration summaries, and official circulars frequently feature Hindi stamps, headings, and Devanagari numerals.
   - *Fix*: Configure OCR parser to support `lang="eng+hin"` with automatic fallback to `eng` if Devanagari training data is absent.

---

### P1 — Important (High-Value Functional & Operational Additions)
*These items significantly elevate the domain intelligence, governance, and operational completeness of Koyla.*

1. **[P1-1] Normalized Lithological Strata Sequence Model**:
   - Implement `BoreholeStratum` database model (`borehole_id`, `stratum_order`, `depth_from_m`, `depth_to_m`, `thickness_m`, `lithology_type`, `seam_name`) and extract structured layer sequences from borehole logs.
2. **[P1-2] Multi-Row Merged Header Propagation in Spreadsheet Parser**:
   - Enhance `SpreadsheetParser` to detect hierarchical merged headers in Excel sheets, forward-filling parent column names (e.g., `["FY24", "Actual"]` $\to$ `"FY24_Actual"`).
3. **[P1-3] Two-Tier (4-Eyes) Verification Workflow for Statutory Reserve Edits**:
   - Require a secondary review / Qualified Person co-signature on the Verification Queue when a user attempts to alter `gross_geological_reserve_mt` or `proved_reserve_mt`.
4. **[P1-4] Automated Celery Beat Backup Scheduler**:
   - Add automated recurring backup schedule in Celery beat (`@crontab(hour=2, minute=0)`) with automatic retention count enforcement.
5. **[P1-5] Statutory Audit Trail CSV/JSON Export API**:
   - Implement `GET /api/v1/audit/export` allowing vigilance and compliance officers to download signed audit logs.
6. **[P1-6] Interactive Executive Dashboard Filters**:
   - Add direct interactive Subsidiary and Fiscal Year dropdown selectors to `Dashboard.tsx` to filter KPI cards and distribution charts live.

---

### P2 — Enhancement (Usability, Diagnostics & Polish)
1. **[P2-1] Multi-Frame TIFF Parser**: Support multi-page TIFF file ingestion for legacy survey scans.
2. **[P2-2] Redis-Backed Distributed Rate Limiter**: Upgrade SlowAPI to share limits across multi-container worker pools.
3. **[P2-3] Token Blacklist in Redis**: Invalidate JWT tokens in Redis upon user logout.
4. **[P2-4] Bulk Triage Actions & Keyboard Shortcuts**: Add multi-select and hotkeys (`[A]`, `[R]`, `[C]`) to the Verification Queue.
5. **[P2-5] Persistent Rotating Log File**: Configure Python logging to write to `/app/logs/koyla.log` with 50MB rotation.

---

### FUTURE (Multi-Year Enterprise Scalability & Custom Research)
1. **[FUTURE-1] Domain-Specific Deep Learning Vision Model**: Fine-tune a vision transformer on hundreds of thousands of proprietary CMPDI borehole logs and seismic sections.
2. **[FUTURE-2] Native SAP NetWeaver PyRFC Connector**: Direct binary RFC gateway integration for legacy SAP R/3 instances.
3. **[FUTURE-3] Continuous PostgreSQL WAL Archiving & PITR**: Implement second-by-second Point-In-Time-Recovery via WAL streaming to remote DR storage.
4. **[FUTURE-4] Relational Partitioning**: Partition `chunks` and `embeddings` by `organization_id` hash for multi-million document production scaling.

---

## 4. Summary of Gaps & Weakness Diagnosis

* **Total Gaps Identified**: **28 distinct engineering gaps** across 16 subsystems.
  - **P0 (Must Fix)**: **4 items**
  - **P1 (Important)**: **6 items**
  - **P2 (Enhancement)**: **5 items**
  - **FUTURE (Roadmap)**: **4 items**
  - **Subsystem-Specific Gaps (Documented in Section 2)**: **9 items**

### The Most Important Engineering Weakness Discovered:
> **The Context-Window Truncation of Multi-Document Numerical Aggregation in Q&A (Gap P0-3).**  
> While Koyla’s hybrid search and arithmetic engine excel at single-document questions (e.g. *"What is the reserve of Seam IV in Raniganj?"*), queries requiring annual totals or multi-document historical summaries (e.g. *"What was the total coal production of ECL across all quarters in 2024?"*) are bottlenecked by the fixed `MAX_EVIDENCE_CHUNKS=5` limit. The system tries to answer an aggregate mathematical question by feeding text chunks to an LLM rather than leveraging SQL aggregations (`SUM()`, `AVG()`) over its existing `ExtractedField` relational database records. Resolving this via a dual-path structured aggregator is the single highest-value engineering enhancement for Koyla.
