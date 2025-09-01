"""Modern PDF Extractor using PyMuPDF4LLM and Marker-PDF.

This extractor uses state-of-the-art libraries for academic PDF extraction,
addressing the issues found in 47.9% of papers in the knowledge base.
"""

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Try to import modern libraries
PYMUPDF4LLM_AVAILABLE = False
MARKER_AVAILABLE = False

try:
    import pymupdf4llm

    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    logger.warning("pymupdf4llm not available. Install with: pip install pymupdf4llm")

try:
    from marker.convert import convert_single_pdf
    from marker.models import load_all_models

    MARKER_AVAILABLE = True
except ImportError:
    logger.warning("marker-pdf not available. Install with: pip install marker-pdf")

# Fallback to basic PyMuPDF if needed
try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available")


@dataclass
class ExtractedSection:
    """Represents an extracted section with metadata."""

    content: str
    confidence: float
    method: str
    word_count: int = 0
    has_contamination: bool = False


class ModernPDFExtractor:
    """Modern PDF extractor using PyMuPDF4LLM and Marker-PDF."""

    # Structured abstract markers to clean
    STRUCTURED_MARKERS = [
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
        "Results:",
        "Findings:",
        "Main Outcome Measures:",
        "Conclusion:",
        "Conclusions:",
        "Interpretation:",
        "Implications:",
        "Importance:",
        "Context:",
        "Evidence:",
        "Data Sources:",
    ]

    # Section contamination patterns
    CONTAMINATION_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:background|objective|methods?|methodology|results?|findings?|"
        r"discussion|conclusions?|purpose|aims?|design|setting|participants?|"
        r"intervention|outcome\s+measures?|data\s+sources?):\s*",
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(self, use_marker_fallback: bool = True, max_abstract_length: int = 3000):
        """Initialize the modern extractor.

        Args:
            use_marker_fallback: Whether to use Marker-PDF for difficult documents
            max_abstract_length: Maximum allowed abstract length
        """
        self.use_marker_fallback = use_marker_fallback and MARKER_AVAILABLE
        self.max_abstract_length = max_abstract_length
        self.extraction_stats = {}

        # Load Marker models once if available
        if self.use_marker_fallback:
            try:
                self.marker_models = load_all_models()
                logger.info("Marker models loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load Marker models: {e}")
                self.use_marker_fallback = False

    def extract(self, pdf_path: str) -> dict[str, Any]:
        """Extract sections from PDF using modern libraries.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extracted sections and metadata
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return {"error": f"File not found: {pdf_path}"}

        # Try extraction methods in order of preference
        sections = {}
        method_used = "none"

        # Method 1: PyMuPDF4LLM (fast, good quality)
        if PYMUPDF4LLM_AVAILABLE:
            try:
                sections, method_used = self._extract_with_pymupdf4llm(pdf_path)

                # Check if we need better extraction
                if self._needs_better_extraction(sections):
                    if self.use_marker_fallback:
                        sections, method_used = self._extract_with_marker(pdf_path)
            except Exception as e:
                logger.error(f"PyMuPDF4LLM extraction failed: {e}")

        # Method 2: Marker-PDF (slower, highest quality)
        if not sections and self.use_marker_fallback:
            try:
                sections, method_used = self._extract_with_marker(pdf_path)
            except Exception as e:
                logger.error(f"Marker extraction failed: {e}")

        # Method 3: Fallback to basic PyMuPDF
        if not sections and PYMUPDF_AVAILABLE:
            sections, method_used = self._extract_with_basic_pymupdf(pdf_path)

        # Clean and validate sections
        sections = self._clean_sections(sections)

        # Calculate metrics
        processing_time = time.time() - start_time

        return {
            "sections": sections,
            "metadata": {
                "method_used": method_used,
                "processing_time": processing_time,
                "sections_found": len(sections),
                "total_words": sum(s.word_count for s in sections.values()),
                "quality_issues": self._detect_quality_issues(sections),
            },
        }

    def _extract_with_pymupdf4llm(self, pdf_path: Path) -> tuple[dict[str, ExtractedSection], str]:
        """Extract using PyMuPDF4LLM."""
        # Convert to markdown
        md_text = pymupdf4llm.to_markdown(str(pdf_path))

        # Parse markdown sections
        sections = self._parse_markdown_sections(md_text)

        return sections, "pymupdf4llm"

    def _extract_with_marker(self, pdf_path: Path) -> tuple[dict[str, ExtractedSection], str]:
        """Extract using Marker-PDF."""
        # Convert using Marker
        full_text, images, metadata = convert_single_pdf(
            str(pdf_path), self.marker_models if hasattr(self, "marker_models") else None, batch_multiplier=2
        )

        # Parse the extracted text
        sections = self._parse_markdown_sections(full_text)

        return sections, "marker"

    def _extract_with_basic_pymupdf(self, pdf_path: Path) -> tuple[dict[str, ExtractedSection], str]:
        """Fallback extraction using basic PyMuPDF."""
        doc = fitz.open(str(pdf_path))
        text = ""

        for page in doc:
            text += page.get_text()

        doc.close()

        # Basic section parsing
        sections = self._parse_basic_text(text)

        return sections, "basic_pymupdf"

    def _parse_markdown_sections(self, md_text: str) -> dict[str, ExtractedSection]:
        """Parse sections from markdown text."""
        sections = {}
        current_section = None
        current_content = []
        current_level = 0

        for line in md_text.split("\n"):
            # Check for markdown headers
            if line.startswith("#"):
                # Save previous section
                if current_section and current_content:
                    content = "\n".join(current_content).strip()
                    sections[current_section] = ExtractedSection(
                        content=content,
                        confidence=0.9,
                        method="markdown_parse",
                        word_count=len(content.split()),
                    )

                # Determine section level and name
                level = len(line) - len(line.lstrip("#"))
                header = line.lstrip("#").strip().lower()

                # Map header to standard section name
                section_name = self._map_header_to_section(header)
                if section_name:
                    current_section = section_name
                    current_content = []
                    current_level = level

            elif current_section:
                current_content.append(line)

        # Don't forget last section
        if current_section and current_content:
            content = "\n".join(current_content).strip()
            sections[current_section] = ExtractedSection(
                content=content, confidence=0.9, method="markdown_parse", word_count=len(content.split())
            )

        return sections

    def _parse_basic_text(self, text: str) -> dict[str, ExtractedSection]:
        """Parse sections from basic text using patterns."""
        sections = {}

        # Define section patterns
        patterns = {
            "abstract": r"(?:^|\n)\s*(?:abstract|summary)\s*(?:\n|:)",
            "introduction": r"(?:^|\n)\s*(?:1\.?\s*)?(?:introduction|background)\s*(?:\n|:)",
            "methods": r"(?:^|\n)\s*(?:2\.?\s*)?(?:methods?|methodology|materials?\s+and\s+methods?)\s*(?:\n|:)",
            "results": r"(?:^|\n)\s*(?:3\.?\s*)?(?:results?|findings?)\s*(?:\n|:)",
            "discussion": r"(?:^|\n)\s*(?:4\.?\s*)?(?:discussion)\s*(?:\n|:)",
            "conclusion": r"(?:^|\n)\s*(?:5\.?\s*)?(?:conclusions?|concluding\s+remarks?)\s*(?:\n|:)",
        }

        for section_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                start_pos = match.end()

                # Find end of section (next section or end of text)
                end_pos = len(text)
                for other_name, other_pattern in patterns.items():
                    if other_name != section_name:
                        next_match = re.search(other_pattern, text[start_pos:], re.IGNORECASE | re.MULTILINE)
                        if next_match:
                            end_pos = min(end_pos, start_pos + next_match.start())

                content = text[start_pos:end_pos].strip()

                if content and len(content) > 50:
                    sections[section_name] = ExtractedSection(
                        content=content,
                        confidence=0.7,
                        method="pattern_match",
                        word_count=len(content.split()),
                    )

        return sections

    def _map_header_to_section(self, header: str) -> str | None:
        """Map various header formats to standard section names."""
        header_lower = header.lower()

        # Mapping rules
        if any(x in header_lower for x in ["abstract", "summary", "synopsis"]):
            return "abstract"
        if any(x in header_lower for x in ["introduction", "background", "overview"]):
            return "introduction"
        if any(x in header_lower for x in ["method", "material", "procedure", "approach"]):
            return "methods"
        if any(x in header_lower for x in ["result", "finding", "outcome"]):
            return "results"
        if any(x in header_lower for x in ["discussion", "interpretation"]):
            return "discussion"
        if any(x in header_lower for x in ["conclusion", "summary", "implication"]):
            return "conclusion"
        if any(x in header_lower for x in ["reference", "bibliography", "citation"]):
            return "references"

        return None

    def _needs_better_extraction(self, sections: dict[str, ExtractedSection]) -> bool:
        """Check if extraction quality is poor and needs fallback."""
        if not sections:
            return True

        # Check for abstract issues
        if "abstract" in sections:
            abstract = sections["abstract"]

            # Check for contamination
            if self.CONTAMINATION_PATTERN.search(abstract.content[:500]):
                return True

            # Check for length issues
            if len(abstract.content) > self.max_abstract_length or len(abstract.content) < 100:
                return True
        else:
            # No abstract found
            return True

        # Check if we have too few sections
        if len(sections) < 3:
            return True

        return False

    def _clean_sections(self, sections: dict[str, ExtractedSection]) -> dict[str, ExtractedSection]:
        """Clean and validate all sections."""
        cleaned = {}

        for name, section in sections.items():
            # Clean content
            content = section.content

            # Clean abstract specifically
            if name == "abstract":
                content = self._clean_structured_abstract(content)

            # Remove excessive whitespace
            content = re.sub(r"\s+", " ", content).strip()

            # Remove citation artifacts if excessive
            if content.count("[") > 50:
                content = re.sub(r"\[\d+\]", "", content)

            # Check for contamination
            has_contamination = False
            if name == "abstract" and self.CONTAMINATION_PATTERN.search(content[:500]):
                has_contamination = True

            # Update section
            cleaned[name] = ExtractedSection(
                content=content,
                confidence=section.confidence,
                method=section.method,
                word_count=len(content.split()),
                has_contamination=has_contamination,
            )

        return cleaned

    def _clean_structured_abstract(self, abstract: str) -> str:
        """Remove structured abstract markers while preserving content."""
        cleaned = abstract

        # Remove markers
        for marker in self.STRUCTURED_MARKERS:
            # Replace marker with space to maintain sentence flow
            cleaned = re.sub(rf"\b{re.escape(marker)}\s*", " ", cleaned, flags=re.IGNORECASE)

        # Clean up multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Ensure sentences flow properly (add period if lowercase follows uppercase)
        cleaned = re.sub(r"([a-z])\s+([A-Z])", r"\1. \2", cleaned)

        return cleaned.strip()

    def _detect_quality_issues(self, sections: dict[str, ExtractedSection]) -> dict[str, Any]:
        """Detect quality issues in extracted sections."""
        issues = {
            "empty_abstract": False,
            "short_abstract": False,
            "long_abstract": False,
            "section_contamination": False,
            "missing_sections": [],
            "total_issues": 0,
        }

        # Check abstract
        if "abstract" not in sections:
            issues["empty_abstract"] = True
            issues["missing_sections"].append("abstract")
        else:
            abstract = sections["abstract"]
            if len(abstract.content) < 100:
                issues["short_abstract"] = True
            elif len(abstract.content) > self.max_abstract_length:
                issues["long_abstract"] = True
            if abstract.has_contamination:
                issues["section_contamination"] = True

        # Check for missing critical sections
        critical_sections = ["introduction", "methods", "results", "discussion"]
        for section in critical_sections:
            if section not in sections:
                issues["missing_sections"].append(section)

        # Count total issues
        issues["total_issues"] = (
            issues["empty_abstract"]
            + issues["short_abstract"]
            + issues["long_abstract"]
            + issues["section_contamination"]
            + len(issues["missing_sections"])
        )

        return issues


def compare_extractors(pdf_path: str) -> dict[str, Any]:
    """Compare modern extractor with existing pragmatic extractor.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Comparison results
    """
    from src.pragmatic_section_extractor import PragmaticSectionExtractor

    # Extract with both methods
    modern = ModernPDFExtractor()
    pragmatic = PragmaticSectionExtractor()

    # Modern extraction
    modern_result = modern.extract(pdf_path)

    # Pragmatic extraction
    pragmatic_result = pragmatic.extract(pdf_path)

    # Compare results
    comparison = {
        "pdf_path": str(pdf_path),
        "modern": {
            "sections_found": modern_result["metadata"]["sections_found"],
            "processing_time": modern_result["metadata"]["processing_time"],
            "method_used": modern_result["metadata"]["method_used"],
            "quality_issues": modern_result["metadata"]["quality_issues"]["total_issues"],
            "has_contamination": modern_result["metadata"]["quality_issues"]["section_contamination"],
        },
        "pragmatic": {
            "sections_found": len(pragmatic_result.get("sections", {})),
            "processing_time": pragmatic_result.get("metadata", {}).get("processing_time", 0),
            "tier_used": pragmatic_result.get("metadata", {}).get("tier_used", "unknown"),
            "quality_issues": 0,  # Will calculate below
            "has_contamination": False,  # Will check below
        },
    }

    # Check pragmatic abstract for issues
    if "abstract" in pragmatic_result.get("sections", {}):
        abstract_content = pragmatic_result["sections"]["abstract"]

        # Check for contamination
        contamination_pattern = ModernPDFExtractor.CONTAMINATION_PATTERN
        if contamination_pattern.search(abstract_content[:500]):
            comparison["pragmatic"]["has_contamination"] = True
            comparison["pragmatic"]["quality_issues"] += 1

        # Check length issues
        if len(abstract_content) < 100:
            comparison["pragmatic"]["quality_issues"] += 1
        elif len(abstract_content) > 3000:
            comparison["pragmatic"]["quality_issues"] += 1
    else:
        comparison["pragmatic"]["quality_issues"] += 1  # No abstract

    # Add abstract samples for comparison
    if "abstract" in modern_result.get("sections", {}):
        comparison["modern"]["abstract_preview"] = modern_result["sections"]["abstract"].content[:200]

    if "abstract" in pragmatic_result.get("sections", {}):
        comparison["pragmatic"]["abstract_preview"] = pragmatic_result["sections"]["abstract"][:200]

    # Speed comparison
    if comparison["pragmatic"]["processing_time"] > 0:
        comparison["speed_ratio"] = (
            comparison["modern"]["processing_time"] / comparison["pragmatic"]["processing_time"]
        )

    return comparison


if __name__ == "__main__":
    # Test extraction
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

        # Run comparison
        results = compare_extractors(pdf_path)

        print("\n=== EXTRACTION COMPARISON ===\n")
        print(f"PDF: {results['pdf_path']}\n")

        print("Modern Extractor:")
        print(f"  Method: {results['modern']['method_used']}")
        print(f"  Time: {results['modern']['processing_time']:.2f}s")
        print(f"  Sections: {results['modern']['sections_found']}")
        print(f"  Quality Issues: {results['modern']['quality_issues']}")
        print(f"  Has Contamination: {results['modern']['has_contamination']}")

        print("\nPragmatic Extractor:")
        print(f"  Tier: {results['pragmatic']['tier_used']}")
        print(f"  Time: {results['pragmatic']['processing_time']:.2f}s")
        print(f"  Sections: {results['pragmatic']['sections_found']}")
        print(f"  Quality Issues: {results['pragmatic']['quality_issues']}")
        print(f"  Has Contamination: {results['pragmatic']['has_contamination']}")

        if "speed_ratio" in results:
            print(f"\nSpeed Ratio: {results['speed_ratio']:.2f}x")

        if "abstract_preview" in results["modern"]:
            print(f"\nModern Abstract Preview:\n{results['modern']['abstract_preview']}...")

        if "abstract_preview" in results["pragmatic"]:
            print(f"\nPragmatic Abstract Preview:\n{results['pragmatic']['abstract_preview']}...")
    else:
        print("Usage: python modern_pdf_extractor.py <pdf_path>")
