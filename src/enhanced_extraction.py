#!/usr/bin/env python3
"""Enhanced extraction strategies for abstract and section boundary detection."""

import re
from typing import Any
from re import Match
from dataclasses import dataclass


@dataclass
class ExtractionResult:
    """Result of an extraction attempt."""

    content: str
    confidence: float
    method: str
    start_pos: int = 0
    end_pos: int = 0


class EnhancedAbstractExtractor:
    """Multiple strategies for robust abstract extraction."""

    def __init__(self) -> None:
        """Initialize the abstract extractor."""
        # Common abstract indicators
        self.abstract_markers = [
            r"(?:^|\n)\s*(?:ABSTRACT|Abstract|Summary|SUMMARY)[:.]?\s*\n",
            r"(?:^|\n)\s*(?:Background|Objective|Purpose|Aim)[:.]?\s*(?=\n|[A-Z])",
        ]

    def extract_abstract(self, text: str, metadata: dict[str, Any] | None = None) -> ExtractionResult | None:
        """Try multiple strategies to extract abstract."""
        # Strategy 1: Use metadata if available (Zotero abstract)
        if metadata and metadata.get("abstract"):
            abstract = str(metadata["abstract"]).strip()
            if len(abstract) > 50:
                return ExtractionResult(content=abstract, confidence=1.0, method="metadata")

        # Strategy 2: Look for explicit abstract label
        result = self._extract_labeled_abstract(text)
        if result and self._validate_abstract(result.content):
            return result

        # Strategy 3: Extract between title area and first section
        result = self._extract_positional_abstract(text)
        if result and self._validate_abstract(result.content):
            return result

        # Strategy 4: Look for structured abstract indicators
        result = self._extract_structured_abstract(text)
        if result and self._validate_abstract(result.content):
            return result

        # Strategy 5: Use first substantial paragraph as fallback
        result = self._extract_fallback_abstract(text)
        if result:
            return result

        return None

    def _extract_labeled_abstract(self, text: str) -> ExtractionResult | None:
        """Extract abstract with explicit label."""
        for pattern in self.abstract_markers:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                start = match.end()

                # Find end of abstract (next section or keywords)
                end_patterns = [
                    r"\n\s*(?:Introduction|Background|1\.?\s*Introduction)\s*\n",
                    r"\n\s*(?:Keywords?|Key\s*words?)[:.]",
                    r"\n\s*\*?\s*(?:Correspondence|Author)",
                    r"\n\s*(?:INTRODUCTION|BACKGROUND)\s*\n",
                ]

                end_pos = len(text)
                for end_pattern in end_patterns:
                    end_match = re.search(end_pattern, text[start : start + 5000], re.IGNORECASE)
                    if end_match:
                        end_pos = min(end_pos, start + end_match.start())

                abstract = text[start:end_pos].strip()
                if abstract:
                    return ExtractionResult(
                        content=abstract, confidence=0.95, method="labeled", start_pos=start, end_pos=end_pos
                    )
        return None

    def _extract_positional_abstract(self, text: str) -> ExtractionResult | None:
        """Extract abstract based on position (after title, before intro)."""
        # Skip likely title/author area (typical paper has 200-500 chars of header)
        start_search = 200

        # Look for introduction start
        intro_pattern = r"\n\s*(?:1\.?\s*)?(?:Introduction|INTRODUCTION|Background)\s*\n"
        intro_match = re.search(intro_pattern, text[start_search:], re.IGNORECASE)

        if intro_match:
            # Extract text between title area and introduction
            abstract_area = text[start_search : start_search + intro_match.start()]

            # Find substantial paragraphs
            paragraphs = [p.strip() for p in abstract_area.split("\n\n") if p.strip()]

            # Look for paragraph that looks like abstract (100-3000 chars for real papers)
            for para in paragraphs[:5]:  # Check first 5 paragraphs
                if 100 < len(para) < 3000 and not para.startswith(("Table", "Figure", "doi:", "http")):
                    # Find exact position of this paragraph
                    para_pos = text.find(para, start_search)
                    if para_pos == -1:
                        para_pos = text.find(para)
                    return ExtractionResult(
                        content=para,
                        confidence=0.85,
                        method="positional",
                        start_pos=para_pos,
                        end_pos=para_pos + len(para) if para_pos >= 0 else len(para),
                    )

        return None

    def _extract_structured_abstract(self, text: str) -> ExtractionResult | None:
        """Extract structured abstract (Background: Methods: Results: etc.)."""
        # Look for structured abstract pattern
        structured_pattern = r"(?:Background|Objective|Purpose)[:.]\s*[A-Z]"

        match = re.search(structured_pattern, text[:3000], re.IGNORECASE)
        if match:
            start = match.start()

            # Find end (usually at Introduction or after 2000 chars)
            end_pattern = r"\n\s*(?:Introduction|Keywords?|1\.?\s*Introduction)"
            end_match = re.search(end_pattern, text[start : start + 3000], re.IGNORECASE)

            if end_match:
                end = start + end_match.start()
            else:
                # Take up to 2000 chars or next double newline
                end = min(start + 2000, len(text))
                next_break = text[start:end].find("\n\n")
                if next_break > 0:
                    end = start + next_break

            abstract = text[start:end].strip()
            if abstract:
                return ExtractionResult(
                    content=abstract, confidence=0.9, method="structured", start_pos=start, end_pos=end
                )

        return None

    def _extract_fallback_abstract(self, text: str) -> ExtractionResult | None:
        """Use first substantial paragraph as abstract."""
        # Skip first 50 chars (likely title)
        text_body = text[50:]

        # Find first substantial paragraph
        paragraphs = text_body.split("\n\n")

        for para in paragraphs[:10]:  # Check first 10 paragraphs
            para = para.strip()
            # Good paragraph: 100-2000 chars, starts with capital, doesn't look like header
            if (
                100 < len(para) < 2000
                and para[0].isupper()
                and not re.match(r"^(?:\d+\.?|Table|Figure|doi:|http|\*)", para)
            ):
                para_pos = text.find(para)
                return ExtractionResult(
                    content=para,
                    confidence=0.7,
                    method="fallback",
                    start_pos=para_pos if para_pos >= 0 else 200,
                    end_pos=(para_pos + len(para)) if para_pos >= 0 else (200 + len(para)),
                )

        return None

    def _validate_abstract(self, content: str) -> bool:
        """Validate abstract quality."""
        if not content:
            return False

        # Length checks
        if len(content) < 50 or len(content) > 5000:
            return False

        # Check for contamination (shouldn't contain these at start of lines)
        bad_patterns = [
            r"^\s*\d+\.?\s+Introduction",
            r"^\s*Table\s+\d+",
            r"^\s*Figure\s+\d+",
            r"^\s*\*\s*Correspondence",
            r"\nKeywords?:",  # Keywords often appear at end
        ]

        for pattern in bad_patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return False

        # Minimum word count for production quality
        word_count = len(content.split())
        return word_count >= 20  # Production threshold for quality abstracts


