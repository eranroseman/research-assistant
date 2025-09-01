#!/usr/bin/env python3
"""
Unit tests for Citation System functionality.

Covers citation formatting and IEEE citation standards.
Tests the generate_ieee_citation function from cli.py.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli import generate_ieee_citation


@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.citation
class TestIEEECitationFormatting:
    """Test IEEE citation formatting functionality."""

    def test_generate_ieee_citation_with_complete_metadata_should_format_correctly(self):
        """
        Test IEEE citation formatting with complete metadata.

        Given: Paper with complete metadata
        When: generate_ieee_citation is called
        Then: Returns properly formatted IEEE citation
        """
        paper = {
            "title": "Advanced Machine Learning Techniques",
            "authors": ["Smith, J.", "Jones, A.", "Brown, B."],
            "year": 2023,
            "journal": "IEEE Transactions on Pattern Analysis",
            "volume": "45",
            "issue": "3",
            "pages": "123-135",
            "doi": "10.1109/TPAMI.2023.1234567",
        }

        citation = generate_ieee_citation(paper, 1)

        # Check IEEE format components
        assert "[1]" in citation
        assert "Advanced Machine Learning Techniques" in citation
        assert "2023" in citation
        assert isinstance(citation, str)
        assert len(citation) > 0

    def test_generate_ieee_citation_with_minimal_metadata_should_format_correctly(self):
        """
        Test IEEE citation formatting with minimal metadata.

        Given: Paper with minimal metadata
        When: generate_ieee_citation is called
        Then: Returns citation with available information
        """
        paper = {"title": "Basic Study", "authors": ["Smith, J."], "year": 2023}

        citation = generate_ieee_citation(paper, 1)

        # Check basic components
        assert "[1]" in citation
        assert "Basic Study" in citation
        assert "2023" in citation
        assert isinstance(citation, str)

    def test_generate_ieee_citation_with_different_numbers_should_format_correctly(self):
        """
        Test IEEE citation numbering.

        Given: Paper metadata and different citation numbers
        When: generate_ieee_citation is called
        Then: Uses correct citation number
        """
        paper = {"title": "Test Paper", "authors": ["Smith, J."], "year": 2023}

        citation1 = generate_ieee_citation(paper, 1)
        citation5 = generate_ieee_citation(paper, 5)

        assert "[1]" in citation1
        assert "[5]" in citation5
        assert "[1]" not in citation5
        assert "[5]" not in citation1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
