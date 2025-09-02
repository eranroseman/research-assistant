#!/usr/bin/env python3
"""OpenAlex V5 Unified Enrichment with Checkpoint Support.

Single-file implementation combining API logic and pipeline orchestration.
Follows the same pattern as other v5 pipeline stages.

Features:
- Checkpoint recovery support for resuming after interruption
- Batch processing with OpenAlex API (50 papers per batch)
- Topic classification and SDG mapping
- Citation metrics and venue information
- Automatic retry logic with exponential backoff
"""

import json
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import Counter
import statistics
from src import config


def create_session(email: str | None = None) -> requests.Session:
    """Create HTTP session with retry logic and polite pool headers."""
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Add email to headers for polite pool (higher rate limits)
    if email:
        session.headers.update({"User-Agent": f"mailto:{email}"})

    return session


def clean_doi(doi: str) -> str | None:
    """Clean and validate a DOI string."""
    if not doi:
        return None

    # Remove whitespace and convert to lowercase
    clean = doi.strip().lower()

    # Handle URLs
    if clean.startswith("http"):
        if "doi.org/" in clean:
            clean = clean.split("doi.org/")[-1]
        elif "doi=" in clean:
            import re

            match = re.search(r"doi=([^&]+)", clean)
            if match:
                clean = match.group(1)
            else:
                return None
        else:
            return None

    # Remove common suffixes from extraction errors
    clean = clean.split(".from")[0]
    clean = clean.split("keywords")[0]
    clean = clean.rstrip(".)•")

    # Validate basic DOI format
    if not clean.startswith("10."):
        return None
    if len(clean) < 7 or len(clean) > 100:  # Reasonable DOI length limits
        return None

    return clean


def get_select_fields() -> str:
    """Get fields to retrieve from OpenAlex API."""
    fields = [
        "id",
        "doi",
        "title",
        "publication_year",
        "topics",
        "sustainable_development_goals",
        "cited_by_count",
        "counts_by_year",
        "authorships",
        "primary_location",
        "type",
        "open_access",
        "keywords",
        "concepts",
        "mesh",
        "referenced_works_count",
        "related_works",
        "cited_by_percentile_year",
        "biblio",
        "is_retracted",
        "is_paratext",
    ]
    return ",".join(fields)


def process_work(work: dict[str, Any]) -> dict[str, Any]:
    """Process OpenAlex work into enriched metadata."""
    enriched = {
        "openalex_id": work.get("id", "").replace("https://openalex.org/", ""),
        "doi": work.get("doi", "").replace("https://doi.org/", ""),
        "title": work.get("title"),
        "year": work.get("publication_year"),
        "type": work.get("type"),
        "is_retracted": work.get("is_retracted", False),
        "is_paratext": work.get("is_paratext", False),
    }

    # Topics (hierarchical classification)
    topics = work.get("topics", [])
    if topics:
        enriched["topics"] = []
        for topic in topics[:3]:  # Top 3 topics
            enriched["topics"].append(
                {
                    "id": topic.get("id"),
                    "name": topic.get("display_name"),
                    "score": topic.get("score"),
                    "domain": topic.get("domain", {}).get("display_name"),
                    "field": topic.get("field", {}).get("display_name"),
                    "subfield": topic.get("subfield", {}).get("display_name"),
                }
            )

    # Sustainable Development Goals
    sdgs = work.get("sustainable_development_goals", [])
    if sdgs:
        enriched["sdgs"] = []
        for sdg in sdgs:
            enriched["sdgs"].append(
                {"id": sdg.get("id"), "name": sdg.get("display_name"), "score": sdg.get("score")}
            )

    # Citation metrics
    enriched["citation_count"] = work.get("cited_by_count", 0)
    enriched["reference_count"] = work.get("referenced_works_count", 0)

    # Citation velocity
    counts = work.get("counts_by_year", [])
    if counts:
        enriched["citations_by_year"] = {str(c["year"]): c["cited_by_count"] for c in counts if c.get("year")}

    # Citation percentile
    percentile = work.get("cited_by_percentile_year")
    if percentile:
        enriched["citation_percentile"] = {"min": percentile.get("min"), "max": percentile.get("max")}

    # Authors and institutions
    authorships = work.get("authorships", [])
    if authorships:
        enriched["authors"] = []
        institutions = set()

        for authorship in authorships:
            author = authorship.get("author", {})
            author_data = {
                "id": author.get("id"),
                "name": author.get("display_name"),
                "orcid": author.get("orcid"),
            }
            enriched["authors"].append(author_data)

            # Collect institutions
            for inst in authorship.get("institutions", []):
                if inst.get("display_name"):
                    institutions.add(inst["display_name"])

        if institutions:
            enriched["institutions"] = list(institutions)

    # Open Access status
    oa = work.get("open_access", {})
    if oa:
        enriched["open_access"] = {
            "is_oa": oa.get("is_oa", False),
            "status": oa.get("oa_status"),
            "url": oa.get("oa_url"),
        }

    # Keywords and concepts
    keywords = work.get("keywords", [])
    if keywords:
        enriched["keywords"] = [
            {"name": k.get("display_name"), "score": k.get("score")}
            for k in keywords
            if k.get("display_name")
        ]

    # MeSH terms (if available)
    mesh = work.get("mesh", [])
    if mesh:
        enriched["mesh_terms"] = [
            {
                "descriptor": m.get("descriptor_name"),
                "qualifier": m.get("qualifier_name"),
                "is_major": m.get("is_major_topic"),
            }
            for m in mesh
        ]

    # Venue information
    location = work.get("primary_location", {})
    if location:
        source = location.get("source", {})
        if source:
            enriched["venue"] = {
                "id": source.get("id"),
                "name": source.get("display_name"),
                "type": source.get("type"),
                "issn": source.get("issn_l"),
                "is_oa": source.get("is_oa"),
            }

    # Bibliographic info
    biblio = work.get("biblio", {})
    if biblio:
        enriched["volume"] = biblio.get("volume")
        enriched["issue"] = biblio.get("issue")
        enriched["first_page"] = biblio.get("first_page")
        enriched["last_page"] = biblio.get("last_page")

    return enriched


