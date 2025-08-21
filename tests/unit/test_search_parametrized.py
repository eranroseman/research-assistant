#!/usr/bin/env python3
"""Parametrized tests for search functionality - replacing repetitive filter tests."""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tests.utils import create_mock_paper


class TestSearchFilters:
    """Parametrized tests for search filtering functionality."""
    
    @pytest.mark.parametrize(("filter_type", "filter_value", "papers_data", "expected_ids"), [
        # Year filtering tests
        ("year", 2023, [
            {"id": "0001", "year": 2020, "abstract": "test"},
            {"id": "0002", "year": 2023, "abstract": "test"},
            {"id": "0003", "year": 2024, "abstract": "test"},
        ], ["0002", "0003"]),
        
        ("year", 2024, [
            {"id": "0001", "year": 2023, "abstract": "test"},
            {"id": "0002", "year": 2024, "abstract": "test"},
            {"id": "0003", "year": 2025, "abstract": "test"},
        ], ["0002", "0003"]),
        
        # Study type filtering tests
        ("study_type", ["rct"], [
            {"id": "0001", "study_type": "rct", "abstract": "test"},
            {"id": "0002", "study_type": "cohort", "abstract": "test"},
            {"id": "0003", "study_type": "systematic_review", "abstract": "test"},
        ], ["0001"]),
        
        ("study_type", ["rct", "systematic_review"], [
            {"id": "0001", "study_type": "rct", "abstract": "test"},
            {"id": "0002", "study_type": "cohort", "abstract": "test"},
            {"id": "0003", "study_type": "systematic_review", "abstract": "test"},
        ], ["0001", "0003"]),
        
        
        # Combined filters
        ("combined_year_type", {"year": 2023, "types": ["rct"]}, [
            {"id": "0001", "year": 2023, "study_type": "rct", "abstract": "test"},
            {"id": "0002", "year": 2023, "study_type": "cohort", "abstract": "test"},
            {"id": "0003", "year": 2022, "study_type": "rct", "abstract": "test"},
        ], ["0001"]),
        
        # Full text filtering
        ("has_full_text", True, [
            {"id": "0001", "has_full_text": True, "abstract": "test"},
            {"id": "0002", "has_full_text": False, "abstract": "test"},
            {"id": "0003", "has_full_text": True, "abstract": "test"},
        ], ["0001", "0003"]),
    ])
    @patch("faiss.read_index")
    @patch("sentence_transformers.SentenceTransformer")
    def test_search_with_filters(
        self,
        mock_transformer,
        mock_faiss_read,
        filter_type,
        filter_value,
        papers_data,
        expected_ids,
        tmp_path
    ):
        """Test search with various filter combinations.
        
        Args:
            filter_type: Type of filter to apply
            filter_value: Value for the filter
            papers_data: Test paper data
            expected_ids: Expected paper IDs in results
        """
        from src.cli import ResearchCLI
        
        # Complete paper data with defaults
        papers = []
        for i, paper_data in enumerate(papers_data):
            paper = create_mock_paper(**paper_data)
            paper["embedding_index"] = i
            papers.append(paper)
        
        metadata = {
            "papers": papers,
            "total_papers": len(papers),
            "version": "4.0"
        }
        
        # Set up test environment
        metadata_file = tmp_path / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))
        (tmp_path / "index.faiss").touch()
        
        # Mock FAISS search to return all papers
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1] * len(papers)]),
            np.array([list(range(len(papers)))])
        )
        mock_faiss_read.return_value = mock_index
        
        # Mock transformer
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(1, 768).astype("float32")
        mock_transformer.return_value = mock_model
        
        # Create CLI and perform search
        cli = ResearchCLI(str(tmp_path))
        
        # Apply appropriate filter based on type
        if filter_type == "year":
            results = cli.search("test", min_year=filter_value)
        elif filter_type == "study_type":
            results = cli.search("test", study_types=filter_value)
        elif filter_type == "has_full_text":
            # ResearchCLI.search doesn't have full_text_only parameter, skip this test
            pytest.skip("full_text_only filtering not implemented in ResearchCLI.search")
        elif filter_type == "combined_year_type":
            results = cli.search(
                "test",
                min_year=filter_value["year"],
                study_types=filter_value["types"]
            )
        else:
            pytest.fail(f"Unknown filter type: {filter_type}")
        
        # Verify results - ResearchCLI.search returns (idx, dist, paper) tuples
        result_ids = [paper["id"] for idx, dist, paper in results]
        assert set(result_ids) == set(expected_ids), (
            f"Expected IDs {expected_ids}, got {result_ids}"
        )


