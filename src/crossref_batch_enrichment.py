#!/usr/bin/env python3
"""Batch CrossRef enrichment using filter API for faster processing.
Processes multiple DOIs in single API calls (up to 100 per batch).
"""

import json
import logging
import time
import requests
from pathlib import Path
from datetime import datetime
import argparse
import sys
import os

# Add src directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from config import CROSSREF_POLITE_EMAIL
except ImportError:
    CROSSREF_POLITE_EMAIL = "research.assistant@university.edu"

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BatchCrossRefEnricher:
    """Batch CrossRef enricher for faster processing."""

    def __init__(self, mailto=None, batch_size=50):
        """Initialize enricher with polite pool access.

        Args:
            mailto: Email for polite pool access
            batch_size: Number of DOIs per batch (max 100, default 50 for safety)
        """
        if mailto is None:
            mailto = CROSSREF_POLITE_EMAIL

        self.mailto = mailto
        self.batch_size = min(batch_size, 100)  # Cap at 100
        self.base_url = "https://api.crossref.org/works"

        logger.info(f"Using CrossRef polite pool with email: {mailto}")
        logger.info(f"Batch size: {self.batch_size} DOIs per request")

        self.stats = {
            "total_papers": 0,
            "papers_with_dois": 0,
            "papers_enriched": 0,
            "papers_failed": 0,
            "api_calls": 0,
            "batches_processed": 0,
        }

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"ResearchAssistant/5.0 (mailto:{mailto})"})

    def fetch_batch(self, dois: list[str]) -> dict[str, dict]:
        """Fetch metadata for a batch of DOIs.

        Args:
            dois: List of DOIs to fetch (up to 100)

        Returns:
            Dictionary mapping DOI to metadata
        """
        if not dois:
            return {}

        # Build filter query with multiple DOIs
        # Format: filter=doi:10.1234/abc,doi:10.5678/def
        doi_filters = ",doi:".join(dois)
        params = {"filter": f"doi:{doi_filters}", "rows": len(dois), "mailto": self.mailto}

        try:
            response = self.session.get(self.base_url, params=params, timeout=30)
            self.stats["api_calls"] += 1

            if response.status_code == 200:
                data = response.json()
                results = {}

                # Map results back to DOIs
                for item in data.get("message", {}).get("items", []):
                    doi = item.get("DOI", "").lower()
                    if doi:
                        results[doi] = item

                return results
            logger.warning(f"API returned status {response.status_code}")
            return {}

        except Exception as e:
            logger.error(f"Batch query failed: {e}")
            return {}

    def extract_metadata(self, crossref_data: dict) -> dict:
        """Extract comprehensive metadata from CrossRef response.

        Args:
            crossref_data: Raw CrossRef API response

        Returns:
            Extracted metadata dictionary
        """
        metadata = {}

        # Basic metadata
        metadata["doi"] = crossref_data.get("DOI", "")
        metadata["title"] = crossref_data.get("title", [""])[0] if crossref_data.get("title") else ""

        # Authors
        authors = []
        for author in crossref_data.get("author", []):
            author_info = {
                "name": f"{author.get('given', '')} {author.get('family', '')}".strip(),
                "orcid": author.get("ORCID", ""),
            }
            if author_info["name"]:
                authors.append(author_info)
        metadata["authors"] = authors

        # Publication info
        metadata["journal"] = (
            crossref_data.get("container-title", [""])[0] if crossref_data.get("container-title") else ""
        )
        metadata["publisher"] = crossref_data.get("publisher", "")
        metadata["volume"] = crossref_data.get("volume", "")
        metadata["issue"] = crossref_data.get("issue", "")
        metadata["pages"] = crossref_data.get("page", "")

        # Dates
        published_date = crossref_data.get("published-print") or crossref_data.get("published-online")
        if published_date and "date-parts" in published_date:
            date_parts = published_date["date-parts"][0] if published_date["date-parts"] else []
            if date_parts and len(date_parts) > 0:
                metadata["year"] = str(date_parts[0])

        # Metrics
        metadata["citation_count"] = crossref_data.get("is-referenced-by-count", 0)
        metadata["reference_count"] = crossref_data.get("reference-count", 0)

        # Abstract
        if crossref_data.get("abstract"):
            metadata["abstract"] = crossref_data["abstract"]

        # ISSN
        issn_list = crossref_data.get("ISSN", [])
        if issn_list:
            metadata["issn"] = issn_list

        # Subject/keywords
        subjects = crossref_data.get("subject", [])
        if subjects:
            metadata["subjects"] = subjects

        # License
        licenses = crossref_data.get("license", [])
        if licenses:
            metadata["licenses"] = [
                {"url": lic.get("URL", ""), "version": lic.get("content-version", "")} for lic in licenses
            ]

        # Funding
        funders = crossref_data.get("funder", [])
        if funders:
            metadata["funding"] = [{"name": f.get("name", ""), "doi": f.get("DOI", "")} for f in funders]

        return metadata

    def process_directory(self, input_dir: Path, output_dir: Path, max_papers: int | None = None):
        """Process all papers in directory with batch queries.

        Args:
            input_dir: Directory with JSON files
            output_dir: Output directory for enriched files
            max_papers: Maximum papers to process (for testing)
        """
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load all papers
        json_files = list(input_dir.glob("*.json"))
        if max_papers:
            json_files = json_files[:max_papers]

        logger.info(f"Found {len(json_files)} papers to process")
        self.stats["total_papers"] = len(json_files)

        # Group papers by DOI availability
        papers_with_dois = {}
        papers_without_dois = []

        for json_file in json_files:
            with open(json_file, encoding="utf-8") as f:
                paper_data = json.load(f)

            doi = paper_data.get("doi", "").strip().lower()
            if doi:
                # Clean DOI
                doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
                papers_with_dois[doi] = (json_file, paper_data)
                self.stats["papers_with_dois"] += 1
            else:
                papers_without_dois.append((json_file, paper_data))

        logger.info(f"Papers with DOIs: {len(papers_with_dois)}")
        logger.info(f"Papers without DOIs: {len(papers_without_dois)}")

        # Process papers with DOIs in batches
        doi_list = list(papers_with_dois.keys())

        for i in range(0, len(doi_list), self.batch_size):
            batch_dois = doi_list[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(doi_list) + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_dois)} DOIs)...")

            # Fetch batch metadata
            batch_results = self.fetch_batch(batch_dois)
            self.stats["batches_processed"] += 1

            # Process each result
            for doi in batch_dois:
                json_file, paper_data = papers_with_dois[doi]

                if doi in batch_results:
                    # Enrich paper with CrossRef data
                    crossref_metadata = self.extract_metadata(batch_results[doi])

                    # Merge with existing data (don't overwrite existing fields)
                    for key, value in crossref_metadata.items():
                        if value and not paper_data.get(key):
                            paper_data[key] = value

                    # Add enrichment metadata
                    paper_data["crossref_enrichment"] = {
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                        "batch_processed": True,
                    }

                    self.stats["papers_enriched"] += 1
                else:
                    # DOI not found in batch results
                    paper_data["crossref_enrichment"] = {
                        "timestamp": datetime.now().isoformat(),
                        "success": False,
                        "error": "DOI not found in CrossRef",
                        "batch_processed": True,
                    }
                    self.stats["papers_failed"] += 1

                # Save enriched paper
                output_file = output_dir / json_file.name
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(paper_data, f, indent=2)

            # Rate limiting - be polite even with batch processing
            if batch_num < total_batches:
                time.sleep(1)  # 1 second between batches

        # Process papers without DOIs (just copy them)
        logger.info(f"Copying {len(papers_without_dois)} papers without DOIs...")
        for json_file, paper_data in papers_without_dois:
            paper_data["crossref_enrichment"] = {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "No DOI available",
                "batch_processed": False,
            }

            output_file = output_dir / json_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(paper_data, f, indent=2)

        # Generate report
        self.generate_report(output_dir)

    def generate_report(self, output_dir: Path):
        """Generate enrichment report.

        Args:
            output_dir: Output directory
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_papers": self.stats["total_papers"],
                "papers_with_dois": self.stats["papers_with_dois"],
                "papers_enriched": self.stats["papers_enriched"],
                "papers_failed": self.stats["papers_failed"],
                "enrichment_rate": f"{(self.stats['papers_enriched'] / max(1, self.stats['papers_with_dois'])) * 100:.1f}%",
                "api_calls": self.stats["api_calls"],
                "batches_processed": self.stats["batches_processed"],
                "avg_papers_per_call": self.stats["papers_with_dois"] / max(1, self.stats["api_calls"]),
            },
        }

        report_file = output_dir / "crossref_batch_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("CROSSREF BATCH ENRICHMENT COMPLETE")
        print("=" * 60)
        print(f"Total papers: {self.stats['total_papers']}")
        print(f"Papers with DOIs: {self.stats['papers_with_dois']}")
        print(f"Papers enriched: {self.stats['papers_enriched']}")
        print(f"Papers failed: {self.stats['papers_failed']}")
        print(
            f"Enrichment rate: {(self.stats['papers_enriched'] / max(1, self.stats['papers_with_dois'])) * 100:.1f}%"
        )
        print("\nAPI efficiency:")
        print(f"Total API calls: {self.stats['api_calls']}")
        print(f"Batches processed: {self.stats['batches_processed']}")
        print(
            f"Average papers per API call: {self.stats['papers_with_dois'] / max(1, self.stats['api_calls']):.1f}"
        )
        print(f"\nReport: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Batch CrossRef enrichment for faster processing")
    parser.add_argument(
        "--input", default="zotero_recovered_20250901", help="Input directory with JSON files"
    )
    parser.add_argument(
        "--output", default="crossref_batch_20250901", help="Output directory for enriched files"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Number of DOIs per batch (max 100, default 50)"
    )
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process (for testing)")
    parser.add_argument(
        "--mailto", default=CROSSREF_POLITE_EMAIL, help="Email for CrossRef polite pool access"
    )

    args = parser.parse_args()

    # Create enricher
    enricher = BatchCrossRefEnricher(mailto=args.mailto, batch_size=args.batch_size)

    # Process papers
    enricher.process_directory(
        input_dir=Path(args.input), output_dir=Path(args.output), max_papers=args.max_papers
    )


if __name__ == "__main__":
    main()
