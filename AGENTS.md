# AGENTS.md
# CIL / CMPDI AI-Powered Geological, Mining and Reporting Platform
# Koyla engineering instructions

## 0. Mission

Build a real, locally runnable, enterprise-grade prototype for SIH Problem Statement 26023:

"AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries"

The product is a unified internal CIL/CMPDI reporting intelligence platform.

The prototype must demonstrate a complete working path:

Document / data ingestion
→ preprocessing / OCR
→ structured extraction
→ validation / confidence
→ indexing / retrieval
→ AI question answering
→ citation / grounding
→ report generation
→ human verification
→ audit trail
→ organization-scoped dashboard.

The system must look and behave like a serious government-sector enterprise application, not a generic AI chatbot or a static UI mockup.

---

# 1. Non-negotiable engineering principles

1. Do not hallucinate CIL/CMPDI facts, statistics, processes, organizational relationships, APIs, internal systems, policies, or operational procedures.

2. Use verified public information only for public organizational metadata.

3. Clearly label synthetic/demo operational data.

4. Never claim that the prototype is connected to internal CIL systems unless an actual tested connector exists.

5. Never create fake "live" numbers merely to make a dashboard look convincing.

6. Every dashboard KPI must come from a database query or a clearly labelled demo-data source.

7. Every AI answer must be traceable to retrieved evidence.

8. When the system cannot verify an answer, it must say that evidence was not found instead of guessing.

9. Prefer deterministic workflows over unrestricted autonomous agents.

10. Use AI where reasoning/language is required, but use deterministic code for validation, calculations, permissions, document rendering, and audit logic.

11. Never use an external AI API at runtime in the intended government deployment architecture.

12. Keep the entire core stack capable of running on-premise.

13. Do not leave dead buttons, fake controls, placeholder pages, or unimplemented navigation in the final demo.

14. Do not make production-readiness claims based solely on architecture diagrams.

---

# 2. Product identity

Working product name:

CIL / CMPDI Reporting Intelligence Platform

Suggested UI descriptor:

"AI-Assisted Geological, Mining & Reporting Intelligence"

Do not invent an official CIL product name.

The UI should feel like an internal government enterprise system:
- formal
- information-dense
- accessible
- restrained
- professional
- audit-oriented
- operational
- no flashy consumer-AI styling.

Avoid:
- neon gradients
- gaming-style dashboards
- excessive animations
- fake AI holograms
- decorative AI imagery
- unnecessary glassmorphism
- marketing-style landing pages.

---

# 3. Primary users

Implement role-aware access.

Prototype roles:

1. Ministry / Central Reviewer
2. CIL / CMPDI HQ Officer
3. Regional Institute Officer
4. Subsidiary Analyst
5. Verification Officer
6. System Administrator

These are application roles for the prototype.

Do not claim they are exact official CIL job titles unless independently verified.

Permissions must be implemented in backend logic, not merely hidden in the frontend.

---

# 4. Organization model

Create a configurable organization hierarchy.

Base conceptual structure:

CIL
└── CMPDI / HQ context
    ├── Regional Institutes
    ├── Subsidiaries
    └── other configured organizational units

Do not hard-code uncertain relationships.

Store the hierarchy in database configuration tables so that:
- organizations can be added
- organizations can be disabled
- parent-child relationships can be updated
- organization scope can be applied to documents and queries.

Use verified public organizational metadata where available.

Every document must have an organization scope.

---

# 5. Core modules

The application must implement the following modules.

## 5.1 Executive Dashboard

Show real calculated data:
- total documents
- processed documents
- documents awaiting verification
- failed processing jobs
- generated reports
- verified answers
- recent activity
- processing trend
- document-type distribution
- organization distribution
- verification status
- topic trends.

Allow filters such as:
- organization
- regional institute
- subsidiary
- fiscal year
- document type
- date range
- verification status.

The dashboard must query the backend.

---

## 5.2 Organization Network

Create an organization explorer.

Capabilities:
- organization hierarchy
- organization summary
- document count
- processing status
- reports
- verification queue
- activity
- organization-scoped search.

Do not use fake statistics.

---

## 5.3 Document Management

Users must be able to:
- upload files
- see processing status
- inspect document metadata
- view extracted text
- inspect page information
- view detected tables
- view extracted entities/metrics
- view confidence
- view trust tier
- see document version history
- download original
- download generated derivative/report where authorized.

