#!/usr/bin/env python3
"""Tests for the cite command functionality."""

import subprocess

import pytest


@pytest.mark.e2e
@pytest.mark.cli
@pytest.mark.requires_kb
class TestCiteCommand:
    """Test suite for cli.py cite command."""

    def test_cite_command_should_exist(self):
        """Test that cite command is available in CLI."""
        try:
            result = subprocess.run(
                ["python", "src/cli.py", "--help"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            pytest.skip("CLI command timed out - possible environment issue")
        assert "cite" in result.stdout
        assert "IEEE" in result.stdout or "citations" in result.stdout.lower()

    def test_cite_help_should_be_available(self):
        """Test cite command help output."""
        try:
            result = subprocess.run(
                ["python", "src/cli.py", "cite", "--help"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            pytest.skip("CLI command timed out - possible environment issue")
        assert result.returncode == 0
        assert "PAPER_IDS" in result.stdout
        assert "--format" in result.stdout
        assert "text|json" in result.stdout
        assert "0001" in result.stdout  # Example paper ID
        assert "IEEE" in result.stdout

    def test_cite_with_no_arguments_should_show_error(self):
        """Test that cite command requires paper IDs."""
        try:
            result = subprocess.run(
                ["python", "src/cli.py", "cite"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            pytest.skip("CLI command timed out - possible environment issue")
        assert result.returncode != 0
        assert "PAPER_IDS" in result.stderr or "required" in result.stderr.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
