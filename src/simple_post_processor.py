#!/usr/bin/env python3
"""Lightweight post-processing with integrated validation for extracted sections."""

import re
from typing import ClassVar


class SimplePostProcessor:
    """Lightweight post-processing with integrated validation."""

    def __init__(self) -> None:
        """Initialize the post processor."""
        # Track truncations for reporting
        self.truncation_stats: dict[str, int] = {}

        # Single configuration dict for all limits - production quality
        self.limits = {
            "abstract": {"min": 100, "max": 5000, "min_words": 20},
            "introduction": {"min": 150, "max": 15000, "min_words": 15},
            "methods": {"min": 150, "max": 25000, "min_words": 15},
            "results": {"min": 150, "max": 25000, "min_words": 15},
            "discussion": {"min": 150, "max": 20000, "min_words": 15},
            "conclusion": {"min": 80, "max": 8000, "min_words": 10},
            "references": {"min": 50, "max": 75000, "min_words": 3},
        }

        # Contamination patterns - comprehensive for real papers
        self.contamination_markers = {
            "abstract": [
                "1. Introduction",
                "Keywords:",
                "*Correspondence",
                "Author information",
                "Article history:",
                "Received:",
                "Accepted:",
                "Published online:",
            ],
            "introduction": [
                "2. Methods",
                "2 Methods",
                "Materials and Methods",
                "Methodology",
                "2. Materials",
                "Study design",
            ],
            "methods": [
                "3. Results",
                "3 Results",
                "Results and Discussion",
                "Findings",
                "3. Findings",
                "Statistical analysis results",
            ],
            "results": [
                "4. Discussion",
                "4 Discussion",
                "Conclusions",
                "Interpretation",
                "4. Interpretation",
                "Clinical implications",
            ],
            "discussion": [
                "5. Conclusion",
                "References",
                "Bibliography",
                "Acknowledgments",
                "Author contributions",
                "Funding",
                "Conflicts of interest",
                "Supplementary",
                "Appendix",
            ],
        }

    def process_sections(self, sections: dict[str, str]) -> dict[str, str]:
        """Single-pass processing of all sections."""
        processed = {}

        for name, content in sections.items():
            if not content or not isinstance(content, str):
                continue

            # Step 1: Remove contamination (truncate at markers)
            content = self._remove_contamination(content, name)

            # Step 2: Clean common artifacts
            content = self._clean_artifacts(content)

            # Step 3: Apply length limits
            content = self._apply_limits(content, name)

            # Step 4: Final validation
            if self._is_valid(content, name):
                processed[name] = content

        return processed

    def _remove_contamination(self, content: str, section_name: str) -> str:
        """Remove content that belongs to other sections."""
        markers = self.contamination_markers.get(section_name, [])

        for marker in markers:
            # Case-insensitive search for marker
            idx = content.lower().find(marker.lower())
            if idx > 0:  # Only truncate if marker is not at the very beginning
                # Truncate at marker, keeping content before it
                truncated = content[:idx].rstrip()
                if truncated:  # Only use truncation if we still have content
                    content = truncated
                    break

        return content

    def _clean_artifacts(self, content: str) -> str:
        """Remove common PDF extraction artifacts."""
        # Remove excessive whitespace (but preserve paragraph breaks)
        content = re.sub(r"[ \t]+", " ", content)  # Horizontal whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)  # Multiple newlines to double

        # Remove isolated page numbers (common patterns)
        content = re.sub(r"\n\s*\d{1,3}\s*\n", "\n", content)

        # Remove repeated dots (........)
        content = re.sub(r"\.{4,}", "", content)

        # Fix hyphenation at line breaks
        content = re.sub(r"(\w+)-\s+(\w+)", r"\1\2", content)

        # Remove common header/footer artifacts
        content = re.sub(r"Downloaded from.*?on \d{2}/\d{2}/\d{4}", "", content, flags=re.IGNORECASE)
        content = re.sub(r"© \d{4}.*?All rights reserved\.?", "", content, flags=re.IGNORECASE)

        return content.strip()

    def _apply_limits(self, content: str, section_name: str) -> str:
        """Apply minimum length constraints only - NO TRUNCATION for data preservation."""
        limits = self.limits.get(section_name, {"min": 50})

        # Too short? Return empty (will fail validation)
        if len(content) < limits["min"]:
            return ""

        # NO MAXIMUM LIMITS - preserve all content
        # Track unusually long sections for quality monitoring
        expected_max = limits.get("max", 50000)
        if len(content) > expected_max * 1.5:  # 50% over expected
            # Log but don't truncate
            self.truncation_stats[f"{section_name}_overlength"] = len(content)

        return content

    def _is_valid(self, content: str, section_name: str) -> bool:
        """Simple validation check."""
        if not content:
            return False

        limits = self.limits.get(section_name, {"min_words": 10})
        word_count = len(content.split())

        return word_count >= limits["min_words"]


class StructuredAbstractHandler:
    """Handles abstracts with internal structure (Background, Methods, etc.)."""

    STRUCTURED_MARKERS: ClassVar[list[str]] = [
        "Background:",
        "Objective:",
        "Objectives:",
        "Purpose:",
        "Aim:",
        "Aims:",
        "Methods:",
        "Methodology:",
        "Design:",
        "Setting:",
        "Participants:",
        "Patients:",
        "Subjects:",
        "Materials and Methods:",
        "Study Design:",
        "Results:",
        "Findings:",
        "Main Outcome Measures:",
        "Outcomes:",
        "Conclusion:",
        "Conclusions:",
        "Interpretation:",
        "Implications:",
        "Significance:",
        "Clinical Relevance:",
        "Context:",
        "Importance:",
    ]

    def clean_structured_abstract(self, abstract_text: str) -> str:
        """Remove structure markers while preserving content."""
        # Detect if abstract is structured (at least 2 markers in first 1000 chars)
        sample = abstract_text[:1000] if len(abstract_text) > 1000 else abstract_text
        marker_count = sum(1 for marker in self.STRUCTURED_MARKERS if marker.lower() in sample.lower())

        if marker_count < 2:
            return abstract_text  # Not structured, return as-is

        # Remove markers but keep content
        cleaned = abstract_text
        for marker in self.STRUCTURED_MARKERS:
            # Replace "Marker:" with space to join sentences
            pattern = re.compile(rf"\b{re.escape(marker)}\s*", re.IGNORECASE)
            cleaned = pattern.sub(" ", cleaned)

        # Clean up multiple spaces and normalize
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Ensure sentences flow properly (lowercase letter followed by uppercase)
        cleaned = re.sub(r"([a-z])\s+([A-Z])", r"\1. \2", cleaned)

        return cleaned

    def extract_structured_components(self, abstract_text: str) -> dict[str, str] | None:
        """Extract components separately if needed for analysis."""
        # Check if abstract is structured
        if sum(1 for marker in self.STRUCTURED_MARKERS if marker.lower() in abstract_text.lower()[:1000]) < 2:
            return None

        components = {}

        # Create regex pattern for all markers
        all_markers = "|".join(re.escape(m) for m in self.STRUCTURED_MARKERS)
        pattern = rf"({all_markers})\s*(.*?)(?=(?:{all_markers})|\Z)"

        matches = re.finditer(pattern, abstract_text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            key = match.group(1).rstrip(":").lower()
            value = match.group(2).strip()
            if value:  # Only add non-empty components
                components[key] = value

        return components if components else None
