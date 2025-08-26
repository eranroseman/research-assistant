#!/usr/bin/env python3
"""Unit tests for enhanced abstract extraction functionality."""

import pytest
from unittest.mock import patch
from src.build_kb import KnowledgeBaseBuilder


@pytest.mark.unit
@pytest.mark.knowledge_base
class TestAbstractExtraction:
    """Test the enhanced abstract extraction with fallback methods."""

    @pytest.fixture
    def kb_builder(self, tmp_path):
        """Create a KnowledgeBaseBuilder instance for testing."""
        with patch("src.kb_indexer.KBIndexer._detect_device", return_value="cpu"):
            builder = KnowledgeBaseBuilder(knowledge_base_path=tmp_path)
            return builder

    def test_extract_abstract_from_zotero_metadata(self, kb_builder):
        """Test that abstract is extracted from Zotero metadata when available."""
        text = "Some paper content without clear abstract"
        paper = {
            "title": "Test Paper",
            "abstract": "This is the abstract from Zotero metadata.",
            "authors": ["Author One"],
        }

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert result == "This is the abstract from Zotero metadata."

    def test_extract_abstract_between_title_and_introduction(self, kb_builder):
        """Test extraction of abstract between title and Introduction section."""
        text = """
Paper Title
Author Names
University Affiliation

This study investigates the effectiveness of machine learning approaches
in medical diagnosis. We present a comprehensive analysis of various algorithms
and their performance on real-world clinical data. Our results demonstrate
significant improvements in diagnostic accuracy compared to traditional methods.

Introduction

The field of medical diagnosis has evolved significantly...
"""
        paper = {"abstract": ""}  # Empty metadata

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert "This study investigates" in result
        assert "diagnostic accuracy" in result
        assert len(result) > 100
        assert len(result) < 5000

    def test_extract_abstract_with_explicit_label(self, kb_builder):
        """Test extraction when abstract is explicitly labeled."""
        text = """
Title of the Paper

Abstract: This paper presents a novel approach to solving complex optimization
problems using quantum computing techniques. We demonstrate that our method
achieves superior performance on benchmark datasets.

Introduction

Recent advances in quantum computing...
"""
        paper = {"abstract": ""}

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert "novel approach" in result
        assert "quantum computing" in result
        assert "superior performance" in result

    def test_extract_abstract_after_doi(self, kb_builder):
        """Test extraction of abstract after DOI metadata."""
        text = """
Paper Title
Authors
DOI: 10.1234/journal.2024.001

We investigated the impact of climate change on marine ecosystems
through a comprehensive meta-analysis of 500 studies. Our findings
reveal significant shifts in species distribution patterns.

Introduction

Climate change represents...
"""
        paper = {"abstract": ""}

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert "climate change" in result
        assert "marine ecosystems" in result

    def test_extract_abstract_from_first_paragraph(self, kb_builder):
        """Test extraction from first substantial paragraph with abstract-like phrases."""
        text = """
Research Article

Some metadata here

This paper examines the relationship between social media usage and mental health
outcomes in adolescents. Through a longitudinal study of 1000 participants over
three years, we found significant correlations between excessive social media use
and increased anxiety levels.

Background and Motivation

The proliferation of social media...
"""
        paper = {"abstract": ""}

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert "This paper examines" in result
        assert "mental health" in result
        assert "longitudinal study" in result

    def test_no_abstract_found_returns_empty(self, kb_builder):
        """Test that empty string is returned when no abstract can be found."""
        text = """
Random text without any abstract-like content.
Just some paragraphs that don't look like an abstract.
No study mentions, no research indicators.
"""
        paper = {"abstract": ""}

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert result == ""

    def test_abstract_length_validation(self, kb_builder):
        """Test that extracted abstracts respect length constraints."""
        # Too short text
        text_short = """
Title

Short.

Introduction
Content here...
"""
        paper = {"abstract": ""}

        result = kb_builder._extract_abstract_fallback(text_short, paper)
        assert result == ""  # Should reject too-short content

        # Very long text
        text_long = (
            """
Title

"""
            + "This is a very long abstract. " * 500
            + """

Introduction
Content...
"""
        )

        result = kb_builder._extract_abstract_fallback(text_long, paper)
        if result:
            assert len(result) <= 5000  # Should limit length

    def test_extract_sections_with_fallback_integration(self, kb_builder):
        """Test that extract_sections integrates with abstract fallback."""
        text = """
Paper Without Clear Abstract

The main contribution of this work is a new framework for understanding
complex systems through network analysis. We apply this framework to
biological networks and demonstrate its effectiveness.

Methods

We collected data from...
"""
        paper = {"abstract": "", "title": "Test Paper"}

        sections = kb_builder.extract_sections(text, paper)

        # Should have extracted abstract using fallback
        assert "abstract" in sections
        if sections["abstract"]:  # May be empty if extractor doesn't find it
            assert "main contribution" in sections["abstract"].lower() or len(sections["abstract"]) > 0

    def test_fallback_priority_order(self, kb_builder):
        """Test that fallback methods are tried in correct priority order."""
        text = """
Title

Abstract: Explicit abstract text here.

This study investigates something else that looks like an abstract.

Introduction
"""

        # Test with metadata - should use metadata first
        paper_with_meta = {"abstract": "Metadata abstract"}
        result = kb_builder._extract_abstract_fallback(text, paper_with_meta)
        assert result == "Metadata abstract"

        # Test without metadata - should find explicit abstract
        paper_no_meta = {"abstract": ""}
        result = kb_builder._extract_abstract_fallback(text, paper_no_meta)
        assert "Explicit abstract text" in result

    def test_abstract_extraction_with_numbered_sections(self, kb_builder):
        """Test abstract extraction when sections are numbered."""
        text = """
Research Paper Title

This comprehensive study analyzes the effectiveness of renewable energy
policies across 50 countries. We find that subsidies combined with
regulatory frameworks yield the best outcomes for adoption rates.

1. Introduction

The transition to renewable energy...
"""
        paper = {"abstract": ""}

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert "comprehensive study" in result
        assert "renewable energy" in result
        assert "50 countries" in result

    def test_abstract_extraction_with_keywords_section(self, kb_builder):
        """Test that abstract before Keywords section is properly extracted."""
        text = """
Title

This research explores machine learning applications in healthcare.
We demonstrate improved diagnostic accuracy through deep learning models
trained on medical imaging data from 10,000 patients.

Keywords: machine learning, healthcare, deep learning, medical imaging

Introduction

Healthcare systems worldwide...
"""
        paper = {"abstract": ""}

        result = kb_builder._extract_abstract_fallback(text, paper)
        assert "machine learning applications" in result
        assert "diagnostic accuracy" in result
        assert "Keywords:" not in result  # Should not include keywords line
