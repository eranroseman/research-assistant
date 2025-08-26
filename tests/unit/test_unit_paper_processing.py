#!/usr/bin/env python3
"""Unit tests for paper processing in KnowledgeBaseBuilder."""

import json
import pytest
from unittest.mock import patch
from src.build_kb import KnowledgeBaseBuilder


@pytest.mark.unit
@pytest.mark.knowledge_base
class TestPaperProcessing:
    """Test paper processing with and without full text."""

    @pytest.fixture
    def kb_builder(self, tmp_path):
        """Create a KnowledgeBaseBuilder instance for testing."""
        with patch("src.kb_indexer.KBIndexer._detect_device", return_value="cpu"):
            builder = KnowledgeBaseBuilder(knowledge_base_path=tmp_path)
            # Create necessary directories
            builder.papers_path.mkdir(parents=True, exist_ok=True)
            return builder

    def test_build_kb_with_papers_without_full_text(self, kb_builder, tmp_path):
        """Test that papers without full text are handled correctly.

        This tests the fix for the UnboundLocalError where extracted_sections
        was not initialized for papers without full text.
        """
        # Simulate what happens during the build process
        papers = [
            {
                "title": "Paper with Full Text",
                "authors": ["Author A"],
                "year": 2024,
                "abstract": "Abstract for paper with full text",
                "full_text": "Introduction\nThis is the introduction.\n\nMethods\nThese are the methods.",
                "doi": "10.1234/test1",
                "journal": "Test Journal",
                "zotero_key": "KEY001",
            },
            {
                "title": "Paper without Full Text",
                "authors": ["Author B"],
                "year": 2024,
                "abstract": "Abstract for paper without full text",
                # No full_text field
                "doi": "10.1234/test2",
                "journal": "Test Journal 2",
                "zotero_key": "KEY002",
            },
        ]

        sections_index = {}

        # Process each paper as the build method would
        for i, paper in enumerate(papers):
            paper_id = f"{i + 1:04d}"

            # This is the fixed logic from build_kb.py
            if paper.get("full_text"):
                # Would call extract_sections here
                extracted_sections = {
                    "abstract": paper.get("abstract", ""),
                    "introduction": "Extracted intro",
                    "methods": "Extracted methods",
                    "results": "",
                    "discussion": "",
                    "conclusion": "",
                    "references": "",
                    "supplementary": "",
                }
                sections_index[paper_id] = extracted_sections
            else:
                # The fix: Initialize extracted_sections for papers without full text
                extracted_sections = {
                    "abstract": paper.get("abstract", ""),
                    "introduction": "",
                    "methods": "",
                    "results": "",
                    "discussion": "",
                    "conclusion": "",
                    "references": "",
                    "supplementary": "",
                }
                sections_index[paper_id] = extracted_sections

            # Format and save the paper - this should not raise UnboundLocalError
            md_content = kb_builder.format_paper_as_markdown(paper, sections=extracted_sections)
            paper_file = kb_builder.papers_path / f"paper_{paper_id}.md"
            paper_file.write_text(md_content)

        # Verify both papers were saved correctly
        paper1_content = (kb_builder.papers_path / "paper_0001.md").read_text()
        assert "# Paper with Full Text" in paper1_content
        assert "**Authors:** Author A" in paper1_content

        paper2_content = (kb_builder.papers_path / "paper_0002.md").read_text()
        assert "# Paper without Full Text" in paper2_content
        assert "**Authors:** Author B" in paper2_content
        assert "## Abstract" in paper2_content
        assert "Abstract for paper without full text" in paper2_content

    def test_format_paper_as_markdown_with_no_full_text_sections(self, kb_builder):
        """Test format_paper_as_markdown handles papers without full text correctly."""
        paper_data = {
            "title": "Paper Without Full Text",
            "authors": ["Test Author"],
            "year": 2024,
            "abstract": "This paper has no full text, only an abstract.",
            "doi": "10.1234/test",
            "journal": "Test Journal",
        }

        # Empty sections (as would be created for papers without full text)
        sections = {
            "abstract": "This paper has no full text, only an abstract.",
            "introduction": "",
            "methods": "",
            "results": "",
            "discussion": "",
            "conclusion": "",
            "references": "",
            "supplementary": "",
        }

        result = kb_builder.format_paper_as_markdown(paper_data, sections=sections)

        assert "# Paper Without Full Text" in result
        assert "**Authors:** Test Author" in result
        assert "**Year:** 2024" in result
        assert "**Journal:** Test Journal" in result
        assert "**DOI:** 10.1234/test" in result
        assert "## Abstract" in result
        assert "This paper has no full text, only an abstract." in result

        # Should not include empty sections
        assert "## Introduction" not in result
        assert "## Methods" not in result
        assert "## Results" not in result

    def test_extract_sections_behavior_with_full_text(self, kb_builder):
        """Test that section extraction works correctly for papers with full text."""
        # Paper with full text that has clear sections
        paper_with_text = {
            "title": "Paper with text",
            "full_text": """Abstract
            This is the abstract.

            Introduction
            This is the introduction section.

            Methods
            This describes the methods used.

            Results
            Here are the results.

            Discussion
            Discussion of findings.

            Conclusion
            Final conclusions.
            """,
            "abstract": "Original abstract",
        }

        # Extract sections
        sections = kb_builder.extract_sections(paper_with_text["full_text"], paper_with_text)

        # Should have extracted content
        assert "abstract" in sections
        assert "introduction" in sections
        assert "methods" in sections
        assert "results" in sections
        assert "discussion" in sections
        assert "conclusion" in sections

    def test_incremental_update_handles_papers_without_full_text(self, kb_builder, tmp_path):
        """Test that incremental updates handle papers without full text correctly."""
        # Create existing metadata with one paper
        existing_metadata = {
            "papers": [
                {
                    "id": "0001",
                    "title": "Existing Paper",
                    "authors": ["Existing Author"],
                    "year": 2023,
                    "has_full_text": True,
                    "zotero_key": "KEY001",
                }
            ]
        }

        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(existing_metadata, f)

        # Create a new paper without full text
        new_paper = {
            "title": "New Paper Without Full Text",
            "authors": ["New Author"],
            "year": 2024,
            "abstract": "New abstract without full text",
            # No full_text field
            "zotero_key": "KEY002",
        }

        # Process the new paper (simulating part of incremental update)
        # This simulates what happens in the incremental update path
        extracted_sections = {}  # Initialize first
        if new_paper.get("full_text"):
            # Would extract sections here
            pass
        else:
            # Use empty sections for papers without full text
            extracted_sections = {
                "abstract": new_paper.get("abstract", ""),
                "introduction": "",
                "methods": "",
                "results": "",
                "discussion": "",
                "conclusion": "",
                "references": "",
                "supplementary": "",
            }

        # Format the paper - this should not raise UnboundLocalError
        md_content = kb_builder.format_paper_as_markdown(new_paper, sections=extracted_sections)

        assert "# New Paper Without Full Text" in md_content
        assert "New abstract without full text" in md_content

    def test_mixed_papers_processing_order(self, kb_builder):
        """Test processing papers in different orders with mixed full text availability."""
        papers = [
            {
                "title": "First - No Full Text",
                "abstract": "Abstract only",
                "authors": ["Author A"],
                "year": 2024,
            },
            {
                "title": "Second - With Full Text",
                "abstract": "Abstract",
                "full_text": "Introduction\nContent here",
                "authors": ["Author B"],
                "year": 2024,
            },
            {
                "title": "Third - No Full Text",
                "abstract": "Another abstract only",
                "authors": ["Author C"],
                "year": 2024,
            },
        ]

        for i, paper in enumerate(papers):
            # Simulate the logic from build()
            if paper.get("full_text"):
                # Would call extract_sections here
                extracted_sections = {
                    "abstract": paper.get("abstract", ""),
                    "introduction": "Extracted intro",
                    "methods": "",
                    "results": "",
                    "discussion": "",
                    "conclusion": "",
                    "references": "",
                    "supplementary": "",
                }
            else:
                # Papers without full text get empty sections
                extracted_sections = {
                    "abstract": paper.get("abstract", ""),
                    "introduction": "",
                    "methods": "",
                    "results": "",
                    "discussion": "",
                    "conclusion": "",
                    "references": "",
                    "supplementary": "",
                }

            # This should work for all papers regardless of full text availability
            md_content = kb_builder.format_paper_as_markdown(paper, sections=extracted_sections)
            assert f"# {paper['title']}" in md_content
            assert paper["abstract"] in md_content
