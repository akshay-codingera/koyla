# PHASE 10.5 — KOYLA EVIDENCE INTELLIGENCE CAPABILITY AUDIT
**Date:** September 30, 2026  
**System:** CIL / CMPDI Reporting Intelligence Platform (Koyla)  
**Environment:** Local Enterprise Container Runtime (Docker: `koyla-backend-1`, PostgreSQL 16 + `pgvector`)  
**Audit Type:** Empirical Capabilities Audit (Live Loaded Corpus & Real Execution Engine)

---

## EXECUTIVE SUMMARY

### Can Koyla move from Search → Evidence → Conflict → Lineage → Defensible Answer?

# **PARTIALLY**

```text
FINDING TEXT                      [PASS]   (Hybrid BM25 + BAAI/bge-small-en-v1.5 + RRF + Cross-Encoder)
      ↓
UNDERSTANDING ENTITIES            [PARTIAL](Regex normalizer, but NO cross-document entity coreference resolver)
      ↓
LINKING ATTRIBUTES                [PARTIAL](Links field to doc/page, but table multi-entity rows cross-pollinate)
      ↓
TRACKING PROVENANCE               [PASS]   (Every chunk, field, visual asset, table row has doc/page/box provenance)
      ↓
DETECTING CONFLICTS               [PASS]   (Reconciliation groups flag >1% discrepancies & exclude from aggregations)
      ↓
REASONING OVER EVIDENCE           [PARTIAL](Deterministic arithmetic & SQL agg work; LLM narrative reasoning fails)
      ↓
CALCULATING WITH LINEAGE          [PASS]   (Python Arithmetic Engine & SQL engine output operand/formula lineage)
      ↓
DISTINGUISHING FACT/CALC/INFERENCE[PARTIAL](Structured prompt separates sections; LLM fails to self-partition)
      ↓
PRODUCING A DEFENSIBLE ANSWER     [PARTIAL](PASS for structured SQL/YoY queries; FAIL for open-ended LLM synthesis)
```

### The Honest Empirical Boundary
Koyla is **substantially ahead of generic RAG chatbots** in its deterministic data layer:
1. It possesses a **deterministic Python Arithmetic Engine** (`arithmetic_engine.py`) that computes year-over-year deltas, percentages, and stripping ratios directly in code with full operand lineage, eliminating mathematical hallucinations.
2. It possesses a **deterministic Multi-Document SQL Aggregation Engine** (`structured_lookup.py`) that executes `SUM`, `AVG`, `MIN`, `MAX`, and `COUNT` across authoritative `ExtractedField` records with strict tenant isolation, excluding unverified proposals and unresolved conflicts.
3. It possesses a **Reconciliation Engine** (`reconciliation.py`) and **Statutory 4-Eyes Verification Engine** (`statutory_verification.py`) that track discrepancies and prevent maker self-approval with immutable audit logs.
4. It possesses **Multimodal Provenance** that links citations not just to documents, but to specific page numbers, table cells/headers, and visual bounding boxes (`visual_provenance`).
5. It possesses an **Honest Refusal Floor**: when topical similarity or verified evidence is missing, it refuses with `"Insufficient verified evidence found in the selected knowledge base."`

**HOWEVER, Koyla breaks down when moving from structured data into language-model reasoning:**
1. **Context Overflow & Small-Model Failure**: The local `SmolLM2-135M-Instruct` model lacks the capacity to reason across dozens of evidence blocks. When presented with enterprise-scale evidence (e.g. 500+ facts across 61 organizations), prompt length exceeds the 8,192 token window (10,089+ tokens observed), triggering repetition loops and hallucinatory synthesis.
2. **No Relational Tuple Binding in Grounding Check**: The `GroundingChecker` validates numbers by checking set membership against a flattened evidence text string. If a number appears anywhere in the retrieved corpus (even for an unrelated mine or seam), the sentence is marked "supported".
3. **No Cross-Document Entity Coreference**: There is no alias resolution graph. Koyla cannot determine whether "Seam IV" at Moonidih is the same geological formation as "Seam IV" in Jharia Block II, or merely a homonymous identifier.
4. **Source Authority Hierarchy is Not Implemented**: Koyla has source tiers (`TIER_A`, `TIER_B`, `TIER_C`), but lacks a deterministic precedence matrix (e.g., Approved Mining Plan > Preliminary Exploration > Draft Note). When asked which source is authoritative, the LLM hallucinates an arbitrary justification.

---

## 1. SYSTEM BASELINE & INVENTORY (TEST 0)

The audit was executed against the active, live Koyla container database (`koyla-backend-1` / PostgreSQL 16):

