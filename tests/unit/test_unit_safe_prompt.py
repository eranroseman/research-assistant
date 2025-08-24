#!/usr/bin/env python3
"""
Unit tests for the new safe_prompt system.

Tests the unified prompt interface with inline context, safety warnings,
help on demand, and smart defaults.
"""

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.build_kb import safe_prompt


class TestSafePromptBasicFunctionality:
    """Test basic safe_prompt functionality."""

    def test_basic_prompt_with_default_yes(self):
        """Test basic prompt accepts default Y on empty input."""
        with patch("builtins.input", return_value=""):
            result = safe_prompt("Test action")
            assert result == "y"

    def test_basic_prompt_with_explicit_yes(self):
        """Test basic prompt accepts explicit 'y' input."""
        with patch("builtins.input", return_value="y"):
            result = safe_prompt("Test action")
            assert result == "y"

    def test_basic_prompt_with_explicit_no(self):
        """Test basic prompt accepts explicit 'n' input."""
        with patch("builtins.input", return_value="n"):
            result = safe_prompt("Test action")
            assert result == "n"

    def test_basic_prompt_with_yes_word(self):
        """Test basic prompt accepts 'yes' as input."""
        with patch("builtins.input", return_value="yes"):
            result = safe_prompt("Test action")
            assert result == "yes"

    def test_basic_prompt_with_no_word(self):
        """Test basic prompt accepts 'no' as input."""
        with patch("builtins.input", return_value="no"):
            result = safe_prompt("Test action")
            assert result == "no"

    def test_default_no_with_empty_input(self):
        """Test prompt with default N returns 'n' on empty input."""
        with patch("builtins.input", return_value=""):
            result = safe_prompt("Test action", default="N")
            assert result == "n"


class TestSafePromptFormatting:
    """Test prompt formatting and display."""

    def test_action_only_prompt_format(self):
        """Test prompt with only action displays correctly."""
        with patch("builtins.input", return_value="y") as mock_input:
            safe_prompt("Test action")
            mock_input.assert_called_with("Test action (reversible)? [Y/n/?]: ")

    def test_action_with_context_prompt_format(self):
        """Test prompt with action and context displays correctly."""
        with patch("builtins.input", return_value="y") as mock_input:
            safe_prompt("Test action", context="100 items")
            mock_input.assert_called_with("Test action (100 items) (reversible)? [Y/n/?]: ")

    def test_action_with_time_estimate_prompt_format(self):
        """Test prompt with time estimate displays correctly."""
        with patch("builtins.input", return_value="y") as mock_input:
            safe_prompt("Test action", time_estimate="5min")
            mock_input.assert_called_with("Test action ~5min (reversible)? [Y/n/?]: ")

    def test_full_context_prompt_format(self):
        """Test prompt with all context displays correctly."""
        with patch("builtins.input", return_value="y") as mock_input:
            safe_prompt("Test action", context="100 items", time_estimate="5min")
            mock_input.assert_called_with("Test action (100 items) ~5min (reversible)? [Y/n/?]: ")

    def test_destructive_operation_prompt_format(self):
        """Test destructive operation displays warning correctly."""
        with patch("builtins.input", return_value="y") as mock_input:
            safe_prompt("Delete data", consequence="PERMANENT data loss", default="N")
            mock_input.assert_called_with("Delete data ⚠️ PERMANENT data loss? [N/y/?]: ")

    def test_non_reversible_without_consequence_no_reversible_tag(self):
        """Test non-reversible operation without consequence doesn't show (reversible)."""
        with patch("builtins.input", return_value="y") as mock_input:
            safe_prompt("Backup data", reversible=False)
            mock_input.assert_called_with("Backup data? [Y/n/?]: ")


class TestSafePromptHelpSystem:
    """Test help on demand functionality."""

    def test_help_request_shows_help_then_prompts_again(self):
        """Test that '?' input shows help and re-prompts."""
        inputs = ["?", "y"]  # First ?, then y
        with patch("builtins.input", side_effect=inputs) as mock_input, patch("builtins.print") as mock_print:
            result = safe_prompt("Test action", help_text="This is test help")
            assert result == "y"

            # Check that help was printed
            help_printed = any("This is test help" in str(call) for call in mock_print.call_args_list)
            assert help_printed, "Help text should be printed when ? is entered"

            # Should be called twice (? then y)
            assert mock_input.call_count == 2

    def test_help_request_with_no_help_text(self):
        """Test help request when no help text provided."""
        inputs = ["?", "y"]
        with patch("builtins.input", side_effect=inputs), patch("builtins.print") as mock_print:
            result = safe_prompt("Test action")  # No help_text
            assert result == "y"

            # Check that "no help available" message was shown
            no_help_printed = any(
                "No detailed help available" in str(call) for call in mock_print.call_args_list
            )
            assert no_help_printed


