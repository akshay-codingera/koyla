# API_CONTRACT.md
# CIL / CMPDI AI Reporting & Intelligence Platform
# REST API Specification (FastAPI / OpenAPI v3)

All endpoints are versioned under `/api/v1` and return standardized JSON envelopes.

---

## 1. Authentication & Identity (`/api/v1/auth`)

### `POST /api/v1/auth/login`
- **Request Body:**
  ```json
  {
    "username": "ri1_analyst",
    "password": "ValidPassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": "u-101",
      "username": "ri1_analyst",
      "full_name": "RI-I Lead Analyst",
      "role": "RI_ANALYST",
      "organization": {
        "id": "org-ri1",
        "code": "RI_1",
        "name": "Regional Institute - I (Asansol)",
        "org_type": "REGIONAL_INSTITUTE"
      }
    }
  }
  ```

### `GET /api/v1/auth/me`
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):** Current user profile with permissions and active organization context.

---

## 2. Organization Network (`/api/v1/organizations`)

### `GET /api/v1/organizations`
- **Query Params:** `parent_id` (optional), `org_type` (optional)
- **Response (200 OK):** Hierarchy array with CIL $\rightarrow$ CMPDI $\rightarrow$ RIs $\rightarrow$ Subsidiaries $\rightarrow$ Areas $\rightarrow$ Mines.

### `GET /api/v1/organizations/{id}/metrics`
- **Response (200 OK):** Calculated statistics (document count, verified metrics, extraction accuracy, verification backlog).

---

## 3. Documents & Ingestion (`/api/v1/documents`)

### `POST /api/v1/documents/upload`
- **Content-Type:** `multipart/form-data`
- **Form Fields:** `file` (binary), `organization_id` (string), `document_type` (string), `source_tier` (string: `TIER_A`|`TIER_B`|`TIER_C`)
- **Response (201 Created):**
  ```json
  {
    "document_id": "doc-501",
    "title": "SECL_Gevra_OCP_Monthly_Production_May2024.pdf",
    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "status": "QUEUED",
    "job_id": "job-801"
  }
  ```

### `GET /api/v1/documents`
- **Query Params:** `organization_id`, `document_type`, `source_tier`, `status`, `page`, `page_size`
- **Response (200 OK):** Paginated documents list with trust badges and processing status.

### `GET /api/v1/documents/{id}`
- **Response (200 OK):** Complete document record including pages, OCR confidence, detected tables, extracted fields, and validation issues.

---

## 3.5 Structured Extraction, Validation & Reconciliation

### `POST /api/v1/extraction/run/{document_id}`
- **Response (200 OK):** `ExtractionRunResponse`
  ```json
  {
    "id": "run-uuid",
    "document_id": "doc-uuid",
    "status": "COMPLETED",
    "fields_extracted_count": 8,
    "validation_issues_count": 1,
    "conflicts_count": 0,
    "started_at": "2026-09-18T00:00:00Z",
    "completed_at": "2026-09-18T00:00:01Z"
  }
  ```

### `GET /api/v1/extraction/documents/{document_id}/fields`
- **Response (200 OK):** List of `ExtractedFieldResponse` with field-level provenance, measurement units, confidence levels, validation status, and validation rule results.

### `GET /api/v1/validation/issues`
- **Query Params:** `document_id`, `severity`, `status`
- **Response (200 OK):** List of `ValidationResultResponse` items.

### `GET /api/v1/reconciliation/conflicts`
- **Response (200 OK):** List of `ReconciliationGroupResponse` items flagging multi-document discrepancies within the same entity and fiscal period.

### `POST /api/v1/reconciliation/groups/{group_id}/resolve`
- **Request Body:** `{"resolved_value": "46.20 MT", "selected_candidate_id": "cand-uuid"}`
- **Response (200 OK):** Updated reconciliation group.

---

## 4. Hybrid Search & Evidence Retrieval (`/api/v1/search`)

