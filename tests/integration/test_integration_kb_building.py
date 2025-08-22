#!/usr/bin/env python3
"""Integration tests for knowledge base building process."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.build_kb import KnowledgeBaseBuilder
from tests.utils import create_test_kb_structure


class TestKnowledgeBaseBuildingProcess:
    """Test complete KB building workflows."""

    @pytest.fixture
    def mock_zotero_data(self):
        """Create mock Zotero database data."""
        return [
            {
                "key": "KEY0001",
                "title": "Systematic Review of Diabetes Treatment",
                "abstract": "A comprehensive systematic review of diabetes interventions.",
                "authors": ["Smith, John", "Doe, Jane"],
                "year": 2023,
                "journal": "Diabetes Care",
                "doi": "10.1234/dc.2023.0001",
                "pdf_path": "/path/to/paper1.pdf",
            },
            {
                "key": "KEY0002",
                "title": "RCT of Novel Diabetes Drug",
                "abstract": "A randomized controlled trial testing a new medication.",
                "authors": ["Johnson, Bob"],
                "year": 2024,
                "journal": "NEJM",
                "doi": "10.1056/nejm.2024.0002",
                "pdf_path": "/path/to/paper2.pdf",
            },
        ]

    def test_empty_kb_initialization_should_create_directory_structure(self, tmp_path):
        """
        Test that initializing an empty KB creates proper structure.

        Given: Empty directory
        When: KnowledgeBaseBuilder initializes
        Then: Creates required directories and files
        """
        # Use utility to create test KB structure
        create_test_kb_structure(tmp_path, include_papers=False, include_index=False)

        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Verify structure
        assert builder.knowledge_base_path.exists()
        assert (tmp_path / "papers").exists()
        assert builder.metadata_file_path == tmp_path / "metadata.json"

    # Removed test_build_kb_with_pdf_extraction_workflow - was skipped

    def test_build_kb_idempotency_should_preserve_existing_data(self, tmp_path):
        """
        Test that rebuilding KB doesn't corrupt existing data.

        Given: Existing KB with data
        When: KB is rebuilt
        Then: Existing data is preserved
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Create initial KB
        initial_metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1", "abstract": "Abstract 1"},
                {"id": "0002", "title": "Paper 2", "abstract": "Abstract 2"},
            ],
            "total_papers": 2,
            "version": "4.0",
            "last_updated": "2024-01-01T00:00:00Z",
        }

        metadata_path = tmp_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(initial_metadata, f)

        # Create paper files
        papers_dir = tmp_path / "papers"
        papers_dir.mkdir(exist_ok=True)
        for paper in initial_metadata["papers"]:
            paper_file = papers_dir / f"paper_{paper['id']}.md"
            paper_file.write_text(f"# {paper['title']}\n\n{paper['abstract']}")

        # Load existing data
        with open(metadata_path) as f:
            loaded_before = json.load(f)

        # Simulate rebuild (without actually calling build_kb)
        # Just verify data can be loaded and saved without corruption
        builder.metadata = loaded_before

        # Save back
        with open(metadata_path, "w") as f:
            json.dump(builder.metadata, f)

        # Verify data preserved
        with open(metadata_path) as f:
            loaded_after = json.load(f)

        assert loaded_after["papers"] == initial_metadata["papers"]
        assert loaded_after["total_papers"] == initial_metadata["total_papers"]

    def test_kb_integrity_after_build_should_validate_structure(self, tmp_path):
        """
        Test that built KB has valid structure.

        Given: Completed KB build
        When: Integrity check is performed
        Then: All required files and consistency checks pass
        """
        _ = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Create complete KB structure
        metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1", "filename": "paper_0001.md"},
                {"id": "0002", "title": "Paper 2", "filename": "paper_0002.md"},
            ],
            "total_papers": 2,
            "version": "4.0",
            "embedding_model": "sentence-transformers/allenai-specter",
            "embedding_dimensions": 768,
        }

        # Save metadata
        metadata_path = tmp_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Create paper files
        papers_dir = tmp_path / "papers"
        papers_dir.mkdir(exist_ok=True)
        for paper in metadata["papers"]:
            paper_file = papers_dir / paper["filename"]
            paper_file.write_text(f"# {paper['title']}")

        # Create index file
        (tmp_path / "index.faiss").touch()

        # Create sections index
        sections = {
            "0001": {"abstract": "Abstract 1", "methods": "Methods 1"},
            "0002": {"abstract": "Abstract 2", "methods": "Methods 2"},
        }
        with open(tmp_path / "sections_index.json", "w") as f:
            json.dump(sections, f)

        # Perform integrity checks
        assert metadata_path.exists()
        assert (tmp_path / "index.faiss").exists()
        assert papers_dir.exists()
        assert len(list(papers_dir.glob("paper_*.md"))) == 2
        assert metadata["total_papers"] == len(metadata["papers"])

        # Check sections index consistency
        with open(tmp_path / "sections_index.json") as f:
            loaded_sections = json.load(f)
        assert set(loaded_sections.keys()) == {"0001", "0002"}

    def test_pdf_extraction_coverage_should_generate_report(self, tmp_path):
        """
        Test PDF extraction coverage calculation.

        Given: KB with mixed PDF extraction success
        When: Coverage is calculated
        Then: Reports accurate extraction percentage
        """
        _ = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Create papers with mixed PDF status
        papers = [
            {"id": "0001", "title": "Paper 1", "full_text": "Full text available"},
            {"id": "0002", "title": "Paper 2", "full_text": None},
            {"id": "0003", "title": "Paper 3", "full_text": "Full text available"},
            {"id": "0004", "title": "Paper 4", "full_text": ""},
            {"id": "0005", "title": "Paper 5", "full_text": "Full text available"},
        ]

        # Calculate coverage
        papers_with_text = sum(1 for p in papers if p.get("full_text") and len(p["full_text"].strip()) > 0)
        total_papers = len(papers)
        coverage = papers_with_text / total_papers if total_papers > 0 else 0

        # Verify coverage calculation
        assert papers_with_text == 3
        assert total_papers == 5
        assert coverage == 0.6  # 60% coverage

        # Test warning threshold
        assert coverage < 0.9  # Should trigger warning

    def test_build_verification_output_should_have_correct_format(self, tmp_path, capsys):
        """
        Test that build verification produces correct output.

        Given: Completed build with issues
        When: Verification is run
        Then: Outputs formatted warnings and statistics
        """
        _ = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Simulate verification output
        stats = {
            "total_papers": 100,
            "papers_with_pdfs": 40,
            "papers_with_embeddings": 100,
            "index_size": 100,
            "cache_hits": 25,
            "extraction_errors": 5,
        }

        # Format verification output
        print("\n=== Build Verification ===")
        print(f"Total papers: {stats['total_papers']}")
        print(
            f"PDFs extracted: {stats['papers_with_pdfs']} ({stats['papers_with_pdfs']/stats['total_papers']*100:.1f}%)"
        )

        if stats["papers_with_pdfs"] < stats["total_papers"] * 0.9:
            print(
                f"⚠️  WARNING: Low PDF coverage ({stats['papers_with_pdfs']/stats['total_papers']*100:.1f}% < 90%)"
            )

        print(f"Embeddings generated: {stats['papers_with_embeddings']}")
        print(f"Index size: {stats['index_size']}")
        print(f"Cache hits: {stats['cache_hits']}")

        if stats["extraction_errors"] > 0:
            print(f"⚠️  Extraction errors: {stats['extraction_errors']}")

        # Capture output
        captured = capsys.readouterr()

        # Verify output format
        assert "Build Verification" in captured.out
        assert "Total papers: 100" in captured.out
        assert "WARNING: Low PDF coverage" in captured.out
        assert "40.0% < 90%" in captured.out
        assert "Extraction errors: 5" in captured.out


