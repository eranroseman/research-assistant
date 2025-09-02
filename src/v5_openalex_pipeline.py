#!/usr/bin/env python3
"""V5 Pipeline Stage 5: OpenAlex Enrichment.

Adds topic classification, SDG mapping, and comprehensive metadata.

Usage:
    python v5_openalex_pipeline.py --input s2_enriched_20250901_final --output openalex_enriched_final
    python v5_openalex_pipeline.py --test  # Test with small dataset
"""

import json
import time
from pathlib import Path
from datetime import datetime, UTC
import argparse
import sys

sys.path.append("src")
from config import CROSSREF_POLITE_EMAIL
from openalex_enricher import OpenAlexEnricher


def analyze_enrichment_results(output_dir: Path) -> None:
    """Analyze and report enrichment statistics.

    .
    """
    report_file = output_dir / "openalex_enrichment_report.json"
    if not report_file.exists():
        print("No report file found")
        return

    with open(report_file) as f:
        report = json.load(f)

    print("\n" + "=" * 80)
    print("OPENALEX ENRICHMENT RESULTS")
    print("=" * 80)

    stats = report["statistics"]
    print("\nProcessing Statistics:")
    print(f"  Total papers: {stats['total_papers']}")
    print(f"  Papers with DOIs: {stats['papers_with_dois']}")
    print(f"  Papers enriched: {stats['papers_enriched']}")
    print(f"  Enrichment rate: {stats['enrichment_rate']}")

    if "coverage" in report:
        print("\nMetadata Coverage:")
        print(f"  Topic classification: {report['coverage']['topics']}")
        print(f"  SDG mapping: {report['coverage']['sdgs']}")
        print(f"  Open Access status: {report['coverage']['open_access']}")

    # Sample detailed analysis
    papers = list(output_dir.glob("*.json"))[:10]

    if papers:
        print(f"\nSample Analysis (first {len(papers)} papers):")

        topic_domains = []
        sdg_goals = []
        citation_counts = []
        oa_papers = 0

        for paper_file in papers:
            if paper_file.name == "openalex_enrichment_report.json":
                continue

            with open(paper_file) as f:
                paper = json.load(f)

                # Topics
                if paper.get("openalex_topics"):
                    for topic in paper["openalex_topics"]:
                        if topic.get("domain"):
                            topic_domains.append(topic["domain"])

                # SDGs
                if paper.get("openalex_sdgs"):
                    for sdg in paper["openalex_sdgs"]:
                        if sdg.get("name"):
                            sdg_goals.append(sdg["name"])

                # Citations
                if paper.get("openalex_citation_count") is not None:
                    citation_counts.append(paper["openalex_citation_count"])

                # Open Access
                if paper.get("openalex_open_access", {}).get("is_oa"):
                    oa_papers += 1

        if topic_domains:
            from collections import Counter

            domain_counts = Counter(topic_domains)
            print("\n  Top Research Domains:")
            for domain, count in domain_counts.most_common(3):
                print(f"    - {domain}: {count} occurrences")

        if sdg_goals:
            sdg_counts = Counter(sdg_goals)
            print("\n  Top SDG Goals:")
            for goal, count in sdg_counts.most_common(3):
                print(f"    - {goal[:50]}...: {count} papers")

        if citation_counts:
            import statistics

            print("\n  Citation Statistics:")
            print(f"    - Mean: {statistics.mean(citation_counts):.1f}")
            print(f"    - Median: {statistics.median(citation_counts):.1f}")
            print(f"    - Max: {max(citation_counts)}")

        print(f"\n  Open Access: {oa_papers}/{len(papers)} papers")

    print("\n" + "=" * 80)