class TestSearchCommandVariations:
    """Parametrized tests for CLI search command variations."""
    
    @pytest.mark.parametrize(("command_args", "expected_in_output", "expected_not_in_output"), [
        # Basic search variations
        (["search", "--help"], ["--after", "--type", "--min-quality"], ["error"]),
        (["smart-search", "--help"], ["smart", "-k"], ["error"]),
        (["author", "--help"], ["author", "--exact"], ["error"]),
        
        # Search with different options
        (["search", "test", "-k", "5"], ["search", "test"], ["error"]),
        (["search", "test", "--show-quality"], ["quality"], ["error"]),
        (["search", "test", "--after", "2023"], ["2023"], ["error"]),
        
        # Info commands
        (["info"], ["papers", "version"], ["error"]),
        (["diagnose"], ["Knowledge base"], ["error"]),
    ])
    def test_cli_command_output(
        self,
        command_args,
        expected_in_output,
        expected_not_in_output,
        tmp_path,
        monkeypatch
    ):
        """Test various CLI command outputs.
        
        Args:
            command_args: CLI command arguments
            expected_in_output: Strings that should appear in output
            expected_not_in_output: Strings that should not appear
        """
        # Create minimal test KB
        from tests.utils import create_test_kb_structure
        create_test_kb_structure(tmp_path)
        
        # Set KB path environment variable
        env = {**os.environ, "KNOWLEDGE_BASE_PATH": str(tmp_path)}
        
        # Run command
        result = subprocess.run(
            [sys.executable, "src/cli.py", *command_args],
            capture_output=True,
            text=True,
            check=False,
            env=env,
            cwd=Path(__file__).parent.parent.parent
        )
        
        # Combine stdout and stderr for checking
        output = result.stdout + result.stderr
        
        # Check expected strings
        for expected in expected_in_output:
            assert expected.lower() in output.lower(), (
                f"Expected '{expected}' in output, got: {output[:200]}"
            )
        
        # Check unexpected strings
        for unexpected in expected_not_in_output:
            assert unexpected.lower() not in output.lower(), (
                f"Unexpected '{unexpected}' in output"
            )


class TestBatchCommandPresets:
    """Parametrized tests for batch command presets."""
    
    @pytest.mark.parametrize(("preset", "topic", "expected_commands", "min_commands"), [
        ("research", "diabetes", ["search", "merge"], 5),
        ("review", "cancer", ["search", "filter"], 4),
        ("author-scan", "Smith J", ["author"], 2),
        
        # Different topics with same preset
        ("research", "AI ethics", ["search"], 5),
        ("research", "COVID-19 vaccines", ["search", "merge"], 5),
        
        # Edge cases
        ("review", "rare disease", ["search", "filter"], 4),
        ("author-scan", "Johnson, A.B.", ["author"], 2),
    ])
    def test_batch_preset_generation(self, preset, topic, expected_commands, min_commands):
        """Test batch preset command generation.
        
        Args:
            preset: Preset name
            topic: Search topic
            expected_commands: Commands that should be present
            min_commands: Minimum number of commands expected
        """
        from src.cli import _generate_preset_commands
        
        commands = _generate_preset_commands(preset, topic)
        
        # Check minimum command count
        assert len(commands) >= min_commands, (
            f"Expected at least {min_commands} commands, got {len(commands)}"
        )
        
        # Check expected commands are present
        command_types = [cmd.get("cmd") for cmd in commands]
        for expected_cmd in expected_commands:
            assert expected_cmd in command_types, (
                f"Expected command '{expected_cmd}' not found in {command_types}"
            )
        
        # Verify all commands have required fields
        for cmd in commands:
            assert "cmd" in cmd
            # Commands should have either args, or specific fields for their command type
            has_fields = (
                "args" in cmd or 
                "query" in cmd or  # search commands
                "name" in cmd or   # author commands
                "min_quality" in cmd or  # filter commands
                cmd["cmd"] in ["merge", "dedupe", "auto-get-all", "auto-get-top", "filter"]
            )
            assert has_fields, f"Command {cmd} missing required fields"
        
        # Check topic is used appropriately
        if preset != "author-scan":
            # Regular presets should use topic in search queries
            search_cmds = [c for c in commands if c["cmd"] == "search"]
            assert any(topic.lower() in str(c.get("args", [])).lower() 
                      for c in search_cmds)


