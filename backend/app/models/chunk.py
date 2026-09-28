from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON, Index, UniqueConstraint, Computed
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.models.base import UUIDMixin
from app.db.database import Base

class Chunk(UUIDMixin, Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("idx_chunks_tsv", "tsv_content", postgresql_using="gin"),
    )
    
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_type = Column(String(20), default="TEXT")  # TEXT or TABLE
    content = Column(Text, nullable=False)
    section_heading = Column(Text, nullable=True)
    tsv_content = Column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(section_heading, '') || ' ' || content)"),
        nullable=True
    )
    metadata_json = Column(JSON, nullable=True)

    # Relationships
    document = relationship("Document", backref="chunks")
    embeddings = relationship("Embedding", back_populates="chunk", cascade="all, delete-orphan")


class Embedding(UUIDMixin, Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "model_name", name="uq_chunk_embedding_model"),
        Index("idx_embeddings_chunk_id", "chunk_id"),
    )
    
    chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(100), nullable=False, default="all-MiniLM-L6-v2")
    dimensions = Column(Integer, nullable=False, default=384)
    embedding_version = Column(String(50), nullable=False, default="1.0.0")
    vector_data = Column(Vector(384), nullable=True)

    # Relationship
    chunk = relationship("Chunk", back_populates="embeddings")

    @property
    def embedding_model(self) -> str:
        return self.model_name

    @property
    def embedding_dimension(self) -> int:
        return self.dimensions

    @property
    def embedding(self):
        return self.vector_data

