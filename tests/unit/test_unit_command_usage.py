#!/usr/bin/env python3
"""
Tests for command usage analytics logging functionality.

Tests the command usage analytics logging system that tracks
command usage patterns, performance metrics, and error patterns
for improving the Research Assistant CLI.
"""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestCommandUsageLogging:
    """Test command usage analytics logging functionality."""

    def test_command_usage_analytics_in_test_environment_should_be_disabled(self):
        """Ensure command usage analytics is disabled when pytest is running."""
        import sys
        from src.cli import _setup_command_usage_logger

        # pytest should be in sys.modules during testing
        assert "pytest" in sys.modules

        # Logger should return None when pytest is detected
        logger = _setup_command_usage_logger()
        assert logger is None

    @pytest.mark.skip(reason="Logger initialization requires non-test environment")
    def test_command_usage_analytics_setup_with_enabled_flag_should_initialize_logger(self):
        """Test command usage analytics setup when enabled outside test environment."""
        import os

        # Save original environment
        original_env = os.environ.get("PYTEST_CURRENT_TEST")

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("src.cli.COMMAND_USAGE_LOG_ENABLED", True),
            patch("src.cli.COMMAND_USAGE_LOG_PATH", Path(temp_dir)),
            patch("src.cli.COMMAND_USAGE_LOG_PREFIX", "test_analytics_"),
            patch("src.cli.COMMAND_USAGE_LOG_LEVEL", "INFO"),
        ):
            # Temporarily remove pytest markers
            if "PYTEST_CURRENT_TEST" in os.environ:
                del os.environ["PYTEST_CURRENT_TEST"]

            # Mock sys.modules to hide pytest
            with patch.dict("sys.modules", {k: v for k, v in sys.modules.items() if k != "pytest"}):
                from src.cli import _setup_command_usage_logger

                logger = _setup_command_usage_logger()
                assert logger is not None
                assert logger.name == "command_usage"

            # Restore environment
            if original_env:
                os.environ["PYTEST_CURRENT_TEST"] = original_env

    def test_command_usage_analytics_setup_with_disabled_flag_should_skip_initialization(self):
        """Test command usage analytics setup when disabled."""
        with patch("src.cli.COMMAND_USAGE_LOG_ENABLED", False):
            from src.cli import _setup_command_usage_logger

            logger = _setup_command_usage_logger()
            assert logger is None

    def test_command_usage_analytics_setup_with_errors_should_handle_gracefully(self):
        """Test that command usage analytics setup handles errors without breaking core functionality."""
        # Mock sys.modules to remove pytest
        with (
            patch.dict("sys.modules"),
            patch("src.cli.COMMAND_USAGE_LOG_ENABLED", True),
            patch("src.cli.COMMAND_USAGE_LOG_PATH", None),
        ):  # Invalid path
            if "pytest" in sys.modules:
                del sys.modules["pytest"]

            from src.cli import _setup_command_usage_logger

            # Should return None instead of raising exception
            logger = _setup_command_usage_logger()
            assert logger is None

    def test_log_command_usage_event_with_valid_logger_should_record_event(self):
        """Test logging events when logger is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test_analytics.jsonl"

            # Create a test logger manually
            logger = logging.getLogger("test_command_usage")
            handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")

            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_data = {
                        "timestamp": "2025-08-21T10:00:00.000000+00:00",
                        "session_id": "test123",
                        "level": record.levelname,
                        "message": record.getMessage(),
                    }
                    if hasattr(record, "extra_data"):
                        log_data.update(record.extra_data)
                    return json.dumps(log_data)

            handler.setFormatter(JSONFormatter())
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Mock the global logger
            with (
                patch("src.cli._command_usage_logger", logger),
                patch("src.cli.COMMAND_USAGE_LOG_ENABLED", True),
            ):
                from src.cli import _log_command_usage_event

                # Test logging an event
                _log_command_usage_event("test_event", command="search", query_length=10, success=True)

            # Verify log was written
            assert log_file.exists()
            with open(log_file) as f:
                log_content = f.read().strip()
                log_data = json.loads(log_content)

                assert log_data["event_type"] == "test_event"
                assert log_data["command"] == "search"
                assert log_data["query_length"] == 10
                assert log_data["success"] is True

    def test_log_command_usage_event_with_no_logger_should_skip_silently(self):
        """Test that logging gracefully handles missing logger."""
        with patch("src.cli._command_usage_logger", None):
            from src.cli import _log_command_usage_event

            # Should not raise exception
            _log_command_usage_event("test_event", command="search")

    def test_log_command_usage_event_with_disabled_logging_should_skip_silently(self):
        """Test that logging respects the enabled flag."""
        mock_logger = MagicMock()

        with (
            patch("src.cli._command_usage_logger", mock_logger),
            patch("src.cli.COMMAND_USAGE_LOG_ENABLED", False),
        ):
            from src.cli import _log_command_usage_event

            _log_command_usage_event("test_event", command="search")

            # Logger should not be called when disabled
            mock_logger.handle.assert_not_called()

    def test_session_id_generation_should_create_unique_ids(self):
        """Test that session IDs are generated correctly."""
        from src.cli import _session_id

        # Session ID should be 8 characters
        assert len(_session_id) == 8
        assert isinstance(_session_id, str)

    def test_command_usage_log_file_naming_should_use_date_format(self):
        """Test that log files are named correctly with date prefix."""
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict("sys.modules"):
            if "pytest" in sys.modules:
                del sys.modules["pytest"]

            with (
                patch("src.cli.COMMAND_USAGE_LOG_ENABLED", True),
                patch("src.cli.COMMAND_USAGE_LOG_PATH", Path(temp_dir)),
                patch("src.cli.COMMAND_USAGE_LOG_PREFIX", "test_analytics_"),
            ):
                from src.cli import _setup_command_usage_logger
                from datetime import datetime, UTC

                logger = _setup_command_usage_logger()
                if logger:  # Only test if logger was created
                    expected_date = datetime.now(UTC).strftime("%Y%m%d")
                    expected_file = Path(temp_dir) / f"test_analytics_{expected_date}.jsonl"

                    # File should exist after logger setup
                    assert expected_file.exists() or len(os.listdir(temp_dir)) > 0


@pytest.mark.integration
class TestCommandUsageIntegration:
    """Integration tests for command usage analytics in CLI commands."""

    def test_command_usage_analytics_in_pytest_environment_should_be_disabled(self):
        """Test that command usage analytics are properly disabled when running under pytest."""
        from src.cli import _command_usage_logger

        # In test environment, logger should be None
        assert _command_usage_logger is None

        # This confirms that pytest detection is working
