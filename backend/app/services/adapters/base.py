import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from app.services.adapters.security import sanitize_credentials


class AdapterStatus(str, Enum):
    """
    Standardized operational states for external enterprise system adapters.
    Guarantees that unconfigured systems are never falsely reported as connected.
    """
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNAVAILABLE = "UNAVAILABLE"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    MOCK_OPERATIONAL = "MOCK_OPERATIONAL"
    ERROR = "ERROR"


@dataclass
class ExternalMetadata:
    """
    Canonical normalized metadata structure across all external enterprise systems.
    Preserves origin tracking, organizational context, and audit provenance.
    """
    source_system: str
    external_id: str
    schema_version: str = "1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    organization_id: Optional[str] = None
    mine_id: Optional[str] = None
    block_id: Optional[str] = None
    source_uri: Optional[str] = None
    raw_properties: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system,
            "external_id": self.external_id,
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "organization_id": self.organization_id,
            "mine_id": self.mine_id,
            "block_id": self.block_id,
            "source_uri": self.source_uri,
            "raw_properties": sanitize_credentials(self.raw_properties),
            "provenance": self.provenance
        }


@dataclass
class ExternalRecord:
    """
    Canonical normalized representation of structured external business records
    (e.g., SAP production line item, CoalNet weighbridge dispatch entry).
    """
    source_system: str
    external_id: str
    record_type: str
    title: str
    data: Dict[str, Any]
    metadata: ExternalMetadata
    timestamps: Dict[str, Optional[str]] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamps and self.metadata:
            self.timestamps = {
                "created_at": self.metadata.created_at.isoformat() if self.metadata.created_at else None,
                "updated_at": self.metadata.updated_at.isoformat() if self.metadata.updated_at else None,
                "fetched_at": self.metadata.fetched_at.isoformat() if self.metadata.fetched_at else None,
            }
        if not self.provenance and self.metadata:
            self.provenance = self.metadata.provenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system,
            "external_id": self.external_id,
            "record_type": self.record_type,
            "title": self.title,
            "data": sanitize_credentials(self.data),
            "metadata": self.metadata.to_dict() if self.metadata else {},
            "timestamps": self.timestamps,
            "provenance": self.provenance
        }


@dataclass
class ExternalDocument:
    """
    Canonical normalized representation of external enterprise documents
    (e.g., DMS PDF geological reports, SAP plant maintenance attachments, CoalNet slips).
    """
    source_system: str
    external_id: str
    document_type: str
    title: str
    file_name: str
    mime_type: str
    content_bytes: Optional[bytes] = None
    content_url: Optional[str] = None
    content_text: Optional[str] = None
    checksum_sha256: Optional[str] = None
    metadata: Optional[ExternalMetadata] = None
    timestamps: Dict[str, Optional[str]] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.content_bytes and not self.checksum_sha256:
            self.checksum_sha256 = hashlib.sha256(self.content_bytes).hexdigest()
        if not self.timestamps and self.metadata:
            self.timestamps = {
                "created_at": self.metadata.created_at.isoformat() if self.metadata.created_at else None,
                "updated_at": self.metadata.updated_at.isoformat() if self.metadata.updated_at else None,
                "fetched_at": self.metadata.fetched_at.isoformat() if self.metadata.fetched_at else None,
            }
        if not self.provenance and self.metadata:
            self.provenance = self.metadata.provenance

    def to_dict(self, include_bytes: bool = False) -> Dict[str, Any]:
        res = {
            "source_system": self.source_system,
            "external_id": self.external_id,
            "document_type": self.document_type,
            "title": self.title,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "content_url": self.content_url,
            "content_text": self.content_text,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": len(self.content_bytes) if self.content_bytes else 0,
            "metadata": self.metadata.to_dict() if self.metadata else {},
            "timestamps": self.timestamps,
            "provenance": self.provenance
        }
        if include_bytes and self.content_bytes:
            res["content_bytes_length"] = len(self.content_bytes)
        return res


class ExternalSystemAdapter(ABC):
    """
    Abstract Enterprise System Adapter Contract.
    Defines common operations across enterprise systems (SAP ERP, CoalNet Logistics, Enterprise DMS)
    while preserving system-specific capabilities and strict fail-closed isolation.
    """
    system_name: str = "base"
    system_type: str = "generic"
    is_mock: bool = False

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if minimum environment configuration is present."""
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """
        Returns structured health and reachability telemetry.
        Never discloses passwords, tokens, or private keys.
        """
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        Validates authentication and connectivity.
        Raises ExternalSystemNotConfiguredError or ExternalSystemUnavailableError on failure.
        """
        pass

    @abstractmethod
    def fetch_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ExternalDocument]:
        """
        Retrieves documents from the external system in Koyla's canonical document format.
        """
        pass

    @abstractmethod
    def fetch_records(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ExternalRecord]:
        """
        Retrieves structured records from the external system in Koyla's canonical record format.
        """
        pass

    @abstractmethod
    def get_metadata(self, external_id: str) -> Optional[ExternalMetadata]:
        """
        Fetches canonical metadata for a specific external entity.
        """
        pass

    @abstractmethod
    def fetch_incremental(
        self,
        since: datetime,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Fetches modified documents and records since a given timestamp for incremental sync.
        Returns {'documents': [...], 'records': [...], 'cursor': ...}
        """
        pass