def main() -> None:
    """Run the main program.

    .
    """
    parser = argparse.ArgumentParser(description="V5 Pipeline Stage 5: OpenAlex Enrichment")
    parser.add_argument(
        "--input", default="s2_enriched_20250901_final", help="Input directory with S2 enriched papers"
    )
    parser.add_argument(
        "--output", default="openalex_enriched_final", help="Output directory for OpenAlex enriched papers"
    )
    parser.add_argument("--email", help="Email for OpenAlex polite pool (higher rate limits)")
    parser.add_argument("--test", action="store_true", help="Test mode - use small dataset")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")

    args = parser.parse_args()

    # Use config email if not provided
    if not args.email:
        args.email = CROSSREF_POLITE_EMAIL

    # Test mode uses small dataset
    if args.test:
        args.input = "s2_enriched_20250901_small"
        args.output = "openalex_test_output"

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
        print("Please run S2 enrichment first (v5_extraction_pipeline.py)")
        return

    # Initialize enricher
    print("=" * 80)
    print("V5 PIPELINE - STAGE 5: OPENALEX ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    if args.email:
        print(f"Email: {args.email} (polite pool)")
    print()

    enricher = OpenAlexEnricher(email=args.email)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    if not paper_files:
        print("No papers found in input directory")
        return

    print(f"Found {len(paper_files)} papers to process")

    # Collect papers with DOIs
    papers_with_dois = []
    papers_by_doi = {}
    papers_without_doi = []

    for paper_file in paper_files:
        if paper_file.name == "s2_batch_report.json":
            continue

        with open(paper_file) as f:
            paper = json.load(f)
            doi = paper.get("doi")
            if doi:
                papers_with_dois.append((paper_file.stem, doi))
                papers_by_doi[doi] = paper
            else:
                papers_without_doi.append(paper_file.stem)

    print(f"Found {len(papers_with_dois)} papers with DOIs")
    if papers_without_doi:
        print(f"Skipping {len(papers_without_doi)} papers without DOIs")

    # Process in batches
    enriched_count = 0
    failed_count = 0
    batch_size = enricher.batch_size
    total_batches = (len(papers_with_dois) + batch_size - 1) // batch_size

    start_time = time.time()

    for i in range(0, len(papers_with_dois), batch_size):
        batch = papers_with_dois[i : i + batch_size]
        batch_num = i // batch_size + 1

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} papers)...")

        # Extract DOIs
        batch_dois = [doi for _, doi in batch]

        # Enrich batch
        batch_results = enricher.enrich_batch(batch_dois)

        # Save enriched papers
        for paper_id, doi in batch:
            original_paper = papers_by_doi[doi].copy()

            if doi in batch_results:
                enrichment = batch_results[doi]

                # Add OpenAlex fields with prefix
                for key, value in enrichment.items():
                    if value is not None:  # Only add non-null values
                        original_paper[f"openalex_{key}"] = value

                enriched_count += 1
                print(f"  ✓ {paper_id}: enriched with {len(enrichment)} fields")
            else:
                failed_count += 1
                print(f"  ✗ {paper_id}: not found in OpenAlex")

            # Always save paper (enriched or not)
            output_file = output_path / f"{paper_id}.json"
            with open(output_file, "w") as f:
                json.dump(original_paper, f, indent=2)

        # Rate limiting
        if batch_num < total_batches:
            time.sleep(0.1)  # Polite delay between batches

    # Also copy papers without DOIs
    for paper_id in papers_without_doi:
        input_file = input_path / f"{paper_id}.json"
        output_file = output_path / f"{paper_id}.json"
        with open(input_file) as f:
            paper = json.load(f)
        with open(output_file, "w") as f:
            json.dump(paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate report
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_stage": "5_openalex_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_with_dois": len(papers_with_dois),
            "papers_without_dois": len(papers_without_doi),
            "papers_enriched": enriched_count,
            "papers_failed": failed_count,
            "enrichment_rate": f"{(enriched_count / len(papers_with_dois) * 100):.1f}%"
            if papers_with_dois
            else "0%",
            "processing_time_seconds": round(elapsed_time, 1),
            "batches_processed": total_batches,
            "avg_papers_per_batch": batch_size,
        },
    }

    report_file = output_path / "openalex_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(
        f"Papers enriched: {enriched_count}/{len(papers_with_dois)} ({(enriched_count / len(papers_with_dois) * 100):.1f}%)"
    )
    print(f"Processing time: {elapsed_time:.1f} seconds")
    print(f"Output directory: {output_path}")
    print(f"Report saved to: {report_file}")

    # Analyze results
    analyze_enrichment_results(output_path)


if __name__ == "__main__":
    main()
