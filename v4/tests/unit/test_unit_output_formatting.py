#!/usr/bin/env python3
"""Unit tests for output formatting module.

Tests unified output formatting system including:
- ProgressTracker class functionality
- OutputFormatter class methods
- Result formatting and display functions
- Consistent status and progress indicators
"""

import time
from unittest.mock import patch

import pytest

# Import the output formatting module
from src.output_formatting import (
    ProgressTracker,
    OutputFormatter,
    ProgressItem,
    format_progress,
    format_status,
    print_header,
    print_status,
    print_summary,
)


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.output_formatting
class TestProgressTracker:
    """Test ProgressTracker class functionality."""

    def test_progress_tracker_initialization_should_work(self):
        """Test ProgressTracker basic initialization."""
        tracker = ProgressTracker("Test operation", total=100)

        assert tracker.operation == "Test operation"
        assert tracker.total == 100
        assert tracker.current == 0
        assert tracker.show_eta is True
        assert tracker.start_time <= time.time()

    def test_progress_tracker_without_eta_should_work(self):
        """Test ProgressTracker without ETA display."""
        tracker = ProgressTracker("Test operation", total=50, show_eta=False)

        assert tracker.show_eta is False
        assert tracker.total == 50

    @patch("builtins.print")
    def test_progress_update_should_display_correctly(self, mock_print):
        """Test progress update display formatting."""
        tracker = ProgressTracker("Processing", total=100, show_eta=False)
        tracker.update(25, "Current task", force=True)

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]  # First positional argument

        assert "🔄 Processing:" in call_args
        assert "25.0%" in call_args
        assert "(25/100)" in call_args
        assert "Current task" in call_args
        assert "█" in call_args  # Progress bar filled portion
        assert "░" in call_args  # Progress bar empty portion

    @patch("builtins.print")
    def test_progress_update_with_eta_should_include_eta(self, mock_print):
        """Test progress update with ETA calculation."""
        tracker = ProgressTracker("Processing", total=100, show_eta=True)

        # Simulate some time passing
        tracker.start_time = time.time() - 10  # 10 seconds ago
        tracker.update(50, force=True)  # Halfway done

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]

        assert "ETA:" in call_args
        assert ":" in call_args  # Time format mm:ss

    @patch("builtins.print")
    def test_progress_complete_should_show_summary(self, mock_print):
        """Test progress completion display."""
        tracker = ProgressTracker("Processing", total=100)
        tracker.start_time = time.time() - 30  # 30 seconds ago
        tracker.complete("All done")

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]

        assert "✅ Processing: Complete" in call_args
        assert "(100 items in" in call_args
        assert "All done" in call_args

    def test_progress_percentage_calculation_should_be_accurate(self):
        """Test progress percentage calculation accuracy."""
        tracker = ProgressTracker("Test", total=150)

        # Test various percentages
        test_cases = [
            (0, 0.0),
            (75, 50.0),
            (150, 100.0),
        ]

        for current, expected_percent in test_cases:
            with patch("builtins.print") as mock_print:
                tracker.update(current, force=True)
                call_args = mock_print.call_args[0][0]
                assert f"{expected_percent}%" in call_args

    def test_progress_bar_visual_should_be_proportional(self):
        """Test that progress bar visual representation is proportional."""
        tracker = ProgressTracker("Test", total=100)

        with patch("builtins.print") as mock_print:
            tracker.update(25, force=True)  # 25%
            call_args = mock_print.call_args[0][0]

            # Count filled and empty portions
            filled_count = call_args.count("█")
            empty_count = call_args.count("░")

            # Should have roughly 1/4 filled (allowing for rounding)
            total_bar = filled_count + empty_count
            assert total_bar == 30  # Default bar width
            assert 6 <= filled_count <= 9  # ~25% of 30, with rounding tolerance


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.output_formatting
class TestOutputFormatter:
    """Test OutputFormatter class functionality."""

    def test_output_formatter_initialization_should_work(self):
        """Test OutputFormatter basic initialization."""
        formatter = OutputFormatter()
        assert formatter.show_timestamps is False

        formatter_with_timestamps = OutputFormatter(show_timestamps=True)
        assert formatter_with_timestamps.show_timestamps is True

    def test_format_timestamp_should_work_when_enabled(self):
        """Test timestamp formatting when enabled."""
        formatter = OutputFormatter(show_timestamps=True)
        timestamp = formatter.format_timestamp()

        assert timestamp.startswith("[")
        assert timestamp.endswith("] ")
        assert ":" in timestamp  # Time format HH:MM:SS

    def test_format_timestamp_should_be_empty_when_disabled(self):
        """Test timestamp formatting when disabled."""
        formatter = OutputFormatter(show_timestamps=False)
        timestamp = formatter.format_timestamp()

        assert timestamp == ""

    @patch("builtins.print")
    def test_print_header_should_format_correctly(self, mock_print):
        """Test header printing with consistent formatting."""
        formatter = OutputFormatter()
        formatter.print_header("Test Title", "Test Subtitle")

        assert mock_print.call_count == 4  # Header line, title, subtitle, footer line
        calls = [call[0][0] for call in mock_print.call_args_list]

        assert "=" in calls[0]  # Header separator
        assert "Test Title" in calls[1]
        assert "Test Subtitle" in calls[2]

    @patch("builtins.print")
    def test_print_status_should_include_icons(self, mock_print):
        """Test status printing with appropriate icons."""
        formatter = OutputFormatter()

        test_cases = [
            ("info", "\u2139\ufe0f"),
            ("success", "✅"),
            ("warning", "⚠️"),
            ("error", "❌"),
            ("working", "🔄"),
        ]

        for status_type, expected_icon in test_cases:
            formatter.print_status(f"Test {status_type}", status_type)
            call_args = mock_print.call_args[0][0]
            assert expected_icon in call_args
            assert f"Test {status_type}" in call_args

    @patch("builtins.print")
    def test_print_results_empty_should_show_warning(self, mock_print):
        """Test results printing with empty results."""
        formatter = OutputFormatter()
        formatter.print_results("Test Results", [])

        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "⚠️" in call_args
        assert "No results found" in call_args

    @patch("builtins.print")
    def test_print_results_should_format_correctly(self, mock_print):
        """Test results printing with sample data."""
        formatter = OutputFormatter()
        results = [
            {
                "id": "0001",
                "title": "Test Paper 1",
                "authors": ["Smith J", "Doe A"],
                "year": 2023,
                "quality_score": 85,
                "similarity": 0.95,
            },
            {
                "id": "0002",
                "title": "Test Paper 2",
                "authors": ["Johnson B"],
                "year": 2022,
                "similarity": 0.87,
            },
        ]

        formatter.print_results("Search Results", results, show_quality=True)

        # Should have printed header + results
        assert mock_print.call_count > 5

        # Check that key information appears in output
        all_output = " ".join([call[0][0] for call in mock_print.call_args_list])
        assert "Test Paper 1" in all_output
        assert "Test Paper 2" in all_output
        assert "[0001]" in all_output
        assert "[0002]" in all_output
        assert "Smith J, Doe A" in all_output
        assert "Johnson B" in all_output
        assert "Quality: 85/100" in all_output  # Only for first paper

    @patch("builtins.print")
    def test_print_results_with_truncation_should_indicate(self, mock_print):
        """Test results printing with result truncation."""
        formatter = OutputFormatter()
        results = [
            {"id": f"{i:04d}", "title": f"Paper {i}", "authors": ["Author"], "year": 2023}
            for i in range(1, 11)  # 10 results
        ]

        formatter.print_results("Test Results", results, max_results=5)

        all_output = " ".join([call[0][0] for call in mock_print.call_args_list])
        assert "Paper 1" in all_output
        assert "Paper 5" in all_output
        assert "Paper 6" not in all_output  # Should be truncated
        assert "and 5 more results" in all_output

    def test_get_quality_grade_should_return_correct_grades(self):
        """Test quality grade calculation."""
        formatter = OutputFormatter()

        test_cases = [
            (95, "A+"),
            (85, "A+"),
            (75, "A"),
            (70, "A"),
            (65, "B"),
            (60, "B"),
            (50, "C"),
            (45, "C"),
            (35, "D"),
            (30, "D"),
            (20, "F"),
            (0, "F"),
        ]

        for score, expected_grade in test_cases:
            grade = formatter._get_quality_grade(score)
            assert grade == expected_grade, f"Score {score} should be grade {expected_grade}, got {grade}"

    @patch("builtins.print")
    def test_print_summary_should_format_stats(self, mock_print):
        """Test summary printing with various stat types."""
        formatter = OutputFormatter()
        stats = {"total_papers": 1250, "execution_time": 65.5, "success_rate": 0.967, "api_calls": 2500}

        formatter.print_summary(stats)

        all_output = " ".join([call[0][0] for call in mock_print.call_args_list])
        assert "Total Papers: 1,250" in all_output  # Large number formatting
        assert "Execution Time: 1:05" in all_output  # Time formatting
        assert "Success Rate: 0.97" in all_output  # Float formatting
        assert "Api Calls: 2,500" in all_output  # Large number formatting


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.output_formatting
class TestUtilityFunctions:
    """Test standalone utility functions."""

    def test_format_progress_should_create_progress_string(self):
        """Test standalone format_progress function."""
        result = format_progress("Processing", 30, 100, "Current step")

        assert "Processing:" in result
        assert "30.0%" in result
        assert "(30/100)" in result
        assert "Current step" in result
        assert "█" in result
        assert "░" in result

    def test_format_status_should_include_icon(self):
        """Test standalone format_status function."""
        result = format_status("Operation complete", "success")

        assert result == "✅ Operation complete"

    def test_format_status_unknown_type_should_use_default_icon(self):
        """Test format_status with unknown status type."""
        result = format_status("Unknown status", "unknown_type")

        assert result == "• Unknown status"

    @patch("builtins.print")
    def test_global_functions_should_use_global_formatter(self, mock_print):
        """Test that global functions use the global formatter instance."""
        print_header("Test Title")
        print_status("Test message", "info")
        print_summary({"test_stat": 42})

        assert mock_print.call_count >= 3  # All functions should have called print

    def test_global_formatter_consistency_should_match(self):
        """Test that global functions produce consistent results with formatter."""
        # Compare direct formatter use vs global function
        status1 = format_status("Test", "info")

        # Global function should work consistently
        assert "\u2139\ufe0f Test" in status1


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.output_formatting
class TestProgressItem:
    """Test ProgressItem dataclass."""

    def test_progress_item_creation_should_work(self):
        """Test ProgressItem dataclass creation."""
        current_time = time.time()
        item = ProgressItem(
            current=50, total=100, message="Test message", start_time=current_time, last_update=current_time
        )

        assert item.current == 50
        assert item.total == 100
        assert item.message == "Test message"
        assert item.start_time == current_time
        assert item.last_update == current_time


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.output_formatting
class TestOutputConsistency:
    """Test output formatting consistency across functions."""

    def test_all_status_types_should_have_icons(self):
        """Test that all status types have appropriate icons."""
        status_types = ["info", "success", "warning", "error", "working"]

        for status_type in status_types:
            result = format_status("Test message", status_type)

            # Should have an icon (emoji or symbol)
            assert len(result) > len("Test message")
            assert "Test message" in result

    @patch("builtins.print")
    def test_header_formatting_should_be_consistent(self, mock_print):
        """Test that header formatting is consistent."""
        formatter = OutputFormatter()

        # Test various header lengths
        headers = [
            ("Short", ""),
            ("Medium Length Title", "With subtitle"),
            ("Very Long Title That Spans Multiple Words", "And a longer subtitle too"),
        ]

        for title, subtitle in headers:
            mock_print.reset_mock()
            formatter.print_header(title, subtitle)

            calls = [call[0][0] for call in mock_print.call_args_list]

            # First call should be separator line
            assert "=" in calls[0]
            # Should contain the title
            assert title in calls[1]
            if subtitle:
                assert subtitle in calls[2]

    def test_quality_grades_should_cover_full_range(self):
        """Test that quality grades cover the full 0-100 range."""
        formatter = OutputFormatter()

        # Test edge cases and boundaries
        test_scores = [0, 29, 30, 44, 45, 59, 60, 69, 70, 84, 85, 100]

        for score in test_scores:
            grade = formatter._get_quality_grade(score)
            assert grade in ["A+", "A", "B", "C", "D", "F"]

    def test_large_number_formatting_should_be_readable(self):
        """Test that large numbers are formatted for readability."""
        formatter = OutputFormatter()

        with patch("builtins.print") as mock_print:
            stats = {"small_number": 42, "large_number": 1234567, "medium_number": 5432}

            formatter.print_summary(stats)

            all_output = " ".join([call[0][0] for call in mock_print.call_args_list])
            assert "42" in all_output  # Small numbers unchanged
            assert "1,234,567" in all_output  # Large numbers with commas
            assert "5,432" in all_output  # Medium numbers with commas


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.output_formatting
class TestOutputValidation:
    """Test output formatting input validation and edge cases."""

    def test_empty_results_list_should_handle_gracefully(self):
        """Test handling of empty results list."""
        formatter = OutputFormatter()

        with patch("builtins.print") as mock_print:
            formatter.print_results("Empty Results", [])

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "No results found" in call_args

    def test_results_with_missing_fields_should_handle_gracefully(self):
        """Test handling of results with missing fields."""
        formatter = OutputFormatter()
        results = [
            {"id": "0001"},  # Missing most fields
            {"title": "No ID Paper", "authors": []},  # Missing ID and authors
            {},  # Empty result
        ]

        with patch("builtins.print") as mock_print:
            formatter.print_results("Partial Results", results)

            # Should not crash, should handle gracefully
            assert mock_print.call_count > 3  # Header + results
            all_output = " ".join([call[0][0] for call in mock_print.call_args_list])
            assert "Unknown" in all_output  # Default values used

    def test_zero_total_progress_should_handle_gracefully(self):
        """Test progress tracker with zero total."""
        tracker = ProgressTracker("Test", total=0)

        with patch("builtins.print") as mock_print:
            tracker.update(0, force=True)

            mock_print.assert_called_once()
            # Should not crash with division by zero

    def test_negative_progress_values_should_handle_gracefully(self):
        """Test progress tracker with negative values."""
        tracker = ProgressTracker("Test", total=100)

        with patch("builtins.print") as mock_print:
            tracker.update(-10, force=True)

            # Should handle gracefully without crashing
            mock_print.assert_called_once()

    def test_very_large_numbers_should_format_correctly(self):
        """Test formatting of very large numbers."""
        formatter = OutputFormatter()

        with patch("builtins.print") as mock_print:
            stats = {"huge_number": 1234567890123, "float_large": 9876543.21}

            formatter.print_summary(stats)

            all_output = " ".join([call[0][0] for call in mock_print.call_args_list])
            # Should include comma formatting for readability
            assert "1,234,567,890,123" in all_output
