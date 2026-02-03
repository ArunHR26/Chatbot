"""Database models for Cloud-Native-RAG using SQLModel and pgvector."""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text
import uuid


class DocumentChunk(SQLModel, table=True):
    """Model for storing document chunks with vector embeddings."""
    
    __tablename__ = "document_chunks"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True
    )
    document_id: str = Field(index=True)
    document_name: str = Field(max_length=500)
    content: str = Field(sa_column=Column(Text))
    chunk_index: int = Field(default=0)
    embedding: list[float] = Field(
        sa_column=Column(Vector(1536))
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True


class ChatMessage(SQLModel):
    """Model for chat messages (not persisted)."""
    
    role: str  # 'user' or 'assistant'
    content: str


class IngestResponse(SQLModel):
    """Response model for document ingestion."""
    
    success: bool
    document_id: str
    filename: str
    chunks_created: int
    message: str


class ChatRequest(SQLModel):
    """Request model for chat endpoint."""
    
    message: str
    history: Optional[list[ChatMessage]] = None


class ChatResponse(SQLModel):
    """Response model for chat (non-streaming)."""
    
    response: str
    sources: list[str]
