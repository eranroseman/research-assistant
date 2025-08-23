#!/usr/bin/env python3
"""Integration tests for the discovery tool."""

import unittest
from unittest.mock import patch, Mock
from pathlib import Path
import tempfile
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discover import (
    discover_papers,
    SemanticScholarDiscovery,
    generate_discovery_report,
    main,
)


class TestSemanticScholarDiscoveryIntegration(unittest.TestCase):
    """Integration tests for Semantic Scholar discovery."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_api_response = {
            "data": [
                {
                    "paperId": "12345",
                    "title": "Diabetes Management in Primary Care",
                    "authors": [{"name": "Dr. Smith"}, {"name": "Dr. Johnson"}],
                    "year": 2023,
                    "abstract": "This study examines diabetes management strategies in primary care settings.",
                    "citationCount": 45,
                    "venue": "Journal of Primary Care",
                    "externalIds": {"DOI": "10.1234/example.2023.001"},
                    "url": "https://semanticscholar.org/paper/12345",
                },
                {
                    "paperId": "67890",
                    "title": "Mobile Health Apps for Diabetes Monitoring",
                    "authors": [{"name": "Dr. Wilson"}, {"name": "Dr. Brown"}, {"name": "Dr. Davis"}],
                    "year": 2024,
                    "abstract": "Evaluation of mobile health applications for continuous glucose monitoring.",
                    "citationCount": 28,
                    "venue": "Digital Health Journal",
                    "externalIds": {"DOI": "10.5678/mhealth.2024.002"},
                    "url": "https://semanticscholar.org/paper/67890",
                },
            ]
        }

    @patch("discover.requests.get")
    @patch("discover.KnowledgeBaseIndex")
    def test_semantic_scholar_discovery_success(self, mock_kb_index, mock_requests_get):
        """Test successful Semantic Scholar API integration."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_api_response
        mock_requests_get.return_value = mock_response

        # Mock KB index for DOI filtering
        mock_kb_index.return_value.papers = [
            {"doi": "10.9999/existing.paper"}  # Different DOI, won't filter out test papers
        ]

        # Initialize discovery service
        discovery = SemanticScholarDiscovery(include_kb_papers=False)

        # Create search query
        from discover import SearchQuery

        query = SearchQuery(
            query_text='"diabetes" OR "management"', filters={"year_from": 2020, "limit": 100}
        )

        # Execute search
        papers = discovery.search_papers(query)

        # Verify results
        assert len(papers) == 2

        # Check first paper
        paper1 = papers[0]
        assert paper1.title == "Diabetes Management in Primary Care"
        assert paper1.doi == "10.1234/example.2023.001"
        assert len(paper1.authors) == 2
        assert paper1.year == 2023
        assert paper1.citation_count == 45

        # Check second paper
        paper2 = papers[1]
        assert paper2.title == "Mobile Health Apps for Diabetes Monitoring"
        assert paper2.doi == "10.5678/mhealth.2024.002"
        assert len(paper2.authors) == 3

    @patch("discover.requests.get")
    @patch("discover.KnowledgeBaseIndex")
    def test_kb_filtering_excludes_existing_papers(self, mock_kb_index, mock_requests_get):
        """Test KB filtering excludes existing papers."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_api_response
        mock_requests_get.return_value = mock_response

        # Mock KB index with one of the test papers
        mock_kb_index.return_value.papers = [
            {"doi": "10.1234/example.2023.001"}  # Same as first test paper
        ]

        # Initialize discovery service with KB filtering
        discovery = SemanticScholarDiscovery(include_kb_papers=False)

        # Create search query
        from discover import SearchQuery

        query = SearchQuery(query_text='"diabetes"', filters={"year_from": 2020, "limit": 100})

        # Execute search
        papers = discovery.search_papers(query)

        # Should only have one paper (the second one)
        assert len(papers) == 1
        assert papers[0].title == "Mobile Health Apps for Diabetes Monitoring"

    @patch("discover.requests.get")
    def test_api_error_handling(self, mock_requests_get):
        """Test API error handling."""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 429  # Rate limited
        mock_response.text = "Rate limit exceeded"
        mock_requests_get.return_value = mock_response

        # Initialize discovery service
        discovery = SemanticScholarDiscovery(include_kb_papers=True)

        # Create search query
        from discover import SearchQuery

        query = SearchQuery(query_text='"diabetes"', filters={"year_from": 2020, "limit": 100})

        # Execute search - should handle error gracefully
        papers = discovery.search_papers(query)

        # Should return empty list on error
        assert len(papers) == 0

    def test_paper_filtering(self):
        """Test client-side paper filtering."""
        # Create test papers
        from discover import Paper

        papers = [
            Paper(
                doi="10.1234/old",
                title="Old Paper",
                authors=["Author A"],
                year=2018,  # Before year_from filter
                abstract="Old research",
                citation_count=5,
                venue="Old Journal",
                url="https://example.com/old",
            ),
            Paper(
                doi="10.1234/new",
                title="New Paper",
                authors=["Author B"],
                year=2023,  # After year_from filter
                abstract="New research",
                citation_count=50,
                venue="New Journal",
                url="https://example.com/new",
            ),
            Paper(
                doi="10.1234/low_citations",
                title="Low Citations Paper",
                authors=["Author C"],
                year=2023,
                abstract="Research with few citations",
                citation_count=1,  # Below min_citations
                venue="Some Journal",
                url="https://example.com/low",
            ),
        ]

        # Initialize discovery service
        discovery = SemanticScholarDiscovery(include_kb_papers=True)

        # Test filtering
        filters = {"year_from": 2020, "min_citations": 10, "study_types": []}

        filtered_papers = discovery._apply_filters(papers, filters)

        # Should only have the new paper with sufficient citations
        assert len(filtered_papers) == 1
        assert filtered_papers[0].title == "New Paper"


class TestDiscoveryWorkflowIntegration(unittest.TestCase):
    """Integration tests for complete discovery workflow."""

    @patch("discover.SemanticScholarDiscovery")
    @patch("discover.ResearchCLI")
    def test_full_discovery_workflow(self, mock_cli_class, mock_discovery_class):
        """Test complete discovery workflow."""
        # Mock discovery results
        from discover import Paper

        mock_papers = [
            Paper(
                doi="10.1234/test1",
                title="Test Paper 1",
                authors=["Author A"],
                year=2023,
                abstract="Test abstract 1",
                citation_count=100,
                venue="Nature",
                url="https://example.com/1",
            ),
            Paper(
                doi="10.1234/test2",
                title="Test Paper 2",
                authors=["Author B"],
                year=2022,
                abstract="Test abstract 2",
                citation_count=50,
                venue="Science",
                url="https://example.com/2",
            ),
        ]

        mock_discovery = Mock()
        mock_discovery.search_papers.return_value = mock_papers
        mock_discovery_class.return_value = mock_discovery

        # Mock KB search results
        mock_cli = Mock()
        mock_cli.search.return_value = [{}] * 30  # 30 KB papers
        mock_cli_class.return_value = mock_cli

        # Execute discovery
        results = discover_papers(
            keywords=["test"],
            year_from=2020,
            study_types=[],
            min_citations=0,
            limit=10,
            quality_threshold=None,
            author_filter=[],
            population_focus=None,
            include_kb_papers=False,
            source="semantic_scholar",
        )

        # Verify results structure
        assert results.papers is not None
        assert results.coverage_status is not None
        assert results.search_params is not None
        assert results.performance_metrics is not None

        # Check search parameters
        assert results.search_params["keywords"] == ["test"]
        assert results.search_params["year_from"] == 2020
        assert results.search_params["source"] == "semantic_scholar"

        # Check coverage status
        assert "status" in results.coverage_status
        assert "kb_count" in results.coverage_status
        assert results.coverage_status["kb_count"] == 30


class TestReportGenerationIntegration(unittest.TestCase):
    """Integration tests for report generation."""

    def test_complete_report_generation(self):
        """Test complete report generation."""
        from discover import Paper, ScoredPaper, DiscoveryResults

        # Create test data
        paper = Paper(
            doi="10.1234/test",
            title="Test Research Paper",
            authors=["Dr. Alice Smith", "Dr. Bob Johnson", "Dr. Carol Williams", "Dr. David Brown"],
            year=2023,
            abstract="This is a comprehensive test abstract that describes the methodology and findings of our research study.",
            citation_count=75,
            venue="Journal of Test Research",
            url="https://example.com/test",
        )

        scored_paper = ScoredPaper(
            paper=paper,
            quality_score=88.0,
            relevance_score=92.0,
            overall_score=90.0,
            confidence="HIGH",
            reasoning="High quality recent study with good methodology",
        )

        results = DiscoveryResults(
            papers=[scored_paper],
            coverage_status={
                "status": "🟡 ADEQUATE",
                "message": "25 KB papers found. Consider adding recent papers.",
                "recommendation": "Consider updating for latest developments",
                "kb_count": 25,
                "discovery_count": 1,
                "high_impact_missing": 1,
                "recent_missing": 1,
            },
            search_params={
                "keywords": ["test", "research"],
                "year_from": 2020,
                "study_types": ["rct"],
                "min_citations": 10,
                "limit": 50,
                "quality_threshold": "HIGH",
                "author_filter": [],
                "population_focus": None,
                "include_kb_papers": False,
                "source": "semantic_scholar",
            },
            performance_metrics={
                "total_time_seconds": 5.2,
                "papers_found": 100,
                "papers_returned": 1,
                "kb_papers_excluded": 5,
            },
        )

        # Generate report
        report = generate_discovery_report(results, "test_output.md")

        # Verify report content
        assert "# Discovery Results" in report
        assert "\U0001f7e1 ADEQUATE" in report
        assert "Test Research Paper" in report
        assert "10.1234/test" in report
        assert "Dr. Alice Smith, Dr. Bob Johnson, Dr. Carol Williams" in report
        assert "2023" in report
        assert "88/100" in report
        assert "HIGH" in report

        # Check search parameters section
        assert "test, research" in report
        assert "2020-2024" in report
        assert "rct" in report

        # Check performance section
        assert "5.2 seconds" in report
        assert "Total Papers Found**: 100" in report

        # Check DOI section
        assert "DOI Lists for Zotero Import" in report
        assert "10.1234/test" in report


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI interface."""

    def test_coverage_info_display(self):
        """Test coverage info display."""
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, ["--coverage-info"])

        assert result.exit_code == 0
        assert "Semantic Scholar provides excellent comprehensive coverage" in result.output
        assert "PubMed" in result.output
        assert "IEEE" in result.output
        assert "arXiv" in result.output

    def test_missing_keywords_error(self):
        """Test error when keywords are missing."""
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, ["--limit", "10"])

        assert result.exit_code == 1
        assert "Keywords are required" in result.output

    @patch("discover.discover_papers")
    @patch("discover.generate_discovery_report")
    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.mkdir")
    def test_successful_discovery_command(
        self, mock_mkdir, mock_write_text, mock_generate_report, mock_discover
    ):
        """Test successful discovery command execution."""
        from click.testing import CliRunner
        from discover import DiscoveryResults

        # Mock discovery results
        mock_results = DiscoveryResults(
            papers=[],
            coverage_status={
                "status": "🟢 EXCELLENT",
                "kb_count": 50,
                "discovery_count": 0,
                "high_impact_missing": 0,
                "recent_missing": 0,
                "message": "Excellent coverage",
                "recommendation": "Proceed with research",
            },
            search_params={},
            performance_metrics={"total_time_seconds": 2.0},
        )
        mock_discover.return_value = mock_results
        mock_generate_report.return_value = "Mock report content"

        runner = CliRunner()
        result = runner.invoke(main, ["--keywords", "diabetes", "--limit", "5"])

        # Debug output on failure
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")

        assert result.exit_code == 0
        assert "Discovery completed successfully" in result.output
        assert "Found 0 papers" in result.output
        assert "\U0001f7e2 EXCELLENT" in result.output


if __name__ == "__main__":
    # Create a temporary directory for test outputs
    with tempfile.TemporaryDirectory() as temp_dir:
        # Change to temp directory to avoid creating files in project
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(temp_dir)
            unittest.main()
        finally:
            os.chdir(original_cwd)