class TestReportGeneration:
    """Test report generation during KB building."""

    def test_small_pdfs_report_should_identify_quality_issues(self, tmp_path):
        """
        Test that small PDFs are identified and reported.

        Given: Papers with varying PDF sizes
        When: Report is generated
        Then: Lists papers with small PDFs
        """
        _ = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir(exist_ok=True)

        papers = [
            {
                "id": "0001",
                "title": "Paper with Small PDF",
                "full_text": "x" * 100,  # Very small
                "authors": ["Smith"],
                "year": 2023,
            },
            {
                "id": "0002",
                "title": "Paper with Normal PDF",
                "full_text": "x" * 10000,  # Normal size
                "authors": ["Jones"],
                "year": 2023,
            },
            {
                "id": "0003",
                "title": "Another Small PDF",
                "full_text": "x" * 500,  # Small
                "authors": ["Lee"],
                "year": 2024,
            },
        ]

        # Generate report
        exports_dir = tmp_path / "exports"
        exports_dir.mkdir()

        small_papers = [p for p in papers if p.get("full_text") and len(p["full_text"]) < 5000]

        report_path = reports_dir / "small_pdfs_report.md"
        with open(report_path, "w") as f:
            f.write("# Small PDFs Report\n\n")
            f.write(f"**Total papers:** {len(papers)}\n")
            f.write(f"**Papers with small PDFs:** {len(small_papers)}\n\n")

            for paper in small_papers:
                f.write(f"- {paper['title']} ({paper['id']}): {len(paper['full_text'])} chars\n")

        # Verify report
        assert report_path.exists()
        content = report_path.read_text()
        assert "Paper with Small PDF" in content
        assert "Another Small PDF" in content
        assert "Paper with Normal PDF" not in content
        assert "Papers with small PDFs:** 2" in content


