#!/usr/bin/env python3
"""V5 Pipeline Stage 8: CORE Enrichment.

Finds additional full-text sources and download statistics from repositories.

Usage:
    python v5_core_pipeline.py --input pubmed_enriched_final --output core_enriched_final
    python v5_core_pipeline.py --test  # Test with small dataset
    python v5_core_pipeline.py --api-key YOUR_KEY  # For higher rate limits
"""

from src import config
import json
import time
from pathlib import Path
from datetime import datetime, UTC
import argparse
import os
from core_enricher import COREEnricher


def analyze_enrichment_results(output_dir: Path) -> None:
    """Analyze and report enrichment statistics.

    .
    """
    report_file = output_dir / "core_enrichment_report.json"
    if not report_file.exists():
        print("No report file found")
        return

    with open(report_file) as f:
        report = json.load(f)

    print("\n" + "=" * 80)
    print("CORE ENRICHMENT RESULTS")
    print("=" * 80)

    stats = report["statistics"]
    print("\nProcessing Statistics:")
    print(f"  Total papers: {stats['total_papers']}")
    print(f"  Papers processed: {stats['papers_processed']}")
    print(f"  Papers enriched: {stats['papers_enriched']}")
    print(f"  Enrichment rate: {stats['enrichment_rate']}")
    print(f"  Processing time: {stats['processing_time_seconds']} seconds")
    print(f"  Avg time per paper: {stats.get('avg_time_per_paper', 0):.2f} seconds")

    if "fulltext_discovery" in report:
        ft = report["fulltext_discovery"]
        print("\nFull Text Discovery:")
        print(f"  Papers with full text: {ft['papers_with_fulltext']} ({ft['fulltext_rate']})")
        print(f"  Papers with PDF: {ft['papers_with_pdf']} ({ft['pdf_rate']})")
        print(f"  Papers with repository info: {ft['papers_with_repository']}")

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

        repositories = []
        pdf_count = 0
        fulltext_count = 0
        download_urls = 0
        doc_types = []

        for paper_file in papers:
            if "report" in paper_file.name:
                continue

            with open(paper_file) as f:
                paper = json.load(f)

                # Repository info
                if paper.get("core_repository"):
                    repo_name = paper["core_repository"].get("name")
                    if repo_name:
                        repositories.append(repo_name)

                # Full text and PDF
                if paper.get("core_has_fulltext"):
                    fulltext_count += 1
                if paper.get("core_has_pdf"):
                    pdf_count += 1
                if paper.get("core_download_url"):
                    download_urls += 1

                # Document type
                if paper.get("core_document_type"):
                    doc_types.append(paper["core_document_type"])

        if repositories:
            from collections import Counter

            repo_counts = Counter(repositories)
            print("\n  Top Repositories in Sample:")
            for repo, count in repo_counts.most_common(5):
                print(f"    - {repo}: {count} papers")

        print("\n  Full Text Availability:")
        print(f"    - Full text: {fulltext_count}/{len(papers)}")
        print(f"    - PDFs: {pdf_count}/{len(papers)}")
        print(f"    - Download URLs: {download_urls}/{len(papers)}")

        if doc_types:
            type_counts = Counter(doc_types)
            print("\n  Document Types:")
            for doc_type, count in type_counts.most_common(5):
                print(f"    - {doc_type}: {count}")

    print("\n" + "=" * 80)


