#!/usr/bin/env python3
"""CrossRef batch enrichment with checkpoint recovery for pipeline resilience.

This enhanced version adds checkpoint recovery to resume processing after interruptions.
"""

from src import config
import json
import time
from pathlib import Path
from datetime import datetime, UTC
import logging
from habanero import Crossref
from collections import defaultdict
from typing import Any
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BatchCrossRefEnricher:
    """Batch process papers through CrossRef API with checkpoint support."""

    def __init__(self, mailto: str = config.CROSSREF_POLITE_EMAIL, batch_size: int = 50) -> None:
        """Initialize CrossRef client with batch capabilities."""
        self.cr = Crossref(mailto=mailto)
        self.batch_size = min(batch_size, 100)  # CrossRef max is 100
        self.stats: dict[str, int] = defaultdict(int)
        self.checkpoint_file: Path | None = None
        self.processed_files: set[str] = set()

    def load_checkpoint(self, output_dir: Path) -> set[str]:
        """Load checkpoint to resume processing."""
        self.checkpoint_file = output_dir / ".crossref_checkpoint.json"

        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, encoding="utf-8") as f:
                    checkpoint_data = json.load(f)
                    self.processed_files = set(checkpoint_data.get("processed_files", []))
                    self.stats = defaultdict(int, checkpoint_data.get("stats", {}))
                    logger.info(
                        "Resuming from checkpoint: %d files already processed", len(self.processed_files)
                    )
                    return self.processed_files
            except Exception as e:
                logger.warning("Could not load checkpoint: %s", e)

        return set()

    def save_checkpoint(self) -> None:
        """Save checkpoint after processing files."""
        if self.checkpoint_file:
            checkpoint_data = {
                "processed_files": list(self.processed_files),
                "stats": dict(self.stats),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2)

    def fetch_batch(self, dois: list[str]) -> dict[str, Any]:
        """Fetch metadata for a batch of DOIs."""
        try:
            # CrossRef batch query
            response = self.cr.works(ids=dois)
            self.stats["api_calls"] += 1

            # Process response
            results = {}
            if isinstance(response, list):
                for item in response:
                    if item and "message" in item:
                        msg = item["message"]
                        doi = msg.get("DOI", "").lower()
                        if doi:
                            results[doi] = msg
                            self.stats["successful_lookups"] += 1

            return results

        except Exception as e:
            logger.error("Batch API error: %s", e)
            self.stats["api_errors"] += 1
            return {}

    def enrich_paper(self, paper_data: dict[str, Any], crossref_data: dict[str, Any]) -> dict[str, Any]:
        """Enrich paper with CrossRef metadata."""
        enriched = paper_data.copy()

        # Add CrossRef metadata
        enriched["crossref_enrichment"] = {
            "status": "enriched",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Title (if missing)
        if not enriched.get("title") and crossref_data.get("title"):
            enriched["title"] = (
                crossref_data["title"][0]
                if isinstance(crossref_data["title"], list)
                else crossref_data["title"]
            )
            self.stats["titles_recovered"] += 1

        # Authors (if missing or incomplete)
        if not enriched.get("authors") and crossref_data.get("author"):
            authors = []
            for author in crossref_data.get("author", []):
                name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                if name:
                    authors.append({"name": name})
            if authors:
                enriched["authors"] = authors
                self.stats["authors_recovered"] += 1

        # Year (if missing)
        if not enriched.get("year") and crossref_data.get("published-print"):
            date_parts = crossref_data["published-print"].get("date-parts", [[]])
            if date_parts and date_parts[0]:
                enriched["year"] = date_parts[0][0]
                self.stats["years_recovered"] += 1

        # Journal/Publisher
        if not enriched.get("journal"):
            journal = crossref_data.get("container-title")
            if journal:
                enriched["journal"] = journal[0] if isinstance(journal, list) else journal
                self.stats["journals_recovered"] += 1

        # Additional metadata
        if crossref_data.get("publisher"):
            enriched["publisher"] = crossref_data["publisher"]

        if crossref_data.get("ISSN"):
            enriched["issn"] = crossref_data["ISSN"]

        if crossref_data.get("volume"):
            enriched["volume"] = crossref_data["volume"]

        if crossref_data.get("issue"):
            enriched["issue"] = crossref_data["issue"]

        if crossref_data.get("page"):
            enriched["pages"] = crossref_data["page"]

        # Citations (reference count)
        if crossref_data.get("reference-count"):
            enriched["reference_count"] = crossref_data["reference-count"]

        # Cited by (may not always be available)
        if crossref_data.get("is-referenced-by-count"):
            enriched["cited_by_count"] = crossref_data["is-referenced-by-count"]

        # License info
        if crossref_data.get("license"):
            licenses = []
            for lic in crossref_data["license"]:
                if lic.get("URL"):
                    licenses.append(lic["URL"])
            if licenses:
                enriched["licenses"] = licenses

        # Funding info
        if crossref_data.get("funder"):
            funders = []
            for funder in crossref_data["funder"]:
                if funder.get("name"):
                    funders.append(funder["name"])
            if funders:
                enriched["funders"] = funders

        self.stats["papers_enriched"] += 1
        return enriched

    def process_directory(self, input_dir: Path, output_dir: Path, max_papers: int | None = None) -> None:
        """Process all papers in directory with batch queries and checkpoint support."""
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load checkpoint
        self.load_checkpoint(output_dir)

        # Load all papers
        all_json_files = list(input_dir.glob("*.json"))

        # Filter out already processed files
        json_files = []
        papers_to_skip = []

        for json_file in all_json_files:
            output_file = output_dir / json_file.name
            if json_file.stem in self.processed_files or output_file.exists():
                if json_file.stem not in self.processed_files:
                    self.processed_files.add(json_file.stem)
                papers_to_skip.append(json_file)
            else:
                json_files.append(json_file)

        if max_papers and len(json_files) > max_papers:
            json_files = json_files[:max_papers]

        logger.info("Found %d total papers", len(all_json_files))
        logger.info("Already processed: %d", len(papers_to_skip))
        logger.info("To process: %d", len(json_files))

        if not json_files:
            logger.info("All files already processed!")
            self.generate_report(output_dir)
            return

        self.stats["total_papers"] = len(all_json_files)

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

        logger.info("Papers with DOIs: %d", len(papers_with_dois))
        logger.info("Papers without DOIs: %d", len(papers_without_dois))

        # Process papers with DOIs in batches
        doi_list = list(papers_with_dois.keys())
        checkpoint_counter = 0

        for i in range(0, len(doi_list), self.batch_size):
            batch_dois = doi_list[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(doi_list) + self.batch_size - 1) // self.batch_size

            logger.info("Processing batch %d/%d (%d DOIs)...", batch_num, total_batches, len(batch_dois))

            # Fetch batch metadata
            batch_results = self.fetch_batch(batch_dois)

            # Process each paper in batch
            for doi in batch_dois:
                json_file, paper_data = papers_with_dois[doi]

                if doi in batch_results:
                    # Enrich with CrossRef data
                    enriched_data = self.enrich_paper(paper_data, batch_results[doi])
                else:
                    # No CrossRef data found
                    enriched_data = paper_data.copy()
                    enriched_data["crossref_enrichment"] = {
                        "status": "not_found",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    self.stats["not_found"] += 1

                # Save enriched paper
                output_file = output_dir / json_file.name
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(enriched_data, f, indent=2)

                # Track processed file
                self.processed_files.add(json_file.stem)
                checkpoint_counter += 1

            # Save checkpoint every 100 files
            if checkpoint_counter >= config.MIN_CONTENT_LENGTH:
                self.save_checkpoint()
                logger.info("Checkpoint saved: %d files processed", len(self.processed_files))
                checkpoint_counter = 0

            # Rate limiting
            time.sleep(0.1)  # Be nice to CrossRef API

        # Process papers without DOIs (just copy them)
        logger.info("Processing %d papers without DOIs...", len(papers_without_dois))
        for json_file, paper_data in papers_without_dois:
            enriched_data = paper_data.copy()
            enriched_data["crossref_enrichment"] = {
                "status": "no_doi",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            output_file = output_dir / json_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(enriched_data, f, indent=2)

            self.processed_files.add(json_file.stem)
            self.stats["no_doi"] += 1

        # Final checkpoint save
        self.save_checkpoint()

        # Generate report
        self.generate_report(output_dir)

    def generate_report(self, output_dir: Path) -> None:
        """Generate enrichment report."""
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "statistics": dict(self.stats),
            "batch_size": self.batch_size,
        }

        report_file = output_dir / "crossref_enrichment_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 70)
        print("CROSSREF BATCH ENRICHMENT COMPLETE")
        print("=" * 70)
        print(f"Total papers: {self.stats['total_papers']}")
        print(f"Papers enriched: {self.stats['papers_enriched']}")
        print(f"Papers without DOI: {self.stats['no_doi']}")
        print(f"Not found in CrossRef: {self.stats['not_found']}")
        print("\nRecovered metadata:")
        print(f"  Titles: {self.stats['titles_recovered']}")
        print(f"  Authors: {self.stats['authors_recovered']}")
        print(f"  Years: {self.stats['years_recovered']}")
        print(f"  Journals: {self.stats['journals_recovered']}")
        print("\nAPI Performance:")
        print(f"  Total API calls: {self.stats['api_calls']}")
        print(f"  API errors: {self.stats['api_errors']}")
        print(
            f"  Average papers per API call: {self.stats['papers_with_dois'] / max(1, self.stats['api_calls']):.1f}"
        )
        print(f"\nReport: {report_file}")


def main() -> None:
    """Run the main program."""
    parser = argparse.ArgumentParser(description="Batch CrossRef enrichment with checkpoint recovery")
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
        "--mailto", default=config.CROSSREF_POLITE_EMAIL, help="Email for CrossRef polite pool access"
    )
    parser.add_argument("--reset", action="store_true", help="Reset checkpoint and start fresh")

    args = parser.parse_args()

    # Create enricher
    enricher = BatchCrossRefEnricher(mailto=args.mailto, batch_size=args.batch_size)

    # Reset checkpoint if requested
    if args.reset:
        checkpoint_file = Path(args.output) / ".crossref_checkpoint.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info("Checkpoint reset")

    # Process papers
    enricher.process_directory(
        input_dir=Path(args.input), output_dir=Path(args.output), max_papers=args.max_papers
    )


if __name__ == "__main__":
    main()
