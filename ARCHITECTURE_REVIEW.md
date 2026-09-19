# ARCHITECTURE_REVIEW.md
# KOYLA: CIL / CMPDI AI Reporting & Intelligence Platform
# Engineering Reconciliation and Architecture Review

## 1. Executive summary
This document serves as the formal reconciliation and engineering review corresponding to Implementation Prompt 1. The eight core engineering specifications (`IMPLEMENTATION_PLAN.md`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `API_CONTRACT.md`, `UI_MAP.md`, `SECURITY_MODEL.md`, `TEST_PLAN.md`, and `DEMO_SCRIPT.md`) were audited against the Master Prompt constraints. The review confirmed the integrity of the local-first, air-gapped architecture, the strict enforcement of deterministic verification over unconstrained AI generation, and the mapping of all SIH 26023 deliverables. Minor omissions in the database schema and API contracts were resolved to ensure full coverage.

## 2. What is already correct
- **Architecture Continuity:** The end-to-end flow from ingestion to DOCX report generation is logically connected.
- **SIH Requirements:** All three product modules (Report Generation, Topic/Word Cloud, AI Query & Response) are supported with verifiable routes.
- **Security & RBAC:** Server-side organization scoping, JWT authentication, and configurable roles (Ministry Officer, CMPDI HQ, RI Analyst, etc.) are correctly mapped. Immutable audit logging is present.
- **On-Premise Constraints:** The design relies exclusively on local adapters (PaddleOCR, PyMuPDF, sentence-transformers, pgvector, Ollama/vLLM) with zero runtime dependencies on OpenAI, Anthropic, Gemini, or external hosted services.
- **AI / RAG Defences:** The extract-then-compose pipeline and explicit deterministic refusal boundaries correctly prevent unsupported prose hallucination.
- **Report Generation:** Generates real DOCX files from validated database records via `python-docx`, not via direct LLM text streaming.
- **Institutional Model:** CIL, CMPDI, Regional Institutes, and Subsidiaries are structured as configurable database rows, without hardcoding business rules.

## 3. Concrete inconsistencies found
1. **Database Schema:** `report_versions` table was required by the Master Prompt but was missing from `DATABASE_SCHEMA.md`.
2. **API Contract:** Endpoints for Topic Analytics (`/api/v1/topics`) and Administration (`/api/v1/admin`) were missing in `API_CONTRACT.md` despite being necessary for the frontend routes.
3. **Prototype vs. Production Mapping:** The explicit categorization of components into "IMPLEMENTED IN PROTOTYPE", "PROTOTYPE SIMULATION", "FUTURE PRODUCTION INTEGRATION", and "ROADMAP" was not explicitly formalized in the architecture document.

## 4. Changes made
- **DATABASE_SCHEMA.md:** Added the `report_versions` table definition and linked it in the Entity-Relationship (ER) diagram.
- **API_CONTRACT.md:** Added sections for Topic Analytics & Word Cloud (`/api/v1/topics`) and Administration (`/api/v1/admin`) to ensure 100% coverage of the frontend `UI_MAP.md`. Corrected the section numbering.
- **ARCHITECTURE.md:** Appended Section 7 to explicitly provide the "Prototype vs Production Implementation Mapping" matrix as mandated.

## 5. Remaining architectural risks
- **OCR Accuracy on Degraded Scans:** Open-source PaddleOCR/Tesseract accuracy varies on highly degraded historical mining scans; this is mitigated by the Human Verification Queue but remains an operational risk.
- **Local LLM Hardware Requirements:** Running a 7B/8B model (Llama-3 or Mistral) locally requires 8GB-12GB VRAM; deployments without GPUs will require the fallback deterministic extractive pipeline, which has lower semantic comprehension capabilities.
- **Cross-document Reconciliation Complexity:** Overlapping reports with differing granularities (e.g., monthly vs. quarterly) may generate a high volume of validation conflicts, stressing the Human Verification Queue.

## 6. Missing dependencies/interfaces
- No major internal dependencies are missing.
- **Future Interface Stubs:** The Active Directory/LDAP integration and enterprise SIEM export are stubbed out but lack specific internal CIL API payload definitions (which cannot be invented during the prototype phase).

## 7. Prototype limitations
- Simulated federated nodes run locally rather than across physical geographic networks.
- Identity management relies on local JWT and synthetic prototype user accounts instead of a live AD bind.
- The document corpus is seeded with synthetic/demo records (`is_demo_data=true`) as real production data is restricted.

## 8. Production-only requirements
- Integration with CIL/CMPDI Active Directory via LDAPS.
- High Availability (HA) deployment for PostgreSQL and Redis.
- Integration of the Audit Log stream with centralized enterprise SIEM tools (e.g., Splunk).
- Dedicated GPU inference nodes for scalable LLM / Embedding batch processing.

## 9. Final dependency graph
```
[Frontend (React/Vite)] ──> [FastAPI Gateway]
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
        [Auth / RBAC]     [Ingest/Parsers]   [Local AI Engine]
                 │               │               │
                 ▼               ▼               ▼
      [PostgreSQL / SQLite (Metadata, Embeddings, Extracted Fields)]
                 │               │               │
                 ▼               ▼               ▼
          [Audit Log]    [Report Studio]  [Federation Simulator]
```

## 10. Readiness assessment for actual implementation
All architectural layers (DB, API, Security, Local AI pipelines, UI routes) are logically consistent, structurally sound, and fully compliant with the government-grade air-gapped constraint. The core specifications now provide an exact blueprint for Phase 1.

## IMPLEMENTATION READINESS
READY
