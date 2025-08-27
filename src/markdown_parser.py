#!/usr/bin/env python3
"""Markdown parser for PyMuPDF4LLM integration with hybrid extraction."""

import re
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarkdownSection:
    """Represents a section extracted from markdown."""

    title: str
    content: str
    level: int  # Header level (1=#, 2=##, etc.)
    start_line: int
    end_line: int


class MarkdownParser:
    """Parse academic paper sections from markdown-formatted text."""

    def __init__(self) -> None:
        """Initialize the markdown parser with section mappings."""
        # Map various header texts to standard section names
        self.section_mappings = {
            # Abstract variations
            "abstract": ["abstract", "summary", "executive summary", "synopsis"],
            "introduction": [
                "introduction",
                "background",
                "introduction and background",
                "motivation",
                "overview",
                "1 introduction",
                "1. introduction",
            ],
            "methods": [
                "methods",
                "methodology",
                "materials and methods",
                "experimental design",
                "approach",
                "materials",
                "study design",
                "2 methods",
                "2. methods",
                "methods and materials",
            ],
            "results": [
                "results",
                "findings",
                "experimental results",
                "outcomes",
                "3 results",
                "3. results",
                "results and discussion",
            ],
            "discussion": ["discussion", "analysis", "interpretation", "4 discussion", "4. discussion"],
            "conclusion": [
                "conclusion",
                "conclusions",
                "summary and conclusions",
                "concluding remarks",
                "final remarks",
                "5 conclusion",
                "5. conclusion",
                "6 conclusion",
            ],
            "references": [
                "references",
                "bibliography",
                "works cited",
                "literature cited",
                "citations",
                "reference",
                "refs",
            ],
        }

        # Build reverse mapping for fast lookup
        self._build_reverse_mapping()

    def _build_reverse_mapping(self) -> None:
        """Build a reverse mapping from variations to standard names."""
        self.header_to_section = {}
        for standard_name, variations in self.section_mappings.items():
            for variation in variations:
                self.header_to_section[variation.lower()] = standard_name

    def parse_markdown(self, md_text: str) -> dict[str, MarkdownSection]:
        """Parse markdown text into sections.

        Args:
            md_text: Markdown-formatted text from PyMuPDF4LLM

        Returns:
            Dictionary mapping section names to MarkdownSection objects
        """
        if not md_text:
            return {}

        lines = md_text.split("\n")
        sections = {}
        current_section = None
        current_content: list[str] = []
        current_start = 0

        for i, line in enumerate(lines):
            # Check if line is a markdown header
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if header_match:
                # Save previous section if exists
                if current_section:
                    sections[current_section.title] = MarkdownSection(
                        title=current_section.title,
                        content="\n".join(current_content).strip(),
                        level=current_section.level,
                        start_line=current_section.start_line,
                        end_line=i - 1,
                    )

                # Start new section
                level = len(header_match.group(1))
                header_text = header_match.group(2).strip()
                standard_name = self._normalize_header(header_text)

                if standard_name:
                    current_section = MarkdownSection(
                        title=standard_name, content="", level=level, start_line=i, end_line=i
                    )
                    current_content = []
            elif current_section:
                # Add content to current section
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section.title] = MarkdownSection(
                title=current_section.title,
                content="\n".join(current_content).strip(),
                level=current_section.level,
                start_line=current_section.start_line,
                end_line=len(lines) - 1,
            )

        return sections

    def _normalize_header(self, header_text: str) -> str | None:  # noqa: PLR0911
        """Normalize header text to standard section name.

        Args:
            header_text: Raw header text from markdown

        Returns:
            Standard section name or None if not recognized
        """
        # Remove common prefixes and clean up
        cleaned = header_text.lower().strip()
        cleaned = re.sub(r"^\d+\.?\s*", "", cleaned)  # Remove numbering
        cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
        cleaned = re.sub(r"[:\-\u2013\u2014]$", "", cleaned)  # Remove trailing punctuation

        # Direct lookup
        if cleaned in self.header_to_section:
            return self.header_to_section[cleaned]

        # Fuzzy matching for common patterns
        for standard_name, variations in self.section_mappings.items():
            for variation in variations:
                if variation.lower() in cleaned or cleaned in variation.lower():
                    return standard_name

        # Check if it contains key terms
        if any(word in cleaned for word in ["abstract", "summary"]):
            return "abstract"
        if any(word in cleaned for word in ["introduction", "background"]):
            return "introduction"
        if any(word in cleaned for word in ["method", "material", "approach"]):
            return "methods"
        if any(word in cleaned for word in ["result", "finding"]):
            return "results"
        if any(word in cleaned for word in ["discussion", "analysis"]):
            return "discussion"
        if any(word in cleaned for word in ["conclusion", "conclud"]):
            return "conclusion"
        if any(word in cleaned for word in ["reference", "bibliography", "citation"]):
            return "references"

        # Return None for unrecognized headers
        return None

    def extract_sections_from_markdown(self, md_text: str) -> dict[str, str]:
        """Extract sections as simple string dictionary.

        Args:
            md_text: Markdown-formatted text

        Returns:
            Dictionary mapping section names to content strings
        """
        markdown_sections = self.parse_markdown(md_text)
        return {name: section.content for name, section in markdown_sections.items()}

    def has_markdown_structure(self, text: str) -> bool:
        """Check if text has markdown headers.

        Args:
            text: Text to check

        Returns:
            True if text contains markdown headers
        """
        # Look for markdown headers (##, ###, etc.)
        return bool(re.search(r"^#{1,6}\s+\w+", text, re.MULTILINE))

    def count_markdown_sections(self, text: str) -> int:
        """Count number of recognized sections in markdown.

        Args:
            text: Markdown text to analyze

        Returns:
            Number of recognized sections
        """
        sections = self.parse_markdown(text)
        return len(sections)

    def get_confidence_score(self, sections: dict[str, MarkdownSection]) -> float:
        """Calculate confidence score for markdown extraction.

        Args:
            sections: Dictionary of extracted sections

        Returns:
            Confidence score between 0 and 1
        """
        if not sections:
            return 0.0

        # High confidence if we have key sections
        key_sections = {"abstract", "introduction", "methods", "results", "discussion"}
        found_keys = key_sections.intersection(sections.keys())

        base_score = len(found_keys) / len(key_sections)

        # Bonus for having conclusion and references
        if "conclusion" in sections:
            base_score += 0.1
        if "references" in sections:
            base_score += 0.1

        # Ensure score is between 0 and 1
        return min(1.0, base_score)