def enrich_batch(
    session: requests.Session, dois: list[str], batch_size: int = 50
) -> dict[str, dict[str, Any]]:
    """Enrich multiple papers in a single API call."""
    results = {}
    base_url = "https://api.openalex.org"

    # Clean DOIs
    clean_dois = []
    doi_map = {}  # Map clean to original

    for doi in dois[:batch_size]:
        clean = clean_doi(doi)
        if clean:
            clean_dois.append(clean)
            doi_map[clean] = doi

    if not clean_dois:
        return results

    try:
        # Build OR filter for OpenAlex
        doi_filter = f"doi:{'|'.join(clean_dois)}"

        params = {
            "filter": doi_filter,
            "per_page": batch_size,
            "select": get_select_fields(),
        }

        response = session.get(f"{base_url}/works", params=params, timeout=60)
        response.raise_for_status()

        data = response.json()

        # Process results
        for work in data.get("results", []):
            processed = process_work(work)
            if processed and processed.get("doi"):
                # Map back to original DOI format
                clean_doi_result = processed["doi"].lower()
                original_doi = doi_map.get(clean_doi_result, clean_doi_result)
                results[original_doi] = processed

    except Exception as e:
        print(f"Error in batch enrichment: {e}")

    return results


def load_checkpoint(checkpoint_file: Path) -> dict[str, Any]:
    """Load checkpoint data if it exists."""
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            return json.load(f)
    return {"processed_papers": [], "last_batch": 0, "stats": {}}


def save_checkpoint(checkpoint_file: Path, checkpoint_data: dict[str, Any]) -> None:
    """Save checkpoint data."""
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f, indent=2)


def analyze_enrichment_results(output_dir: Path) -> None:
    """Analyze and report enrichment statistics."""
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
            if paper_file.name in ["openalex_enrichment_report.json", ".openalex_checkpoint.json"]:
                continue

            with open(paper_file) as f:
                paper = json.load(f)

                if paper.get("openalex_topics"):
                    for topic in paper["openalex_topics"]:
                        if topic.get("domain"):
                            topic_domains.append(topic["domain"])

                if paper.get("openalex_sdgs"):
                    for sdg in paper["openalex_sdgs"]:
                        if sdg.get("name"):
                            sdg_goals.append(sdg["name"])

                if paper.get("openalex_citation_count") is not None:
                    citation_counts.append(paper["openalex_citation_count"])

                if paper.get("openalex_open_access", {}).get("is_oa"):
                    oa_papers += 1

        if topic_domains:
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
            print("\n  Citation Statistics:")
            print(f"    - Mean: {statistics.mean(citation_counts):.1f}")
            print(f"    - Median: {statistics.median(citation_counts):.1f}")
            print(f"    - Max: {max(citation_counts)}")

        print(f"\n  Open Access: {oa_papers}/{len(papers)} papers")

    print("\n" + "=" * 80)


