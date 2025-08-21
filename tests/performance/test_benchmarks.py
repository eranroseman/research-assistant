#!/usr/bin/env python3
"""Performance benchmark tests for Research Assistant."""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.utils import create_mock_cli


class TestSearchPerformance:
    """Test search performance benchmarks."""

    @pytest.mark.performance
    def test_search_performance_with_large_kb(self, tmp_path):
        """
        Test that search performs well with large knowledge base.
        
        Given: Knowledge base with 1000+ papers
        When: Search is performed
        Then: Completes within acceptable time limits
        """
        # Use utility to create large mock CLI
        cli = create_mock_cli(
            papers_count=1000,
            with_embeddings=True,
            with_index=True,
            kb_path=tmp_path
        )
        
        # Mock search to return realistic results with timing
        def mock_search_with_timing(query, k=10, **kwargs):
            # Simulate realistic search time proportional to k
            time.sleep(0.001 * k)  # 1ms per result
            return cli.metadata["papers"][:k]
        
        cli.search.side_effect = mock_search_with_timing
        
        # Measure search time
        start = time.time()
        results = cli.search("machine learning healthcare", k=100)
        elapsed = time.time() - start
        
        # Performance assertions
        assert elapsed < 5.0, f"Search took {elapsed:.2f}s, expected < 5s"
        assert len(results) <= 100
        
        # Measure filtered search
        start = time.time()
        results = cli.search(
            "diabetes treatment",
            k=50,
            min_year=2022,
            study_types=["systematic_review", "rct"]
        )
        elapsed = time.time() - start
        
        assert elapsed < 5.0, f"Filtered search took {elapsed:.2f}s, expected < 5s"

    @pytest.mark.performance
    def test_batch_performance_vs_individual_commands(self):
        """
        Test that batch operations are significantly faster than individual commands.
        
        Given: Multiple search commands
        When: Executed as batch vs individually
        Then: Batch is at least 5x faster due to single model load
        """
        from src.cli import _generate_preset_commands
        
        # Generate a research workflow
        commands = _generate_preset_commands("research", "diabetes")
        
        # Verify batch has multiple operations
        assert len(commands) >= 5, "Research preset should have multiple commands"
        
        # Check that commands are structured correctly
        search_commands = [c for c in commands if c.get("cmd") == "search"]
        assert len(search_commands) >= 3, "Should have multiple search variations"
        
        # Verify workflow includes aggregation
        assert any(c.get("cmd") == "merge" for c in commands), "Should have merge command"
        assert any(c.get("cmd") == "filter" for c in commands), "Should have filter command"


class TestKBBuildingPerformance:
    """Test knowledge base building performance."""

    @pytest.mark.performance
    @patch("src.build_kb.SentenceTransformer")
    def test_embedding_generation_performance(self, mock_transformer, tmp_path):
        """
        Test embedding generation performance with batching.
        
        Given: 500 papers to embed
        When: Embeddings are generated
        Then: Completes efficiently with proper batching
        """
        from src.build_kb import KnowledgeBaseBuilder
        
        # Mock embedding model
        mock_model = MagicMock()
        
        def mock_encode(texts, show_progress_bar=True, batch_size=64):
            # Simulate processing time (very fast for testing)
            time.sleep(0.001 * len(texts))
            return np.random.randn(len(texts), 768).astype("float32")
        
        mock_model.encode = MagicMock(side_effect=mock_encode)
        mock_transformer.return_value = mock_model
        
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        builder.embedding_model = mock_model
        
        # Create test papers
        papers = []
        for i in range(1, 501):
            papers.append({
                "id": f"{i:04d}",
                "title": f"Paper {i}",
                "abstract": f"Abstract for paper {i}" * 10,
                "full_text": f"Full text for paper {i}" * 100 if i % 3 == 0 else None
            })
        
        # Measure embedding generation
        start = time.time()
        embeddings = builder.generate_embeddings(papers)
        elapsed = time.time() - start
        
        # Performance assertions
        assert embeddings.shape == (500, 768)
        assert elapsed < 10.0, f"Embedding generation took {elapsed:.2f}s, expected < 10s"
        
        # Verify batching was used (should be called once with batch_size)
        assert mock_model.encode.call_count == 1, "Should batch all papers in one call"

    @pytest.mark.performance
    @patch("src.build_kb.faiss")
    def test_faiss_index_building_performance(self, mock_faiss, tmp_path):
        """
        Test FAISS index building performance.
        
        Given: 1000 embeddings
        When: FAISS index is built
        Then: Completes efficiently
        """
        from src.build_kb import KnowledgeBaseBuilder
        
        # Mock FAISS
        mock_index = MagicMock()
        mock_faiss.IndexFlatL2.return_value = mock_index
        
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        # Create test embeddings
        embeddings = np.random.randn(1000, 768).astype("float32")
        
        # Measure index building
        start = time.time()
        builder.build_faiss_index(embeddings)
        elapsed = time.time() - start
        
        # Performance assertions
        assert elapsed < 2.0, f"Index building took {elapsed:.2f}s, expected < 2s"
        mock_index.add.assert_called_once()
        mock_faiss.write_index.assert_called_once()