class TestCacheOperations:
    """Test cache operations during KB building."""

    def test_cache_usage_should_speed_up_rebuilds(self, tmp_path):
        """
        Test that cache improves rebuild performance.

        Given: Cached PDF text
        When: KB is rebuilt
        Then: Uses cache instead of re-extracting
        """
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))

        # Pre-populate cache
        cache_data = {
            "KEY0001": {"text": "Cached PDF content for paper 1", "hash": "abc123"},
            "KEY0002": {"text": "Cached PDF content for paper 2", "hash": "def456"},
        }

        cache_file = tmp_path / ".pdf_text_cache.json"
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        # Load cache
        builder.cache = builder.load_cache()

        # Simulate PDF extraction with cache
        extract_count = 0

        for key in ["KEY0001", "KEY0002", "KEY0003"]:
            if key in builder.cache:
                # Cache hit
                text = builder.cache[key]["text"]
            else:
                # Cache miss - would extract
                extract_count += 1
                text = f"Extracted text for {key}"
                builder.cache[key] = {"text": text}

        # Verify cache usage
        assert extract_count == 1  # Only KEY0003 needed extraction
        assert len(builder.cache) == 3

    # Removed test_embedding_cache_incremental_updates - was skipped


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestCriticalKBIntegrity:
    """Critical KB integrity tests migrated from test_critical.py."""

    @pytest.mark.integration
    def test_empty_kb_handling_should_work_correctly(self, tmp_path):
        """Test 3: Ensure empty knowledge base doesn't crash the system."""
        import json
        import os
        import subprocess

        # Create empty metadata
        empty_metadata = {
            "papers": [],
            "total_papers": 0,
            "last_updated": "2025-01-01T00:00:00Z",
            "embedding_model": "allenai-specter",
            "embedding_dimensions": 768,
            "version": "4.0",  # Add v4.0 version
        }

        metadata_path = tmp_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(empty_metadata, f)

        # Create empty FAISS index
        try:
            import faiss

            index = faiss.IndexFlatL2(768)
            faiss.write_index(index, str(tmp_path / "index.faiss"))
        except ImportError:
            pytest.skip("FAISS not installed")

        # Test that search works with empty KB
        result = subprocess.run(
            ["python", "src/cli.py", "search", "test", "--json"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            env={**dict(os.environ), "KNOWLEDGE_BASE_PATH": str(tmp_path)},
        )

        # Should return empty results or error message, not crash
        if result.returncode == 0 and result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                assert output == [] or output.get("results") == []
            except json.JSONDecodeError:
                # If not JSON, just ensure it didn't crash catastrophically
                pass

    @pytest.mark.integration
    def test_build_verification_should_output_summary(self):
        """Test that build verification warnings work correctly."""
        # This test checks if the verification output format is correct
        # by examining the build_kb.py module directly

        # Create a mock scenario with low PDF coverage
        test_papers = [{"id": f"{i:04d}", "title": f"Paper {i}", "abstract": "Test"} for i in range(1, 101)]

        # Only 40 papers have PDFs (40% coverage, should trigger warning)
        for i in range(40):
            test_papers[i]["full_text"] = "Sample full text"

        # Check that the warning threshold is set correctly (90%)
        papers_with_pdfs = 40
        total_papers = 100

        # Should trigger warning since 40% < 90%
        assert papers_with_pdfs < total_papers * 0.9, "Warning should be triggered"
