#!/usr/bin/env python3
"""Deep dive analysis of problem papers to understand root causes."""

from src import config

import json
import logging
from pathlib import Path
from collections import defaultdict
import re
from typing import Any

# Set up module logger
logger = logging.getLogger(__name__)


def analyze_problem_paper(paper_file: Path) -> dict[str, Any]:
    """Analyze a single problem paper in detail."""
    with open(paper_file, encoding="utf-8") as f:
        data = json.load(f)

    analysis: dict[str, Any] = {
        "paper_id": paper_file.stem,
        "file_size": paper_file.stat().st_size,
        "has_title": bool(data.get("title")),
        "has_doi": bool(data.get("doi")),
        "has_year": bool(data.get("year")),
        "has_authors": bool(data.get("authors")),
        "has_abstract": bool(data.get("abstract")),
        "has_sections": bool(data.get("sections")),
        "has_journal": bool(data.get("journal")),
        "enrichment_statuses": {},
        "text_lengths": {},
        "likely_document_type": "unknown",
    }

    # Get text lengths
    if data.get("title"):
        analysis["text_lengths"]["title"] = len(data["title"])
    if data.get("abstract"):
        analysis["text_lengths"]["abstract"] = len(data["abstract"])
    if data.get("sections"):
        total_text = sum(len(s.get("text", "")) for s in data["sections"])
        analysis["text_lengths"]["sections"] = total_text

    # Check enrichment statuses
    if "crossref_enrichment" in data:
        analysis["enrichment_statuses"]["crossref"] = data["crossref_enrichment"].get("status", "unknown")
    if "zotero_recovery" in data:
        analysis["enrichment_statuses"]["zotero"] = "recovered"

    # Try to determine document type
    title = (data.get("title") or "").lower()
    abstract = (data.get("abstract") or "").lower()

    # Check for non-article indicators
    non_article_patterns = [
        r"\beditorial\b",
        r"\bcomment\b",
        r"\bcorrespondence\b",
        r"\bletter to\b",
        r"\berratum\b",
        r"\bcorrection\b",
        r"\bsupplement\b",
        r"\bbook review\b",
        r"\bnews\b",
        r"\bannouncement\b",
        r"\babstract only\b",
        r"\bposter\b",
    ]

    for pattern in non_article_patterns:
        if re.search(pattern, title) or re.search(pattern, abstract[:200] if abstract else ""):
            analysis["likely_document_type"] = pattern.strip("\\b")
            break

    # Check if it's likely a dataset or supplementary material
    if "figshare" in str(data.get("doi", "")) or "zenodo" in str(data.get("doi", "")):
        analysis["likely_document_type"] = "dataset"
    elif "supplement" in title or "additional file" in title:
        analysis["likely_document_type"] = "supplementary material"

    # Check for very short content suggesting extraction failure
    if analysis["text_lengths"].get("sections", 0) < config.MIN_FULL_TEXT_LENGTH_THRESHOLD:
        if analysis["text_lengths"].get("sections", 0) == 0:
            analysis["likely_document_type"] = "extraction_failure"
        else:
            analysis["likely_document_type"] = "partial_extraction"

    return analysis


def find_problem_papers(
    pipeline_dir: Path, max_papers: int = config.MIN_ABSTRACT_LENGTH
) -> list[dict[str, Any]]:
    """Find papers with the most missing critical fields."""
    critical_fields = ["title", "doi", "year", "authors", "abstract", "sections"]
    problem_papers: list[dict[str, Any]] = []

    # Find the last enrichment stage
    stages = ["08_pubmed_enrichment", "07_unpaywall_enrichment", "06_openalex_enrichment", "05_s2_enrichment"]
    target_dir = None
    for stage in stages:
        stage_dir = pipeline_dir / stage
        if stage_dir.exists() and len(list(stage_dir.glob("*.json"))) > 0:
            target_dir = stage_dir
            break

    if not target_dir:
        print(f"No enriched data found in {pipeline_dir}")
        return []

    print(f"Analyzing papers in {target_dir}...")

    for json_file in target_dir.glob("*.json"):
        if "report" in json_file.name or json_file.name.startswith("."):
            continue

        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            missing_fields = []
            for field in critical_fields:
                if not data.get(field):
                    missing_fields.append(field)

            if (
                len(missing_fields) >= config.MIN_MATCH_COUNT
            ):  # Papers missing config.MIN_MATCH_COUNT+ critical fields
                problem_papers.append(
                    {
                        "file": json_file,
                        "paper_id": json_file.stem,
                        "missing_count": len(missing_fields),
                        "missing_fields": missing_fields,
                    }
                )
        except Exception as e:
            logger.debug("Error processing %s: %s", json_file, e)

    # Sort by number of missing fields
    problem_papers.sort(key=lambda x: x["missing_count"], reverse=True)

    return problem_papers[:max_papers]


