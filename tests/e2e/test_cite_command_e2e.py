#!/usr/bin/env python3
"""Tests for the cite command functionality."""

import json
import subprocess
from pathlib import Path

import pytest


class TestCiteCommand:
    """Test suite for cli.py cite command."""

    def test_cite_command_exists(self):
        """Test that cite command is available in CLI."""
        result = subprocess.run(
            ["python", "src/cli.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert "cite" in result.stdout
        assert "IEEE" in result.stdout or "citations" in result.stdout.lower()

    def test_cite_help(self):
        """Test cite command help output."""
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "PAPER_IDS" in result.stdout
        assert "--format" in result.stdout
        assert "text|json" in result.stdout
        assert "0001" in result.stdout  # Example paper ID
        assert "IEEE" in result.stdout

    def test_cite_no_arguments_error(self):
        """Test that cite command requires paper IDs."""
        result = subprocess.run(
            ["python", "src/cli.py", "cite"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "PAPER_IDS" in result.stderr or "required" in result.stderr.lower()

    def test_cite_single_paper_integration(self):
        """Test citing a single paper with actual KB if available."""
        # First check if KB exists
        kb_path = Path("kb_data")
        if not kb_path.exists():
            pytest.skip("Knowledge base not found, skipping integration test")

        # Try to cite paper 0001 (usually exists in most KBs)
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "0001"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Check if paper exists
        if "not found" not in result.stderr.lower() and "not found" not in result.stdout.lower():
            assert result.returncode == 0
            assert "IEEE Citations" in result.stdout or "[1]" in result.stdout
            # Should have some citation content
            assert len(result.stdout.strip()) > 50

    def test_cite_multiple_papers_integration(self):
        """Test citing multiple papers with actual KB if available."""
        kb_path = Path("kb_data")
        if not kb_path.exists():
            pytest.skip("Knowledge base not found, skipping integration test")

        # Try to cite multiple papers
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "0001", "0002"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Check basic output structure
        if result.returncode == 0:
            output = result.stdout
            # Should have multiple citations
            assert "[1]" in output or "IEEE Citations" in output
            # If both papers exist, should have [2] as well
            if "not found" not in result.stderr:
                lines = output.strip().split("\n")
                # Should have multiple non-empty lines
                assert len([line for line in lines if line.strip()]) > 2

    def test_cite_json_format(self):
        """Test JSON output format."""
        kb_path = Path("kb_data")
        if not kb_path.exists():
            pytest.skip("Knowledge base not found, skipping integration test")

        # Try with JSON format
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "0001", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        if result.returncode == 0:
            try:
                # Strip any loading messages before JSON
                output = result.stdout
                json_start = output.find("{")
                if json_start != -1:
                    json_str = output[json_start:]
                else:
                    json_str = output

                json_output = json.loads(json_str)
                assert "citations" in json_output
                assert "errors" in json_output
                assert "count" in json_output
                assert isinstance(json_output["count"], int)
                assert isinstance(json_output["citations"], list)
                assert isinstance(json_output["errors"], list)

                # If paper was found
                if json_output["count"] > 0:
                    citation = json_output["citations"][0]
                    assert "id" in citation
                    assert "citation" in citation
                    assert "number" in citation
            except json.JSONDecodeError:
                pytest.fail(f"Output is not valid JSON: {result.stdout}")

    def test_cite_invalid_paper_id(self):
        """Test handling of invalid paper IDs."""
        kb_path = Path("kb_data")
        if not kb_path.exists():
            pytest.skip("Knowledge base not found, skipping integration test")

        # Use a very high ID that likely doesn't exist
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "9999"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should handle gracefully
        assert result.returncode == 0  # Command completes but reports error
        # Error should be reported
        assert "9999" in result.stderr or "9999" in result.stdout
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_cite_mixed_valid_invalid_json(self):
        """Test citing mix of valid and invalid paper IDs with JSON output."""
        kb_path = Path("kb_data")
        if not kb_path.exists():
            pytest.skip("Knowledge base not found, skipping integration test")

        # Mix valid (0001) and invalid (9999) IDs
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "0001", "9999", "--format", "json"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        if result.returncode == 0:
            try:
                # Strip any loading messages before JSON
                output = result.stdout
                json_start = output.find("{")
                if json_start != -1:
                    json_str = output[json_start:]
                else:
                    json_str = output

                json_output = json.loads(json_str)
                # Should have structure even with errors
                assert "citations" in json_output
                assert "errors" in json_output
                assert "count" in json_output

                # Should have at least one error for 9999
                if len(json_output["errors"]) > 0:
                    error_text = " ".join(json_output["errors"])
                    assert "9999" in error_text
            except json.JSONDecodeError:
                # If KB doesn't exist properly, skip
                if "not found" in result.stderr.lower():
                    pytest.skip("KB not properly initialized")
                else:
                    pytest.fail(f"Output is not valid JSON: {result.stdout}")

    def test_cite_id_normalization(self):
        """Test that paper IDs are normalized to 4 digits."""
        kb_path = Path("kb_data")
        if not kb_path.exists():
            pytest.skip("Knowledge base not found, skipping integration test")

        # Test with non-padded ID
        result1 = subprocess.run(
            ["python", "src/cli.py", "cite", "1"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Test with padded ID
        result2 = subprocess.run(
            ["python", "src/cli.py", "cite", "0001"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Both should produce same result (whether found or not found)
        if "not found" in result1.stderr and "not found" in result2.stderr:
            # Both not found - check they reference same ID
            assert "0001" in result1.stderr or "0001" in result1.stdout
            assert "0001" in result2.stderr or "0001" in result2.stdout
        elif result1.returncode == 0 and result2.returncode == 0:
            # Both found - outputs should be similar
            # Remove variable parts like timestamps
            output1 = result1.stdout.replace("=", "").strip()
            output2 = result2.stdout.replace("=", "").strip()
            # Should have same citation content
            if "[1]" in output1 and "[1]" in output2:
                # Extract citation line
                cite1 = [line for line in output1.split("\n") if "[1]" in line]
                cite2 = [line for line in output2.split("\n") if "[1]" in line]
                if cite1 and cite2:
                    assert cite1[0] == cite2[0]

    def test_cite_format_option_validation(self):
        """Test that format option only accepts valid values."""
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "0001", "--format", "invalid"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should reject invalid format
        assert result.returncode != 0
        assert "invalid" in result.stderr.lower() or "choice" in result.stderr.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
