#!/usr/bin/env python3
"""
Integration tests for the updated prompt system in build_kb.py.

Tests that the refactored prompt functions work correctly with the new safe_prompt system.
"""

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.build_kb import (
    ask_user_for_fallback_approval,
    confirm_long_operation,
    prompt_gap_analysis_after_build,
)


class TestPromptIntegration:
    """Test integration of new prompt system with existing functions."""

    def test_ask_user_for_fallback_approval_high_failure_rate(self, capsys):
        """Test fallback approval with high failure rate defaults to basic scoring."""
        with patch("src.build_kb.safe_prompt", return_value="y") as mock_prompt:
            result = ask_user_for_fallback_approval(failed_count=800, total_count=1000)

            assert result is True  # Should return True for basic scoring

            # Check that safe_prompt was called with correct parameters
            mock_prompt.assert_called_once()
            call_args = mock_prompt.call_args

            # Verify the action and context for high failure rate
            assert call_args[1]["action"] == "Use basic scoring"
            assert "80%" in call_args[1]["context"]  # 800/1000 = 80%
            assert "API unstable" in call_args[1]["context"]
            assert call_args[1]["default"] == "Y"  # High failure rate defaults to basic scoring
            assert call_args[1]["reversible"] is True
            assert "API Scoring Failure Details" in call_args[1]["help_text"]

    def test_ask_user_for_fallback_approval_low_failure_rate(self):
        """Test fallback approval with low failure rate defaults to retry."""
        with patch("src.build_kb.safe_prompt", return_value="y") as mock_prompt:
            result = ask_user_for_fallback_approval(failed_count=100, total_count=1000)

            assert result is True  # Returns True even for low failure when user says "y" (use basic)

            call_args = mock_prompt.call_args
            assert "10%" in call_args[1]["context"]  # 100/1000 = 10%
            assert call_args[1]["default"] == "N"  # Low failure rate defaults to retry (N = don't use basic)

    def test_ask_user_for_fallback_approval_low_failure_user_chooses_retry(self):
        """Test low failure rate when user chooses to retry (default behavior)."""
        with patch("src.build_kb.safe_prompt", return_value="n") as mock_prompt:
            result = ask_user_for_fallback_approval(failed_count=100, total_count=1000)

            assert result is False  # Should return False for retry

            call_args = mock_prompt.call_args
            assert "10%" in call_args[1]["context"]
            assert "or retry enhanced?" in call_args[1]["context"]

    def test_ask_user_for_fallback_approval_user_says_no_high_failure(self):
        """Test fallback approval when user says no to basic scoring (high failure rate)."""
        with patch("src.build_kb.safe_prompt", return_value="n"):
            result = ask_user_for_fallback_approval(failed_count=800, total_count=1000)

            assert result is False  # Should return False for retry even with high failure rate

    def test_confirm_long_operation_under_threshold(self):
        """Test long operation confirmation doesn't prompt for short operations."""
        # Import the threshold
        from src.build_kb import LONG_OPERATION_THRESHOLD

        short_time = LONG_OPERATION_THRESHOLD - 10  # Under threshold

        result = confirm_long_operation(short_time, "Test operation")

        assert result is True  # Should return True without prompting

    def test_confirm_long_operation_over_threshold_user_continues(self):
        """Test long operation confirmation prompts and user continues."""
        from src.build_kb import LONG_OPERATION_THRESHOLD

        long_time = LONG_OPERATION_THRESHOLD + 100  # Over threshold

        with patch("src.build_kb.safe_prompt", return_value="y") as mock_prompt:
            result = confirm_long_operation(long_time, "Long operation")

            assert result is True

            # Verify safe_prompt was called correctly
            mock_prompt.assert_called_once()
            call_args = mock_prompt.call_args

            assert call_args[1]["action"] == "Continue"
            assert "long operation" in call_args[1]["context"]
            assert call_args[1]["reversible"] is False  # Can't undo time spent
            assert "Long Operation Details" in call_args[1]["help_text"]

    def test_confirm_long_operation_over_threshold_user_aborts(self, capsys):
        """Test long operation confirmation when user chooses to abort."""
        from src.build_kb import LONG_OPERATION_THRESHOLD

        long_time = LONG_OPERATION_THRESHOLD + 100

        with patch("src.build_kb.safe_prompt", return_value="n"):
            result = confirm_long_operation(long_time, "Long operation")

            assert result is False

            # Check that abort message was printed
            captured = capsys.readouterr()
            assert "Aborted by user" in captured.out

    def test_confirm_long_operation_time_formatting(self):
        """Test that time estimates are formatted correctly."""
        with patch("src.build_kb.safe_prompt", return_value="y") as mock_prompt:
            # Test seconds
            confirm_long_operation(3900, "Operation")  # Just over threshold, in seconds
            call_args = mock_prompt.call_args
            # Should be formatted as seconds or minutes depending on LONG_OPERATION_THRESHOLD

            # Test minutes
            confirm_long_operation(7200, "Operation")  # 2 hours in seconds
            call_args = mock_prompt.call_args
            assert "2.0h" in call_args[1]["time_estimate"]

    def test_prompt_gap_analysis_insufficient_conditions(self, capsys):
        """Test gap analysis prompt when conditions not met."""
        with patch("src.build_kb.has_enhanced_scoring", return_value=False):
            prompt_gap_analysis_after_build(total_papers=100, build_time=5.5)

            captured = capsys.readouterr()
            assert "Knowledge base built successfully!" in captured.out
            assert "100 papers indexed in 5.5 minutes" in captured.out
            assert "Gap analysis requires enhanced quality scoring" in captured.out

    def test_prompt_gap_analysis_insufficient_papers(self, capsys):
        """Test gap analysis prompt with too few papers."""
        with patch("src.build_kb.has_enhanced_scoring", return_value=True):
            prompt_gap_analysis_after_build(total_papers=10, build_time=2.0)  # < 20 papers

            captured = capsys.readouterr()
            assert "Gap analysis requires enhanced quality scoring and ≥20 papers" in captured.out

    def test_prompt_gap_analysis_valid_conditions_user_accepts(self, capsys):
        """Test gap analysis prompt with valid conditions and user accepts."""
        with (
            patch("src.build_kb.has_enhanced_scoring", return_value=True),
            patch("src.build_kb.safe_prompt", return_value="y") as mock_prompt,
            patch("subprocess.run") as mock_subprocess,
        ):
            prompt_gap_analysis_after_build(total_papers=100, build_time=8.2)

            # Verify safe_prompt was called correctly
            mock_prompt.assert_called_once()
            call_args = mock_prompt.call_args

            assert call_args[1]["action"] == "Run gap analysis"
            assert "100 papers analyzed" in call_args[1]["context"]
            assert "2-3min" in call_args[1]["time_estimate"]
            assert call_args[1]["reversible"] is True
            assert "Gap Analysis Details" in call_args[1]["help_text"]

            # Verify subprocess was called to run gap analysis
            mock_subprocess.assert_called_once_with(["python", "src/analyze_gaps.py"], check=False)

    def test_prompt_gap_analysis_valid_conditions_user_declines(self, capsys):
        """Test gap analysis prompt with valid conditions and user declines."""
        with (
            patch("src.build_kb.has_enhanced_scoring", return_value=True),
            patch("src.build_kb.safe_prompt", return_value="n"),
            patch("subprocess.run") as mock_subprocess,
        ):
            prompt_gap_analysis_after_build(total_papers=50, build_time=3.1)

            # Verify subprocess was NOT called
            mock_subprocess.assert_not_called()