Supported initial formats:
- PDF
- XLSX/XLS
- DOCX
- images
- TXT/CSV where useful.

---

# 6. Ingestion pipeline

Implement a real backend pipeline:

Upload
→ MIME detection
→ SHA-256 hash
→ document registration
→ source classification
→ parser selection
→ preprocessing
→ OCR if required
→ structure extraction
→ metadata extraction
→ field extraction
→ validation
→ chunking
→ embeddings
→ indexing.

For digital PDFs:
- use a native parser before OCR.

For scanned documents:
- preprocess image
- deskew
- denoise
- OCR
- preserve page information.

Never OCR a clean digital document unnecessarily.

---

# 7. OCR and extraction

Initial implementation should be local.

Preferred components:
- PyMuPDF / pdfplumber for digital PDFs
- OpenCV for preprocessing
- PaddleOCR or Tesseract for local OCR
- openpyxl for spreadsheets
- python-docx for DOCX inspection/generation.

Preserve:
- page number
- section
- heading
- table identity
- row/column relationship
- source document ID.

The chunking system must be structure-preserving.

Do not split a table arbitrarily merely because a fixed token/word limit was reached.

---

# 8. Source classification

Every ingested source must have a trust classification.

Use configurable tiers such as:

Tier A:
authoritative / verified source

Tier B:
internal operational source requiring defined trust handling

Tier C:
unverified / user-provided / low-trust material

Do not silently assume that all uploaded data is authoritative.

The exact meaning of each tier must be configurable.

---

# 9. Structured extraction

The extraction layer must produce machine-readable JSON.

Do not make the LLM directly write final report prose.

Example conceptual output:

{
  "document_id": "...",
  "organization_id": "...",
  "fiscal_year": "...",
  "reserve_mt": {
    "value": 0,
    "unit": "MT",
    "confidence": 0.0,
    "source_page": 0
  }
}

Use:
- deterministic regex/pattern extraction where sufficient
- domain entity rules
- local LLM for difficult language understanding
- explicit confidence
- source references.

Every extracted field should retain provenance.

---

# 10. Validation engine

Implement deterministic validation wherever possible.

Examples:
- numeric range checks
- unit consistency
- required fields
- date consistency
- cross-document comparison
- duplicate values
- conflicting values
- missing values.

When two sources conflict:

DO NOT silently choose one.

Create a validation issue containing:
- field
- source A
- source B
- values
- confidence
- status
- review requirement.

---

# 11. Retrieval engine

Initial architecture:

BM25
+
dense vector search
→ Reciprocal Rank Fusion
→ metadata filtering
→ cross-encoder reranking
→ top evidence selection.

Required metadata filters:
- organization
- subsidiary
- regional institute
- fiscal year
- document type
- source tier
- date range where applicable.

Search should support:
- exact identifiers
- natural-language conceptual queries
- numeric/document queries
- domain terms.

Keep keyword and semantic search independently testable.

---

# 12. AI Query and Response

This is a grounded retrieval system, not an unrestricted chatbot.

Pipeline:

User question
→ query understanding
→ metadata constraints
→ BM25
→ dense retrieval
→ RRF
→ reranking
→ evidence extraction
→ answer generation
→ verification
→ citation
→ answer.

Use an extract-then-compose architecture where appropriate.

The composition model must receive only approved evidence for the final answer.

The answer must contain source references.

When evidence is insufficient:

Return:
"Insufficient verified evidence found in the selected knowledge base."

Do not guess.

---

# 13. Hallucination defence

Implement multiple layers.

Layer 1:
evidence extraction / selection

Layer 2:
schema-constrained generation

Layer 3:
NLI / entailment verification when technically feasible

Layer 4:
secondary model/judge validation when technically feasible

Layer 5:
deterministic citation/provenance checks.

The final system must distinguish:
- supported
- partially supported
- unsupported.

Unsupported output must not be presented as verified fact.

---

# 14. Local LLM architecture

The production architecture must support self-hosted inference.

Design the application behind an LLM service abstraction:

LLMService
- generate()
- structured_generate()
- health()
- model_info()

The first implementation may use:
- Ollama
or
- vLLM

Do not hard-wire the business logic to one provider.

The rest of the application must call the abstraction.

Do not send confidential application data to external AI services.

---

# 15. Embeddings

Use a local embedding service.