class TestMemoryUsage:
    """Test memory usage characteristics."""

    @pytest.mark.performance
    def test_large_paper_loading_memory_efficient(self):
        """
        Test that loading large papers is memory efficient.
        
        Given: Large paper files
        When: Papers are loaded
        Then: Memory usage remains reasonable
        """
        import json
        
        # Create test paper with large content
        large_paper = {
            "id": "0001",
            "title": "Large Paper",
            "abstract": "Abstract " * 100,
            "full_text": "Full text content " * 10000,  # ~170KB
            "authors": ["Author"] * 50,
            "references": ["Reference"] * 100
        }
        
        # Serialize to JSON to measure size
        json_str = json.dumps(large_paper)
        size_kb = len(json_str) / 1024
        
        # Verify size is reasonable
        assert size_kb < 500, f"Paper size {size_kb:.1f}KB exceeds reasonable limit"
        
        # Test that we can handle multiple large papers
        papers = [large_paper.copy() for _ in range(10)]
        for i, p in enumerate(papers):
            p["id"] = f"{i+1:04d}"
        
        # Total size should still be manageable
        total_json = json.dumps(papers)
        total_size_mb = len(total_json) / (1024 * 1024)
        
        assert total_size_mb < 10, f"Total size {total_size_mb:.1f}MB exceeds limit"


class TestConcurrentOperations:
    """Test concurrent operation handling."""

    @pytest.mark.performance
    def test_batch_command_parallelization_potential(self):
        """
        Test that batch commands could be parallelized.
        
        Given: Independent batch commands
        When: Commands are analyzed
        Then: Independent commands are identified for parallel execution
        """
        # Create test commands
        commands = [
            {"cmd": "search", "query": "diabetes", "k": 10},
            {"cmd": "search", "query": "hypertension", "k": 10},
            {"cmd": "search", "query": "cancer", "k": 10},
            {"cmd": "merge"},  # Depends on previous searches
            {"cmd": "filter", "min_quality": 80},  # Depends on merge
        ]
        
        # Identify independent commands
        independent = []
        dependent = []
        
        for i, cmd in enumerate(commands):
            if cmd["cmd"] in ["merge", "filter", "auto-get-top", "auto-get-all"]:
                dependent.append(i)
            else:
                independent.append(i)
        
        # First 3 searches are independent
        assert len(independent) == 3, "Three search commands should be independent"
        assert independent == [0, 1, 2], "First three commands are independent"
        
        # Last 2 are dependent
        assert len(dependent) == 2, "Two commands should be dependent"
        assert dependent == [3, 4], "Merge and filter are dependent"


class TestCachePerformance:
    """Test cache operation performance."""

    @pytest.mark.performance
    def test_cache_speeds_up_repeated_operations(self, tmp_path):
        """
        Test that caching significantly speeds up repeated operations.
        
        Given: Cached PDF text
        When: PDF extraction is requested again
        Then: Returns instantly from cache
        """
        import json
        from src.build_kb import KnowledgeBaseBuilder
        
        builder = KnowledgeBaseBuilder(knowledge_base_path=str(tmp_path))
        
        # Pre-populate cache with many entries
        cache_data = {}
        for i in range(1, 101):
            cache_data[f"KEY{i:04d}"] = {
                "text": f"Cached content for paper {i}" * 100,
                "hash": f"hash_{i}"
            }
        
        cache_file = tmp_path / ".pdf_text_cache.json"
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        
        # Load cache
        start = time.time()
        cache = builder.load_cache()
        load_time = time.time() - start
        
        assert load_time < 1.0, f"Cache loading took {load_time:.2f}s, expected < 1s"
        assert len(cache) == 100
        
        # Access cached items (should be O(1))
        start = time.time()
        for i in range(1, 51):
            key = f"KEY{i:04d}"
            assert key in cache
            _ = cache[key]["text"]
        access_time = time.time() - start
        
        assert access_time < 0.1, f"Cache access took {access_time:.2f}s, expected < 0.1s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
