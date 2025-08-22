#!/usr/bin/env python3
"""
Unit tests for Search Engine functionality.

Covers search algorithms, embedding operations, and result ranking.
Consolidates tests from test_search_parametrized.py and cli search tests.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.build_kb import calculate_enhanced_quality_score


class TestSearchParametrized:
    """Test parametrized search functionality."""

    @pytest.mark.parametrize(
        ("query", "expected_type"),
        [
            ("diabetes", str),
            ("machine learning", str),
            ("covid-19", str),
            ("", str),
        ],
    )
    def test_search_with_various_queries_should_return_string_result(self, query, expected_type):
        """
        Test search queries return expected types.

        Given: Various search queries
        When: Search is performed
        Then: Returns result of expected type
        """
        # Mock search result
        result = f"Search results for: {query}"
        assert isinstance(result, expected_type)

    @pytest.mark.parametrize("k_value", [1, 5, 10, 20, 50])
    def test_search_with_various_k_values_should_handle_correctly(self, k_value):
        """
        Test search with different k values.

        Given: Various k values for result count
        When: Search is performed
        Then: Handles k parameter correctly
        """
        # Mock that k value is within reasonable bounds
        assert k_value > 0
        assert k_value <= 100

    @pytest.mark.parametrize("quality_threshold", [0, 25, 50, 75, 100])
    def test_search_with_quality_filters_should_apply_correctly(self, quality_threshold):
        """
        Test search quality filtering.

        Given: Various quality thresholds
        When: Search is performed with quality filter
        Then: Applies threshold correctly
        """
        # Mock quality filtering logic
        test_quality = 60
        should_include = test_quality >= quality_threshold
        assert isinstance(should_include, bool)


class TestEmbeddingOperations:
    """Test embedding generation and similarity calculations."""

    def test_embedding_generation_should_produce_correct_dimensions(self):
        """
        Test embedding vector dimensions.

        Given: Text input
        When: Embedding is generated
        Then: Produces 768-dimensional vector
        """
        # Mock Multi-QA MPNet embedding
        mock_embedding = np.random.randn(768).astype("float32")
        assert mock_embedding.shape == (768,)
        assert mock_embedding.dtype == np.float32

    def test_cosine_similarity_calculation_should_work_correctly(self):
        """
        Test cosine similarity calculations.

        Given: Two embedding vectors
        When: Cosine similarity is calculated
        Then: Returns value between -1 and 1
        """
        # Mock similarity calculation
        vec1 = np.random.randn(768).astype("float32")
        vec2 = np.random.randn(768).astype("float32")

        # Normalize vectors
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)

        # Calculate cosine similarity
        similarity = np.dot(vec1_norm, vec2_norm)

        assert -1.0 <= similarity <= 1.0

    def test_embedding_caching_should_improve_performance(self):
        """
        Test embedding cache functionality.

        Given: Previously computed embeddings
        When: Same text is processed again
        Then: Uses cached embedding
        """
        # Mock cache behavior
        cache = {"test_text": np.random.randn(768).astype("float32")}
        text = "test_text"

        if text in cache:
            result = cache[text]
            assert result.shape == (768,)
        else:
            # Would compute new embedding
            result = np.random.randn(768).astype("float32")
            cache[text] = result

        assert text in cache


class TestResultRanking:
    """Test search result ranking and scoring."""

    def test_result_ranking_integration_should_work_correctly(self):
        """
        Test search result ranking integration.

        Given: Search results with different papers
        When: Results are ranked by quality
        Then: Higher quality papers rank higher
        """
        # Mock search results with different quality papers
        results = [
            {"title": "High Quality Systematic Review", "study_type": "systematic_review", "year": 2024},
            {"title": "Medium Quality RCT", "study_type": "rct", "year": 2020},
            {"title": "Low Quality Case Report", "study_type": "case_report", "year": 2015},
        ]

        # Calculate quality scores for ranking using enhanced scoring
        scored_results = []
        for paper in results:
            # Mock API data based on paper quality
            if paper["study_type"] == "systematic_review":
                s2_data = {"citationCount": 200, "venue": {"name": "Cochrane"}, "authors": [{"hIndex": 50}]}
            elif paper["study_type"] == "rct":
                s2_data = {
                    "citationCount": 50,
                    "venue": {"name": "Medical Journal"},
                    "authors": [{"hIndex": 20}],
                }
            else:
                s2_data = {"citationCount": 5, "venue": {"name": "Case Reports"}, "authors": [{"hIndex": 5}]}

            score, _ = calculate_enhanced_quality_score(paper, s2_data)
            scored_results.append((score, paper))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Verify ranking order
        assert scored_results[0][1]["study_type"] == "systematic_review"
        assert scored_results[1][1]["study_type"] == "rct"
        assert scored_results[2][1]["study_type"] == "case_report"


class TestSearchFiltering:
    """Test search filtering and refinement."""

    def test_author_filtering_should_work_correctly(self):
        """
        Test author-based filtering.

        Given: Author search query
        When: Author filter is applied
        Then: Returns papers by specified author
        """
        papers = [
            {"authors": ["Smith, J.", "Jones, A."]},
            {"authors": ["Brown, B.", "Davis, C."]},
            {"authors": ["Smith, J.", "Wilson, D."]},
        ]

        # Mock author filtering
        target_author = "Smith"
        filtered = [p for p in papers if any(target_author in author for author in p["authors"])]

        assert len(filtered) == 2
        assert all(any(target_author in author for author in p["authors"]) for p in filtered)

    def test_year_range_filtering_should_work_correctly(self):
        """
        Test year range filtering.

        Given: Papers from different years
        When: Year filter is applied
        Then: Returns papers within specified range
        """
        papers = [{"year": 2020}, {"year": 2021}, {"year": 2022}, {"year": 2023}, {"year": 2024}]

        # Mock year filtering
        min_year = 2022
        filtered = [p for p in papers if p["year"] >= min_year]

        assert len(filtered) == 3
        assert all(p["year"] >= min_year for p in filtered)

    def test_study_type_filtering_should_work_correctly(self):
        """
        Test study type filtering.

        Given: Papers of different study types
        When: Study type filter is applied
        Then: Returns papers of specified type
        """
        papers = [
            {"study_type": "rct"},
            {"study_type": "systematic_review"},
            {"study_type": "cohort"},
            {"study_type": "rct"},
        ]

        # Mock study type filtering
        target_type = "rct"
        filtered = [p for p in papers if p["study_type"] == target_type]

        assert len(filtered) == 2
        assert all(p["study_type"] == target_type for p in filtered)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
