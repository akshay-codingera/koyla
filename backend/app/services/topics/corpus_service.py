"""
Corpus selection and assembly service for Topic Analysis.
Extracts filtered documents and chunks, preserving metadata and statutory integrity.
Database raw chunk content is strictly read-only.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.document import Document
from app.models.chunk import Chunk, Embedding
from app.models.organization import Organization
from app.models.extraction import ExtractedField
from app.services.topics.preprocessor import preprocess_text

logger = logging.getLogger(__name__)

class CorpusService:
    """
    Builds structured topic modeling corpora from existing documents and chunks.
    """

    def build_corpus(
        self,
        db: Session,
        allowed_org_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit_chunks: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Select chunks and assemble corpus items based on multi-criteria filters.
        Strictly enforces tenant isolation via allowed_org_ids.
        """
        filters = dict(filters or {})
        effective_filters: Dict[str, Any] = {}

        # Base query joining Chunk with Document and Organization
        q = db.query(
            Chunk.id.label("chunk_id"),
            Chunk.document_id,
            Chunk.chunk_index,
            Chunk.page_number,
            Chunk.chunk_type,
            Chunk.section_heading,
            Chunk.content.label("raw_content"),
            Chunk.metadata_json.label("chunk_metadata"),
            Document.title.label("doc_title"),
            Document.document_type,
            Document.source_tier,
            Document.created_at.label("doc_created_at"),
            Organization.id.label("org_id"),
            Organization.code.label("org_code"),
            Organization.name.label("org_name"),
            Organization.org_type.label("org_type"),
        ).join(
            Document, Document.id == Chunk.document_id
        ).join(
            Organization, Organization.id == Document.organization_id
        )

        # 1. Mandatory Server-Side Organization Isolation
        if allowed_org_ids is not None:
            q = q.filter(Document.organization_id.in_(allowed_org_ids))
            effective_filters["allowed_org_ids"] = sorted(allowed_org_ids)

        # 2. Specific Organization Scope
        if filters.get("organization_id"):
            org_id = filters["organization_id"]
            # Ensure requested org_id is permitted
            if allowed_org_ids is not None and org_id not in allowed_org_ids:
                return {
                    "items": [],
                    "total_documents": 0,
                    "total_chunks": 0,
                    "document_ids": [],
                    "chunk_ids": [],
                    "effective_filters": effective_filters,
                }
            q = q.filter(Document.organization_id == org_id)
            effective_filters["organization_id"] = org_id

        # 3. Subsidiary Filter
        if filters.get("subsidiary"):
            sub = filters["subsidiary"].strip()
            q = q.filter(or_(
                Organization.code.ilike(f"%{sub}%"),
                Organization.name.ilike(f"%{sub}%"),
                Document.title.ilike(f"%{sub}%")
            ))
            effective_filters["subsidiary"] = sub

        # 4. Regional Institute Filter
        if filters.get("regional_institute"):
            ri = filters["regional_institute"].strip()
            q = q.filter(or_(
                Organization.code.ilike(f"%{ri}%"),
                Organization.name.ilike(f"%{ri}%"),
                Document.title.ilike(f"%{ri}%")
            ))
            effective_filters["regional_institute"] = ri

        # 5. Document Type Filter
        if filters.get("document_type"):
            doc_type = filters["document_type"].strip()
            q = q.filter(Document.document_type == doc_type)
            effective_filters["document_type"] = doc_type

        # 6. Specific Document IDs Filter
        if filters.get("document_ids"):
            doc_ids = filters["document_ids"]
            if isinstance(doc_ids, list):
                q = q.filter(Document.id.in_(doc_ids))
                effective_filters["document_ids"] = sorted(doc_ids)

        # 7. Fiscal Year Filter
        if filters.get("fiscal_year"):
            fy = filters["fiscal_year"].strip()
            clean_fy = re.sub(r'^FY\s*[-_]?', '', fy, flags=re.IGNORECASE)
            
            # Find documents matching fiscal year in ExtractedField
            matching_doc_ids = [
                row[0] for row in db.query(ExtractedField.document_id).filter(
                    ExtractedField.field_name.ilike("%fiscal_year%"),
                    or_(
                        ExtractedField.raw_value.ilike(f"%{fy}%"),
                        ExtractedField.raw_value.ilike(f"%{clean_fy}%")
                    )
                ).distinct().all()
            ]

            fy_conditions = [
                Document.title.ilike(f"%{fy}%"),
                Document.title.ilike(f"%{clean_fy}%"),
                Chunk.content.ilike(f"%{fy}%"),
                Chunk.content.ilike(f"%{clean_fy}%"),
            ]
            if matching_doc_ids:
                fy_conditions.append(Document.id.in_(matching_doc_ids))

            q = q.filter(or_(*fy_conditions))
            effective_filters["fiscal_year"] = fy

        # 8. Mine Name Filter
        if filters.get("mine_name"):
            mine = filters["mine_name"].strip()
            mine_doc_ids = [
                row[0] for row in db.query(ExtractedField.document_id).filter(
                    ExtractedField.field_name.ilike("%mine%"),
                    ExtractedField.raw_value.ilike(f"%{mine}%")
                ).distinct().all()
            ]

            mine_conditions = [
                Document.title.ilike(f"%{mine}%"),
                Chunk.content.ilike(f"%{mine}%"),
            ]
            if mine_doc_ids:
                mine_conditions.append(Document.id.in_(mine_doc_ids))

            q = q.filter(or_(*mine_conditions))
            effective_filters["mine_name"] = mine

        # 9. Block Name Filter
        if filters.get("block_name"):
            block = filters["block_name"].strip()
            block_doc_ids = [
                row[0] for row in db.query(ExtractedField.document_id).filter(
                    ExtractedField.field_name.ilike("%block%"),
                    ExtractedField.raw_value.ilike(f"%{block}%")
                ).distinct().all()
            ]

            block_conditions = [
                Document.title.ilike(f"%{block}%"),
                Chunk.content.ilike(f"%{block}%"),
            ]
            if block_doc_ids:
                block_conditions.append(Document.id.in_(block_doc_ids))

            q = q.filter(or_(*block_conditions))
            effective_filters["block_name"] = block

        # Order deterministically by document_id, chunk_index
        q = q.order_by(Document.id.asc(), Chunk.chunk_index.asc())

        if limit_chunks:
            q = q.limit(limit_chunks)

        rows = q.all()

        # Batch query existing embeddings for selected chunks
        chunk_ids_list = [r.chunk_id for r in rows]
        embedding_map: Dict[str, str] = {}
        if chunk_ids_list:
            emb_rows = db.query(Embedding.chunk_id, Embedding.id).filter(
                Embedding.chunk_id.in_(chunk_ids_list)
            ).all()
            for c_id, e_id in emb_rows:
                embedding_map[c_id] = e_id

        # Assemble corpus items with preprocessed text and rich metadata
        items: List[Dict[str, Any]] = []
        doc_ids_set = set()

        for r in rows:
            doc_ids_set.add(r.document_id)
            prep = preprocess_text(r.raw_content)

            chunk_meta = r.chunk_metadata or {}
            item = {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "chunk_index": r.chunk_index,
                "page_number": r.page_number,
                "chunk_type": r.chunk_type,
                "section_heading": r.section_heading,
                "organization_id": r.org_id,
                "organization_code": r.org_code,
                "organization_name": r.org_name,
                "subsidiary": r.org_code if r.org_type == "SUBSIDIARY" else chunk_meta.get("subsidiary"),
                "regional_institute": r.org_code if "RI" in (r.org_code or "") else chunk_meta.get("regional_institute"),
                "mine_name": chunk_meta.get("mine_name"),
                "block_name": chunk_meta.get("block_name"),
                "document_type": r.document_type,
                "fiscal_year": chunk_meta.get("fiscal_year"),
                "document_date": r.doc_created_at.isoformat() if r.doc_created_at else None,
                "raw_text": r.raw_content,  # Original text preserved, read-only
                "cleaned_text": prep["cleaned_text"],
                "token_count": prep["token_count"],
                "reduction_ratio": prep["reduction_ratio"],
                "has_embedding": r.chunk_id in embedding_map,
                "embedding_id": embedding_map.get(r.chunk_id),
            }
            items.append(item)

        unique_doc_ids = sorted(list(doc_ids_set))
        unique_chunk_ids = sorted(chunk_ids_list)

        return {
            "items": items,
            "total_documents": len(unique_doc_ids),
            "total_chunks": len(items),
            "document_ids": unique_doc_ids,
            "chunk_ids": unique_chunk_ids,
            "effective_filters": effective_filters,
        }

corpus_service = CorpusService()
