#!/usr/bin/env python3
"""Unpaywall Enrichment for V5 Pipeline
Identifies open access versions and provides direct links to free full-text PDFs.

Features:
- OA status classification (gold, green, hybrid, bronze, closed)
- Best OA location with direct PDF links
- Repository information (PMC, arXiv, institutional repos)
- License information (CC-BY, CC0, etc.)
- Evidence tracking for OA determination
- ~52% global OA rate (higher for recent papers)
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict


class UnpaywallEnricher:
    """Enrich papers with Unpaywall open access metadata."""

    def __init__(self, email: str):
        """Initialize Unpaywall enricher.

        Args:
            email: Required email for API access
        """
        if not email:
            raise ValueError("Email is required for Unpaywall API access")

        self.base_url = "https://api.unpaywall.org/v2"
        self.email = email
        self.session = self._create_session()
        self.stats = defaultdict(int)

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set user agent
        session.headers.update({"User-Agent": f"Research Assistant v5.0 (mailto:{self.email})"})

        return session

    def enrich_single(self, doi: str) -> dict[str, Any] | None:
        """Enrich a single paper by DOI.

        Args:
            doi: Paper DOI

        Returns:
            Enriched metadata or None if not found
        """
        try:
            # Clean DOI (reuse logic from OpenAlex)
            clean_doi = self._clean_doi(doi)
            if not clean_doi:
                self.stats["invalid_doi"] += 1
                return None

            # Query Unpaywall
            url = f"{self.base_url}/{clean_doi}"
            params = {"email": self.email}

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 404:
                self.stats["not_found"] += 1
                return None

            response.raise_for_status()

            data = response.json()
            return self._process_oa_data(data)

        except requests.exceptions.Timeout:
            self.stats["timeout"] += 1
            print(f"Timeout for {doi}")
        except requests.exceptions.RequestException as e:
            self.stats["error"] += 1
            print(f"Error enriching {doi}: {e}")

        return None

    def _clean_doi(self, doi: str) -> str | None:
        """Clean and validate a DOI.
        Reuses logic from OpenAlex enricher for consistency.

        Args:
            doi: Raw DOI string

        Returns:
            Cleaned DOI or None if invalid
        """
        if not doi:
            return None

        # Remove whitespace and convert to lowercase
        clean = doi.strip().lower()

        # Handle URLs
        if clean.startswith("http"):
            # Extract DOI from URL
            if "doi.org/" in clean:
                clean = clean.split("doi.org/")[-1]
            elif "doi=" in clean:
                # Extract from query parameter
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
        if len(clean) < 10 or len(clean) > 100:
            return None

        return clean

    def _process_oa_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process Unpaywall data into enriched metadata.

        Args:
            data: Raw Unpaywall response

        Returns:
            Processed metadata
        """
        enriched = {
            "doi": data.get("doi", "").replace("https://doi.org/", ""),
            "is_oa": data.get("is_oa", False),
            "oa_status": data.get("oa_status"),  # gold, green, hybrid, bronze, closed
            "has_repository_copy": data.get("has_repository_copy", False),
            "journal_is_oa": data.get("journal_is_oa", False),
            "journal_is_in_doaj": data.get("journal_is_in_doaj", False),
        }

        # Best OA location (highest quality/most reliable)
        best_location = data.get("best_oa_location")
        if best_location:
            enriched["best_oa_location"] = {
                "url": best_location.get("url"),
                "url_for_pdf": best_location.get("url_for_pdf"),
                "url_for_landing_page": best_location.get("url_for_landing_page"),
                "evidence": best_location.get("evidence"),
                "license": best_location.get("license"),
                "version": best_location.get(
                    "version"
                ),  # publishedVersion, acceptedVersion, submittedVersion
                "host_type": best_location.get("host_type"),  # publisher, repository
                "is_best": True,
            }

            # Repository information
            if best_location.get("pmh_id"):
                enriched["best_oa_location"]["pmh_id"] = best_location["pmh_id"]
            if best_location.get("repository_institution"):
                enriched["best_oa_location"]["repository"] = best_location["repository_institution"]

        # All OA locations (including alternatives)
        all_locations = data.get("oa_locations", [])
        if all_locations and len(all_locations) > 1:
            enriched["alternative_oa_locations"] = []
            for loc in all_locations:
                if loc != best_location:  # Skip best location (already captured)
                    alt_location = {
                        "url": loc.get("url"),
                        "url_for_pdf": loc.get("url_for_pdf"),
                        "evidence": loc.get("evidence"),
                        "license": loc.get("license"),
                        "version": loc.get("version"),
                        "host_type": loc.get("host_type"),
                    }

                    # Repository information
                    if loc.get("pmh_id"):
                        alt_location["pmh_id"] = loc["pmh_id"]
                    if loc.get("repository_institution"):
                        alt_location["repository"] = loc["repository_institution"]

                    enriched["alternative_oa_locations"].append(alt_location)

        # Publication info (basic metadata from Unpaywall)
        enriched["title"] = data.get("title")
        enriched["year"] = data.get("year")
        enriched["journal_name"] = data.get("journal_name")
        enriched["publisher"] = data.get("publisher")

        # First and last author (useful for disambiguation)
        z_authors = data.get("z_authors", [])
        if z_authors:
            if z_authors[0].get("family"):
                enriched["first_author"] = (
                    f"{z_authors[0].get('given', '')} {z_authors[0].get('family', '')}".strip()
                )
            if len(z_authors) > 1 and z_authors[-1].get("family"):
                enriched["last_author"] = (
                    f"{z_authors[-1].get('given', '')} {z_authors[-1].get('family', '')}".strip()
                )

        # Track OA status for statistics
        if enriched["is_oa"]:
            self.stats[f"oa_{enriched['oa_status']}"] += 1
        else:
            self.stats["closed"] += 1

        return enriched

    def enrich_batch(
        self, dois: list[str], parallel: bool = True, max_workers: int = 5
    ) -> dict[str, dict[str, Any]]:
        """Enrich multiple papers. Unlike OpenAlex, Unpaywall doesn't support batch queries,
        so we process individually with optional parallelization.

        Args:
            dois: List of DOIs
            parallel: Whether to use parallel processing
            max_workers: Number of parallel workers

        Returns:
            Dictionary mapping DOI to enriched metadata
        """
        results = {}

        if parallel and len(dois) > 10:
            # Use parallel processing for larger batches
            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_doi = {executor.submit(self.enrich_single, doi): doi for doi in dois}

                # Process completed tasks
                for future in as_completed(future_to_doi):
                    original_doi = future_to_doi[future]
                    try:
                        result = future.result(timeout=30)
                        if result:
                            results[original_doi] = result
                            self.stats["enriched"] += 1
                        else:
                            self.stats["failed"] += 1
                    except Exception as e:
                        print(f"Error processing {original_doi}: {e}")
                        self.stats["failed"] += 1

                    # Rate limiting between completed requests
                    time.sleep(0.1)
        else:
            # Sequential processing for small batches
            for doi in dois:
                result = self.enrich_single(doi)
                if result:
                    results[doi] = result
                    self.stats["enriched"] += 1
                else:
                    self.stats["failed"] += 1

                # Rate limiting
                time.sleep(0.1)

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get enrichment statistics."""
        total = self.stats["enriched"] + self.stats["failed"]
        oa_total = sum(self.stats[k] for k in self.stats if k.startswith("oa_"))

        return {
            "total_processed": total,
            "enriched": self.stats["enriched"],
            "failed": self.stats["failed"],
            "enrichment_rate": f"{(self.stats['enriched'] / total * 100):.1f}%" if total else "0%",
            "oa_discovered": oa_total,
            "oa_rate": f"{(oa_total / self.stats['enriched'] * 100):.1f}%"
            if self.stats["enriched"]
            else "0%",
            "oa_breakdown": {
                "gold": self.stats.get("oa_gold", 0),
                "green": self.stats.get("oa_green", 0),
                "hybrid": self.stats.get("oa_hybrid", 0),
                "bronze": self.stats.get("oa_bronze", 0),
            },
            "errors": {
                "not_found": self.stats.get("not_found", 0),
                "invalid_doi": self.stats.get("invalid_doi", 0),
                "timeout": self.stats.get("timeout", 0),
                "other": self.stats.get("error", 0),
            },
        }


def process_directory(input_dir: str, output_dir: str, email: str, parallel: bool = True):
    """Process all papers in a directory with Unpaywall enrichment.

    Args:
        input_dir: Directory containing paper JSON files
        output_dir: Directory to save enriched papers
        email: Required email for API access
        parallel: Whether to use parallel processing
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize enricher
    enricher = UnpaywallEnricher(email=email)

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    print(f"Found {len(paper_files)} papers to process")

    # Collect papers with DOIs
    papers_with_dois = []
    papers_by_doi = {}
    papers_without_doi = []

    for paper_file in paper_files:
        # Skip report files
        if "report" in paper_file.name:
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

    # Process all DOIs (with progress tracking)
    all_dois = [doi for _, doi in papers_with_dois]
    start_time = time.time()

    print("\nProcessing papers with Unpaywall API...")
    print("Note: This may take a while due to rate limiting (1 request per DOI)")

    # Process in chunks for better progress tracking
    chunk_size = 50
    all_results = {}

    for i in range(0, len(all_dois), chunk_size):
        chunk = all_dois[i : i + chunk_size]
        chunk_num = i // chunk_size + 1
        total_chunks = (len(all_dois) + chunk_size - 1) // chunk_size

        print(f"\nProcessing chunk {chunk_num}/{total_chunks} ({len(chunk)} papers)...")
        chunk_results = enricher.enrich_batch(chunk, parallel=parallel)
        all_results.update(chunk_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Progress: {stats['enriched']}/{stats['total_processed']} enriched")
        print(f"  OA discovered: {stats['oa_discovered']} ({stats['oa_rate']})")

    # Save enriched papers
    print("\nSaving enriched papers...")
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

    # Generate detailed report
    stats = enricher.get_statistics()
    report = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_stage": "6_unpaywall_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_with_dois": len(papers_with_dois),
            "papers_without_dois": len(papers_without_doi),
            "papers_enriched": stats["enriched"],
            "papers_failed": stats["failed"],
            "enrichment_rate": stats["enrichment_rate"],
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / len(papers_with_dois), 2) if papers_with_dois else 0,
        },
        "open_access": {
            "papers_with_oa": stats["oa_discovered"],
            "oa_rate": stats["oa_rate"],
            "oa_breakdown": stats["oa_breakdown"],
        },
        "errors": stats["errors"],
    }

    report_file = output_path / "unpaywall_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\nEnrichment complete!")
    print(f"  Papers enriched: {stats['enriched']}/{len(papers_with_dois)} ({stats['enrichment_rate']})")
    print(f"  Open Access found: {stats['oa_discovered']} ({stats['oa_rate']})")
    print("  OA breakdown:")
    for oa_type, count in stats["oa_breakdown"].items():
        if count > 0:
            print(f"    - {oa_type}: {count}")
    print(f"  Processing time: {elapsed_time:.1f} seconds")
    print(f"  Report saved to: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enrich papers with Unpaywall open access metadata")
    parser.add_argument("--input", default="openalex_enriched_final", help="Input directory with papers")
    parser.add_argument("--output", default="unpaywall_enriched", help="Output directory")
    parser.add_argument("--email", required=True, help="Email for Unpaywall API (required)")
    parser.add_argument("--test", action="store_true", help="Test with single paper")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel processing")

    args = parser.parse_args()

    if args.test:
        # Test with a single DOI
        enricher = UnpaywallEnricher(email=args.email)
        test_doi = "10.1038/s41586-020-2649-2"  # Example Nature paper

        print(f"Testing with DOI: {test_doi}")
        result = enricher.enrich_single(test_doi)

        if result:
            print("\nEnrichment successful!")
            print(json.dumps(result, indent=2))

            # Show statistics
            stats = enricher.get_statistics()
            print(f"\nStatistics: {json.dumps(stats, indent=2)}")
        else:
            print("Enrichment failed")
    else:
        process_directory(args.input, args.output, args.email, parallel=not args.no_parallel)
