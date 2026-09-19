import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

STANDARD_REFUSAL_TEXT = "Insufficient verified evidence found in the selected knowledge base."

# Speculative and ungrounded extrapolation patterns that local LLMs tend to generate
SPECULATION_PATTERNS = [
    r'\b(?:indicates|suggests|implies|proves)\s+that\b',
    r'\bsufficient\s+(?:coal\s+)?resources\s+to\s+meet\b',
    r'\bmeet\s+(?:its\s+|the\s+)?(?:current\s+|future\s+)?demand\b',
    r'\bwithout\s+(?:any\s+)?(?:significant\s+)?depletion\b',
    r'\bdepletion\s+over\s+time\b',
    r'\boperational\s+(?:failure|breakdown|inefficiency|bottleneck)\b',
    r'\bdue\s+to\s+(?:bad\s+weather|mismanagement|negligence|strike|flooding)\b',
    r'\bcauses?\s+of\s+(?:the\s+)?(?:decline|increase|fluctuation)\b',
    r'\blong-term\s+sustainability\b',
    r'\bwill\s+(?:likely|continue\s+to)\s+(?:increase|decrease|exhaust)\b',
    r'\bdemand\s+growth\b',
]


class SentenceClaim(BaseModel):
    sentence_index: int
    text: str
    is_supported: bool
    is_speculative: bool = False
    numbers_found: List[str] = Field(default_factory=list)
    unsupported_reasons: List[str] = Field(default_factory=list)
    supporting_citations: List[int] = Field(default_factory=list)


class GroundingReport(BaseModel):
    is_grounded: bool
    verification_status: str  # 'SUPPORTED', 'PARTIALLY_SUPPORTED', 'UNSUPPORTED', 'REFUSED'
    confidence_score: float
    total_claims: int
    supported_claims: int
    unsupported_claims: List[str] = Field(default_factory=list)
    citations_found: int
    is_refusal: bool = False
    refusal_reason: Optional[str] = None
    claims: List[SentenceClaim] = Field(default_factory=list)
    refined_answer: Optional[str] = None
    has_speculative_inference: bool = False
    citation_binding_valid: bool = True
    mismatched_citations: List[str] = Field(default_factory=list)


