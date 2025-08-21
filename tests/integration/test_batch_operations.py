#!/usr/bin/env python3
"""Integration tests for batch command operations."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli import _execute_batch, _generate_preset_commands
from tests.utils import create_mock_cli, assert_batch_command_output


class TestBatchOperationsIntegration:
    """Test batch command execution workflows."""

    @pytest.fixture
    def mock_cli(self):
        """Create a mock CLI instance with test data."""
        # Use utility to create mock CLI with test papers
        cli = create_mock_cli(papers_count=4)
        
        # Update papers with specific test data
        cli.metadata["papers"][0].update({
            "title": "Systematic Review of Treatment",
            "abstract": "A comprehensive systematic review.",
            "study_type": "systematic_review",
            "quality_score": 95,
            "authors": ["Smith, J."],
            "journal": "Nature Medicine"
        })
        cli.metadata["papers"][1].update({
            "title": "RCT of New Drug",
            "abstract": "A randomized controlled trial.",
            "study_type": "rct",
            "quality_score": 85,
            "sample_size": 500,
            "authors": ["Johnson, B."],
            "journal": "NEJM"
        })
        cli.metadata["papers"][2].update({
            "title": "Cohort Study",
            "abstract": "A prospective cohort study.",
            "study_type": "cohort",
            "quality_score": 70,
            "authors": ["Lee, C."],
            "journal": "BMJ"
        })
        cli.metadata["papers"][3].update({
            "title": "Case Report",
            "abstract": "An unusual case presentation.",
            "study_type": "case_report",
            "quality_score": 45,
            "authors": ["Brown, D."],
            "journal": "Case Reports"
        })
        
        # Mock search method
        def mock_search(query, k=10, **kwargs):
            # Return different results based on query
            if "systematic" in query.lower():
                return [(0, 0.95, cli.metadata["papers"][0])]
            elif "rct" in query.lower() or "randomized" in query.lower():
                return [(1, 0.90, cli.metadata["papers"][1])]
            elif "cohort" in query.lower():
                return [(2, 0.85, cli.metadata["papers"][2])]
            else:
                # Return all papers for general queries
                return [
                    (i, 0.95 - i*0.05, paper)
                    for i, paper in enumerate(cli.metadata["papers"])
                ]
        
        cli.search = MagicMock(side_effect=mock_search)
        return cli

    def test_batch_execute_search_workflow(self, mock_cli):
        """
        Test batch execution of search commands.
        
        Given: Batch with multiple search commands
        When: Batch is executed
        Then: All searches are performed and results collected
        """
        commands = [
            {"cmd": "search", "query": "systematic review", "k": 5},
            {"cmd": "search", "query": "randomized trial", "k": 5},
            {"cmd": "search", "query": "treatment", "k": 10}
        ]
        
        result = _execute_batch(mock_cli, commands)
        
        # Use utility to verify batch execution
        assert_batch_command_output(
            result,
            expected_commands=["search", "search", "search"],
            expected_results_count=3
        )
        
        # Verify specific search results - using actual CLI format
        assert len(result) == 3  # Three commands executed
        assert result[0]["type"] == "search"
        assert result[1]["type"] == "search"
        assert result[2]["type"] == "search"

    def test_batch_meta_command_merge_workflow(self, mock_cli):
        """
        Test merge meta-command in batch workflow.
        
        Given: Multiple searches followed by merge
        When: Batch is executed
        Then: Results are merged and deduplicated
        """
        commands = [
            {"cmd": "search", "query": "systematic", "k": 2},
            {"cmd": "search", "query": "treatment", "k": 3},
            {"cmd": "merge"}
        ]
        
        result = _execute_batch(mock_cli, commands)
        
        # Use utility to verify batch execution
        assert_batch_command_output(
            result,
            expected_commands=["search", "search", "merge"],
            expected_results_count=3
        )
        
        # Check merge-specific behavior
        results = result["results"]
        merged_ids = {p["id"] for p in results[2]["data"]}
        assert len(merged_ids) == results[2]["count"]  # No duplicates

    def test_batch_meta_command_filter_workflow(self, mock_cli):
        """
        Test filter meta-command in batch workflow.
        
        Given: Search followed by quality filter
        When: Batch is executed
        Then: Only high-quality papers remain
        """
        commands = [
            {"cmd": "search", "query": "treatment", "k": 10},
            {"cmd": "filter", "min_quality": 80}
        ]
        
        result = _execute_batch(mock_cli, commands)
        
        # Use utility to verify batch execution
        assert_batch_command_output(
            result,
            expected_commands=["search", "filter"],
            expected_results_count=2
        )
        
        # Check filter-specific behavior
        results = result["results"]
        filtered_papers = results[1]["data"]
        assert all(p["quality_score"] >= 80 for p in filtered_papers)
        assert len(filtered_papers) == 2  # Only systematic review and RCT

    def test_batch_meta_command_auto_get_top_workflow(self, mock_cli):
        """
        Test auto-get-top meta-command in batch workflow.
        
        Given: Search followed by auto-get-top
        When: Batch is executed
        Then: Top papers are retrieved with content
        """
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Paper content"
            with patch("pathlib.Path.exists", return_value=True):
                commands = [
                    {"cmd": "search", "query": "treatment", "k": 5},
                    {"cmd": "auto-get-top", "limit": 2, "min_quality": 70}
                ]
                
                results = _execute_batch(mock_cli, commands)
                
                # Verify auto-get-top command
                assert len(results) == 2
                assert results[1]["type"] == "auto-get-top"
                assert results[1]["success"] is True
                assert results[1]["count"] == 2
                
                # Check content was added
                for paper in results[1]["data"]:
                    assert "content" in paper
                    assert paper["quality_score"] >= 70

    def test_batch_context_sharing_between_commands(self, mock_cli):
        """
        Test that context is properly shared between batch commands.
        
        Given: Sequential commands that depend on previous results
        When: Batch is executed
        Then: Each command operates on results from previous commands
        """
        commands = [
            {"cmd": "search", "query": "treatment", "k": 10},
            {"cmd": "filter", "min_quality": 70},
            {"cmd": "filter", "min_year": 2023},
            {"cmd": "auto-get-top", "limit": 1}
        ]
        
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Content"
            with patch("pathlib.Path.exists", return_value=True):
                results = _execute_batch(mock_cli, commands)
        
        # Verify context flows through commands
        assert len(results) == 4
        
        # After first filter (quality >= 70)
        assert results[1]["count"] == 3  # Excludes case report
        
        # After second filter (year >= 2023)
        assert results[2]["count"] == 2  # Only 2023 and 2024 papers
        
        # Auto-get-top gets the filtered results
        assert results[3]["count"] == 1
        assert results[3]["data"][0]["year"] >= 2023

    def test_batch_error_handling_continues_execution(self, mock_cli):
        """
        Test that batch continues after command errors.
        
        Given: Batch with failing command in middle
        When: Batch is executed
        Then: Error is recorded but execution continues
        """
        # Make search fail for specific query
        def mock_search_with_error(query, **kwargs):
            if "error" in query:
                raise RuntimeError("Search failed")
            return [(0, 0.9, mock_cli.metadata["papers"][0])]
        
        mock_cli.search = MagicMock(side_effect=mock_search_with_error)
        
        commands = [
            {"cmd": "search", "query": "valid query", "k": 5},
            {"cmd": "search", "query": "error query", "k": 5},
            {"cmd": "search", "query": "another valid", "k": 5}
        ]
        
        results = _execute_batch(mock_cli, commands)
        
        # All commands should have results
        assert len(results) == 3
        
        # First command succeeds
        assert results[0]["success"] is True
        
        # Second command fails
        assert results[1]["success"] is False
        assert "Search failed" in results[1]["error"]
        
        # Third command still executes
        assert results[2]["success"] is True

    def test_batch_unknown_command_handling(self, mock_cli):
        """
        Test handling of unknown commands in batch.
        
        Given: Batch with unknown command
        When: Batch is executed
        Then: Unknown command returns error
        """
        commands = [
            {"cmd": "search", "query": "test", "k": 5},
            {"cmd": "unknown_command", "param": "value"},
            {"cmd": "filter", "min_quality": 80}
        ]
        
        results = _execute_batch(mock_cli, commands)
        
        # All commands processed
        assert len(results) == 3
        
        # Unknown command fails
        assert results[1]["success"] is False
        assert "Unknown command" in results[1]["error"]
        
        # Other commands still work
        assert results[0]["success"] is True
        assert results[2]["success"] is True


class TestBatchPresetWorkflows:
    """Test preset-based batch workflows."""

    def test_research_preset_comprehensive_workflow(self):
        """
        Test that research preset creates comprehensive workflow.
        
        Given: Research preset for a topic
        When: Commands are generated
        Then: Creates multi-faceted search workflow
        """
        commands = _generate_preset_commands("research", "diabetes treatment")
        
        # Verify comprehensive search strategy
        search_commands = [c for c in commands if c["cmd"] == "search"]
        assert len(search_commands) >= 3
        
        # Check search variations
        queries = [c["query"] for c in search_commands]
        assert any("systematic review" in q for q in queries)
        assert any("randomized" in q or "RCT" in q for q in queries)
        assert any("meta-analysis" in q for q in queries)
        
        # Verify workflow commands
        assert any(c["cmd"] == "merge" for c in commands)
        assert any(c["cmd"] == "filter" for c in commands)
        assert any(c["cmd"] == "auto-get-top" for c in commands)

    def test_review_preset_focuses_on_high_quality(self):
        """
        Test that review preset focuses on high-quality evidence.
        
        Given: Review preset for a topic
        When: Commands are generated
        Then: Searches for and filters high-quality papers
        """
        commands = _generate_preset_commands("review", "hypertension management")
        
        # Check focus on reviews
        search_commands = [c for c in commands if c["cmd"] == "search"]
        for cmd in search_commands:
            query = cmd["query"].lower()
            assert "systematic review" in query or "meta-analysis" in query
        
        # Check quality filtering
        filter_commands = [c for c in commands if c["cmd"] == "filter"]
        assert len(filter_commands) > 0
        assert any(c.get("min_quality", 0) >= 80 for c in filter_commands)

    def test_author_scan_preset_workflow(self):
        """
        Test that author-scan preset searches by author.
        
        Given: Author-scan preset with author name
        When: Commands are generated
        Then: Searches for author's papers and retrieves them
        """
        commands = _generate_preset_commands("author-scan", "Smith J")
        
        # Check author search
        author_commands = [c for c in commands if c["cmd"] == "author"]
        assert len(author_commands) == 1
        assert author_commands[0]["name"] == "Smith J"
        
        # Check retrieval command
        assert any(c["cmd"] == "auto-get-all" for c in commands)


class TestBatchPerformance:
    """Test batch operation performance characteristics."""

    @patch("src.cli.ResearchCLI")
    def test_batch_reuses_model_for_efficiency(self, mock_cli_class):
        """
        Test that batch operations reuse loaded model.
        
        Given: Multiple search commands in batch
        When: Batch is executed
        Then: Model is loaded once and reused
        """
        mock_cli = MagicMock()
        mock_model = MagicMock()
        mock_cli.model = mock_model
        mock_cli.metadata = {"papers": []}
        
        # Track model encode calls
        encode_calls = []
        mock_model.encode.side_effect = lambda x, **_kwargs: encode_calls.append(x) or np.random.randn(1, 768)
        
        # Mock search to use the model
        def mock_search(query, **kwargs):
            mock_model.encode([query])
            return []
        
        mock_cli.search = MagicMock(side_effect=mock_search)
        
        # Execute batch with multiple searches
        commands = [
            {"cmd": "search", "query": f"query {i}", "k": 5}
            for i in range(5)
        ]
        
        _execute_batch(mock_cli, commands)
        
        # Model should be used for each search
        assert len(encode_calls) == 5
        
        # But model itself is the same instance (not reloaded)
        assert mock_cli.model is mock_model

    def test_batch_handles_large_result_sets(self, mock_cli):
        """
        Test that batch handles large result sets efficiently.
        
        Given: Commands that return many results
        When: Batch is executed
        Then: Handles large data without issues
        """
        # Make search return many results
        large_results = [
            (i, 0.99 - i*0.001, {
                "id": f"{i:04d}",
                "title": f"Paper {i}",
                "abstract": f"Abstract {i}" * 100,  # Large abstract
                "quality_score": 80
            })
            for i in range(100)
        ]
        
        mock_cli.search = MagicMock(return_value=large_results)
        
        commands = [
            {"cmd": "search", "query": "large search", "k": 100},
            {"cmd": "filter", "min_quality": 75}
        ]
        
        results = _execute_batch(mock_cli, commands)
        
        # Should handle large results
        assert results[0]["success"] is True
        assert results[0]["count"] == 100
        
        # Filter should work on large set
        assert results[1]["success"] is True
        assert results[1]["count"] == 100  # All pass filter


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
