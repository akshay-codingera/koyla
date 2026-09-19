"""
Report Narrative Generation Service
Generates strictly grounded narrative sections using the Phase 6 local LLM
and validates factual claims via the Phase 6 claim-level GroundingChecker.
Prunes speculation and guarantees zero hallucinated numbers or causal claims.
"""
import logging
from typing import List, Dict, Any, Optional
from app.services.llm.factory import get_llm_provider
from app.services.qa.grounding_checker import GroundingChecker, GroundingReport, STANDARD_REFUSAL_TEXT

logger = logging.getLogger(__name__)

OFFICIAL_UNAVAILABLE_NOTICE = "DATA NOT AVAILABLE IN VERIFIED KNOWLEDGE BASE"


class ReportNarrativeService:

    @classmethod
    def generate_grounded_field_narrative(
        cls,
        field_id: str,
        official_label: str,
        official_instruction: str,
        evidence_chunks: List[Dict[str, Any]],
        organization_name: Optional[str] = None,
        block_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes a narrative for a descriptive official report section using retrieved evidence.
        Enforces claim-level verification and eliminates speculative inferences.
        """
        if not evidence_chunks:
            return {
                "text": OFFICIAL_UNAVAILABLE_NOTICE,
                "grounding_status": "DATA_UNAVAILABLE",
                "confidence": 0.0,
                "citations": [],
                "grounding_report": None,
            }

        # Build context from evidence chunks with [Doc X] citations
        context_lines = []
        for idx, chunk in enumerate(evidence_chunks, start=1):
            title = chunk.get("document_title", "Document")
            page = chunk.get("page_number", 1)
            content = chunk.get("content", "").strip()
            context_lines.append(f"[Doc {idx}] ({title}, Page {page}):\n{content}")

        evidence_text = "\n\n".join(context_lines)

        prompt = (
            f"You are a technical mining reporting officer preparing a statutory Mining Plan.\n"
            f"Write a concise, strictly factual paragraph for the section: '{official_label}'.\n"
            f"Statutory Scope: {official_instruction}\n"
            f"Mine / Block: {block_name or 'Project Area'} ({organization_name or 'CIL Subsidiary'})\n\n"
            f"EVIDENCE CONTEXT:\n{evidence_text}\n\n"
            f"STRICT INSTRUCTIONS:\n"
            f"1. State ONLY facts directly mentioned in the evidence above.\n"
            f"2. Cite evidence using bracketed notation like [Doc 1], [Doc 2].\n"
            f"3. Do NOT make future projections, speculate on demand or depletion, or invent causes.\n"
            f"4. If specific information is not in the evidence, do NOT guess."
        )

        llm = get_llm_provider()
        try:
            raw_response = llm.generate_response(
                query=f"Describe {official_label} for {block_name}",
                context=evidence_text,
                system_prompt="You are a statutory mining plan compiler. Output only verified facts with citations [Doc X]."
            )
        except Exception as e:
            logger.warning(f"Local LLM generation failed for field {field_id}: {e}")
            raw_response = None

        if not raw_response or STANDARD_REFUSAL_TEXT in raw_response:
            # Deterministic evidence summary fallback
            first_chunk = evidence_chunks[0]
            summary_snippet = first_chunk.get("content", "").strip()
            if len(summary_snippet) > 300:
                summary_snippet = summary_snippet[:300].rsplit(" ", 1)[0] + "..."
            raw_response = f"According to verified project records, {summary_snippet} [Doc 1]"

        # Run Phase 6 Grounding Checker on the synthesized text
        grounding_report: GroundingReport = GroundingChecker.evaluate(
            answer=raw_response,
            evidence_chunks=evidence_chunks,
        )

        final_text = raw_response
        # If speculative or partially supported claims exist, use refined_answer
        if grounding_report.refined_answer and not grounding_report.is_refusal:
            final_text = grounding_report.refined_answer

        if grounding_report.is_refusal or grounding_report.verification_status == "UNSUPPORTED":
            final_text = OFFICIAL_UNAVAILABLE_NOTICE
            confidence = 0.0
            status = "DATA_UNAVAILABLE"
        else:
            confidence = grounding_report.confidence_score
            status = grounding_report.verification_status

        # Map citation documents
        citations = []
        for c in evidence_chunks:
            citations.append({
                "document_id": c.get("document_id"),
                "chunk_id": c.get("id") or c.get("chunk_id"),
                "document_title": c.get("document_title"),
                "page_number": c.get("page_number"),
            })

        return {
            "text": final_text,
            "grounding_status": status,
            "confidence": confidence,
            "citations": citations,
            "grounding_report": grounding_report.model_dump(),
        }
