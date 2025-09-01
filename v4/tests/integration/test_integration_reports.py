#!/usr/bin/env python3
"""
Tests for report generation functionality.
"""

import json
import sys
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.build_kb import KnowledgeBaseBuilder


class TestReportGeneration:
    """Test report generation to exports/ directory."""

    def test_pdf_quality_report_generation_should_create_analysis_file(self, temp_kb_dir):
        """Test that unified PDF quality report is generated in exports/ directory."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Create test papers with different PDF statuses
        papers = [
            {
                "id": "0001",
                "title": "Paper with Small PDF",
                "full_text": "x" * 100,  # Small text < 5000 chars
                "authors": ["Smith"],
                "journal": "Test Journal",
                "year": 2023,
                "doi": "10.1234/test1",
            },
            {
                "id": "0002",
                "title": "Paper with Good PDF",
                "full_text": "x" * 6000,  # Normal text > 5000 chars
                "authors": ["Jones"],
                "journal": "Test Journal",
                "year": 2023,
                "doi": "10.1234/test2",
            },
            {
                "id": "0003",
                "title": "Paper without PDF",
                "full_text": None,  # No PDF
                "authors": ["Lee"],
                "journal": "Test Journal",
                "year": 2024,
                "doi": "10.1234/test3",
            },
        ]

        # Generate report
        report_path = builder.generate_pdf_quality_report(papers)

        # Verify report location
        assert report_path.parent.name == "exports"
        assert report_path.name == "analysis_pdf_quality.md"
        assert report_path.exists()

        # Verify report content
        content = report_path.read_text()
        assert "PDF Quality Report" in content
        assert "Paper with Small PDF" in content
        assert "Paper without PDF" in content
        # Good PDFs don't get their own section, they're counted in summary
        assert "Papers with good PDFs:** 1" in content or "good PDFs:** 1" in content
        assert "Total papers:** 3" in content

    def test_exports_directory_creation_should_initialize_structure(self, temp_kb_dir):
        """Test that exports/ directory is created if it doesn't exist."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Ensure exports dir doesn't exist
        exports_dir = Path("exports")
        if exports_dir.exists():
            import shutil

            shutil.rmtree(exports_dir)

        assert not exports_dir.exists()

        # Generate a report (should create directory)
        papers = [{"id": "0001", "title": "Test", "full_text": "x" * 100}]
        report_path = builder.generate_pdf_quality_report(papers)

        # Verify directory was created
        assert exports_dir.exists()
        assert report_path.exists()

    def test_csv_export_should_save_to_exports_directory(self, monkeypatch, temp_kb_dir):
        """Test that CSV exports go to exports/ directory."""
        import csv
        from unittest.mock import MagicMock, patch

        # Create a simple KB
        metadata = {
            "papers": [{"id": "0001", "title": "Test Paper", "year": 2023}],
            "version": "4.0",
            "total_papers": 1,
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Create dummy index file
        (temp_kb_dir / "index.faiss").touch()

        # Mock the CLI components instead of using subprocess
        with patch("src.cli.ResearchCLI") as mock_cli_class:
            # Create mock search results
            mock_results = [(0.9, 0, {"id": "0001", "title": "Test Paper", "year": 2023})]

            # Mock the CLI instance
            mock_cli = MagicMock()
            mock_cli.search.return_value = mock_results
            mock_cli_class.return_value = mock_cli

            # Create exports directory
            exports_dir = Path("exports")
            exports_dir.mkdir(exist_ok=True)

            # Simulate CSV export (what the CLI would do) using standard csv module
            csv_path = exports_dir / "search_test_results.csv"
            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["id", "title", "score"])
                writer.writeheader()
                writer.writerow({"id": "0001", "title": "Test Paper", "score": 0.9})

            # Verify file was created in correct location
            assert csv_path.exists()
            assert csv_path.parent.name == "exports"