### `POST /api/v1/search/query`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "query": "geological exploration drilling coal seam",
    "mode": "HYBRID",
    "organization_id": "org-uuid (optional)",
    "fiscal_year": "FY2024-25 (optional)",
    "document_type": "GEOLOGICAL_REPORT (optional)",
    "source_tier": "TIER_A (optional)",
    "period_start": "2024-04-01T00:00:00 (optional)",
    "period_end": "2025-03-31T23:59:59 (optional)",
    "limit": 10,
    "enable_reranker": true
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "query": "geological exploration drilling coal seam",
    "mode": "HYBRID",
    "results": [
      {
        "result_id": "res-uuid",
        "chunk_id": "chunk-uuid",
        "document_id": "doc-uuid",
        "document_version_id": "ver-uuid",
        "organization_id": "org-uuid",
        "organization_name": "Bharat Coking Coal Limited",
        "title": "BCCL Geological Exploration Report 2024",
        "document_type": "GEOLOGICAL_REPORT",
        "source_tier": "TIER_A",
        "fiscal_year": "FY2024-25",
        "page_number": 1,
        "chunk_type": "TEXT",
        "section_heading": "1. Geological Overview",
        "source_text": "BHARAT COKING COAL LIMITED...",
        "retrieval_method": "HYBRID_RRF",
        "keyword_rank": 3,
        "keyword_score": 0.0825,
        "dense_rank": 1,
        "dense_score": 0.8412,
        "rrf_score": 0.032266,
        "reranker_score": null,
        "final_rank": 1,
        "provenance": {
          "document_id": "doc-uuid",
          "document_title": "BCCL Geological Exploration Report 2024",
          "version_id": "ver-uuid",
          "page_number": 1,
          "chunk_id": "chunk-uuid",
          "chunk_type": "TEXT",
          "section_heading": "1. Geological Overview",
          "table": null
        }
      }
    ],
    "trace": {
      "trace_id": "trace-uuid",
      "query": "geological exploration drilling coal seam",
      "normalized_query": {
        "original_query": "geological exploration drilling coal seam",
        "clean_query": "geological exploration drilling coal seam",
        "entities": [],
        "metrics": [],
        "fiscal_years": [],
        "period_start": null,
        "period_end": null,
        "topics": ["drilling", "exploration"],
        "suggested_filters": {}
      },
      "applied_filters": {},
      "search_mode": "HYBRID",
      "keyword_candidate_count": 30,
      "dense_candidate_count": 30,
      "fused_candidate_count": 30,
      "final_result_count": 10,
      "reranker_status": "RERANKER_UNAVAILABLE",
      "timings_ms": {
        "query_normalization": 0.22,
        "keyword_search": 16.23,
        "dense_search": 4.31,
        "rrf_fusion": 0.06,
        "reranking": 0.0,
        "total": 22.21
      }
    }
  }
  ```

### `GET /api/v1/search/status`
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):**
  ```json
  {
    "total_chunks": 278,
    "total_embeddings": 269,
    "distinct_embedded_chunks": 269,
    "coverage_pct": 96.8,
    "provider_info": {
      "provider": "DeterministicLocalEmbeddingProvider",
      "model_name": "all-MiniLM-L6-v2",
      "dimension": 384,
      "version": "1.0.0",
      "is_local": true,
      "device": "cpu",
      "normalized": true
    },
    "health": {
      "status": "UP",
      "provider": "DeterministicLocalEmbeddingProvider",
      "model_name": "all-MiniLM-L6-v2",
      "dimension": 384,
      "version": "1.0.0",
      "available": true
    }
  }
  ```

### `POST /api/v1/search/index/{document_id}`
- **Headers:** `Authorization: Bearer <token>`
- **Query Params:** `force=false`
- **Response (200 OK):** `{"status": "INDEXED", "document_id": "...", "indexed_chunks": 12}`

### `POST /api/v1/search/reindex`
- **Headers:** `Authorization: Bearer <token>` (Admin only)
- **Query Params:** `force=false`
- **Response (200 OK):** `{"status": "SUCCESS", "documents_processed": 14, "embeddings_created": 269, "errors": []}`

### `POST /api/v1/qa/ask`
- **Request Body:**
  ```json
  {
    "question": "What was the total coal production and stripping ratio for Dipka OCP in FY 2023-24?",
    "organization_scope": "org-secl",
    "filters": {
      "subsidiary_code": "SECL"
    }
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "query_id": "q-901",
    "question": "What was the total coal production and stripping ratio for Dipka OCP in FY 2023-24?",
    "answer": "For Dipka Open Cast Project (SECL) in FY 2023-24, total coal production was 38.25 Million Tonnes with an average stripping ratio of 1.42 m³/tonne [Doc #doc-410, p. 3].",
    "verification_status": "SUPPORTED",
    "confidence_score": 0.94,
    "citations": [
      {
        "document_id": "doc-410",
        "document_title": "SECL_Dipka_Annual_Review_2023-24.pdf",
        "page_number": 3,
        "excerpt": "Dipka OCP produced 38.25 MT of raw coal against target with a recorded stripping ratio of 1.42.",
        "score": 0.89
      }
    ]
  }
  ```

---

## 5. Report Studio (`/api/v1/reports`)

### `GET /api/v1/reports/templates`
- **Response (200 OK):** List of registered report schemas (Parliamentary brief, Monthly production, Geological exploration digest).

### `POST /api/v1/reports/generate`
- **Request Body:**
  ```json
  {
    "template_id": "tmpl-prod-summary",
    "organization_id": "org-secl",
    "title": "Monthly Production Digest - SECL Korba Area",
    "period": "May 2024"
  }
  ```
- **Response (201 Created):** Generated report metadata, validation status, frozen JSON schema, and DOCX download URL (`/api/v1/reports/{id}/download`).

---

## 6. Verification Queue & Audit (`/api/v1/verification` & `/api/v1/governance`)

### `GET /api/v1/verification/queue`
- **Query Params:** `status` (`PENDING`), `task_type`
- **Response (200 OK):** Triage items with source snippet, conflicting values, and confidence scores.

### `POST /api/v1/verification/tasks/{id}/action`
- **Request Body:**
  ```json
  {
    "action": "APPROVE",
    "corrected_value": null,
    "notes": "Verified against original signed survey sheet"
  }
  ```

### `GET /api/v1/governance/audit-logs`
- **Response (200 OK):** Immutable audit events including actor, role, action, object ID, hash, and timestamp.
---

## 8. Topic Intelligence & Temporal Analytics (`/api/v1/topics`)

### `POST /api/v1/topics/analyze`
- **Request Body:**
  ```json
  {
    "organization_id": "org-ecl",
    "corpus_filters": {
      "fiscal_year": "FY2024-25",
      "document_type": "MINING_PLAN"
    },
    "force_refresh": false
  }
  ```
- **Response (200 OK):** `TopicAnalysisResponse`
  - Returns cached analysis if SHA-256 `corpus_hash` matches existing completed run, or initiates deterministic clustering run.
  - Envelope includes: `id`, `organization_id`, `corpus_hash`, `document_count`, `chunk_count`, `quality_metrics` (coherence, silhouette), and array of discovered `topics` with `label`, `prevalence_pct`, `semantic_topic_coherence`, diagnostic `terms`, and grounded `evidence`.

### `GET /api/v1/topics/history`
- **Query Params:** `organization_id` (optional), `limit` (default 20)
- **Response (200 OK):** List of past analytical runs with runtime statistics and corpus volumes.

### `GET /api/v1/topics/{analysis_id}`
- **Response (200 OK):** Complete analysis dossier including all topics, vocabulary term weights, and physical chunk evidence citations.

### `GET /api/v1/topics/{analysis_id}/trends`
- **Response (200 OK):** Period prevalence trends across historical fiscal years with explicit sample sizes `(topic_docs / period_docs)`, $\Delta_{abs}$, $\Delta_{pp}$, $g_{rel}$, and trend status badges (`GROWING`, `DECLINING`, `STABLE`, `EMERGING`, `INSUFFICIENT_HISTORY`).

### `GET /api/v1/topics/{analysis_id}/trends/{topic_id}`
- **Response (200 OK):** Granular period progression for a single topic.

### `GET /api/v1/topics/{analysis_id}/comparison`
- **Query Params:** `dimension_type` (`SUBSIDIARY`, `MINE`, `BLOCK`, `DOCUMENT_TYPE`), `dimension_a`, `dimension_b`
- **Response (200 OK):** Side-by-side comparative distribution, share difference, and topic compositions across specified entities.
- **Convenience Sub-Routes:**
  - `GET /api/v1/topics/{analysis_id}/comparison/organizations`
  - `GET /api/v1/topics/{analysis_id}/comparison/mines`
  - `GET /api/v1/topics/{analysis_id}/comparison/blocks`
  - `GET /api/v1/topics/{analysis_id}/comparison/document-types`

### `GET /api/v1/topics/{analysis_id}/term-evolution`
- **Response (200 OK):** Longitudinal vocabulary tracking showing term frequency and weight movements across fiscal years.

### `POST /api/v1/topics/{analysis_id}/summary`
- **Response (200 OK):** Local LLM-generated empirical factual summary (bulleted observable shifts, zero speculative causal claims, deterministic fallback).

### `POST /api/v1/topics/{analysis_id}/add-to-report`
- **Request Body:**
  ```json
  {
    "report_id": "rep-uuid-1234",
    "topic_ids": ["topic-uuid-1", "topic-uuid-2"]
  }
  ```
- **Response (200 OK):** Attaches serialized analytical topic dossier as an optional annexure (`requirement_type="OPTIONAL"`) in Report Studio without disrupting official statutory chapter numbering.

---

## 9. Administration (`/api/v1/admin`)

### `GET /api/v1/admin/users`
- **Response (200 OK):** List of all users and their role assignments (System Admin only).

### `GET /api/v1/admin/organizations`
- **Response (200 OK):** Configurable organization nodes and reporting policies.
---

## 10. System Health & Operational Telemetry (`/api/v1/system/health`)

### `GET /api/v1/system/health`
- **Description:** Real-time capability check executing genuine operational queries across all 9 core subsystems. No fake green statuses.
- **Response (200 OK):**
  ```json
  {
    "status": "UP",
    "timestamp": "2026-09-20T04:00:00.000000",
    "platform": "CIL/CMPDI Reporting Intelligence Platform",
    "environment": "airgapped-local",
    "database_type": "PostgreSQL",
    "pgvector_enabled": true,
    "services": {
      "backend": "UP",
      "api": "UP",
      "database": "UP",
      "vector_store": "UP",
      "ocr_engine": "UP",
      "embedding_service": "UP",
      "llm_service": "OFFLINE",
      "topic_engine": "UP",
      "temporal_analytics": "UP",
      "report_engine": "UP"
    },
    "details": {
      "database": "PostgreSQL live connection OK (SELECT 1)",
      "vector_store": "pgvector live operator check OK (<->)",
      "ocr_engine": "Local Tesseract/PyMuPDF operational",
      "embedding_service": "BAAI/bge-small-en-v1.5 local weights loaded",
      "llm_service": "Local daemon on port 11434 unreachable (offline fallback active)"
    }
  }
  ```

