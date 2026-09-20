import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.qa import QueryRecord, AnswerRecord, AnswerCitation
from app.services.retrieval import retrieval_service, RetrievalResult
from app.services.retrieval.query_normalizer import query_normalizer, NormalizedQuery
from app.services.llm import get_llm_provider, LLMUnavailableError, LLMResponse
from app.services.qa.arithmetic_engine import arithmetic_engine, CalculationResult
from app.services.qa.structured_lookup import (
    structured_lookup_service,
    StructuredLookupResult,
    StructuredFact,
    ConflictWarning,
)
from app.services.qa.grounding_checker import (
    grounding_checker,
    GroundingReport,
    STANDARD_REFUSAL_TEXT,
)
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)


class QACitation(BaseModel):
    citation_id: str
    citation_index: int
    document_id: str
    document_title: str
    document_type: str
    source_tier: str
    page_number: Optional[int] = None
    excerpt: str
    relevance_score: float
    table_provenance: Optional[Dict[str, Any]] = None


class QAResponse(BaseModel):
    query_id: str
    answer_id: str
    query: str
    answer: str
    verification_status: str  # 'SUPPORTED', 'PARTIALLY_SUPPORTED', 'REFUSED'
    confidence_score: float
    llm_status: str           # 'AVAILABLE', 'UNAVAILABLE'
    llm_provider: str
    llm_model: str
    arithmetic_used: bool
    conflict_detected: bool
    citations: List[QACitation] = Field(default_factory=list)
    structured_facts: List[Dict[str, Any]] = Field(default_factory=list)
    calculations: List[Dict[str, Any]] = Field(default_factory=list)
    conflict_warning: Optional[Dict[str, Any]] = None
    trace: Dict[str, Any] = Field(default_factory=dict)


