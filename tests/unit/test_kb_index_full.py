#!/usr/bin/env python3
"""
Tests for cli_kb_index module - O(1) paper lookups and index operations.
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli_kb_index import KnowledgeBaseIndex


class TestKnowledgeBaseIndex:
    """Test O(1) lookup functionality."""

    def test_paper_lookup_by_id(self, temp_kb_dir):
        """Test O(1) paper lookup by ID."""
        # Create mock metadata
        metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1", "year": 2023},
                {"id": "0002", "title": "Paper 2", "year": 2024},
                {"id": "0003", "title": "Paper 3", "year": 2022},
            ],
            "version": "4.0",
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Test lookups
        kb_index = KnowledgeBaseIndex(str(temp_kb_dir))

        # Test valid ID lookup
        paper = kb_index.get_paper_by_id("0002")
        assert paper is not None
        assert paper["title"] == "Paper 2"

        # Test ID normalization (accepts "2" and returns paper "0002")
        paper = kb_index.get_paper_by_id("2")
        assert paper is not None
        assert paper["id"] == "0002"

        # Test non-existent ID
        paper = kb_index.get_paper_by_id("9999")
        assert paper is None

    def test_paper_lookup_by_index(self, temp_kb_dir):
        """Test paper lookup by FAISS index."""
        metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1"},
                {"id": "0002", "title": "Paper 2"},
            ],
            "version": "4.0",
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        kb_index = KnowledgeBaseIndex(str(temp_kb_dir))

        # Test valid index
        paper = kb_index.get_paper_by_index(0)
        assert paper["id"] == "0001"

        paper = kb_index.get_paper_by_index(1)
        assert paper["id"] == "0002"

        # Test out of range
        paper = kb_index.get_paper_by_index(10)
        assert paper is None

    def test_author_search(self, temp_kb_dir):
        """Test author search functionality."""
        metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1", "authors": ["John Smith", "Jane Doe"]},
                {"id": "0002", "title": "Paper 2", "authors": ["Alice Johnson"]},
                {"id": "0003", "title": "Paper 3", "authors": ["John Smith", "Bob Wilson"]},
            ],
            "version": "4.0",
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        kb_index = KnowledgeBaseIndex(str(temp_kb_dir))

        # Search for papers by John Smith
        papers = kb_index.search_by_author("John Smith")
        assert len(papers) == 2
        assert all("John Smith" in p.get("authors", []) for p in papers)

        # Case-insensitive partial match
        papers = kb_index.search_by_author("smith")
        assert len(papers) == 2

    def test_year_range_search(self, temp_kb_dir):
        """Test year range filtering."""
        metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1", "year": 2020},
                {"id": "0002", "title": "Paper 2", "year": 2022},
                {"id": "0003", "title": "Paper 3", "year": 2024},
                {"id": "0004", "title": "Paper 4", "year": 2021},
            ],
            "version": "4.0",
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        kb_index = KnowledgeBaseIndex(str(temp_kb_dir))

        # Search for papers in range
        papers = kb_index.search_by_year_range(2021, 2023)
        assert len(papers) == 2
        years = [p["year"] for p in papers]
        assert 2021 in years
        assert 2022 in years
        assert 2020 not in years
        assert 2024 not in years

    def test_consistency_validation(self, temp_kb_dir):
        """Test index consistency validation."""
        metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1"},
                {"id": "0002", "title": "Paper 2"},
            ],
            "version": "4.0",
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        kb_index = KnowledgeBaseIndex(str(temp_kb_dir))

        # Validate consistency
        result = kb_index.validate_consistency()
        assert result["valid"] is True
        assert result["total_papers"] == 2
        assert result["unique_ids"] == 2
        assert len(result["issues"]) == 0

    def test_invalid_paper_id_format(self, temp_kb_dir):
        """Test handling of invalid paper ID formats."""
        metadata = {"papers": [], "version": "4.0"}

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        kb_index = KnowledgeBaseIndex(str(temp_kb_dir))

        # Test various invalid formats
        with pytest.raises(ValueError, match="Invalid paper ID"):
            kb_index._normalize_id("abc")

        with pytest.raises(ValueError, match="Invalid paper ID"):
            kb_index._normalize_id("12345")  # Too many digits

        with pytest.raises(ValueError, match="Invalid paper ID"):
            kb_index._normalize_id("")

    def test_missing_kb_error(self):
        """Test error when KB doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Knowledge base not found"):
            KnowledgeBaseIndex("/nonexistent/path")

    def test_corrupted_metadata_error(self, temp_kb_dir):
        """Test error handling for corrupted metadata."""
        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            f.write("invalid json {")

        with pytest.raises(ValueError, match="Corrupted metadata file"):
            KnowledgeBaseIndex(str(temp_kb_dir))
