"""Services for PDF processing, embeddings, and RAG chat with resilience patterns."""

import io
import json
import uuid
from typing import AsyncIterator
import httpx
from PyPDF2 import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .models import DocumentChunk
from .config import get_settings
from .logging_config import get_logger
from .exceptions import (
    DocumentExtractionError,
    EmbeddingGenerationError,
    LLMConnectionError,
    LLMRateLimitError,
)

settings = get_settings()
logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings via OpenRouter with retry logic."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text with retry."""
        try:
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.embedding_model,
                    "input": text
                }
            )
            
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 30))
                logger.warning("Rate limited on embeddings", retry_after=retry_after)
                raise LLMRateLimitError(retry_after=retry_after)
            
            response.raise_for_status()
            data = response.json()
            
            logger.debug("Generated embedding", text_length=len(text))
            return data["data"][0]["embedding"]
            
        except httpx.HTTPError as e:
            logger.error("Embedding API error", error=str(e))
            raise EmbeddingGenerationError(reason=str(e))
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts with retry."""
        try:
            logger.info("Generating batch embeddings", count=len(texts))
            
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.embedding_model,
                    "input": texts
                }
            )
            
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 30))
                raise LLMRateLimitError(retry_after=retry_after)
            
            response.raise_for_status()
            data = response.json()
            
            embeddings = [item["embedding"] for item in data["data"]]
            logger.info("Batch embeddings generated", count=len(embeddings))
            return embeddings
            
        except httpx.HTTPError as e:
            logger.error("Batch embedding API error", error=str(e))
            raise EmbeddingGenerationError(reason=str(e))
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class PDFService:
    """Service for PDF text extraction."""
    
    @staticmethod
    def extract_text(file_content: bytes, filename: str = "unknown.pdf") -> str:
        """Extract text from PDF bytes."""
        try:
            pdf_file = io.BytesIO(file_content)
            reader = PdfReader(pdf_file)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                    
            extracted = "\n\n".join(text_parts)
            logger.info(
                "Extracted text from PDF",
                filename=filename,
                pages=len(reader.pages),
                characters=len(extracted)
            )
            
            return extracted
            
        except Exception as e:
            logger.error("PDF extraction failed", filename=filename, error=str(e))
            raise DocumentExtractionError(filename=filename, reason=str(e))


class ChunkingService:
    """Service for splitting text into chunks."""
    
    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        chunk_overlap: int = settings.chunk_overlap
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # If not at the end, try to break at a sentence boundary
            if end < text_length:
                # Look for sentence endings within the chunk
                for sep in ['. ', '.\n', '? ', '!\n', '\n\n']:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep != -1 and last_sep > self.chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
        
        logger.debug(
            "Split text into chunks",
            total_length=text_length,
            chunks=len(chunks),
            avg_chunk_size=text_length // len(chunks) if chunks else 0
        )
        
        return chunks


class IngestionService:
    """Service for document ingestion pipeline."""
    
    def __init__(self):
        self.pdf_service = PDFService()
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
    
    async def ingest_document(
        self,
        filename: str,
        file_content: bytes,
        session: AsyncSession
    ) -> tuple[str, int]:
        """Ingest a document: extract, chunk, embed, and store."""
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        logger.info(
            "Starting document ingestion",
            document_id=document_id,
            filename=filename,
            size_bytes=len(file_content)
        )
        
        # Extract text from PDF
        text = self.pdf_service.extract_text(file_content, filename)
        
        if not text:
            raise ValueError("Could not extract text from PDF")
        
        # Split into chunks
        chunks = self.chunking_service.split_text(text)
        
        if not chunks:
            raise ValueError("No chunks generated from document")
        
        # Generate embeddings in batch
        embeddings = await self.embedding_service.get_embeddings_batch(chunks)
        
        # Create and store document chunks
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            doc_chunk = DocumentChunk(
                document_id=document_id,
                document_name=filename,
                content=chunk_text,
                chunk_index=idx,
                embedding=embedding
            )
            session.add(doc_chunk)
        
        await session.commit()
        
        logger.info(
            "Document ingestion completed",
            document_id=document_id,
            filename=filename,
            chunks_created=len(chunks)
        )
        
        return document_id, len(chunks)


class ChatService:
    """Service for RAG-powered chat with resilience."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def similarity_search(
        self,
        query_embedding: list[float],
        session: AsyncSession,
        top_k: int = 5
    ) -> list[DocumentChunk]:
        """Find most similar document chunks."""
        # Use pgvector's L2 distance for similarity search
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        query = text(f"""
            SELECT id, document_id, document_name, content, chunk_index, created_at,
                   embedding <-> '{embedding_str}'::vector AS distance
            FROM document_chunks
            ORDER BY distance
            LIMIT :limit
        """)
        
        result = await session.execute(query, {"limit": top_k})
        rows = result.fetchall()
        
        chunks = []
        for row in rows:
            chunk = DocumentChunk(
                id=row.id,
                document_id=row.document_id,
                document_name=row.document_name,
                content=row.content,
                chunk_index=row.chunk_index,
                created_at=row.created_at,
                embedding=[]  # Don't return embeddings
            )
            chunks.append(chunk)
        
        logger.debug("Similarity search completed", results=len(chunks))
        
        return chunks
    
    def build_context(self, chunks: list[DocumentChunk]) -> str:
        """Build context string from retrieved chunks."""
        if not chunks:
            return "No relevant documents found in the knowledge base."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}: {chunk.document_name}]\n{chunk.content}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, "WARNING"),
    )
    async def stream_chat_response(
        self,
        message: str,
        context: str,
        history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream chat response from OpenRouter with retry."""
        
        system_prompt = """You are a helpful AI assistant with access to a knowledge base. 
Answer questions based on the provided context. If the context doesn't contain 
relevant information, say so and provide a general answer if possible.
Always cite the source documents when using information from the context.

Context from knowledge base:
{context}"""
        
        messages = [
            {"role": "system", "content": system_prompt.format(context=context)}
        ]
        
        # Add conversation history if provided
        if history:
            for msg in history[-10:]:  # Keep last 10 messages
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": message})
        
        logger.info("Starting chat stream", message_length=len(message))
        
        try:
            async with self.client.stream(
                "POST",
                f"{settings.openrouter_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": messages,
                    "stream": True
                }
            ) as response:
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 30))
                    raise LLMRateLimitError(retry_after=retry_after)
                
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices") and chunk["choices"][0].get("delta"):
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
                
                logger.info("Chat stream completed")
                
        except httpx.ConnectError as e:
            logger.error("LLM connection failed", error=str(e))
            raise LLMConnectionError(service="OpenRouter", reason=str(e))
    
    async def close(self):
        """Close HTTP clients."""
        await self.client.aclose()
        await self.embedding_service.close()