def main() -> None:
    """Run the main program.

    .
    """
    parser = argparse.ArgumentParser(description="V5 Pipeline Stage 8: CORE Enrichment")
    parser.add_argument(
        "--input", default="pubmed_enriched_final", help="Input directory with PubMed enriched papers"
    )
    parser.add_argument(
        "--output", default="core_enriched_final", help="Output directory for CORE enriched papers"
    )
    parser.add_argument("--api-key", help="CORE API key for higher rate limits")
    parser.add_argument("--test", action="store_true", help="Test mode - use small dataset")
    parser.add_argument("--no-title-fallback", action="store_true", help="Don't use title search as fallback")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")

    args = parser.parse_args()

    # Check for API key in environment if not provided
    if not args.api_key:
        args.api_key = os.environ.get("CORE_API_KEY")

    # Test mode uses small dataset
    if args.test:
        args.input = "pubmed_test_output"
        args.output = "core_test_output"

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
        print("Please run PubMed enrichment first (v5_pubmed_pipeline.py)")
        return

    # Initialize enricher
    print("=" * 80)
    print("V5 PIPELINE - STAGE 8: CORE ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    if args.api_key:
        print("API Key: Provided (higher rate limits)")
    else:
        print("API Key: Not provided (conservative rate limiting)")
        print("Get an API key at: https://core.ac.uk/services/api")
    print(f"Title fallback: {'Disabled' if args.no_title_fallback else 'Enabled'}")
    print()

    enricher = COREEnricher(api_key=args.api_key)

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

    # Collect papers with identifiers
    papers_to_process = []
    papers_by_id = {}

    for paper_file in paper_files:
        with open(paper_file) as f:
            paper = json.load(f)

            # Prepare paper dict
            paper_dict = {}
            if paper.get("doi"):
                paper_dict["doi"] = paper["doi"]
            if paper.get("title"):
                paper_dict["title"] = paper["title"]

            if paper_dict:
                # Use DOI as key if available, otherwise title
                key = paper_dict.get("doi") or paper_dict.get("title")
                papers_to_process.append(paper_dict)
                papers_by_id[key] = (paper_file.stem, paper)

    print(f"Found {len(papers_to_process)} papers with DOI or title")

    if not papers_to_process:
        print("No papers with identifiers to process")
        return

    # Process papers
    print("\nProcessing papers with CORE API...")
    print("Note: CORE aggregates content from repositories worldwide")
    print("Expected coverage: ~40% overlap with existing papers")

    start_time = time.time()

    # Process in chunks for progress tracking
    chunk_size = 10
    all_results = {}

    for i in range(0, len(papers_to_process), chunk_size):
        chunk = papers_to_process[i : i + chunk_size]
        chunk_num = i // chunk_size + 1
        total_chunks = (len(papers_to_process) + chunk_size - 1) // chunk_size

        print(f"\nProcessing chunk {chunk_num}/{total_chunks} ({len(chunk)} papers)...")

        # Process chunk
        chunk_results = enricher.enrich_batch(chunk, use_title_fallback=not args.no_title_fallback)
        all_results.update(chunk_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Enriched: {stats['enriched']}")
        print(f"  Failed: {stats['failed']}")
        if stats["enriched"] > 0:
            print(f"  Full text rate: {stats['fulltext_rate']}")
            print(f"  PDF rate: {stats['pdf_rate']}")

        # Save checkpoint every 50 papers
        if (i + chunk_size) % 50 == 0 or (i + chunk_size) >= len(papers_to_process):
            print("  Saving checkpoint...")
            for key, (paper_id, original_paper) in papers_by_id.items():
                if key in all_results:
                    enrichment = all_results[key]
                    for field, value in enrichment.items():
                        if value is not None:
                            original_paper[f"core_{field}"] = value

                output_file = output_path / f"{paper_id}.json"
                with open(output_file, "w") as f:
                    json.dump(original_paper, f, indent=2)

    # Save all papers (final pass)
    print("\nSaving all papers...")
    enriched_count = 0
    for key, (paper_id, original_paper) in papers_by_id.items():
        if key in all_results:
            enrichment = all_results[key]

            # Add CORE fields with prefix
            for field, value in enrichment.items():
                if value is not None:
                    original_paper[f"core_{field}"] = value

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
        "pipeline_stage": "8_core_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_processed": len(papers_to_process),
            "papers_enriched": final_stats["enriched"],
            "papers_failed": final_stats["failed"],
            "enrichment_rate": final_stats["enrichment_rate"],
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / len(papers_to_process), 2) if papers_to_process else 0,
        },
        "fulltext_discovery": {
            "papers_with_fulltext": final_stats["has_fulltext"],
            "fulltext_rate": final_stats["fulltext_rate"],
            "papers_with_pdf": final_stats["has_pdf"],
            "pdf_rate": final_stats["pdf_rate"],
            "papers_with_repository": final_stats["has_repository"],
        },
        "errors": final_stats["errors"],
    }

    report_file = output_path / "core_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(
        f"Papers enriched: {final_stats['enriched']}/{len(papers_to_process)} ({final_stats['enrichment_rate']})"
    )
    if final_stats["enriched"] > 0:
        print(f"Full text found: {final_stats['has_fulltext']} ({final_stats['fulltext_rate']})")
        print(f"PDFs available: {final_stats['has_pdf']} ({final_stats['pdf_rate']})")
        print(f"Repositories identified: {final_stats['has_repository']}")
    print(f"Processing time: {elapsed_time:.1f} seconds")
    print(f"Output directory: {output_path}")
    print(f"Report saved to: {report_file}")

    # Analyze results
    if final_stats["enriched"] > 0:
        analyze_enrichment_results(output_path)


if __name__ == "__main__":
    main()