class QAService:
    """
    Master Grounded Q&A Coordinator for KOYLA.
    Coordinates Dual Data Retrieval (Structured Facts + Phase 5 Hybrid Search)
    -> Deterministic Arithmetic -> Grounded Prompt Construction -> Local LLM
    -> Grounding Verification & Bounded Retry -> Citation Assembly -> Audit Persistence.
    """

    def answer_query(
        self,
        db: Session,
        query: str,
        current_user: User,
        allowed_org_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        enable_reranker: bool = True
    ) -> Dict[str, Any]:
        overall_start = time.perf_counter()
        filters = dict(filters or {})
        top_k = min(max(top_k, 1), settings.MAX_EVIDENCE_CHUNKS)

        # 1. Query Normalization
        t_norm_start = time.perf_counter()
        norm_query: NormalizedQuery = query_normalizer.normalize(query)
        t_norm_ms = (time.perf_counter() - t_norm_start) * 1000.0

        # 2. Dual Data Retrieval - Path A: Structured Database & Conflict Lookup
        t_struct_start = time.perf_counter()
        struct_res: StructuredLookupResult = structured_lookup_service.lookup(
            db=db,
            query=query,
            allowed_org_ids=allowed_org_ids,
            normalized_query=norm_query
        )
        t_struct_ms = (time.perf_counter() - t_struct_start) * 1000.0

        # 3. Dual Data Retrieval - Path B: Phase 5 Hybrid Vector & Keyword Search
        t_retrieval_start = time.perf_counter()
        search_res = retrieval_service.retrieve(
            db=db,
            query=query,
            allowed_org_ids=allowed_org_ids,
            filters=filters,
            search_mode="HYBRID",
            top_k=top_k,
            enable_reranker=enable_reranker
        )
        t_retrieval_ms = (time.perf_counter() - t_retrieval_start) * 1000.0
        raw_results: List[Dict[str, Any]] = [
            r.to_dict() if hasattr(r, "to_dict") else r for r in search_res.get("results", [])
        ]

        # 3b. Organization & Subsidiary Consistency Filter
        # If the query asks for a specific subsidiary (e.g. ECL), do not cite unrelated subsidiaries (e.g. BCCL)
        import re
        detected_subsidiaries = [
            e.upper() for e in norm_query.entities
            if e.upper() in ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL", "CMPDI", "CIL"]
        ]
        if not detected_subsidiaries:
            for sub_code in ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL", "CMPDI"]:
                if re.search(r'\b' + sub_code + r'\b', query, re.IGNORECASE):
                    detected_subsidiaries.append(sub_code)

        if detected_subsidiaries:
            target_sub = detected_subsidiaries[0]
            consistent_results = []
            for r in raw_results:
                r_text = (r.get("source_text") or "").upper()
                r_title = (r.get("title") or "").upper()
                # If target sub is mentioned in chunk or document title
                if target_sub in r_text or target_sub in r_title:
                    consistent_results.append(r)
                else:
                    # Check if document belongs to an unrelated subsidiary
                    is_conflicting_sub = any(
                        other_sub in r_title
                        for other_sub in ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL"]
                        if other_sub != target_sub
                    )
                    if not is_conflicting_sub:
                        consistent_results.append(r)
            retrieved_results: List[Dict[str, Any]] = consistent_results if consistent_results else raw_results
        else:
            retrieved_results = raw_results

        # 4. Deterministic Arithmetic Calculations
        t_calc_start = time.perf_counter()
        fact_dicts = [f.dict() for f in struct_res.facts]
        calculations = arithmetic_engine.detect_and_execute_calculations(
            query=query,
            structured_records=fact_dicts
        )
        calc_dicts = [c.dict() for c in calculations]
        t_calc_ms = (time.perf_counter() - t_calc_start) * 1000.0

        # 5. Check Refusal Conditions (Insufficient Evidence or Off-Topic Retrieval)
        has_evidence = bool(retrieved_results) or bool(struct_res.facts)
        if search_res.get("results"):
            first_res = search_res["results"][0]
            top_score = first_res.get("rrf_score", 0.0) if isinstance(first_res, dict) else getattr(first_res, "rrf_score", 0.0)
        else:
            top_score = 0.0


        # Check semantic/lexical topical overlap of substantive query terms with evidence
        import re
        stopwords = {
            "what", "when", "where", "which", "with", "from", "that", "this", "these", "those",
            "have", "been", "were", "reported", "annual", "about", "coal", "block", "mine", "review",
            "tell", "give", "show", "details", "data", "information", "fiscal", "year"
        }
        substantive_query_words = [
            w for w in re.findall(r'\b[a-zA-Z]{4,}\b', query.lower())
            if w not in stopwords
        ]
        evidence_corpus_text = " ".join([r.get("source_text", "").lower() for r in retrieved_results])
        for f in struct_res.facts:
            evidence_corpus_text += f" {f.raw_value} {f.metric_name} {f.entity_name or ''}".lower()

        has_topical_overlap = True
        if substantive_query_words and not struct_res.facts:
            has_topical_overlap = any(
                bool(re.search(r'\b' + re.escape(w) + r'\b', evidence_corpus_text))
                for w in substantive_query_words
            )

        if not has_evidence or not has_topical_overlap or (not struct_res.facts and top_score < settings.QA_REFUSAL_THRESHOLD):
            # Deterministic Refusal
            return self._persist_and_return_refusal(
                db=db,
                query=query,
                current_user=current_user,
                norm_query=norm_query,
                filters=filters,
                reason="Insufficient verified evidence found in the selected knowledge base.",
                overall_start=overall_start,
                search_res=search_res
            )


        # 6. Context Compilation for Grounded Generation
        evidence_blocks = []
        evidence_texts = []
        citations_list: List[QACitation] = []

        for idx, item in enumerate(retrieved_results, start=1):
            p_num = item.get("page_number", 1)
            d_title = item.get("title", "Document")
            d_id = item.get("document_id")
            c_type = item.get("chunk_type", "TEXT")
            s_tier = item.get("source_tier", "TIER_B")
            c_text = item.get("source_text", "").strip()
            table_info = item.get("provenance", {}).get("table") or item.get("provenance", {}).get("table_info")

            evidence_texts.append(c_text)
            block = f"[{idx}] Source: \"{d_title}\" (Doc ID: {d_id}, Page: {p_num}, Tier: {s_tier})\n"
            if table_info:
                block += f"Table Part {table_info.get('part_number', 1)} of {table_info.get('total_parts', 1)}"
                if table_info.get("caption"):
                    block += f" - Caption: {table_info.get('caption')}"
                block += f"\nHeaders: {table_info.get('headers', [])}\n"
            block += f"Content: {c_text}\n"
            evidence_blocks.append(block)

            citations_list.append(QACitation(
                citation_id=f"cite-{idx}",
                citation_index=idx,
                document_id=d_id,
                document_title=d_title,
                document_type=item.get("document_type", "DOCUMENT"),
                source_tier=s_tier,
                page_number=p_num,
                excerpt=c_text[:300] + "..." if len(c_text) > 300 else c_text,
                relevance_score=item.get("rrf_score", 0.0),
                table_provenance=table_info
            ))

        compiled_context = "=== EVIDENCE CHUNKS ===\n" + "\n".join(evidence_blocks)

        if struct_res.conflict_warning:
            compiled_context += (
                f"\n=== CROSS-DOCUMENT CONFLICT ALERT ===\n"
                f"{struct_res.conflict_warning.message}\n"
                f"ACTION REQUIRED: State both conflicting values explicitly and inform the user that human review is required.\n"
            )

        if calc_dicts:
            compiled_context += "\n=== VERIFIED CALCULATIONS (Computed Deterministically by System) ===\n"
            for c in calc_dicts:
                compiled_context += f"- {c['natural_language_summary']} [Formula: {c['formula']}]\n"

        if struct_res.facts:
            compiled_context += "\n=== VERIFIED STRUCTURED FACTS ===\n"
            for f in struct_res.facts[:10]:
                compiled_context += (
                    f"- {f.entity_name or 'Entity'} | {f.metric_name}: {f.raw_value} "
                    f"({f.reporting_period or ''}) [Source: {f.document_title}, P.{f.page_number}]\n"
                )

        # 7. Local LLM Generation & Honest Fallback
        t_llm_start = time.perf_counter()
        llm_provider = get_llm_provider()
        llm_status = "AVAILABLE"
        answer_text = ""

        system_prompt = (
            "You are an enterprise Geological & Mining Reporting Intelligence Officer for Coal India Limited (CIL) and CMPDI.\n"
            "Answer the question strictly based on the provided Evidence Chunks, Verified Structured Facts, and Verified Calculations.\n"
            "RULES:\n"
            "1. Ground all statements strictly in the provided evidence. Use bracketed citation numbers e.g. [1], [2].\n"
            "2. Never compute numbers yourself; use numbers directly from the evidence or [VERIFIED CALCULATIONS].\n"
            "3. If a cross-document conflict is noted, state both numbers and note that review is required.\n"
            "4. If the question cannot be answered from the evidence, respond EXACTLY with:\n"
            f"\"{STANDARD_REFUSAL_TEXT}\"\n"
            "5. STRICT CONSTRAINT: State ONLY verified factual quantities and findings directly reported. "
            "DO NOT infer or speculate regarding coal demand, resource sufficiency, depletion rates, future growth, "
            "or operational causes/consequences unless explicitly stated verbatim in the evidence.\n"
            "6. Keep the response concise, factual, and audit-grade."
        )

        user_prompt = f"{compiled_context}\n\nUser Question: {query}\n\nAuthoritative Answer:"

        try:
            llm_res: LLMResponse = llm_provider.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=256
            )
            answer_text = llm_res.content
        except (LLMUnavailableError, Exception) as e:
            logger.warning(f"Local LLM unavailable: {e}. Executing deterministic grounded synthesis.")
            llm_status = "UNAVAILABLE"
            answer_text = self._deterministic_grounded_synthesis(
                query=query,
                struct_res=struct_res,
                calc_dicts=calc_dicts,
                retrieved_results=retrieved_results
            )

        t_llm_ms = (time.perf_counter() - t_llm_start) * 1000.0

        # 8. Grounding Verification & Claim-Level Refinement
        t_ground_start = time.perf_counter()
        grounding_rep: GroundingReport = grounding_checker.check(
            answer_text=answer_text,
            evidence_texts=evidence_texts,
            structured_facts=fact_dicts,
            calculations=calc_dicts,
            top_retrieval_score=top_score,
            retrieved_chunks=retrieved_results
        )

        # If speculative inferences were detected, refine answer to retain ONLY verified factual claims
        if grounding_rep.has_speculative_inference and grounding_rep.refined_answer:
            logger.info(f"Refining answer to eliminate speculative inferences. Refined text: {grounding_rep.refined_answer}")
            answer_text = grounding_rep.refined_answer
            grounding_rep = grounding_checker.check(
                answer_text=answer_text,
                evidence_texts=evidence_texts,
                structured_facts=fact_dicts,
                calculations=calc_dicts,
                top_retrieval_score=top_score,
                retrieved_chunks=retrieved_results
            )

        # Bounded Retry if LLM produced unsupported answer
        if llm_status == "AVAILABLE" and grounding_rep.verification_status == "UNSUPPORTED":
            logger.info("Answer failed grounding check. Executing bounded retry.")
            retry_prompt = (
                f"{compiled_context}\n\nUser Question: {query}\n\n"
                f"CORRECTION NOTICE: Your previous answer contained assertions not supported by the evidence. "
                f"State only direct factual metrics or respond with: \"{STANDARD_REFUSAL_TEXT}\"."
            )
            try:
                retry_res = llm_provider.generate(
                    prompt=retry_prompt,
                    system_prompt=system_prompt,
                    temperature=0.0,
                    max_tokens=256
                )
                retry_rep = grounding_checker.check(
                    answer_text=retry_res.content,
                    evidence_texts=evidence_texts,
                    structured_facts=fact_dicts,
                    calculations=calc_dicts,
                    top_retrieval_score=top_score,
                    retrieved_chunks=retrieved_results
                )
                if retry_rep.has_speculative_inference and retry_rep.refined_answer:
                    retry_res.content = retry_rep.refined_answer
                    retry_rep = grounding_checker.check(
                        answer_text=retry_res.content,
                        evidence_texts=evidence_texts,
                        structured_facts=fact_dicts,
                        calculations=calc_dicts,
                        top_retrieval_score=top_score,
                        retrieved_chunks=retrieved_results
                    )
                if retry_rep.is_grounded or retry_rep.is_refusal:
                    answer_text = retry_res.content
                    grounding_rep = retry_rep
                else:
                    answer_text = STANDARD_REFUSAL_TEXT
                    grounding_rep.verification_status = "REFUSED"
            except Exception:
                answer_text = STANDARD_REFUSAL_TEXT
                grounding_rep.verification_status = "REFUSED"


        t_ground_ms = (time.perf_counter() - t_ground_start) * 1000.0

        # 9. Persist Query, Answer, Citations in Relational DB
        t_persist_start = time.perf_counter()
        q_record = QueryRecord(
            user_id=current_user.id,
            organization_id=current_user.organization_id or "CENTRAL",
            query_text=query,
            normalized_query=norm_query.to_dict() if hasattr(norm_query, "to_dict") else norm_query.dict(),
            filters_applied=filters
        )
        db.add(q_record)
        db.flush()

        a_record = AnswerRecord(
            query_id=q_record.id,
            answer_text=answer_text,
            confidence_score=grounding_rep.confidence_score,
            verification_status=grounding_rep.verification_status,
            latency_ms=(time.perf_counter() - overall_start) * 1000.0,
            llm_provider=llm_provider.model_info().provider if llm_status == "AVAILABLE" else "none",
            llm_model=llm_provider.model_info().model_name if llm_status == "AVAILABLE" else "deterministic_fallback",
            arithmetic_used=bool(calc_dicts),
            conflict_detected=bool(struct_res.conflict_warning)
        )
        db.add(a_record)
        db.flush()

        for c in citations_list:
            citation_rec = AnswerCitation(
                answer_id=a_record.id,
                chunk_id=None,
                document_id=c.document_id,
                page_number=c.page_number,
                excerpt=c.excerpt,
                score=c.relevance_score,
                table_provenance=c.table_provenance
            )
            db.add(citation_rec)

        db.commit()
        t_persist_ms = (time.perf_counter() - t_persist_start) * 1000.0

        # 10. Audit Logging
        log_audit_event(
            db=db,
            action="QA_QUERY_EXECUTED",
            actor_id=current_user.id,
            organization_id=current_user.organization_id or "CENTRAL",
            object_type="qa_query",
            object_id=q_record.id,
            details={
                "query": query,
                "verification_status": grounding_rep.verification_status,
                "confidence_score": grounding_rep.confidence_score,
                "llm_status": llm_status,
                "arithmetic_used": bool(calc_dicts),
                "conflict_detected": bool(struct_res.conflict_warning),
                "citations_count": len(citations_list)
            }
        )

        overall_ms = (time.perf_counter() - overall_start) * 1000.0

        return {
            "query_id": q_record.id,
            "answer_id": a_record.id,
            "query": query,
            "answer": answer_text,
            "verification_status": grounding_rep.verification_status,
            "confidence_score": grounding_rep.confidence_score,
            "llm_status": llm_status,
            "llm_provider": a_record.llm_provider,
            "llm_model": a_record.llm_model,
            "arithmetic_used": a_record.arithmetic_used,
            "conflict_detected": a_record.conflict_detected,
            "citations": [c.dict() for c in citations_list],
            "structured_facts": [f.dict() for f in struct_res.facts],
            "calculations": calc_dicts,
            "conflict_warning": struct_res.conflict_warning.dict() if struct_res.conflict_warning else None,
            "claim_audit": [c.dict() for c in grounding_rep.claims],
            "unsupported_claims": grounding_rep.unsupported_claims,
            "citation_binding_valid": grounding_rep.citation_binding_valid,
            "mismatched_citations": grounding_rep.mismatched_citations,
            "trace": {
                "trace_id": search_res.get("trace", {}).get("trace_id"),
                "total_latency_ms": round(overall_ms, 2),
                "timings_ms": {
                    "normalization": round(t_norm_ms, 2),
                    "structured_lookup": round(t_struct_ms, 2),
                    "hybrid_retrieval": round(t_retrieval_ms, 2),
                    "arithmetic_engine": round(t_calc_ms, 2),
                    "llm_inference": round(t_llm_ms, 2),
                    "grounding_check": round(t_ground_ms, 2),
                    "persistence": round(t_persist_ms, 2)
                }
            }
        }

    def _deterministic_grounded_synthesis(
        self,
        query: str,
        struct_res: StructuredLookupResult,
        calc_dicts: List[Dict[str, Any]],
        retrieved_results: List[Dict[str, Any]]
    ) -> str:
        """
        Deterministic, extractive answer synthesis used when the local LLM is offline.
        Ensures the system never fabricates answers and clearly reports factual data.
        """
        sections = []

        if struct_res.conflict_warning:
            sections.append(
                f"**Cross-Document Conflict Advisory**\n"
                f"{struct_res.conflict_warning.message}\n"
                f"Status: **CONFLICT_REQUIRES_REVIEW** (Flagged in Verification Queue)."
            )

        if calc_dicts:
            calc_lines = []
            for c in calc_dicts:
                calc_lines.append(f"- **{c['natural_language_summary']}** [Formula: `{c['formula']}`]")
            sections.append("**Verified Calculations (Computed Deterministically):**\n" + "\n".join(calc_lines))

        if struct_res.facts:
            fact_lines = []
            for idx, f in enumerate(struct_res.facts[:5], start=1):
                p_str = f"Page {f.page_number}" if f.page_number else "N/A"
                fact_lines.append(
                    f"- **{f.entity_name or 'Entity'}** - {f.metric_name}: `{f.raw_value}` "
                    f"({f.reporting_period or 'FY N/A'}) [Source: *{f.document_title}*, {p_str}] [{idx}]"
                )
            sections.append("**Verified Structured Metrics:**\n" + "\n".join(fact_lines))

        if retrieved_results and not struct_res.facts and not calc_dicts:
            snippets = []
            for idx, r in enumerate(retrieved_results[:2], start=1):
                t_str = f"Page {r.get('page_number', 1)}"
                snippet = r.get("source_text", "").strip().replace("\n", " ")[:200]
                snippets.append(f"[{idx}] *\"{snippet}...\"* (Source: *{r.get('title')}*, {t_str})")
            sections.append("**Retrieved Source Evidence:**\n" + "\n".join(snippets))

        ollama_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        sections.append(
            f"\n*(Notice: Local LLM service is offline or unreachable at {ollama_url}. "
            "Evidence records and verified calculations above are compiled deterministically.)*"
        )

        return "\n\n".join(sections)

    def _persist_and_return_refusal(
        self,
        db: Session,
        query: str,
        current_user: User,
        norm_query: NormalizedQuery,
        filters: Dict[str, Any],
        reason: str,
        overall_start: float,
        search_res: Dict[str, Any]
    ) -> Dict[str, Any]:
        q_record = QueryRecord(
            user_id=current_user.id,
            organization_id=current_user.organization_id or "CENTRAL",
            query_text=query,
            normalized_query=norm_query.to_dict() if hasattr(norm_query, "to_dict") else norm_query.dict(),
            filters_applied=filters
        )
        db.add(q_record)
        db.flush()

        a_record = AnswerRecord(
            query_id=q_record.id,
            answer_text=STANDARD_REFUSAL_TEXT,
            confidence_score=1.0,
            verification_status="REFUSED",
            latency_ms=(time.perf_counter() - overall_start) * 1000.0,
            llm_provider="none",
            llm_model="refusal_policy",
            arithmetic_used=False,
            conflict_detected=False
        )
        db.add(a_record)
        db.commit()

        log_audit_event(
            db=db,
            action="QA_QUERY_REFUSED",
            actor_id=current_user.id,
            organization_id=current_user.organization_id or "CENTRAL",
            object_type="qa_query",
            object_id=q_record.id,
            details={"query": query, "reason": reason}
        )

        overall_ms = (time.perf_counter() - overall_start) * 1000.0

        return {
            "query_id": q_record.id,
            "answer_id": a_record.id,
            "query": query,
            "answer": STANDARD_REFUSAL_TEXT,
            "verification_status": "REFUSED",
            "confidence_score": 1.0,
            "llm_status": "AVAILABLE",
            "llm_provider": "none",
            "llm_model": "refusal_policy",
            "arithmetic_used": False,
            "conflict_detected": False,
            "citations": [],
            "structured_facts": [],
            "calculations": [],
            "conflict_warning": None,
            "trace": {
                "trace_id": search_res.get("trace", {}).get("trace_id"),
                "total_latency_ms": round(overall_ms, 2),
                "refusal_reason": reason
            }
        }


qa_service = QAService()
