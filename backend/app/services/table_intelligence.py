from dataclasses import dataclass, field
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple
from app.services.parsers.base import ParsedTable

CONTINUATION_KEYWORDS = [
    r"cont(?:inue)?d?\.?",
    r"cont\.",
    r"continued",
    r"continuation",
    r"\(cont(?:inue)?d?\.?\)",
    r"part\s*\d+",
]

DISTINCT_TABLE_KEYWORDS = [
    r"table\s*\d+",
    r"statement\s*\d+",
    r"annexure\s*[a-z0-9]+",
    r"appendix\s*[a-z0-9]+",
    r"schedule\s*[a-z0-9]+",
]

SUMMARY_KEYWORDS = [
    "total",
    "grand total",
    "summary",
    "sub-total",
    "sub total",
    "net total",
    "overall"
]

@dataclass
class ContinuationEvaluation:
    score: float
    has_repeated_headers: bool
    strip_row_0: bool
    hard_gate_passed: bool
    gate_failure_reason: Optional[str] = None
    signals: Dict[str, float] = field(default_factory=dict)
    summary_text: str = ""

class TableIntelligenceService:
    """
    Deterministic Intelligence Service for multi-page table continuation analysis.
    Implements a rigorous two-pass document-wide algorithm with explicit signal weights,
    hard-gating safeguards, row provenance tracking, and evidence persistence.
    """

    # Weights
    W_BASE = 0.15
    W_HDR_REPEATED = 0.35
    W_HDR_IDENTICAL = 0.20
    W_HDR_HEADLESS = 0.25
    W_HDR_PARTIAL = 0.10
    W_HDR_CONTRADICT = -0.40
    W_CUE_CAPTION = 0.35
    W_CTX_IDENTICAL_CAPTION = 0.25
    W_CTX_TOP_OF_PAGE = 0.10
    W_ALIGN_TYPES = 0.10
    P_DIFF_CAPTION = -0.50

    # Decision Thresholds
    THRESH_MERGE = 0.70
    THRESH_REVIEW = 0.35

    def detect_continuations(self, tables: List[ParsedTable]) -> List[ParsedTable]:
        """
        Two-pass document-wide continuation analysis:
        Pass 1: Evaluate candidate table pairs, compute scores, and discover logical clusters.
        Pass 2: Sort cluster members by (page, index) and assign contiguous part numbers and total parts.
        """
        if not tables:
            return []

        # Sort physical tables in document reading order
        sorted_tables = sorted(tables, key=lambda t: (t.page_number, t.table_index))

        # Initialize defaults
        for t in sorted_tables:
            if not t.logical_table_id:
                t.logical_table_id = str(uuid.uuid4())
            t.part_number = 1
            t.total_parts = 1
            t.is_continuation = False
            t.continuation_status = "STANDALONE"
            t.continuation_confidence = 1.0
            if not t.row_pages:
                t.row_pages = [t.page_number] * len(t.rows)

        # PASS 1: Cluster discovery
        # logical_clusters: logical_table_id -> List of table indices in sorted_tables
        logical_clusters: Dict[str, List[int]] = {}
        active_logical_id = sorted_tables[0].logical_table_id
        logical_clusters[active_logical_id] = [0]

        for i in range(1, len(sorted_tables)):
            prev_t = sorted_tables[i - 1]
            curr_t = sorted_tables[i]

            eval_res = self.evaluate_candidate_pair(prev_t, curr_t)

            # Store evaluated signals in metadata for auditing and verification
            curr_t.metadata["continuation_signals"] = {
                "score": eval_res.score,
                "hard_gate_passed": eval_res.hard_gate_passed,
                "gate_failure_reason": eval_res.gate_failure_reason,
                "signals": eval_res.signals,
                "summary": eval_res.summary_text
            }

            if eval_res.score >= self.THRESH_MERGE:
                # Merge into previous table's logical cluster
                curr_t.is_continuation = True
                curr_t.continuation_status = "AUTO_MERGED"
                curr_t.continuation_confidence = round(eval_res.score, 2)
                curr_t.logical_table_id = prev_t.logical_table_id
                curr_t.continuation_of_idx = prev_t.table_index
                curr_t.has_repeated_headers = eval_res.has_repeated_headers

                if eval_res.strip_row_0 and len(curr_t.rows) > 0:
                    curr_t.rows = curr_t.rows[1:]
                    if curr_t.row_pages and len(curr_t.row_pages) > 0:
                        curr_t.row_pages = curr_t.row_pages[1:]

                # Inherit headers if current table was headless
                if not curr_t.headers and prev_t.headers:
                    curr_t.headers = list(prev_t.headers)

                logical_clusters[curr_t.logical_table_id].append(i)

            elif self.THRESH_REVIEW <= eval_res.score < self.THRESH_MERGE:
                # Ambiguous continuation -> Do NOT merge silently!
                curr_t.continuation_status = "REVIEW_REQUIRED"
                curr_t.continuation_confidence = round(eval_res.score, 2)
                curr_t.logical_table_id = str(uuid.uuid4())
                curr_t.is_continuation = False
                logical_clusters[curr_t.logical_table_id] = [i]

            else:
                # Standalone table
                curr_t.continuation_status = "STANDALONE"
                curr_t.continuation_confidence = 1.0
                curr_t.logical_table_id = str(uuid.uuid4())
                curr_t.is_continuation = False
                logical_clusters[curr_t.logical_table_id] = [i]

        # PASS 2: Part numbering and total_parts assignment across clusters
        for log_id, member_indices in logical_clusters.items():
            total_parts = len(member_indices)
            # Sort cluster members strictly by page and index
            member_indices.sort(key=lambda idx: (sorted_tables[idx].page_number, sorted_tables[idx].table_index))
            for part_idx, table_idx in enumerate(member_indices):
                tbl = sorted_tables[table_idx]
                tbl.part_number = part_idx + 1
                tbl.total_parts = total_parts
                if part_idx > 0:
                    tbl.is_continuation = True
                    tbl.continuation_of_idx = sorted_tables[member_indices[part_idx - 1]].table_index

        return sorted_tables

    def evaluate_candidate_pair(
        self, prev: ParsedTable, curr: ParsedTable
    ) -> ContinuationEvaluation:
        """
        Evaluates continuation suitability between prev and curr table using the
        mathematical scoring formula and explicit signal weights.
        """
        # Hard Gating Rule 1: Page Adjacency (must be strictly next page)
        if curr.page_number != prev.page_number + 1:
            return ContinuationEvaluation(
                score=0.0,
                has_repeated_headers=False,
                strip_row_0=False,
                hard_gate_passed=False,
                gate_failure_reason=f"Pages are not strictly adjacent (prev: {prev.page_number}, curr: {curr.page_number})"
            )

        # Hard Gating Rule 2: Column count match
        prev_cols = len(prev.headers) if prev.headers else (len(prev.rows[0]) if prev.rows else 0)
        curr_cols = len(curr.headers) if curr.headers else (len(curr.rows[0]) if curr.rows else 0)

        if prev_cols == 0 or curr_cols == 0 or prev_cols != curr_cols:
            return ContinuationEvaluation(
                score=0.0,
                has_repeated_headers=False,
                strip_row_0=False,
                hard_gate_passed=False,
                gate_failure_reason=f"Column counts mismatch (prev: {prev_cols}, curr: {curr_cols})"
            )

        # Hard Gating Rule 3: Terminal summary row in predecessor
        if prev.rows:
            last_row_text = " ".join(str(c).lower() for c in prev.rows[-1])
            if any(re.search(rf"\b{kw}\b", last_row_text) for kw in SUMMARY_KEYWORDS):
                return ContinuationEvaluation(
                    score=0.0,
                    has_repeated_headers=False,
                    strip_row_0=False,
                    hard_gate_passed=False,
                    gate_failure_reason=f"Predecessor table ends with terminal summary row ('{prev.rows[-1][0]}')"
                )

        # Hard Gating Rule 4: Distinct table numbering in captions (e.g. Table 1 vs Table 2)
        prev_cap = (prev.caption or "").strip().lower()
        curr_cap = (curr.caption or "").strip().lower()
        prev_tbl_match = re.search(r"table\s*(\d+)", prev_cap)
        curr_tbl_match = re.search(r"table\s*(\d+)", curr_cap)
        if prev_tbl_match and curr_tbl_match:
            if prev_tbl_match.group(1) != curr_tbl_match.group(1):
                return ContinuationEvaluation(
                    score=0.0,
                    has_repeated_headers=False,
                    strip_row_0=False,
                    hard_gate_passed=False,
                    gate_failure_reason=f"Distinct table numbers in captions ('{prev.caption}' vs '{curr.caption}')"
                )

        # Hard gating passed -> calculate weighted signals
        signals: Dict[str, float] = {}
        score = self.W_BASE
        signals["base_adjacency_and_cols"] = self.W_BASE

        has_repeated_headers = False
        strip_row_0 = False

        norm_prev_headers = [str(h).strip().lower() for h in prev.headers]
        norm_curr_headers = [str(h).strip().lower() for h in curr.headers]

        # 1. Header Analysis
        # Check if row 0 of curr contains repeated headers
        if curr.rows and norm_prev_headers:
            row0_norm = [str(c).strip().lower() for c in curr.rows[0]]
            if row0_norm == norm_prev_headers:
                has_repeated_headers = True
                strip_row_0 = True
                score += self.W_HDR_REPEATED
                signals["repeated_header_row0"] = self.W_HDR_REPEATED
            else:
                set_prev = set(norm_prev_headers)
                set_r0 = set(row0_norm)
                sim = len(set_prev & set_r0) / max(len(set_prev | set_r0), 1)
                if sim >= 0.70:
                    has_repeated_headers = True
                    strip_row_0 = True
                    score += self.W_HDR_REPEATED
                    signals["repeated_header_row0"] = self.W_HDR_REPEATED

        if not strip_row_0:
            if not norm_curr_headers:
                # No headers on successor (headless continuation)
                score += self.W_HDR_HEADLESS
                signals["headless_continuation"] = self.W_HDR_HEADLESS
            elif norm_curr_headers == norm_prev_headers:
                score += self.W_HDR_IDENTICAL
                signals["identical_declared_headers"] = self.W_HDR_IDENTICAL
            else:
                set_prev = set(norm_prev_headers)
                set_curr = set(norm_curr_headers)
                sim = len(set_prev & set_curr) / max(len(set_prev | set_curr), 1)
                if sim >= 0.60:
                    score += self.W_HDR_PARTIAL
                    signals["partial_header_match"] = self.W_HDR_PARTIAL
                elif sim < 0.30:
                    score += self.W_HDR_CONTRADICT
                    signals["header_contradiction"] = self.W_HDR_CONTRADICT

        # 2. Continuation Cue Analysis
        is_cont_cue = any(re.search(kw, curr_cap) for kw in CONTINUATION_KEYWORDS) if curr_cap else False
        if is_cont_cue:
            score += self.W_CUE_CAPTION
            signals["caption_continuation_cue"] = self.W_CUE_CAPTION

        # 3. Contextual Analysis
        if curr_cap and prev_cap and curr_cap == prev_cap:
            score += self.W_CTX_IDENTICAL_CAPTION
            signals["identical_caption"] = self.W_CTX_IDENTICAL_CAPTION

        if curr.table_index == 0:
            score += self.W_CTX_TOP_OF_PAGE
            signals["top_of_page_position"] = self.W_CTX_TOP_OF_PAGE

        # Distinct caption penalty: if caption exists and has no continuation cue and differs from prev
        if curr_cap and not is_cont_cue and (prev_cap != curr_cap):
            score += self.P_DIFF_CAPTION
            signals["distinct_caption_penalty"] = self.P_DIFF_CAPTION

        # 4. Structural Alignment
        if prev.rows and curr.rows:
            sample_curr = curr.rows[1] if (strip_row_0 and len(curr.rows) > 1) else curr.rows[0]
            sample_prev = prev.rows[-1]
            matches = 0
            for c_idx in range(min(len(sample_prev), len(sample_curr))):
                p_num = str(sample_prev[c_idx]).replace(".", "").replace(",", "").replace("-", "").isdigit()
                c_num = str(sample_curr[c_idx]).replace(".", "").replace(",", "").replace("-", "").isdigit()
                if p_num == c_num:
                    matches += 1
            if matches == prev_cols:
                score += self.W_ALIGN_TYPES
                signals["column_datatype_alignment"] = self.W_ALIGN_TYPES

        final_score = min(max(round(score, 2), 0.0), 1.0)
        summary = f"Score {final_score:.2f}: " + ", ".join(f"{k}={v:+.2f}" for k, v in signals.items())

        return ContinuationEvaluation(
            score=final_score,
            has_repeated_headers=has_repeated_headers,
            strip_row_0=strip_row_0,
            hard_gate_passed=True,
            signals=signals,
            summary_text=summary
        )

table_intelligence_service = TableIntelligenceService()