Provide:

EmbeddingService
- embed_text()
- embed_batch()
- model_info()
- health()

Embeddings must be generated locally.

Persist the model identifier with the embedding index metadata.

---

# 16. Report Generation

Implement real report generation.

Workflow:

Select report template
→ select organization
→ select period
→ retrieve structured data
→ validate
→ populate schema
→ human review
→ deterministic document rendering.

Use python-docx initially.

Possible report templates:
- Parliamentary Question brief
- Monthly production summary
- Geological information summary
- Document evidence brief
- Executive analytical report.

Do not claim these are official CIL templates unless sourced from an actual official template.

Allow templates to be configured.

---

# 17. Report schema

Every report should have:
- report ID
- report type
- organization
- period
- created by
- created at
- status
- source documents
- fields
- validation status
- reviewer
- approval timestamp
- version.

Report versions must never overwrite historical versions silently.

---

# 18. Topic Identification

Implement:
- document embeddings
- topic clustering
- c-TF-IDF / equivalent topic representation
- topic labels
- topic frequency
- trend analysis across time.

Show:
- topic list
- representative terms
- document counts
- trend
- organizations associated with the topic.

The Word Cloud may be a visualization on top of the topic-identification pipeline.

The topic cloud itself is not the intelligence layer.

---

# 19. Human Verification Queue

Create a real verification interface.

Queue items:
- low confidence OCR
- extraction conflicts
- unsupported AI answer
- source conflict
- suspicious numeric value
- report requiring approval.

Reviewer actions:
- approve
- reject
- correct
- request reprocessing
- add review note.

Every action goes into the audit log.

---

# 20. Audit and traceability

Maintain immutable-style audit records for:
- login
- document upload
- document access
- extraction
- validation
- search
- AI query
- report creation
- report approval
- report download
- correction
- administration changes.

Each audit event must contain:
- actor
- role
- organization
- action
- object type
- object ID
- timestamp
- result
- relevant metadata.

---

# 21. Document integrity

At ingest:
- calculate SHA-256
- store hash.

On retrieval/download where appropriate:
- provide integrity verification.

Version relationships should support:

document A
→ supersedes
document B

rather than deleting history.

---

# 22. Database

Use PostgreSQL.

Use pgvector for embeddings.

Core entities should include at minimum:

organizations
users
roles
documents
document_versions
document_pages
document_sections
chunks
tables
table_rows
figures
extracted_entities
extracted_metrics
validation_issues
embeddings
topics
document_topics
queries
query_evidence
answers
reports
report_versions
verification_tasks
audit_events
processing_jobs
system_settings.

Use proper foreign keys.

Use indexes.

Use timestamps consistently.

Do not put everything into one JSON blob.

Use normalized relational tables for important business entities.

---

# 23. API

Implement versioned API routes.

Suggested structure:

/api/v1/auth
/api/v1/organizations
/api/v1/documents
/api/v1/ingestion
/api/v1/extraction
/api/v1/validation
/api/v1/search
/api/v1/qa
/api/v1/reports
/api/v1/topics
/api/v1/verification
/api/v1/audit
/api/v1/admin
/api/v1/health

Frontend must consume these APIs instead of embedding business logic directly inside pages.

---

# 24. Authentication

Prototype:
- local development authentication

Architecture:
- abstract identity provider.

Production-ready target:
- CIL / CMPDI AD/LDAP integration.

Do not fake an AD integration.

Create an interface so LDAP/AD can be plugged in later.

---

# 25. Organization-level access control

A user must have:
- role
- organization scope
- allowed actions.

Example conceptual rule:

CMPDI HQ user:
may query allowed RI/subsidiary data according to permission policy.

Subsidiary user:
may access only authorized subsidiary scope.

Do not implement access control by hiding UI buttons alone.

Backend must enforce it.

---

# 26. Federation

Do not attempt a real production federation first.

Build a local simulation.

Run:
- node-cmpdi
- node-subsidiary-a
- node-subsidiary-b

Each node has its own logical dataset.

Federation gateway:

query
→ determine relevant nodes
→ send query
→ receive ranked evidence
→ merge results
→ preserve source-node identity
→ return citations.

This must be demonstrable from the UI.

Never claim the simulated nodes are actual CIL systems.

---

# 27. Dashboard metrics

Metrics must be derived from actual system records.

At minimum:

