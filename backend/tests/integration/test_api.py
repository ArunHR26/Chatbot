"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.mark.integration
    async def test_health_check(self, client: AsyncClient):
        """Test health endpoint returns healthy status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rag-backend"


class TestDocumentEndpoints:
    """Tests for document-related endpoints."""
    
    @pytest.mark.integration
    async def test_list_documents_empty(self, client: AsyncClient):
        """Test listing documents when none exist."""
        response = await client.get("/api/v1/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["total"] == 0
    
    @pytest.mark.integration
    async def test_ingest_no_file(self, client: AsyncClient):
        """Test ingestion without file returns error."""
        response = await client.post("/api/v1/ingest")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    async def test_ingest_non_pdf(self, client: AsyncClient):
        """Test ingestion of non-PDF file returns error."""
        files = {"file": ("test.txt", b"not a pdf", "text/plain")}
        response = await client.post("/api/v1/ingest", files=files)
        
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]
    
    @pytest.mark.integration
    async def test_delete_nonexistent_document(self, client: AsyncClient):
        """Test deleting non-existent document returns 404."""
        response = await client.delete("/api/v1/documents/nonexistent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.integration
    async def test_stats_endpoint(self, client: AsyncClient):
        """Test stats endpoint."""
        response = await client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "chunks" in data


class TestChatEndpoints:
    """Tests for chat endpoints."""
    
    @pytest.mark.integration
    async def test_chat_empty_message(self, client: AsyncClient):
        """Test chat with empty message returns error."""
        response = await client.post(
            "/api/v1/chat",
            json={"message": ""}
        )
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    @pytest.mark.integration
    async def test_chat_whitespace_message(self, client: AsyncClient):
        """Test chat with whitespace-only message returns error."""
        response = await client.post(
            "/api/v1/chat",
            json={"message": "   "}
        )
        
        assert response.status_code == 400
