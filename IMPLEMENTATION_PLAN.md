# IMPLEMENTATION PLAN — PHASE 10: UNIVERSAL EVIDENCE ENGINE

## Automatic Multiformat Intelligence, Multimodal Grounding & Human Verification

---

## 1. Executive Summary & Objective

Phase 10 elevates Koyla from separate document and visual intelligence modules into a **Universal Evidence Engine**.
The guiding design principle is:
> **ONE ACTION FOR THE USER → AUTOMATIC EVIDENCE PIPELINE → ONE UNIFIED EVIDENCE LAYER → GROUNDED ANSWERS → HUMAN REVIEW ONLY WHEN NECESSARY**

The platform will automatically ingest heterogeneous mining and geological records (**PDF, DOCX, XLSX, XLS, CSV, JPG/JPEG, PNG, TXT**), extract structured and multimodal evidence with format-aware provenance (Workbook/Sheet/Cell, File/Row/Column, PDF/Page/Bbox), discover cross-record relationships, index everything in the existing `pgvector` store, and enable multimodal grounded Q&A with deterministic arithmetic.

---

## 2. Non-Negotiable Architecture Constraints

1. **Reuse Existing Stack**:
   - Reuse existing `Document`, `Chunk`, `Embedding`, `VisualAsset`, `ExtractedField`, and `VerificationTask` tables.
   - Reuse existing `bge-small-en-v1.5` embeddings and `pgvector` index.
   - Reuse existing hybrid BM25 + dense search + RRF retrieval engine.
   - Reuse existing Phase 9 visual detector and storage pipeline.
   - Do NOT create a second ingestion architecture, retrieval stack, or vector database.
2. **Zero Hallucination & Strict Grounding**:
   - Numerical calculations must be computed deterministically via `ArithmeticEngine` (no LLM math).
   - If evidence is missing or contradictory, state refusal or report conflict requiring review.
3. **Automatic UX**:
   - No 8-step wizard. One unified **ADD EVIDENCE** action for multi-file drag-and-drop.
   - Automated format detection, parser selection, confidence estimation, and relationship discovery.
   - Human review requested **only** for low-confidence or conflicting items.

---

## 3. Dependency Graph & Module Breakdown

```text
                [User: ADD EVIDENCE (Multi-File Drop)]
                                 │
                                 ▼
                     [StorageService Validation]
                     (PDF, DOCX, XLSX, XLS, CSV, JPG, PNG, TXT)
                                 │
                                 ▼
                    [Universal Ingestion Router]
         ┌───────────────┬───────────────┬───────────────┐
         ▼               ▼               ▼               ▼
    [PDFParser]    [Spreadsheet/     [DOCXParser]   [OCRParser /
   (PyMuPDF +       CSV Parser]     (python-docx +  VisualDetector]
  VisualDetector) (openpyxl + csv)   embed images)   (Direct Images)
         │               │               │               │
         └───────────────┼───────────────┴───────────────┘
                         ▼
             [Format-Aware Evidence Normalization]
             - Text Chunks (Page / Section)
             - Table Chunks (Sheet / Range / Caption)
             - Structured Values (Workbook / Sheet / Cell)
             - Visual Assets (Page / Bbox / OCR / Classification)
                         │
                         ▼
             [Confidence Evaluation & Auto-Acceptance]
             - High confidence -> AUTO-ACCEPTED
             - Low confidence -> REVIEW_REQUIRED (VerificationTask)
                         │
                         ▼
             [Automatic Relationship Discovery]
             - Match: same org, same mine, same period, same metric
                         │
                         ▼
             [pgvector Dense Indexing (BGE-small-en-v1.5)]
                         │
                         ▼
        ┌────────────────────────────────────────────────┐
        │              UNIFIED EVIDENCE LAYER            │
        │ - Evidence Control Room (/evidence)            │
        │ - Hybrid Multimodal Retrieval (BM25 + Dense)   │
        │ - Multimodal Grounded Q&A + Deterministic Math │
        └────────────────────────────────────────────────┘
```

---

## 4. Proposed Technical Changes

### 4.1 Backend Services & Parsers

#### A. Storage & Allowed Extensions ([`backend/app/services/storage.py`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/backend/app/services/storage.py))
- Add `.csv` (`text/csv`) and `.txt` (`text/plain`) to `ALLOWED_EXTENSIONS` and `ALLOWED_MIME_TYPES`.
- Ensure streaming SHA-256 calculation and path sanitization protect against path traversal.

