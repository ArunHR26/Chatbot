"""Custom exception classes for the RAG application."""

from typing import Any


class RAGException(Exception):
    """Base exception for RAG application."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DocumentException(RAGException):
    """Exceptions related to document processing."""
    pass


class DocumentNotFoundError(DocumentException):
    """Document was not found."""
    
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document not found: {document_id}",
            details={"document_id": document_id}
        )


class DocumentExtractionError(DocumentException):
    """Failed to extract text from document."""
    
    def __init__(self, filename: str, reason: str):
        super().__init__(
            message=f"Failed to extract text from {filename}: {reason}",
            details={"filename": filename, "reason": reason}
        )


class DocumentTooLargeError(DocumentException):
    """Document exceeds size limit."""
    
    def __init__(self, filename: str, size_bytes: int, max_bytes: int):
        super().__init__(
            message=f"Document {filename} ({size_bytes} bytes) exceeds limit ({max_bytes} bytes)",
            details={
                "filename": filename,
                "size_bytes": size_bytes,
                "max_bytes": max_bytes
            }
        )


class UnsupportedFileTypeError(DocumentException):
    """File type is not supported."""
    
    def __init__(self, filename: str, file_type: str):
        super().__init__(
            message=f"Unsupported file type: {file_type} for file {filename}",
            details={"filename": filename, "file_type": file_type}
        )


class EmbeddingException(RAGException):
    """Exceptions related to embedding generation."""
    pass


class EmbeddingGenerationError(EmbeddingException):
    """Failed to generate embeddings."""
    
    def __init__(self, reason: str, retry_after: int | None = None):
        super().__init__(
            message=f"Failed to generate embeddings: {reason}",
            details={"reason": reason, "retry_after": retry_after}
        )


class LLMException(RAGException):
    """Exceptions related to LLM interactions."""
    pass


class LLMConnectionError(LLMException):
    """Failed to connect to LLM service."""
    
    def __init__(self, service: str, reason: str):
        super().__init__(
            message=f"Failed to connect to {service}: {reason}",
            details={"service": service, "reason": reason}
        )


class LLMRateLimitError(LLMException):
    """LLM rate limit exceeded."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            details={"retry_after": retry_after}
        )


class DatabaseException(RAGException):
    """Exceptions related to database operations."""
    pass


class DatabaseConnectionError(DatabaseException):
    """Failed to connect to database."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Database connection failed: {reason}",
            details={"reason": reason}
        )


class VectorSearchError(DatabaseException):
    """Failed to perform vector similarity search."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Vector search failed: {reason}",
            details={"reason": reason}
        )