class GroundingChecker:
    """
    Evaluates factual grounding at the sentence and claim level.
    Ensures every assertion is directly traceable to retrieved evidence or calculations.
    Rejects or flags speculative inferences regarding demand, depletion, and causality.
    """

    def _split_into_sentences(self, text: str) -> List[str]:
        # Split on sentence terminals (.!?\n) avoiding decimals in numbers e.g. 42.5
        raw_parts = re.split(r'(?<=[.!?])\s+|\n+', text)
        sentences = []
        for s in raw_parts:
            s_clean = s.strip()
            if not s_clean:
                continue
            # Remove markdown bullets or numbers at start e.g. '1. ', '- '
            s_clean = re.sub(r'^(?:\d+\.|\*|-)\s*', '', s_clean).strip()
            if len(s_clean) > 8:
                sentences.append(s_clean)
        return sentences

    def check(
        self,
        answer_text: str,
        evidence_texts: List[str],
        structured_facts: List[Dict[str, Any]],
        calculations: List[Dict[str, Any]],
        top_retrieval_score: float = 1.0,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> GroundingReport:
        clean_ans = answer_text.strip()

        # 1. Explicit Refusal Check
        if STANDARD_REFUSAL_TEXT.lower() in clean_ans.lower() or "insufficient verified evidence" in clean_ans.lower():
            return GroundingReport(
                is_grounded=True,
                verification_status="REFUSED",
                confidence_score=0.0,
                total_claims=0,
                supported_claims=0,
                citations_found=0,
                is_refusal=True,
                refusal_reason="Answer explicitly refused due to insufficient evidence"
            )

        # 2. Retrieval Confidence Floor
        if top_retrieval_score < settings.QA_REFUSAL_THRESHOLD and not structured_facts and not calculations:
            return GroundingReport(
                is_grounded=False,
                verification_status="REFUSED",
                confidence_score=0.0,
                total_claims=1,
                supported_claims=0,
                unsupported_claims=["Top retrieval similarity score below refusal threshold"],
                citations_found=0,
                is_refusal=True,
                refusal_reason=f"Top evidence score ({top_retrieval_score:.4f}) below refusal threshold ({settings.QA_REFUSAL_THRESHOLD})"
            )

        # 3. Construct Unified Evidence Corpus
        evidence_corpus = " ".join(evidence_texts).lower()
        for f in structured_facts:
            raw_val = str(f.get("raw_value") or "")
            norm_val = str(f.get("numeric_value") or "")
            evidence_corpus += f" {raw_val} {norm_val} {f.get('metric_name', '')} {f.get('entity_name', '')} {f.get('reporting_period', '')}"

        for c in calculations:
            evidence_corpus += f" {c.get('calculated_value')} {c.get('absolute_change')} {c.get('percentage_change')}% {c.get('natural_language_summary', '')}"

        evidence_corpus_lower = evidence_corpus.lower()

        # 4. Decompose Answer into Sentence-Level Claims
        sentences = self._split_into_sentences(clean_ans)
        claims: List[SentenceClaim] = []
        supported_sentences: List[str] = []
        unsupported_claims_summary: List[str] = []
        has_speculative_inference = False

        mismatched_citations: List[str] = []

        for idx, sent in enumerate(sentences, start=1):
            sent_lower = sent.lower()
            reasons = []

            # Extract numbers from sentence (excluding trivial citation tags like [1])
            raw_nums = re.findall(r'\b\d+(?:\.\d+)?%?\b', sent)
            substantive_numbers = [
                n for n in raw_nums
                if not (len(n) == 1 and f"[{n}]" in sent)
            ]

            # Check for speculative inference patterns
            is_speculative = False
            for pat in SPECULATION_PATTERNS:
                if re.search(pat, sent_lower):
                    # Check if evidence actually discusses this speculative topic verbatim
                    spec_terms = ["demand", "depletion", "depleted", "sufficiency", "sustainability", "failure"]
                    matched_spec_terms = [t for t in spec_terms if t in sent_lower]
                    unbacked_terms = [t for t in matched_spec_terms if t not in evidence_corpus_lower]
                    if unbacked_terms or "indicates that" in sent_lower or "sufficient" in sent_lower:
                        is_speculative = True
                        has_speculative_inference = True
                        reasons.append(f"Unsupported speculative inference: '{sent}'")
                        break

            # Check numerical fidelity
            for num in substantive_numbers:
                clean_num = num.rstrip('%')
                num_present = clean_num in evidence_corpus_lower or num in evidence_corpus_lower
                if not num_present:
                    try:
                        num_f = float(clean_num)
                        # Check calculations close float match
                        found_calc = False
                        for c in calculations:
                            for k in ["calculated_value", "absolute_change", "percentage_change"]:
                                if c.get(k) is not None and abs(c[k] - num_f) < 0.05:
                                    found_calc = True
                                    break
                            if found_calc:
                                break
                        if not found_calc:
                            reasons.append(f"Number '{num}' in sentence {idx} not found in evidence")
                    except ValueError:
                        reasons.append(f"Metric '{num}' in sentence {idx} not found in evidence")

            # Check citation-to-claim binding if citation markers are present in this sentence
            cite_matches = [int(c) for c in re.findall(r'\[(\d+)\]', sent)]
            if cite_matches and retrieved_chunks:
                for c_idx in cite_matches:
                    if 1 <= c_idx <= len(retrieved_chunks):
                        target_chunk = retrieved_chunks[c_idx - 1]
                        chunk_text = target_chunk.get("source_text", "").lower()
                        # Verify that the cited chunk actually supports at least one number or key term
                        if substantive_numbers:
                            num_in_chunk = any(n.rstrip('%') in chunk_text for n in substantive_numbers)
                            if not num_in_chunk:
                                mismatched_citations.append(
                                    f"Citation [{c_idx}] does not contain the numbers asserted in sentence: '{sent}'"
                                )
                    else:
                        mismatched_citations.append(f"Invalid citation index [{c_idx}] out of range")

            # Sentence without numbers: verify significant lexical overlap
            if not substantive_numbers and not is_speculative:
                substantive_words = [
                    w for w in re.findall(r'\b[a-zA-Z]{4,}\b', sent_lower)
                    if w not in ["based", "given", "evidence", "report", "reported", "include", "includes", "approximately"]
                ]
                if substantive_words:
                    overlap = [w for w in substantive_words if w in evidence_corpus_lower]
                    if len(overlap) / len(substantive_words) < 0.4:
                        reasons.append(f"General claim has insufficient overlap with evidence: '{sent}'")

            is_supported = (len(reasons) == 0 and not is_speculative)
            if is_supported:
                supported_sentences.append(sent)
            else:
                unsupported_claims_summary.extend(reasons)

            claims.append(SentenceClaim(
                sentence_index=idx,
                text=sent,
                is_supported=is_supported,
                is_speculative=is_speculative,
                numbers_found=substantive_numbers,
                unsupported_reasons=reasons,
                supporting_citations=cite_matches
            ))

        total_claims = max(len(claims), 1)
        supported_count = sum(1 for c in claims if c.is_supported)

        # 5. Determine Overall Grounding Status & Calibrated Confidence
        # Refined answer keeps only evidence-supported sentences
        refined_answer = " ".join(supported_sentences).strip() if supported_sentences else None

        citations_found = len(re.findall(r'\[(?:Doc|P\.|\d+|Citation)[^\]]*\]', clean_ans, re.IGNORECASE))
        citation_binding_valid = len(mismatched_citations) == 0

        # Confidence Calibration
        if supported_count == total_claims and total_claims > 0 and citation_binding_valid:
            # Fully supported claims (calibrated maximum 0.95 to avoid false mathematical certainty)
            confidence_score = 0.95 if citations_found >= 2 else 0.90
            verification_status = "SUPPORTED"
            is_grounded = True
        elif supported_count > 0:
            # Partially supported: factual claims present, but unsupported/speculative assertions occurred
            ratio = supported_count / total_claims
            confidence_score = round(ratio * 0.70, 2)
            verification_status = "PARTIALLY_SUPPORTED"
            is_grounded = False
        else:
            confidence_score = 0.10
            verification_status = "UNSUPPORTED"
            is_grounded = False

        return GroundingReport(
            is_grounded=is_grounded,
            verification_status=verification_status,
            confidence_score=confidence_score,
            total_claims=total_claims,
            supported_claims=supported_count,
            unsupported_claims=unsupported_claims_summary,
            citations_found=citations_found,
            is_refusal=False,
            claims=claims,
            refined_answer=refined_answer,
            has_speculative_inference=has_speculative_inference,
            citation_binding_valid=citation_binding_valid,
            mismatched_citations=mismatched_citations
        )


grounding_checker = GroundingChecker()
