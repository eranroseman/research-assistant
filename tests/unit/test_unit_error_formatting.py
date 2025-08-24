#!/usr/bin/env python3
"""Unit tests for error formatting module.

Tests unified error message formatting system including:
- ErrorFormatter class functionality
- Common error patterns and templates
- Safe exit and error display functions
- Integration with command usage analytics
"""

import pytest
from unittest.mock import patch
from io import StringIO

# Import the error formatting module
from src.error_formatting import (
    ErrorFormatter,
    format_error,
    safe_exit,
    get_common_error,
    exit_with_common_error,
    COMMON_ERRORS,
)


class TestErrorFormatter:
    """Test ErrorFormatter class functionality."""

    def test_format_error_basic_should_work(self):
        """Test basic error formatting with minimal inputs."""
        formatter = ErrorFormatter(module="test")
        result = formatter.format_error("Test error")

        assert "❌ test: Test error" in result
        assert result.count("\n") == 0  # Single line for minimal input

    def test_format_error_with_context_should_include_context(self):
        """Test error formatting with context information."""
        formatter = ErrorFormatter(module="cli", command="search")
        result = formatter.format_error("Knowledge base not found", context="Attempting to load search index")

        assert "❌ cli.search: Knowledge base not found" in result
        assert "Context: Attempting to load search index" in result

    def test_format_error_with_all_fields_should_format_completely(self):
        """Test error formatting with all optional fields."""
        formatter = ErrorFormatter(module="build", command="kb")
        result = formatter.format_error(
            "API timeout",
            context="Enhanced quality scoring",
            suggestion="Retry with --basic-scoring flag",
            technical_details="Semantic Scholar API returned 504",
        )

        assert "❌ build.kb: API timeout" in result
        assert "Context: Enhanced quality scoring" in result
        assert "Solution: Retry with --basic-scoring flag" in result
        assert "Details: Semantic Scholar API returned 504" in result

    def test_error_method_should_exit_with_code(self):
        """Test that error method calls sys.exit with correct code."""
        formatter = ErrorFormatter(module="test")

        with patch("sys.exit") as mock_exit, patch("builtins.print") as mock_print:
            formatter.error("Test error", exit_code=2)

            mock_exit.assert_called_once_with(2)
            mock_print.assert_called_once()

    def test_error_method_should_print_to_stderr(self):
        """Test that error method prints to stderr."""
        formatter = ErrorFormatter(module="test")

        with patch("sys.exit"), patch("sys.stderr", new=StringIO()) as fake_stderr:
            formatter.error("Test error")

            output = fake_stderr.getvalue()
            assert "❌ test: Test error" in output


class TestUtilityFunctions:
    """Test standalone utility functions."""

    def test_format_error_function_should_work(self):
        """Test standalone format_error function."""
        result = format_error("Connection failed", suggestion="Check network connection", module="discover")

        assert "❌ discover: Connection failed" in result
        assert "Solution: Check network connection" in result

    def test_safe_exit_should_format_and_exit(self):
        """Test safe_exit function formatting and exit behavior."""
        with patch("sys.exit") as mock_exit, patch("builtins.print") as mock_print:
            safe_exit("Fatal error", "Restart application", module="cli", exit_code=1)

            mock_exit.assert_called_once_with(1)
            mock_print.assert_called_once()


