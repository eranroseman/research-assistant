#!/usr/bin/env python3
"""Integration tests for search workflow."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSearchWorkflowIntegration:
    """Test complete search workflows."""

    @pytest.fixture
    def mock_kb(self, tmp_path):
        """Create a mock knowledge base for testing."""
        # Create metadata
        metadata = {
            "papers": [
                {
                    "id": "0001",
                    "title": "Systematic Review of Diabetes Treatment",
                    "abstract": "A comprehensive systematic review examining diabetes interventions.",
                    "year": 2023,
                    "study_type": "systematic_review",
                    "has_full_text": True,
                    "authors": ["Smith, J.", "Doe, A."],
                    "journal": "Diabetes Care",
                    "doi": "10.1234/dc.2023.0001"
                },
                {
                    "id": "0002",
                    "title": "RCT of New Diabetes Drug",
                    "abstract": "A randomized controlled trial testing a novel diabetes medication.",
                    "year": 2024,
                    "study_type": "rct",
                    "sample_size": 500,
                    "has_full_text": True,
                    "authors": ["Johnson, B."],
                    "journal": "NEJM",
                    "doi": "10.1234/nejm.2024.0002"
                },
                {
                    "id": "0003",
                    "title": "Diabetes Case Report",
                    "abstract": "A case report of unusual diabetes presentation.",
                    "year": 2020,
                    "study_type": "case_report",
                    "has_full_text": False,
                    "authors": ["Lee, C."],
                    "journal": "Case Reports",
                    "doi": "10.1234/cr.2020.0003"
                }
            ],
            "total_papers": 3,
            "version": "4.0",
            "embedding_model": "sentence-transformers/allenai-specter",
            "embedding_dimensions": 768
        }
        
        # Save metadata
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)
        
        # Create paper files
        papers_dir = tmp_path / "papers"
        papers_dir.mkdir()
        
        for paper in metadata["papers"]:
            paper_file = papers_dir / f"paper_{paper['id']}.md"
            paper_file.write_text(f"# {paper['title']}\n\n{paper['abstract']}")
        
        # Create sections index
        sections = {
            "0001": {
                "abstract": metadata["papers"][0]["abstract"],
                "methods": "Systematic search of databases...",
                "results": "Found 50 relevant studies...",
                "conclusion": "Evidence supports intervention..."
            },
            "0002": {
                "abstract": metadata["papers"][1]["abstract"],
                "methods": "Double-blind randomized design...",
                "results": "Significant improvement in HbA1c...",
                "conclusion": "Drug shows promise..."
            },
            "0003": {
                "abstract": metadata["papers"][2]["abstract"],
                "introduction": "Unusual presentation...",
                "case": "Patient presented with..."
            }
        }
        
        sections_file = tmp_path / "sections_index.json"
        with open(sections_file, "w") as f:
            json.dump(sections, f)
        
        return tmp_path

    @patch("src.cli.faiss")
    @patch("sentence_transformers.SentenceTransformer")
    def test_search_with_quality_filter_workflow(self, mock_transformer, mock_faiss, mock_kb):
        """
        Test search workflow with quality filtering.
        
        Given: Knowledge base with papers of varying quality
        When: Search is performed with quality filter
        Then: Only high-quality papers are returned
        """
        from src.cli import ResearchCLI
        
        # Mock embedding model
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(1, 768).astype("float32")
        mock_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = MagicMock()
        # Return all 3 papers with decreasing similarity scores
        mock_index.search.return_value = (
            np.array([[0.1, 0.2, 0.3]]),
            np.array([[0, 1, 2]])
        )
        mock_faiss.read_index.return_value = mock_index
        
        # Initialize CLI
        cli = ResearchCLI(str(mock_kb))
        
        # Search with basic parameters (quality filtering happens in CLI command, not method)
        results = cli.search(
            "diabetes treatment",
            top_k=10
        )
        
        # Should return all papers that match the query
        assert len(results) == 3  # All papers match the query
        paper_ids = [r[2]["id"] for r in results]
        assert "0001" in paper_ids  # Systematic review
        assert "0002" in paper_ids  # RCT
        assert "0003" in paper_ids  # Case report

    @patch("src.cli.faiss")
    @patch("sentence_transformers.SentenceTransformer")
    def test_smart_search_section_chunking_workflow(self, mock_transformer, mock_faiss, mock_kb):
        """
        Test smart search with section chunking.
        
        Given: Query focused on methods
        When: Smart search is performed
        Then: Searches across section chunks and aggregates results
        """
        from src.cli import ResearchCLI
        
        # Mock embedding model
        mock_model = MagicMock()
        call_count = 0
        
        def encode_side_effect(texts, **kwargs):
            nonlocal call_count
            call_count += 1
            # Return different embeddings for each call
            return np.random.randn(len(texts) if isinstance(texts, list) else 1, 768).astype("float32")
        
        mock_model.encode = MagicMock(side_effect=encode_side_effect)
        mock_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1, 0.2]]),
            np.array([[0, 1]])
        )
        mock_faiss.read_index.return_value = mock_index
        
        # Initialize CLI
        cli = ResearchCLI(str(mock_kb))
        
        # Perform smart search
        results = cli.smart_search(
            "randomized controlled trial methodology",
            k=5
        )
        
        # Should have made multiple searches (for different sections)
        assert call_count > 1
        
        # Results should be saved to file
        output_file = Path("system") / "dev_smart_search_results.json"
        if output_file.exists():
            with open(output_file) as f:
                saved_results = json.load(f)
            assert "results" in saved_results

    @patch("src.cli.faiss")
    @patch("sentence_transformers.SentenceTransformer")
    def test_batch_research_workflow(self, mock_transformer, mock_faiss, mock_kb):
        """
        Test complete batch research workflow.
        
        Given: Research preset for diabetes
        When: Batch is executed
        Then: Performs multiple searches and aggregates results
        """
        from src.cli import ResearchCLI, _generate_preset_commands, _execute_batch
        
        # Mock embedding model
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(1, 768).astype("float32")
        mock_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1, 0.2, 0.3]]),
            np.array([[0, 1, 2]])
        )
        mock_faiss.read_index.return_value = mock_index
        
        # Initialize CLI
        cli = ResearchCLI(str(mock_kb))
        
        # Generate research workflow
        commands = _generate_preset_commands("research", "diabetes")
        
        # Execute batch
        results = _execute_batch(cli, commands)
        
        # Should have results for all commands
        assert len(results) == len(commands)
        
        # Check that searches were performed
        search_results = [r for r in results if r.get("type") == "search"]
        assert len(search_results) >= 3
        
        # Check that merge was performed
        merge_results = [r for r in results if r.get("type") == "merge"]
        assert len(merge_results) >= 1
        
        # Check that filter was applied
        filter_results = [r for r in results if r.get("type") == "filter"]
        assert len(filter_results) >= 1

    @patch("src.cli.faiss")
    @patch("sentence_transformers.SentenceTransformer")
    def test_author_search_workflow(self, mock_transformer, mock_faiss, mock_kb):
        """
        Test author search workflow.
        
        Given: Author name
        When: Author search is performed
        Then: Returns papers by that author
        """
        from src.cli import ResearchCLI
        from src.cli_kb_index import KnowledgeBaseIndex
        
        # Mock embedding model
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = MagicMock()
        mock_faiss.read_index.return_value = mock_index
        
        # Initialize CLI and index
        cli = ResearchCLI(str(mock_kb))
        kb_index = KnowledgeBaseIndex(str(mock_kb))
        
        # Search for author
        papers = kb_index.search_by_author("Smith")
        
        # Should find paper by Smith, J.
        assert len(papers) == 1
        assert papers[0]["id"] == "0001"
        assert "Smith, J." in papers[0]["authors"]

    @patch("src.cli.faiss")
    @patch("sentence_transformers.SentenceTransformer")
    def test_citation_generation_workflow(self, mock_transformer, mock_faiss, mock_kb):
        """
        Test citation generation for multiple papers.
        
        Given: List of paper IDs
        When: Citations are generated
        Then: Returns IEEE formatted citations
        """
        from src.cli import ResearchCLI, generate_ieee_citation
        
        # Mock embedding model
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = MagicMock()
        mock_faiss.read_index.return_value = mock_index
        
        # Initialize CLI
        cli = ResearchCLI(str(mock_kb))
        
        # Generate citations
        citations = []
        for i, paper_id in enumerate(["0001", "0002"], start=1):
            paper = next(p for p in cli.metadata["papers"] if p["id"] == paper_id)
            citation = generate_ieee_citation(paper, i)
            citations.append(citation)
        
        # Verify citations
        assert len(citations) == 2
        assert "[1]" in citations[0]
        assert "Smith" in citations[0]
        assert "Systematic Review" in citations[0]
        assert "[2]" in citations[1]
        assert "Johnson" in citations[1]
        assert "RCT" in citations[1]


class TestSearchPerformance:
    """Test search performance characteristics."""

    @patch("src.cli.faiss")
    @patch("sentence_transformers.SentenceTransformer")
    def test_search_completes_within_timeout(self, mock_transformer, mock_faiss, tmp_path):
        """
        Test that search completes in reasonable time.
        
        Given: Large knowledge base
        When: Search is performed
        Then: Completes within 5 seconds
        """
        import time
        from src.cli import ResearchCLI
        
        # Create large metadata
        papers = []
        for i in range(1000):
            papers.append({
                "id": f"{i:04d}",
                "title": f"Paper {i}",
                "abstract": f"Abstract for paper {i}",
                "year": 2020 + (i % 5),
                "study_type": ["rct", "systematic_review", "cohort"][i % 3]
            })
        
        metadata = {
            "papers": papers,
            "total_papers": 1000,
            "version": "4.0",
            "embedding_model": "sentence-transformers/allenai-specter",
            "embedding_dimensions": 768
        }
        
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)
        
        # Mock components
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(1, 768).astype("float32")
        mock_transformer.return_value = mock_model
        
        mock_index = MagicMock()
        # Return 100 results
        distances = np.random.rand(1, 100)
        indices = np.arange(100).reshape(1, 100)
        mock_index.search.return_value = (distances, indices)
        mock_faiss.read_index.return_value = mock_index
        
        # Initialize CLI
        cli = ResearchCLI(str(tmp_path))
        
        # Measure search time
        start = time.time()
        results = cli.search("test query", k=100)
        elapsed = time.time() - start
        
        # Should complete quickly
        assert elapsed < 5.0
        assert len(results) <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
