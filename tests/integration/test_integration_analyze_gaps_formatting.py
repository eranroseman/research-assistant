#!/usr/bin/env python3
"""
Integration tests for analyze_gaps.py unified formatting system.

Tests that the analyze_gaps.py CLI module properly integrates with the
unified error formatting, status formatting, and progress tracking systems.
"""

import sys
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.analyze_gaps import validate_kb_requirements, run_gap_analysis, main


class TestAnalyzeGapsErrorFormatting:
    """Test that analyze_gaps.py uses unified error formatting correctly."""

    @patch("builtins.print")
    @patch("sys.exit")
    def test_kb_not_found_error_formatting(self, mock_exit, mock_print, temp_kb_dir):
        """Test KB not found error uses unified formatting."""
        non_existent_path = temp_kb_dir / "non_existent"

        validate_kb_requirements(str(non_existent_path))

        # Should call sys.exit with code 1
        mock_exit.assert_called_once_with(1)

        # Should print unified error format
        mock_print.assert_called_once()
        error_output = mock_print.call_args[0][0]
        assert "❌ analyze_gaps: Knowledge base not found" in error_output
        assert "Context: KB validation during gap analysis" in error_output
        assert "Solution: Run: python src/build_kb.py --demo" in error_output

    @patch("builtins.print")
    @patch("sys.exit")
    def test_corrupted_metadata_error_formatting(self, mock_exit, mock_print, temp_kb_dir):
        """Test corrupted metadata error uses unified formatting."""
        # Create corrupted metadata file
        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            f.write("invalid json{")

        validate_kb_requirements(str(temp_kb_dir))

        mock_exit.assert_called_once_with(1)
        error_output = mock_print.call_args[0][0]
        assert "❌ analyze_gaps: Failed to load KB metadata" in error_output
        assert "Context: KB metadata loading during gap analysis" in error_output
        assert "Solution: Run: python src/build_kb.py --rebuild" in error_output
        assert "Details:" in error_output  # Should include JSON error details

    @patch("builtins.print")
    @patch("sys.exit")
    def test_version_mismatch_error_formatting(self, mock_exit, mock_print, temp_kb_dir):
        """Test version mismatch error uses unified formatting."""
        import json

        # Create metadata with wrong version
        metadata = {
            "version": "3.0",  # Wrong version
            "papers": [{"id": "0001", "title": "Test", "authors": ["Author"]}] * 25,
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        validate_kb_requirements(str(temp_kb_dir))

        mock_exit.assert_called_once_with(1)
        error_output = mock_print.call_args[0][0]
        assert "❌ analyze_gaps:" in error_output
        assert "KB v4." in error_output
        assert "required" in error_output
        assert "Context: KB version compatibility check" in error_output
        assert "Solution: Delete kb_data/ and rebuild" in error_output

    @patch("builtins.print")
    @patch("sys.exit")
    def test_insufficient_papers_error_formatting(self, mock_exit, mock_print, temp_kb_dir):
        """Test insufficient papers error uses unified formatting."""
        import json

        # Create metadata with too few papers
        metadata = {
            "version": "4.0",
            "papers": [{"id": "0001", "title": "Test", "authors": ["Author"]}],  # Only 1 paper
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        validate_kb_requirements(str(temp_kb_dir))

        mock_exit.assert_called_once_with(1)
        error_output = mock_print.call_args[0][0]
        assert "❌ analyze_gaps: Minimum 20 papers required for gap analysis" in error_output
        assert "Context: Paper count validation" in error_output
        assert "Found 1 papers" in error_output


class TestAnalyzeGapsStatusFormatting:
    """Test that analyze_gaps.py uses unified status formatting correctly."""

    @patch("src.analyze_gaps._import_gap_analyzer")
    @patch("builtins.print")
    def test_workflow_status_formatting(self, mock_print, mock_import_gap_analyzer, temp_kb_dir):
        """Test workflow uses unified status formatting."""
        import json

        # Create valid KB
        metadata = {
            "version": "4.0",
            "papers": [{"id": f"{i:04d}", "title": f"Paper {i}", "authors": ["Author"]} for i in range(25)],
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Mock GapAnalyzer
        mock_analyzer = AsyncMock()
        mock_analyzer.find_citation_gaps = AsyncMock(
            return_value=[{"title": "Gap 1", "gap_type": "citation_network"}]
        )
        mock_analyzer.find_author_gaps = AsyncMock(
            return_value=[{"title": "Gap 2", "gap_type": "author_network"}]
        )
        mock_analyzer.generate_report = AsyncMock(return_value=None)
        mock_analyzer_class = Mock(return_value=mock_analyzer)
        mock_import_gap_analyzer.return_value = mock_analyzer_class

        # Call the actual function with mocked dependencies
        import asyncio

        # Use a new event loop to avoid conflicts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_gap_analysis(str(temp_kb_dir), 0, 2022, None))
        finally:
            loop.close()

        # Check that status messages use unified formatting
        all_output = " ".join([str(call[0][0]) for call in mock_print.call_args_list if call[0]])

        # Should have header
        assert "🔍 Running Network Gap Analysis" in all_output
        assert "=" * 60 in all_output  # Header separator

        # Should have info status messages
        assert "\u2139\ufe0f" in all_output  # Info icon used
        assert "Knowledge Base:" in all_output
        assert "papers" in all_output
        assert "KB Version: v4.0" in all_output

        # Should have success status messages
        assert "✅" in all_output  # Success icon used
        assert "Gap Analysis Complete!" in all_output


class TestAnalyzeGapsProgressTracking:
    """Test that analyze_gaps.py integrates progress tracking correctly."""

    @patch("src.analyze_gaps._import_gap_analyzer")
    @patch("builtins.print")
    def test_progress_tracking_formatting_integration(
        self, mock_print, mock_import_gap_analyzer, temp_kb_dir
    ):
        """Test that progress tracking formatting shows workflow steps."""
        import json

        # Create valid KB
        metadata = {
            "version": "4.0",
            "papers": [{"id": f"{i:04d}", "title": f"Paper {i}", "authors": ["Author"]} for i in range(25)],
        }

        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)

        # Mock GapAnalyzer
        mock_analyzer = AsyncMock()
        mock_analyzer.find_citation_gaps = AsyncMock(return_value=[{"title": "Gap 1"}])
        mock_analyzer.find_author_gaps = AsyncMock(return_value=[{"title": "Gap 2"}])
        mock_analyzer.generate_report = AsyncMock(return_value=None)
        mock_analyzer_class = Mock(return_value=mock_analyzer)
        mock_import_gap_analyzer.return_value = mock_analyzer_class

        # Call the actual function with mocked dependencies
        import asyncio

        # Use a new event loop to avoid conflicts
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_gap_analysis(str(temp_kb_dir), 0, 2022, None))
        finally:
            loop.close()

        # Check that progress tracking is used
        all_output = " ".join([str(call[0][0]) for call in mock_print.call_args_list if call[0]])

        # Should show progress completion (mocked methods return immediately)
        assert "Gap Analysis Workflow:" in all_output  # Progress tracking component
        assert "Complete" in all_output  # Completion indicator
        assert "Analysis complete" in all_output  # Final status message


class TestAnalyzeGapsCLIFormatting:
    """Test that analyze_gaps.py CLI argument validation uses unified formatting."""

    def test_cli_year_validation_formatting(self):
        """Test CLI year validation uses unified error formatting."""
        from click.testing import CliRunner

        runner = CliRunner()

        # Test year too old
        result = runner.invoke(main, ["--year-from", "2010"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --year-from must be 2015 or later" in result.output
        assert "Context: Command-line argument validation" in result.output
        assert "Solution: Semantic Scholar coverage is limited before 2015" in result.output

        # Test future year
        result = runner.invoke(main, ["--year-from", "2030"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --year-from cannot be in the future" in result.output
        assert "Context: Command-line argument validation" in result.output

    def test_cli_limit_validation_formatting(self):
        """Test CLI limit validation uses unified error formatting."""
        from click.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(main, ["--limit", "0"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --limit must be positive" in result.output
        assert "Context: Command-line argument validation" in result.output
        assert "Solution: Use positive integer or omit for unlimited results" in result.output

    def test_cli_citations_validation_formatting(self):
        """Test CLI citations validation uses unified error formatting."""
        from click.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(main, ["--min-citations", "-5"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --min-citations cannot be negative" in result.output
        assert "Context: Command-line argument validation" in result.output
        assert "Solution: Use 0 for all papers or positive integer for citation threshold" in result.output


class TestAnalyzeGapsErrorContexts:
    """Test that analyze_gaps.py provides appropriate error contexts."""

    @patch("builtins.print")
    @patch("sys.exit")
    def test_error_contexts_are_specific(self, mock_exit, mock_print, temp_kb_dir):
        """Test that error messages provide specific operational context."""
        # Test multiple error scenarios to verify context specificity

        # KB not found context
        validate_kb_requirements(str(temp_kb_dir / "missing"))
        context1 = mock_print.call_args[0][0]
        assert "Context: KB validation during gap analysis" in context1

        mock_print.reset_mock()
        mock_exit.reset_mock()

        # Corrupted metadata context
        metadata_file = temp_kb_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            f.write("invalid")

        validate_kb_requirements(str(temp_kb_dir))
        context2 = mock_print.call_args[0][0]
        assert "Context: KB metadata loading during gap analysis" in context2

        # Contexts should be different and specific
        assert "KB validation" in context1
        assert "metadata loading" in context2

    def test_error_solutions_are_actionable(self):
        """Test that error solutions provide clear actionable steps."""
        from click.testing import CliRunner

        runner = CliRunner()

        # Test that solutions are specific and actionable
        result = runner.invoke(main, ["--year-from", "2010"])
        assert "Solution: Semantic Scholar coverage is limited before 2015" in result.output

        result = runner.invoke(main, ["--limit", "-10"])
        assert "Solution: Use positive integer or omit for unlimited results" in result.output

        result = runner.invoke(main, ["--min-citations", "-5"])
        assert "Solution: Use 0 for all papers or positive integer for citation threshold" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
