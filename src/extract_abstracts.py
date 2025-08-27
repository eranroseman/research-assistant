#!/usr/bin/env python3
"""Advanced Abstract Detection and Extraction for Academic Papers.

This script uses multiple strategies to detect and extract abstracts from
academic papers, including those without explicit "Abstract" labels.

Usage:
    python src/extract_abstracts.py
    python src/extract_abstracts.py --input-dir raw_texts
    python src/extract_abstracts.py --sample 100
"""

import json
import re
from pathlib import Path
from typing import Any

import click
from tqdm import tqdm


class AbstractExtractor:
    """Extract abstracts using multiple detection strategies."""

    def __init__(self, input_dir: Path | None = None):
        """Initialize extractor.

        Args:
            input_dir: Directory containing raw text files
        """
        self.input_dir = Path(input_dir) if input_dir else Path("raw_texts")

    def extract_abstract(self, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Extract abstract using multiple strategies.

        Args:
            text: Full paper text
            metadata: Optional paper metadata

        Returns:
            Dictionary with abstract info and confidence score
        """
        result = {"abstract": None, "method": None, "confidence": 0.0, "start_pos": -1, "end_pos": -1}

        # Try strategies in order of reliability
        strategies = [
            ("labeled", self._extract_labeled_abstract),
            ("structured", self._extract_structured_abstract),
            ("positional", self._extract_positional_abstract),
            ("heuristic", self._extract_heuristic_abstract),
            ("doi_based", self._extract_doi_based_abstract),
        ]

        for method_name, method in strategies:
            abstract_text, confidence, start_pos, end_pos = method(text)
            if abstract_text and len(abstract_text) > 100:  # Minimum length check
                result = {
                    "abstract": abstract_text,
                    "method": method_name,
                    "confidence": confidence,
                    "start_pos": start_pos,
                    "end_pos": end_pos,
                }
                break

        return result

    def _extract_labeled_abstract(self, text: str) -> tuple[str | None, float, int, int]:
        """Extract explicitly labeled abstract.

        Returns: (abstract_text, confidence, start_pos, end_pos)
        """
        # Limit search to first 15000 chars (abstracts are always at the beginning)
        search_text = text[:15000]

        # Multiple patterns for labeled abstracts with better boundaries
        patterns = [
            # Standard "Abstract" label with max 3000 chars
            (
                r"(?i)\n\s*abstract\s*\n\s*(.{100,3000}?)(?=\n\s*(?:introduction|background|keywords|1\.\s|introduction\s|background\s|\n\n\n))",
                0.95,
            ),
            # With colon
            (
                r"(?i)\n\s*abstract:\s*\n?\s*(.{100,3000}?)(?=\n\s*(?:introduction|background|keywords|1\.\s|\n\n\n))",
                0.95,
            ),
            # Bold or emphasized
            (
                r"(?i)\*\*abstract\*\*\s*\n\s*(.{100,3000}?)(?=\n\s*(?:introduction|background|keywords|\n\n))",
                0.90,
            ),
            # All caps
            (
                r"\n\s*ABSTRACT\s*\n\s*(.{100,3000}?)(?=\n\s*(?:INTRODUCTION|BACKGROUND|Keywords|1\.\s|\n\n\n))",
                0.95,
            ),
            # Summary variant
            (
                r"(?i)\n\s*summary\s*\n\s*(.{100,3000}?)(?=\n\s*(?:introduction|background|keywords|1\.\s|\n\n))",
                0.85,
            ),
            # Abstract without newline after label
            (r"(?i)\babstract\s+(.{100,2500}?)(?=\n\s*(?:introduction|keywords|1\.\s|background))", 0.85),
        ]

        for pattern, confidence in patterns:
            match = re.search(pattern, search_text, re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = self._clean_abstract_text(abstract)

                # Validate abstract length (typical abstracts are 150-2000 chars, but allow up to 4000)
                if 100 < len(abstract) < 4000:
                    # Check if it's actually an abstract (not capturing too much)
                    # Abstracts usually don't have numbered sections inside (but check conservatively)
                    section_pattern = r"\n\s*\d+\.\d+\s+\w+|\n\s*\d+\.\s+[A-Z][a-z]+\s+[A-Z]"
                    if not re.search(section_pattern, abstract):
                        return abstract, confidence, match.start(), match.end()

        return None, 0.0, -1, -1

    def _extract_structured_abstract(self, text: str) -> tuple[str | None, float, int, int]:
        """Extract structured abstract with sections like Background, Methods, Results.

        Returns: (abstract_text, confidence, start_pos, end_pos)
        """
        # Look for structured abstract pattern
        pattern = r"(?i)((?:background|objective|purpose|aims?)[\s\S]{20,500}?(?:method|design|approach)[\s\S]{20,500}?(?:result|finding)[\s\S]{20,500}?(?:conclusion|implication)[\s\S]{20,500}?)(?=\n\s*(?:keywords|introduction|\d+\.\s*introduction|©|\n\n\n))"

        match = re.search(pattern, text[:10000])  # Check first 10k chars
        if match:
            abstract = match.group(1).strip()
            abstract = self._clean_abstract_text(abstract)
            if 200 < len(abstract) < 3000:  # Reasonable abstract length
                return abstract, 0.85, match.start(), match.end()

        return None, 0.0, -1, -1

    def _extract_positional_abstract(self, text: str) -> tuple[str | None, float, int, int]:
        """Extract abstract based on position after title/authors.

        Returns: (abstract_text, confidence, start_pos, end_pos)
        """
        lines = text.split("\n")

        # Find where main content starts (after title, authors, affiliations)
        content_start = -1
        author_section_end = -1

        # Look for author/affiliation patterns
        for i, line in enumerate(lines[:100]):  # Check first 100 lines
            if re.search(r"@|\.edu|\.com|university|institute|department|college", line.lower()):
                author_section_end = i
            # Look for section headers that indicate content start
            if re.search(r"(?i)^(introduction|background|1\.\s*introduction|keywords)", line):
                if author_section_end > 0 and i > author_section_end + 2:
                    content_start = author_section_end + 1
                    content_end = i
                    break

        if content_start > 0 and content_end > content_start:
            # Extract paragraph(s) between authors and first section
            abstract_lines = []
            for i in range(content_start, min(content_end, content_start + 30)):
                line = lines[i].strip()
                if len(line) > 40:  # Substantial line
                    abstract_lines.append(line)
                elif abstract_lines and not line:  # Empty line after content
                    if len(" ".join(abstract_lines)) > 150:
                        break

            if abstract_lines:
                abstract = " ".join(abstract_lines)
                abstract = self._clean_abstract_text(abstract)
                if 150 < len(abstract) < 2000:
                    # Calculate position in original text
                    start_pos = text.find(abstract_lines[0])
                    end_pos = text.find(abstract_lines[-1]) + len(abstract_lines[-1])
                    return abstract, 0.70, start_pos, end_pos

        return None, 0.0, -1, -1

    def _extract_heuristic_abstract(self, text: str) -> tuple[str | None, float, int, int]:
        """Use heuristics to identify abstract-like content.

        Returns: (abstract_text, confidence, start_pos, end_pos)
        """
        # Look for paragraph that contains key abstract indicators
        abstract_indicators = [
            r"(?i)\bthis\s+(study|paper|article|research)\s+(investigates?|examines?|explores?|analyzes?|presents?|proposes?|describes?|evaluates?|assesses?)",
            r"(?i)\bwe\s+(investigate|examine|explore|analyze|present|propose|describe|evaluate|assess|study)",
            r"(?i)\b(objective|aim|purpose|goal)s?\s+of\s+this\s+(study|paper|research)",
            r"(?i)\bthe\s+present\s+(study|paper|research|article)",
            r"(?i)\bin\s+this\s+(study|paper|article|research)",
        ]

        # Find paragraphs (text blocks between newlines)
        paragraphs = re.split(r"\n\s*\n", text[:10000])

        for i, para in enumerate(paragraphs):
            para = para.strip()
            if 200 < len(para) < 2000:  # Reasonable paragraph length
                # Check if paragraph contains abstract indicators
                indicator_count = sum(1 for pattern in abstract_indicators if re.search(pattern, para))

                # Check for result/conclusion language
                has_results = bool(
                    re.search(
                        r"(?i)\b(results?|findings?|showed|demonstrated|revealed|indicated|suggested)\b", para
                    )
                )
                has_conclusion = bool(
                    re.search(r"(?i)\b(conclude|conclusion|implications?|suggests?)\b", para)
                )

                if indicator_count > 0 and (has_results or has_conclusion):
                    abstract = self._clean_abstract_text(para)
                    start_pos = text.find(para)
                    end_pos = start_pos + len(para)
                    confidence = min(0.60 + (indicator_count * 0.1), 0.75)
                    return abstract, confidence, start_pos, end_pos

        return None, 0.0, -1, -1

    def _extract_doi_based_abstract(self, text: str) -> tuple[str | None, float, int, int]:
        """Extract abstract near DOI location (often at paper start).

        Returns: (abstract_text, confidence, start_pos, end_pos)
        """
        # Find DOI
        doi_pattern = r"(?i)doi:?\s*10\.\d{4,}(?:\.\d+)*\/[-._;()\/:a-zA-Z0-9]+"
        doi_match = re.search(doi_pattern, text[:5000])

        if doi_match:
            # Look for substantial text block near DOI
            doi_pos = doi_match.end()
            # Get text after DOI
            after_doi = text[doi_pos : doi_pos + 3000]

            # Split into paragraphs
            paragraphs = re.split(r"\n\s*\n", after_doi)

            for para in paragraphs:
                para = para.strip()
                # Skip if it's keywords, copyright, or author info
                if re.search(r"(?i)^(keywords|copyright|©|author|affiliation)", para):
                    continue

                if 200 < len(para) < 2000:
                    # Check if it looks like abstract content
                    if not re.search(
                        r"(?i)^(introduction|background|1\.\s*introduction|methods|materials)", para
                    ):
                        abstract = self._clean_abstract_text(para)
                        start_pos = text.find(para)
                        end_pos = start_pos + len(para)
                        return abstract, 0.65, start_pos, end_pos

        return None, 0.0, -1, -1

    def _clean_abstract_text(self, text: str) -> str:
        """Clean extracted abstract text.

        Args:
            text: Raw abstract text

        Returns:
            Cleaned abstract text
        """
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove page numbers
        text = re.sub(r"\n\d+\n", " ", text)

        # Remove headers/footers
        text = re.sub(r"(?i)(frontiers in|journal of|proceedings|volume \d+|page \d+)", "", text)

        # Remove keywords if at the end
        text = re.sub(r"(?i)\s*keywords?:.*$", "", text)

        # Remove citation numbers [1], [2,3], etc.
        text = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", text)

        # Clean up spacing
        text = re.sub(r"\s+([.,;!?])", r"\1", text)
        text = re.sub(r"([.,;!?])(\w)", r"\1 \2", text)

        return text.strip()

    def extract_all_abstracts(self, sample_size: int | None = None) -> dict[str, Any]:
        """Extract abstracts from all text files.

        Args:
            sample_size: If provided, only process this many files

        Returns:
            Extraction statistics and results
        """
        # Load index if available
        index_path = self.input_dir / "extraction_index.json"
        metadata_map = {}
        if index_path.exists():
            with open(index_path) as f:
                index = json.load(f)
                for paper in index.get("papers", []):
                    metadata_map[paper["output_file"]] = paper

        # Get text files
        text_files = list(self.input_dir.glob("*.txt"))
        if sample_size:
            text_files = text_files[:sample_size]

        results = []
        stats = {
            "total_files": len(text_files),
            "abstracts_found": 0,
            "method_counts": {},
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
            "avg_abstract_length": 0,
        }

        print(f"Extracting abstracts from {len(text_files)} files...")

        for text_file in tqdm(text_files, desc="Extracting abstracts"):
            try:
                text = text_file.read_text(encoding="utf-8", errors="ignore")
                metadata = metadata_map.get(text_file.name, {})

                result = self.extract_abstract(text, metadata)
                result["filename"] = text_file.name
                result["title"] = metadata.get("title", "Unknown")

                if result["abstract"]:
                    stats["abstracts_found"] += 1
                    method = result["method"]
                    stats["method_counts"][method] = stats["method_counts"].get(method, 0) + 1

                    # Categorize confidence
                    if result["confidence"] >= 0.8:
                        stats["confidence_distribution"]["high"] += 1
                    elif result["confidence"] >= 0.6:
                        stats["confidence_distribution"]["medium"] += 1
                    else:
                        stats["confidence_distribution"]["low"] += 1

                results.append(result)

            except Exception as e:
                print(f"Error processing {text_file.name}: {e}")

        # Calculate statistics
        if stats["abstracts_found"] > 0:
            total_length = sum(len(r["abstract"]) for r in results if r["abstract"])
            stats["avg_abstract_length"] = total_length / stats["abstracts_found"]

        stats["detection_rate"] = (
            (stats["abstracts_found"] / stats["total_files"] * 100) if stats["total_files"] > 0 else 0
        )

        return {"stats": stats, "results": results}

    def save_results(self, data: dict[str, Any], output_file: Path | None = None):
        """Save extraction results to JSON file.

        Args:
            data: Results data
            output_file: Output file path
        """
        if not output_file:
            output_file = self.input_dir / "abstracts_extracted.json"

        # Prepare data for JSON serialization
        save_data = {"stats": data["stats"], "abstracts": []}

        for result in data["results"]:
            if result["abstract"]:
                save_data["abstracts"].append(
                    {
                        "filename": result["filename"],
                        "title": result["title"],
                        "abstract": result["abstract"][:500] + "..."
                        if len(result["abstract"]) > 500
                        else result["abstract"],
                        "method": result["method"],
                        "confidence": result["confidence"],
                        "length": len(result["abstract"]),
                    }
                )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_file}")

    def print_report(self, data: dict[str, Any]):
        """Print extraction report.

        Args:
            data: Results data
        """
        stats = data["stats"]

        print("\n" + "=" * 60)
        print("ABSTRACT EXTRACTION REPORT")
        print("=" * 60)
        print(f"\nTotal files processed: {stats['total_files']}")
        print(f"Abstracts found: {stats['abstracts_found']} ({stats['detection_rate']:.1f}%)")
        print(f"Average abstract length: {stats['avg_abstract_length']:.0f} characters")

        print("\nDetection methods used:")
        for method, count in sorted(stats["method_counts"].items(), key=lambda x: x[1], reverse=True):
            percentage = count / stats["abstracts_found"] * 100 if stats["abstracts_found"] > 0 else 0
            print(f"  {method}: {count} ({percentage:.1f}%)")

        print("\nConfidence distribution:")
        total = sum(stats["confidence_distribution"].values())
        if total > 0:
            for level in ["high", "medium", "low"]:
                count = stats["confidence_distribution"][level]
                percentage = count / total * 100
                print(f"  {level} (>0.8, 0.6-0.8, <0.6): {count} ({percentage:.1f}%)")

        # Show examples from each method
        print("\nExample abstracts by detection method:")
        shown_methods = set()
        for result in data["results"][:100]:  # Check first 100
            if result["abstract"] and result["method"] not in shown_methods:
                shown_methods.add(result["method"])
                print(f"\n{result['method'].upper()} (confidence: {result['confidence']:.2f}):")
                print(f"  Title: {result['title'][:60]}...")
                print(f"  Abstract: {result['abstract'][:150]}...")

                if len(shown_methods) >= len(stats["method_counts"]):
                    break

        print("\n" + "=" * 60)


@click.command()
@click.option(
    "--input-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default="raw_texts",
    help="Directory containing raw text files",
)
@click.option("--sample", type=int, default=None, help="Process only a sample of files")
@click.option(
    "--output",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Output file for results",
)
def main(input_dir: Path, sample: int | None, output: Path | None):
    """Extract abstracts from academic papers using multiple strategies."""
    extractor = AbstractExtractor(input_dir)

    # Extract abstracts
    data = extractor.extract_all_abstracts(sample_size=sample)

    # Print report
    extractor.print_report(data)

    # Save results
    extractor.save_results(data, output_file=output)

    return 0


if __name__ == "__main__":
    exit(main())
