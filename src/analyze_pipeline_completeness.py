#!/usr/bin/env python3
"""Comprehensive analysis of pipeline output data completeness and failure root causes."""

from src import config

import json
from pathlib import Path
from collections import defaultdict, Counter
import re
from datetime import datetime, UTC
from typing import Any


class PipelineCompletenessAnalyzer:
    """Analyze pipeline results for data completeness and failure patterns."""

    def __init__(self) -> None:
        """Initialize the analyzer with default statistics containers."""
        self.stats: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.missing_fields: defaultdict[str, list[str]] = defaultdict(list)
        self.failure_patterns: defaultdict[str, list[str]] = defaultdict(list)
        self.field_coverage: defaultdict[str, int] = defaultdict(int)
        self.enrichment_tracking: defaultdict[str, dict[str, int]] = defaultdict(dict)

    def analyze_paper(self, paper_data: dict[str, Any], paper_id: str) -> dict[str, Any]:
        """Analyze a single paper for completeness."""
        analysis: dict[str, Any] = {
            "paper_id": paper_id,
            "critical_fields": {},
            "enrichment_fields": {},
            "missing_critical": [],
            "missing_enrichment": [],
            "data_quality_issues": [],
        }

        # Critical fields (must have)
        critical_fields = ["title", "doi", "year", "authors", "abstract", "sections"]
        for field in critical_fields:
            has_field = bool(paper_data.get(field))
            analysis["critical_fields"][field] = has_field
            if not has_field:
                analysis["missing_critical"].append(field)
                self.missing_fields[field].append(paper_id)
            else:
                self.field_coverage[field] += 1

        # Enrichment fields (nice to have)
        enrichment_fields = [
            "journal",
            "publisher",
            "keywords",
            "references",
            "cited_by_count",
            "issn",
            "volume",
            "issue",
            "pages",
            "funders",
            "licenses",
            "oa_status",
            "topics",
            "mesh_terms",
            "arxiv_id",
            "pmid",
            "semantic_scholar_id",
            "openalex_id",
        ]
        for field in enrichment_fields:
            has_field = bool(paper_data.get(field))
            analysis["enrichment_fields"][field] = has_field
            if not has_field:
                analysis["missing_enrichment"].append(field)
            else:
                self.field_coverage[field] += 1

        # Check data quality issues
        # 1. Empty or very short content
        if paper_data.get("abstract") and len(paper_data["abstract"]) < config.MIN_ABSTRACT_LENGTH:
            analysis["data_quality_issues"].append("Very short abstract (<config.MIN_ABSTRACT_LENGTH chars)")

        sections = paper_data.get("sections", [])
        if sections:
            total_text = sum(len(s.get("text", "")) for s in sections)
            if total_text < config.MIN_FULL_TEXT_LENGTH_THRESHOLD:
                analysis["data_quality_issues"].append(f"Very short full text ({total_text} chars)")
        else:
            analysis["data_quality_issues"].append("No sections/full text")

        # 2. Malformed DOI
        doi = paper_data.get("doi", "")
        if doi and not re.match(r"^10\.\d{4,}/.+", doi):
            analysis["data_quality_issues"].append(f"Malformed DOI: {doi}")

        # 3. Invalid year
        year = paper_data.get("year")
        if year:
            try:
                year_int = int(year)
                if year_int < config.MIN_YEAR_VALID or year_int > datetime.now(UTC).year + 1:
                    analysis["data_quality_issues"].append(f"Invalid year: {year}")
            except (ValueError, TypeError):
                analysis["data_quality_issues"].append(f"Non-numeric year: {year}")

        # 4. Check enrichment status
        if "crossref_enrichment" in paper_data:
            status = paper_data["crossref_enrichment"].get("status", "unknown")
            self.enrichment_tracking["crossref"][status] = (
                self.enrichment_tracking["crossref"].get(status, 0) + 1
            )

        if "s2_enrichment" in paper_data:
            self.enrichment_tracking["s2"]["enriched"] = self.enrichment_tracking["s2"].get("enriched", 0) + 1

        if "openalex_enrichment" in paper_data:
            self.enrichment_tracking["openalex"]["enriched"] = (
                self.enrichment_tracking["openalex"].get("enriched", 0) + 1
            )

        if "unpaywall_enrichment" in paper_data:
            self.enrichment_tracking["unpaywall"]["enriched"] = (
                self.enrichment_tracking["unpaywall"].get("enriched", 0) + 1
            )

        return analysis

    def analyze_directory(self, directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Analyze all papers in a directory."""
        json_files = [
            f for f in directory.glob("*.json") if "report" not in f.name and not f.name.startswith(".")
        ]

        all_analyses = []

        print(f"Analyzing {len(json_files)} papers from {directory.name}...")

        for i, json_file in enumerate(json_files):
            if (i + 1) % config.LARGE_BATCH_SIZE == 0:
                print(f"  Processed {i + 1}/{len(json_files)} papers...")

            try:
                with open(json_file, encoding="utf-8") as f:
                    paper_data = json.load(f)

                analysis = self.analyze_paper(paper_data, json_file.stem)
                all_analyses.append(analysis)

                # Track overall stats
                if analysis["missing_critical"]:
                    self.stats["papers_with_missing_critical"]["count"] += 1

                if analysis["data_quality_issues"]:
                    self.stats["papers_with_quality_issues"]["count"] += 1
                    for issue in analysis["data_quality_issues"]:
                        self.failure_patterns[issue].append(json_file.stem)

            except Exception as e:
                self.stats["failed_to_parse"]["count"] += 1
                self.failure_patterns[f"Parse error: {e!s}"].append(json_file.stem)

        return self.stats, all_analyses

    def generate_report(self, directory: Path, all_analyses: list[dict[str, Any]]) -> str:
        """Generate comprehensive analysis report."""
        total_papers = len(all_analyses)

        report = []
        report.append("=" * 80)
        report.append("PIPELINE DATA COMPLETENESS ANALYSIS")
        report.append("=" * 80)
        report.append(f"Directory: {directory}")
        report.append(f"Total papers analyzed: {total_papers}")
        report.append(f"Analysis timestamp: {datetime.now(UTC).isoformat()}")
        report.append("")

        # Critical fields coverage
        report.append("CRITICAL FIELDS COVERAGE")
        report.append("-" * 40)
        critical_fields = ["title", "doi", "year", "authors", "abstract", "sections"]
        for field in critical_fields:
            count = self.field_coverage.get(field, 0)
            percentage = (count / total_papers * config.MIN_CONTENT_LENGTH) if total_papers > 0 else 0
            missing = total_papers - count
            report.append(f"{field:15s}: {count:5d}/{total_papers} ({percentage:6.2f}%) - Missing: {missing}")
        report.append("")

        # Enrichment fields coverage
        report.append("ENRICHMENT FIELDS COVERAGE")
        report.append("-" * 40)
        enrichment_fields = [
            "journal",
            "publisher",
            "keywords",
            "references",
            "cited_by_count",
            "issn",
            "volume",
            "issue",
            "pages",
        ]
        for field in enrichment_fields:
            count = self.field_coverage.get(field, 0)
            percentage = (count / total_papers * config.MIN_CONTENT_LENGTH) if total_papers > 0 else 0
            report.append(f"{field:15s}: {count:5d}/{total_papers} ({percentage:6.2f}%)")
        report.append("")

        # API enrichment coverage
        report.append("API ENRICHMENT STATUS")
        report.append("-" * 40)
        for api, statuses in self.enrichment_tracking.items():
            report.append(f"\n{api.upper()}:")
            for status, count in statuses.items():
                percentage = (count / total_papers * config.MIN_CONTENT_LENGTH) if total_papers > 0 else 0
                report.append(f"  {status:15s}: {count:5d} ({percentage:6.2f}%)")
        report.append("")

        # Data quality issues
        report.append("DATA QUALITY ISSUES")
        report.append("-" * 40)
        sorted_issues = sorted(self.failure_patterns.items(), key=lambda x: len(x[1]), reverse=True)
        for issue, papers in sorted_issues[:20]:  # Top 20 issues
            count = len(papers)
            percentage = (count / total_papers * config.MIN_CONTENT_LENGTH) if total_papers > 0 else 0
            report.append(f"{issue[:50]:50s}: {count:5d} ({percentage:6.2f}%)")
            if count <= config.DEFAULT_MAX_RESULTS:  # Show paper IDs for rare issues
                report.append(f"  Papers: {', '.join(papers[:5])}")
        report.append("")

        # Papers with critical missing fields
        report.append("CRITICAL MISSING FIELDS ANALYSIS")
        report.append("-" * 40)
        papers_missing_critical = sum(1 for a in all_analyses if a["missing_critical"])
        report.append(
            f"Papers with missing critical fields: {papers_missing_critical}/{total_papers} ({papers_missing_critical / total_papers * 100:.2f}%)"
        )

        # Count by missing field combinations
        missing_combinations: Counter[tuple[str, ...]] = Counter()
        for analysis in all_analyses:
            if analysis["missing_critical"]:
                combo = tuple(sorted(analysis["missing_critical"]))
                missing_combinations[combo] += 1

        report.append("\nMost common missing field combinations:")
        for combo, count in missing_combinations.most_common(10):
            percentage = count / total_papers * 100
            report.append(f"  {', '.join(combo)}: {count} papers ({percentage:.2f}%)")
        report.append("")

        # Identify problem papers
        report.append("PROBLEM PAPERS (Multiple Critical Fields Missing)")
        report.append("-" * 40)
        problem_papers = []
        for analysis in all_analyses:
            if len(analysis["missing_critical"]) >= config.MAX_RETRIES_DEFAULT:
                problem_papers.append(
                    {
                        "id": analysis["paper_id"],
                        "missing": analysis["missing_critical"],
                        "quality_issues": analysis["data_quality_issues"],
                    }
                )

        report.append(f"Found {len(problem_papers)} papers with 3+ missing critical fields")
        for paper in problem_papers[:10]:  # Show first 10
            report.append(f"  {paper['id']}: Missing {', '.join(paper['missing'])}")
            if paper["quality_issues"]:
                report.append(f"    Issues: {', '.join(paper['quality_issues'][:2])}")
        report.append("")

        # Root cause analysis
        report.append("ROOT CAUSE ANALYSIS")
        report.append("-" * 40)

        # Papers without DOI
        no_doi = [a for a in all_analyses if "doi" in a["missing_critical"]]
        report.append(f"Papers without DOI: {len(no_doi)} ({len(no_doi) / total_papers * 100:.2f}%)")

        # Papers without title
        no_title = [a for a in all_analyses if "title" in a["missing_critical"]]
        report.append(f"Papers without title: {len(no_title)} ({len(no_title) / total_papers * 100:.2f}%)")

        # Papers without abstract
        no_abstract = [a for a in all_analyses if "abstract" in a["missing_critical"]]
        report.append(
            f"Papers without abstract: {len(no_abstract)} ({len(no_abstract) / total_papers * 100:.2f}%)"
        )

        # Papers without sections
        no_sections = [a for a in all_analyses if "sections" in a["missing_critical"]]
        report.append(
            f"Papers without sections/full text: {len(no_sections)} ({len(no_sections) / total_papers * 100:.2f}%)"
        )

        report.append("")
        report.append("LIKELY ROOT CAUSES:")
        report.append("1. GROBID extraction failures (papers without sections)")
        report.append("2. Non-article documents (editorials, supplements)")
        report.append("3. Corrupted or malformed PDFs")
        report.append("4. Papers behind paywalls (no full text)")
        report.append("5. Pre-prints or grey literature (missing metadata)")

        return "\n".join(report)


def compare_pipelines() -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
    """Compare original vs fixed pipeline results."""
    pipelines = [
        ("extraction_pipeline_20250901/07_unpaywall_enrichment", "Original (with race condition)"),
        ("extraction_pipeline_fixed_20250901/08_pubmed_enrichment", "Fixed (checkpoint-enabled)"),
    ]

    all_reports = []

    for pipeline_dir, description in pipelines:
        directory = Path(pipeline_dir)
        if not directory.exists():
            print(f"Directory not found: {directory}")
            continue

        print(f"\n{'=' * 80}")
        print(f"Analyzing: {description}")
        print(f"{'=' * 80}")

        analyzer = PipelineCompletenessAnalyzer()
        stats, analyses = analyzer.analyze_directory(directory)
        report = analyzer.generate_report(directory, analyses)

        print(report)

        # Save report
        report_file = directory.parent / f"completeness_analysis_{directory.parent.name}.txt"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {report_file}")

        all_reports.append((description, stats, analyses))

    return all_reports


if __name__ == "__main__":
    compare_pipelines()
