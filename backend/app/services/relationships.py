import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.document import Document
from app.models.extraction import ExtractedField
from app.models.visual import VisualAsset
from app.models.evidence import DocumentRelationship

logger = logging.getLogger(__name__)

class RelationshipDiscoveryService:
    """
    Deterministic cross-document relationship discovery.
    Identifies factual links between heterogeneous mining records without LLM hallucination:
    - SAME_MINE_OR_BLOCK
    - SAME_PERIOD
    - SAME_METRIC
    - DOCUMENT_FAMILY
    - CROSS_MODAL_EVIDENCE
    """

    def discover_relationships(
        self,
        db: Session,
        document_id: str,
        organization_id: str
    ) -> List[DocumentRelationship]:
        """
        Discovers and persists factual relationships between the newly ingested document
        and existing documents in the same organization.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return []

        # Find other documents in the same organization
        other_docs = db.query(Document).filter(
            Document.organization_id == organization_id,
            Document.id != document_id,
            Document.status == "COMPLETED"
        ).all()

        if not other_docs:
            return []

        # Fetch extracted fields for the current document
        doc_fields = db.query(ExtractedField).filter(
            ExtractedField.document_id == document_id,
            ExtractedField.validation_status != "ERROR"
        ).all()

        # Check visual assets for current document
        doc_visuals = db.query(VisualAsset).filter(
            VisualAsset.document_id == document_id
        ).all()

        created_relationships: List[DocumentRelationship] = []

        for other in other_docs:
            # Check if relationship already exists
            existing_rel = db.query(DocumentRelationship).filter(
                or_(
                    and_(DocumentRelationship.source_document_id == document_id, DocumentRelationship.target_document_id == other.id),
                    and_(DocumentRelationship.source_document_id == other.id, DocumentRelationship.target_document_id == document_id)
                )
            ).first()

            other_fields = db.query(ExtractedField).filter(
                ExtractedField.document_id == other.id,
                ExtractedField.validation_status != "ERROR"
            ).all()

            other_visuals = db.query(VisualAsset).filter(
                VisualAsset.document_id == other.id
            ).all()

            # Rule 1: Mine or Block Entity Match
            doc_mines = {f.normalized_value.lower() for f in doc_fields if f.field_name in ["mine_name", "project_name", "block_name"] and f.normalized_value}
            other_mines = {f.normalized_value.lower() for f in other_fields if f.field_name in ["mine_name", "project_name", "block_name"] and f.normalized_value}
            common_mines = doc_mines.intersection(other_mines)
            if common_mines:
                matched_mine = list(common_mines)[0]
                rel = DocumentRelationship(
                    source_document_id=document_id,
                    target_document_id=other.id,
                    relationship_type="SAME_MINE_OR_BLOCK",
                    confidence=1.0,
                    matching_criteria={"entity": "mine_or_block", "matched_value": matched_mine},
                    description=f"Both documents report data for mine/block: '{matched_mine.title()}'"
                )
                db.add(rel)
                created_relationships.append(rel)

            # Rule 2: Operational Period / Fiscal Year Match
            doc_periods = {f.normalized_value.lower() for f in doc_fields if f.field_name in ["fiscal_year", "reporting_period"] and f.normalized_value}
            other_periods = {f.normalized_value.lower() for f in other_fields if f.field_name in ["fiscal_year", "reporting_period"] and f.normalized_value}
            common_periods = doc_periods.intersection(other_periods)
            if common_periods:
                matched_period = list(common_periods)[0]
                rel = DocumentRelationship(
                    source_document_id=document_id,
                    target_document_id=other.id,
                    relationship_type="SAME_PERIOD",
                    confidence=0.95,
                    matching_criteria={"field": "period", "matched_value": matched_period},
                    description=f"Matching operational period: '{matched_period}'"
                )
                db.add(rel)
                created_relationships.append(rel)

            # Rule 3: Common Metric Tracking (e.g. Coal Production or Reserves)
            doc_metrics = {f.field_name for f in doc_fields if f.data_type == "NUMBER" and f.numeric_value is not None}
            other_metrics = {f.field_name for f in other_fields if f.data_type == "NUMBER" and f.numeric_value is not None}
            common_metrics = doc_metrics.intersection(other_metrics)
            if common_metrics:
                primary_metric = sorted(list(common_metrics))[0]
                rel = DocumentRelationship(
                    source_document_id=document_id,
                    target_document_id=other.id,
                    relationship_type="SAME_METRIC",
                    confidence=0.90,
                    matching_criteria={"common_metrics": list(common_metrics)},
                    description=f"Both documents report metrics for: {', '.join(sorted(list(common_metrics))[:3])}"
                )
                db.add(rel)
                created_relationships.append(rel)

            # Rule 4: Document Family (filename prefix or common naming pattern)
            doc_stem = doc.original_filename.rsplit(".", 1)[0].lower().replace("_", " ").replace("-", " ")
            other_stem = other.original_filename.rsplit(".", 1)[0].lower().replace("_", " ").replace("-", " ")
            doc_prefix = doc_stem.split()[0] if doc_stem.split() else ""
            other_prefix = other_stem.split()[0] if other_stem.split() else ""
            if doc_prefix and len(doc_prefix) >= 4 and doc_prefix == other_prefix:
                rel = DocumentRelationship(
                    source_document_id=document_id,
                    target_document_id=other.id,
                    relationship_type="DOCUMENT_FAMILY",
                    confidence=0.85,
                    matching_criteria={"prefix": doc_prefix},
                    description=f"Document series match: prefix '{doc_prefix.title()}'"
                )
                db.add(rel)
                created_relationships.append(rel)

            # Rule 5: Cross-Modal Corroboration (Visual + Structured/Textual)
            has_visual_1 = len(doc_visuals) > 0 or doc.mime_type.startswith("image/")
            has_visual_2 = len(other_visuals) > 0 or other.mime_type.startswith("image/")
            if (has_visual_1 and not has_visual_2) or (has_visual_2 and not has_visual_1):
                if common_mines or common_periods or (doc_prefix and doc_prefix == other_prefix):
                    rel = DocumentRelationship(
                        source_document_id=document_id,
                        target_document_id=other.id,
                        relationship_type="CROSS_MODAL_EVIDENCE",
                        confidence=0.90,
                        matching_criteria={"visual_document": document_id if has_visual_1 else other.id},
                        description="Cross-modal corroboration: geological/mining diagram links with tabular or narrative reporting"
                    )
                    db.add(rel)
                    created_relationships.append(rel)

        if created_relationships:
            db.commit()

        return created_relationships

relationship_discovery_service = RelationshipDiscoveryService()
