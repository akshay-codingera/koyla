from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Text, Float, JSON
from sqlalchemy.orm import relationship

from app.models.base import UUIDMixin
from app.db.database import Base


class QueryRecord(UUIDMixin, Base):
    __tablename__ = "queries"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    query_text = Column(Text, nullable=False)
    normalized_query = Column(JSON, nullable=True)
    filters_applied = Column(JSON, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    answers = relationship("AnswerRecord", back_populates="query", cascade="all, delete-orphan")


class AnswerRecord(UUIDMixin, Base):
    __tablename__ = "answers"

    query_id = Column(String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    verification_status = Column(String(50), default="SUPPORTED", nullable=False)  # 'SUPPORTED', 'PARTIALLY_SUPPORTED', 'REFUSED'
    latency_ms = Column(Float, default=0.0, nullable=False)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    arithmetic_used = Column(Boolean, default=False, nullable=False)
    conflict_detected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    query = relationship("QueryRecord", back_populates="answers")
    citations = relationship("AnswerCitation", back_populates="answer", cascade="all, delete-orphan")


class AnswerCitation(UUIDMixin, Base):
    __tablename__ = "answer_citations"

    answer_id = Column(String(36), ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=True)
    excerpt = Column(Text, nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    table_provenance = Column(JSON, nullable=True)

    # Relationships
    answer = relationship("AnswerRecord", back_populates="citations")
