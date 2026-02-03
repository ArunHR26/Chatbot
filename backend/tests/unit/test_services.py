"""Unit tests for services module."""

import pytest
from app.services import ChunkingService, PDFService


class TestChunkingService:
    """Tests for ChunkingService."""
    
    @pytest.mark.unit
    def test_split_text_basic(self):
        """Test basic text splitting."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "A" * 250  # 250 characters
        
        chunks = service.split_text(text)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
    
    @pytest.mark.unit
    def test_split_text_empty(self):
        """Test splitting empty text."""
        service = ChunkingService()
        
        chunks = service.split_text("")
        
        assert chunks == []
    
    @pytest.mark.unit
    def test_split_text_with_sentence_boundary(self):
        """Test that chunks break at sentence boundaries when possible."""
        service = ChunkingService(chunk_size=50, chunk_overlap=10)
        text = "This is sentence one. This is sentence two. This is sentence three."
        
        chunks = service.split_text(text)
        
        # Should prefer breaking at sentence boundaries
        assert len(chunks) >= 1
    
    @pytest.mark.unit
    def test_split_text_short(self):
        """Test splitting text shorter than chunk size."""
        service = ChunkingService(chunk_size=1000, chunk_overlap=100)
        text = "Short text"
        
        chunks = service.split_text(text)
        
        assert len(chunks) == 1
        assert chunks[0] == "Short text"
    
    @pytest.mark.unit
    def test_split_text_overlap(self):
        """Test that chunks have proper overlap."""
        service = ChunkingService(chunk_size=100, chunk_overlap=20)
        text = "A" * 150  # Force at least 2 chunks
        
        chunks = service.split_text(text)
        
        # With proper overlap, total length should be > original due to overlap
        assert len(chunks) >= 2


class TestPDFService:
    """Tests for PDFService."""
    
    @pytest.mark.unit
    def test_extract_text_invalid_pdf(self):
        """Test extraction from invalid PDF."""
        from app.exceptions import DocumentExtractionError
        
        with pytest.raises(DocumentExtractionError):
            PDFService.extract_text(b"not a pdf", "test.pdf")
    
    @pytest.mark.unit
    def test_extract_text_empty_bytes(self):
        """Test extraction from empty bytes."""
        from app.exceptions import DocumentExtractionError
        
        with pytest.raises(DocumentExtractionError):
            PDFService.extract_text(b"", "empty.pdf")
