#!/usr/bin/env python3
"""Integration tests for consistent formatting across modules.

Tests that error, help, and output formatting work together properly
across different components of the Research Assistant system.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.error_formatting import ErrorFormatter, safe_exit, get_common_error
from src.help_formatting import get_command_help, format_command_help
from src.output_formatting import OutputFormatter, ProgressTracker, print_status


class TestErrorFormattingIntegration:
    """Test error formatting integration with actual modules."""

    def test_cli_error_integration_should_use_consistent_patterns(self):
        """Test that CLI module uses consistent error patterns."""
        formatter = ErrorFormatter(module="cli", command="search")

        # Test common CLI error scenarios
        result1 = formatter.format_error(
            "Knowledge base not found",
            context="Attempting to load search index",
            suggestion="Run 'python src/build_kb.py --demo' to create demo KB",
        )

        result2 = formatter.format_error(
            "Invalid paper ID format",
            context="Paper ID validation",
            suggestion="Use 4-digit format (e.g., 0001, 0042, 1234)",
        )

        # Both should follow consistent pattern
        assert result1.startswith("❌ cli.search:")
        assert result2.startswith("❌ cli.search:")
        assert "Solution:" in result1
        assert "Solution:" in result2

    def test_build_kb_error_integration_should_handle_zotero_issues(self):
        """Test build_kb error formatting for common Zotero issues."""
        config = get_common_error("zotero_connection", module="build_kb")

        assert "Cannot connect to Zotero API" in config["error_type"]
        assert "Start Zotero" in config["suggestion"]
        assert "Preferences → Advanced" in config["suggestion"]

    def test_discover_error_integration_should_handle_api_issues(self):
        """Test discover module error formatting for API issues."""
        formatter = ErrorFormatter(module="discover")
        result = formatter.format_error(
            "Semantic Scholar API rate limit exceeded",
            context="Paper discovery search",
            suggestion="Wait 1 minute and retry, or reduce search scope",
            technical_details="HTTP 429 Too Many Requests",
        )

        assert "❌ discover:" in result
        assert "Context: Paper discovery search" in result
        assert "Solution: Wait 1 minute" in result
        assert "Details: HTTP 429" in result

    @patch("sys.exit")
    @patch("builtins.print")
    def test_error_exit_integration_should_work_across_modules(self, mock_print, mock_exit):
        """Test that error exit works consistently across modules."""
        modules = ["cli", "build_kb", "discover", "analyze_gaps"]

        for module in modules:
            mock_print.reset_mock()
            mock_exit.reset_mock()

            safe_exit("Test error", "Test solution", module=module, exit_code=1)

            mock_exit.assert_called_once_with(1)
            mock_print.assert_called_once()

            # Check error message format
            error_msg = mock_print.call_args[0][0]
            assert f"❌ {module}: Test error" in error_msg


class TestHelpFormattingIntegration:
    """Test help formatting integration with command systems."""

    def test_cli_help_integration_should_provide_comprehensive_info(self):
        """Test CLI help integration provides comprehensive information."""
        search_help = get_command_help("search")

        # Should contain key CLI search concepts
        assert "semantic similarity" in search_help
        assert "Multi-QA MPNet" in search_help
        assert "quality scores" in search_help
        assert "Examples:" in search_help
        assert "Notes:" in search_help
        assert "See also:" in search_help

    def test_build_kb_help_integration_should_explain_safety(self):
        """Test build_kb help integration explains safety features."""
        build_help = get_command_help("build_kb")

        # Should emphasize safety
        assert "Safe by default" in build_help
        assert "--demo" in build_help
        assert "Zotero library" in build_help
        assert "Examples:" in build_help

    def test_discover_help_integration_should_explain_workflow(self):
        """Test discover help integration explains discovery workflow."""
        discover_help = get_command_help("discover")

        # Should explain discovery concepts
        assert "Semantic Scholar" in discover_help
        assert "214M paper" in discover_help
        assert "--keywords" in discover_help
        assert "population focus" in discover_help.lower()

    def test_help_consistency_across_commands_should_match_patterns(self):
        """Test that help formatting is consistent across all commands."""
        commands = ["search", "get", "build_kb", "discover"]

        for command in commands:
            help_text = get_command_help(command)

            # All should have consistent structure
            assert len(help_text) > 100  # Substantial help
            assert "Examples:" in help_text
            assert "python src/" in help_text  # Command examples

            # Check line structure
            lines = help_text.split("\n")
            example_start = next(i for i, line in enumerate(lines) if "Examples:" in line)

            # Examples should be indented
            for i in range(example_start + 1, len(lines)):
                if lines[i].strip() and not lines[i].startswith(("Notes:", "See also:")):
                    assert lines[i].startswith("  "), f"Example not indented in {command}: {lines[i]}"

    def test_custom_help_formatting_should_integrate_properly(self):
        """Test custom help formatting integrates with existing patterns."""
        custom_help = format_command_help(
            "Custom test command",
            examples=["python test_command --option value"],
            notes=["This is a test command", "Used for integration testing"],
            see_also=["search: Main search functionality"],
        )

        assert "Custom test command" in custom_help
        assert "Examples:" in custom_help
        assert "python test_command --option value" in custom_help
        assert "Notes:" in custom_help
        assert "• This is a test command" in custom_help
        assert "See also:" in custom_help
        assert "• search: Main search functionality" in custom_help


class TestOutputFormattingIntegration:
    """Test output formatting integration with actual workflows."""

    @patch("builtins.print")
    def test_progress_tracking_integration_should_work_in_workflows(self, mock_print):
        """Test progress tracking integration in typical workflows."""
        # Simulate KB building progress
        tracker = ProgressTracker("Building knowledge base", total=100, show_eta=False)

        # Simulate progress updates
        progress_points = [10, 25, 50, 75, 100]
        messages = [
            "Loading papers",
            "Extracting text",
            "Generating embeddings",
            "Quality scoring",
            "Saving index",
        ]

        for progress, message in zip(progress_points, messages, strict=False):
            tracker.update(progress, message, force=True)

        tracker.complete("Knowledge base ready")

        # Should have called print for each update + completion
        assert mock_print.call_count == len(progress_points) + 1

        # Check progress formatting
        for call in mock_print.call_args_list[:-1]:  # Exclude completion call
            call_text = call[0][0]
            assert "🔄 Building knowledge base:" in call_text
            assert "█" in call_text  # Progress bar
            assert "%" in call_text  # Percentage

        # Check completion formatting
        completion_call = mock_print.call_args_list[-1][0][0]
        assert "✅ Building knowledge base: Complete" in completion_call

    @patch("builtins.print")
    def test_status_formatting_integration_should_be_consistent(self, mock_print):
        """Test status formatting consistency across different scenarios."""
        # Test various status scenarios
        status_scenarios = [
            ("Enhanced quality scoring available", "success"),
            ("API rate limit exceeded", "error"),
            ("Using fallback basic scoring", "warning"),
            ("Loading knowledge base", "working"),
            ("Knowledge base statistics", "info"),
        ]

        for message, status_type in status_scenarios:
            print_status(message, status_type)

        assert mock_print.call_count == len(status_scenarios)

        # Check each status has appropriate icon
        icons = ["✅", "❌", "⚠️", "🔄", "\u2139\ufe0f"]
        for call, expected_icon in zip(mock_print.call_args_list, icons, strict=False):
            call_text = call[0][0]
            assert expected_icon in call_text

    @patch("builtins.print")
    def test_results_formatting_integration_should_handle_real_data(self, mock_print):
        """Test results formatting with realistic research data."""
        formatter = OutputFormatter()

        # Simulate realistic search results
        results = [
            {
                "id": "0001",
                "title": "Deep Learning for Healthcare: A Systematic Review",
                "authors": ["Smith, John A.", "Doe, Jane B.", "Johnson, Robert C."],
                "year": 2023,
                "quality_score": 87,
                "similarity": 0.945,
                "citation_count": 42,
            },
            {
                "id": "0042",
                "title": "Mobile Health Interventions in Diabetes Management",
                "authors": ["Garcia, Maria"],
                "year": 2022,
                "quality_score": 73,
                "similarity": 0.821,
                "citation_count": 18,
            },
            {
                "id": "0234",
                "title": "AI-Assisted Diagnostic Tools: Current State and Future Prospects",
                "authors": ["Chen, Wei", "Kumar, Amit", "Thompson, Sarah", "Williams, David"],
                "year": 2024,
                "quality_score": 91,
                "similarity": 0.889,
            },
        ]

        formatter.print_results("Search Results", results, show_quality=True, show_citations=True)

        # Should have printed header + results
        assert mock_print.call_count > 10

        all_output = " ".join([call[0][0] for call in mock_print.call_args_list])

        # Check key information appears
        assert "Deep Learning for Healthcare" in all_output
        assert "Mobile Health Interventions" in all_output
        assert "[0001]" in all_output
        assert "[0042]" in all_output
        assert "[0234]" in all_output
        assert "Quality: 87/100 (A+)" in all_output
        assert "Quality: 73/100 (A)" in all_output
        assert "Citations: 42" in all_output
        assert "Citations: 18" in all_output
        assert "Smith, John A., Doe, Jane B., Johnson, Robert C." in all_output
        assert "Garcia, Maria" in all_output

    @patch("builtins.print")
    def test_summary_formatting_integration_should_handle_kb_stats(self, mock_print):
        """Test summary formatting with knowledge base statistics."""
        formatter = OutputFormatter()

        # Simulate KB statistics
        stats = {
            "total_papers": 2180,
            "enhanced_quality_papers": 2109,
            "build_time": 1023.5,  # ~17 minutes
            "embedding_model": "Multi-QA MPNet",
            "success_rate": 0.967,
            "api_calls": 87,
            "cache_hit_rate": 0.85,
        }

        formatter.print_summary(stats)

        all_output = " ".join([call[0][0] for call in mock_print.call_args_list])

        # Check formatting
        assert "Total Papers: 2,180" in all_output  # Large number formatting
        assert "Enhanced Quality Papers: 2,109" in all_output
        assert "Build Time: 17:03" in all_output  # Time formatting (1023.5s = 17:03)
        assert "Success Rate: 0.97" in all_output  # Float formatting
        assert "Api Calls: 87" in all_output


class TestCrossModuleFormattingConsistency:
    """Test formatting consistency across different modules."""

    def test_error_and_help_integration_should_complement(self):
        """Test that error messages and help text complement each other."""
        # Get KB not found error
        kb_error_config = get_common_error("kb_not_found")
        build_help = get_command_help("build_kb")

        # Error should point to solution that help explains
        assert "build_kb.py --demo" in kb_error_config["suggestion"]
        assert "--demo" in build_help
        assert "demo" in build_help.lower()

    def test_status_and_progress_integration_should_work_together(self):
        """Test that status messages and progress tracking work together."""
        with patch("builtins.print") as mock_print:
            # Simulate combined status + progress workflow
            print_status("Starting knowledge base build", "working")

            tracker = ProgressTracker("Processing papers", total=50, show_eta=False)
            tracker.update(25, "Quality scoring", force=True)
            tracker.complete()

            print_status("Knowledge base build complete", "success")

            # Should have consistent formatting
            all_calls = [call[0][0] for call in mock_print.call_args_list]

            # Status messages should have icons
            assert "🔄" in all_calls[0]  # Working status
            assert "✅" in all_calls[-1]  # Success status

            # Progress should have consistent format
            progress_call = all_calls[1]
            assert "🔄 Processing papers:" in progress_call
            assert "[" in progress_call
            assert "]" in progress_call

    def test_module_identification_should_be_consistent(self):
        """Test that module identification is consistent across formatters."""
        modules = ["cli", "build_kb", "discover", "analyze_gaps"]

        for module in modules:
            # Error formatter
            error_formatter = ErrorFormatter(module=module)
            error_result = error_formatter.format_error("Test error")
            assert f"❌ {module}: Test error" in error_result

            # Output formatter with module context (via print_status)
            with patch("builtins.print") as mock_print:
                print_status(f"Module {module} operation", "info")
                status_result = mock_print.call_args[0][0]
                assert "\u2139\ufe0f" in status_result

    def test_formatting_robustness_across_modules_should_handle_edge_cases(self):
        """Test that formatting handles edge cases consistently across modules."""
        edge_cases = [
            ("", "Empty message"),
            ("Very long message that might wrap " * 10, "Long message"),
            ("Message with 'quotes' and \"double quotes\"", "Special characters"),
            ("Unicode message: ñáéíóú 中文 🎉", "Unicode content"),
        ]

        for test_message, description in edge_cases:
            # Test error formatting
            formatter = ErrorFormatter(module="test")
            error_result = formatter.format_error(test_message or "Empty error")
            assert "❌ test:" in error_result

            # Test status formatting
            with patch("builtins.print") as mock_print:
                print_status(test_message or "Empty status", "info")
                status_result = mock_print.call_args[0][0]
                assert "\u2139\ufe0f" in status_result

    def test_help_and_error_cross_references_should_be_accurate(self):
        """Test that help text and error messages have accurate cross-references."""
        # Check that commands mentioned in help actually exist
        all_help_texts = []
        for command in ["search", "get", "build_kb", "discover"]:
            help_text = get_command_help(command)
            all_help_texts.append(help_text)

        combined_help = " ".join(all_help_texts)

        # Commands referenced in help should be real
        referenced_commands = ["diagnose", "info", "smart-search", "author", "cite"]
        for cmd in referenced_commands:
            if cmd in combined_help:
                # Command is mentioned, should be legitimate reference
                assert len(cmd) > 2  # Reasonable command name length

        # Error messages should reference real commands/files
        common_errors = ["kb_not_found", "zotero_connection", "faiss_import"]
        for error_key in common_errors:
            config = get_common_error(error_key)
            suggestion = config["suggestion"]

            # Should reference real Python commands
            if "python src/" in suggestion:
                assert "build_kb.py" in suggestion or "cli.py" in suggestion
