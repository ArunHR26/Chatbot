"""API v1 router with versioned endpoints."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json

from ..database import get_session
from ..models import IngestResponse, ChatRequest
from ..services import IngestionService, ChatService
from ..repository import DocumentRepository
from ..logging_config import get_logger
from ..exceptions import (
    DocumentExtractionError,
    DocumentTooLargeError,
    UnsupportedFileTypeError,
    EmbeddingGenerationError,
    LLMConnectionError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["v1"])

# Initialize services
ingestion_service = IngestionService()
chat_service = ChatService()

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Ingest a PDF document into the knowledge base.
    
    - Extracts text from PDF
    - Splits into chunks
    - Generates embeddings
    - Stores in PostgreSQL with pgvector
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        logger.warning("Unsupported file type uploaded", filename=file.filename)
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(content) > MAX_FILE_SIZE:
            logger.warning(
                "File too large",
                filename=file.filename,
                size=len(content),
                max_size=MAX_FILE_SIZE
            )
            raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
        
        logger.info("Starting document ingestion", filename=file.filename, size=len(content))
        
        document_id, chunks_created = await ingestion_service.ingest_document(
            filename=file.filename,
            file_content=content,
            session=session
        )
        
        logger.info(
            "Document ingested successfully",
            document_id=document_id,
            filename=file.filename,
            chunks=chunks_created
        )
        
        return IngestResponse(
            success=True,
            document_id=document_id,
            filename=file.filename,
            chunks_created=chunks_created,
            message=f"Successfully ingested {file.filename} with {chunks_created} chunks"
        )
        
    except DocumentExtractionError as e:
        logger.error("Document extraction failed", error=str(e), filename=file.filename)
        raise HTTPException(status_code=400, detail=str(e))
    except EmbeddingGenerationError as e:
        logger.error("Embedding generation failed", error=str(e))
        raise HTTPException(status_code=502, detail="Failed to generate embeddings")
    except Exception as e:
        logger.exception("Ingestion failed", filename=file.filename)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/chat")
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Chat with the RAG system.
    
    - Retrieves relevant context from the knowledge base
    - Streams response from the LLM
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        logger.info("Chat request received", message_length=len(request.message))
        
        # Generate embedding for the query
        query_embedding = await chat_service.embedding_service.get_embedding(
            request.message
        )
        
        # Use repository for similarity search
        repo = DocumentRepository(session)
        results = await repo.similarity_search(
            query_embedding=query_embedding,
            top_k=5
        )
        
        # Extract chunks from results
        relevant_chunks = [chunk for chunk, score in results]
        
        # Build context from chunks
        context = chat_service.build_context(relevant_chunks)
        
        # Prepare history for the chat
        history = None
        if request.history:
            history = [{"role": m.role, "content": m.content} for m in request.history]
        
        async def generate():
            """Generate streaming response with SSE format."""
            sources = list(set(chunk.document_name for chunk in relevant_chunks))
            
            # Send sources first
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            
            # Stream LLM response
            async for chunk in chat_service.stream_chat_response(
                message=request.message,
                context=context,
                history=history
            ):
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
            
            # Send done signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except LLMConnectionError as e:
        logger.error("LLM connection failed", error=str(e))
        raise HTTPException(status_code=502, detail="Failed to connect to LLM service")
    except Exception as e:
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/documents")
async def list_documents(session: AsyncSession = Depends(get_session)):
    """List all ingested documents."""
    try:
        repo = DocumentRepository(session)
        documents = await repo.list_documents()
        total = await repo.count_documents()
        
        return {"documents": documents, "total": total}
        
    except Exception as e:
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Delete a document and all its chunks."""
    try:
        repo = DocumentRepository(session)
        deleted_count = await repo.delete_document(document_id)
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        
        await session.commit()
        
        logger.info("Document deleted", document_id=document_id, chunks_deleted=deleted_count)
        
        return {
            "success": True,
            "document_id": document_id,
            "chunks_deleted": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete document", document_id=document_id)
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Get system statistics."""
    try:
        repo = DocumentRepository(session)
        
        return {
            "documents": await repo.count_documents(),
            "chunks": await repo.count_chunks(),
        }
        
    except Exception as e:
        logger.exception("Failed to get stats")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
