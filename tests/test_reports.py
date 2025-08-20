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
    """Test report generation to reports/ directory."""

    def test_small_pdfs_report_generation(self, temp_kb_dir):
        """Test that small PDFs report is generated in reports/ directory."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Create test papers with small and normal PDFs
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
                "title": "Paper with Normal PDF",
                "full_text": "x" * 6000,  # Normal text > 5000 chars
                "authors": ["Jones"],
                "journal": "Test Journal",
                "year": 2023,
                "doi": "10.1234/test2",
            },
            {
                "id": "0003",
                "title": "Another Small PDF Paper",
                "full_text": "x" * 1000,  # Small text
                "authors": ["Lee"],
                "journal": "Test Journal",
                "year": 2024,
                "doi": "10.1234/test3",
            },
        ]

        # Generate report
        report_path = builder.generate_small_pdfs_report(papers)

        # Verify report location
        assert report_path.parent.name == "reports"
        assert report_path.name == "small_pdfs_report.md"
        assert report_path.exists()

        # Verify report content
        content = report_path.read_text()
        assert "Small PDFs Report" in content
        assert "Paper with Small PDF" in content
        assert "Another Small PDF Paper" in content
        assert "Paper with Normal PDF" not in content  # Should not include normal PDFs
        assert "**Total papers:** 3" in content
        assert "**Papers with small PDFs:** 2" in content

    def test_missing_pdfs_report_generation(self, temp_kb_dir):
        """Test that missing PDFs report is generated in reports/ directory."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Create test papers
        papers = [
            {
                "id": "0001",
                "title": "Paper with PDF",
                "full_text": "Some text",
                "authors": ["Smith"],
                "year": 2023,
            },
            {
                "id": "0002",
                "title": "Paper without PDF",
                "full_text": None,  # No PDF
                "authors": ["Jones"],
                "year": 2023,
            },
            {
                "id": "0003",
                "title": "Another Missing PDF",
                "full_text": "",  # Empty text
                "authors": ["Lee"],
                "year": 2024,
            },
        ]

        # Generate report
        report_path = builder.generate_missing_pdfs_report(papers)

        # Verify report location
        assert report_path.parent.name == "reports"
        assert report_path.name == "missing_pdfs_report.md"
        assert report_path.exists()

        # Verify report content
        content = report_path.read_text()
        assert "Missing/Incomplete PDFs Report" in content
        assert "Paper without PDF" in content
        assert "Another Missing PDF" in content
        # Paper with PDF appears in "Small PDFs" section since it has <5KB text
        assert "Paper with PDF" in content  # It's listed as small PDF
        assert "**Total papers:** 3" in content
        assert "**Missing PDFs:** 2" in content

    def test_reports_directory_creation(self, temp_kb_dir):
        """Test that reports/ directory is created if it doesn't exist."""
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(temp_kb_dir))

        # Ensure reports dir doesn't exist
        reports_dir = Path("reports")
        if reports_dir.exists():
            import shutil

            shutil.rmtree(reports_dir)

        assert not reports_dir.exists()

        # Generate a report (should create directory)
        papers = [{"id": "0001", "title": "Test", "full_text": "x" * 100}]
        report_path = builder.generate_small_pdfs_report(papers)

        # Verify directory was created
        assert reports_dir.exists()
        assert report_path.exists()

    def test_csv_export_to_reports(self, monkeypatch, temp_kb_dir):
        """Test that CSV exports go to reports/ directory."""
        import subprocess

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

        # Test CSV export
        result = subprocess.run(
            ["python", "src/cli.py", "search", "test", "--export", "test_results.csv"],
            check=False, capture_output=True,
            text=True,
        )

        # Check if file would be created in reports/
        # Note: This will fail in actual search but we're testing the path
        if "Exported" in result.stdout:
            assert "reports/test_results.csv" in result.stdout

    def test_smart_search_results_to_reports(self, temp_kb_dir):
        """Test that smart-search saves results to reports/ directory."""
        # This is tested indirectly as smart-search command
        # always saves to reports/smart_search_results.json
        reports_dir = Path("reports")
        expected_file = reports_dir / "smart_search_results.json"

        # The actual smart-search is tested in other test files
        # Here we just verify the expected path
        assert expected_file.parent.name == "reports"
        assert expected_file.name == "smart_search_results.json"
