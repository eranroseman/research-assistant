#!/usr/bin/env python3
"""Enhanced quality scoring tests - supports only enhanced scoring system."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.build_kb import (
    calculate_quality_score,
    calculate_enhanced_quality_score,
    calculate_citation_impact_score,
    calculate_venue_prestige_score,
    calculate_author_authority_score,
    calculate_cross_validation_score
)


class TestEnhancedQualityScoring:
    """Tests for enhanced quality scoring with API data."""

    @pytest.mark.parametrize(
        ("citation_count", "expected_score"),
        [
            (0, 0),
            (1, 2),      # minimal
            (5, 4),      # few
            (20, 7),     # some  
            (50, 10),    # moderate
            (100, 15),   # good
            (500, 20),   # high
            (1000, 25),  # exceptional
            (2000, 25),  # exceptional (max)
        ]
    )
    def test_citation_impact_scoring_should_return_expected_scores(self, citation_count, expected_score):
        """Test citation impact scoring with various citation counts."""
        score = calculate_citation_impact_score(citation_count)
        assert score == expected_score

    @pytest.mark.parametrize(
        ("venue_name", "expected_score_range"),
        [
            ("Nature", 15),                    # Q1 tier
            ("Science", 15),                   # Q1 tier  
            ("Journal of Medicine", 12),       # Q2 tier
            ("IEEE Transactions on AI", 12),   # Q2 tier
            ("Some Journal", 8),               # Q3 tier
            ("Conference Proceedings", 8),     # Q3 tier
            ("Unknown Venue", 2),              # Unranked
            ("", 2),                          # Empty venue
        ]
    )
    def test_venue_prestige_scoring_should_return_expected_scores(self, venue_name, expected_score_range):
        """Test venue prestige scoring with different venue types."""
        venue_data = {"name": venue_name}
        score = calculate_venue_prestige_score(venue_data)
        assert score == expected_score_range

    @pytest.mark.parametrize(
        ("authors_data", "expected_score"),
        [
            ([], 0),                                          # No authors
            ([{"hIndex": 0}], 0),                            # No h-index
            ([{"hIndex": 1}], 2),                            # Early career
            ([{"hIndex": 5}], 4),                            # Emerging  
            ([{"hIndex": 15}], 6),                           # Experienced
            ([{"hIndex": 30}], 8),                           # Established
            ([{"hIndex": 50}], 10),                          # Renowned
            ([{"hIndex": 100}], 10),                         # Renowned (max)
            ([{"hIndex": 5}, {"hIndex": 30}], 8),            # Multiple authors (max h-index)
            ([{"hIndex": None}], 0),                         # None h-index
            ([{}], 0),                                       # Missing h-index field
        ]
    )
    def test_author_authority_scoring_should_return_expected_scores(self, authors_data, expected_score):
        """Test author authority scoring with various author data."""
        score = calculate_author_authority_score(authors_data)
        assert score == expected_score

    def test_cross_validation_scoring_should_award_points_for_completeness(self):
        """Test cross-validation scoring with complete paper data."""
        paper_data = {"study_type": "rct"}
        s2_data = {
            "externalIds": {"DOI": "10.1000/test", "PubMed": "123456"},
            "publicationTypes": ["JournalArticle"],
            "fieldsOfStudy": ["Medicine", "Computer Science"]
        }
        
        score = calculate_cross_validation_score(paper_data, s2_data)
        # Should get: external_ids(3) + pub_types(2) + fields(2) + high_quality_study(3) = 10
        assert score == 10

    def test_cross_validation_scoring_should_handle_minimal_data(self):
        """Test cross-validation scoring with minimal data."""
        paper_data = {"study_type": "case_report"}
        s2_data = {}
        
        score = calculate_cross_validation_score(paper_data, s2_data)
        assert score == 0  # No bonus points for minimal data

    def test_enhanced_quality_score_integration_should_combine_all_factors(self):
        """Test full enhanced quality scoring with realistic data."""
        paper_data = {
            "study_type": "rct",
            "year": 2023,
            "sample_size": 500,
            "has_full_text": True
        }
        
        s2_data = {
            "citationCount": 100,
            "venue": {"name": "Nature Medicine"},
            "authors": [{"hIndex": 30}],
            "externalIds": {"DOI": "10.1000/test"},
            "publicationTypes": ["JournalArticle"],
            "fieldsOfStudy": ["Medicine"]
        }
        
        score, explanation = calculate_enhanced_quality_score(paper_data, s2_data)
        
        # Should be high-quality score combining all factors
        assert score > 70  # Good quality threshold
        assert score <= 100  # Maximum possible
        assert "[Enhanced scoring]" in explanation

    def test_quality_score_should_require_valid_api_data(self):
        """Test that quality scoring requires valid API data (no fallback)."""
        paper_data = {
            "study_type": "rct",
            "year": 2023,
            "has_full_text": True
        }
        
        # Test with error in API data
        s2_data_with_error = {"error": "api_failure"}
        
        with pytest.raises(Exception, match="Enhanced quality scoring requires valid API data"):
            calculate_quality_score(paper_data, s2_data_with_error)

    def test_quality_score_should_require_api_data_parameter(self):
        """Test that quality scoring requires API data parameter."""
        paper_data = {
            "study_type": "rct",
            "year": 2023,
            "has_full_text": True
        }
        
        # Test with None API data
        with pytest.raises(Exception, match="Enhanced quality scoring requires valid API data"):
            calculate_quality_score(paper_data, None)

    def test_enhanced_quality_score_with_systematic_review_should_score_high(self):
        """Test enhanced quality scoring with systematic review."""
        paper_data = {
            "study_type": "systematic_review",
            "year": 2024,
            "sample_size": 1000,
            "has_full_text": True
        }
        
        s2_data = {
            "citationCount": 200,
            "venue": {"name": "Cochrane Reviews"},
            "authors": [{"hIndex": 50}],
            "externalIds": {"DOI": "10.1000/systematic", "PubMed": "987654"},
            "publicationTypes": ["JournalArticle"],
            "fieldsOfStudy": ["Medicine", "Health Sciences"]
        }
        
        score, explanation = calculate_enhanced_quality_score(paper_data, s2_data)
        
        # Should be high quality score for systematic review with good API data
        assert score >= 70  # Very good quality threshold
        assert score <= 100  # Maximum possible
        assert "[Enhanced scoring]" in explanation
        assert "systematic_review" in explanation.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
