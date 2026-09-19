# SECURITY_MODEL.md
# CIL / CMPDI AI Reporting & Intelligence Platform
# Security, RBAC & Governance Model

## 1. Security Architecture Overview
The platform enforces security, air-gapped data segregation, and multi-tenant organization scoping without reliance on external identity SaaS providers.

```
Request ──> [JWT Bearer Validation] ──> [User Identity & Role Resolution]
                                                   │
                                                   ▼
                                    [Organization Scope Check]
                                                   │
                                                   ▼
                                    [Permission Matrix Check]
                                                   │
                                                   ▼
                                        [Backend Controller]
                                                   │
                                                   ▼
                                      [Audit Event Logged to DB]
```

---

## 2. Authentication & Identity
- **Prototype Mode:** Local prototype authentication engine issuing signed HS256 JWT bearer tokens containing `sub` (user_id), `org_id`, `role`, and `exp`.
- **Production Target Adapter:** Pluggable identity abstraction ready for CIL/CMPDI Active Directory / LDAP authentication via LDAPS (`backend/app/core/auth_ldap.py` interface).
- **Password Hashing:** Passwords stored using PBKDF2 with SHA-256 or bcrypt salts.

---

## 3. Role-Based Access Control (RBAC) Specification

| Role Code | Role Name | Allowed Scopes | Key Permissions |
|---|---|---|---|
| `MINISTRY_OFFICER` | Ministry / Central Reviewer | Global (All Subsidiaries & CMPDI) | `view_dashboard_all`, `query_all`, `view_reports_approved`, `view_audit_all` (Read-Only) |
| `CMPDI_HQ_OFFICER` | CMPDI HQ Officer | CMPDI HQ + All Regional Institutes | `ingest_doc`, `extract_all`, `query_all`, `generate_report`, `approve_report`, `view_audit_org` |
| `RI_ANALYST` | Regional Institute Analyst | Assigned RI + Associated Subsidiary | `ingest_doc_ri`, `view_doc_ri`, `query_ri`, `generate_report_ri`, `request_validation` |
| `SUBSIDIARY_ANALYST` | Subsidiary Analyst | Assigned Subsidiary (e.g. SECL, ECL) | `ingest_doc_sub`, `view_doc_sub`, `query_sub`, `generate_report_sub` |
| `VERIFICATION_OFFICER` | Verification Officer | Assigned Organization or Cross-Org Queue | `view_verification_queue`, `approve_verification`, `reject_verification`, `edit_field_value` |
| `SYSTEM_ADMIN` | System Administrator | System-Wide | `manage_users`, `manage_roles`, `manage_orgs`, `manage_rules`, `view_system_health` |

---

## 4. Organization Scoping Enforcement
Authorization checks are enforced server-side via FastAPI dependency injection:
- Every document, chunk, and report has an explicit `organization_id`.
- When an analyst from `SECL` queries documents, the backend queries automatically inject `WHERE organization_id IN (:secl_org_ids)`.
- Cross-organization queries by lower-tier analysts are rejected with HTTP `403 Forbidden`.
- Ministry and CMPDI HQ Officers are granted cross-boundary visibility according to configured policy.

---

## 5. Cryptographic Provenance & Document Integrity
1. **SHA-256 Hashing:** Calculated immediately on file upload. The hash is saved to the `documents` table and validated whenever the file is retrieved.
2. **Immutability of Versions:** If an updated version of a document is uploaded, it creates a new `document_versions` row linking back to the original via `supersedes_id`. Past versions are never deleted or silently modified.
3. **Report Snapshot Hashing:** When a report is approved, a frozen JSON snapshot of all fields and citations is saved alongside the generated `.docx` file hash.

---

## 6. Immutable Audit Trail
Every security-critical operation writes an immutable entry into `audit_events`:
- **Captured Fields:** `id`, `actor_id`, `actor_name`, `role_code`, `organization_id`, `action`, `object_type`, `object_id`, `sha256_hash`, `ip_address`, `details` (JSONB), `created_at`.
- **Audited Events:**
  - `AUTH_LOGIN`, `AUTH_LOGOUT`, `AUTH_FAILED`
  - `DOC_UPLOAD`, `DOC_PARSED`, `DOC_DOWNLOADED`
  - `FIELD_EXTRACTED`, `FIELD_VALIDATED`
  - `VERIFICATION_APPROVED`, `VERIFICATION_REJECTED`, `VERIFICATION_CORRECTED`
  - `QA_QUERY_EXECUTED`, `QA_ANSWER_GENERATED`, `QA_REFUSAL`
  - `REPORT_GENERATED`, `REPORT_APPROVED`, `REPORT_DOWNLOADED`
  - `ADMIN_CONFIG_CHANGED`
