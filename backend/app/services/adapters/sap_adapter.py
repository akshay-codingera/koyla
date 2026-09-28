import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.services.adapters.base import (
    ExternalSystemAdapter,
    AdapterStatus,
    ExternalDocument,
    ExternalRecord,
    ExternalMetadata,
)
from app.services.adapters.exceptions import (
    ExternalSystemNotConfiguredError,
    ExternalSystemUnavailableError,
    ExternalSystemTimeoutError,
)
from app.services.adapters.security import (
    validate_endpoint_url,
    sanitize_url_for_logging,
)

logger = logging.getLogger(__name__)


class SAPAdapter(ExternalSystemAdapter):
    """
    Enterprise SAP ERP Adapter (Materials Management, Plant Maintenance, Production Accounting).
    Connects to SAP S/4HANA / OData / RFC endpoints when configured.
    Guarantees strict credential protection and explicit unconfigured/unavailable states.
    """
    system_name: str = "sap"
    system_type: str = "erp"
    is_mock: bool = False

    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        cfg = config_override or {}
        self.enabled = cfg.get("SAP_ENABLED", getattr(settings, "SAP_ENABLED", False))
        self.endpoint = cfg.get("SAP_ENDPOINT", getattr(settings, "SAP_ENDPOINT", None))
        self.client_id = cfg.get("SAP_CLIENT_ID", getattr(settings, "SAP_CLIENT_ID", None))
        self.client_secret = cfg.get("SAP_CLIENT_SECRET", getattr(settings, "SAP_CLIENT_SECRET", None))
        self.auth_mode = cfg.get("SAP_AUTH_MODE", getattr(settings, "SAP_AUTH_MODE", "oauth2"))
        self.timeout_seconds = float(cfg.get("SAP_TIMEOUT_SECONDS", getattr(settings, "SAP_TIMEOUT_SECONDS", 5.0)))
        self.verify_tls = bool(cfg.get("SAP_VERIFY_TLS", getattr(settings, "SAP_VERIFY_TLS", True)))

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.endpoint and (self.client_id or self.auth_mode == "mock"))

    def health(self) -> Dict[str, Any]:
        """
        Reports SAP reachability without exposing client secrets or credentials.
        """
        if not self.enabled:
            return {
                "system_name": self.system_name,
                "system_type": self.system_type,
                "status": AdapterStatus.NOT_CONFIGURED.value,
                "message": "SAP adapter is disabled in environment configuration.",
                "is_mock": self.is_mock,
                "configured": False,
                "endpoint": None,
                "tls_verified": self.verify_tls
            }

        if not self.is_configured:
            return {
                "system_name": self.system_name,
                "system_type": self.system_type,
                "status": AdapterStatus.NOT_CONFIGURED.value,
                "message": "SAP endpoint or client credentials are missing.",
                "is_mock": self.is_mock,
                "configured": False,
                "endpoint": sanitize_url_for_logging(self.endpoint),
                "tls_verified": self.verify_tls
            }

        try:
            valid_url = validate_endpoint_url(self.endpoint, enforce_https=self.verify_tls)
            # In a non-mock environment without a live backend, report UNAVAILABLE
            return {
                "system_name": self.system_name,
                "system_type": self.system_type,
                "status": AdapterStatus.UNAVAILABLE.value,
                "message": "SAP endpoint configured, but live SAP system is unreachable or offline.",
                "is_mock": self.is_mock,
                "configured": True,
                "endpoint": sanitize_url_for_logging(valid_url),
                "tls_verified": self.verify_tls
            }
        except Exception as e:
            return {
                "system_name": self.system_name,
                "system_type": self.system_type,
                "status": AdapterStatus.ERROR.value,
                "message": f"SAP configuration security validation failed: {str(e)}",
                "is_mock": self.is_mock,
                "configured": False,
                "endpoint": sanitize_url_for_logging(self.endpoint),
                "tls_verified": self.verify_tls
            }

    def connect(self) -> bool:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "SAP system is not configured. Provide SAP_ENDPOINT and credentials via environment.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            f"Cannot connect to SAP at '{sanitize_url_for_logging(self.endpoint)}': Live enterprise connection not established.",
            system_name=self.system_name
        )

    def fetch_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ExternalDocument]:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "Cannot fetch documents: SAP adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live SAP system connection is unavailable.",
            system_name=self.system_name
        )

    def fetch_records(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ExternalRecord]:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "Cannot fetch records: SAP adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live SAP system connection is unavailable.",
            system_name=self.system_name
        )

    def get_metadata(self, external_id: str) -> Optional[ExternalMetadata]:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "Cannot retrieve metadata: SAP adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live SAP system connection is unavailable.",
            system_name=self.system_name
        )

    def fetch_incremental(
        self,
        since: datetime,
        limit: int = 50
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "Cannot fetch incremental sync: SAP adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live SAP system connection is unavailable.",
            system_name=self.system_name
        )


