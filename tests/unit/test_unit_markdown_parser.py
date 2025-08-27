#!/usr/bin/env python3
"""Unit tests for markdown parser and hybrid extraction."""

import pytest
from src.markdown_parser import MarkdownParser, HybridMarkdownExtractor, MarkdownSection


class TestMarkdownParser:
    """Tests for the markdown parser."""

    def test_parse_simple_markdown(self):
        """Test parsing basic markdown with headers."""
        parser = MarkdownParser()

        md_text = """# Title

## Abstract
This is the abstract content.

## Introduction
This is the introduction.

## Methods
The methods section.

## Results
The results section.

## Conclusion
The conclusion.
"""
        sections = parser.parse_markdown(md_text)

        assert "abstract" in sections
        assert "introduction" in sections
        assert "methods" in sections
        assert "results" in sections
        assert "conclusion" in sections

        assert sections["abstract"].content == "This is the abstract content."
        assert sections["abstract"].level == 2

    def test_normalize_header_variations(self):
        """Test normalization of different header variations."""
        parser = MarkdownParser()

        # Test various forms
        assert parser._normalize_header("Abstract") == "abstract"
        assert parser._normalize_header("ABSTRACT") == "abstract"
        assert parser._normalize_header("Summary") == "abstract"
        assert parser._normalize_header("1. Introduction") == "introduction"
        assert parser._normalize_header("2 Methods") == "methods"
        assert parser._normalize_header("Materials and Methods") == "methods"
        assert parser._normalize_header("Results and Discussion") == "results"
        assert parser._normalize_header("Conclusions") == "conclusion"
        assert parser._normalize_header("Bibliography") == "references"

    def test_numbered_sections(self):
        """Test parsing sections with numbering."""
        parser = MarkdownParser()

        md_text = """## 1. Introduction
Introduction content.

## 2. Methods
Methods content.

## 3. Results
Results content.
"""
        sections = parser.parse_markdown(md_text)

        assert "introduction" in sections
        assert "methods" in sections
        assert "results" in sections

    def test_structured_abstract(self):
        """Test handling of structured abstracts."""
        parser = MarkdownParser()

        md_text = """## Abstract

**Background:** This study examines...
**Methods:** We conducted...
**Results:** The analysis showed...
**Conclusion:** These findings suggest...

## Introduction
The introduction begins here.
"""
        sections = parser.parse_markdown(md_text)

        assert "abstract" in sections
        abstract_content = sections["abstract"].content
        assert "Background:" in abstract_content
        assert "Methods:" in abstract_content
        assert "The introduction begins" not in abstract_content

    def test_mixed_header_levels(self):
        """Test parsing with different header levels."""
        parser = MarkdownParser()

        md_text = """# Main Title

## Abstract
Abstract content.

### Subsection
This should be ignored or handled separately.

## Methods
Methods content.
"""
        sections = parser.parse_markdown(md_text)

        assert "abstract" in sections
        assert "methods" in sections
        # Subsection without recognized name should not appear
        assert "subsection" not in sections

    def test_has_markdown_structure(self):
        """Test detection of markdown structure."""
        parser = MarkdownParser()

        # Has markdown
        assert parser.has_markdown_structure("## Abstract\nContent")
        assert parser.has_markdown_structure("### Methods\nContent")

        # No markdown
        assert not parser.has_markdown_structure("Abstract\nContent")
        assert not parser.has_markdown_structure("Just plain text")

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        parser = MarkdownParser()

        # High confidence - all key sections
        sections_full = {
            "abstract": MarkdownSection("abstract", "content", 2, 0, 10),
            "introduction": MarkdownSection("introduction", "content", 2, 11, 20),
            "methods": MarkdownSection("methods", "content", 2, 21, 30),
            "results": MarkdownSection("results", "content", 2, 31, 40),
            "discussion": MarkdownSection("discussion", "content", 2, 41, 50),
            "conclusion": MarkdownSection("conclusion", "content", 2, 51, 60),
        }

        confidence = parser.get_confidence_score(sections_full)
        assert confidence >= 0.9

        # Low confidence - few sections
        sections_partial = {
            "abstract": MarkdownSection("abstract", "content", 2, 0, 10),
        }

        confidence = parser.get_confidence_score(sections_partial)
        assert confidence < 0.5

    def test_extract_sections_from_markdown(self):
        """Test simple dictionary extraction."""
        parser = MarkdownParser()

        md_text = """## Abstract
Abstract text.

## Methods
Methods text.
"""
        sections = parser.extract_sections_from_markdown(md_text)

        assert isinstance(sections, dict)
        assert sections["abstract"] == "Abstract text."
        assert sections["methods"] == "Methods text."


