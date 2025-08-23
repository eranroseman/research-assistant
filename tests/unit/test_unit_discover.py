#!/usr/bin/env python3
"""Unit tests for the discovery tool."""

import unittest
from unittest.mock import patch, Mock

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discover import (
    Paper,
    ScoredPaper,
    RateLimiter,
    generate_semantic_scholar_query,
    score_discovery_papers,
    calculate_keyword_relevance,
    assess_kb_coverage,
    generate_paper_list,
    generate_doi_lists,
)


class TestPaperDataStructures(unittest.TestCase):
    """Test paper data structures."""

    def test_paper_creation(self):
        """Test Paper dataclass creation."""
        paper = Paper(
            doi="10.1234/example",
            title="Test Paper",
            authors=["Author A", "Author B"],
            year=2023,
            abstract="Test abstract",
            citation_count=10,
            venue="Test Journal",
            url="https://example.com",
            source="semantic_scholar",
        )

        assert paper.doi == "10.1234/example"
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
        assert paper.year == 2023
        assert paper.citation_count == 10

    def test_scored_paper_creation(self):
        """Test ScoredPaper dataclass creation."""
        paper = Paper(
            doi="10.1234/example",
            title="Test Paper",
            authors=["Author A"],
            year=2023,
            abstract="Test abstract",
            citation_count=10,
            venue="Test Journal",
            url="https://example.com",
        )

        scored_paper = ScoredPaper(
            paper=paper,
            quality_score=85.0,
            relevance_score=90.0,
            overall_score=87.5,
            confidence="HIGH",
            reasoning="Test reasoning",
        )

        assert scored_paper.paper.title == "Test Paper"
        assert scored_paper.quality_score == 85.0
        assert scored_paper.confidence == "HIGH"


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality."""

    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(requests_per_second=1.0)
        assert limiter.min_interval == 1.0
        assert limiter.last_request_time == 0.0

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limiter_wait_needed(self, mock_sleep, mock_time):
        """Test rate limiter waits when needed."""
        mock_time.side_effect = [0.5, 1.5]  # First call returns 0.5, second returns 1.5

        limiter = RateLimiter(requests_per_second=1.0)
        limiter.last_request_time = 0.0

        limiter.wait_if_needed()

        mock_sleep.assert_called_once_with(0.5)  # Should wait 0.5 seconds

    @patch("time.time")
    @patch("time.sleep")
    def test_rate_limiter_no_wait_needed(self, mock_sleep, mock_time):
        """Test rate limiter doesn't wait when not needed."""
        mock_time.side_effect = [2.0, 2.0]

        limiter = RateLimiter(requests_per_second=1.0)
        limiter.last_request_time = 0.0

        limiter.wait_if_needed()

        mock_sleep.assert_not_called()


class TestSearchQueryGeneration(unittest.TestCase):
    """Test search query generation."""

    def test_basic_query_generation(self):
        """Test basic search query generation."""
        query = generate_semantic_scholar_query(
            keywords=["diabetes", "treatment"],
            year_from=2020,
            study_types=[],
            population_focus=None,
        )

        assert query.source == "semantic_scholar"
        assert "diabetes" in query.query_text
        assert "treatment" in query.query_text
        assert query.filters["year_from"] == 2020

    def test_query_with_population_focus(self):
        """Test query generation with population focus."""
        query = generate_semantic_scholar_query(
            keywords=["diabetes"],
            year_from=2020,
            study_types=[],
            population_focus="pediatric",
        )

        # Should include pediatric-related terms
        query_lower = query.query_text.lower()
        assert any(term in query_lower for term in ["children", "pediatric", "adolescent"])

    def test_query_with_study_types(self):
        """Test query generation with study types."""
        query = generate_semantic_scholar_query(
            keywords=["diabetes"],
            year_from=2020,
            study_types=["rct", "systematic_review"],
            population_focus=None,
        )

        assert "rct" in query.query_text
        assert "systematic_review" in query.query_text


class TestKeywordRelevance(unittest.TestCase):
    """Test keyword relevance calculation."""

    def test_perfect_match(self):
        """Test perfect keyword match."""
        paper = Paper(
            doi="10.1234/example",
            title="Diabetes Treatment Study",
            authors=["Author A"],
            year=2023,
            abstract="This study examines diabetes treatment effectiveness",
            citation_count=10,
            venue="Test Journal",
            url="https://example.com",
        )

        score = calculate_keyword_relevance(paper, ["diabetes", "treatment"])
        assert score == 100.0  # Both keywords in title and abstract

    def test_partial_match(self):
        """Test partial keyword match."""
        paper = Paper(
            doi="10.1234/example",
            title="Diabetes Study",
            authors=["Author A"],
            year=2023,
            abstract="This study examines diabetes management",
            citation_count=10,
            venue="Test Journal",
            url="https://example.com",
        )

        score = calculate_keyword_relevance(paper, ["diabetes", "treatment"])
        assert score > 0
        assert score < 100

    def test_no_match(self):
        """Test no keyword match."""
        paper = Paper(
            doi="10.1234/example",
            title="Cancer Research",
            authors=["Author A"],
            year=2023,
            abstract="This study examines cancer biology",
            citation_count=10,
            venue="Test Journal",
            url="https://example.com",
        )

        score = calculate_keyword_relevance(paper, ["diabetes", "treatment"])
        assert score == 0.0