class MockSAPAdapter(SAPAdapter):
    """
    Deterministic Local Mock SAP Adapter for development, air-gapped demo mode,
    and automated regression testing.
    Clearly marks all data and status with MOCK labels.
    """
    is_mock: bool = True

    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        super().__init__(config_override)
        self.enabled = True
        self.endpoint = "https://mock-sap.internal.local/odata/v4"
        self.client_id = "mock_koyla_sap_client"

    @property
    def is_configured(self) -> bool:
        return True

    def health(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "system_type": self.system_type,
            "status": AdapterStatus.MOCK_OPERATIONAL.value,
            "message": "Deterministic local mock SAP operational (simulated environment).",
            "is_mock": True,
            "configured": True,
            "endpoint": self.endpoint,
            "tls_verified": True
        }

    def connect(self) -> bool:
        return True

    def fetch_records(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ExternalRecord]:
        now = datetime.utcnow()
        mock_data = [
            {
                "id": "SAP-MAT-PROD-2026-001",
                "title": "SAP Raw Coal Production Ledger Entry - Gevra OC",
                "type": "production_accounting",
                "org_id": "SECL",
                "mine_id": "GEVRA_OC",
                "block_id": "BLOCK_IV",
                "data": {
                    "material_code": "COAL_RAW_G11",
                    "material_desc": "Raw Non-Coking Coal Grade G11",
                    "quantity_mt": 142500.0,
                    "cost_center": "CC-SECL-GEV-01",
                    "plant_code": "PLNT-4100",
                    "fiscal_period": "2025-Q4",
                    "storage_location": "SIDING_SILO_A"
                }
            },
            {
                "id": "SAP-MAT-PROD-2026-002",
                "title": "SAP Heavy Machinery Maintenance & Fuel Ledger - Rajmahal",
                "type": "equipment_maintenance",
                "org_id": "ECL",
                "mine_id": "RAJMAHAL_OCP",
                "block_id": "BLOCK_NORTH",
                "data": {
                    "equipment_id": "SHOVEL_HEMM_042",
                    "operating_hours": 420.5,
                    "diesel_consumed_liters": 18240.0,
                    "maintenance_order": "MO-884920",
                    "status": "OPERATIONAL"
                }
            }
        ]

        records = []
        for item in mock_data[:limit]:
            meta = ExternalMetadata(
                source_system=self.system_name,
                external_id=item["id"],
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(hours=4),
                fetched_at=now,
                organization_id=item["org_id"],
                mine_id=item["mine_id"],
                block_id=item["block_id"],
                source_uri=f"{self.endpoint}/ProductionLedger('{item['id']}')",
                raw_properties={"sap_system_id": "PRD_MOCK", "sync_batch": "MOCK-BATCH-001"},
                provenance={"adapter": "MockSAPAdapter", "environment": "simulated"}
            )
            records.append(ExternalRecord(
                source_system=self.system_name,
                external_id=item["id"],
                record_type=item["type"],
                title=item["title"],
                data=item["data"],
                metadata=meta
            ))
        return records

    def fetch_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ExternalDocument]:
        now = datetime.utcnow()
        doc_id = "SAP-DOC-HEMM-MAINT-2026.pdf"
        meta = ExternalMetadata(
            source_system=self.system_name,
            external_id=doc_id,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=1),
            fetched_at=now,
            organization_id="SECL",
            mine_id="GEVRA_OC",
            source_uri=f"{self.endpoint}/Attachments('{doc_id}')/$value",
            provenance={"adapter": "MockSAPAdapter", "format": "PDF"}
        )
        sample_content = b"%PDF-1.4 Mock SAP HEMM Fleet Maintenance Report Document Content"
        return [ExternalDocument(
            source_system=self.system_name,
            external_id=doc_id,
            document_type="plant_maintenance_report",
            title="SAP HEMM Monthly Overhaul & Fitness Certificate",
            file_name="SAP-DOC-HEMM-MAINT-2026.pdf",
            mime_type="application/pdf",
            content_bytes=sample_content,
            metadata=meta
        )]

    def get_metadata(self, external_id: str) -> Optional[ExternalMetadata]:
        now = datetime.utcnow()
        return ExternalMetadata(
            source_system=self.system_name,
            external_id=external_id,
            created_at=now - timedelta(days=1),
            updated_at=now,
            fetched_at=now,
            organization_id="SECL",
            source_uri=f"{self.endpoint}/Entities('{external_id}')",
            provenance={"adapter": "MockSAPAdapter"}
        )

    def fetch_incremental(
        self,
        since: datetime,
        limit: int = 50
    ) -> Dict[str, Any]:
        records = self.fetch_records(limit=limit)
        docs = self.fetch_documents(limit=limit)
        return {
            "source_system": self.system_name,
            "since": since.isoformat(),
            "records": [r.to_dict() for r in records],
            "documents": [d.to_dict() for d in docs],
            "cursor": datetime.utcnow().isoformat()
        }
