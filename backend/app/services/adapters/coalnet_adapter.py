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
)
from app.services.adapters.security import (
    validate_endpoint_url,
    sanitize_url_for_logging,
)

logger = logging.getLogger(__name__)


class CoalNetAdapter(ExternalSystemAdapter):
    """
    CoalNet Logistics & Dispatch Adapter.
    Tracks pithead weighbridges, rail rake loading sidings, and road dispatches.
    Guarantees strict credential protection and explicit unconfigured/unavailable states.
    """
    system_name: str = "coalnet"
    system_type: str = "dispatch"
    is_mock: bool = False

    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        cfg = config_override or {}
        self.enabled = cfg.get("COALNET_ENABLED", getattr(settings, "COALNET_ENABLED", False))
        self.endpoint = cfg.get("COALNET_ENDPOINT", getattr(settings, "COALNET_ENDPOINT", None))
        self.api_key = cfg.get("COALNET_API_KEY", getattr(settings, "COALNET_API_KEY", None))
        self.timeout_seconds = float(cfg.get("COALNET_TIMEOUT_SECONDS", getattr(settings, "COALNET_TIMEOUT_SECONDS", 5.0)))
        self.verify_tls = bool(cfg.get("COALNET_VERIFY_TLS", getattr(settings, "COALNET_VERIFY_TLS", True)))

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.endpoint and self.api_key)

    def health(self) -> Dict[str, Any]:
        """
        Reports CoalNet reachability without disclosing the API key.
        """
        if not self.enabled:
            return {
                "system_name": self.system_name,
                "system_type": self.system_type,
                "status": AdapterStatus.NOT_CONFIGURED.value,
                "message": "CoalNet adapter is disabled in environment configuration.",
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
                "message": "CoalNet endpoint or API authentication key is missing.",
                "is_mock": self.is_mock,
                "configured": False,
                "endpoint": sanitize_url_for_logging(self.endpoint),
                "tls_verified": self.verify_tls
            }

        try:
            valid_url = validate_endpoint_url(self.endpoint, enforce_https=self.verify_tls)
            return {
                "system_name": self.system_name,
                "system_type": self.system_type,
                "status": AdapterStatus.UNAVAILABLE.value,
                "message": "CoalNet endpoint configured, but live service is unreachable or offline.",
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
                "message": f"CoalNet configuration security validation error: {str(e)}",
                "is_mock": self.is_mock,
                "configured": False,
                "endpoint": sanitize_url_for_logging(self.endpoint),
                "tls_verified": self.verify_tls
            }

    def connect(self) -> bool:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "CoalNet system is not configured. Provide COALNET_ENDPOINT and credentials via environment.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            f"Cannot connect to CoalNet at '{sanitize_url_for_logging(self.endpoint)}': Live enterprise connection not established.",
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
                "Cannot fetch documents: CoalNet adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live CoalNet system connection is unavailable.",
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
                "Cannot fetch records: CoalNet adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live CoalNet system connection is unavailable.",
            system_name=self.system_name
        )

    def get_metadata(self, external_id: str) -> Optional[ExternalMetadata]:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "Cannot retrieve metadata: CoalNet adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live CoalNet system connection is unavailable.",
            system_name=self.system_name
        )

    def fetch_incremental(
        self,
        since: datetime,
        limit: int = 50
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise ExternalSystemNotConfiguredError(
                "Cannot fetch incremental sync: CoalNet adapter is not configured.",
                system_name=self.system_name
            )
        raise ExternalSystemUnavailableError(
            "Live CoalNet system connection is unavailable.",
            system_name=self.system_name
        )


class MockCoalNetAdapter(CoalNetAdapter):
    """
    Deterministic Local Mock CoalNet Adapter.
    Generates synthetic weighbridge and rail rake dispatch records.
    Clearly identifies itself as a mock.
    """
    is_mock: bool = True

    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        super().__init__(config_override)
        self.enabled = True
        self.endpoint = "https://mock-coalnet.internal.local/api/v2"
        self.api_key = "mock_coalnet_key_demo"

    @property
    def is_configured(self) -> bool:
        return True

    def health(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "system_type": self.system_type,
            "status": AdapterStatus.MOCK_OPERATIONAL.value,
            "message": "Deterministic local mock CoalNet operational (simulated dispatch network).",
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
        mock_dispatches = [
            {
                "id": "CN-RAKE-2026-0418",
                "title": "CoalNet Rail Rake Despatch - Kusmunda Siding to NTPC Korba",
                "type": "rake_dispatch",
                "org_id": "SECL",
                "mine_id": "KUSMUNDA_OC",
                "block_id": "BLOCK_SOUTH",
                "data": {
                    "siding_code": "SDG-KUS-01",
                    "destination_consumer": "NTPC_KORBA_STPS",
                    "coal_grade": "G11",
                    "wagon_type": "BOXN",
                    "wagon_count": 58,
                    "gross_weight_mt": 5120.4,
                    "tare_weight_mt": 1284.2,
                    "net_weight_mt": 3836.2,
                    "dispatch_timestamp": (now - timedelta(hours=6)).isoformat(),
                    "challan_number": "CH-2026-99412"
                }
            },
            {
                "id": "CN-ROAD-2026-1189",
                "title": "CoalNet Road Weighbridge Despatch - Piparwar Pithead",
                "type": "road_dispatch",
                "org_id": "CCL",
                "mine_id": "PIPARWAR_OCP",
                "block_id": "BLOCK_WEST",
                "data": {
                    "weighbridge_id": "WB-CCL-PIP-03",
                    "truck_registration": "JH-01-AZ-9912",
                    "destination_consumer": "Tenughat TPS",
                    "coal_grade": "G12",
                    "net_weight_mt": 34.85,
                    "dispatch_timestamp": (now - timedelta(hours=2)).isoformat(),
                    "gate_pass_no": "GP-441208"
                }
            }
        ]

        records = []
        for item in mock_dispatches[:limit]:
            meta = ExternalMetadata(
                source_system=self.system_name,
                external_id=item["id"],
                created_at=now - timedelta(hours=8),
                updated_at=now - timedelta(hours=2),
                fetched_at=now,
                organization_id=item["org_id"],
                mine_id=item["mine_id"],
                block_id=item["block_id"],
                source_uri=f"{self.endpoint}/dispatches/{item['id']}",
                raw_properties={"weighbridge_calibration_date": "2026-01-15", "tamper_seal_ok": True},
                provenance={"adapter": "MockCoalNetAdapter", "environment": "simulated"}
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
        doc_id = "COALNET_RAKE_CHALLAN_99412.pdf"
        meta = ExternalMetadata(
            source_system=self.system_name,
            external_id=doc_id,
            created_at=now - timedelta(hours=6),
            updated_at=now - timedelta(hours=6),
            fetched_at=now,
            organization_id="SECL",
            mine_id="KUSMUNDA_OC",
            source_uri=f"{self.endpoint}/challans/{doc_id}",
            provenance={"adapter": "MockCoalNetAdapter", "format": "PDF"}
        )
        sample_bytes = b"%PDF-1.4 Mock CoalNet Rake Weighment Summary Challan Slips"
        return [ExternalDocument(
            source_system=self.system_name,
            external_id=doc_id,
            document_type="weighment_challan",
            title="CoalNet Electronic Rake Weighment Challan",
            file_name=doc_id,
            mime_type="application/pdf",
            content_bytes=sample_bytes,
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
            source_uri=f"{self.endpoint}/items/{external_id}",
            provenance={"adapter": "MockCoalNetAdapter"}
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