### 1.1 Database Counts
| Component | Actual Count in DB | Implementation Model / Table |
| :--- | :---: | :--- |
| **Organizations** | 61 | `organizations` (Hierarchical CIL $\rightarrow$ CMPDI/Subsidiaries) |
| **Total Registered Documents** | 4,032 | `documents` |
| **Completed / Indexed Documents** | 2,948 completed, 775 processed | `documents.status` |
| **Document Pages** | 812 | `document_pages` |
| **Indexed Chunks (Text & Visual)** | 4,924 | `chunks` (pgvector 384-dim embeddings) |
| **Visual Assets (Diagrams/Sections)** | 116 | `visual_assets` (with OCR/captions & bounding boxes) |
| **Extracted Tables** | 903 | `tables` |
| **Extracted Table Rows** | 3,199 | `table_rows` |
| **Extracted Structured Fields** | 5,499 | `extracted_fields` (with confidence & verification) |
| **Borehole Strata Sequence Records** | 0 (Schema active; seed data pending) | `borehole_strata` |
| **Reconciliation Conflict Groups** | 257 | `reconciliation_groups` |
| **Reconciliation Candidates** | 1,598 | `reconciliation_candidates` |
| **Verification Tasks** | 358 | `verification_tasks` |
| **Statutory 4-Eyes Verifications** | Verified in P1-3 test suite | `statutory_reserve_verifications` |
| **Historical Queries Logged** | 493 | `query_records` |
| **Historical Answers Logged** | 493 | `answer_records` |
| **Audit Events Logged** | 3,142 | `audit_events` (Immutable ledger) |

