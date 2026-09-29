from app.models.base import Base, UUIDMixin
from app.models.organization import Organization, OrganizationRelationship
from app.models.user import User, Role, UserRole
from app.models.document import Document, DocumentVersion, ProcessingJob, DocumentPage, Table, TableRow
from app.models.chunk import Chunk, Embedding
from app.models.audit import AuditEvent
from app.models.visual import VisualAsset
from app.models.extraction import (
    ExtractionRun,
    ExtractedField,
    ValidationResult,
    ReconciliationGroup,
    ReconciliationCandidate,
)
from app.models.verification import VerificationTask, StatutoryReserveVerification
from app.models.qa import QueryRecord, AnswerRecord, AnswerCitation
from app.models.report import (
    ReportFormat,
    Report,
    ReportFieldMapping,
    ReportTable,
    ReportAnnexure,
    ReportPlate,
    ReportCertification,
    ReportComplianceIssue,
    ReportVersion,
)
from app.models.topic import (
    TopicAnalysis,
    Topic,
    TopicTerm,
    TopicDocument,
    TopicEvidence,
)
from app.models.evidence import DocumentRelationship
from app.models.geology import BoreholeStratum

__all__ = [
    "Base",
    "UUIDMixin",
    "BoreholeStratum",
    "Organization",
    "OrganizationRelationship",
    "User",
    "Role",
    "UserRole",
    "Document",
    "DocumentVersion",
    "ProcessingJob",
    "DocumentPage",
    "Table",
    "TableRow",
    "VerificationTask",
    "StatutoryReserveVerification",
    "Chunk",
    "Embedding",
    "AuditEvent",
    "ExtractionRun",
    "ExtractedField",
    "ValidationResult",
    "ReconciliationGroup",
    "ReconciliationCandidate",
    "QueryRecord",
    "AnswerRecord",
    "AnswerCitation",
    "ReportFormat",
    "Report",
    "ReportFieldMapping",
    "ReportTable",
    "ReportAnnexure",
    "ReportPlate",
    "ReportCertification",
    "ReportComplianceIssue",
    "ReportVersion",
    "TopicAnalysis",
    "Topic",
    "TopicTerm",
    "TopicDocument",
    "TopicEvidence",
    "VisualAsset",
    "DocumentRelationship",
]

