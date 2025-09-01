#!/usr/bin/env python3
"""Analyze raw extracted texts from PDFs.

This script provides analysis tools for the raw text files extracted
from PDFs, helping to understand the quality of text extraction and
identify patterns in section detection issues.

Usage:
    python src/analyze_raw_texts.py
    python src/analyze_raw_texts.py --input-dir raw_texts
    python src/analyze_raw_texts.py --sample 10
"""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import click
from tqdm import tqdm


class RawTextAnalyzer:
    """Analyze raw extracted text files."""

    # Common section headers in academic papers
    SECTION_PATTERNS = [
        r"(?i)^\s*abstract\s*$",
        r"(?i)^\s*introduction\s*$",
        r"(?i)^\s*background\s*$",
        r"(?i)^\s*literature\s+review\s*$",
        r"(?i)^\s*methods?\s*$",
        r"(?i)^\s*methodology\s*$",
        r"(?i)^\s*materials?\s+and\s+methods?\s*$",
        r"(?i)^\s*results?\s*$",
        r"(?i)^\s*findings?\s*$",
        r"(?i)^\s*discussion\s*$",
        r"(?i)^\s*conclusions?\s*$",
        r"(?i)^\s*references?\s*$",
        r"(?i)^\s*bibliography\s*$",
        r"(?i)^\s*acknowledgments?\s*$",
        r"(?i)^\s*appendix\s*",
        r"(?i)^\s*supplementary\s+",
        r"(?i)^\s*\d+\.?\s*(introduction|background|methods|results|discussion|conclusion)",
    ]

    def __init__(self, input_dir: Path | None = None):
        """Initialize analyzer.

        Args:
            input_dir: Directory containing raw text files
        """
        self.input_dir = Path(input_dir) if input_dir else Path("raw_texts")

    def analyze_text_quality(self, text: str) -> dict[str, Any]:
        """Analyze the quality of extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Dictionary with quality metrics
        """
        lines = text.split("\n")

        # Basic metrics
        metrics = {
            "total_chars": len(text),
            "total_lines": len(lines),
            "non_empty_lines": sum(1 for line in lines if line.strip()),
            "avg_line_length": sum(len(line) for line in lines) / max(len(lines), 1),
            "total_words": len(text.split()),
        }

        # Check for common extraction issues
        metrics["garbled_text_ratio"] = self._calculate_garbled_ratio(text)
        metrics["excessive_whitespace"] = text.count("  ") / max(len(text), 1)
        metrics["line_break_issues"] = sum(1 for line in lines if len(line) > 200) / max(len(lines), 1)

        # Detect sections
        sections_found = []
        for pattern in self.SECTION_PATTERNS:
            for line in lines:
                if re.match(pattern, line):
                    sections_found.append(line.strip())
                    break

        metrics["sections_detected"] = len(sections_found)
        metrics["section_names"] = sections_found[:10]  # First 10 sections

        # Check for common paper elements
        metrics["has_abstract"] = bool(re.search(r"(?i)\babstract\b", text))
        metrics["has_introduction"] = bool(re.search(r"(?i)\bintroduction\b", text))
        metrics["has_methods"] = bool(re.search(r"(?i)\bmethods?\b", text))
        metrics["has_results"] = bool(re.search(r"(?i)\bresults?\b", text))
        metrics["has_discussion"] = bool(re.search(r"(?i)\bdiscussion\b", text))
        metrics["has_conclusion"] = bool(re.search(r"(?i)\bconclusions?\b", text))
        metrics["has_references"] = bool(re.search(r"(?i)\breferences?\b", text))

        # Check for DOI
        doi_pattern = r"10\.\d{4,}(?:\.\d+)*\/[-._;()\/:a-zA-Z0-9]+"
        dois = re.findall(doi_pattern, text)
        metrics["has_doi"] = len(dois) > 0
        metrics["doi_count"] = len(dois)

        # Check for email addresses (indicates author information)
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, text)
        metrics["has_emails"] = len(emails) > 0
        metrics["email_count"] = len(emails)

        # Estimate readability
        metrics["readable_score"] = self._calculate_readability_score(metrics)

        return metrics

    def _calculate_garbled_ratio(self, text: str) -> float:
        """Calculate ratio of potentially garbled text.

        Args:
            text: Text to analyze

        Returns:
            Ratio of garbled characters (0-1)
        """
        # Look for common signs of garbled text
        garbled_patterns = [
            r"[^\x00-\x7F]{3,}",  # Non-ASCII sequences
            r"[^a-zA-Z0-9\s\.\,\;\:\!\?\-\(\)\'\"]{5,}",  # Unusual character sequences
            r"(\w)\1{5,}",  # Repeated characters
        ]

        garbled_chars = 0
        for pattern in garbled_patterns:
            matches = re.findall(pattern, text)
            garbled_chars += sum(len(match) for match in matches)

        return garbled_chars / max(len(text), 1)

    def _calculate_readability_score(self, metrics: dict[str, Any]) -> float:
        """Calculate overall readability score.

        Args:
            metrics: Text metrics

        Returns:
            Readability score (0-100)
        """
        score = 100.0

        # Penalize for issues
        score -= metrics["garbled_text_ratio"] * 50
        score -= metrics["excessive_whitespace"] * 20
        score -= metrics["line_break_issues"] * 10

        # Reward for having standard sections
        section_bonus = sum(
            [
                metrics["has_abstract"] * 5,
                metrics["has_introduction"] * 5,
                metrics["has_methods"] * 5,
                metrics["has_results"] * 5,
                metrics["has_discussion"] * 5,
                metrics["has_conclusion"] * 5,
                metrics["has_references"] * 5,
            ]
        )
        score = min(100, score + section_bonus)

        # Ensure score is in valid range
        return max(0, min(100, score))

    def analyze_all_texts(self, sample_size: int | None = None) -> dict[str, Any]:
        """Analyze all extracted text files.

        Args:
            sample_size: If provided, only analyze this many files

        Returns:
            Analysis results
        """
        text_files = list(self.input_dir.glob("*.txt"))

        if not text_files:
            print(f"No text files found in {self.input_dir}")
            return {}

        if sample_size:
            text_files = text_files[:sample_size]

        print(f"Analyzing {len(text_files)} text files...")

        all_metrics = []
        problem_files = []

        for text_file in tqdm(text_files, desc="Analyzing texts"):
            try:
                text = text_file.read_text(encoding="utf-8")
                metrics = self.analyze_text_quality(text)
                metrics["filename"] = text_file.name
                all_metrics.append(metrics)

                # Track problematic files
                if metrics["readable_score"] < 70:
                    problem_files.append(
                        {
                            "filename": text_file.name,
                            "score": metrics["readable_score"],
                            "issues": self._identify_issues(metrics),
                        }
                    )

            except Exception as e:
                print(f"Error analyzing {text_file.name}: {e}")

        # Calculate aggregate statistics
        stats = self._calculate_aggregate_stats(all_metrics)
        stats["problem_files"] = problem_files[:20]  # Top 20 problematic files

        return stats

    def _identify_issues(self, metrics: dict[str, Any]) -> list[str]:
        """Identify specific issues in text extraction.

        Args:
            metrics: Text metrics

        Returns:
            List of identified issues
        """
        issues = []

        if metrics["garbled_text_ratio"] > 0.05:
            issues.append(f"High garbled text ratio: {metrics['garbled_text_ratio']:.2%}")

        if metrics["excessive_whitespace"] > 0.1:
            issues.append(f"Excessive whitespace: {metrics['excessive_whitespace']:.2%}")

        if metrics["line_break_issues"] > 0.1:
            issues.append(f"Line break issues: {metrics['line_break_issues']:.2%}")

        if metrics["sections_detected"] < 3:
            issues.append(f"Few sections detected: {metrics['sections_detected']}")

        if not metrics["has_abstract"]:
            issues.append("No abstract detected")

        if not metrics["has_references"]:
            issues.append("No references detected")

        return issues

    def _calculate_aggregate_stats(self, all_metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate aggregate statistics from all metrics.

        Args:
            all_metrics: List of metrics for all files

        Returns:
            Aggregate statistics
        """
        if not all_metrics:
            return {}

        total = len(all_metrics)

        stats = {
            "total_files": total,
            "avg_chars_per_file": sum(m["total_chars"] for m in all_metrics) / total,
            "avg_words_per_file": sum(m["total_words"] for m in all_metrics) / total,
            "avg_sections_detected": sum(m["sections_detected"] for m in all_metrics) / total,
            "avg_readability_score": sum(m["readable_score"] for m in all_metrics) / total,
            # Section presence
            "files_with_abstract": sum(1 for m in all_metrics if m["has_abstract"]) / total * 100,
            "files_with_introduction": sum(1 for m in all_metrics if m["has_introduction"]) / total * 100,
            "files_with_methods": sum(1 for m in all_metrics if m["has_methods"]) / total * 100,
            "files_with_results": sum(1 for m in all_metrics if m["has_results"]) / total * 100,
            "files_with_discussion": sum(1 for m in all_metrics if m["has_discussion"]) / total * 100,
            "files_with_conclusion": sum(1 for m in all_metrics if m["has_conclusion"]) / total * 100,
            "files_with_references": sum(1 for m in all_metrics if m["has_references"]) / total * 100,
            # Quality indicators
            "files_with_doi": sum(1 for m in all_metrics if m["has_doi"]) / total * 100,
            "files_with_emails": sum(1 for m in all_metrics if m["has_emails"]) / total * 100,
            # Quality distribution
            "excellent_quality": sum(1 for m in all_metrics if m["readable_score"] >= 90) / total * 100,
            "good_quality": sum(1 for m in all_metrics if 70 <= m["readable_score"] < 90) / total * 100,
            "fair_quality": sum(1 for m in all_metrics if 50 <= m["readable_score"] < 70) / total * 100,
            "poor_quality": sum(1 for m in all_metrics if m["readable_score"] < 50) / total * 100,
        }

        # Find most common section names
        all_sections = []
        for m in all_metrics:
            all_sections.extend(m["section_names"])
        section_counts = Counter(all_sections)
        stats["most_common_sections"] = section_counts.most_common(20)

        return stats

    def generate_report(self, stats: dict[str, Any], output_file: Path | None = None):
        """Generate analysis report.

        Args:
            stats: Analysis statistics
            output_file: Optional output file path
        """
        if not stats:
            print("No statistics to report")
            return

        report = []
        report.append("=" * 60)
        report.append("RAW TEXT EXTRACTION ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")

        report.append(f"Total files analyzed: {stats.get('total_files', 0):,}")
        report.append(f"Average characters per file: {stats.get('avg_chars_per_file', 0):,.0f}")
        report.append(f"Average words per file: {stats.get('avg_words_per_file', 0):,.0f}")
        report.append(f"Average sections detected: {stats.get('avg_sections_detected', 0):.1f}")
        report.append(f"Average readability score: {stats.get('avg_readability_score', 0):.1f}/100")
        report.append("")

        report.append("SECTION DETECTION RATES:")
        report.append("-" * 40)
        report.append(f"  Abstract: {stats.get('files_with_abstract', 0):.1f}%")
        report.append(f"  Introduction: {stats.get('files_with_introduction', 0):.1f}%")
        report.append(f"  Methods: {stats.get('files_with_methods', 0):.1f}%")
        report.append(f"  Results: {stats.get('files_with_results', 0):.1f}%")
        report.append(f"  Discussion: {stats.get('files_with_discussion', 0):.1f}%")
        report.append(f"  Conclusion: {stats.get('files_with_conclusion', 0):.1f}%")
        report.append(f"  References: {stats.get('files_with_references', 0):.1f}%")
        report.append("")

        report.append("QUALITY INDICATORS:")
        report.append("-" * 40)
        report.append(f"  Files with DOI: {stats.get('files_with_doi', 0):.1f}%")
        report.append(f"  Files with email addresses: {stats.get('files_with_emails', 0):.1f}%")
        report.append("")

        report.append("QUALITY DISTRIBUTION:")
        report.append("-" * 40)
        report.append(f"  Excellent (90-100): {stats.get('excellent_quality', 0):.1f}%")
        report.append(f"  Good (70-89): {stats.get('good_quality', 0):.1f}%")
        report.append(f"  Fair (50-69): {stats.get('fair_quality', 0):.1f}%")
        report.append(f"  Poor (<50): {stats.get('poor_quality', 0):.1f}%")
        report.append("")

        if stats.get("most_common_sections"):
            report.append("MOST COMMON SECTION HEADERS:")
            report.append("-" * 40)
            for section, count in stats["most_common_sections"][:10]:
                report.append(f"  {section}: {count} occurrences")
            report.append("")

        if stats.get("problem_files"):
            report.append("PROBLEMATIC FILES (lowest quality scores):")
            report.append("-" * 40)
            for pf in stats["problem_files"][:10]:
                report.append(f"  {pf['filename'][:50]}... (score: {pf['score']:.1f})")
                for issue in pf["issues"][:3]:
                    report.append(f"    - {issue}")
            report.append("")

        report.append("=" * 60)
        report.append("END OF REPORT")
        report.append("=" * 60)

        report_text = "\n".join(report)

        # Print to console
        print(report_text)

        # Save to file if requested
        if output_file:
            output_file.write_text(report_text)
            print(f"\nReport saved to: {output_file}")

        # Also save detailed JSON stats
        json_file = self.input_dir / "analysis_report.json"
        with open(json_file, "w") as f:
            json.dump(stats, f, indent=2, default=str)
        print(f"Detailed statistics saved to: {json_file}")


@click.command()
@click.option(
    "--input-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default="raw_texts",
    help="Directory containing raw text files",
)
@click.option("--sample", type=int, default=None, help="Analyze only a sample of files (for testing)")
@click.option(
    "--output",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Output file for the report",
)
def main(input_dir: Path, sample: int | None, output: Path | None):
    """Analyze raw extracted texts from PDFs."""
    analyzer = RawTextAnalyzer(input_dir)

    # Run analysis
    stats = analyzer.analyze_all_texts(sample_size=sample)

    # Generate report
    if stats:
        analyzer.generate_report(stats, output_file=output)
    else:
        print("No files to analyze")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