class TestCommonErrors:
    """Test pre-configured common error patterns."""

    def test_common_errors_dict_should_have_required_keys(self):
        """Test that all common errors have required fields."""
        required_keys = ["error_type", "context", "suggestion", "technical_details"]

        for error_key, error_config in COMMON_ERRORS.items():
            for key in required_keys:
                assert key in error_config, f"Missing {key} in {error_key}"

    def test_get_common_error_should_return_config(self):
        """Test getting common error configuration."""
        config = get_common_error("kb_not_found", module="cli")

        assert config["module"] == "cli"
        assert config["error_type"] == "Knowledge base not found"
        assert "python src/build_kb.py --demo" in config["suggestion"]

    def test_get_common_error_with_override_should_merge(self):
        """Test getting common error with field overrides."""
        config = get_common_error("kb_not_found", module="test", suggestion="Custom solution")

        assert config["module"] == "test"
        assert config["suggestion"] == "Custom solution"
        assert config["error_type"] == "Knowledge base not found"  # Unchanged

    def test_get_common_error_invalid_key_should_raise(self):
        """Test that invalid error key raises ValueError."""
        with pytest.raises(ValueError, match="Unknown error key"):
            get_common_error("nonexistent_error")

    def test_exit_with_common_error_should_work(self):
        """Test exit_with_common_error function."""
        with patch("sys.exit") as mock_exit, patch("builtins.print") as mock_print:
            exit_with_common_error("faiss_import", module="cli")

            mock_exit.assert_called_once_with(1)
            mock_print.assert_called_once()

    def test_exit_with_common_error_custom_exit_code_should_work(self):
        """Test exit_with_common_error with custom exit code."""
        with patch("sys.exit") as mock_exit, patch("builtins.print"):
            exit_with_common_error("kb_not_found", exit_code=2)

            mock_exit.assert_called_once_with(2)


class TestErrorIntegration:
    """Test error formatting integration scenarios."""

    def test_error_formatter_consistency_should_match_patterns(self):
        """Test that different formatters produce consistent patterns."""
        formatter1 = ErrorFormatter(module="cli", command="search")
        formatter2 = ErrorFormatter(module="discover")

        result1 = formatter1.format_error("Test error", context="Test context")
        result2 = formatter2.format_error("Test error", context="Test context")

        # Both should have error icon and consistent structure
        assert result1.startswith("❌ cli.search:")
        assert result2.startswith("❌ discover:")
        assert "Context: Test context" in result1
        assert "Context: Test context" in result2

    def test_error_messages_should_be_actionable(self):
        """Test that common errors provide actionable guidance."""
        actionable_patterns = ["Run", "Install", "Start", "Enable", "Use", "Delete"]

        for error_key, error_config in COMMON_ERRORS.items():
            suggestion = error_config["suggestion"]

            # Check that suggestion contains at least one actionable verb
            has_actionable = any(pattern in suggestion for pattern in actionable_patterns)
            assert has_actionable, f"Error {error_key} suggestion not actionable: {suggestion}"

    def test_module_context_should_be_preserved(self):
        """Test that module context is properly preserved in error messages."""
        modules = ["cli", "build_kb", "discover", "analyze_gaps"]

        for module in modules:
            formatter = ErrorFormatter(module=module)
            result = formatter.format_error("Test error")

            assert f"❌ {module}: Test error" in result

    def test_technical_details_should_be_optional(self):
        """Test that technical details are properly optional."""
        formatter = ErrorFormatter(module="test")

        # Without technical details
        result1 = formatter.format_error("Error", context="Context", suggestion="Solution")
        assert "Details:" not in result1

        # With technical details
        result2 = formatter.format_error(
            "Error", context="Context", suggestion="Solution", technical_details="Technical info"
        )
        assert "Details: Technical info" in result2


class TestErrorValidation:
    """Test error formatting input validation and edge cases."""

    def test_empty_error_type_should_handle_gracefully(self):
        """Test handling of empty error type."""
        formatter = ErrorFormatter(module="test")
        result = formatter.format_error("")

        assert "❌ test: " in result  # Should still format with empty error

    def test_long_error_messages_should_not_break_formatting(self):
        """Test that long error messages maintain formatting."""
        formatter = ErrorFormatter(module="test")
        long_error = "This is a very long error message " * 10
        long_context = "Very long context " * 20

        result = formatter.format_error(long_error, context=long_context)

        # Should still maintain structure
        assert "❌ test:" in result
        assert "Context:" in result
        lines = result.split("\n")
        assert len(lines) >= 2  # At least error and context lines

    def test_special_characters_should_be_handled(self):
        """Test that special characters in error messages are handled properly."""
        formatter = ErrorFormatter(module="test")
        special_chars = "Error with 'quotes' and \"double quotes\" and unicode: ñáéí"

        result = formatter.format_error(special_chars)

        assert special_chars in result
        assert "❌ test:" in result
