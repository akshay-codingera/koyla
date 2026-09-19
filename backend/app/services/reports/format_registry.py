"""
Official Report Format Registry
Maintains statutory and regulatory report formats with authoritative Source Records.
"""
import os
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.report import ReportFormat

SCHEMA_FILE_PATH = os.path.join(os.path.dirname(__file__), "mining_plan_2025_schema.json")


class FormatRegistry:
    @staticmethod
    def calculate_schema_hash(schema_dict: Dict[str, Any]) -> str:
        serialized = json.dumps(schema_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def seed_default_statutory_format(cls, db: Session) -> ReportFormat:
        """Seed or update the official 2025 Mining Plan statutory format."""
        if not os.path.exists(SCHEMA_FILE_PATH):
            raise FileNotFoundError(f"Authoritative schema file missing at: {SCHEMA_FILE_PATH}")

        with open(SCHEMA_FILE_PATH, "r", encoding="utf-8") as f:
            schema_data = json.load(f)

        report_type = schema_data.get("format_id", "MINING_PLAN_AND_CLOSURE_PLAN_2025")
        schema_hash = cls.calculate_schema_hash(schema_data)

        existing = db.query(ReportFormat).filter(ReportFormat.report_type == report_type).first()
        if existing:
            # Update schema if hash differs
            if existing.source_document_hash != schema_hash:
                existing.schema_json = schema_data
                existing.source_document_hash = schema_hash
                existing.retrieved_at = datetime.utcnow()
                db.commit()
                db.refresh(existing)
            return existing

        new_format = ReportFormat(
            report_type=report_type,
            issuing_authority=schema_data.get("issuing_authority", "Ministry of Coal / Coal Controller Organisation (CCO)"),
            document_title=schema_data.get("document_title", "Guidelines for preparation of Mining Plan and Mine Closure Plan for Coal and Lignite Blocks, 2025"),
            om_number=schema_data.get("om_number", "F.No. CPAM-34011/28/2019-CPAM [E-343762]"),
            om_date=schema_data.get("om_date", "2025-01-31"),
            guideline_year=schema_data.get("guideline_year", 2025),
            effective_status=schema_data.get("effective_status", "ACTIVE_STATUTORY"),
            official_source_url=schema_data.get("official_source_url"),
            source_document_hash=schema_hash,
            format_tier=schema_data.get("format_tier", "STATUTORY"),
            schema_json=schema_data,
        )
        db.add(new_format)
        db.commit()
        db.refresh(new_format)
        return new_format

    @classmethod
    def list_formats(cls, db: Session) -> List[Dict[str, Any]]:
        cls.seed_default_statutory_format(db)
        formats = db.query(ReportFormat).all()
        result = []
        for fmt in formats:
            result.append({
                "id": fmt.id,
                "report_type": fmt.report_type,
                "issuing_authority": fmt.issuing_authority,
                "document_title": fmt.document_title,
                "om_number": fmt.om_number,
                "om_date": fmt.om_date,
                "guideline_year": fmt.guideline_year,
                "effective_status": fmt.effective_status,
                "official_source_url": fmt.official_source_url,
                "source_document_hash": fmt.source_document_hash,
                "format_tier": fmt.format_tier,
                "is_statutory": fmt.format_tier == "STATUTORY",
                "created_at": fmt.created_at.isoformat() if fmt.created_at else None,
            })
        return result

    @classmethod
    def get_format(cls, db: Session, format_id: str) -> Optional[ReportFormat]:
        fmt = db.query(ReportFormat).filter(ReportFormat.id == format_id).first()
        if not fmt:
            # Check by report_type
            fmt = db.query(ReportFormat).filter(ReportFormat.report_type == format_id).first()
        if not fmt:
            # Ensure default format is seeded
            cls.seed_default_statutory_format(db)
            fmt = db.query(ReportFormat).filter(ReportFormat.report_type == format_id).first()
        return fmt
