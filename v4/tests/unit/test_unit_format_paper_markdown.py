#!/usr/bin/env python3
"""Unit tests for the format_paper_as_markdown method in KnowledgeBaseBuilder."""

import pytest
from unittest.mock import patch
from src.build_kb import KnowledgeBaseBuilder


@pytest.mark.unit
@pytest.mark.knowledge_base
class TestFormatPaperAsMarkdown:
    """Test the format_paper_as_markdown method."""

    @pytest.fixture
    def kb_builder(self, tmp_path):
        """Create a KnowledgeBaseBuilder instance for testing."""
        with patch("src.kb_indexer.KBIndexer._detect_device", return_value="cpu"):
            builder = KnowledgeBaseBuilder(knowledge_base_path=tmp_path)
            return builder

    def test_format_with_basic_metadata_only(self, kb_builder):
        """Test formatting with only basic metadata."""
        paper_data = {
            "title": "Test Paper Title",
            "authors": ["Author One", "Author Two"],
            "year": 2024,
            "abstract": "This is the abstract text.",
        }

        result = kb_builder.format_paper_as_markdown(paper_data)

        assert "# Test Paper Title" in result
        assert "**Authors:** Author One, Author Two" in result
        assert "**Year:** 2024" in result
        assert "## Abstract" in result
        assert "This is the abstract text." in result

    def test_format_with_complete_metadata(self, kb_builder):
        """Test formatting with complete metadata fields."""
        paper_data = {
            "title": "Complete Paper",
            "authors": ["First Author", "Second Author"],
            "year": 2023,
            "journal": "Nature",
            "volume": "123",
            "issue": "4",
            "pages": "456-789",
            "doi": "10.1038/nature.2023.123",
            "abstract": "Abstract content here.",
        }

        result = kb_builder.format_paper_as_markdown(paper_data)

        assert "# Complete Paper" in result
        assert "**Authors:** First Author, Second Author" in result
        assert "**Year:** 2023" in result
        assert "**Journal:** Nature" in result
        assert "**Volume:** 123" in result
        assert "**Issue:** 4" in result
        assert "**Pages:** 456-789" in result
        assert "**DOI:** 10.1038/nature.2023.123" in result
        assert "## Abstract" in result
        assert "Abstract content here." in result

    def test_format_with_sections_provided(self, kb_builder):
        """Test formatting with extracted sections."""
        paper_data = {
            "title": "Paper with Sections",
            "authors": ["Author A"],
            "year": 2024,
            "abstract": "Paper abstract",
            "full_text": "This should not appear when sections are provided",
        }

        sections = {
            "abstract": "Extracted abstract text",
            "introduction": "This is the introduction section.",
            "methods": "Methods section content here.",
            "results": "Results section content.",
            "discussion": "Discussion of findings.",
            "conclusion": "Concluding remarks.",
            "references": "1. Reference One\n2. Reference Two",
        }

        result = kb_builder.format_paper_as_markdown(paper_data, sections=sections)

        # Check that structured sections are included
        assert "## Abstract" in result
        assert "Extracted abstract text" in result
        assert "## Introduction" in result
        assert "This is the introduction section." in result
        assert "## Methods" in result
        assert "Methods section content here." in result
        assert "## Results" in result
        assert "Results section content." in result
        assert "## Discussion" in result
        assert "Discussion of findings." in result
        assert "## Conclusion" in result
        assert "Concluding remarks." in result
        assert "## References" in result
        assert "1. Reference One" in result

        # Check that full_text is NOT included when sections are present
        assert "This should not appear when sections are provided" not in result
        assert "## Full Text" not in result

    def test_format_with_empty_sections_falls_back_to_full_text(self, kb_builder):
        """Test that empty sections dictionary falls back to full text."""
        paper_data = {
            "title": "Paper with Empty Sections",
            "authors": ["Author B"],
            "year": 2024,
            "abstract": "Original abstract",
            "full_text": "This is the full text content that should appear.",
        }

        sections = {}  # Empty sections

        result = kb_builder.format_paper_as_markdown(paper_data, sections=sections)

        # Should fall back to original behavior
        assert "## Abstract" in result
        assert "Original abstract" in result
        assert "## Full Text" in result
        assert "This is the full text content that should appear." in result

    def test_format_with_partial_sections(self, kb_builder):
        """Test formatting with only some sections extracted."""
        paper_data = {
            "title": "Paper with Partial Sections",
            "authors": ["Author C"],
            "year": 2024,
            "abstract": "Paper abstract",
        }

        sections = {
            "introduction": "Introduction only",
            "methods": "Methods section",
            # Missing other sections
        }

        result = kb_builder.format_paper_as_markdown(paper_data, sections=sections)

        # Should include the sections that are present
        assert "## Introduction" in result
        assert "Introduction only" in result
        assert "## Methods" in result
        assert "Methods section" in result

        # Should use paper's abstract since no extracted abstract
        assert "## Abstract" in result
        assert "Paper abstract" in result

        # Should not include sections that weren't extracted
        assert "## Results" not in result
        assert "## Discussion" not in result

    def test_format_without_sections_parameter(self, kb_builder):
        """Test backward compatibility when sections parameter is not provided."""
        paper_data = {
            "title": "Legacy Paper",
            "authors": ["Legacy Author"],
            "year": 2022,
            "abstract": "Legacy abstract",
            "full_text": "Legacy full text content",
        }

        # Call without sections parameter (backward compatibility)
        result = kb_builder.format_paper_as_markdown(paper_data)

        assert "# Legacy Paper" in result
        assert "## Abstract" in result
        assert "Legacy abstract" in result
        assert "## Full Text" in result
        assert "Legacy full text content" in result

    def test_format_with_missing_optional_fields(self, kb_builder):
        """Test formatting when optional fields are missing."""
        paper_data = {
            "title": "Minimal Paper",
            # No authors
            # No year
            # No journal info
            # No abstract
        }

        result = kb_builder.format_paper_as_markdown(paper_data)

        assert "# Minimal Paper" in result
        assert "**Year:** Unknown" in result
        assert "## Abstract" in result
        assert "No abstract available." in result

        # Should not include missing fields
        assert "**Authors:**" not in result  # No authors field when empty
        assert "**Journal:**" not in result
        assert "**DOI:**" not in result

    def test_format_with_sections_but_no_content_falls_back(self, kb_builder):
        """Test that sections with all empty values falls back to full text."""
        paper_data = {
            "title": "Paper with Null Sections",
            "authors": ["Author D"],
            "year": 2024,
            "abstract": "Original abstract",
            "full_text": "Full text fallback content",
        }

        sections = {
            "introduction": "",
            "methods": None,
            "results": "",
            # All sections are empty or None
        }

        result = kb_builder.format_paper_as_markdown(paper_data, sections=sections)

        # Should fall back to full text since no sections have content
        assert "## Abstract" in result
        assert "Original abstract" in result
        assert "## Full Text" in result
        assert "Full text fallback content" in result

    def test_format_preserves_section_order(self, kb_builder):
        """Test that sections appear in the correct order."""
        paper_data = {"title": "Ordered Paper", "authors": ["Author E"], "year": 2024, "abstract": "Abstract"}

        sections = {
            "conclusion": "Conclusion content",  # Out of order in dict
            "introduction": "Introduction content",
            "results": "Results content",
            "methods": "Methods content",
            "discussion": "Discussion content",
        }

        result = kb_builder.format_paper_as_markdown(paper_data, sections=sections)

        # Find positions of sections in the output
        intro_pos = result.find("## Introduction")
        methods_pos = result.find("## Methods")
        results_pos = result.find("## Results")
        discussion_pos = result.find("## Discussion")
        conclusion_pos = result.find("## Conclusion")

        # Verify correct order
        assert intro_pos < methods_pos
        assert methods_pos < results_pos
        assert results_pos < discussion_pos
        assert discussion_pos < conclusion_pos

    def test_format_handles_special_characters(self, kb_builder):
        """Test that special characters in content are preserved."""
        paper_data = {
            "title": "Paper with Special Characters & Symbols",
            "authors": ["Author & Co.", "Smith, J."],
            "year": 2024,
            "abstract": "Abstract with 'quotes' and \"double quotes\"",
        }

        sections = {
            "introduction": "Math symbols: α, β, γ, Δ, ∑",  # noqa: RUF001
            "methods": "Code snippet: `print('hello')`",
            "results": "p < 0.05, n=100, R²=0.85",
        }

        result = kb_builder.format_paper_as_markdown(paper_data, sections=sections)

        assert "Paper with Special Characters & Symbols" in result
        assert "Author & Co., Smith, J." in result
        assert "'quotes' and \"double quotes\"" in result
        assert "α, β, γ, Δ, ∑" in result  # noqa: RUF001
        assert "`print('hello')`" in result
        assert "p < 0.05, n=100, R²=0.85" in result
