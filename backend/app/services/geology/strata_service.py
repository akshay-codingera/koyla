import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.geology import BoreholeStratum
from app.models.document import Document, DocumentPage, Table, TableRow
from app.services.geology.extractor import (
    extract_strata_from_text_lines,
    extract_strata_from_table,
    extract_borehole_id_from_text,
)
from app.services.geology.validator import validate_stratum_metrics

logger = logging.getLogger(__name__)


class LithologicalStrataService:
    """
    Core domain service managing extraction, persistence, validation,
    and organization-scoped retrieval of normalized borehole lithological strata.
    """

    def extract_and_persist_strata(
        self, db: Session, document_id: str, organization_id: str
    ) -> List[BoreholeStratum]:
        """
        Extracts lithological strata from document pages and tables,
        normalizes lithology, validates intervals, and persists records.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning(f"Document {document_id} not found for strata extraction.")
            return []

        org_id = organization_id or doc.organization_id

        # 1. Detect document-level borehole mention if present
        doc_bh_id = extract_borehole_id_from_text(doc.title) or extract_borehole_id_from_text(doc.original_filename)

        all_candidates: List[Dict[str, Any]] = []

        # 2. Extract from tables first (highest structure fidelity)
        tables = db.query(Table).filter(Table.document_id == document_id).all()
        for t in tables:
            rows = db.query(TableRow).filter(TableRow.table_id == t.id).order_by(TableRow.row_index).all()
            table_strata = extract_strata_from_table(t, rows, document_id, default_borehole_id=doc_bh_id)
            all_candidates.extend(table_strata)

        # 3. Extract from text / OCR pages
        pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number).all()
        for p in pages:
            if not p.extracted_text:
                continue
            page_bh_id = extract_borehole_id_from_text(p.extracted_text) or doc_bh_id
            page_strata = extract_strata_from_text_lines(
                p.extracted_text,
                default_borehole_id=page_bh_id,
                page_number=p.page_number,
                document_id=document_id,
            )
            all_candidates.extend(page_strata)

        if not all_candidates:
            logger.info(f"No lithological strata detected in document {document_id}.")
            return []

        # 4. De-duplicate candidates by (borehole_id, stratum_order, depth_from_m)
        seen = set()
        persisted: List[BoreholeStratum] = []

        for c in all_candidates:
            key = (c["borehole_id"], c["stratum_order"], round(c["depth_from_m"], 2))
            if key in seen:
                continue
            seen.add(key)

            stratum = BoreholeStratum(
                organization_id=org_id,
                document_id=document_id,
                borehole_id=c["borehole_id"],
                stratum_order=c["stratum_order"],
                depth_from_m=c["depth_from_m"],
                depth_to_m=c["depth_to_m"],
                thickness_m=c["thickness_m"],
                stated_thickness_m=c.get("stated_thickness_m"),
                lithology_type=c["lithology_type"],
                raw_lithology=c.get("raw_lithology"),
                seam_name=c.get("seam_name"),
                page_number=c.get("page_number"),
                table_id=c.get("table_id"),
                row_id=c.get("row_id"),
                source_text=c.get("source_text"),
                extraction_method=c.get("extraction_method", "RULE_BASED"),
                confidence_score=c.get("confidence_score", 1.0),
                has_thickness_discrepancy=c.get("has_thickness_discrepancy", False),
                discrepancy_details=c.get("discrepancy_details"),
                metadata_json=c.get("metadata_json"),
            )
            db.add(stratum)
            persisted.append(stratum)

        db.commit()

        # Refresh persisted records
        for s in persisted:
            db.refresh(s)

        bh_ids = list(set(s.borehole_id for s in persisted))
        logger.info(
            f"Extracted and persisted {len(persisted)} strata for boreholes {bh_ids} in doc {document_id}",
            extra={
                "event": "strata_extracted",
                "document_id": document_id,
                "organization_id": org_id,
                "strata_count": len(persisted),
                "borehole_ids": bh_ids,
            },
        )
        return persisted

    def get_strata_by_borehole(
        self,
        db: Session,
        borehole_id: str,
        organization_id: Optional[str] = None,
        allowed_org_ids: Optional[List[str]] = None,
    ) -> List[BoreholeStratum]:
        """
        Retrieves ordered vertical sequence of lithological strata for a given borehole.
        Strictly enforces server-side organization scoping.
        """
        query = db.query(BoreholeStratum).filter(
            func.lower(BoreholeStratum.borehole_id) == borehole_id.lower().strip()
        )

        if allowed_org_ids is not None:
            query = query.filter(BoreholeStratum.organization_id.in_(allowed_org_ids))
        elif organization_id:
            query = query.filter(BoreholeStratum.organization_id == organization_id)

        return query.order_by(BoreholeStratum.stratum_order.asc(), BoreholeStratum.depth_from_m.asc()).all()

    def get_stratum_by_id(
        self,
        db: Session,
        stratum_id: str,
        allowed_org_ids: Optional[List[str]] = None,
    ) -> Optional[BoreholeStratum]:
        """
        Retrieves a single stratum by ID with organization access control.
        """
        query = db.query(BoreholeStratum).filter(BoreholeStratum.id == stratum_id)
        if allowed_org_ids is not None:
            query = query.filter(BoreholeStratum.organization_id.in_(allowed_org_ids))
        return query.first()

    def get_borehole_summary(
        self,
        db: Session,
        borehole_id: str,
        organization_id: Optional[str] = None,
        allowed_org_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Computes analytical summary metrics for a borehole's strata sequence.
        """
        strata = self.get_strata_by_borehole(
            db, borehole_id, organization_id=organization_id, allowed_org_ids=allowed_org_ids
        )

        if not strata:
            return {
                "borehole_id": borehole_id,
                "strata_count": 0,
                "total_depth_m": 0.0,
                "total_coal_thickness_m": 0.0,
                "coal_strata_count": 0,
                "seams": [],
                "lithology_breakdown": {},
                "discrepancy_count": 0,
                "found": False,
            }

        total_depth = max(s.depth_to_m for s in strata)
        coal_strata = [s for s in strata if s.lithology_type == "Coal"]
        total_coal_thickness = round(sum(s.thickness_m for s in coal_strata), 3)

        seams = sorted(list(set(s.seam_name for s in strata if s.seam_name)))
        
        lithology_breakdown: Dict[str, float] = {}
        for s in strata:
            lithology_breakdown[s.lithology_type] = round(
                lithology_breakdown.get(s.lithology_type, 0.0) + s.thickness_m, 3
            )

        discrepancy_count = sum(1 for s in strata if s.has_thickness_discrepancy)

        return {
            "borehole_id": borehole_id,
            "organization_id": strata[0].organization_id,
            "strata_count": len(strata),
            "total_depth_m": round(total_depth, 3),
            "total_coal_thickness_m": total_coal_thickness,
            "coal_strata_count": len(coal_strata),
            "seams": seams,
            "lithology_breakdown": lithology_breakdown,
            "discrepancy_count": discrepancy_count,
            "found": True,
        }

    def create_stratum(
        self,
        db: Session,
        data: Dict[str, Any],
        organization_id: str,
    ) -> BoreholeStratum:
        """
        Creates and persists a validated BoreholeStratum entity.
        """
        depth_from = data["depth_from_m"]
        depth_to = data["depth_to_m"]
        stated_thick = data.get("stated_thickness_m")

        metrics = validate_stratum_metrics(depth_from, depth_to, stated_thickness_m=stated_thick)

        stratum = BoreholeStratum(
            organization_id=organization_id,
            document_id=data["document_id"],
            borehole_id=data["borehole_id"],
            stratum_order=data.get("stratum_order", 1),
            depth_from_m=metrics["depth_from_m"],
            depth_to_m=metrics["depth_to_m"],
            thickness_m=metrics["thickness_m"],
            stated_thickness_m=metrics["stated_thickness_m"],
            lithology_type=data["lithology_type"],
            raw_lithology=data.get("raw_lithology"),
            seam_name=data.get("seam_name"),
            page_number=data.get("page_number"),
            chunk_id=data.get("chunk_id"),
            table_id=data.get("table_id"),
            row_id=data.get("row_id"),
            source_text=data.get("source_text"),
            extraction_method=data.get("extraction_method", "MANUAL_ENTRY"),
            confidence_score=data.get("confidence_score", 1.0),
            has_thickness_discrepancy=metrics["has_thickness_discrepancy"],
            discrepancy_details=metrics["discrepancy_details"],
            metadata_json=data.get("metadata_json"),
        )
        db.add(stratum)
        db.commit()
        db.refresh(stratum)
        return stratum


strata_service = LithologicalStrataService()