### 1.2 System & Model Configuration
* **LLM Engine**: `SmolLM2-135M-Instruct` running locally via HuggingFace `transformers` in PyTorch (`local_transformers.py`). Auto-selected fallback: deterministic structured synthesis.
* **Embedding Model**: `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors, PyTorch local sentence-transformers).
* **Lexical Search**: PostgreSQL Full-Text Search (`to_tsvector('english', ...)`) with phrase matching and frequency ranking (`keyword_search.py`).
* **Dense Vector Search**: PostgreSQL `pgvector` cosine similarity (`<=>`) with HNSW indexing (`dense_search.py`).
* **Hybrid Fusion**: Reciprocal Rank Fusion ($k=60$) combining lexical and dense scores (`fusion.py`).
* **Cross-Encoder Reranker**: `cross-encoder/ms-marco-TinyBERT-L-2-v2` (`reranker.py`).
* **Deterministic Calculation Engine**: Active (`arithmetic_engine.py` for YoY, deltas, percentages, stripping ratio).
* **Deterministic Aggregation Engine**: Active (`structured_lookup.py` for SQL `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`).
* **Conflict Detection Engine**: Active (`reconciliation.py` flags numerical divergence $>1\%$ among identical entities/periods).
* **Source Authority Hierarchy**: **NOT IMPLEMENTED** (Tiers exist, but no precedence resolution logic).
* **Entity Coreference / Alias Resolution**: **NOT IMPLEMENTED** (Regex normalizer exists; no relational alias graph).
* **Calculation Lineage**: **ACTIVE** for deterministic calculations; **NOT IMPLEMENTED** for freeform LLM generation.

---

## 2. CORPUS USED IN AUDIT

The audit exercised actual domain documents loaded into Koyla, including:
1. `Geological Exploration Report Seam IV (Phase 9 Visual Test)` (CMPDI HQ, Doc ID: `57dde557...`)
2. `Geological Exploration Report Seam IV` (CIL Corporate, Doc ID: `e58274d0...`)
3. `BCCL Geological Exploration Report 2024` (BCCL, Doc ID: `e2254f80...`)
4. `Moonidih Geological Survey Report FY2024-25` (BCCL, Doc ID: `e9318624...`)
5. `bccl_moonidih_strata_metrics.csv` (BCCL Annexure, Doc ID: `3cecdb1b...`)
6. `ECL Jhanjra Seam Correlation Report FY2023-24` & `FY2024-25` (ECL, Doc IDs: `96e9c2e8...`)
7. `ECL Coal Seam Deposition Analysis FY2024-25` (ECL, Doc ID: `26bbd6b0...`)
8. `Annual Production Summary for Rajmahal Opencast Mine FY2023-24` & `FY2024-25` (ECL)
9. `Rajmahal Open Cast Production Summary FY2023-24` (ECL, Doc ID: `9d2a5272...`)
10. `Gevra OC Annual Operational Review 2023-24` & `secl_gevra_production_fy24.xlsx` (SECL)
11. `MoC Statutory Guidelines Test Upload` (MoC / CIL, Doc ID: `79112335...`, 83 pages)
12. `Conflict Report Alpha` & `Conflict Report Beta` (Synthetic multi-source conflict benchmark pair)

---

## 3. AUDIT TEST RESULTS (Q1 – Q14)

All questions were submitted directly to the live API/QA pipeline (`qa_service.answer_query`) using an authenticated enterprise administrator user (`sysadmin`).

```text
================================================================================
TEST 1 — CONTEXT UNDERSTANDING (Q1 & Q2)
================================================================================
```

### Q1: "Find all references to Seam IV. Group them by mine, report, year, and document type."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 12 | **Citations Returned**: 11 | **Latency**: 21.37s
* **Actual System Answer**:
  > *"Based on the provided evidence, the following references are found to be relevant to the Seam IV:*  
  > *1. 'Geological Exploration Report Seam IV' (Doc ID: e58274d0..., Page: 3, Tier: TIER_A)*  
  > *2. 'BCCL Geological Exploration Report 2024' (Doc ID: e2254f80..., Page: 1, Tier: TIER_A)*  
  > *3. 'Test Continuous Table Ingestion' (Doc ID: cd962c70..., Page: 1, Tier: TIER_A)*  
  > *4. 'BCCL Geological Exploration Report 2024' (Doc ID: e2254f80..., Page: 1, Tier: TIER_A)..."*
* **Empirical Evaluation**:
  * **Entity Recognition**: PASS. Correctly retrieved documents mentioning Seam IV.
  * **Hierarchical Grouping**: **FAIL**. The system returned a flat list of document titles. It did NOT organize output into the requested hierarchical tree (`Mine` $\rightarrow$ `Report` $\rightarrow$ `Year` $\rightarrow$ `Document Type`).
  * **Mechanism in Code**: `qa_service.py` executes vector + keyword search and passes top chunks to the LLM. It does not have an entity aggregation or hierarchical taxonomic grouping schema for document references.
  * **Verdict**: **PARTIAL**

---

### Q2: "What are the thickness, depth, roof, floor and ash percentage associated with Seam IV? Give the source document and page for each attribute."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 163 | **Citations Returned**: 162 | **Latency**: 16.02s
* **Actual System Answer**:
  > *"Based on the provided evidence, the thickness, depth, roof, floor, ash percentage, and source document for Seam IV are:*  
  > *Seam IV | 210.0 | 5.8 | Steel-I | 12.8*  
  > *Seam XVI-A | 145.5 | 4.2 | Steel-II | 18.4*  
  > *Seam XV | 210.0 | 5.8 | Steel-II | 18.4*  
  > *Seam XIII | 340.8 | 3.9 | Washery-I | 24.6*  
  > *Seam XIV | 285.2 | 6.1 | Washery-II | 24.6..."*
* **Empirical Evaluation**:
  * **Attribute Linking**: **FAIL / UNSAFE**. The system retrieved a multi-seam stratigraphy table from `Moonidih Geological Survey Report FY2024-25` (Page 3) and `BCCL Geological Exploration Report 2024`. Because multiple seams appeared in the same table chunk, the LLM conflated rows, reporting attributes for Seam XVI-A, Seam XV, and Seam XIII under Seam IV.
  * **Roof & Floor Lithology**: **FAIL**. The source table contained "Coal Grade" ("Steel-I", "Steel-II"), which the LLM erroneously placed into the Roof/Floor slot. Roof and floor strata (Sandstone/Shale) were present in Figure 1 of Doc `57dde557...` (Visual Asset), but were NOT joined to the tabular metrics.
  * **Mechanism in Code**: Table chunks are serialized as Markdown text. The LLM has no relational table parser during generation that binds `(Entity="Seam IV", Attribute="Roof Lithology")` as a typed tuple.
  * **Verdict**: **FAIL / PARTIAL RETRIEVAL**

---

```text
================================================================================
TEST 2 — EVIDENCE CONFLICT (Q3 & Q4)
================================================================================
```

### Q3: "Different documents contain different values for the reserve of Seam IV. Identify all conflicting values and explain why they may differ."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 151 | **Citations Returned**: 156 | **Latency**: 19.93s
* **Actual System Answer**:
  > *"Based on the provided evidence, the following conflicting values are mentioned:*  
  > *1. Seam IV: 52.40 (Source: Multi-page Geological Exploration Statement, P.1)*  
  > *2. Seam IV: 52.40 (Source: Multi-page Geological Exploration Statement, P.1)... [repeated 9 times]"*
* **Empirical Evaluation**:
  * **Conflict Identification**: **FAIL**. The system repeated the identical value `52.40` nine times. It did not find an actual reserve conflict in the corpus for Seam IV, yet instead of honestly stating that no conflicting values were found in the knowledge base, it labeled identical values as "conflicting".
  * **Explanation of Difference**: **FAIL**. No explanation of geological definitions (e.g. Proved vs Extractable) was produced.
  * **Mechanism in Code**: The prompt presupposed a conflict. Because no `ReconciliationGroup` conflict was flagged in PostgreSQL for Seam IV, `struct_res.conflict_warning` was `None`. The LLM, coerced by the prompt, blindly listed whatever single reserve number it found in `struct_res.facts` repeatedly.
  * **Verdict**: **FAIL**

---

### Q4: "For the conflicting reserve values of Seam IV, identify the date, document type, revision/status and source location associated with each value."
* **Status**: `SUPPORTED` | **Facts Found**: 151 | **Citations Returned**: 156 | **Latency**: 19.19s
* **Actual System Answer**:
  > *"Based on the provided evidence, the conflicting reserve values of Seam IV are:*  
  > *1. Seam IV | reserves_proved: 52.40 () [Source: Multi-page Geological Exploration Statement, P.1]*  
  > *2. Seam IV | reserves_proved: 52.40 () [Source: Multi-page Geological Exploration Statement, P.1]..."*
* **Empirical Evaluation**:
  * **Lineage Tracking**:
    * `VALUE`: 52.40 [PRESENT]
    * `DOCUMENT`: Multi-page Geological Exploration Statement [PRESENT]
    * `PAGE`: Page 1 [PRESENT]
    * `DATE / REPORTING PERIOD`: `()` **[EMPTY / NOT PRESENT]**
    * `DOCUMENT TYPE`: **[NOT PRESENT IN OUTPUT]**
    * `REVISION / STATUS`: **[NOT PRESENT IN OUTPUT]**
  * **Mechanism in Code**: `qa_service.py` formats `struct_res.facts` as:
    `f"- {f.entity_name} | {f.metric_name}: {f.raw_value} ({f.reporting_period or ''}) [Source: {f.document_title}, P.{f.page_number}]"`.
    The document's `document_type` and `document_versions.version_number` are not joined into `StructuredFact`.
  * **Verdict**: **NOT IMPLEMENTED / NOT PRESENT IN SOURCE FORMATTER**

---

```text
================================================================================
TEST 3 — SOURCE AUTHORITY (Q5)
================================================================================
```

### Q5: "Which source should be considered authoritative for the current reserve of Seam IV? Explain the evidence you used to determine this, rather than simply choosing the most recent number."
* **Status**: `SUPPORTED` | **Facts Found**: 151 | **Citations Returned**: 156 | **Latency**: 22.68s
* **Actual System Answer**:
  > *"Based on the evidence provided, the most authoritative source for the current reserve of Seam IV is the Multi-page Geological Exploration Statement (MPGS) from the Coal Board of India (CBI). The MPGS is a detailed report prepared by the CBI and is considered the most authoritative source for the current reserve of Seam IV... The MPGS is considered authoritative because it is the most recent report from the CBI..."*
* **Empirical Evaluation**:
  * **Authority Resolution**: **CRITICAL FAILURE / HALLUCINATION**. The system fabricated an entity called the "Coal Board of India (CBI)" and explicitly fell into the prohibited trap of declaring authority "because it is the most recent report".
  * **Mechanism in Code**: Koyla currently has **NO source authority resolution rules** in its QA or retrieval pipeline. While `documents.source_tier` exists in the database schema (`TIER_A`, `TIER_B`, `TIER_C`), there is no rule-based evaluator that resolves which document takes precedence (e.g. DGMS Safety Audit vs CMPDI Exploration Bulletin vs Form-A Statutory Mine Profile).
  * **Verdict**: **AUTHORITY RULE NOT IMPLEMENTED**

---

```text
================================================================================
TEST 4 — NUMBER LINEAGE & CALCULATION (Q6)
================================================================================
```

### Q6: "Calculate the current recoverable reserve of Seam IV using the relevant source data. Show every input, operation, unit, source document and page used in the calculation."
* **Status**: `SUPPORTED` | **Facts Found**: 151 | **Citations Returned**: 156 | **Calculations Count**: 0 | **Latency**: 19.82s
* **Actual System Answer**:
  > *"1. Current recoverable reserve of Seam IV: 52.40 (Source: Multi-page Geological Exploration Statement, P.1)*  
  > *2. Current recoverable reserve of Seam IV: 52.40 (Source: Multi-page Geological Exploration Statement, P.1)... [repeated]"*
* **Empirical Evaluation**:
  * **Calculation Lineage**: **FAIL**. The system performed NO calculation (`Calculations Count: 0`). It simply regurgitated the proved reserve number (52.40 MT) and mislabeled it as "recoverable reserve".
  * **Mechanism in Code**: `arithmetic_engine.py` only triggers when the query contains explicit comparative terms ("growth from", "change between", "stripping ratio"). It does not possess an autonomous formula-discovery engine for mining formulas like `Recoverable = Proved * Mining Recovery Factor`.
  * **Verdict**: **CALCULATION NOT JUSTIFIED**

---

```text
================================================================================
TEST 5 — CALCULATION VERIFICATION (Q7)
================================================================================
```

### Q7: "Verify the calculation you just performed. Check whether the units are consistent, whether any input was duplicated, and whether every input has a source."
* **Status**: `REFUSED` | **Facts Found**: 0 | **Citations Returned**: 0 | **Calculations Count**: 0 | **Latency**: 0.90s
* **Actual System Answer**:
  > *"Insufficient verified evidence found in the selected knowledge base."*
* **Empirical Evaluation**:
  * **Refusal Behavior**: **PASS (Correct Honest Refusal)**. Because no calculation had been performed in Q6 and this conversational prompt contained no factual entity keywords, Koyla's retrieval score fell below `QA_REFUSAL_THRESHOLD` (0.35) and facts were 0. The system executed a clean, deterministic refusal rather than hallucinating a fake verification.
  * **Capability Assessment**: Interactive post-generation calculation verification is **NOT IMPLEMENTED** as an architectural service.
  * **Verdict**: **PASS (Honest Refusal) / FEATURE NOT IMPLEMENTED**

---

```text
================================================================================
TEST 6 — GEOLOGICAL RELATIONSHIPS (Q8)
================================================================================
```

### Q8: "For Seam IV, explain the relationship between its thickness, depth, roof lithology, floor lithology and ash percentage. Do not simply list the values."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 163 | **Citations Returned**: 162 | **Latency**: 17.26s
* **Actual System Answer**:
  > *"Based on the provided evidence, the relationship between the thickness, depth, roof lithology, floor lithology, and ash percentage of Seam IV is as follows:*  
  > *- Seam IV is a shallow, thin, and thin-thickness coalfield, with a shallow roof lithology and a thin floor lithology.*  
  > *- The roof lithology is a thin, thin-thickness coalfield, with a thin, thin-thickness roof lithology.*  
  > *- The floor lithology is a thin, thin-thickness coalfield, with a thin, thin-thickness floor lithology.*  
  > *- The ash percentage is a high, high-percentage coalfield, with a high ash percentage..."*
* **Empirical Evaluation**:
  * **Relationship Reasoning**: **CRITICAL FAILURE**. The small LLM broke down into circular nonsensical repetitions ("thin, thin-thickness coalfield with a thin floor lithology").
  * **Distinction of Direct vs Inferred**: **FAIL**. The system failed to distinguish directly measured physical parameters from geological depositional hypotheses.
  * **Mechanism in Code**: Koyla has no geological knowledge graph, Bayesian network, or causal reasoning module. Asking an SLM (135M parameters) to reason about lithological depositional relationships without structured prompt guardrails produces severe degradation.
  * **Verdict**: **FAIL / ARCHITECTURAL GAP**

---

```text
================================================================================
TEST 7 — CROSS-DOCUMENT ENTITY RESOLUTION (Q9)
================================================================================
```

### Q9: "Are 'Seam IV', 'Seam-IV', 'IV Seam' and 'Seam 4' referring to the same geological entity in these documents? Provide the evidence supporting your conclusion."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 12 | **Citations Returned**: 11 | **Latency**: 17.56s
* **Actual System Answer**:
  > *"Based on the provided evidence, it is evident that 'Seam IV', 'Seam-IV', 'IV Seam', 'IV-Seam', 'IV-Seam-IV', and 'Seam-4' are referring to the same geological entity in the documents. The evidence supports this conclusion by:*  
  > *1. Verified structural information: The document states that 'Seam IV', 'Seam-IV', 'IV Seam'... are referring to the same geological entity in the documents.*  
  > *2. Verified geological information: The document states that... [repeated]"*
* **Empirical Evaluation**:
  * **Entity Resolution**: **FAIL**. The system claimed that the documents explicitly state they are the same entity, which is false. No document contains a statement equating these names.
  * **Mechanism in Code**: Koyla currently has **NO entity resolution service or alias graph**. In mining geology, "Seam IV" at Moonidih (Jharia Coalfield) is completely independent of "Seam IV" in Raniganj or Korba. Koyla's query normalizer handles string aliases for metrics (e.g. `OB` $\rightarrow$ `overburden`), but has no entity disambiguation engine for geological bodies across different mines or coal basins.
  * **Verdict**: **CANNOT ESTABLISH SAME ENTITY / SERVICE NOT IMPLEMENTED**

---

```text
================================================================================
TEST 8 — CONTRADICTORY EVIDENCE (Q10)
================================================================================
```

### Q10: "The documents contain inconsistent information about Seam IV. Do not guess. Identify the inconsistency, explain what additional evidence is required to resolve it, and state what cannot currently be concluded."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 12 | **Citations Returned**: 11 | **Latency**: 23.04s
* **Actual System Answer**:
  > *"The inconsistency in the information about Seam IV is due to the inconsistency in the following documents:*  
  > *1. The document on Seam IV (P.1) states that the Seam IV is '95%' and '98%' in the table. However, the document on Seam IV (P.2) states that the Seam IV is '90%' and '88%' in the table... [repeated]*  
  > *To resolve the inconsistency, additional evidence would be required to: 1. Confirm the accuracy of..."*
* **Empirical Evaluation**:
  * **Inconsistency Handling**: **CRITICAL FAILURE / FABRICATION**. The system hallucinated numbers ("95%", "98%", "90%", "88%") that do not exist in either Seam IV document!
  * **Mechanism in Code**: Because the prompt asserted that "The documents contain inconsistent information", the LLM was pressured to invent conflicting values. Because Koyla's reconciliation service had not detected a reconciliation group conflict for Seam IV, no structured conflict warning was injected into the prompt. The LLM was left unconstrained and invented percentages.
  * **Verdict**: **FAIL / INADMISSIBLE HALLUCINATION UNDER LEADING PROMPT**

---

```text
================================================================================
TEST 9 — CITATION PROVENANCE (Q11)
================================================================================
```

### Q11: "For every factual claim in your answer, provide the exact source document and page/table/section from which it was obtained."
* **Status**: `REFUSED` | **Facts Found**: 0 | **Citations Returned**: 0 | **Latency**: 0.52s
* **Actual System Answer**:
  > *"Insufficient verified evidence found in the selected knowledge base."*
* **Empirical Evaluation**:
  * **Refusal Behavior**: **PASS**. The meta-query contains no domain search terms. Koyla's retrieval floor correctly halted generation.
  * **Verdict**: **PASS (Correct Refusal)**

---

```text
================================================================================
TEST 10 — FACT VS CALCULATION VS INFERENCE (Q12)
================================================================================
```

### Q12: "Separate your answer into three categories: (1) directly stated facts, (2) values calculated from source data, and (3) conclusions inferred from the documents."
* **Status**: `SUPPORTED` | **Facts Found**: 0 | **Citations Returned**: 5 | **Latency**: 37.59s
* **Actual System Answer**:
  > *"1. The document states that the mine closure plan will be revised for extraction of less coal on a year-on-year basis.*  
  > *2. The document states that the mine owner is mandated to prepare and obtain approval for a temporary mine closure plan...*  
  > *3. The document states that the mine owner is required to deposit the annual amount to be deposited for each financial year by 30th September... [repeated]"*
* **Empirical Evaluation**:
  * **Three-Category Separation**: **FAIL**. The system retrieved arbitrary mine closure chunks from `MoC Statutory Guidelines Test Upload` (Pages 12, 15, 17) and output six bullet points repeating statutory rules. It failed to partition into Directly Stated Facts vs Calculated Values vs Inferred Conclusions.
  * **Mechanism in Code**: Koyla partitions facts vs calculations when deterministic Python engines run (`calc_dicts` and `struct_res.facts` are partitioned in prompt compilation). However, the generative LLM has no meta-prompting template that enforces this three-way taxonomy in its generated text.
  * **Verdict**: **FAIL**

---

```text
================================================================================
TEST 11 — TEMPORAL REASONING (Q13)
================================================================================
```

### Q13: "How did the reported reserve/production value for Seam IV change over time? Construct a chronological timeline and cite the source for every value."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 749 | **Citations Returned**: 695 | **Calculations Count**: 76 | **Latency**: 67.30s
* **Actual System Answer**:
  > *"Based on the provided information, here is a chronological timeline of the reported reserves/production values for Seam IV over time:*  
  > *1. 2018: 42.50 (Production)*  
  > *2. 2019: 45.00 (Production)*  
  > *3. 2020: 48.00 (Production)*  
  > *4. 2021: 50.00 (Production)*  
  > *5. 2022: 52.50 (Production)*  
  > *6. 2023: 55.00 (Production)*  
  > *The values for Seam IV have changed over time, but the underlying data is consistent with the information provided."*
* **Empirical Evaluation**:
  * **Temporal Lineage**: **CRITICAL FAILURE / FABRICATED TIMELINE**. The system hallucinated a perfectly neat, fabricated chronological progression from 2018 to 2023 (`42.50, 45.00, 48.00, 50.00, 52.50, 55.00`)!
  * **Citation Verification**:
    * Citation [1]: `MoC Statutory Guidelines Test Upload` (Page 36) — contains Table 1 of mine closure guideline formats; mentions no Seam IV timeline.
    * Citation [2]: `secl_gevra_production_fy24.xlsx` (Page 2) — contains Gevra Seam reserves (Upper Gevra, Lower Gevra); mentions no 2018–2023 yearly Seam IV timeline.
    * Citation [3]: `BCCL Geological Exploration Report 2024` (Page 1) — contains Seam XVI-A; mentions no Seam IV timeline.
  * **Mechanism in Code**:
    1. Because the query asked for an enterprise-wide temporal query across all organizations, `qa_service.py` retrieved **749 facts** and **76 calculations**.
    2. The prompt reached over **10,000 tokens**, blowing past SmolLM2's context window.
    3. `grounding_checker.py` checked whether `42.50`, `50.00`, `52.50`, and `55.00` were in `evidence_corpus`. Because those numbers existed scattered across unrelated CCL, Gevra, and Moonidih tables, the number check passed!
    4. The LLM synthesized a fake chronological progression connecting unrelated numbers.
  * **Verdict**: **CRITICAL FAILURE (Temporal Fabrication Masked by Shallow Grounding Check)**

---

```text
================================================================================
TEST 12 — KILLER TEST ON LOADED DOMAIN CORPUS (Q14)
================================================================================
```

### Q14: "What was the raw coal production for Rajmahal Opencast Mine in FY 2023-24, and what was the growth compared to previous year? State the exact values, sources, and any conflicting records."
* **Status**: `PARTIALLY_SUPPORTED` | **Facts Found**: 598 | **Citations Returned**: 544 | **Calculations Count**: 77 | **Latency**: 72.97s
* **Actual System Answer (Enterprise Scope)**:
  > *"Based on the provided information, the raw coal production for Rajmahal Opencast Mine in FY 2023-24 was 38.00 MT. The growth compared to previous year was 42.50 MT. The sources of the growth were: 1. Raw coal production: 55.0 MT, 2. Raw coal production: 50.0 MT... The conflicting records include: 1. Raw coal production: 55.0 MT... [repetitive loop]"*

* **Actual Ground Truth in Loaded Database**:
  1. `Rajmahal Open Cast Production Summary FY2023-24` (Doc ID: `9d2a5272...`, Page 2):
     `"ECL Rajmahal Mine achieved total coal production of 14.50 MT during FY2023-24 with stripping ratio 2.10."`
  2. `Annual Production Summary for Rajmahal Opencast Mine FY2024-25` (Doc ID: `d97fd6a0...`, Page 1):
     `"Rajmahal Opencast project achieved total coal production of 17.50 MT of grade G11 in FY2024-25."`
  3. `Conflict Report Alpha` & `Conflict Report Beta` (Synthetic benchmark documents):
     Contain `38.00 MT` and `42.50 MT` for conflicting production reconciliation tests.

* **Actual System Answer (Scoped to ECL Subsidiary)**:
  When scoped to `allowed_org_ids=[ECL_ORG_ID]`, the context is properly restricted, and Koyla returns:
  > *"- Production_quantity: 38.00 (Annual Reconciliation Statement Document B, P.None)*  
  > *- Production_quantity: 55.0 MT (Monthly Operating Review Document A, P.None)*  
  > *- Production_quantity: 42.50 (Monthly Operating Review Document A, P.None)..."*

* **Empirical Evaluation**:
  * **When Query is Enterprise-Wide**: The retrieval engine pulls hundreds of records from unrelated subsidiaries (SECL Gevra, CCL Barka-Sayal, synthetic conflict benchmarks). The 135M parameter LLM cannot perform contextual entity filtering and hallucinates the production value (calling it 38.00 MT instead of 14.50 MT).
  * **When Query is Scoped to Entity/Organization**: The deterministic SQL lookup identifies the exact contributing documents (`Document A` vs `Document B`) and flags the conflicting values explicitly.
  * **Verdict**: **PARTIAL (PASS when Scoped to Deterministic Aggregation / FAIL under Global Unconstrained LLM Context)**

---

## 4. CAPABILITY SCORECARD

| Capability | Rating | Evidence / Root Cause in Code |
| :--- | :---: | :--- |
| **Entity recognition** | **PARTIAL** | `query_normalizer.py` recognizes CIL entities via regex; fails on novel or multi-word geological strata. |
| **Entity normalization** | **PARTIAL** | Expands known acronyms (MT, OB, ECL); cannot resolve geological seam synonyms across basins. |
| **Attribute linking** | **PARTIAL** | Single-field extraction links value to page; table parsing cross-pollinates columns across multiple seam rows. |
| **Cross-document reasoning** | **PARTIAL** | Supported for deterministic YoY & SQL aggregations; fails in LLM narrative synthesis. |
| **Provenance tracking** | **PASS** | Full relational provenance (`document_id`, `page_number`, `chunk_id`, `table_id`, `visual_id`, `bounding_box`). |
| **Conflict detection** | **PASS** | `reconciliation.py` identifies numerical divergence $>1\%$ and blocks corrupted aggregations. |
| **Conflict explanation** | **NOT IMPLEMENTED** | System flags *that* values differ; possesses no domain knowledge base to explain *why*. |
| **Source authority** | **NOT IMPLEMENTED** | Tiers exist in DB; zero runtime logic for ranking document precedence (Draft vs Approved vs Statutory). |
| **Number lineage** | **PASS / FAIL** | **PASS** in Python Arithmetic/SQL engine (`formula`, operands, sources); **FAIL** in freeform LLM prose. |
| **Deterministic calculation**| **PASS** | YoY, percentages, ratios, SUM, AVG, MIN, MAX, COUNT strictly computed in Python/SQL. Zero LLM math. |
| **Calculation verification** | **PARTIAL** | Unit compatibility and duplicate checks run in backend services; no conversational verification module. |
| **Geological reasoning** | **FAIL** | Zero geological causal knowledge. SmolLM2-135M degenerates into circular hallucination. |
| **Alias / entity resolution** | **NOT IMPLEMENTED** | No entity coreference engine, graph database, or cross-document entity linker. |
| **Temporal reasoning** | **PARTIAL** | **PASS** for metadata-tagged periods in `arithmetic_engine`; **FAIL** for open-ended timeline prompts. |
| **Fact/Calc/Inference split**| **PARTIAL** | Structured prompts segregate facts and calculations; LLM output text fails to self-classify. |
| **Refusal behavior** | **PASS** | Deterministic refusal (`STANDARD_REFUSAL_TEXT`) triggered when retrieval similarity $<0.35$. |
| **Citation correctness** | **PARTIAL** | Citation links point to real chunks; but cited text frequently does not support LLM's hallucinated claims. |
| **Multimodal grounding** | **PASS** | Cross-sections, maps, and stratigraphic columns are indexed, captioned, and visually cited with bboxes. |

---

## 5. CRITICAL SECOND PASS: ARCHITECTURAL GAPS VS DATA LIMITATIONS

The audit proves that failures in Koyla fall into two distinct engineering categories:

### 5.1 Architectural Gaps (Require Core Code Development)
1. **Shallow Grounding Verification (The Set-Membership Flaw)**:
   * *Observed*: In Q13, the LLM hallucinated a fake timeline (`42.5, 45.0, 48.0, 52.5`), yet `GroundingChecker` marked it `PARTIALLY_SUPPORTED`.
   * *Mechanism*: `grounding_checker.py` (lines 161–180) checks whether each number in the sentence exists in `evidence_corpus.lower()`. Because those numbers existed anywhere in the 700 retrieved facts, the check passed.
   * *Root Cause*: Lack of **Relational Tuple Binding**. The verification layer must verify `(Subject, Predicate, Object, Period)` tuples, not isolated scalars.
2. **Missing Source Authority Hierarchy**:
   * *Observed*: In Q5, the system chose the most recent report and invented an authority justification ("Coal Board of India").
   * *Mechanism*: `qa_service.py` sorts chunks strictly by RRF relevance score. It does not apply statutory or document precedence weightings.
   * *Root Cause*: Lack of a deterministic precedence matrix (e.g. `Statutory Form-A` > `Approved Mining Plan` > `Preliminary Geological Report` > `Internal Note`).
3. **No Entity Coreference Resolution Engine**:
   * *Observed*: In Q9, the system falsely claimed that documents state "Seam IV", "Seam-IV", and "IV Seam" are the same entity.
   * *Mechanism*: Koyla relies on lexical matching and cosine similarity. It has no entity resolver that disambiguates whether a seam identifier belongs to Mine A or Mine B.
4. **Context Window Blowout in Unscoped Queries**:
   * *Observed*: In Q13 and Q14, prompt size reached 10,089 tokens, exceeding the 8,192 token limit of the local model.
   * *Mechanism*: `qa_service.py` appends all retrieved facts and calculations without a strict token-budget compressor or hard top-k limit on structured facts.

### 5.2 Data-Related Limitations (Corpus Deficiencies)
1. **Lack of Borehole Strata Instances in Active DB**:
   * *Observed*: `BoreholeStratum` table count is 0 in the live database.
   * *Cause*: While the normalized strata model was implemented in P1-1, large-scale CSV/borehole datasets have not yet been bulk-ingested into PostgreSQL.
2. **Synthetic Conflict Pollution in Enterprise Scope**:
   * *Observed*: In Q14, synthetic conflict test documents (`Conflict Report Alpha`, `Doc X`, `Doc Y`) injected conflicting production numbers (38 MT, 42.5 MT) into real Rajmahal queries.
   * *Cause*: Test benchmark documents share the default organization space rather than being isolated in a dedicated test tenant sandbox.

---

## 6. WHAT KOYLA CAN ALREADY DO (PROVEN STRENGTHS)

1. **Deterministic Mathematical Lineage**: When asked for Year-over-Year changes, percentage variance, or stripping ratios, Koyla executes pure Python code in `arithmetic_engine.py`. It outputs the exact formula, operands, document sources, and page numbers, completely eliminating math hallucinations.
2. **Deterministic Multi-Document SQL Aggregation**: Through `structured_lookup.py`, Koyla aggregates millions of tonnes across multiple documents using verified database queries with strict tenant isolation, excluding pending or conflicted records.
3. **Robust Four-Eyes Governance**: Enforces maker-checker separation of duties on statutory reserve edits at the database level, preventing self-approval and logging security audit events.
4. **Honest Refusal Floor**: Correctly halts execution and outputs `"Insufficient verified evidence found in the selected knowledge base."` when questions are ungrounded or lack topical relevance.
5. **Full Relational Provenance**: Retains physical document IDs, page numbers, table coordinates, and visual diagram bounding boxes through the entire ingestion and retrieval pipeline.

---

## 7. WHAT KOYLA CANNOT CURRENTLY DO (CURRENT LIMITATIONS)

1. **Cannot Reason Over Multi-Row Geological Tables**: Conflates rows when multiple seams or stratigraphic units appear in the same table chunk.
2. **Cannot Arbitrate Source Authority**: Cannot deterministically decide which document supersedes another when values diverge.
3. **Cannot Perform Open-Ended Autonomous Calculation**: Cannot discover domain equations (e.g. Recoverable Reserves) unless the specific formula is hardcoded in the Python engine.
4. **Cannot Disambiguate Homonymous Entities**: Cannot verify whether an entity name across two reports represents the same geological formation.
5. **Cannot Reliably Synthesize Narrative Geological Explanations**: The 135M parameter local model degenerates into repetitive or circular text when prompted for causal or depositional relationships.

---

## 8. RECOMMENDED NEXT ENGINEERING PHASE

Based on this empirical capability audit, the next engineering phase must NOT focus on cosmetic UI changes or adding more general RAG documents.

### Recommended Priority: **P1-4 — Relational Tuple Grounding & Source Authority Precedence**
1. **Implement Source Authority Hierarchy (`authority_service.py`)**:
   * Create an authoritative ranking rule:
     `STATUTORY_GUIDELINE (Tier A, Rank 1) > APPROVED_MINING_PLAN (Tier A, Rank 2) > GEOLOGICAL_REPORT (Tier A, Rank 3) > PRODUCTION_SUMMARY (Tier B, Rank 4) > INTERNAL_NOTE (Tier C, Rank 5)`.
   * When conflicting metrics exist, explicitly declare the highest-ranking source authoritative and cite the precedence rule.
2. **Implement Relational Tuple Grounding in `GroundingChecker`**:
   * Replace loose scalar number set-membership with typed entity-attribute tuple verification:
     `Assertion: (Entity, Metric, Value, Unit, Period) must match ExtractedField record`.
   * Reject LLM assertions where a number is attributed to the wrong seam or mine.
3. **Dynamic Prompt Token Budgeter in `qa_service.py`**:
   * Cap structured facts context at 1,500 tokens using similarity ranking against query entities to prevent context window overflow (avoiding the 10,089 token blowout).
4. **Entity Disambiguation / Mine Context Filter**:
   * Require explicit or inferred `Mine / Block` scoping before aggregating seam attributes to prevent cross-coalfield entity confusion.

---
**Audit Completed & Verified by Antigravity Agentic Engineer**  
*Output Document:* `PHASE_10_5_EVIDENCE_INTELLIGENCE_AUDIT.md`  
*Raw Execution Telemetry:* `backend/scripts/audit_raw_results.json`
