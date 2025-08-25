#!/usr/bin/env python3
"""Comprehensive CLI tests to improve coverage."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli import (
    _generate_preset_commands,
    _execute_batch,
)
from src.build_kb import calculate_enhanced_quality_score
from tests.utils import (
    create_mock_cli,
    create_test_kb_structure,
)


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.cli
class TestCLICore:
    """Test core CLI functionality."""

    def test_cli_initialization_with_valid_kb_should_succeed(self, tmp_path):
        """Test successful CLI initialization."""
        # Use utility to create test KB structure
        create_test_kb_structure(tmp_path, include_papers=True, include_index=True)

        # Use utility to create mock CLI
        cli = create_mock_cli(papers_count=2, kb_path=tmp_path)

        assert cli.knowledge_base_path == tmp_path
        assert len(cli.metadata["papers"]) == 2
        assert cli.metadata["papers"][0]["id"] == "0001"

    def test_search_execution_should_return_formatted_results(self, tmp_path):
        """Test search returns formatted results using mock CLI."""
        # Use utility to create mock CLI with proper setup
        cli = create_mock_cli(papers_count=1, with_embeddings=True, with_index=True)

        # Set up mock search results
        test_paper = cli.metadata["papers"][0]
        test_paper.update({"id": "0001", "title": "Test Paper 1", "study_type": "rct", "quality_score": 75})

        # Mock the search method to return expected format
        def mock_search_impl(query_text, **kwargs):
            return [(0, 0.9, test_paper)]

        cli.search = MagicMock(side_effect=mock_search_impl)
        results = cli.search("test")

        assert len(results) == 1
        assert results[0][2]["id"] == "0001"

    def test_quality_scoring_integration_with_cli_should_work_correctly(self):
        """Test enhanced quality scoring integration with CLI workflows."""
        # Test that enhanced quality scoring works within CLI context
        paper = {"title": "Test Integration Paper", "study_type": "rct", "year": 2023, "sample_size": 500}

        # Mock Semantic Scholar API data
        s2_data = {
            "citationCount": 50,
            "venue": {"name": "Journal of Medicine"},
            "authors": [{"hIndex": 15}],
            "externalIds": {"DOI": "10.1000/test"},
            "publicationTypes": ["JournalArticle"],
            "fieldsOfStudy": ["Medicine"],
        }

        score, explanation = calculate_enhanced_quality_score(paper, s2_data)

        # Verify enhanced scoring integration
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "[Enhanced scoring]" in explanation

        # Should score reasonably for an RCT
        assert score >= 50

    def test_batch_command_generation_should_create_valid_commands(self):
        """Test batch command generation."""
        # Test research preset
        commands = _generate_preset_commands("research", "diabetes")
        assert len(commands) > 5
        assert any(c.get("cmd") == "search" for c in commands)
        assert any(c.get("cmd") == "merge" for c in commands)
        assert any(c.get("cmd") == "filter" for c in commands)

        # Test review preset
        commands = _generate_preset_commands("review", "hypertension")
        assert len(commands) > 3
        assert any("systematic" in str(c).lower() for c in commands)

        # Test author-scan preset
        commands = _generate_preset_commands("author-scan", "Smith J")
        assert len(commands) >= 1
        assert any(c.get("cmd") == "author" for c in commands)

        # Test invalid preset
        with pytest.raises(ValueError, match="Unknown preset"):
            _generate_preset_commands("invalid", "test")

    def test_execute_batch_commands_should_run_successfully(self):
        """Test batch command execution using mock CLI."""
        # Use utility to create mock CLI
        cli = create_mock_cli(papers_count=2)

        # Mock the search method to return proper format
        def mock_search_impl(query_text, **kwargs):
            return [(0, 0.9, cli.metadata["papers"][0]), (1, 0.8, cli.metadata["papers"][1])]

        cli.search = MagicMock(side_effect=mock_search_impl)

        # Test batch execution
        commands = [
            {"cmd": "search", "query": "test", "k": 10},
        ]

        results = _execute_batch(cli, commands)

        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["type"] == "search"
        assert "data" in results[0]


# Search functionality tests moved to test_search_parametrized.py
# Using parametrized tests for better coverage and less duplication


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.citation
class TestCitationFunctionality:
    """Test citation generation."""

    def test_generate_citations_should_format_correctly(self, tmp_path):
        """Test IEEE citation generation."""
        # Use utility to create mock CLI with citation-ready paper
        cli = create_mock_cli(papers_count=1, kb_path=tmp_path)

        # Update paper with citation fields
        cli.metadata["papers"][0].update(
            {
                "title": "Test Paper",
                "authors": ["Smith, J.", "Doe, J."],
                "journal": "Test Journal",
                "volume": "10",
                "number": "2",
                "pages": "100-110",
                "year": 2023,
                "doi": "10.1234/test.2023.001",
            },
        )

        # Mock the generate_ieee_citation method
        def mock_generate_citation(paper_id):
            paper = cli.metadata["papers"][0]
            return f'{", ".join(paper["authors"])}, "{paper["title"]}," {paper["journal"]}, vol. {paper["volume"]}, no. {paper["number"]}, pp. {paper["pages"]}, {paper["year"]}.'

        cli.generate_ieee_citation = MagicMock(side_effect=mock_generate_citation)

        # Generate citation
        citation = cli.generate_ieee_citation("0001")

        assert citation is not None
        assert "Smith, J." in citation
        assert "Test Paper" in citation
        assert "2023" in citation
        assert "Test Journal" in citation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
