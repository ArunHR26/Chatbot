"""FastAPI main application for Cloud-Native-RAG backend."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
import json

from .config import get_settings
from .database import init_db, get_session
from .models import IngestResponse, ChatRequest
from .services import IngestionService, ChatService
from .logging_config import setup_logging, get_logger, bind_context, clear_context
from .tracing import setup_tracing, instrument_app
from .exceptions import RAGException
from .api import router as api_v1_router

settings = get_settings()

# Setup logging
json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(json_logs=json_logs, log_level=log_level)

logger = get_logger(__name__)

# Setup tracing
tracing_enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"
setup_tracing(
    service_name="rag-backend",
    enabled=tracing_enabled
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    logger.info("Starting application", version="1.0.0")
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="Cloud-Native-RAG API",
    description="Production-ready RAG API with pgvector and OpenRouter",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS to allow all origins
# NOTE: For production, restrict this to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request context middleware
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Add request context to logs."""
    import uuid
    request_id = str(uuid.uuid4())[:8]
    bind_context(request_id=request_id)
    
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
    )
    
    response = await call_next(request)
    
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    
    clear_context()
    return response


# Exception handlers
@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    """Handle custom RAG exceptions."""
    logger.error(
        "RAG exception",
        error=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "type": type(exc).__name__}
    )


# Prometheus metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health", "/ready"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)
instrumentator.instrument(app).expose(app, endpoint="/metrics")

# Instrument for tracing
if tracing_enabled:
    instrument_app(app)

# Include API v1 router
app.include_router(api_v1_router)

# Initialize services for legacy endpoints
ingestion_service = IngestionService()
chat_service = ChatService()


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "healthy", "service": "rag-backend", "version": "1.0.0"}


@app.get("/ready")
async def readiness_check(session: AsyncSession = Depends(get_session)):
    """Readiness check - verifies database connection."""
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Database not ready: {str(e)}")


# Legacy endpoints (for backwards compatibility, redirect to v1)
@app.post("/api/ingest", response_model=IngestResponse, deprecated=True)
async def ingest_document_legacy(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """
    [DEPRECATED] Use /api/v1/ingest instead.
    
    Ingest a PDF document into the knowledge base.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
        
        document_id, chunks_created = await ingestion_service.ingest_document(
            filename=file.filename,
            file_content=content,
            session=session
        )
        
        return IngestResponse(
            success=True,
            document_id=document_id,
            filename=file.filename,
            chunks_created=chunks_created,
            message=f"Successfully ingested {file.filename} with {chunks_created} chunks"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/api/chat", deprecated=True)
async def chat_legacy(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    [DEPRECATED] Use /api/v1/chat instead.
    
    Chat with the RAG system.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        query_embedding = await chat_service.embedding_service.get_embedding(
            request.message
        )
        
        relevant_chunks = await chat_service.similarity_search(
            query_embedding=query_embedding,
            session=session,
            top_k=5
        )
        
        context = chat_service.build_context(relevant_chunks)
        
        history = None
        if request.history:
            history = [{"role": m.role, "content": m.content} for m in request.history]
        
        async def generate():
            sources = list(set(chunk.document_name for chunk in relevant_chunks))
            yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
            
            async for chunk in chat_service.stream_chat_response(
                message=request.message,
                context=context,
                history=history
            ):
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
            
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
        
    except Exception as e:
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/api/documents", deprecated=True)
async def list_documents_legacy(session: AsyncSession = Depends(get_session)):
    """[DEPRECATED] Use /api/v1/documents instead."""
    try:
        from sqlalchemy import text
        result = await session.execute(
            text("""
                SELECT DISTINCT document_id, document_name, 
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
        
        return {"documents": documents, "total": len(documents)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