def has_openalex_data(paper: dict) -> bool:
    """Check if paper already has OpenAlex enrichment."""
    # Check for openalex_enriched marker
    if paper.get("openalex_enriched"):
        return True
    # Check for any openalex_ prefixed fields
    return any(key.startswith("openalex_") for key in paper)


def main():
    """Main entry point for OpenAlex enrichment."""
    parser = argparse.ArgumentParser(description="OpenAlex V5 Unified Enrichment with Checkpoint Support")
    parser.add_argument("--input", required=True, help="Input directory with papers to enrich")
    parser.add_argument("--output", required=True, help="Output directory for enriched papers")
    parser.add_argument(
        "--email",
        default="eran-roseman@uiowa.edu",
        help="Email for OpenAlex polite pool (higher rate limits)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=config.FAST_API_CHECKPOINT_INTERVAL,
        help="Papers per checkpoint (default 500)",
    )
    parser.add_argument("--reset", action="store_true", help="Reset checkpoint and start fresh")
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process (for testing)")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")
    parser.add_argument("--force", action="store_true", help="Force re-enrichment even if already processed")

    args = parser.parse_args()

    # Setup paths
    input_path = Path(args.input)
    output_path = Path(args.output)
    checkpoint_file = output_path / ".openalex_checkpoint.json"

    # Analyze only mode
    if args.analyze_only:
        if not output_path.exists():
            print(f"Output directory {output_path} does not exist")
            return
        analyze_enrichment_results(output_path)
        return

    # Check input directory
    if not input_path.exists():
        print(f"Error: Input directory {input_path} does not exist")
        sys.exit(1)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Reset checkpoint if requested
    if args.reset and checkpoint_file.exists():
        checkpoint_file.unlink()
        print("Checkpoint reset")

    # Load checkpoint
    checkpoint_data = load_checkpoint(checkpoint_file)
    processed_papers = set(checkpoint_data.get("processed_papers", []))
    last_batch = checkpoint_data.get("last_batch", 0)

    print("=" * 80)
    print("OPENALEX V5 UNIFIED ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Email: {args.email} (polite pool)")
    print(f"Batch size: {args.batch_size}")

    if processed_papers:
        print(f"Resuming from checkpoint: {len(processed_papers)} papers already processed")

    # Create session
    session = create_session(args.email)

    # Load all papers
    paper_files = list(input_path.glob("*.json"))
    if not paper_files:
        print("No papers found in input directory")
        return

    print(f"\nFound {len(paper_files)} total papers")

    # Filter out already processed papers
    papers_to_process = []
    papers_with_dois = []
    papers_by_doi = {}
    papers_without_doi = []
    skipped_already_enriched = 0

    for paper_file in paper_files:
        if paper_file.name in ["s2_batch_report.json", "crossref_report.json", ".openalex_checkpoint.json"]:
            continue

        paper_id = paper_file.stem

        # Skip if already processed
        if paper_id in processed_papers:
            continue

        # Apply max papers limit if specified
        if args.max_papers and len(papers_to_process) >= args.max_papers:
            break

        with open(paper_file) as f:
            paper = json.load(f)

            # Skip if already enriched (unless force mode)
            if not args.force and has_openalex_data(paper):
                skipped_already_enriched += 1
                processed_papers.add(paper_id)
                continue

            papers_to_process.append(paper_file)
            doi = paper.get("doi")
            if doi:
                papers_with_dois.append((paper_id, doi))
                papers_by_doi[doi] = paper
            else:
                papers_without_doi.append(paper_id)

    print(f"Papers to process: {len(papers_to_process)}")
    if skipped_already_enriched > 0:
        print(f"Skipped (already enriched): {skipped_already_enriched}")
    print(f"Papers with DOIs: {len(papers_with_dois)}")
    if papers_without_doi:
        print(f"Papers without DOIs: {len(papers_without_doi)}")
    if args.force:
        print("Force mode: Re-enriching all papers")

    if not papers_to_process:
        print("\nAll papers already processed!")
        analyze_enrichment_results(output_path)
        return

    # Process in batches
    enriched_count = checkpoint_data.get("stats", {}).get("enriched_count", 0)
    failed_count = checkpoint_data.get("stats", {}).get("failed_count", 0)
    total_batches = (len(papers_with_dois) + args.batch_size - 1) // args.batch_size

    start_time = time.time()

    # Process papers with DOIs in batches
    for i in range(last_batch * args.batch_size, len(papers_with_dois), args.batch_size):
        batch = papers_with_dois[i : i + args.batch_size]
        batch_num = i // args.batch_size + 1

        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} papers)...")

        # Extract DOIs
        batch_dois = [doi for _, doi in batch]

        # Enrich batch
        batch_results = enrich_batch(session, batch_dois, args.batch_size)

        # Save enriched papers
        for paper_id, doi in batch:
            original_paper = papers_by_doi[doi].copy()

            if doi in batch_results:
                enrichment = batch_results[doi]

                # Add OpenAlex fields with prefix
                for key, value in enrichment.items():
                    if value is not None:
                        original_paper[f"openalex_{key}"] = value

                # Add enrichment marker
                original_paper["openalex_enriched"] = True
                original_paper["openalex_enriched_date"] = datetime.now(UTC).isoformat()

                enriched_count += 1
                print(f"  ✓ {paper_id}: enriched with {len(enrichment)} fields")
            else:
                failed_count += 1
                print(f"  ✗ {paper_id}: not found in OpenAlex")

            # Save paper (enriched or not)
            output_file = output_path / f"{paper_id}.json"
            with open(output_file, "w") as f:
                json.dump(original_paper, f, indent=2)

            # Update checkpoint
            processed_papers.add(paper_id)

        # Save checkpoint after each batch
        checkpoint_data = {
            "processed_papers": list(processed_papers),
            "last_batch": batch_num,
            "stats": {"enriched_count": enriched_count, "failed_count": failed_count},
        }
        save_checkpoint(checkpoint_file, checkpoint_data)

        # Rate limiting
        if batch_num < total_batches:
            time.sleep(0.1)  # Polite delay between batches

    # Copy papers without DOIs
    for paper_id in papers_without_doi:
        input_file = input_path / f"{paper_id}.json"
        output_file = output_path / f"{paper_id}.json"
        with open(input_file) as f:
            paper = json.load(f)
        with open(output_file, "w") as f:
            json.dump(paper, f, indent=2)
        processed_papers.add(paper_id)

    elapsed_time = time.time() - start_time

    # Calculate final statistics
    total_processed = len(processed_papers)
    total_with_dois = len([p for p in processed_papers if p not in papers_without_doi])

    # Generate report
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_stage": "openalex_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_processed": total_processed,
            "papers_with_dois": total_with_dois,
            "papers_without_dois": len(papers_without_doi),
            "papers_enriched": enriched_count,
            "papers_failed": failed_count,
            "enrichment_rate": f"{(enriched_count / total_with_dois * 100):.1f}%"
            if total_with_dois
            else "0%",
            "processing_time_seconds": round(elapsed_time, 1),
            "batches_processed": total_batches,
            "avg_papers_per_batch": args.batch_size,
        },
    }

    # Analyze coverage from enriched papers
    topic_coverage = 0
    sdg_coverage = 0
    oa_coverage = 0

    for paper_id in processed_papers:
        if paper_id in papers_without_doi:
            continue
        output_file = output_path / f"{paper_id}.json"
        if output_file.exists():
            with open(output_file) as f:
                paper = json.load(f)
                if paper.get("openalex_topics"):
                    topic_coverage += 1
                if paper.get("openalex_sdgs"):
                    sdg_coverage += 1
                if paper.get("openalex_open_access", {}).get("is_oa"):
                    oa_coverage += 1

    if enriched_count > 0:
        report["coverage"] = {
            "topics": f"{(topic_coverage / enriched_count * 100):.1f}%",
            "sdgs": f"{(sdg_coverage / enriched_count * 100):.1f}%",
            "open_access": f"{(oa_coverage / enriched_count * 100):.1f}%",
        }

    # Save report
    report_file = output_path / "openalex_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    # Remove checkpoint file after successful completion
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(
        f"Papers enriched: {enriched_count}/{total_with_dois} ({(enriched_count / total_with_dois * 100):.1f}%)"
        if total_with_dois
        else "No papers with DOIs"
    )
    print(f"Processing time: {elapsed_time:.1f} seconds")
    print(f"Output directory: {output_path}")
    print(f"Report saved to: {report_file}")

    # Analyze results
    analyze_enrichment_results(output_path)


if __name__ == "__main__":
    main()
