#!/usr/bin/env python3
"""Semantic Scholar (S2) batch enrichment for v5 pipeline.

Enriches papers with citation counts, author h-index, and additional metadata.
Uses batch API for efficient processing (up to 500 papers per call).
"""

import json
import logging
import time
import requests
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
import argparse
import sys
import os

# Add src directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from config import MIN_ABSTRACT_LENGTH, HTTP_TOO_MANY_REQUESTS, HTTP_OK
except ImportError:
    # Fallback values if config not found
    MIN_ABSTRACT_LENGTH = 50
    HTTP_TOO_MANY_REQUESTS = 429
    HTTP_OK = 200

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class S2BatchEnricher:
    """Semantic Scholar batch enricher for paper metadata.

    .
    """

    def __init__(self, batch_size: int = 500, force: bool = False) -> None:
        """Initialize enricher.

        Args:
            batch_size: Number of papers per batch (max 500 for S2)
            force: Force re-enrichment even if already processed
        """
        self.batch_size = min(batch_size, 500)  # S2 max is 500
        self.force = force
        self.base_url = "https://api.semanticscholar.org/graph/v1"

        logger.info("Using Semantic Scholar API")
        logger.info("Batch size: %d papers per request", self.batch_size)

        self.stats = {
            "total_papers": 0,
            "papers_with_dois": 0,
            "papers_enriched": 0,
            "papers_failed": 0,
            "api_calls": 0,
            "batches_processed": 0,
            "new_fields_added": 0,
        }

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ResearchAssistant/5.0"})

        # Rate limiter - only apply AFTER getting 429 errors, not preemptively
        self.last_request_time: float = 0
        self.min_interval: float = 0  # Don't rate limit preemptively

    def rate_limit(self) -> None:
        """Enforce rate limiting.

        .
        """
        now = time.time()
        time_since_last = now - self.last_request_time

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            time.sleep(wait_time)

        self.last_request_time = time.time()

    def fetch_batch(
        self, paper_ids: list[str], id_type: str = "doi", max_retries: int = 5
    ) -> dict[str, dict[str, Any]]:
        """Fetch metadata for a batch of papers with retry logic.

        Args:
            paper_ids: List of paper identifiers
            id_type: Type of identifier ("doi" or "S2")
            max_retries: Maximum number of retries

        Returns:
            Dictionary mapping paper ID to metadata
        """
        if not paper_ids:
            return {}

        # Format IDs based on type
        formatted_ids = [f"DOI:{pid}" for pid in paper_ids] if id_type == "doi" else paper_ids

        # Request ALL available S2 fields for comprehensive enrichment
        # Note: removed unsupported fields like authors.aliases
        fields = "paperId,externalIds,url,title,abstract,venue,publicationVenue,year,publicationDate,journal,referenceCount,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,citationStyles,authors,authors.authorId,authors.name,authors.url,authors.affiliations,authors.homepage,authors.paperCount,authors.citationCount,authors.hIndex,tldr,citations,references"

        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            # NO preemptive rate limiting - only apply after 429 errors

            try:
                # Use batch endpoint
                response = self.session.post(
                    f"{self.base_url}/paper/batch",
                    params={"fields": fields},
                    json={"ids": formatted_ids},
                    timeout=60,  # Longer timeout for batch requests
                )
                self.stats["api_calls"] += 1

                if response.status_code == HTTP_OK:
                    data = response.json()
                    results = {}

                    # Map results back to original IDs
                    for i, original_id in enumerate(paper_ids):
                        if i < len(data) and data[i]:
                            results[original_id] = data[i]

                    return results
                if response.status_code == HTTP_TOO_MANY_REQUESTS:
                    # Rate limited - exponential backoff
                    wait_time = min(2**attempt, 32)  # Max 32 seconds
                    logger.warning("Rate limited (429). Waiting %d seconds...", wait_time)
                    time.sleep(wait_time)
                    # Set minimum interval for future requests after getting 429
                    self.min_interval = 1.0
                    continue
                logger.warning("API returned status %d", response.status_code)
                return {}

            except Exception as e:
                logger.error("Batch query failed: %s", e)
                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 32)
                    logger.info("Retrying in %d seconds...", wait_time)
                    time.sleep(wait_time)
                    continue
                return {}

        logger.error("Failed after %d attempts", max_retries)
        return {}

    def extract_metadata(self, s2_data: dict[str, Any]) -> dict[str, Any]:
        """Extract comprehensive metadata from S2 response.

        Args:
            s2_data: Raw S2 API response

        Returns:
            Extracted metadata dictionary
        """
        metadata = {}

        # Paper IDs
        metadata["s2_paper_id"] = s2_data.get("paperId", "")

        # External IDs (DOI, PubMed, etc.)
        external_ids = s2_data.get("externalIds", {})
        if external_ids:
            if external_ids.get("DOI"):
                metadata["doi"] = external_ids["DOI"]
            if "PubMed" in external_ids:
                metadata["pubmed_id"] = external_ids["PubMed"]
            if "ArXiv" in external_ids:
                metadata["arxiv_id"] = external_ids["ArXiv"]

        # Basic metadata
        if s2_data.get("title"):
            metadata["title"] = s2_data["title"]

        if s2_data.get("abstract"):
            metadata["abstract"] = s2_data["abstract"]

        if s2_data.get("year"):
            metadata["year"] = str(s2_data["year"])

        if s2_data.get("publicationDate"):
            metadata["publication_date"] = s2_data["publicationDate"]

        # Venue and journal
        if s2_data.get("venue"):
            metadata["venue"] = s2_data["venue"]

        if s2_data.get("journal"):
            journal_info = s2_data["journal"]
            if journal_info.get("name"):
                metadata["journal"] = journal_info["name"]
            if journal_info.get("volume"):
                metadata["volume"] = journal_info["volume"]
            if journal_info.get("pages"):
                metadata["pages"] = journal_info["pages"]

        # Publication venue details (impact factor, etc.)
        pub_venue = s2_data.get("publicationVenue", {})
        if pub_venue:
            metadata["venue_id"] = pub_venue.get("id", "")
            metadata["venue_type"] = pub_venue.get("type", "")
            metadata["venue_alternate_names"] = pub_venue.get("alternate_names", [])
            metadata["venue_issn"] = pub_venue.get("issn", "")

        # Metrics
        metadata["citation_count"] = s2_data.get("citationCount", 0)
        metadata["reference_count"] = s2_data.get("referenceCount", 0)
        metadata["influential_citation_count"] = s2_data.get("influentialCitationCount", 0)

        # Open access
        metadata["is_open_access"] = s2_data.get("isOpenAccess", False)
        open_access_pdf = s2_data.get("openAccessPdf")
        if open_access_pdf:
            metadata["open_access_pdf_url"] = open_access_pdf.get("url", "")

        # Fields of study
        fields_of_study = s2_data.get("fieldsOfStudy", [])
        if fields_of_study:
            metadata["fields_of_study"] = fields_of_study

        s2_fields = s2_data.get("s2FieldsOfStudy", [])
        if s2_fields:
            metadata["s2_fields_of_study"] = [
                {"category": f.get("category", ""), "source": f.get("source", "")} for f in s2_fields
            ]

        # Publication types
        pub_types = s2_data.get("publicationTypes", [])
        if pub_types:
            metadata["publication_types"] = pub_types

        # Authors with enhanced metadata
        authors = []
        for author in s2_data.get("authors", []):
            author_info = {
                "name": author.get("name", ""),
                "author_id": author.get("authorId", ""),
                "h_index": author.get("hIndex", 0),
                "citation_count": author.get("citationCount", 0),
                "paper_count": author.get("paperCount", 0),
            }
            if author_info["name"]:
                authors.append(author_info)

        if authors:
            metadata["authors"] = authors
            # Calculate max h-index for quality scoring
            h_indices = [a["h_index"] for a in authors if a["h_index"]]
            if h_indices:
                metadata["max_author_h_index"] = max(h_indices)

        # TLDR (automatic summary)
        tldr = s2_data.get("tldr")
        if tldr:
            metadata["tldr"] = tldr.get("text", "")
            metadata["tldr_model"] = tldr.get("model", "")

        # Citation and reference titles (for context)
        citations = s2_data.get("citations", [])
        if citations:
            metadata["citation_titles"] = [c.get("title", "") for c in citations[:10]]  # Top 10

        references = s2_data.get("references", [])
        if references:
            metadata["reference_titles"] = [r.get("title", "") for r in references[:10]]  # Top 10

        return metadata

    def has_s2_data(self, paper: dict) -> bool:
        """Check if paper already has S2 enrichment."""
        # Check for s2_enriched marker
        if paper.get("s2_enriched"):
            return True
        # Check for any s2_ prefixed fields
        return any(key.startswith("s2_") for key in paper)

    def process_directory(self, input_dir: Path, output_dir: Path, max_papers: int | None = None) -> None:
        """Process all papers in directory with batch queries and checkpoint recovery.

        Args:
            input_dir: Directory with JSON files
            output_dir: Output directory for enriched files
            max_papers: Maximum papers to process (for testing)
        """
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check for checkpoint file
        checkpoint_file = output_dir / ".s2_checkpoint.json"
        processed_papers = set()

        if checkpoint_file.exists():
            with open(checkpoint_file) as f:
                checkpoint_data = json.load(f)
                processed_papers = set(checkpoint_data.get("processed_papers", []))
                logger.info("Resuming from checkpoint: %d papers already processed", len(processed_papers))

        # Load all papers
        json_files = list(input_dir.glob("*.json"))
        if max_papers:
            json_files = json_files[:max_papers]

        logger.info("Found %d papers to process", len(json_files))
        self.stats["total_papers"] = len(json_files)

        # Group papers by DOI availability, skipping already processed ones
        papers_with_dois = {}
        papers_without_dois = []
        skipped_count = 0
        skipped_already_enriched = 0

        for json_file in json_files:
            # Skip checkpoint and report files
            if "checkpoint" in json_file.name or "report" in json_file.name:
                continue

            # Skip if already processed
            if json_file.stem in processed_papers:
                skipped_count += 1
                continue

            with open(json_file, encoding="utf-8") as f:
                paper_data = json.load(f)

            # Skip if already enriched (unless force mode)
            if not self.force and self.has_s2_data(paper_data):
                skipped_already_enriched += 1
                processed_papers.add(json_file.stem)
                continue

            doi = paper_data.get("doi", "").strip()
            if doi:
                # Clean DOI
                doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
                papers_with_dois[doi] = (json_file, paper_data)
                self.stats["papers_with_dois"] += 1
            else:
                papers_without_dois.append((json_file, paper_data))

        if skipped_count > 0:
            logger.info("Skipped %d already processed papers", skipped_count)
        if skipped_already_enriched > 0:
            logger.info("Skipped %d already enriched papers", skipped_already_enriched)
        if self.force:
            logger.info("Force mode: Re-enriching all papers")

        logger.info("Papers with DOIs to process: %d", len(papers_with_dois))
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
            batch_results = self.fetch_batch(batch_dois, id_type="doi")
            self.stats["batches_processed"] += 1

            # Process each result
            for doi in batch_dois:
                json_file, paper_data = papers_with_dois[doi]

                if doi in batch_results:
                    # Extract S2 metadata
                    s2_metadata = self.extract_metadata(batch_results[doi])

                    # Count new fields added
                    new_fields = 0
                    for key, value in s2_metadata.items():
                        if value and not paper_data.get(key):
                            paper_data[key] = value
                            new_fields += 1

                    # Always update citation metrics (they change over time)
                    if "citation_count" in s2_metadata:
                        paper_data["s2_citation_count"] = s2_metadata["citation_count"]
                    if "influential_citation_count" in s2_metadata:
                        paper_data["s2_influential_citations"] = s2_metadata["influential_citation_count"]

                    # Add enrichment metadata
                    paper_data["s2_enriched"] = True
                    paper_data["s2_enriched_date"] = datetime.now(UTC).isoformat()
                    paper_data["s2_enrichment"] = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "success": True,
                        "new_fields_added": new_fields,
                        "s2_paper_id": s2_metadata.get("s2_paper_id", ""),
                    }

                    self.stats["papers_enriched"] += 1
                    self.stats["new_fields_added"] += new_fields
                else:
                    # DOI not found in S2
                    paper_data["s2_enrichment"] = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "success": False,
                        "error": "Paper not found in Semantic Scholar",
                    }
                    self.stats["papers_failed"] += 1

                # Save enriched paper
                output_file = output_dir / json_file.name
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(paper_data, f, indent=2)

                # Track processed paper
                processed_papers.add(json_file.stem)
                checkpoint_counter += 1

            # Save checkpoint every 50 papers
            if checkpoint_counter >= MIN_ABSTRACT_LENGTH:
                with open(checkpoint_file, "w") as f:
                    json.dump({"processed_papers": list(processed_papers)}, f)
                logger.info("Checkpoint saved: %d papers processed", len(processed_papers))
                checkpoint_counter = 0

        # Process papers without DOIs (just copy them)
        if papers_without_dois:
            logger.info("Copying %d papers without DOIs...", len(papers_without_dois))
            for json_file, paper_data in papers_without_dois:
                paper_data["s2_enrichment"] = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "success": False,
                    "error": "No DOI available for S2 lookup",
                }

                output_file = output_dir / json_file.name
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(paper_data, f, indent=2)

                processed_papers.add(json_file.stem)

        # Final checkpoint save
        with open(checkpoint_file, "w") as f:
            json.dump({"processed_papers": list(processed_papers)}, f)

        # Generate report
        self.generate_report(output_dir)

    def generate_report(self, output_dir: Path) -> None:
        """Generate enrichment report.

        Args:
            output_dir: Output directory
        """
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "statistics": {
                "total_papers": self.stats["total_papers"],
                "papers_with_dois": self.stats["papers_with_dois"],
                "papers_enriched": self.stats["papers_enriched"],
                "papers_failed": self.stats["papers_failed"],
                "enrichment_rate": f"{(self.stats['papers_enriched'] / max(1, self.stats['papers_with_dois'])) * 100:.1f}%",
                "api_calls": self.stats["api_calls"],
                "batches_processed": self.stats["batches_processed"],
                "avg_papers_per_call": self.stats["papers_with_dois"] / max(1, self.stats["api_calls"]),
                "new_fields_added": self.stats["new_fields_added"],
                "avg_new_fields_per_paper": self.stats["new_fields_added"]
                / max(1, self.stats["papers_enriched"]),
            },
        }

        report_file = output_dir / "s2_batch_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("SEMANTIC SCHOLAR BATCH ENRICHMENT COMPLETE")
        print("=" * 60)
        print(f"Total papers: {self.stats['total_papers']}")
        print(f"Papers with DOIs: {self.stats['papers_with_dois']}")
        print(f"Papers enriched: {self.stats['papers_enriched']}")
        print(f"Papers failed: {self.stats['papers_failed']}")
        print(
            f"Enrichment rate: {(self.stats['papers_enriched'] / max(1, self.stats['papers_with_dois'])) * 100:.1f}%"
        )
        print("\nMetadata improvements:")
        print(f"Total new fields added: {self.stats['new_fields_added']}")
        print(
            f"Average new fields per paper: {self.stats['new_fields_added'] / max(1, self.stats['papers_enriched']):.1f}"
        )
        print("\nAPI efficiency:")
        print(f"Total API calls: {self.stats['api_calls']}")
        print(f"Batches processed: {self.stats['batches_processed']}")
        print(
            f"Average papers per API call: {self.stats['papers_with_dois'] / max(1, self.stats['api_calls']):.1f}"
        )
        print(f"\nReport: {report_file}")


def main() -> None:
    """Run the main program.

    .
    """
    parser = argparse.ArgumentParser(description="Semantic Scholar batch enrichment for v5 pipeline")
    parser.add_argument("--input", default="crossref_batch_20250901", help="Input directory with JSON files")
    parser.add_argument(
        "--output", default="s2_enriched_20250901", help="Output directory for enriched files"
    )
    parser.add_argument("--batch-size", type=int, default=500, help="Number of papers per batch (max 500)")
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process (for testing)")
    parser.add_argument("--force", action="store_true", help="Force re-enrichment even if already processed")

    args = parser.parse_args()

    # Create enricher
    enricher = S2BatchEnricher(batch_size=args.batch_size, force=args.force)

    # Process papers
    enricher.process_directory(
        input_dir=Path(args.input), output_dir=Path(args.output), max_papers=args.max_papers
    )


if __name__ == "__main__":
    main()