Documents received
Documents processed
Documents failed
Documents awaiting verification
Average processing time
Reports generated
Queries executed
Verified answers
Verification backlog
Extraction confidence
Topic distribution.

For prototype evaluation also calculate:

time saved
automation percentage
extraction accuracy
report generation accuracy

But do not fabricate benchmark values.

Create a benchmark dataset and calculate them.

---

# 28. Demo dataset

Create a clearly labelled synthetic demonstration dataset.

Use realistic document categories such as:
- geological report
- mine information
- production report
- exploration report
- reserve statement
- annexure spreadsheet
- administrative correspondence
- historical report.

Do not copy confidential data.

Do not present synthetic numbers as real CIL numbers.

Include deliberately difficult test documents:
- clean PDF
- scanned PDF
- degraded scan
- spreadsheet
- conflicting-source pair
- unanswerable question.

These should be used to prove the system's validation and refusal behaviour.

---

# 29. Frontend

Preferred stack:

React
+
TypeScript
+
Vite / Next.js as appropriate
+
Tailwind or a restrained enterprise design system
+
Chart library
+
Data table library.

Prioritize:
- accessibility
- keyboard navigation
- clear tables
- filters
- status indicators
- breadcrumbs
- organization context.

Every route must work.

Every important action must have:
- loading state
- success state
- empty state
- error state.

---

# 30. Backend

Preferred initial stack:

Python
+
FastAPI
+
PostgreSQL
+
pgvector
+
Redis if needed
+
background worker.

Suggested worker choices:
- Celery
or
- RQ
or
- a simpler PostgreSQL-backed job model if sufficient for prototype.

Keep processing asynchronous for large files.

---

# 31. Containers

Provide docker-compose for:

frontend
backend
worker
postgres
redis if required
ollama or vLLM where hardware allows.

The entire prototype should start through one documented command.

Example target:

docker compose up --build

No hidden manual configuration should be required beyond documented environment variables.

---

# 32. Local-first design

The application must remain functional without Internet access after the required model packages/assets have been provisioned.

External Internet must not be a runtime dependency for:
- AI generation
- embeddings
- OCR
- document search
- report generation.

---

# 33. UI pages

Implement all of these routes:

/login
/dashboard
/organizations
/organizations/:id
/documents
/documents/:id
/upload
/search
/ask
/ask/history
/reports
/reports/new
/reports/:id
/topics
/verification
/audit
/system
/admin/users
/admin/organizations
/admin/templates
/admin/models

Do not create routes that only render placeholder text.

---

# 34. AI Query UI

The query interface must show:

Question
→ selected organization scope
→ filters
→ retrieval status
→ evidence cards
→ answer
→ citations
→ confidence
→ verification state.

Include a visible "Evidence" area.

The user should be able to open the source page/document.

---

# 35. Document viewer

Implement:
- PDF preview
- page navigation
- extracted text panel
- metadata panel
- entities/metrics panel
- validation issues panel
- provenance.

For the prototype, source page references are essential.

---

# 36. Report Studio

Provide:

Choose template
Choose organization
Choose date range
Choose documents
Preview structured fields
Validate
Generate
Review
Approve
Download.

The generated DOCX must actually be created on the backend.

---

# 37. System Health

Provide a health dashboard for:
- API
- database
- vector store
- OCR
- embedding service
- LLM service
- worker
- storage.

Show:
UP / DEGRADED / DOWN

based on real health checks.

---

# 38. Error handling

Never silently swallow errors.

Backend:
- structured error responses
- correlation/request ID
- logging.

Frontend:
- understandable error message
- retry action where appropriate.

AI:
- explicit fallback/refusal.

---

# 39. Testing requirements

Implement tests for:

Unit:
- hashing
- metadata filtering
- validation
- RRF
- permissions
- report schema.

Integration:
- document upload
- OCR
- extraction
- indexing
- query
- report generation.

End-to-end:
- login
- upload document
- processing
- search
- AI question
- verification
- report generation
- audit.

The application is not "done" if the UI renders but these flows fail.

---

# 40. Browser verification

After each substantial UI phase:

1. Start the app.
2. Open it in the browser.
3. Navigate every newly implemented route.
4. Test forms.
5. Test filters.
6. Test uploads.
7. Inspect console errors.
8. Inspect network failures.
9. Fix problems.
10. Repeat until clean.

Do not merely rely on build success.

