"""Repository pattern for data access layer."""

from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete
from sqlalchemy.orm import selectinload

from .models import DocumentChunk
from .logging_config import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    """Repository for document chunk operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
        """Create a new document chunk."""
        self.session.add(chunk)
        await self.session.flush()
        logger.info(
            "Created document chunk",
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index
        )
        return chunk
    
    async def create_chunks_batch(self, chunks: list[DocumentChunk]) -> int:
        """Create multiple document chunks in a batch."""
        self.session.add_all(chunks)
        await self.session.flush()
        logger.info(
            "Created document chunks batch",
            count=len(chunks),
            document_id=chunks[0].document_id if chunks else None
        )
        return len(chunks)
    
    async def get_chunk_by_id(self, chunk_id: str) -> DocumentChunk | None:
        """Get a document chunk by ID."""
        result = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )
        return result.scalar_one_or_none()
    
    async def get_chunks_by_document_id(
        self, 
        document_id: str
    ) -> Sequence[DocumentChunk]:
        """Get all chunks for a document."""
        result = await self.session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return result.scalars().all()
    
    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        result = await self.session.execute(
            delete(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        deleted_count = result.rowcount
        logger.info(
            "Deleted document chunks",
            document_id=document_id,
            deleted_count=deleted_count
        )
        return deleted_count
    
    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float | None = None
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Find most similar document chunks using pgvector.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            score_threshold: Optional minimum similarity score
            
        Returns:
            List of (chunk, distance) tuples ordered by similarity
        """
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        # Use parameterized query with pgvector distance operator
        query = text("""
            SELECT 
                id, document_id, document_name, content, 
                chunk_index, created_at,
                embedding <-> :embedding::vector AS distance
            FROM document_chunks
            ORDER BY distance
            LIMIT :limit
        """)
        
        result = await self.session.execute(
            query, 
            {"embedding": embedding_str, "limit": top_k}
        )
        
        rows = result.fetchall()
        
        chunks_with_scores = []
        for row in rows:
            # Skip if below threshold
            if score_threshold and row.distance > score_threshold:
                continue
                
            chunk = DocumentChunk(
                id=row.id,
                document_id=row.document_id,
                document_name=row.document_name,
                content=row.content,
                chunk_index=row.chunk_index,
                created_at=row.created_at,
                embedding=[]  # Don't return embeddings
            )
            chunks_with_scores.append((chunk, row.distance))
        
        logger.debug(
            "Similarity search completed",
            results_count=len(chunks_with_scores),
            top_k=top_k
        )
        
        return chunks_with_scores
    
    async def list_documents(self) -> list[dict]:
        """List all unique documents with metadata."""
        result = await self.session.execute(
            text("""
                SELECT DISTINCT 
                    document_id, 
                    document_name, 
                    MIN(created_at) as created_at,
                    COUNT(*) as chunk_count
                FROM document_chunks
                GROUP BY document_id, document_name
                ORDER BY MIN(created_at) DESC
            """)
        )
        
        documents = []
        for row in result.fetchall():
            documents.append({
                "id": row.document_id,
                "name": row.document_name,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "chunks": row.chunk_count
            })
        
        return documents
    
    async def count_documents(self) -> int:
        """Count total unique documents."""
        result = await self.session.execute(
            text("SELECT COUNT(DISTINCT document_id) FROM document_chunks")
        )
        return result.scalar() or 0
    
    async def count_chunks(self) -> int:
        """Count total chunks."""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )
        return result.scalar() or 0
