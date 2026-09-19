"""
Deterministic hashing service for topic analysis corpus and configuration.
Provides SHA-256 fingerprinting across corpus items, effective filters, and model parameters.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional

def compute_corpus_hash(
    chunk_ids: List[str],
    document_ids: List[str],
    filters: Dict[str, Any],
    preprocessor_version: str = "1.0.0",
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    analysis_method: str = "FOUNDATION",
    parameters: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash identifying the exact corpus configuration.
    
    Guarantees:
    - Sorted ordering for chunk_ids and document_ids
    - Canonical JSON formatting with sorted keys for filters and parameters
    - Embedding model and preprocessor version binding
    """
    sorted_chunk_ids = sorted(list(set(chunk_ids)))
    sorted_document_ids = sorted(list(set(document_ids)))
    canonical_filters = json.dumps(filters or {}, sort_keys=True, separators=(",", ":"))
    canonical_parameters = json.dumps(parameters or {}, sort_keys=True, separators=(",", ":"))

    hasher = hashlib.sha256()
    hasher.update(f"chunks:{','.join(sorted_chunk_ids)}".encode("utf-8"))
    hasher.update(b"|")
    hasher.update(f"docs:{','.join(sorted_document_ids)}".encode("utf-8"))
    hasher.update(b"|")
    hasher.update(f"filters:{canonical_filters}".encode("utf-8"))
    hasher.update(b"|")
    hasher.update(f"preprocessor:{preprocessor_version}".encode("utf-8"))
    hasher.update(b"|")
    hasher.update(f"model:{embedding_model}".encode("utf-8"))
    hasher.update(b"|")
    hasher.update(f"method:{analysis_method}".encode("utf-8"))
    hasher.update(b"|")
    hasher.update(f"params:{canonical_parameters}".encode("utf-8"))

    return hasher.hexdigest()