class TestSafePromptErrorHandling:
    """Test error handling and invalid input."""

    def test_invalid_input_re_prompts(self):
        """Test that invalid input causes re-prompting."""
        inputs = ["invalid", "y"]  # Invalid input, then valid
        with (
            patch("builtins.input", side_effect=inputs) as mock_input,
            patch("builtins.print"),
        ):  # Suppress error message
            result = safe_prompt("Test action")
            assert result == "y"
            assert mock_input.call_count == 2

    def test_multiple_invalid_inputs_keep_prompting(self):
        """Test that multiple invalid inputs keep re-prompting."""
        inputs = ["bad", "also_bad", "still_bad", "y"]  # Multiple invalid, then valid
        with (
            patch("builtins.input", side_effect=inputs) as mock_input,
            patch("builtins.print"),
        ):  # Suppress error messages
            result = safe_prompt("Test action")
            assert result == "y"
            assert mock_input.call_count == 4


class TestSafePromptRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_quality_upgrade_scenario(self):
        """Test typical quality upgrade prompt scenario."""
        with patch("builtins.input", return_value="y") as mock_input:
            result = safe_prompt(
                action="Upgrade scores",
                context="245 papers",
                time_estimate="3min",
                reversible=True,
                help_text="Upgrades basic to enhanced scoring...",
            )
            assert result == "y"
            # Check prompt format matches expected
            expected_prompt = "Upgrade scores (245 papers) ~3min (reversible)? [Y/n/?]: "
            mock_input.assert_called_with(expected_prompt)

    def test_destructive_import_scenario(self):
        """Test destructive import operation scenario."""
        with patch("builtins.input", return_value="n") as mock_input:
            result = safe_prompt(
                action="Import KB",
                context="overwrites 1,200 papers, 305MB",
                consequence="PERMANENT data loss",
                default="N",
                reversible=False,
                help_text="This will permanently delete your existing KB...",
            )
            assert result == "n"
            expected_prompt = "Import KB (overwrites 1,200 papers, 305MB) ⚠️ PERMANENT data loss? [N/y/?]: "
            mock_input.assert_called_with(expected_prompt)

    def test_api_failure_scenario(self):
        """Test binary choice scenario (not the 3-option API failure which uses different function)."""
        with patch("builtins.input", return_value="") as mock_input:  # Empty = default
            result = safe_prompt(
                action="Continue with basic scoring",
                context="API unavailable, upgradeable later",
                reversible=True,
                help_text="Basic scoring details...",
            )
            assert result == "y"  # Default is Y
            expected_prompt = (
                "Continue with basic scoring (API unavailable, upgradeable later) (reversible)? [Y/n/?]: "
            )
            mock_input.assert_called_with(expected_prompt)

    def test_gap_analysis_scenario(self):
        """Test gap analysis invitation scenario."""
        with patch("builtins.input", return_value="y") as mock_input:
            result = safe_prompt(
                action="Run gap analysis",
                context="discovers ~25% more papers, 1,500 papers analyzed",
                time_estimate="2-3min",
                reversible=True,
                help_text="Gap analysis discovers missing papers...",
            )
            assert result == "y"
            expected_prompt = "Run gap analysis (discovers ~25% more papers, 1,500 papers analyzed) ~2-3min (reversible)? [Y/n/?]: "
            mock_input.assert_called_with(expected_prompt)


class TestSafePromptEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_action_string(self):
        """Test behavior with empty action string."""
        with patch("builtins.input", return_value="y") as mock_input:
            result = safe_prompt("")
            assert result == "y"
            mock_input.assert_called_with(" (reversible)? [Y/n/?]: ")

    def test_very_long_context_string(self):
        """Test behavior with very long context."""
        long_context = "very " * 100 + "long context"
        with patch("builtins.input", return_value="y") as mock_input:
            result = safe_prompt("Test", context=long_context)
            assert result == "y"
            # Should still format correctly
            expected_prompt = f"Test ({long_context}) (reversible)? [Y/n/?]: "
            mock_input.assert_called_with(expected_prompt)

    def test_case_insensitive_input(self):
        """Test that input is handled case-insensitively."""
        test_cases = ["Y", "y", "YES", "yes", "N", "n", "NO", "no"]
        for test_input in test_cases:
            with patch("builtins.input", return_value=test_input):
                result = safe_prompt("Test action")
                assert result == test_input.lower()

    def test_whitespace_handling(self):
        """Test that whitespace in input is stripped."""
        inputs_with_whitespace = ["  y  ", "\\t\\ny\\t\\n", "   n   "]
        expected = ["y", "y", "n"]

        for test_input, expected_result in zip(inputs_with_whitespace, expected, strict=False):
            with patch("builtins.input", return_value=test_input):
                result = safe_prompt("Test action")
                assert result == expected_result