class TestHybridMarkdownExtractor:
    """Tests for the hybrid extraction approach."""

    def test_should_use_markdown_good_structure(self):
        """Test decision to use markdown with good structure."""
        extractor = HybridMarkdownExtractor()

        good_md = """## Abstract
This is a substantial abstract with enough content to be meaningful.

## Introduction
A proper introduction section with adequate content.

## Methods
Detailed methods section with sufficient text.

## Results
Results with enough content.

## Discussion
Discussion section.

## Conclusion
Conclusion text.
"""
        assert extractor.should_use_markdown(good_md)

    def test_should_not_use_markdown_poor_structure(self):
        """Test rejection of poor markdown structure."""
        extractor = HybridMarkdownExtractor()

        # No headers
        plain_text = "This is just plain text without markdown headers."
        assert not extractor.should_use_markdown(plain_text)

        # Too few sections
        sparse_md = """## Abstract
Short content.

## Conclusion
Brief conclusion.
"""
        assert not extractor.should_use_markdown(sparse_md)

        # Headers but no content
        empty_md = """## Abstract

## Introduction

## Methods

## Results
"""
        assert not extractor.should_use_markdown(empty_md)

    def test_extract_with_fallback_good_markdown(self):
        """Test extraction with good markdown."""
        extractor = HybridMarkdownExtractor()

        good_md = """## Abstract
This is a comprehensive abstract with substantial content that provides a clear overview.

## Introduction
The introduction provides background and context for the research with enough detail.

## Methods
Methods are described in detail with sufficient information about the approach.

## Results
Results section contains findings and data analysis with adequate detail.
"""
        sections, method = extractor.extract_with_fallback(good_md)

        assert method == "markdown"
        assert "abstract" in sections
        assert "introduction" in sections
        assert "methods" in sections
        assert "results" in sections

    def test_extract_with_fallback_poor_markdown(self):
        """Test fallback for poor markdown."""
        extractor = HybridMarkdownExtractor()

        poor_text = "This is plain text without proper markdown structure."

        sections, method = extractor.extract_with_fallback(poor_text)

        assert method == "regex_fallback"
        assert sections == {}  # Should return empty to trigger regex

    def test_markdown_with_special_characters(self):
        """Test handling of special characters in headers."""
        parser = MarkdownParser()

        md_text = """## Abstract:
Content with colon.

## Methods & Materials
Content with ampersand.

## Results/Findings
Content with slash.
"""
        sections = parser.parse_markdown(md_text)

        assert "abstract" in sections
        assert "methods" in sections
        assert "results" in sections

    def test_case_insensitive_matching(self):
        """Test case-insensitive header matching."""
        parser = MarkdownParser()

        md_text = """## ABSTRACT
Upper case abstract.

## introduction
Lower case introduction.

## MeThOdS
Mixed case methods.
"""
        sections = parser.parse_markdown(md_text)

        assert "abstract" in sections
        assert "introduction" in sections
        assert "methods" in sections

    def test_markdown_with_inline_formatting(self):
        """Test handling of markdown with inline formatting."""
        parser = MarkdownParser()

        md_text = """## Abstract

This abstract has **bold text** and *italic text* and [links](http://example.com).

## Methods

Methods with `code snippets` and _underscores_.
"""
        sections = parser.parse_markdown(md_text)

        assert "abstract" in sections
        assert "**bold text**" in sections["abstract"].content
        assert "*italic text*" in sections["abstract"].content

        assert "methods" in sections
        assert "`code snippets`" in sections["methods"].content

    def test_count_markdown_sections(self):
        """Test counting recognized sections."""
        parser = MarkdownParser()

        md_text = """## Abstract
Content.

## Random Header
Not recognized.

## Methods
Content.

## Another Random
Not recognized.

## Conclusion
Content.
"""
        count = parser.count_markdown_sections(md_text)
        assert count == 3  # Only abstract, methods, conclusion


class TestHybridIntegration:
    """Test integration between markdown and regex fallback."""

    def test_threshold_settings(self):
        """Test configurable thresholds."""
        extractor = HybridMarkdownExtractor()

        assert extractor.min_sections_for_markdown == 3
        assert extractor.min_confidence_for_markdown == 0.6

        # Test with custom thresholds
        extractor.min_sections_for_markdown = 5
        extractor.min_confidence_for_markdown = 0.8

        # This should now fail with only 4 sections
        md_text = """## Abstract
Content here.

## Introduction
Content here.

## Methods
Content here.

## Conclusion
Content here.
"""
        assert not extractor.should_use_markdown(md_text)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
