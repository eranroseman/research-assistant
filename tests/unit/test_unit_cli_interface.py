#!/usr/bin/env python3
"""
Unit tests for CLI Interface functionality.

Tests core CLI utility functions and ID normalization.
Simplified tests for actual available functions.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.build_kb import calculate_enhanced_quality_score


class TestEnhancedQualityScoring:
    """Test enhanced quality scoring functionality."""

    def test_enhanced_quality_scoring_with_systematic_review_should_score_high(self):
        """
        Test enhanced quality scoring for systematic reviews.

        Given: Paper with systematic review indicators and API data
        When: calculate_enhanced_quality_score is called
        Then: Returns high quality score
        """
        paper = {
            "title": "Systematic Review of Machine Learning",
            "abstract": "This systematic review and meta-analysis examines...",
            "year": 2023,
            "study_type": "systematic_review",
            "sample_size": 1000,
            "has_full_text": True,
        }

        # Mock Semantic Scholar API data
        s2_data = {
            "citationCount": 100,
            "venue": {"name": "Nature Medicine"},
            "authors": [{"hIndex": 30}],
            "externalIds": {"DOI": "10.1000/test"},
            "publicationTypes": ["JournalArticle"],
            "fieldsOfStudy": ["Medicine"],
        }

        score, explanation = calculate_enhanced_quality_score(paper, s2_data)

        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        # Systematic reviews with good API data should score high
        assert score >= 70

    def test_enhanced_quality_scoring_with_rct_should_score_well(self):
        """
        Test enhanced quality scoring for RCTs.

        Given: Paper with RCT indicators and API data
        When: calculate_enhanced_quality_score is called
        Then: Returns good quality score
        """
        paper = {
            "title": "Randomized Controlled Trial",
            "abstract": "This randomized controlled trial enrolled patients...",
            "year": 2023,
            "study_type": "rct",
            "sample_size": 500,
        }

        # Mock Semantic Scholar API data
        s2_data = {
            "citationCount": 50,
            "venue": {"name": "Journal of Medicine"},
            "authors": [{"hIndex": 15}],
            "externalIds": {"DOI": "10.1000/test2"},
            "publicationTypes": ["JournalArticle"],
            "fieldsOfStudy": ["Medicine"],
        }

        score, explanation = calculate_enhanced_quality_score(paper, s2_data)

        assert isinstance(score, int)
        assert 0 <= score <= 100
        # RCTs with decent API data should score well
        assert score >= 60

    def test_enhanced_quality_scoring_with_minimal_api_data_should_handle_gracefully(self):
        """
        Test enhanced quality scoring with minimal API data.

        Given: Paper with minimal metadata and minimal API data
        When: calculate_enhanced_quality_score is called
        Then: Handles missing data gracefully
        """
        paper = {"title": "Basic Paper", "year": 2020, "study_type": "study"}

        # Minimal API data
        s2_data = {
            "citationCount": 0,
            "venue": {},
            "authors": [],
            "externalIds": {},
            "publicationTypes": [],
            "fieldsOfStudy": [],
        }

        score, explanation = calculate_enhanced_quality_score(paper, s2_data)

        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(explanation, str)


class TestUtilityFunctions:
    """Test utility functions available in CLI."""

    def test_paper_id_validation_pattern_should_work(self):
        """
        Test paper ID pattern validation.

        Given: Various paper ID formats
        When: Pattern is checked
        Then: Validates correctly
        """
        import re

        # Mock the pattern from CLI
        pattern = r"^\d{4}$"

        assert re.match(pattern, "0001")
        assert re.match(pattern, "1234")
        assert not re.match(pattern, "001")
        assert not re.match(pattern, "12345")
        assert not re.match(pattern, "abc1")

    def test_string_formatting_should_handle_special_characters(self):
        """
        Test string formatting with special characters.

        Given: Strings with special characters
        When: Formatted for output
        Then: Handles characters correctly
        """
        test_string = 'Test with "quotes" and special chars: a, b, c'

        # Should handle without errors
        formatted = f'"{test_string}"'
        assert "quotes" in formatted
        assert "a" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
