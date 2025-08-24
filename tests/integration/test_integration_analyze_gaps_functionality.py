#!/usr/bin/env python3
"""
Simple integration tests to verify analyze_gaps.py unified formatting works.

These tests focus on the working functionality and avoid complex mocking
that causes import issues in the test environment.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestAnalyzeGapsFunctionalityWorks:
    """Test that core analyze_gaps.py functionality works with unified formatting."""

    def test_cli_help_command_works(self):
        """Test that CLI help command works correctly."""
        from click.testing import CliRunner
        from src.analyze_gaps import main

        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        # Should succeed
        assert result.exit_code == 0

        # Should contain expected help content
        assert "Network Gap Analysis" in result.output
        assert "OVERVIEW:" in result.output
        assert "GAP TYPES:" in result.output
        assert "--min-citations" in result.output
        assert "--year-from" in result.output
        assert "--limit" in result.output
        assert "--kb-path" in result.output

    def test_cli_parameter_validation_works(self):
        """Test that CLI parameter validation works with unified formatting."""
        from click.testing import CliRunner
        from src.analyze_gaps import main

        runner = CliRunner()

        # Test year validation
        result = runner.invoke(main, ["--year-from", "2010"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --year-from must be 2015 or later" in result.output
        assert "Context: Command-line argument validation" in result.output
        assert "Solution: Semantic Scholar coverage is limited before 2015" in result.output

        # Test future year validation
        result = runner.invoke(main, ["--year-from", "2030"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --year-from cannot be in the future" in result.output

        # Test limit validation
        result = runner.invoke(main, ["--limit", "0"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --limit must be positive" in result.output

        # Test citations validation
        result = runner.invoke(main, ["--min-citations", "-5"])
        assert result.exit_code == 1
        assert "❌ analyze_gaps: --min-citations cannot be negative" in result.output

    def test_imports_work_correctly(self):
        """Test that all required imports work correctly."""
        # Test that analyze_gaps can import its dependencies
        from src.analyze_gaps import validate_kb_requirements, run_gap_analysis, main

        # Test that formatting modules can be imported
        from src.error_formatting import safe_exit

        # All imports successful
        assert callable(validate_kb_requirements)
        assert callable(run_gap_analysis)
        assert callable(main)
        assert callable(safe_exit)

    def test_error_formatting_integration(self):
        """Test that error formatting integration works correctly."""
        from src.error_formatting import ErrorFormatter

        # Test the formatter used by analyze_gaps
        formatter = ErrorFormatter(module="analyze_gaps")

        result = formatter.format_error(
            "Test error message",
            "Test context information",
            "Test solution guidance",
            "Test technical details",
        )

        # Should have correct format
        assert "❌ analyze_gaps: Test error message" in result
        assert "Context: Test context information" in result
        assert "Solution: Test solution guidance" in result
        assert "Details: Test technical details" in result

    def test_status_formatting_integration(self):
        """Test that status formatting integration works correctly."""
        from unittest.mock import patch
        from src.output_formatting import print_status, print_header

        # Test status message formatting
        with patch("builtins.print") as mock_print:
            print_status("Test status message", "success")

            mock_print.assert_called_once()
            output = mock_print.call_args[0][0]
            assert "✅ Test status message" in output

        # Test header formatting
        with patch("builtins.print") as mock_print:
            print_header("🔍 Test Header")

            # Should print header with separators
            assert mock_print.call_count >= 1
            # Check that some call includes the header text
            all_output = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
            assert "🔍 Test Header" in all_output

    def test_progress_tracking_integration(self):
        """Test that progress tracking integration works correctly."""
        from unittest.mock import patch
        from src.output_formatting import ProgressTracker

        with patch("builtins.print") as mock_print:
            progress = ProgressTracker("Test Workflow", total=3, show_eta=False)
            progress.update(1, "Step 1")
            progress.update(2, "Step 2")
            progress.complete("All done")

            # Should have made multiple print calls
            assert mock_print.call_count >= 3

            # Check that progress elements appear in output
            all_output = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
            assert "🔄 Test Workflow:" in all_output
            assert "[" in all_output
            assert "]" in all_output
            assert "%" in all_output  # Percentage
            assert "✅ Test Workflow: Complete" in all_output

    def test_unified_formatting_consistency(self):
        """Test that all formatting follows consistent patterns."""
        from src.error_formatting import ErrorFormatter
        from src.output_formatting import print_status
        from unittest.mock import patch

        # Test that error messages use consistent module identification
        formatter = ErrorFormatter(module="analyze_gaps")
        error_result = formatter.format_error("Test error")
        assert "❌ analyze_gaps: Test error" in error_result

        # Test that status messages use consistent icons
        with patch("builtins.print") as mock_print:
            print_status("Test message", "info")
            output = mock_print.call_args[0][0]
            assert "\u2139\ufe0f Test message" in output

        with patch("builtins.print") as mock_print:
            print_status("Test message", "success")
            output = mock_print.call_args[0][0]
            assert "✅ Test message" in output

        with patch("builtins.print") as mock_print:
            print_status("Test message", "error")
            output = mock_print.call_args[0][0]
            assert "❌ Test message" in output


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