class HybridMarkdownExtractor:
    """Combines markdown parsing with fallback strategies."""

    def __init__(self) -> None:
        """Initialize the hybrid extractor."""
        self.parser = MarkdownParser()
        self.min_sections_for_markdown = 3  # Minimum sections to trust markdown
        self.min_confidence_for_markdown = 0.6  # Minimum confidence to use markdown

    def should_use_markdown(self, text: str) -> bool:
        """Determine if markdown parsing should be used.

        Args:
            text: Text to analyze

        Returns:
            True if markdown parsing is appropriate
        """
        if not self.parser.has_markdown_structure(text):
            return False

        # Parse and check quality
        sections = self.parser.parse_markdown(text)

        # Check if we have enough sections
        if len(sections) < self.min_sections_for_markdown:
            return False

        # Check confidence
        confidence = self.parser.get_confidence_score(sections)
        if confidence < self.min_confidence_for_markdown:
            return False

        # Check that sections have reasonable content
        return any(section.content and len(section.content.strip()) > 50 for section in sections.values())

    def extract_with_fallback(self, text: str) -> tuple[dict[str, str], str]:
        """Extract sections with automatic fallback.

        Args:
            text: Text to extract from (could be markdown or plain)

        Returns:
            Tuple of (sections dict, method used)
        """
        # Try markdown parsing first if appropriate
        if self.should_use_markdown(text):
            try:
                sections = self.parser.extract_sections_from_markdown(text)
                if sections:
                    logger.info("Successfully extracted %d sections via markdown", len(sections))
                    return sections, "markdown"
            except Exception as e:
                logger.warning("Markdown parsing failed: %s", e)

        # Return empty dict to trigger regex fallback
        return {}, "regex_fallback"
