#!/usr/bin/env python3
"""
Example test file demonstrating use of new fixtures and markers.

This file shows best practices for using the centralized fixtures
and test markers added to the test suite.
"""

import pytest


@pytest.mark.unit
@pytest.mark.cli
@pytest.mark.fast
class TestExampleWithFixtures:
    """Example tests using the new centralized fixtures."""

    def test_cli_with_runner_fixture(self, runner):
        """
        Example using the centralized runner fixture.
        
        No need to import CliRunner or create it manually.
        """
        from src.cli import cli
        
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_cli_with_isolated_runner(self, isolated_runner):
        """
        Example using the isolated runner fixture.
        
        Automatically provides isolated filesystem.
        """
        from src.cli import cli
        
        # Can create files in isolated environment
        with open("test_file.txt", "w") as f:
            f.write("test content")
        
        isolated_runner.invoke(cli, ["info"])
        # File exists in isolated environment but won't affect real filesystem

    def test_with_mock_semantic_scholar(self, mock_semantic_scholar):
        """
        Example using the mock Semantic Scholar API fixture.
        
        API calls are automatically mocked with realistic responses.
        """
        import requests
        
        # This would normally hit the real API, but it's mocked
        response = requests.get("https://api.semanticscholar.org/paper/123")
        data = response.json()
        
        assert response.status_code == 200
        assert data["paperId"] == "test123"
        assert data["citationCount"] == 50

    def test_with_mock_error_responses(self, mock_semantic_scholar_error):
        """
        Example using the error mock fixture.
        
        Simulates API errors for error handling tests.
        """
        import requests
        
        # Test rate limiting
        response = requests.get("https://api.semanticscholar.org/rate_limit")
        assert response.status_code == 429
        assert "Rate limit" in response.json()["error"]

    def test_with_sample_data(self, sample_paper, sample_kb_metadata):
        """
        Example using sample data fixtures.
        
        Provides consistent test data without repetition.
        """
        # sample_paper provides a complete paper dictionary
        assert sample_paper["id"] == "0001"
        assert sample_paper["quality_score"] == 75
        
        # sample_kb_metadata creates a metadata file in temp directory
        import json
        with open(sample_kb_metadata) as f:
            metadata = json.load(f)
        
        assert metadata["version"] == "4.0"
        assert len(metadata["papers"]) == 5

    def test_with_all_mocks(self, mock_external_apis):
        """
        Example using the convenience fixture for all mocks.
        
        Both Semantic Scholar and Zotero are mocked.
        """
        # Both APIs are mocked
        semantic_scholar = mock_external_apis["semantic_scholar"]
        
        # Can verify mock calls
        import requests
        requests.get("https://api.semanticscholar.org/paper/123")
        semantic_scholar.assert_called_once()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_kb
class TestExampleIntegration:
    """Example integration tests with appropriate markers."""

    @pytest.mark.serial
    def test_that_must_run_alone(self, runner, temp_kb_dir):
        """
        Test marked as serial - won't run in parallel.
        
        Use for tests that modify global state.
        """
        # This test won't be run in parallel with others

    @pytest.mark.flaky
    @pytest.mark.requires_api
    def test_with_real_api(self):
        """
        Test that might fail intermittently.
        
        Marked as flaky and requires_api for appropriate handling.
        """
        # This would hit real API - should be mocked in CI


@pytest.mark.performance
@pytest.mark.requires_gpu
class TestExamplePerformance:
    """Example performance tests with GPU requirement."""

    def test_embedding_speed(self):
        """Test requiring GPU for performance benchmarking."""
        # Would test GPU-accelerated embeddings


# Example of running specific test sets:
# pytest -m "unit and not slow"           # Fast unit tests only
# pytest -m "cli and not requires_kb"     # CLI tests without KB
# pytest -m "critical"                    # Only critical tests
# pytest -m "not requires_api"            # Skip tests needing API
# pytest -m "performance" -n 0            # Performance tests, no parallel