---

# 41. Agent strategy

Use specialized sub-agents where helpful.

Suggested roles:

ARCHITECT
- architecture
- database/API contracts
- integration boundaries

BACKEND
- FastAPI
- database
- jobs
- services

FRONTEND
- dashboard
- navigation
- tables
- forms
- document viewer

AI
- OCR
- extraction
- embeddings
- retrieval
- grounding
- local LLM abstraction

REPORTS
- schemas
- templates
- python-docx

SECURITY
- RBAC
- audit
- organization scope

QA
- tests
- browser verification
- regression testing

Do not let multiple agents independently redefine the architecture.

The architecture documents are the source of truth.

---

# 42. Development order

Follow this order.

PHASE 0
Repository inspection and architecture documents

PHASE 1
Database + organizations + authentication + RBAC + audit

PHASE 2
Document upload + storage + ingestion jobs

PHASE 3
PDF/XLSX/DOCX parsing + OCR

PHASE 4
Structured extraction + validation

PHASE 5
Search + pgvector + BM25 + RRF

PHASE 6
Local LLM + grounded Q&A

PHASE 7
Report Studio + DOCX generation

PHASE 8
Topic identification

PHASE 9
Verification queue

PHASE 10
Executive dashboard

PHASE 11
Federated simulated nodes

PHASE 12
E2E testing + demo hardening

Never build the dashboard first and then fake the backend.

---

# 43. Definition of done

The prototype is considered working only when this complete scenario succeeds:

1. User logs in.
2. User sees their authorized organization.
3. User uploads a document.
4. System hashes the file.
5. Processing job appears.
6. OCR/parser processes it.
7. Extracted content is stored.
8. Structured fields are created.
9. Validation runs.
10. Chunks are indexed.
11. User asks a question.
12. Retrieval finds evidence.
13. AI produces an answer grounded in that evidence.
14. UI shows citations.
15. Unsupported question produces a refusal.
16. User generates a report.
17. Structured fields are validated.
18. DOCX is generated.
19. Reviewer approves or corrects.
20. Audit trail records the complete operation.
21. Dashboard updates from actual stored records.

---

# 44. Anti-fake rule

If a feature is not implemented:

DO NOT make it look implemented.

Instead:
- disable it clearly,
- mark it "Prototype / not connected",
- or implement a real local simulation.

Examples:

Do NOT display:
"Connected to CIL AD"

unless it is truly connected.

Display:
"Identity Provider: Local Prototype"

until AD/LDAP is actually integrated.

Do NOT display:
"Live CIL Production Data"

when using seed data.

Display:
"Demonstration Dataset"

instead.

---

# 45. SIH presentation mode

Create an optional `/demo` route.

It should provide a controlled demonstration workspace using clearly labelled synthetic data.

The demo must show:

1. Upload
2. Processing
3. Extraction
4. Validation
5. Search
6. AI Q&A
7. Evidence
8. Report generation
9. Verification
10. Audit
11. Cross-node query.

The demo mode must never change the architecture into a fake presentation layer.

It should exercise the same APIs and business services as the real application.

---

# 46. Documentation

Keep these files updated:

README.md
ARCHITECTURE.md
DATABASE_SCHEMA.md
API_CONTRACT.md
SECURITY_MODEL.md
UI_MAP.md
IMPLEMENTATION_PLAN.md
TEST_PLAN.md
DEMO_SCRIPT.md

Every major architectural decision must be documented.

---

# 47. Final engineering behaviour

Before changing architecture:
- inspect existing code
- inspect existing documentation
- preserve working functionality.

Before installing a dependency:
- check whether an existing dependency already solves the problem.

Before claiming completion:
- run tests
- run the application
- inspect it in browser
- verify core flows.

When an implementation choice is uncertain:
- choose the smallest reversible implementation
- document the assumption
- do not invent organizational facts.

Do not optimize for amount of code.

Optimize for:
1. correctness
2. traceability
3. working end-to-end flow
4. security
5. maintainability
6. demonstrability.

---

# 48. First command to execute

After reading this file, do NOT immediately start coding.

First create:

IMPLEMENTATION_PLAN.md

It must contain:
- architecture
- modules
- dependency graph
- milestones
- database entities
- API boundaries
- frontend routes
- test strategy
- local deployment strategy
- known assumptions
- known limitations.

Then wait for the next implementation task.