#### B. Spreadsheet & CSV Parser Upgrades ([`backend/app/services/parsers/`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/backend/app/services/parsers/))
- **`spreadsheet_parser.py`**:
  - Deep inspection of multi-sheet workbooks (`openpyxl`).
  - Extract exact cell/range provenance (e.g. `Sheet: 'Monthly Production', Range: 'B12:E18'`).
  - Extract structured reporting fields (metric name, numeric value, unit, sheet, cell address).
  - Handle merged cells and data types cleanly without crashing.
- **`csv_parser.py` [NEW]**:
  - Automatic delimiter detection (comma `,`, tab `\t`, semicolon `;`, pipe `|`) via Python `csv.Sniffer`.
  - Encoding fallback (`utf-8`, `utf-8-sig`, `latin-1`).
  - Column type inference (numeric, date, text) and row-level coordinates (e.g. `Row 184, Column 'production'`).
- **`txt_parser.py` [NEW]**:
  - Plain text file ingestion with structured paragraph segmentation and char/line provenance.
- **`ocr_parser.py`**:
  - For direct image uploads (`.jpg`, `.jpeg`, `.png`), pass image to `visual_detector.detect_visuals_from_image_file()`.
  - Automatically create `ParsedVisual` with 14-type classification, confidence, and OCR transcript.
- **`docx_parser.py`**:
  - Extract embedded images from `doc.part.related_parts` as `ParsedVisual` entries.

#### C. Ingestion Pipeline & Auto-Classification ([`backend/app/services/ingestion.py`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/backend/app/services/ingestion.py))
- Infer `document_type` automatically from file extension and content if not explicitly specified:
  - `.xlsx`, `.xls`, `.csv` -> `STATISTICAL_ANNEXURE` or `PRODUCTION_SUMMARY`
  - `.png`, `.jpg`, `.jpeg` -> `VISUAL_RECORD`
  - `.pdf`, `.docx` -> `GEOLOGICAL_REPORT` or `TECHNICAL_REPORT`
  - `.txt` -> `TECHNICAL_MEMO`
- Ingest structured values directly into `ExtractedField` with format-aware `metadata_json`.
- Chunk structured records into `Chunk` with `chunk_type="STRUCTURED_VALUE"` or `"TABLE"`.
- Assess extraction/OCR confidence: if `< 0.60`, flag `needs_review=True` and insert `VerificationTask`.

#### D. Automatic Relationship Discovery ([`backend/app/services/relationships.py`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/backend/app/services/relationships.py) [NEW])
- Service detecting lightweight deterministic connections across evidence items:
  - `SAME_ORGANIZATION`: Shared `organization_id`
  - `SAME_MINE_OR_BLOCK`: Shared entity name (e.g. "Rajmahal OCP", "Gevra OC", "Moonidih")
  - `SAME_PERIOD`: Matching fiscal year or monthly period (e.g. "FY 2024-25", "May 2024")
  - `SAME_METRIC`: Identical metric name across different files (e.g. "coal_production" in Excel vs. Report)
  - `SAME_DOCUMENT_FAMILY`: Related annexures, figures, and versions
- Strictly deterministic matching; no LLM entity invention.

#### E. Universal Evidence API ([`backend/app/api/v1/evidence.py`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/backend/app/api/v1/evidence.py) [NEW])
- `POST /api/v1/evidence/upload`: Multi-file upload (`List[UploadFile]`) with automatic format routing and background ingestion.
- `GET /api/v1/evidence/summary`: Aggregated counts across records, text items, tables, structured values, figures, and review backlog.
- `GET /api/v1/evidence/items`: Unified list of evidence items with filtering by type, source document, and review status.
- `GET /api/v1/evidence/{evidence_id}`: Granular evidence inspector with exact location and source snippet.
- `POST /api/v1/evidence/{evidence_id}/review`: One-click verification action (`APPROVE`, `CORRECT`, `REJECT`).
- `GET /api/v1/evidence/relationships`: List of discovered cross-record relationships.
- Registered in `backend/app/main.py`.

#### F. Multimodal Grounding in Q&A ([`backend/app/services/qa/qa_service.py`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/backend/app/services/qa/qa_service.py))
- Update evidence compilation to seamlessly interleave:
  - Textual paragraphs
  - Spreadsheet tables with sheet and cell ranges
  - Structured values with cell provenance
  - Visual figures with figure numbers, types, captions, and thumbnails
