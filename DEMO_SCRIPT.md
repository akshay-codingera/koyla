# DEMO_SCRIPT.md
# CIL / CMPDI AI Reporting & Intelligence Platform
# SIH Problem Statement 26023 — Demonstration Script & Walkthrough

## 1. Demonstration Purpose
Demonstrate an end-to-end, locally runnable, air-gapped enterprise prototype solving SIH Problem Statement 26023:
**"AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries"**

This walkthrough proves that:
1. The platform is not a toy chatbot or static UI, but a genuine internal government enterprise intelligence platform.
2. Ingestion, OCR, structure recovery, domain extraction, and validation are deterministic and audit-backed.
3. Grounded Q&A refuses to hallucinate when evidence is missing.
4. Reports are generated as genuine, editable `.docx` files from verified database records.
5. Verification, governance, and audit trails trace every datum back to source documents.

---

## 2. Demonstration Step-by-Step Flow

### Step 1: Secure Login & Institutional Scoping
- **Action:** Open `http://localhost:5173/login`.
- **Narration:** *"We log into the CIL / CMPDI Reporting Intelligence Platform. Notice our prototype role selector: Ministry Officer, CMPDI HQ Officer, RI Analyst, Subsidiary Analyst, Verification Officer, and System Administrator. We log in as the CMPDI HQ Officer."*
- **What to Show:**
  - Official enterprise UI with dark coal/graphite structure, clear typography, and zero flashy consumer-AI clichés.
  - Organization context indicator: `[CMPDI HQ - Ranchi]`.
  - Prominent banner: `[Prototype / Demonstration Dataset - Synthetic Records]`.

### Step 2: Executive Dashboard — Real Calculated Database Metrics
- **Action:** Navigate to `/dashboard`.
- **Narration:** *"Every metric on this dashboard is calculated directly from database queries — not hardcoded constants. We see total documents ingested, processing status, extraction confidence, verification backlogs, and subsidiary distributions across ECL, BCCL, CCL, WCL, SECL, NCL, and MCL."*
- **What to Show:**
  - Live charts showing document types, verification statuses, and processing pipelines.
  - Active filter by Subsidiary or Regional Institute.

### Step 3: Organization Explorer & 3-Node Federation Simulator
- **Action:** Navigate to `/organization`.
- **Narration:** *"Here is the complete organizational hierarchy: Coal India Limited at the apex, CMPDI HQ, and the 7 Regional Institutes mapped to their corresponding operating subsidiaries — such as RI-I to ECL, RI-V to SECL, and RI-VII to MCL. Down below, we simulate cross-subsidiary federation across three isolated nodes: node-cmpdi, node-secl, and node-ecl."*
- **What to Show:**
  - Interactive hierarchical tree.
  - Federation simulation panel demonstrating cross-boundary queries while respecting data tenancy.

### Step 4: Document Ingestion & Structure Recovery
- **Action:** Navigate to `/documents/ingest`.
- **Narration:** *"We ingest a new mining document — for example, a monthly production bulletin or geological survey. The system immediately computes its cryptographic SHA-256 hash, determines its MIME type, and assigns a configurable Trust Tier (Tier A Authoritative, Tier B Internal Operational, Tier C User-Provided)."*
- **What to Show:**
  - Drag-and-drop file upload.
  - Immediate SHA-256 digest display.
  - Processing job status updating in real-time.

### Step 5: Document Detail, Local OCR & Table Preservation
- **Action:** Navigate to `/documents/:id` (e.g. `SECL_Gevra_OCP_Monthly_Production_May2024.pdf`).
- **Narration:** *"Let's inspect the document intelligence engine. The digital parser and local OpenCV/OCR pipeline have extracted the text, preserved table structures with column headers intact, and isolated domain entities like coal production, stripping ratio, and overburden removal."*
- **What to Show:**
  - Side-by-side or tabbed viewer: Original preview, raw extracted text, recovered tables, and extracted domain fields with confidence scores.
  - Notice the field-level provenance: Page number, source text snippet, and extraction confidence.

