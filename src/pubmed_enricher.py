#!/usr/bin/env python3
"""V5 Pipeline Stage 7: PubMed Enrichment.

Adds authoritative medical metadata for biomedical papers.

Usage:
    python v5_pubmed_pipeline.py --input unpaywall_enriched_final --output pubmed_enriched_final
    python v5_pubmed_pipeline.py --test  # Test with small dataset
    python v5_pubmed_pipeline.py --api-key YOUR_KEY  # For higher rate limits
"""

from src import config
import json
import time
from pathlib import Path
from datetime import datetime, UTC
import argparse
import os
from typing import Any
from pubmed_enricher import PubMedEnricher


def analyze_enrichment_results(output_dir: Path) -> None:
    """Analyze and report enrichment statistics.

    .
    """
    report_file = output_dir / "pubmed_enrichment_report.json"
    if not report_file.exists():
        print("No report file found")
        return

    with open(report_file) as f:
        report = json.load(f)

    print("\n" + "=" * 80)
    print("PUBMED ENRICHMENT RESULTS")
    print("=" * 80)

    stats = report["statistics"]
    print("\nProcessing Statistics:")
    print(f"  Total papers: {stats['total_papers']}")
    print(f"  Papers with DOI/PMID: {stats['papers_with_identifiers']}")
    print(f"  Papers enriched: {stats['papers_enriched']}")
    print(f"  Papers not in PubMed: {stats['not_in_pubmed']}")
    print(f"  Enrichment rate: {stats['enrichment_rate']}")
    print(f"  Processing time: {stats['processing_time_seconds']} seconds")

    if "biomedical_metadata" in report:
        bio = report["biomedical_metadata"]
        print("\nBiomedical Metadata:")
        print(f"  Papers with MeSH terms: {bio['mesh_terms']} ({bio['mesh_coverage']})")
        print(f"  Papers with chemicals: {bio['chemicals']}")

        pub_types = bio.get("publication_types", {})
        if pub_types:
            print("\nPublication Types:")
            print(f"  Clinical Trials: {pub_types.get('clinical_trials', 0)}")
            print(f"  Reviews: {pub_types.get('reviews', 0)}")
            print(f"  Meta-Analyses: {pub_types.get('meta_analyses', 0)}")

    if "errors" in report:
        errors = report["errors"]
        if any(errors.values()):
            print("\nError Analysis:")
            for error_type, count in errors.items():
                if count > 0:
                    print(f"  - {error_type}: {count}")

    # Sample detailed analysis
    papers = list(output_dir.glob("*.json"))[: config.DEFAULT_PROCESSING_LIMIT]

    if papers:
        print(f"\nSample Analysis (first {len(papers)} papers):")

        mesh_descriptors = []
        chemicals = []
        pub_types_list = []
        grants_found = 0

        for paper_file in papers:
            if "report" in paper_file.name:
                continue

            with open(paper_file) as f:
                paper = json.load(f)

                # MeSH terms
                if paper.get("pubmed_mesh_terms"):
                    for mesh in paper["pubmed_mesh_terms"]:
                        descriptor = mesh.get("descriptor")
                        if descriptor:
                            mesh_descriptors.append(descriptor)

                # Chemicals
                if paper.get("pubmed_chemicals"):
                    for chem in paper["pubmed_chemicals"]:
                        name = chem.get("name")
                        if name:
                            chemicals.append(name)

                # Publication types
                if paper.get("pubmed_publication_types"):
                    pub_types_list.extend(paper["pubmed_publication_types"])

                # Grants
                if paper.get("pubmed_grants"):
                    grants_found += 1

        if mesh_descriptors:
            from collections import Counter

            mesh_counts = Counter(mesh_descriptors)
            print("\n  Top MeSH Terms in Sample:")
            for term, count in mesh_counts.most_common(config.DEFAULT_MAX_RESULTS):
                print(f"    - {term}: {count} occurrences")

        if chemicals:
            chem_counts = Counter(chemicals)
            print("\n  Top Chemicals in Sample:")
            for chem, count in chem_counts.most_common(config.DEFAULT_MAX_RESULTS):
                print(f"    - {chem}: {count} occurrences")

        if pub_types_list:
            type_counts = Counter(pub_types_list)
            print("\n  Publication Types in Sample:")
            for pub_type, count in type_counts.most_common(config.DEFAULT_MAX_RESULTS):
                print(f"    - {pub_type}: {count}")

        if grants_found:
            print(f"\n  Papers with grant information: {grants_found}/{len(papers)}")

    print("\n" + "=" * 80)