- Update `ArithmeticEngine` to support percentage change and delta calculations across spreadsheet/CSV records.
- Ensure citations reflect format-aware provenance (`Workbook -> Sheet -> Cell`, `PDF -> Page`, `Figure -> Bbox`).

---

### 4.2 Frontend Interfaces

#### A. Unified "ADD EVIDENCE" Drag & Drop UX
- Enhance [`frontend/src/pages/DocumentUpload.tsx`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/frontend/src/pages/DocumentUpload.tsx):
  - Support multi-file selection and drop for all 8 formats.
  - Batch processing indicator showing real-time file-by-file progress.
  - Completion summary banner showing text count, table count, visual count, structured value count, and relationships discovered.
  - Direct button to `[VIEW EVIDENCE]`.

#### B. Evidence Control Room ([`frontend/src/pages/EvidenceControlRoom.tsx`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/frontend/src/pages/EvidenceControlRoom.tsx) [NEW])
- Route: `/evidence`
- Dark technical enterprise layout matching Koyla design language.
- Top KPI counters: Total Records, Text Items, Tables, Structured Values, Visuals, Needs Review.
- Filter toolbar: `All | Text | Tables | Values | Visuals | Needs Review`.
- Evidence Register table with format-aware location badges (`Sheet: April, D17`, `Page 18, Fig 1`).
- Inspector Modal: Shows raw content, image preview (if visual), table grid (if table), and review actions (`[Approve]`, `[Correct]`, `[Reject]`).

#### C. Multimodal Q&A Results ([`frontend/src/pages/AIQuery.tsx`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/frontend/src/pages/AIQuery.tsx))
- Display citations with evidence-type badges (`TEXT`, `TABLE`, `VALUE`, `VISUAL`).
- Visual citations include an inline thumbnail and link to source page.
- Tabular citations include sheet and cell coordinates.
- Arithmetic cards explain formula and source cells for calculated metrics.

#### D. Navigation Update ([`frontend/src/components/ProtectedRoute.tsx`](file:///c:/Users/aksha/.gemini/antigravity/scratch/koyla/frontend/src/components/ProtectedRoute.tsx))
- Add `Evidence` link to top navbar.

---

## 5. Verification Plan

### 5.1 Automated Unit & Integration Tests (`backend/tests/test_universal_evidence.py`)
- Test ingestion of all 8 formats: PDF, DOCX, XLSX, XLS, CSV, JPG, PNG, TXT.
- Test CSV delimiter detection (comma, tab, semicolon, pipe) and malformed CSV handling.
- Test Excel multi-sheet parsing and cell/range coordinate preservation.
- Test direct image parsing into `VisualAsset` and `VISUAL` chunks.
- Test automatic relationship discovery across records.
- Test multimodal Q&A retrieval and citation formatting.
- Test deterministic arithmetic calculations on extracted spreadsheet values.
- Test security checks: path traversal, malicious formulas, unauthorized evidence access.

### 5.2 Full Backend Regression
- Run complete test suite:
  ```bash
  docker compose exec -e PYTHONPATH=. backend pytest tests/ -q
  ```
  Ensure all 185+ tests pass with 0 regressions.

### 5.3 Live Multimodal End-to-End Test & Golden Demo (`backend/tests/verify_phase10_live.py`)
- Synthetic dataset containing:
  - `annual_report.pdf` (technical report with geological context)
  - `production.xlsx` (multi-sheet production workbook with April and May figures)
  - `mine_data.csv` (CSV operational data with delimiter detection)
  - `geological_section.png` (direct visual cross-section)
- Upload all 4 files simultaneously via `ADD EVIDENCE`.
- Verify automatic processing, evidence counts, and relationship discovery.
- Execute Golden Demo Query:
  *"Compare Mine A's May production with April and explain whether the geological report contains evidence relevant to the mine's condition."*
- Validate that the answer combines:
  - Numerical calculation (`((May - April) / April) * 100`) with Excel cell provenance
  - Visual evidence from `geological_section.png` with bounding box
  - Textual context from `annual_report.pdf`
- Run Playwright browser automation capturing screenshots of:
  1. Add Evidence batch processing
  2. Evidence Control Room with register and filters
  3. Evidence Inspector Modal with review actions
  4. Multimodal Q&A response with visual and tabular citations

### 5.4 Git Delivery
- Git commit: `feat: add universal evidence ingestion and multimodal grounding`
- Push cleanly to `origin/main`.
