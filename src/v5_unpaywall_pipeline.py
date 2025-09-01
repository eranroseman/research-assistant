#!/usr/bin/env python3
"""V5 Pipeline Stage 6: Unpaywall Enrichment
Identifies open access versions and provides direct links to free full-text PDFs.

Usage:
    python v5_unpaywall_pipeline.py --input openalex_enriched_final --output unpaywall_enriched_final
    python v5_unpaywall_pipeline.py --test  # Test with small dataset
"""

import json
import time
from pathlib import Path
from datetime import datetime
import argparse
import sys

sys.path.append("src")
from config import CROSSREF_POLITE_EMAIL
from unpaywall_enricher import UnpaywallEnricher


def analyze_enrichment_results(output_dir: Path):
    """Analyze and report enrichment statistics."""
    report_file = output_dir / "unpaywall_enrichment_report.json"
    if not report_file.exists():
        print("No report file found")
        return

    with open(report_file) as f:
        report = json.load(f)

    print("\n" + "=" * 80)
    print("UNPAYWALL ENRICHMENT RESULTS")
    print("=" * 80)

    stats = report["statistics"]
    print("\nProcessing Statistics:")
    print(f"  Total papers: {stats['total_papers']}")
    print(f"  Papers with DOIs: {stats['papers_with_dois']}")
    print(f"  Papers enriched: {stats['papers_enriched']}")
    print(f"  Enrichment rate: {stats['enrichment_rate']}")
    print(f"  Processing time: {stats['processing_time_seconds']} seconds")
    print(f"  Avg time per paper: {stats.get('avg_time_per_paper', 0):.2f} seconds")

    if "open_access" in report:
        oa = report["open_access"]
        print("\nOpen Access Discovery:")
        print(f"  Papers with OA: {oa['papers_with_oa']} ({oa['oa_rate']})")
        print("  OA Breakdown:")
        for oa_type, count in oa["oa_breakdown"].items():
            if count > 0:
                pct = (count / oa["papers_with_oa"] * 100) if oa["papers_with_oa"] > 0 else 0
                print(f"    - {oa_type.capitalize()}: {count} ({pct:.1f}%)")

    if "errors" in report:
        errors = report["errors"]
        if any(errors.values()):
            print("\nError Analysis:")
            for error_type, count in errors.items():
                if count > 0:
                    print(f"  - {error_type}: {count}")

    # Sample detailed analysis
    papers = list(output_dir.glob("*.json"))[:10]

    if papers:
        print(f"\nSample Analysis (first {len(papers)} papers):")

        oa_types = []
        pdf_links = 0
        repositories = []
        licenses = []

        for paper_file in papers:
            if "report" in paper_file.name:
                continue

            with open(paper_file) as f:
                paper = json.load(f)

                # OA status
                if paper.get("unpaywall_is_oa"):
                    oa_types.append(paper.get("unpaywall_oa_status", "unknown"))

                    # PDF links
                    if paper.get("unpaywall_best_oa_location", {}).get("url_for_pdf"):
                        pdf_links += 1

                    # Repository
                    repo = paper.get("unpaywall_best_oa_location", {}).get("repository")
                    if repo:
                        repositories.append(repo)

                    # License
                    license = paper.get("unpaywall_best_oa_location", {}).get("license")
                    if license:
                        licenses.append(license)

        if oa_types:
            from collections import Counter

            oa_counts = Counter(oa_types)
            print("\n  OA Types in Sample:")
            for oa_type, count in oa_counts.most_common():
                print(f"    - {oa_type}: {count}")

        print(f"\n  Direct PDF Links: {pdf_links}/{len(papers)}")

        if repositories:
            repo_counts = Counter(repositories)
            print("\n  Top Repositories:")
            for repo, count in repo_counts.most_common(3):
                print(f"    - {repo}: {count}")

        if licenses:
            license_counts = Counter(licenses)
            print("\n  License Distribution:")
            for license, count in license_counts.most_common():
                print(f"    - {license}: {count}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(description="V5 Pipeline Stage 6: Unpaywall Enrichment")
    parser.add_argument(
        "--input", default="openalex_enriched_final", help="Input directory with OpenAlex enriched papers"
    )
    parser.add_argument(
        "--output", default="unpaywall_enriched_final", help="Output directory for Unpaywall enriched papers"
    )
    parser.add_argument("--email", help="Email for Unpaywall API (required)")
    parser.add_argument("--test", action="store_true", help="Test mode - use small dataset")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel processing")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")

    args = parser.parse_args()

    # Use config email if not provided
    if not args.email:
        args.email = CROSSREF_POLITE_EMAIL

    # Test mode uses small dataset
    if args.test:
        args.input = "openalex_test_output"
        args.output = "unpaywall_test_output"

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
        print("Please run OpenAlex enrichment first (v5_openalex_pipeline.py)")
        return

    # Initialize enricher
    print("=" * 80)
    print("V5 PIPELINE - STAGE 6: UNPAYWALL ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Email: {args.email}")
    print(f"Parallel processing: {'Disabled' if args.no_parallel else 'Enabled'}")
    print()

    try:
        enricher = UnpaywallEnricher(email=args.email)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    if not paper_files:
        print("No papers found in input directory")
        return

    # Filter out report files
    paper_files = [f for f in paper_files if "report" not in f.name]
    print(f"Found {len(paper_files)} papers to process")

    # Collect papers with DOIs
    papers_with_dois = []
    papers_by_doi = {}
    papers_without_doi = []

    for paper_file in paper_files:
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

    if not papers_with_dois:
        print("No papers with DOIs to process")
        return

    # Process papers
    print("\nProcessing papers with Unpaywall API...")
    print("Note: Unpaywall requires individual API calls per DOI")
    if len(papers_with_dois) > 100:
        estimated_time = len(papers_with_dois) * 0.15  # ~0.15 seconds per paper with parallelization
        print(f"Estimated time: {estimated_time / 60:.1f} minutes")

    start_time = time.time()

    # Process in chunks for better progress tracking
    chunk_size = 50
    all_results = {}
    all_dois = [doi for _, doi in papers_with_dois]

    for i in range(0, len(all_dois), chunk_size):
        chunk = all_dois[i : i + chunk_size]
        chunk_num = i // chunk_size + 1
        total_chunks = (len(all_dois) + chunk_size - 1) // chunk_size

        print(f"\nProcessing chunk {chunk_num}/{total_chunks} ({len(chunk)} papers)...")

        # Process chunk
        chunk_results = enricher.enrich_batch(
            chunk, parallel=not args.no_parallel, max_workers=5 if not args.test else 2
        )
        all_results.update(chunk_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Enriched: {stats['enriched']}")
        print(f"  OA found: {stats['oa_discovered']} ({stats['oa_rate']})")

        # Save checkpoint every 100 papers
        if (i + chunk_size) % 100 == 0 or (i + chunk_size) >= len(all_dois):
            print("  Saving checkpoint...")
            for paper_id, doi in papers_with_dois[: i + chunk_size]:
                original_paper = papers_by_doi[doi].copy()

                if doi in all_results:
                    enrichment = all_results[doi]
                    for key, value in enrichment.items():
                        if value is not None:
                            original_paper[f"unpaywall_{key}"] = value

                output_file = output_path / f"{paper_id}.json"
                with open(output_file, "w") as f:
                    json.dump(original_paper, f, indent=2)

    # Save remaining papers
    print("\nSaving all enriched papers...")
    for paper_id, doi in papers_with_dois:
        original_paper = papers_by_doi[doi].copy()

        if doi in all_results:
            enrichment = all_results[doi]

            # Add Unpaywall fields with prefix
            for key, value in enrichment.items():
                if value is not None:  # Only add non-null values
                    original_paper[f"unpaywall_{key}"] = value

        # Save paper (enriched or not)
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(original_paper, f, indent=2)

    # Also copy papers without DOIs
    for paper_id in papers_without_doi:
        input_file = input_path / f"{paper_id}.json"
        output_file = output_path / f"{paper_id}.json"
        with open(input_file) as f:
            paper = json.load(f)
        with open(output_file, "w") as f:
            json.dump(paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate final report
    final_stats = enricher.get_statistics()
    report = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_stage": "6_unpaywall_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_with_dois": len(papers_with_dois),
            "papers_without_dois": len(papers_without_doi),
            "papers_enriched": final_stats["enriched"],
            "papers_failed": final_stats["failed"],
            "enrichment_rate": final_stats["enrichment_rate"],
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / len(papers_with_dois), 2) if papers_with_dois else 0,
        },
        "open_access": {
            "papers_with_oa": final_stats["oa_discovered"],
            "oa_rate": final_stats["oa_rate"],
            "oa_breakdown": final_stats["oa_breakdown"],
        },
        "errors": final_stats["errors"],
    }

    report_file = output_path / "unpaywall_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(
        f"Papers enriched: {final_stats['enriched']}/{len(papers_with_dois)} ({final_stats['enrichment_rate']})"
    )
    print(f"Open Access found: {final_stats['oa_discovered']} ({final_stats['oa_rate']})")
    print(f"Processing time: {elapsed_time:.1f} seconds")
    print(f"Output directory: {output_path}")
    print(f"Report saved to: {report_file}")

    # Analyze results
    analyze_enrichment_results(output_path)


if __name__ == "__main__":
    main()
