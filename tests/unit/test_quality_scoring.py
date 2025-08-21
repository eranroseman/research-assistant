#!/usr/bin/env python3
"""Parametrized tests for quality scoring - replacing repetitive individual tests."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli import estimate_paper_quality


class TestQualityScoreParametrized:
    """Parametrized tests for paper quality scoring."""
    
    @pytest.mark.parametrize(("study_type", "expected_score", "expected_explanation_text"), [
        # Study type scoring tests
        ("systematic_review", 85, "systematic review"),
        ("meta_analysis", 85, "meta analysis"),
        ("rct", 75, "rct"),
        ("cohort", 65, "cohort"),
        ("case_control", 60, "case control"),
        ("cross_sectional", 55, "cross sectional"),
        ("case_report", 50, "case report"),
        ("unknown", 50, "unknown"),
        
        # Edge cases
        ("SYSTEMATIC_REVIEW", 85, "systematic review"),  # Case insensitive
        ("", 50, "unknown"),  # Empty string
        (None, 50, "unknown"),  # None value
    ])
    def test_quality_score_by_study_type(self, study_type, expected_score, expected_explanation_text):
        """Test quality scoring for different study types."""
        paper = {
            "study_type": study_type,
            "year": 2019,  # Old enough to not get recency bonus
            "has_full_text": False
        }
        
        score, explanation = estimate_paper_quality(paper)
        
        assert score == expected_score
        assert expected_explanation_text in explanation.lower()
    
    @pytest.mark.parametrize(("year", "expected_recency_bonus"), [
        # Recency scoring tests
        (2025, 10),  # Current year gets full bonus
        (2024, 8),   # 1 year old
        (2023, 6),   # 2 years old  
        (2022, 4),   # 3 years old
        (2021, 2),   # 4 years old
        (2020, 0),   # 5+ years old gets no bonus
        (2015, 0),   # Very old paper
        (1990, 0),   # Ancient paper
        
        # Edge cases
        (2030, 10),  # Future year (shouldn't happen but handle gracefully)
        (None, 0),   # Missing year
    ])
    def test_quality_score_recency_bonus(self, year, expected_recency_bonus):
        """Test recency bonus calculation."""
        paper = {
            "study_type": "rct",  # Fixed study type for consistent base score
            "year": year,
            "has_full_text": False
        }
        
        score, explanation = estimate_paper_quality(paper)
        
        expected_total = 75 + expected_recency_bonus  # 75 = base(50) + rct(25)
        assert score == expected_total
        
        if expected_recency_bonus > 0:
            assert "recent" in explanation.lower() or "recency" in explanation.lower()
    
    @pytest.mark.parametrize(("sample_size", "expected_bonus", "expected_in_explanation"), [
        # Sample size scoring tests
        (1000, 10, "large sample"),
        (500, 8, "substantial sample"),
        (250, 6, "moderate sample"),
        (100, 4, "reasonable sample"),
        (50, 2, "small sample"),
        (25, 0, ""),  # Too small for bonus
        (10, 0, ""),
        (None, 0, ""),  # Missing sample size
        (0, 0, ""),     # Zero sample size
        
        # Edge cases
        (5000, 10, "large sample"),  # Very large gets max bonus
        (-1, 0, ""),  # Negative (invalid)
    ])
    def test_quality_score_sample_size_bonus(self, sample_size, expected_bonus, expected_in_explanation):
        """Test sample size bonus calculation."""
        paper = {
            "study_type": "rct",
            "year": 2019,  # No recency bonus
            "sample_size": sample_size,
            "has_full_text": False
        }
        
        score, explanation = estimate_paper_quality(paper)
        
        expected_total = 75 + expected_bonus  # 75 = base(50) + rct(25)
        assert score == expected_total
        
        if expected_in_explanation:
            assert expected_in_explanation in explanation.lower()
    
    @pytest.mark.parametrize(("has_full_text", "expected_bonus"), [
        # Full text availability tests
        (True, 5),
        (False, 0),
        (None, 0),  # Missing field
    ])
    def test_quality_score_full_text_bonus(self, has_full_text, expected_bonus):
        """Test full text availability bonus."""
        paper = {
            "study_type": "rct",
            "year": 2019,  # No recency bonus
            "has_full_text": has_full_text
        }
        
        score, explanation = estimate_paper_quality(paper)
        
        expected_total = 75 + expected_bonus  # 75 = base(50) + rct(25)
        assert score == expected_total
        
        if expected_bonus > 0:
            assert "full text" in explanation.lower()
    
    @pytest.mark.parametrize(("paper_data", "expected_score_range", "required_explanation_terms"), [
        # Combined scoring tests
        ({
            "study_type": "systematic_review",
            "year": 2024,
            "sample_size": 1000,
            "has_full_text": True
        }, (108, 110), ["systematic review", "recent", "large sample", "full text"]),
        
        ({
            "study_type": "case_report",
            "year": 2015,
            "has_full_text": False
        }, (50, 50), ["case report"]),
        
        ({
            "study_type": "rct",
            "year": 2023,
            "sample_size": 500,
            "has_full_text": True
        }, (94, 96), ["rct", "recent", "substantial sample", "full text"]),
        
        # Missing fields
        ({}, (50, 50), ["unknown"]),
        
        # Only some fields
        ({"study_type": "cohort", "year": 2024}, (73, 73), ["cohort", "recent"]),
    ])
    def test_quality_score_combinations(self, paper_data, expected_score_range, required_explanation_terms):
        """Test quality scoring with various field combinations."""
        score, explanation = estimate_paper_quality(paper_data)
        
        min_score, max_score = expected_score_range
        assert min_score <= score <= max_score, f"Score {score} not in range {expected_score_range}"
        
        for term in required_explanation_terms:
            assert term.lower() in explanation.lower(), f"'{term}' not found in: {explanation}"
    
    def test_quality_score_bounds(self):
        """Test that quality scores stay within reasonable bounds."""
        # Maximum possible score
        max_paper = {
            "study_type": "systematic_review",
            "year": 2025,
            "sample_size": 10000,
            "has_full_text": True
        }
        max_score, _ = estimate_paper_quality(max_paper)
        assert max_score <= 110  # Should not exceed reasonable maximum
        
        # Minimum possible score
        min_paper = {
            "study_type": "case_report",
            "year": 1990,
            "has_full_text": False
        }
        min_score, _ = estimate_paper_quality(min_paper)
        assert min_score >= 50  # Should have reasonable minimum
        assert min_score <= max_score  # Sanity check