def has_pubmed_data(paper: dict[str, Any]) -> bool:
    """Check if paper already has PubMed enrichment."""
    # Check for pubmed_enriched marker
    if paper.get("pubmed_enriched"):
        return True
    # Check for any pubmed_ prefixed fields
    return any(key.startswith("pubmed_") for key in paper)


def main() -> None:
    """Run the main program.

    .
    """
    parser = argparse.ArgumentParser(description="V5 Pipeline Stage 7: PubMed Enrichment")
    parser.add_argument(
        "--input", default="unpaywall_enriched_final", help="Input directory with Unpaywall enriched papers"
    )
    parser.add_argument(
        "--output", default="pubmed_enriched_final", help="Output directory for PubMed enriched papers"
    )
    parser.add_argument("--api-key", help="NCBI API key for higher rate limits (10/sec vs 3/sec)")
    parser.add_argument("--test", action="store_true", help="Test mode - use small dataset")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")
    parser.add_argument("--force", action="store_true", help="Force re-enrichment even if already processed")

    args = parser.parse_args()

    # Check for API key in environment if not provided
    if not args.api_key:
        args.api_key = os.environ.get("NCBI_API_KEY")

    # Test mode uses small dataset
    if args.test:
        args.input = "unpaywall_test_output"
        args.output = "pubmed_test_output"

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
        print("Please run Unpaywall enrichment first (v5_unpaywall_pipeline.py)")
        return

    # Initialize enricher
    print("=" * 80)
    print("V5 PIPELINE - STAGE 7: PUBMED ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    if args.api_key:
        print("API Key: Provided (10 requests/sec)")
    else:
        print("API Key: Not provided (3 requests/sec)")
        print("Get a free API key at: https://www.ncbi.nlm.nih.gov/account/")
    print()

    enricher = PubMedEnricher(api_key=args.api_key)

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

    # Collect identifiers
    identifiers = []
    papers_by_id: dict[str, tuple[str, Any]] = {}
    papers_without_id = []
    skipped_already_enriched = 0

    for paper_file in paper_files:
        with open(paper_file) as f:
            paper = json.load(f)

            # Skip if already enriched (unless force mode)
            if not args.force and has_pubmed_data(paper):
                skipped_already_enriched += 1
                papers_by_id[paper_file.stem] = (paper_file.stem, paper)  # Keep for final save
                continue

            # Check for existing PMID or DOI
            id_dict = {}
            if paper.get("pmid"):
                id_dict["pmid"] = paper["pmid"]
            elif paper.get("pubmed_pmid"):  # From previous enrichment
                id_dict["pmid"] = paper["pubmed_pmid"]
            elif paper.get("doi"):
                id_dict["doi"] = paper["doi"]

            if id_dict:
                key = id_dict.get("doi") or id_dict.get("pmid")
                if key:
                    identifiers.append(id_dict)
                    papers_by_id[key] = (paper_file.stem, paper)
            else:
                papers_without_id.append((paper_file.stem, paper))

    print(f"Found {len(identifiers)} papers with DOIs or PMIDs")
    if skipped_already_enriched > 0:
        print(f"Skipped (already enriched): {skipped_already_enriched}")
    if papers_without_id:
        print(f"Skipping {len(papers_without_id)} papers without identifiers")
    if args.force:
        print("Force mode: Re-enriching all papers")

    if not identifiers:
        print("No papers with identifiers to process")
        return

    # Process papers
    print("\nProcessing papers with PubMed API...")
    print("Note: PubMed primarily covers biomedical literature")
    print("Expected coverage: ~30% of general research papers")

    start_time = time.time()

    # Process in batches
    batch_size = config.MEDIUM_API_CHECKPOINT_INTERVAL // 2  # 100 papers (PubMed efetch can handle up to 200)
    all_results = {}

    for i in range(0, len(identifiers), batch_size):
        batch = identifiers[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(identifiers) + batch_size - 1) // batch_size

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} papers)...")

        # Process batch
        batch_results = enricher.enrich_batch(batch, batch_size=batch_size)
        all_results.update(batch_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Enriched: {stats['enriched']}")
        print(f"  Not in PubMed: {stats['not_in_pubmed']}")
        if stats["enriched"] > 0:
            print(f"  MeSH coverage: {stats['mesh_coverage']}")

        # Save checkpoint every 100 papers
        if (i + batch_size) % config.MEDIUM_API_CHECKPOINT_INTERVAL == 0 or (i + batch_size) >= len(
            identifiers
        ):
            print("  Saving checkpoint...")
            for key, (paper_id, original_paper) in list(papers_by_id.items())[: i + batch_size]:
                if key in all_results:
                    enrichment = all_results[key]
                    for field, value in enrichment.items():
                        if value is not None:
                            original_paper[f"pubmed_{field}"] = value

                output_file = output_path / f"{paper_id}.json"
                with open(output_file, "w") as f:
                    json.dump(original_paper, f, indent=2)

    # Save all papers
    print("\nSaving all papers...")
    enriched_count = 0
    for key, (paper_id, original_paper) in papers_by_id.items():
        if key in all_results:
            enrichment = all_results[key]

            # Add PubMed fields with prefix
            for field, value in enrichment.items():
                if value is not None:
                    original_paper[f"pubmed_{field}"] = value

            # Add enrichment marker
            original_paper["pubmed_enriched"] = True
            original_paper["pubmed_enriched_date"] = datetime.now(UTC).isoformat()

            enriched_count += 1

        # Save paper (enriched or not)
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(original_paper, f, indent=2)

    # Also copy papers without identifiers
    for paper_id, paper in papers_without_id:
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate final report
    final_stats = enricher.get_statistics()
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_stage": "7_pubmed_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_with_identifiers": len(identifiers),
            "papers_without_identifiers": len(papers_without_id),
            "papers_enriched": final_stats["enriched"],
            "papers_failed": final_stats["failed"],
            "enrichment_rate": final_stats["enrichment_rate"],
            "not_in_pubmed": final_stats["not_in_pubmed"],
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / len(identifiers), 2) if identifiers else 0,
        },
        "biomedical_metadata": {
            "mesh_terms": final_stats["has_mesh"],
            "mesh_coverage": final_stats["mesh_coverage"],
            "chemicals": final_stats["has_chemicals"],
            "publication_types": final_stats["publication_types"],
        },
        "errors": final_stats["errors"],
    }

    report_file = output_path / "pubmed_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"Papers enriched: {final_stats['enriched']}/{len(identifiers)} ({final_stats['enrichment_rate']})")
    print(f"Papers not in PubMed: {final_stats['not_in_pubmed']}")
    if final_stats["enriched"] > 0:
        print(f"MeSH term coverage: {final_stats['has_mesh']} papers ({final_stats['mesh_coverage']})")
        print(f"Clinical trials: {final_stats['publication_types']['clinical_trials']}")
        print(f"Reviews: {final_stats['publication_types']['reviews']}")
        print(f"Meta-analyses: {final_stats['publication_types']['meta_analyses']}")
    print(f"Processing time: {elapsed_time:.1f} seconds")
    print(f"Output directory: {output_path}")
    print(f"Report saved to: {report_file}")

    # Analyze results
    if final_stats["enriched"] > 0:
        analyze_enrichment_results(output_path)


if __name__ == "__main__":
    main()
