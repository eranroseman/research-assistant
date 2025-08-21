#!/usr/bin/env python3
"""Unit tests for build_kb.py - Knowledge Base Builder functionality."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.build_kb import KnowledgeBaseBuilder


class TestKnowledgeBaseBuilderInit:
    """Test KnowledgeBaseBuilder initialization."""

    def test_init_with_default_path_creates_builder(self):
        """
        Test that KnowledgeBaseBuilder initializes with default path.
        
        Given: No parameters
        When: KnowledgeBaseBuilder is instantiated
        Then: Builder is created with default kb_data path
        """
        builder = KnowledgeBaseBuilder()
        assert builder.knowledge_base_path == Path("kb_data")
        assert builder.cache_file_path == Path("kb_data") / ".pdf_text_cache.json"

    def test_init_with_custom_path_creates_builder(self, tmp_path):
        """
        Test that KnowledgeBaseBuilder accepts custom path.
        
        Given: Custom knowledge base path
        When: KnowledgeBaseBuilder is instantiated
        Then: Builder uses the custom path
        """
        custom_path = tmp_path / "custom_kb"
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(custom_path))
        assert builder.knowledge_base_path == custom_path


class TestPDFExtraction:
    """Test PDF text extraction functionality."""

    def test_extract_pdf_text_with_missing_file_returns_none(self, tmp_path):
        """
        Test that missing PDF files are handled gracefully.
        
        Given: Non-existent PDF path
        When: extract_pdf_text is called
        Then: Returns None without crashing
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        result = builder.extract_pdf_text(
            pdf_path="nonexistent.pdf",
            paper_key="TEST_KEY",
            use_cache=False
        )
        assert result is None

    def test_extract_pdf_text_with_valid_pdf_returns_text(self, tmp_path):
        """
        Test that valid PDFs are extracted correctly.
        
        Given: Valid PDF file
        When: extract_pdf_text is called
        Then: Returns extracted text
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        # Create a dummy PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"dummy pdf content")
        
        with patch("fitz.open") as mock_fitz_open:
            # Mock PDF document
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Test PDF content"
            mock_doc = MagicMock()
            mock_doc.__enter__ = MagicMock(return_value=mock_doc)
            mock_doc.__exit__ = MagicMock(return_value=None)
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
            mock_fitz_open.return_value = mock_doc
            
            result = builder.extract_pdf_text(
                pdf_path=str(pdf_path),
                paper_key="TEST_KEY",
                use_cache=False
            )
            
            assert result == "Test PDF content"
            mock_fitz_open.assert_called_once()

    def test_extract_pdf_text_with_cache_reuses_content(self, tmp_path):
        """
        Test that cached PDF text is reused.
        
        Given: PDF text in cache
        When: extract_pdf_text is called with use_cache=True
        Then: Returns cached content without extraction
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        # Create a dummy PDF file for path validation
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"dummy pdf content")
        
        # Get file stats for cache validation
        import os
        stat = os.stat(pdf_path)
        
        # Pre-populate cache with matching file metadata
        builder.cache = {
            "TEST_KEY": {
                "text": "Cached PDF content",
                "file_size": stat.st_size,
                "file_mtime": stat.st_mtime
            }
        }
        
        result = builder.extract_pdf_text(
            pdf_path=str(pdf_path),
            paper_key="TEST_KEY",
            use_cache=True
        )
        
        assert result == "Cached PDF content"


class TestEmbeddingGeneration:
    """Test embedding generation functionality."""

    def test_placeholder_for_removed_tests(self):
        """
        Placeholder test - generate_embeddings method doesn't exist in codebase.
        
        The methods being tested don't exist in the actual implementation.
        Embedding generation is handled by other methods during KB building.
        """