def main() -> None:
    """Analyze problem papers from both pipelines."""
    pipelines = [Path("extraction_pipeline_20250901"), Path("extraction_pipeline_fixed_20250901")]

    for pipeline_dir in pipelines:
        if not pipeline_dir.exists():
            continue

        print(f"\n{'=' * 80}")
        print(f"PROBLEM PAPER ANALYSIS: {pipeline_dir.name}")
        print("=" * 80)

        problem_papers = find_problem_papers(pipeline_dir, max_papers=30)

        if not problem_papers:
            print("No problem papers found")
            continue

        print(f"Found {len(problem_papers)} problem papers")
        print()

        # Group by missing field patterns
        patterns = defaultdict(list)
        for paper in problem_papers:
            pattern = tuple(sorted(paper["missing_fields"]))
            patterns[pattern].append(paper["paper_id"])

        print("MISSING FIELD PATTERNS")
        print("-" * 40)
        for pattern, papers in sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            print(f"\nMissing: {', '.join(pattern)}")
            print(f"Count: {len(papers)} papers")
            print(f"Examples: {', '.join(papers[:5])}")

        # Deep dive on worst cases
        print("\n" + "=" * 80)
        print("DEEP DIVE: WORST PROBLEM PAPERS")
        print("=" * 80)

        worst_papers = problem_papers[:10]
        document_types: dict[str, int] = defaultdict(int)

        for paper_info in worst_papers:
            analysis = analyze_problem_paper(paper_info["file"])
            document_types[analysis["likely_document_type"]] += 1

            print(f"\nPaper ID: {analysis['paper_id']}")
            print(f"Missing fields: {', '.join(paper_info['missing_fields'])}")
            print(f"File size: {analysis['file_size']} bytes")
            print(f"Document type: {analysis['likely_document_type']}")

            if analysis["text_lengths"]:
                print(f"Text lengths: {analysis['text_lengths']}")
            if analysis["enrichment_statuses"]:
                print(f"Enrichment: {analysis['enrichment_statuses']}")

        print("\n" + "=" * 80)
        print("ROOT CAUSE SUMMARY")
        print("=" * 80)
        print("\nDocument type distribution (worst 10 papers):")
        for doc_type, count in sorted(document_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {doc_type}: {count}")

        # Trace back to original extraction
        print("\n" + "=" * 80)
        print("TRACING BACK TO ORIGINAL EXTRACTION")
        print("=" * 80)

        # Check if these papers exist in earlier stages
        for paper_info in worst_papers[:5]:
            paper_id = paper_info["paper_id"]
            print(f"\n{paper_id}:")

            # Check each stage
            stages = ["01_tei_xml", "02_json_extraction", "03_zotero_recovery", "04_crossref_enrichment"]

            for stage in stages:
                stage_file = pipeline_dir / stage / f"{paper_id}.json"
                if not stage_file.exists():
                    stage_file = pipeline_dir / stage / f"{paper_id}.xml"

                if stage_file.exists():
                    size = stage_file.stat().st_size
                    print(f"  {stage}: ✓ ({size} bytes)")

                    # Check what happened at this stage
                    if stage == "02_json_extraction" and stage_file.suffix == ".json":
                        with open(stage_file) as f:
                            data = json.load(f)
                        fields_present = sum(
                            1
                            for field in ["title", "doi", "year", "authors", "abstract", "sections"]
                            if data.get(field)
                        )
                        print(f"    → Had {fields_present}/6 critical fields")
                else:
                    print(f"  {stage}: ✗ (not found)")
                    break


if __name__ == "__main__":
    main()
