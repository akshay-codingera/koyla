# UI_MAP.md
# CIL / CMPDI AI Reporting & Intelligence Platform
# User Interface Route & Navigation Map

## 1. Visual & Interaction Design Principles
- **Aesthetic:** Serious government-sector enterprise system. Clean dark coal / graphite structural headers and sidebars (`#1a1f2c`), cool slate surfaces (`#f8fafc`), formal borders, restrained earthy amber / emerald accents for statuses.
- **No Consumer-AI Clichés:** No neon gradients, no holograms, no decorative bot avatars, no glassmorphic marketing cards.
- **Information Density:** Clean, high-density data tables, breadcrumb navigation, persistent organization switcher in top navbar, visible confidence chips, and slide-over evidence panels.
- **No Dead Controls:** Every button, tab, and filter has concrete API backing with four mandatory states:
  1. `Loading` (subtle pulse or spinner)
  2. `Success` (updated table or badge)
  3. `Empty` (instructional guidance)
  4. `Error` (descriptive error with retry button)

---

## 2. Route Directory & Component Matrix

| Route | Page Title | Primary Component | Key Capabilities |
|---|---|---|---|
| `/login` | Secure Portal Login | `LoginPage` | Local prototype credential selection, role preview, JWT storage |
| `/dashboard` | Executive Dashboard | `DashboardPage` | Calculated KPIs (docs ingested, extraction accuracy, verification backlog), trend charts, subsidiary distribution |
| `/organization` | Organization Explorer & Federation | `OrganizationPage` | Interactive tree (CIL $\rightarrow$ CMPDI $\rightarrow$ 7 RIs $\rightarrow$ Subsidiaries $\rightarrow$ Mines) + 3-Node Federation simulator view |
| `/documents` | Document Intelligence Repository | `DocumentsPage` | Filterable repository, status badges, trust tier chips, SHA-256 links |
| `/documents/ingest` | Document Ingestion Hub | `IngestPage` | Drag-and-drop file upload, MIME & SHA-256 detection, tier selector |
| `/documents/:id` | Document Inspection & Provenance | `DocumentDetailPage` | Multi-tab viewer (PDF/Image preview, raw text, detected tables, extracted fields, validation conflicts, audit log) |
| `/knowledge` | Knowledge Explorer & Hybrid Search | `KnowledgeSearchPage` | Hybrid BM25 + Vector query, metadata filters, RRF score breakdown |
| `/query` | Grounded AI Q&A Console | `QueryConsolePage` | Extract-then-compose Q&A, evidence cards, citations drawer, refusal demonstration |
| `/reports` | Report Library | `ReportsListPage` | Filter by period/subsidiary, status badges (Draft, Approved), DOCX download |
| `/reports/new` | Report Generation Studio | `ReportBuilderPage` | Template picker, automated schema population, structured validation preview |
| `/reports/:id` | Report Inspection & Verification | `ReportDetailPage` | Field-level provenance review, approval/rejection actions, real DOCX download |
| `/topics` | Topic Identification & Word Cloud | `TopicsPage` | c-TF-IDF keyword clusters, temporal trend graph, interactive domain Word Cloud |
| `/verification` | Human Verification Center | `VerificationQueuePage` | Tri-pane triage: Document snippet, extracted value, approval/correction actions |
| `/governance` | Governance & Audit Ledger | `GovernancePage` | Immutable audit trail, cryptographic SHA-256 verification tool |
| `/administration` | Platform Administration | `AdminPage` | Users, roles, organization nodes, trust tier definitions, validation rules |
| `/system` | System Health & Services | `SystemHealthPage` | Real-time status cards: API, Database, Vector Store, OCR, LLM service, storage |
| `/demo` | SIH Presentation Workspace | `DemoShowcasePage` | Guided demonstration path highlighting the 11 key SIH criteria with pre-loaded test cases |

---

## 3. Persistent Layout Elements
1. **Top Navigation Bar:**
   - CIL / CMPDI official emblem styling and portal title: *"CIL / CMPDI Reporting Intelligence Platform"*
   - Active Organization Switcher (drop-down filter changing user's active scoping context)
   - Prominent dataset indicator badge: `[DEMO DATASET / PROTOTYPE]`
   - Current User profile chip & Logout button
2. **Left Navigation Sidebar:**
   - Core Operations: Executive Dashboard, Document Repository, Ingest Document, Knowledge Search, AI Query Console
   - Reporting & Intelligence: Report Studio, Topic Trends & Word Cloud
   - Governance & Quality: Verification Queue, Audit & Provenance, Organization Network
   - System: Administration, System Health, Presentation Demo
