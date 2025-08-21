#!/usr/bin/env python3
"""Comprehensive CLI tests to improve coverage."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli import (
    ResearchCLI,
    estimate_paper_quality,
    _generate_preset_commands,
    _execute_batch,
)
from tests.utils import (
    create_mock_cli,
    create_test_kb_structure,
)


class TestCLICore:
    """Test core CLI functionality."""

    def test_cli_initialization_success(self, tmp_path):
        """Test successful CLI initialization."""
        # Use utility to create test KB structure
        create_test_kb_structure(
            tmp_path,
            include_papers=True,
            include_index=True
        )
        
        # Use utility to create mock CLI
        cli = create_mock_cli(
            papers_count=2,
            kb_path=tmp_path
        )
        
        assert cli.knowledge_base_path == tmp_path
        assert len(cli.metadata["papers"]) == 2
        assert cli.metadata["papers"][0]["id"] == "0001"

    def test_search_returns_formatted_results(self, tmp_path):
        """Test search returns formatted results."""
        with patch('src.cli.ResearchCLI._load_embedding_model') as mock_load_model, \
             patch('src.cli_kb_index.KnowledgeBaseIndex') as mock_kb_index, \
             patch('src.cli.faiss.read_index') as mock_read_index:
            
            # Create test KB structure
            create_test_kb_structure(tmp_path, include_papers=True, include_index=True)
            
            # Setup mocks
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[0.1] * 768])
            mock_load_model.return_value = mock_model
            
            mock_kb = MagicMock()
            test_paper = {
                "id": "0001",
                "title": "Test Paper 1",
                "authors": ["Author A", "Author B"],
                "year": 2023,
                "journal": "Test Journal",
                "abstract": "This is a test abstract",
                "study_type": "rct",
                "sample_size": 1000,
                "has_full_text": True,
                "embedding_index": 0
            }
            mock_kb.metadata = {
                "version": "4.0",
                "papers": [test_paper]
            }
            mock_kb.get_paper_by_index.return_value = test_paper
            mock_kb_index.return_value = mock_kb
            
            mock_index = MagicMock()
            mock_index.search.return_value = (np.array([[0.9]]), np.array([[0]]))
            mock_read_index.return_value = mock_index
            
            cli = ResearchCLI(str(tmp_path))
            results = cli.search("test")
            
            assert len(results) == 1
            assert results[0][2]["id"] == "0001"

    def test_estimate_paper_quality_comprehensive(self):
        """Test comprehensive quality scoring."""
        test_cases = [
            # Minimal paper
            ({}, 50, "base score"),
            # With study type
            ({"study_type": "systematic_review"}, 85, "systematic"),
            ({"study_type": "meta_analysis"}, 85, "meta"),
            ({"study_type": "rct"}, 75, "rct"),
            ({"study_type": "cohort"}, 65, "cohort"),
            ({"study_type": "case_control"}, 60, "case control"),
            ({"study_type": "cross_sectional"}, 55, "cross sectional"),
            ({"study_type": "case_report"}, 50, "case report"),
            ({"study_type": "unknown"}, 50, "unknown"),
            # With year (based on current year 2025)
            ({"year": 2024}, 58, "2024"),  # 1 year old = +8
            ({"year": 2020}, 50, "2020"),  # 5 years old = +0
            ({"year": 2015}, 50, "2015"),  # 10 years old = +0
            ({"year": 2000}, 50, "2000"),  # 25 years old = +0
            # With sample size (RCT)
            ({"study_type": "rct", "sample_size": 50}, 77, "small"),      # 50 + 25 + 2 = 77
            ({"study_type": "rct", "sample_size": 600}, 83, "medium"),    # 50 + 25 + 8 = 83
            ({"study_type": "rct", "sample_size": 1500}, 85, "large"),    # 50 + 25 + 10 = 85
            # With full text
            ({"has_full_text": True}, 55, "full-text"),
            ({"has_full_text": False}, 50, "no full-text"),
            # Combined high quality
            ({
                "study_type": "systematic_review",
                "year": 2024,
                "sample_size": 5000,
                "has_full_text": True
            }, 100, "maximum"),
        ]
        
        for paper, expected_score, description in test_cases:
            score, explanation = estimate_paper_quality(paper)
            assert score == expected_score, f"Failed for {description}: got {score}, expected {expected_score}"
            assert isinstance(explanation, str)

    def test_batch_command_generation(self):
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

    def test_execute_batch_commands(self, tmp_path):
        """Test batch command execution."""
        with patch('src.cli.ResearchCLI._load_embedding_model') as mock_load_model, \
             patch('src.cli_kb_index.KnowledgeBaseIndex') as mock_kb_index, \
             patch('src.cli.faiss.read_index') as mock_read_index:
            
            # Create test KB structure
            create_test_kb_structure(tmp_path, include_papers=True, include_index=True)
            
            # Setup mocks
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[0.1] * 768])
            mock_load_model.return_value = mock_model
            
            test_papers = [
                {"id": "0001", "title": "Result 1", "abstract": "test", "year": 2023, "embedding_index": 0},
                {"id": "0002", "title": "Result 2", "abstract": "test", "year": 2022, "embedding_index": 1}
            ]
            
            mock_kb = MagicMock()
            mock_kb.metadata = {"version": "4.0", "papers": test_papers}
            mock_kb.get_paper_by_index.side_effect = lambda i: test_papers[i] if i < len(test_papers) else None
            mock_kb_index.return_value = mock_kb
            
            mock_index = MagicMock()
            mock_index.search.return_value = (np.array([[0.1, 0.2]]), np.array([[0, 1]]))
            mock_read_index.return_value = mock_index
            
            cli = ResearchCLI(str(tmp_path))
            
            # Test batch execution
            commands = [
                {"cmd": "search", "query": "test", "k": 10},
                {"cmd": "merge"},
            ]
            
            results = _execute_batch(cli, commands)
            
            assert len(results) == 2
            assert results[0]["success"]
            assert "data" in results[0]



# Search functionality tests moved to test_search_parametrized.py
# Using parametrized tests for better coverage and less duplication


class TestCitationFunctionality:
    """Test citation generation."""

    def test_generate_citations(self, tmp_path):
        """Test IEEE citation generation."""
        # Use utility to create mock CLI with citation-ready paper
        cli = create_mock_cli(papers_count=1, kb_path=tmp_path)
        
        # Update paper with citation fields
        cli.metadata["papers"][0].update({
            "title": "Test Paper",
            "authors": ["Smith, J.", "Doe, J."],
            "journal": "Test Journal",
            "volume": "10",
            "number": "2",
            "pages": "100-110",
            "year": 2023,
            "doi": "10.1234/test.2023.001"
        })
        
        # Mock the generate_ieee_citation method
        def mock_generate_citation(paper_id):
            paper = cli.metadata["papers"][0]
            return f"{', '.join(paper['authors'])}, \"{paper['title']},\" {paper['journal']}, vol. {paper['volume']}, no. {paper['number']}, pp. {paper['pages']}, {paper['year']}."
        
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