class ContentBasedBoundaryDetector:
    """Detect section boundaries using content analysis."""

    def __init__(self) -> None:
        """Initialize the boundary detector."""
        # Define what typically follows each section
        self.next_sections = {
            "abstract": ["introduction", "background", "1.", "keywords", "key words"],
            "introduction": ["methods", "methodology", "2.", "materials", "materials and methods"],
            "methods": ["results", "findings", "3.", "statistical analysis"],
            "results": ["discussion", "4.", "interpretation"],
            "discussion": ["conclusion", "conclusions", "references", "5.", "acknowledgments"],
            "conclusion": ["references", "bibliography", "acknowledgments", "appendix"],
        }

        # Search scope for finding next section (NOT truncation limits)
        # We search this far ahead for the next section marker
        self.search_scope = {
            "abstract": 5000,  # Look up to 5k chars for next section
            "introduction": 20000,  # Intros can be long
            "methods": 30000,  # Methods can be very detailed
            "results": 30000,  # Results with multiple experiments
            "discussion": 25000,  # Thorough discussions
            "conclusion": 10000,  # Conclusions usually shorter
            "references": 100000,  # References can be extremely long
        }

    def find_section_boundary(self, text: str, start_pos: int, section_type: str) -> int:
        """Find where a section ends based on content patterns.

        IMPORTANT: This limits SEARCH scope, not content extraction.
        If no boundary found within search_limit, ALL remaining text is included.
        """
        # Get text after section start
        text_after = text[start_pos:]
        search_limit = self.search_scope.get(section_type, 20000)

        # Look for next section indicators within search limit
        # If not found, we'll take everything (no truncation)
        next_indicators = self.next_sections.get(section_type, [])
        search_end = min(len(text_after), search_limit)  # How far to SEARCH
        actual_end = len(text_after)  # Default: take ALL if no boundary found

        found_boundary = False
        for indicator in next_indicators:
            # Build pattern for section header
            if indicator.endswith("."):
                # Numbered section
                pattern = rf"(?:^|\n)\s*{re.escape(indicator)}\s*\w+"
            else:
                # Named section
                pattern = rf"(?:^|\n)\s*{re.escape(indicator)}[:.]?\s*(?:\n|[A-Z])"

            # Only search within search_limit for performance
            match = re.search(pattern, text_after[:search_end], re.IGNORECASE | re.MULTILINE)
            if match:
                actual_end = min(actual_end, match.start())
                found_boundary = True

        # Also check for common end markers (within search scope)
        end_markers = [
            r"\n\s*References\s*\n",
            r"\n\s*REFERENCES\s*\n",
            r"\n\s*Bibliography\s*\n",
            r"\n\s*Acknowledgments?\s*\n",
            r"\n\s*Author Contributions?\s*\n",
            r"\n\s*Funding\s*\n",
            r"\n\s*Conflicts?\s+of\s+Interest\s*\n",
            r"\n\s*Supplementary\s+Materials?\s*\n",
        ]

        for pattern_str in end_markers:
            match = re.search(pattern_str, text_after[:search_end], re.IGNORECASE)
            if match:
                actual_end = min(actual_end, match.start())
                found_boundary = True

        # If we found a boundary, try to end at a clean break
        if found_boundary and actual_end > 100:
            # Try to find clean paragraph break
            last_para_break = text_after[:actual_end].rfind("\n\n")
            if last_para_break > actual_end * 0.7:  # If we have at least 70% of content
                actual_end = last_para_break
            else:
                # Look for sentence end near boundary
                search_start = max(0, actual_end - 200)
                sentence_ends = []
                for match in re.finditer(r"[.!?]\s*\n", text_after[search_start:actual_end]):
                    sentence_ends.append(search_start + match.end())

                if sentence_ends:
                    actual_end = sentence_ends[-1]

        # Return the actual end position (might be entire remaining text)
        return start_pos + actual_end

    def extract_section_with_boundaries(
        self, text: str, section_name: str, start_match: Match[str]
    ) -> tuple[str, int, int]:
        """Extract section content with proper boundary detection."""
        # Start position is after the section header
        start_pos = start_match.end()

        # Skip any whitespace after header
        while start_pos < len(text) and text[start_pos] in "\n\r\t ":
            start_pos += 1

        # Find end position using boundary detection
        end_pos = self.find_section_boundary(text, start_pos, section_name)

        # Extract content
        content = text[start_pos:end_pos].strip()

        return content, start_pos, end_pos