### Step 6: Deterministic Validation & Conflict Detection
- **Action:** Inspect the Validation Issues panel in the document viewer or navigate to `/verification`.
- **Narration:** *"The platform does not trust AI blindly. Our deterministic validation engine compares values against physical bounds and cross-references overlapping reports. Here, two reports submitted differing coal reserve figures for the same block. Instead of silently guessing, the system flagged a high-severity CONFLICT and routed it to the Human Verification Queue."*
- **What to Show:**
  - Validation issue card highlighting field name, Source Document A, Source Document B, conflicting values, and review status.

### Step 7: Grounded AI Q&A with Strict Citation
- **Action:** Navigate to `/query`.
- **Narration:** *"Now let's ask a domain question: 'What was the coal production and stripping ratio for Gevra Open Cast Project in May 2024?'"*
- **What to Show:**
  - Hybrid RRF retrieval finds top evidence chunks.
  - Answer is generated strictly citing the evidence: `[Doc #doc-501, Page 2]`.
  - Evidence drawer opens to reveal the exact source excerpt and matching confidence score.

### Step 8: Hallucination Refusal Demonstration
- **Action:** Submit an unanswerable or out-of-domain query: *"What is the enriched uranium output of Kusmunda colliery?"*.
- **Narration:** *"Notice what happens when we ask about an ungrounded or unsupported concept. Rather than hallucinating an answer, our multi-layer hallucination defence deterministically triggers a refusal: 'Insufficient verified evidence found in the indexed sources for the selected organization scope.' This guarantees institutional trustworthiness."*
- **What to Show:**
  - Clear refusal badge and explanation without fabricated figures.

### Step 9: Report Generation Studio & DOCX Download
- **Action:** Navigate to `/reports/new`.
- **Narration:** *"Now let's demonstrate Module 1: Automated Report Generation. We choose the 'Monthly Production Summary' template, select SECL, and specify the period. The platform retrieves verified structured fields from the database, runs validation checks, and presents a review screen. Once approved, it deterministically renders a real, editable Microsoft Word (.docx) document."*
- **What to Show:**
  - Template selector and structured schema preview.
  - Clicking 'Generate & Approve Report' generates the `.docx` file.
  - Download and open the actual `.docx` file showing official CIL/CMPDI formatted tables, headers, and metadata.

### Step 10: Topic Identification & Interactive Word Cloud
- **Action:** Navigate to `/topics`.
- **Narration:** *"Here is Module 2: Automated Topic Identification and Word Cloud. Using local embeddings and c-TF-IDF clustering, the platform extracts key themes across all ingested geological and operational reports — such as Overburden Removal, Dragline Optimization, Seam Coal Quality, and Statutory Safety. An interactive word cloud and temporal trend graph show how focus areas evolve over fiscal years."*
- **What to Show:**
  - Topic cluster ranking with document counts.
  - Interactive Word Cloud with mining domain terms.

### Step 11: Human Verification Queue & Governance Audit Ledger
- **Action:** Navigate to `/verification` and then `/governance`.
- **Narration:** *"In the Human Verification Center, officers review low-confidence OCR, conflicting values, and drafted reports. Approving an item updates the database and immediately writes an immutable record into the Governance Audit Ledger. Every action — from login and upload to Q&A and report download — is cryptographically logged with actor, organization, timestamp, and SHA-256 hash."*
- **What to Show:**
  - Triage approval action.
  - Audit trail table showing real-time event updates.

### Step 12: System Health & Zero External Runtime Dependencies
- **Action:** Navigate to `/system`.
- **Narration:** *"Finally, we check System Health. All services — FastAPI Core, Database, Vector Search, Local OCR, and Local LLM Abstraction — report healthy statuses. Not a single byte of CIL data was sent to any external cloud AI provider. The system is 100% capable of operating on-premise in an air-gapped government data center."*
- **What to Show:**
  - System health grid showing UP statuses, local model info, and queue states.
