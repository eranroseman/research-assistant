#!/usr/bin/env python3
"""V5 Pipeline Stage 9: arXiv Enrichment.

Tracks preprint versions and updates for STEM papers.

Usage:
    python v5_arxiv_pipeline.py --input pubmed_enriched_final --output arxiv_enriched_final
    python v5_arxiv_pipeline.py --test  # Test with small dataset
"""

from src import config
import json
import time
from pathlib import Path
from datetime import datetime, UTC
import argparse
from arxiv_enricher import ArXivEnricher


def analyze_enrichment_results(output_dir: Path) -> None:
    """Analyze and report enrichment statistics.

    .
    """
    report_file = output_dir / "arxiv_enrichment_report.json"
    if not report_file.exists():
        print("No report file found")
        return

    with open(report_file) as f:
        report = json.load(f)

    print("\n" + "=" * 80)
    print("ARXIV ENRICHMENT RESULTS")
    print("=" * 80)

    stats = report["statistics"]
    print("\nProcessing Statistics:")
    print(f"  Total papers: {stats['total_papers']}")
    print(f"  Papers processed: {stats['papers_processed']}")
    print(f"  Papers enriched: {stats['papers_enriched']}")
    print(f"  Enrichment rate: {stats['enrichment_rate']}")
    print(f"  Processing time: {stats['processing_time_seconds']} seconds")
    print(f"  Avg time per paper: {stats.get('avg_time_per_paper', 0):.2f} seconds")

    if "preprint_discovery" in report:
        pd = report["preprint_discovery"]
        print("\nPreprint Discovery:")
        print(f"  Papers found on arXiv: {pd['papers_found']}")
        print(f"  Papers not found: {pd['not_found']}")
        print(f"  No match (low similarity): {pd['no_match']}")

        if pd.get("domains"):
            print("\nDomain Distribution:")
            for domain, count in sorted(pd["domains"].items(), key=lambda x: x[1], reverse=True):
                print(f"    - {domain}: {count} papers")

    if "errors" in report:
        errors = report["errors"]
        if any(errors.values()):
            print("\nError Analysis:")
            for error_type, count in errors.items():
                if count > 0:
                    print(f"  - {error_type}: {count}")

    # Sample detailed analysis
    papers = list(output_dir.glob("*.json"))[:20]

    if papers:
        print(f"\nSample Analysis (first {len(papers)} papers):")

        categories = []
        versions = []
        published_dois = 0
        has_comments = 0
        pdf_links = 0

        for paper_file in papers:
            if "report" in paper_file.name:
                continue

            with open(paper_file) as f:
                paper = json.load(f)

                # Categories
                if paper.get("arxiv_categories"):
                    categories.extend(paper["arxiv_categories"])

                # Versions
                if paper.get("arxiv_version"):
                    versions.append(paper["arxiv_version"])

                # Published DOI (indicates paper was published)
                if paper.get("arxiv_published_doi"):
                    published_dois += 1

                # Comments
                if paper.get("arxiv_comment"):
                    has_comments += 1

                # PDF links
                if paper.get("arxiv_pdf_url"):
                    pdf_links += 1

        if categories:
            from collections import Counter

            cat_counts = Counter(categories)
            print("\n  Top arXiv Categories in Sample:")
            for cat, count in cat_counts.most_common(10):
                print(f"    - {cat}: {count} occurrences")

        if versions:
            print("\n  Version Distribution:")
            version_counts = Counter(versions)
            for version, count in sorted(version_counts.items()):
                print(f"    - v{version}: {count} papers")

        print("\n  Papers with:")
        print(f"    - PDF links: {pdf_links}")
        print(f"    - Published DOIs: {published_dois} (published after preprint)")
        print(f"    - Author comments: {has_comments}")

    print("\n" + "=" * 80)


