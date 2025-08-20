#!/usr/bin/env python3
"""Tests for the batch command functionality."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBatchCommand:
    """Test suite for cli.py batch command."""

    def test_batch_command_exists(self):
        """Test that batch command is available in CLI."""
        result = subprocess.run(
            ["python", "src/cli.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert "batch" in result.stdout
        assert "Execute" in result.stdout or "efficient" in result.stdout

    def test_batch_help(self):
        """Test batch command help output."""
        result = subprocess.run(
            ["python", "src/cli.py", "batch", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "preset" in result.stdout
        assert "research" in result.stdout
        assert "review" in result.stdout
        assert "author-scan" in result.stdout

    def test_batch_preset_research(self):
        """Test research preset generates correct commands."""
        from src.cli import _generate_preset_commands

        commands = _generate_preset_commands("research", "diabetes")

        # Should have multiple searches
        search_commands = [c for c in commands if c.get("cmd") == "search"]
        assert len(search_commands) >= 3

        # Should have merge command
        assert any(c.get("cmd") == "merge" for c in commands)

        # Should have filter command
        assert any(c.get("cmd") == "filter" for c in commands)

        # Should have auto-get-top command
        assert any(c.get("cmd") == "auto-get-top" for c in commands)

        # Check search queries include the topic
        for search_cmd in search_commands:
            assert "diabetes" in search_cmd.get("query", "").lower()

    def test_batch_preset_review(self):
        """Test review preset generates correct commands."""
        from src.cli import _generate_preset_commands

        commands = _generate_preset_commands("review", "hypertension")

        # Should focus on systematic reviews and meta-analyses
        search_commands = [c for c in commands if c.get("cmd") == "search"]
        for cmd in search_commands:
            query = cmd.get("query", "").lower()
            assert "systematic review" in query or "meta-analysis" in query

        # Should have quality filter
        filter_cmd = next(c for c in commands if c.get("cmd") == "filter")
        assert filter_cmd.get("min_quality", 0) >= 80

    def test_batch_preset_author_scan(self):
        """Test author-scan preset generates correct commands."""
        from src.cli import _generate_preset_commands

        commands = _generate_preset_commands("author-scan", "Smith J")

        # Should have author search
        assert any(c.get("cmd") == "author" and c.get("name") == "Smith J" for c in commands)

        # Should have auto-get-all
        assert any(c.get("cmd") == "auto-get-all" for c in commands)

    def test_batch_invalid_preset(self):
        """Test that invalid preset raises error."""
        from src.cli import _generate_preset_commands

        with pytest.raises(ValueError, match="Unknown preset"):
            _generate_preset_commands("invalid_preset", "test")

    @patch("src.cli.ResearchCLI")
    def test_batch_execute_search(self, mock_cli_class):
        """Test batch execution of search commands."""
        from src.cli import _execute_batch

        # Setup mock
        mock_cli = MagicMock()
        mock_cli.search.return_value = [
            (0, 0.95, {"id": "0001", "title": "Test Paper 1", "quality_score": 85}),
            (1, 0.90, {"id": "0002", "title": "Test Paper 2", "quality_score": 75}),
        ]
        mock_cli.metadata = {"papers": []}

        # Execute batch
        commands = [{"cmd": "search", "query": "test", "k": 2, "show_quality": True}]
        results = _execute_batch(mock_cli, commands)

        # Verify results
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["type"] == "search"
        assert results[0]["count"] == 2
        assert len(results[0]["data"]) == 2
        assert results[0]["data"][0]["id"] == "0001"
        assert results[0]["data"][0]["study_type"] == "UNKNOWN"  # Because show_quality=True

    @patch("src.cli.ResearchCLI")
    def test_batch_meta_command_merge(self, mock_cli_class):
        """Test merge meta-command."""
        from src.cli import _execute_batch

        # Setup mock
        mock_cli = MagicMock()
        mock_cli.search.return_value = [
            (0, 0.95, {"id": "0001", "title": "Test Paper 1", "quality_score": 85}),
            (1, 0.90, {"id": "0002", "title": "Test Paper 2", "quality_score": 75}),
        ]
        mock_cli.metadata = {"papers": []}

        # Execute batch with two searches and merge
        commands = [
            {"cmd": "search", "query": "test1", "k": 2},
            {"cmd": "search", "query": "test2", "k": 2},
            {"cmd": "merge"},
        ]
        results = _execute_batch(mock_cli, commands)

        # Verify merge result
        assert len(results) == 3
        assert results[2]["type"] == "merge"
        assert results[2]["success"] is True
        # Should have deduplicated papers (2 unique papers)
        assert results[2]["count"] == 2

    @patch("src.cli.ResearchCLI")
    def test_batch_meta_command_filter(self, mock_cli_class):
        """Test filter meta-command."""
        from src.cli import _execute_batch

        # Setup mock
        mock_cli = MagicMock()
        mock_cli.search.return_value = [
            (0, 0.95, {"id": "0001", "title": "High Quality", "quality_score": 85}),
            (1, 0.90, {"id": "0002", "title": "Low Quality", "quality_score": 65}),
        ]
        mock_cli.metadata = {"papers": []}

        # Execute batch with search and filter
        commands = [
            {"cmd": "search", "query": "test", "k": 2},
            {"cmd": "filter", "min_quality": 80},
        ]
        results = _execute_batch(mock_cli, commands)

        # Verify filter result
        assert len(results) == 2
        assert results[1]["type"] == "filter"
        assert results[1]["success"] is True
        assert results[1]["count"] == 1  # Only high quality paper
        assert results[1]["data"][0]["id"] == "0001"

    @patch("src.cli.ResearchCLI")
    def test_batch_meta_command_auto_get_top(self, mock_cli_class):
        """Test auto-get-top meta-command."""
        from src.cli import _execute_batch

        # Setup mock
        mock_cli = MagicMock()
        mock_cli.search.return_value = [
            (0, 0.95, {"id": "0001", "title": "Paper 1", "quality_score": 85}),
            (1, 0.90, {"id": "0002", "title": "Paper 2", "quality_score": 75}),
            (2, 0.85, {"id": "0003", "title": "Paper 3", "quality_score": 70}),
        ]
        mock_cli.metadata = {
            "papers": [
                {"id": "0001", "title": "Paper 1", "abstract": "Abstract 1"},
                {"id": "0002", "title": "Paper 2", "abstract": "Abstract 2"},
                {"id": "0003", "title": "Paper 3", "abstract": "Abstract 3"},
            ]
        }

        # Execute batch
        commands = [
            {"cmd": "search", "query": "test", "k": 3},
            {"cmd": "auto-get-top", "limit": 2, "min_quality": 70},
        ]

        # Mock file reading for paper content
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Paper content"
            with patch("pathlib.Path.exists", return_value=True):
                results = _execute_batch(mock_cli, commands)

        # Verify auto-get-top result
        assert len(results) == 2
        assert results[1]["type"] == "auto-get-top"
        assert results[1]["success"] is True
        assert results[1]["count"] == 2  # Top 2 papers
        assert all("content" in paper for paper in results[1]["data"])

    @patch("src.cli.ResearchCLI")
    def test_batch_error_handling(self, mock_cli_class):
        """Test error handling in batch execution."""
        from src.cli import _execute_batch

        # Setup mock
        mock_cli = MagicMock()
        mock_cli.search.side_effect = Exception("Search failed")
        mock_cli.metadata = {"papers": []}

        # Execute batch with failing command
        commands = [{"cmd": "search", "query": "test"}]
        results = _execute_batch(mock_cli, commands)

        # Verify error handling
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Search failed" in results[0]["error"]

    @patch("src.cli.ResearchCLI")
    def test_batch_unknown_command(self, mock_cli_class):
        """Test handling of unknown commands."""
        from src.cli import _execute_batch

        # Setup mock
        mock_cli = MagicMock()
        mock_cli.metadata = {"papers": []}

        # Execute batch with unknown command
        commands = [{"cmd": "unknown_command"}]
        results = _execute_batch(mock_cli, commands)

        # Verify error handling
        assert len(results) == 1
        assert results[0]["success"] is False
        assert "Unknown command" in results[0]["error"]

    def test_batch_json_file_input(self):
        """Test batch execution from JSON file."""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"cmd": "search", "query": "test", "k": 1}], f)
            temp_file = f.name

        try:
            # Run batch command with file
            result = subprocess.run(
                ["python", "src/cli.py", "batch", temp_file, "--output", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            # Should not error (even if no KB exists)
            # The command should at least parse the JSON
            assert "Invalid JSON" not in result.stderr
        finally:
            # Clean up
            Path(temp_file).unlink()

    def test_batch_stdin_input(self):
        """Test batch execution from stdin."""
        # Prepare JSON input
        commands = json.dumps([{"cmd": "search", "query": "test", "k": 1}])

        # Run batch command with stdin
        result = subprocess.run(
            ["python", "src/cli.py", "batch", "-", "--output", "json"],
            input=commands,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        # Should not error on JSON parsing
        assert "Invalid JSON" not in result.stderr

    def test_batch_output_formats(self):
        """Test both JSON and text output formats."""
        from src.cli import _format_batch_text

        # Test text formatting
        results = [
            {
                "success": True,
                "type": "search",
                "count": 2,
                "data": [
                    {"id": "0001", "title": "Paper 1", "quality": 85, "score": 0.95},
                    {"id": "0002", "title": "Paper 2", "quality": 75, "score": 0.90},
                ],
            }
        ]

        # Should not raise any exceptions
        _format_batch_text(results)

    @patch("src.cli.ResearchCLI")
    def test_batch_context_sharing(self, mock_cli_class):
        """Test that context is properly shared between commands."""
        from src.cli import _execute_batch

        # Setup mock
        mock_cli = MagicMock()
        mock_cli.search.return_value = [
            (0, 0.95, {"id": "0001", "title": "Paper 1", "quality_score": 85}),
        ]
        mock_cli.metadata = {"papers": []}

        # Execute batch with commands that depend on context
        commands = [
            {"cmd": "search", "query": "test", "k": 1},
            {"cmd": "filter", "min_quality": 80},  # Should filter previous search
        ]
        results = _execute_batch(mock_cli, commands)

        # Verify context was maintained
        assert results[1]["success"] is True
        assert results[1]["count"] == 1  # Filter applied to search results

    def test_batch_performance(self):
        """Test that batch is faster than individual commands (when KB exists)."""
        # This is more of an integration test
        # We'll just verify the command structure is correct
        from src.cli import _generate_preset_commands

        commands = _generate_preset_commands("research", "test")

        # Research preset should have multiple operations
        assert len(commands) >= 5

        # If executed, this would be much faster than individual calls
        # because model loads only once