class TestPromptSystemRobustness:
    """Test robustness and edge cases of the prompt system integration."""

    def test_fallback_approval_extreme_failure_rates(self):
        """Test fallback approval with extreme failure rates."""
        # 100% failure rate - should default to basic scoring (Y)
        with patch("src.build_kb.safe_prompt", return_value="y"):
            result = ask_user_for_fallback_approval(1000, 1000)
            assert result is True

        # 0% failure rate - should default to retry (N), but user says yes to basic
        with patch("src.build_kb.safe_prompt", return_value="y"):
            result = ask_user_for_fallback_approval(0, 1000)
            assert result is True  # User overrides default and chooses basic scoring

    def test_time_formatting_edge_cases(self):
        """Test time formatting for various durations."""
        test_cases = [
            (320, "5min"),  # 320 seconds = 5.33min -> rounds to 5min
            (420, "7min"),  # 420 seconds = 7.0min -> shows as 7min
            (3900, "1.1h"),  # 3900 seconds = 1.083h -> shows as 1.1h
            (7560, "2.1h"),  # 7560 seconds = 2.1h -> shows as 2.1h
        ]

        for seconds, expected_format in test_cases:
            with patch("src.build_kb.safe_prompt", return_value="y") as mock_prompt:
                confirm_long_operation(seconds, "Test")  # Test with actual duration
                call_args = mock_prompt.call_args
                assert expected_format in call_args[1]["time_estimate"]

    def test_help_text_content_quality(self):
        """Test that help text contains useful information."""
        with patch("src.build_kb.safe_prompt", return_value="y") as mock_prompt:
            ask_user_for_fallback_approval(failed_count=600, total_count=1000)

            call_args = mock_prompt.call_args
            help_text = call_args[1]["help_text"]

            # Check that help contains key information for new simplified format
            assert "What happened:" in help_text
            assert "Your options:" in help_text
            assert "Current situation:" in help_text
            assert "600" in help_text  # Failed count
            assert "1,000" in help_text  # Total count (with comma formatting)
            assert "60%" in help_text  # Failure rate
            assert "Use basic scoring" in help_text  # Option 1
            assert "Retry enhanced scoring" in help_text  # Option 2

    def test_gap_analysis_help_text_quality(self):
        """Test that gap analysis help text is comprehensive."""
        with (
            patch("src.build_kb.has_enhanced_scoring", return_value=True),
            patch("src.build_kb.safe_prompt", return_value="n") as mock_prompt,
        ):
            prompt_gap_analysis_after_build(total_papers=250, build_time=12.5)

            call_args = mock_prompt.call_args
            help_text = call_args[1]["help_text"]

            # Check comprehensive help content
            assert "What it does:" in help_text
            assert "5 types of literature gaps identified:" in help_text
            assert "Time estimate:" in help_text
            assert "Output:" in help_text
            assert "Value:" in help_text
            assert "250" in help_text  # Paper count should be included
