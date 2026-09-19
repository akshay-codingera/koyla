from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, JSON, DateTime, Index
from sqlalchemy.orm import relationship
from app.models.base import UUIDMixin
from app.db.database import Base

class TopicAnalysis(UUIDMixin, Base):
    __tablename__ = "topic_analyses"
    
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    corpus_filters = Column(JSON, nullable=False, default=dict)
    corpus_hash = Column(String(64), nullable=False, index=True)
    embedding_model = Column(String(100), nullable=False, default="BAAI/bge-small-en-v1.5")
    analysis_method = Column(String(50), nullable=False, default="FOUNDATION")
    parameters = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="QUEUED")  # QUEUED, RUNNING, COMPLETED, FAILED
    progress_pct = Column(Integer, nullable=False, default=0)
    runtime_seconds = Column(Float, nullable=True)
    document_count = Column(Integer, nullable=False, default=0)
    chunk_count = Column(Integer, nullable=False, default=0)
    outlier_count = Column(Integer, nullable=False, default=0)
    quality_metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization")
    creator = relationship("User")
    topics = relationship("Topic", back_populates="analysis", cascade="all, delete-orphan")


class Topic(UUIDMixin, Base):
    __tablename__ = "topics"
    
    analysis_id = Column(String(36), ForeignKey("topic_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_index = Column(Integer, nullable=False)
    label = Column(String(255), nullable=True)
    document_count = Column(Integer, default=0, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    prevalence_pct = Column(Float, default=0.0, nullable=False)
    coherence_score = Column(Float, nullable=True)  # semantic_topic_coherence diagnostic
    metadata_json = Column(JSON, nullable=True)
    
    # Relationships
    analysis = relationship("TopicAnalysis", back_populates="topics")
    terms = relationship("TopicTerm", back_populates="topic", cascade="all, delete-orphan")
    documents = relationship("TopicDocument", back_populates="topic", cascade="all, delete-orphan")
    evidence = relationship("TopicEvidence", back_populates="topic", cascade="all, delete-orphan")

    @property
    def semantic_topic_coherence(self) -> float:
        return self.coherence_score


class TopicTerm(UUIDMixin, Base):
    __tablename__ = "topic_terms"
    __table_args__ = (
        Index("idx_topic_terms_topic_rank", "topic_id", "rank"),
    )
    
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    term = Column(String(100), nullable=False)
    weight = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    frequency = Column(Integer, default=0, nullable=False)
    document_count = Column(Integer, default=0, nullable=False)
    
    topic = relationship("Topic", back_populates="terms")


class TopicDocument(UUIDMixin, Base):
    __tablename__ = "topic_documents"
    __table_args__ = (
        Index("idx_topic_documents_topic_doc", "topic_id", "document_id"),
    )
    
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=True)
    contribution_pct = Column(Float, nullable=True)
    
    topic = relationship("Topic", back_populates="documents")
    document = relationship("Document")


class TopicEvidence(UUIDMixin, Base):
    __tablename__ = "topic_evidence"
    __table_args__ = (
        Index("idx_topic_evidence_topic_chunk", "topic_id", "chunk_id"),
    )
    
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    representative_score = Column(Float, nullable=True)
    
    topic = relationship("Topic", back_populates="evidence")
    chunk = relationship("Chunk")


class TopicTrend(UUIDMixin, Base):
    __tablename__ = "topic_trends"
    __table_args__ = (
        Index("idx_topic_trends_analysis_period", "analysis_id", "period_value"),
        Index("idx_topic_trends_topic_period", "topic_id", "period_value"),
    )
    
    analysis_id = Column(String(36), ForeignKey("topic_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    period_type = Column(String(50), nullable=False, default="FISCAL_YEAR")
    period_value = Column(String(50), nullable=False, index=True)
    document_count = Column(Integer, nullable=False, default=0)
    chunk_count = Column(Integer, nullable=False, default=0)
    corpus_document_count = Column(Integer, nullable=False, default=0)
    corpus_chunk_count = Column(Integer, nullable=False, default=0)
    document_share_pct = Column(Float, nullable=False, default=0.0)
    chunk_share_pct = Column(Float, nullable=False, default=0.0)
    absolute_change = Column(Integer, nullable=True)
    percentage_point_change = Column(Float, nullable=True)
    growth_rate_pct = Column(Float, nullable=True)
    trend_status = Column(String(50), nullable=False, default="INSUFFICIENT_HISTORY")
    metadata_json = Column(JSON, nullable=True)
    
    analysis = relationship("TopicAnalysis", backref="trends")
    topic = relationship("Topic", backref="trends")


class TopicComparison(UUIDMixin, Base):
    __tablename__ = "topic_comparisons"
    __table_args__ = (
        Index("idx_topic_comparisons_analysis_dim", "analysis_id", "dimension_type"),
        Index("idx_topic_comparisons_topic_dim", "topic_id", "dimension_type"),
    )
    
    analysis_id = Column(String(36), ForeignKey("topic_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    dimension_type = Column(String(50), nullable=False)  # ORGANIZATION, SUBSIDIARY, MINE, BLOCK, DOCUMENT_TYPE, PERIOD
    dimension_a = Column(String(100), nullable=False)
    dimension_b = Column(String(100), nullable=False)
    value_a = Column(Float, nullable=False, default=0.0)
    value_b = Column(Float, nullable=False, default=0.0)
    difference = Column(Float, nullable=False, default=0.0)
    difference_pct_points = Column(Float, nullable=False, default=0.0)
    document_count_a = Column(Integer, nullable=False, default=0)
    document_count_b = Column(Integer, nullable=False, default=0)
    chunk_count_a = Column(Integer, nullable=False, default=0)
    chunk_count_b = Column(Integer, nullable=False, default=0)
    metadata_json = Column(JSON, nullable=True)
    
    analysis = relationship("TopicAnalysis", backref="comparisons")
    topic = relationship("Topic", backref="comparisons")