class TestPaperScoring(unittest.TestCase):
    """Test paper scoring functionality."""

    @patch("discover.detect_study_type")
    @patch("discover.calculate_basic_quality_score")
    def test_score_discovery_papers(self, mock_quality_score, mock_study_type):
        """Test paper scoring."""
        mock_study_type.return_value = "rct"
        mock_quality_score.return_value = (85, "High quality RCT")

        paper = Paper(
            doi="10.1234/example",
            title="Diabetes RCT",
            authors=["Author A"],
            year=2023,
            abstract="Randomized controlled trial of diabetes treatment",
            citation_count=100,
            venue="Nature",
            url="https://example.com",
        )

        scored_papers = score_discovery_papers([paper], ["diabetes"], None)

        assert len(scored_papers) == 1
        scored_paper = scored_papers[0]
        assert scored_paper.confidence == "HIGH"
        assert scored_paper.overall_score > 80

    @patch("discover.detect_study_type")
    @patch("discover.calculate_basic_quality_score")
    def test_quality_threshold_filtering(self, mock_quality_score, mock_study_type):
        """Test quality threshold filtering."""
        mock_study_type.return_value = "case_report"
        mock_quality_score.return_value = (30, "Low quality case report")

        paper = Paper(
            doi="10.1234/example",
            title="Case Report",
            authors=["Author A"],
            year=2020,
            abstract="A case report",
            citation_count=1,
            venue="Unknown Journal",
            url="https://example.com",
        )

        # Should be filtered out with HIGH threshold
        scored_papers = score_discovery_papers([paper], ["case"], "HIGH")
        assert len(scored_papers) == 0

        # Should pass with LOW threshold
        scored_papers = score_discovery_papers([paper], ["case"], "LOW")
        assert len(scored_papers) == 1


class TestKBCoverageAssessment(unittest.TestCase):
    """Test KB coverage assessment."""

    @patch("discover.ResearchCLI")
    def test_excellent_coverage(self, mock_cli_class):
        """Test excellent KB coverage assessment."""
        mock_cli = Mock()
        mock_cli.search.return_value = [{}] * 50  # 50 papers found
        mock_cli_class.return_value = mock_cli

        paper = Paper(
            doi="10.1234/example",
            title="Test Paper",
            authors=["Author A"],
            year=2023,
            abstract="Test abstract",
            citation_count=10,
            venue="Test Journal",
            url="https://example.com",
        )

        scored_paper = ScoredPaper(
            paper=paper,
            quality_score=85.0,
            relevance_score=90.0,
            overall_score=87.5,
            confidence="HIGH",
            reasoning="Test",
        )

        coverage = assess_kb_coverage(["test"], [scored_paper])

        assert "\U0001f7e2 EXCELLENT" in coverage["status"]
        assert coverage["kb_count"] == 50

    @patch("discover.ResearchCLI")
    def test_needs_update_coverage(self, mock_cli_class):
        """Test needs update KB coverage assessment."""
        mock_cli = Mock()
        mock_cli.search.return_value = [{}] * 5  # Only 5 papers found
        mock_cli_class.return_value = mock_cli

        # Create high-impact missing papers
        papers = []
        for i in range(15):
            paper = Paper(
                doi=f"10.1234/example{i}",
                title=f"High Impact Paper {i}",
                authors=["Author A"],
                year=2023,
                abstract="Test abstract",
                citation_count=100,  # High citations
                venue="Nature",
                url="https://example.com",
            )

            scored_paper = ScoredPaper(
                paper=paper,
                quality_score=85.0,
                relevance_score=90.0,
                overall_score=87.5,
                confidence="HIGH",
                reasoning="Test",
            )
            papers.append(scored_paper)

        coverage = assess_kb_coverage(["test"], papers)

        assert "🔴 NEEDS UPDATE" in coverage["status"]
        assert coverage["kb_count"] == 5
        assert coverage["high_impact_missing"] == 15


class TestReportGeneration(unittest.TestCase):
    """Test report generation functionality."""

    def test_generate_paper_list_empty(self):
        """Test paper list generation with empty list."""
        result = generate_paper_list([])
        assert result == "No papers found in this category."

    def test_generate_paper_list_with_papers(self):
        """Test paper list generation with papers."""
        paper = Paper(
            doi="10.1234/example",
            title="Test Paper",
            authors=["Author A", "Author B"],
            year=2023,
            abstract="Test abstract content",
            citation_count=10,
            venue="Test Journal",
            url="https://example.com",
        )

        scored_paper = ScoredPaper(
            paper=paper,
            quality_score=85.0,
            relevance_score=90.0,
            overall_score=87.5,
            confidence="HIGH",
            reasoning="High quality study",
        )

        result = generate_paper_list([scored_paper])

        assert "Test Paper" in result
        assert "10.1234/example" in result
        assert "Author A, Author B" in result
        assert "2023" in result
        assert "85/100" in result

    def test_generate_doi_lists(self):
        """Test DOI list generation."""
        paper1 = Paper(
            doi="10.1234/example1",
            title="Paper 1",
            authors=["Author A"],
            year=2023,
            abstract="Abstract 1",
            citation_count=10,
            venue="Journal 1",
            url="https://example.com/1",
        )

        paper2 = Paper(
            doi="s2-12345",  # Semantic Scholar ID, should be excluded
            title="Paper 2",
            authors=["Author B"],
            year=2023,
            abstract="Abstract 2",
            citation_count=5,
            venue="Journal 2",
            url="https://example.com/2",
        )

        scored1 = ScoredPaper(
            paper=paper1,
            quality_score=85.0,
            relevance_score=90.0,
            overall_score=87.5,
            confidence="HIGH",
            reasoning="Good",
        )

        scored2 = ScoredPaper(
            paper=paper2,
            quality_score=75.0,
            relevance_score=80.0,
            overall_score=77.5,
            confidence="MEDIUM",
            reasoning="OK",
        )

        result = generate_doi_lists([scored1], [scored2], [])

        assert "10.1234/example1" in result
        assert "s2-12345" not in result  # Should be filtered out
        assert "High Confidence Papers (1 DOIs)" in result


if __name__ == "__main__":
    unittest.main()