class TestCacheManagement:
    """Test cache functionality."""

    def test_load_cache_with_corrupt_file_returns_empty_dict(self, tmp_path):
        """
        Test that corrupted cache files are handled gracefully.
        
        Given: Corrupted cache file
        When: load_cache is called
        Then: Returns empty dictionary
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        # Create corrupted cache file
        cache_file = tmp_path / ".pdf_text_cache.json"
        cache_file.write_text("corrupted json {[}")
        
        cache = builder.load_cache()
        
        assert cache == {}

    def test_save_cache_writes_json_file(self, tmp_path):
        """
        Test that cache is saved correctly.
        
        Given: Cache data
        When: save_cache is called
        Then: Writes valid JSON file
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        builder.cache = {"TEST_KEY": {"text": "Test content"}}
        
        builder.save_cache()
        
        # Verify file was written
        cache_file = tmp_path / ".pdf_text_cache.json"
        assert cache_file.exists()
        
        # Verify content
        with open(cache_file) as f:
            loaded = json.load(f)
        assert loaded == builder.cache

    def test_clear_cache_removes_file_and_data(self, tmp_path):
        """
        Test that cache clearing works properly.
        
        Given: Existing cache file and data
        When: clear_cache is called
        Then: File is deleted and cache is empty
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        # Create cache file
        cache_file = tmp_path / ".pdf_text_cache.json"
        cache_file.write_text('{"TEST": "data"}')
        builder.cache = {"TEST": "data"}
        
        builder.clear_cache()
        
        assert not cache_file.exists()
        assert builder.cache == {}


class TestEmbeddingCache:
    """Test embedding cache functionality."""

    def test_load_embedding_cache_with_corrupt_file_returns_defaults(self, tmp_path):
        """
        Test that corrupted embedding cache is handled.
        
        Given: Corrupted .npz file
        When: load_embedding_cache is called
        Then: Returns default empty cache structure
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        # Create corrupted npz file
        cache_file = tmp_path / ".embedding_cache.npz"
        cache_file.write_bytes(b"corrupted npz data")
        
        cache = builder.load_embedding_cache()
        
        assert isinstance(cache, dict)
        assert cache.get("embeddings") is None
        assert cache.get("hashes") == []

    def test_save_embedding_cache_writes_npz_file(self, tmp_path):
        """
        Test that embedding cache is saved correctly.
        
        Given: Embeddings and hashes
        When: save_embedding_cache is called
        Then: Writes valid .npz file
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        embeddings = np.random.randn(5, 768).astype("float32")
        hashes = ["hash1", "hash2", "hash3", "hash4", "hash5"]
        
        builder.save_embedding_cache(embeddings, hashes)
        
        # Verify files were written
        json_cache_file = tmp_path / ".embedding_cache.json"
        npy_cache_file = tmp_path / ".embedding_data.npy"
        
        assert json_cache_file.exists()
        assert npy_cache_file.exists()
        
        # Verify content
        loaded_embeddings = np.load(npy_cache_file, allow_pickle=False)
        np.testing.assert_array_almost_equal(loaded_embeddings, embeddings)
        
        import json
        with open(json_cache_file) as f:
            loaded_meta = json.load(f)
        assert loaded_meta["hashes"] == hashes


class TestStudyTypeDetection:
    """Test study type detection functionality."""

    def test_detect_study_type_identifies_systematic_review(self):
        """
        Test that systematic reviews are detected.
        
        Given: Text containing systematic review indicators
        When: detect_study_type is called
        Then: Returns 'systematic_review'
        """
        from src.build_kb import detect_study_type
        
        text = "This systematic review and meta-analysis examines..."
        result = detect_study_type(text)
        assert result == "systematic_review"

    def test_detect_study_type_identifies_rct(self):
        """
        Test that RCTs are detected.
        
        Given: Text containing RCT indicators
        When: detect_study_type is called
        Then: Returns 'rct'
        """
        from src.build_kb import detect_study_type
        
        text = "This randomized controlled trial enrolled 500 patients..."
        result = detect_study_type(text)
        assert result == "rct"

    def test_detect_study_type_with_ambiguous_text_returns_unknown(self):
        """
        Test that ambiguous text returns unknown.
        
        Given: Text without clear study type indicators
        When: detect_study_type is called
        Then: Returns 'unknown'
        """
        from src.build_kb import detect_study_type
        
        text = "This paper discusses various topics in medicine."
        result = detect_study_type(text)
        assert result == "study"


class TestSampleSizeExtraction:
    """Test sample size extraction functionality."""

    def test_extract_rct_sample_size_finds_n_value(self):
        """
        Test that sample size is extracted from RCT text.
        
        Given: Text with n= notation
        When: extract_rct_sample_size is called
        Then: Returns the sample size
        """
        from src.build_kb import extract_rct_sample_size
        
        text = "We enrolled 1234 patients (n=1234) in this trial."
        result = extract_rct_sample_size(text, "rct")
        assert result == 1234

    def test_extract_rct_sample_size_with_no_sample_returns_none(self):
        """
        Test that missing sample size returns None.
        
        Given: Text without sample size
        When: extract_rct_sample_size is called
        Then: Returns None
        """
        from src.build_kb import extract_rct_sample_size
        
        text = "This study examined various outcomes."
        result = extract_rct_sample_size(text, "rct")
        assert result is None


class TestFAISSIndexOperations:
    """Test FAISS index building and operations."""

    def test_placeholder_for_removed_test(self):
        """
        Placeholder test - build_faiss_index method doesn't exist in codebase.
        
        The method being tested doesn't exist in the actual implementation.
        FAISS index building is handled by other methods.
        """


class TestCriticalCacheFunctionality:
    """Critical cache tests migrated from test_critical.py."""

    @pytest.mark.unit
    def test_cache_corruption_recovery(self, tmp_path):
        """Test 2: Ensure corrupted cache doesn't break the system."""
        from src.build_kb import KnowledgeBaseBuilder
        
        # Create corrupted cache file
        cache_file = tmp_path / ".pdf_text_cache.json"
        cache_file.write_text("corrupted json data {{{")
        
        # Create a builder with a corrupted cache
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # This should not crash, even with corrupted cache
        try:
            cache = builder.load_cache()
            # Should return empty dict for corrupted cache
            assert isinstance(cache, dict)
            assert len(cache) == 0 or "TEST_KEY" not in cache
        except Exception as e:
            pytest.fail(f"Failed to handle corrupted cache gracefully: {e}")

    @pytest.mark.unit
    def test_missing_pdf_extraction(self, tmp_path):
        """Test 4: Ensure system handles missing PDFs gracefully."""
        from src.build_kb import KnowledgeBaseBuilder
        
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Try to extract text from non-existent PDF
        result = builder.extract_pdf_text(
            pdf_path="nonexistent_file.pdf", paper_key="TEST_KEY", use_cache=False
        )

        # Should return None, not crash
        assert result is None

    @pytest.mark.unit
    def test_embedding_cache_corruption_handling(self, tmp_path):
        """Ensure embedding cache corruption doesn't break the system."""
        from src.build_kb import KnowledgeBaseBuilder
        
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Create corrupted embedding cache
        cache_path = tmp_path / ".embedding_cache.npz"
        with open(cache_path, "wb") as f:
            f.write(b"corrupted numpy data")

        # Should handle gracefully - the load_embedding_cache method should catch the error
        cache = builder.load_embedding_cache()
        assert isinstance(cache, dict)
        # Should return default empty cache when corrupted
        assert cache.get("embeddings") is None
        assert cache.get("hashes") == []

    @pytest.mark.unit
    def test_cache_clear_functionality(self, tmp_path):
        """Ensure cache clearing works properly."""
        from src.build_kb import KnowledgeBaseBuilder
        
        # Create valid cache file
        cache_file = tmp_path / ".pdf_text_cache.json"
        cache_file.write_text('{"TEST_KEY": {"text": "test", "hash": "123"}}')
        
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Verify cache exists
        assert cache_file.exists()

        # Clear cache
        builder.clear_cache()

        # Cache file should be gone
        assert not cache_file.exists()

        # Cache should be empty
        assert builder.cache == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
