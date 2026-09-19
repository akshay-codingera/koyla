r"""
Class-based Term Frequency-Inverse Document Frequency (c-TF-IDF) Engine.

Mathematical Formulation:
-------------------------
Let C be the total number of topic classes (excluding outliers).
For each class c in {0, ..., C-1}:
1. Aggregate all cleaned text chunks belonging to class c into a composite document D_c.
2. For each term t in the global vocabulary V:
   f_{t, c} = raw frequency of term t in composite document D_c.
3. Total term-frequency mass of class c:
   W_c = \sum_{t' \in V} f_{t', c}
4. Normalized within-class term frequency:
   tf(t, c) = f_{t, c} / W_c    (if W_c > 0 else 0.0)
5. Average word count per class across all topic classes:
   A = (1 / C) * \sum_{c'=0}^{C-1} W_{c'}
6. Total frequency of term t across all classes:
   F_t = \sum_{c'=0}^{C-1} f_{t, c'}
7. Smoothed inverse class frequency:
   icf(t) = log(1.0 + A / F_t)  (natural logarithm)
8. Deterministic composite c-TF-IDF weight:
   W_{t, c} = tf(t, c) * icf(t) = (f_{t, c} / W_c) * log(1.0 + A / F_t)

Deterministic Sorting and Tie-breaking:
---------------------------------------
Terms within a class are ranked by (-weight, term) so identical scores
are deterministically resolved alphabetically.
"""

import math
import re
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple, Optional
from app.services.topics.domain_vocabulary import DOMAIN_STOPWORDS, STATUTORY_TERMS_PRESERVED

class ClassTfidfTransformer:
    """
    Computes deterministic class-based TF-IDF weights and descriptive labels
    from clustered text items.
    """

    def __init__(self, min_df: int = 1, max_df_ratio: float = 0.95):
        self.min_df = min_df
        self.max_df_ratio = max_df_ratio

    def fit_transform(
        self,
        cluster_docs: Dict[int, List[Dict[str, Any]]],
        top_k_terms: int = 10,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Compute c-TF-IDF for each class.
        cluster_docs: mapping from cluster_id (int >= 0) to list of corpus items.
        Returns:
            Dict[cluster_id, {
                "top_terms": List[Dict[str, Any]], # {term, weight, rank, frequency, document_count}
                "label": str,
                "word_mass": int,
            }]
        """
        valid_clusters = [c for c in sorted(cluster_docs.keys()) if c >= 0 and len(cluster_docs[c]) > 0]
        C = len(valid_clusters)
        if C == 0:
            return {}

        # 1. Tokenize and count frequencies per class and document occurrences
        class_term_counts: Dict[int, Counter] = {}
        class_doc_counts: Dict[int, Counter] = {}
        class_total_words: Dict[int, int] = {}
        global_term_counts: Counter = Counter()
        global_doc_counts: Counter = Counter()

        for c in valid_clusters:
            items = cluster_docs[c]
            c_counter = Counter()
            c_doc_counter = Counter()
            seen_in_doc_terms = set()

            for item in items:
                text = item.get("cleaned_text") or item.get("raw_text") or ""
                tokens = self._tokenize(text)
                c_counter.update(tokens)
                doc_id = item.get("document_id") or item.get("chunk_id")
                unique_doc_tokens = set(tokens)
                for t in unique_doc_tokens:
                    c_doc_counter[t] += 1
                    seen_in_doc_terms.add(t)

            class_term_counts[c] = c_counter
            class_doc_counts[c] = c_doc_counter
            mass = sum(c_counter.values())
            class_total_words[c] = mass
            global_term_counts.update(c_counter)
            for t in seen_in_doc_terms:
                global_doc_counts[t] += 1

        # 2. Compute average class word mass A
        total_all_words = sum(class_total_words.values())
        A = total_all_words / float(C) if C > 0 else 0.0

        # 3. Filter vocabulary by min_df and stopwords
        filtered_vocab = set()
        for term, f_t in global_term_counts.items():
            if f_t < self.min_df:
                continue
            if term in DOMAIN_STOPWORDS and term not in STATUTORY_TERMS_PRESERVED:
                continue
            filtered_vocab.add(term)

        # 4. Compute c-TF-IDF weights per class
        results: Dict[int, Dict[str, Any]] = {}

        for c in valid_clusters:
            c_counts = class_term_counts[c]
            c_docs = class_doc_counts[c]
            W_c = class_total_words[c]

            scored_terms: List[Tuple[str, float, int, int]] = []

            for term in filtered_vocab:
                f_tc = c_counts.get(term, 0)
                if f_tc == 0:
                    continue
                tf = f_tc / float(W_c) if W_c > 0 else 0.0
                F_t = global_term_counts[term]
                icf = math.log(1.0 + (A / float(F_t))) if F_t > 0 else 0.0
                weight = tf * icf
                doc_cnt = c_docs.get(term, 0)
                scored_terms.append((term, weight, f_tc, doc_cnt))

            # Deterministic sorting: highest weight first, alphabetical tie-breaker
            scored_terms.sort(key=lambda x: (-x[1], x[0]))

            top_records = []
            for rank_idx, (term, weight, freq, d_cnt) in enumerate(scored_terms[:top_k_terms], start=1):
                top_records.append({
                    "term": term,
                    "weight": round(weight, 6),
                    "rank": rank_idx,
                    "frequency": freq,
                    "document_count": d_cnt,
                })

            label = self.generate_label(top_records)

            results[c] = {
                "top_terms": top_records,
                "label": label,
                "word_mass": W_c,
            }

        return results

    def _tokenize(self, text: str) -> List[str]:
        """Deterministic tokenization stripping punctuation and numbers without unit."""
        raw_tokens = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
        tokens = []
        for t in raw_tokens:
            cleaned = t.strip("-_")
            if len(cleaned) >= 2 and not cleaned.isdigit():
                tokens.append(cleaned)
        return tokens

    def generate_label(self, top_terms: List[Dict[str, Any]]) -> str:
        """
        Generate a descriptive domain topic label from top terms.
        Never produces generic labels like 'Topic 1'.
        """
        if not top_terms:
            return "General Geological & Mining Operations"

        # Select top 3-4 terms with highest weights
        selected_terms = [t["term"] for t in top_terms[:4]]
        # Capitalize and format nicely
        title_terms = [t.title() for t in selected_terms]

        if len(title_terms) == 1:
            return f"{title_terms[0]} Operations"
        elif len(title_terms) == 2:
            return f"{title_terms[0]} & {title_terms[1]}"
        elif len(title_terms) == 3:
            return f"{title_terms[0]}, {title_terms[1]} & {title_terms[2]}"
        else:
            return f"{title_terms[0]} & {title_terms[1]} ({title_terms[2]}, {title_terms[3]})"

c_tfidf_transformer = ClassTfidfTransformer()
