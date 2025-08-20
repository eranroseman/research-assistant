#!/usr/bin/env python3
"""
Tests for incremental update functionality.

These tests verify that the knowledge base performs minimal work
when updating, only generating embeddings for changed papers.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

# Add src to path
sys.path.insert(0, "src")


class TestIncrementalUpdates:
    """Test suite for incremental KB updates."""

    @pytest.fixture
    def temp_kb(self):
        """Create a temporary KB directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_path = Path(tmpdir) / "kb_data"
            kb_path.mkdir()
            (kb_path / "papers").mkdir()
            yield kb_path

    def create_test_metadata(self, kb_path: Path, num_papers: int = 5):
        """Create test metadata.json with papers."""
        papers = []
        for i in range(1, num_papers + 1):
            papers.append(
                {
                    "id": f"{i:04d}",
                    "title": f"Test Paper {i}",
                    "abstract": f"Abstract for paper {i}",
                    "authors": [f"Author {i}"],
                    "year": 2020 + i,
                    "doi": f"10.1000/test{i}",
                    "journal": "Test Journal",
                    "study_type": "rct",
                    "sample_size": 100 * i,
                    "has_full_text": False,
                    "filename": f"paper_{i:04d}.md",
                    "zotero_key": f"KEY{i:04d}",
                }
            )

            # Create paper file
            paper_file = kb_path / "papers" / f"paper_{i:04d}.md"
            paper_file.write_text(f"# {papers[-1]['title']}\n\n{papers[-1]['abstract']}")

        metadata = {
            "papers": papers,
            "total_papers": num_papers,
            "version": "4.0",
            "last_updated": "2024-01-19T10:00:00Z",
        }

        with open(kb_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    def create_test_index(self, kb_path: Path, num_embeddings: int):
        """Create a test FAISS index with embeddings."""
        import faiss

        # Create random embeddings
        embeddings = np.random.rand(num_embeddings, 768).astype("float32")

        # Create and save index
        index = faiss.IndexFlatL2(768)
        index.add(embeddings)
        faiss.write_index(index, str(kb_path / "index.faiss"))

        return index

    @patch("build_kb.KnowledgeBaseBuilder.embedding_model", new_callable=PropertyMock)
    def test_incremental_update_only_new_papers(self, mock_embedding_prop, temp_kb):
        """Verify only new papers get embedded."""
        from build_kb import KnowledgeBaseBuilder

        # Create mock embedding model
        mock_model = MagicMock()
        embeddings_generated = []

        def mock_encode(texts, show_progress_bar=True, batch_size=64):
            # Track what was encoded
            embeddings_generated.extend(texts)
            # Return deterministic embeddings
            result = []
            for text in texts:
                seed = hash(text) % 10000
                np.random.seed(seed)
                result.append(np.random.rand(768).astype("float32"))
            return np.array(result)

        mock_model.encode = MagicMock(side_effect=mock_encode)
        mock_embedding_prop.return_value = mock_model

        # Setup: Create KB with 5 papers
        builder = KnowledgeBaseBuilder(str(temp_kb))
        self.create_test_metadata(temp_kb, 5)
        self.create_test_index(temp_kb, 5)

        # Add 2 new papers to metadata
        with open(temp_kb / "metadata.json") as f:
            metadata = json.load(f)

        for i in [6, 7]:
            metadata["papers"].append(
                {
                    "id": f"{i:04d}",
                    "title": f"Test Paper {i}",
                    "abstract": f"Abstract for paper {i}",
                    "authors": [f"Author {i}"],
                    "year": 2020 + i,
                    "doi": f"10.1000/test{i}",
                    "journal": "Test Journal",
                    "study_type": "rct",
                    "sample_size": 100 * i,
                    "has_full_text": False,
                    "filename": f"paper_{i:04d}.md",
                    "zotero_key": f"KEY{i:04d}",
                }
            )
        metadata["total_papers"] = 7

        with open(temp_kb / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Simulate changes for incremental update
        changes = {
            "new_keys": {"KEY0006", "KEY0007"},
            "updated_keys": set(),
            "deleted_keys": set(),
            "new": 2,
            "updated": 0,
            "deleted": 0,
            "needs_reindex": False,
        }

        # Run incremental update
        builder.update_index_incrementally(metadata["papers"], changes)

        # Verify: Only 2 new papers were embedded
        assert (
            len(embeddings_generated) == 2
        ), f"Should encode exactly 2 new papers, got {len(embeddings_generated)}"

        # Check that the new papers were the ones encoded
        encoded_texts = set(embeddings_generated)
        assert any("Test Paper 6" in text for text in encoded_texts), "Paper 6 should be encoded"
        assert any("Test Paper 7" in text for text in encoded_texts), "Paper 7 should be encoded"

        # Verify the index has 7 total embeddings
        import faiss

        index = faiss.read_index(str(temp_kb / "index.faiss"))
        assert index.ntotal == 7, f"Index should have 7 papers, got {index.ntotal}"

    @patch("build_kb.KnowledgeBaseBuilder.embedding_model", new_callable=PropertyMock)
    def test_reuse_existing_embeddings(self, mock_embedding_prop, temp_kb):
        """Verify unchanged papers keep embeddings."""
        from build_kb import KnowledgeBaseBuilder

        # Create mock embedding model
        mock_model = MagicMock()
        embeddings_generated = []

        def mock_encode(texts, show_progress_bar=True, batch_size=64):
            embeddings_generated.extend(texts)
            result = []
            for text in texts:
                seed = hash(text) % 10000
                np.random.seed(seed)
                result.append(np.random.rand(768).astype("float32"))
            return np.array(result)

        mock_model.encode = MagicMock(side_effect=mock_encode)
        mock_embedding_prop.return_value = mock_model

        # Setup: Create KB with 5 papers and index
        builder = KnowledgeBaseBuilder(str(temp_kb))
        self.create_test_metadata(temp_kb, 5)
        self.create_test_index(temp_kb, 5)

        # Load metadata and modify paper 3
        with open(temp_kb / "metadata.json") as f:
            metadata = json.load(f)

        metadata["papers"][2]["abstract"] = "Updated abstract for paper 3"

        with open(temp_kb / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Simulate updating 1 paper
        changes = {
            "new_keys": set(),
            "updated_keys": {"KEY0003"},
            "deleted_keys": set(),
            "new": 0,
            "updated": 1,
            "deleted": 0,
            "needs_reindex": False,
        }

        # Run incremental update
        builder.update_index_incrementally(metadata["papers"], changes)

        # Verify: Only 1 embedding was regenerated
        assert (
            len(embeddings_generated) == 1
        ), f"Should encode exactly 1 updated paper, got {len(embeddings_generated)}"
        assert "Updated abstract" in embeddings_generated[0], "Should encode the updated paper"

        # Verify index still has 5 papers
        import faiss

        index = faiss.read_index(str(temp_kb / "index.faiss"))
        assert index.ntotal == 5, f"Index should still have 5 papers, got {index.ntotal}"

    @patch("build_kb.KnowledgeBaseBuilder.embedding_model", new_callable=PropertyMock)
    def test_corrupted_index_triggers_rebuild(self, mock_embedding_prop, temp_kb):
        """Verify graceful handling of corruption."""
        from build_kb import KnowledgeBaseBuilder

        # Create mock embedding model
        mock_model = MagicMock()
        embeddings_generated = []

        def mock_encode(texts, show_progress_bar=True, batch_size=64):
            embeddings_generated.extend(texts)
            result = []
            for text in texts:
                seed = hash(text) % 10000
                np.random.seed(seed)
                result.append(np.random.rand(768).astype("float32"))
            return np.array(result)

        mock_model.encode = MagicMock(side_effect=mock_encode)
        mock_embedding_prop.return_value = mock_model

        # Setup: Create KB with metadata but corrupt index
        builder = KnowledgeBaseBuilder(str(temp_kb))
        self.create_test_metadata(temp_kb, 5)

        # Create corrupted index file
        with open(temp_kb / "index.faiss", "wb") as f:
            f.write(b"CORRUPTED DATA NOT A REAL FAISS INDEX")

        with open(temp_kb / "metadata.json") as f:
            metadata = json.load(f)

        # Simulate no changes but checking index
        changes = {
            "new_keys": set(),
            "updated_keys": set(),
            "deleted_keys": set(),
            "new": 0,
            "updated": 0,
            "deleted": 0,
            "needs_reindex": False,
        }

        # Run update - should trigger rebuild due to corruption
        builder.update_index_incrementally(metadata["papers"], changes)

        # Verify: Full rebuild was triggered (all 5 papers embedded)
        assert len(embeddings_generated) == 5, f"Should rebuild all 5 papers, got {len(embeddings_generated)}"

        # Verify index is now valid with 5 papers
        import faiss

        index = faiss.read_index(str(temp_kb / "index.faiss"))
        assert index.ntotal == 5, f"Index should have 5 papers after rebuild, got {index.ntotal}"

    @patch("build_kb.KnowledgeBaseBuilder.embedding_model", new_callable=PropertyMock)
    def test_missing_index_triggers_build(self, mock_embedding_prop, temp_kb):
        """Verify missing index triggers full build."""
        from build_kb import KnowledgeBaseBuilder

        # Create mock embedding model
        mock_model = MagicMock()
        embeddings_generated = []

        def mock_encode(texts, show_progress_bar=True, batch_size=64):
            embeddings_generated.extend(texts)
            result = []
            for text in texts:
                seed = hash(text) % 10000
                np.random.seed(seed)
                result.append(np.random.rand(768).astype("float32"))
            return np.array(result)

        mock_model.encode = MagicMock(side_effect=mock_encode)
        mock_embedding_prop.return_value = mock_model

        # Setup: Create KB with metadata but no index
        builder = KnowledgeBaseBuilder(str(temp_kb))
        self.create_test_metadata(temp_kb, 5)

        # Ensure no index exists
        index_path = temp_kb / "index.faiss"
        if index_path.exists():
            index_path.unlink()

        with open(temp_kb / "metadata.json") as f:
            metadata = json.load(f)

        changes = {
            "new_keys": set(),
            "updated_keys": set(),
            "deleted_keys": set(),
            "new": 0,
            "updated": 0,
            "deleted": 0,
            "needs_reindex": False,
        }

        # Run update - should build index from scratch
        builder.update_index_incrementally(metadata["papers"], changes)

        # Verify: All papers were embedded
        assert (
            len(embeddings_generated) == 5
        ), f"Should build embeddings for all 5 papers, got {len(embeddings_generated)}"

        # Verify index now exists with correct size
        import faiss

        index = faiss.read_index(str(temp_kb / "index.faiss"))
        assert index.ntotal == 5, f"Index should have 5 papers, got {index.ntotal}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