def main() -> None:
    """Run the main program.

    .
    """
    parser = argparse.ArgumentParser(description="V5 Pipeline Stage 9: arXiv Enrichment")
    parser.add_argument(
        "--input", default="pubmed_enriched_final", help="Input directory with enriched papers"
    )
    parser.add_argument(
        "--output", default="arxiv_enriched_final", help="Output directory for arXiv enriched papers"
    )
    parser.add_argument("--test", action="store_true", help="Test mode - use small dataset")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")

    args = parser.parse_args()

    # Test mode uses small dataset
    if args.test:
        args.input = "pubmed_test_output"
        args.output = "arxiv_test_output"

    output_path = Path(args.output)

    # Analyze only mode
    if args.analyze_only:
        if not output_path.exists():
            print(f"Output directory {output_path} does not exist")
            return
        analyze_enrichment_results(output_path)
        return

    # Check input directory
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input directory {input_path} does not exist")
        print("Please run previous enrichment steps first")
        return

    # Initialize enricher
    print("=" * 80)
    print("V5 PIPELINE - STAGE 9: ARXIV ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print()
    print("Note: arXiv API requires 3-second delays between requests")
    print("Expected coverage: ~10-15% for STEM papers")
    print()

    enricher = ArXivEnricher()

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    if not paper_files:
        print("No papers found in input directory")
        return

    # Filter out report files
    paper_files = [f for f in paper_files if "report" not in f.name]

    # Limit to 20 papers in test mode for faster testing
    if args.test and len(paper_files) > config.DEFAULT_PROCESSING_LIMIT:
        paper_files = paper_files[: config.DEFAULT_PROCESSING_LIMIT]
        print(f"Test mode: Processing only first {config.DEFAULT_PROCESSING_LIMIT} papers")

    print(f"Found {len(paper_files)} papers to process")

    # Prepare papers for enrichment
    papers_to_process = []
    papers_by_id = {}

    for paper_file in paper_files:
        with open(paper_file) as f:
            paper = json.load(f)

            # Prepare paper dict
            paper_dict = {"id": paper_file.stem, "title": paper.get("title"), "authors": []}

            # Extract authors from various sources
            if paper.get("authors"):
                # Handle different author formats
                authors = paper["authors"]
                if authors and isinstance(authors[0], dict):
                    # Extract names from dict format
                    paper_dict["authors"] = [a.get("name") for a in authors if a.get("name")]
                else:
                    paper_dict["authors"] = authors
            elif paper.get("pubmed_authors"):
                paper_dict["authors"] = paper["pubmed_authors"]
            elif paper.get("openalex_authors"):
                paper_dict["authors"] = [a.get("name") for a in paper["openalex_authors"] if a.get("name")]

            # Check for existing arXiv ID (from other sources)
            if paper.get("arxiv_id"):
                paper_dict["arxiv_id"] = paper["arxiv_id"]

            papers_to_process.append(paper_dict)
            papers_by_id[paper_file.stem] = paper

    print(f"Prepared {len(papers_to_process)} papers for arXiv search")

    # Process papers
    print("\nSearching arXiv for preprints...")
    start_time = time.time()

    # Process in chunks for progress tracking
    chunk_size = 10
    all_results = {}

    for i in range(0, len(papers_to_process), chunk_size):
        chunk = papers_to_process[i : i + chunk_size]
        chunk_num = i // chunk_size + 1
        total_chunks = (len(papers_to_process) + chunk_size - 1) // chunk_size

        print(f"\nProcessing chunk {chunk_num}/{total_chunks} ({len(chunk)} papers)...")
        print(f"  Estimated time: {len(chunk) * 3} seconds")

        # Process chunk
        chunk_results = enricher.enrich_batch(chunk)
        all_results.update(chunk_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Enriched: {stats['enriched']}")
        print(f"  Not found: {stats['not_found']}")
        if stats.get("domains"):
            domain_str = ", ".join(f"{k}:{v}" for k, v in stats["domains"].items())
            print(f"  Domains: {domain_str}")

    # Save enriched papers
    print("\nSaving enriched papers...")
    enriched_count = 0
    for paper_id, original_paper in papers_by_id.items():
        if paper_id in all_results:
            enrichment = all_results[paper_id]

            # Add arXiv fields with prefix
            for field, value in enrichment.items():
                if value is not None:
                    original_paper[f"arxiv_{field}"] = value

            enriched_count += 1

        # Save paper (enriched or not)
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(original_paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate final report
    final_stats = enricher.get_statistics()
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_stage": "9_arxiv_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_processed": len(papers_to_process),
            "papers_enriched": final_stats["enriched"],
            "papers_failed": final_stats["failed"],
            "enrichment_rate": final_stats["enrichment_rate"],
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / len(papers_to_process), 2) if papers_to_process else 0,
        },
        "preprint_discovery": {
            "papers_found": final_stats["enriched"],
            "not_found": final_stats["not_found"],
            "no_match": final_stats["no_match"],
            "domains": final_stats.get("domains", {}),
        },
        "errors": final_stats["errors"],
    }

    report_file = output_path / "arxiv_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(
        f"Papers enriched: {final_stats['enriched']}/{len(papers_to_process)} ({final_stats['enrichment_rate']})"
    )
    if final_stats.get("domains"):
        print("Domain distribution:")
        for domain, count in sorted(final_stats["domains"].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {domain}: {count} papers")
    print(f"Processing time: {elapsed_time:.1f} seconds")
    print(f"Output directory: {output_path}")
    print(f"Report saved to: {report_file}")

    # Analyze results
    if final_stats["enriched"] > 0:
        analyze_enrichment_results(output_path)


if __name__ == "__main__":
    main()
