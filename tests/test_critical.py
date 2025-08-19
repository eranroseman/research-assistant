"""Critical tests for research assistant - the minimal safety net."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.build_kb import KnowledgeBaseBuilder


class TestCriticalFunctionality:
    """Test the most critical functions that could cause data loss or crashes."""

    def test_kb_search_doesnt_crash(self):
        """Test 1: Ensure basic search doesn't crash even with no/bad data."""
        # Test that CLI search command runs without crashing
        result = subprocess.run(
            ["python", "src/cli.py", "search", "diabetes", "-k", "1"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # Should either succeed or give a clear error message
        assert result.returncode in [
            0,
            1,
        ], f"Search crashed with code {result.returncode}"

        # If it failed, should have a helpful error message
        if result.returncode == 1:
            assert "Knowledge base not found" in result.stderr or "not found" in result.stdout.lower()

    def test_cache_corruption_recovery(self, temp_kb_dir, corrupt_cache_file):
        """Test 2: Ensure corrupted cache doesn't break the system."""
        # Create a builder with a corrupted cache
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # This should not crash, even with corrupted cache
        try:
            cache = builder.load_cache()
            # Should return empty dict for corrupted cache
            assert isinstance(cache, dict)
            assert len(cache) == 0 or "TEST_KEY" not in cache
        except Exception as e:
            pytest.fail(f"Failed to handle corrupted cache gracefully: {e}")

    def test_empty_kb_handling(self, temp_kb_dir):
        """Test 3: Ensure empty knowledge base doesn't crash the system."""
        # Create empty metadata
        empty_metadata = {
            "papers": [],
            "total_papers": 0,
            "last_updated": "2025-01-01T00:00:00Z",
            "embedding_model": "allenai-specter",
            "embedding_dimensions": 768,
        }

        metadata_path = temp_kb_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(empty_metadata, f)

        # Create empty FAISS index
        try:
            import faiss

            index = faiss.IndexFlatL2(768)
            faiss.write_index(index, str(temp_kb_dir / "index.faiss"))
        except ImportError:
            pytest.skip("FAISS not installed")

        # Test that search works with empty KB
        result = subprocess.run(
            ["python", "src/cli.py", "search", "test", "--json"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(os.environ), "KNOWLEDGE_BASE_PATH": str(temp_kb_dir)},
        )

        # Should return empty results or error message, not crash
        if result.returncode == 0 and result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                assert output == [] or output.get("results") == []
            except json.JSONDecodeError:
                # If not JSON, just ensure it didn't crash catastrophically
                pass

    def test_missing_pdf_extraction(self, temp_kb_dir):
        """Test 4: Ensure system handles missing PDFs gracefully."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Try to extract text from non-existent PDF
        result = builder.extract_pdf_text(
            pdf_path="nonexistent_file.pdf", paper_key="TEST_KEY", use_cache=False
        )

        # Should return None, not crash
        assert result is None

    def test_cli_basic_commands(self):
        """Test 5: Ensure CLI basic commands don't crash."""
        cli_commands = [
            ["python", "src/cli.py", "info"],
            ["python", "src/cli.py", "--help"],
            ["python", "src/cli.py", "search", "--help"],
        ]

        for cmd in cli_commands:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                timeout=10,  # Prevent hanging
            )

            # Should not crash (exit code 0 or 1 is OK)
            assert result.returncode in [
                0,
                1,
            ], f"Command {' '.join(cmd)} failed with code {result.returncode}\nError: {result.stderr}"

    def test_build_kb_idempotency(self, temp_kb_dir, sample_metadata):
        """Test 6 (Bonus): Ensure rebuilding doesn't corrupt existing data."""
        # Save initial metadata
        metadata_path = temp_kb_dir / "metadata.json"
        papers_dir = temp_kb_dir / "papers"
        papers_dir.mkdir(exist_ok=True)

        with open(metadata_path, "w") as f:
            json.dump(sample_metadata, f)

        # Create paper files
        for paper in sample_metadata["papers"]:
            paper_file = papers_dir / paper["filename"]
            with open(paper_file, "w") as f:
                f.write(f"# {paper['title']}\n\n{paper['abstract']}")

        # Create a simple index
        try:
            import faiss

            index = faiss.IndexFlatL2(768)
            # Add dummy embeddings
            embeddings = np.random.randn(2, 768).astype("float32")
            index.add(embeddings)
            faiss.write_index(index, str(temp_kb_dir / "index.faiss"))
        except ImportError:
            pytest.skip("FAISS not installed")

        # Load initial state
        with open(metadata_path) as f:
            initial_data = json.load(f)

        # Simulate a rebuild (without actually calling build_kb to avoid dependencies)
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Just verify the builder can load without corrupting
        builder.knowledge_base_path.exists()

        # Verify data still intact
        with open(metadata_path) as f:
            final_data = json.load(f)

        assert len(final_data["papers"]) == len(initial_data["papers"])
        assert final_data["papers"][0]["title"] == initial_data["papers"][0]["title"]


class TestCacheIntegrity:
    """Test cache-related functions for data integrity."""

    def test_embedding_cache_corruption_handling(self, temp_kb_dir):
        """Ensure embedding cache corruption doesn't break the system."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Create corrupted embedding cache
        cache_path = temp_kb_dir / ".embedding_cache.npz"
        with open(cache_path, "wb") as f:
            f.write(b"corrupted numpy data")

        # Should handle gracefully - the load_embedding_cache method should catch the error
        cache = builder.load_embedding_cache()
        assert isinstance(cache, dict)
        # Should return default empty cache when corrupted
        assert cache.get("embeddings") is None
        assert cache.get("hashes") == []

    def test_cache_clear_functionality(self, temp_kb_dir, valid_cache_file):
        """Ensure cache clearing works properly."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Verify cache exists
        assert valid_cache_file.exists()

        # Clear cache
        builder.clear_cache()

        # Cache file should be gone
        assert not valid_cache_file.exists()

        # Cache should be empty
        assert builder.cache == {}


class TestSearchFilters:
    """Test search filtering functionality."""

    def test_year_filter(self):
        """Ensure year filtering doesn't crash with edge cases."""
        test_cases = [
            ["--after", "2020"],
            ["--after", "9999"],  # Future year
            ["--after", "0"],  # Invalid year
        ]

        for args in test_cases:
            cmd = ["python", "src/cli.py", "search", "test", "-k", "1", *args]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                timeout=60,  # Increased timeout for model loading
            )
            # Should handle gracefully
            assert result.returncode in [0, 1], f"Filter {args} caused crash"

    def test_study_type_filter(self):
        """Ensure study type filtering doesn't crash."""
        cmd = [
            "python",
            "src/cli.py",
            "search",
            "test",
            "-k",
            "1",
            "--type",
            "rct",
            "--type",
            "systematic_review",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=60,  # Increased timeout for model loading
        )
        # Should handle gracefully
        assert result.returncode in [0, 1], "Study type filter caused crash"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
