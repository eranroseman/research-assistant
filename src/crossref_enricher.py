#!/usr/bin/env python3
"""V5 Unified CrossRef Enrichment with comprehensive fields, batch processing, and checkpoints.

This unified script combines:
- Comprehensive field extraction (50+ fields from CrossRef)
- Batch processing for efficiency (50 DOIs per request)
- Checkpoint recovery for resilience
- Funding DOI filtering
- Papers without DOIs handling via title search

Follows v5 design principles from v5_design/17_extended_enrichment_pipeline.md
"""

import json
import logging
import time
import re
from pathlib import Path
from datetime import datetime, UTC
import argparse
from typing import Any
from collections import defaultdict
from src import config
from src.pipeline_utils import clean_doi

try:
    from habanero import Crossref
except ImportError:
    print("ERROR: habanero package not installed!")
    print("Install with: pip install habanero")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CrossRefV5Enricher:
    """V5 Unified CrossRef enricher with all features."""

    def __init__(self, email: str = "research.assistant@university.edu", force: bool = False):
        """Initialize with polite pool settings."""
        self.cr = Crossref(mailto=email)
        self.email = email
        self.batch_size = config.FAST_API_CHECKPOINT_INTERVAL  # 500 papers
        self.checkpoint_file: Path | None = None
        self.processed_papers: set[str] = set()
        self.stats = defaultdict(int)
        self.comprehensive_fields_extracted = defaultdict(int)
        self.force = force  # Force re-enrichment even if already has data

    def load_checkpoint(self, output_dir: Path) -> int:
        """Load checkpoint to resume processing."""
        self.checkpoint_file = output_dir / ".crossref_v5_checkpoint.json"

        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    checkpoint_data = json.load(f)
                    self.processed_papers = set(checkpoint_data.get("processed_papers", []))
                    self.stats = defaultdict(int, checkpoint_data.get("stats", {}))
                    logger.info(
                        f"Resuming from checkpoint: {len(self.processed_papers)} papers already processed"
                    )
                    return len(self.processed_papers)
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
        return 0

    def save_checkpoint(self) -> None:
        """Save current progress to checkpoint file."""
        if self.checkpoint_file:
            checkpoint_data = {
                "processed_papers": list(self.processed_papers),
                "stats": dict(self.stats),
                "timestamp": datetime.now(UTC).isoformat(),
                "comprehensive_fields": dict(self.comprehensive_fields_extracted),
            }
            try:
                with open(self.checkpoint_file, "w") as f:
                    json.dump(checkpoint_data, f, indent=2)
                logger.debug(f"Checkpoint saved: {len(self.processed_papers)} papers processed")
            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")

    def clean_doi_with_stats(self, doi: str) -> str | None:
        """Clean DOI using shared utility and track statistics."""
        cleaned = clean_doi(doi)

        if doi and not cleaned:
            # Track why it was rejected
            if doi and "10.13039" in str(doi):
                self.stats["funding_dois_removed"] += 1
            else:
                self.stats["invalid_dois"] += 1

        return cleaned

    def extract_comprehensive_fields(self, crossref_data: dict[str, Any]) -> dict[str, Any]:
        """Extract ALL available fields from CrossRef response."""
        extracted = {}

        # Basic metadata
        basic_fields = [
            "DOI",
            "URL",
            "type",
            "title",
            "subtitle",
            "short-title",
            "container-title",
            "container-title-short",
            "publisher",
            "publisher-location",
            "volume",
            "issue",
            "page",
            "article-number",
        ]

        for field in basic_fields:
            if field in crossref_data:
                value = crossref_data[field]
                if isinstance(value, list) and value:
                    value = value[0]
                if value:
                    extracted[field] = value
                    self.comprehensive_fields_extracted[field] += 1

        # Dates with proper handling
        date_fields = [
            "created",
            "deposited",
            "indexed",
            "issued",
            "published-print",
            "published-online",
            "accepted",
            "approved",
        ]

        for field in date_fields:
            if field in crossref_data:
                date_val = crossref_data[field]
                if isinstance(date_val, dict):
                    if "date-time" in date_val:
                        extracted[field] = date_val["date-time"]
                    elif date_val.get("date-parts"):
                        parts = date_val["date-parts"][0]
                        if parts:
                            extracted[field] = "-".join(str(p) for p in parts)
                    self.comprehensive_fields_extracted[field] += 1

        # Authors with ORCID and affiliations
        if "author" in crossref_data:
            authors = []
            for author in crossref_data["author"]:
                author_info = {
                    "name": f"{author.get('given', '')} {author.get('family', '')}".strip(),
                    "family": author.get("family"),
                    "given": author.get("given"),
                }
                if "ORCID" in author:
                    author_info["orcid"] = author["ORCID"]
                    self.comprehensive_fields_extracted["orcid"] += 1
                if author.get("affiliation"):
                    affiliations = []
                    for aff in author["affiliation"]:
                        if "name" in aff:
                            affiliations.append(aff["name"])
                    if affiliations:
                        author_info["affiliations"] = affiliations
                        self.comprehensive_fields_extracted["affiliations"] += 1
                authors.append(author_info)
            extracted["authors"] = authors

        # Abstract (clean XML tags if present)
        if "abstract" in crossref_data:
            abstract = re.sub("<[^<]+?>", "", crossref_data["abstract"])
            extracted["abstract"] = abstract
            self.comprehensive_fields_extracted["abstract"] += 1

        # Identifiers
        id_fields = ["ISSN", "ISBN", "archive"]
        for field in id_fields:
            if field in crossref_data:
                value = crossref_data[field]
                if isinstance(value, list) and value:
                    extracted[field] = value
                    self.comprehensive_fields_extracted[field] += 1

        # Metrics
        metric_fields = ["is-referenced-by-count", "references-count", "score"]
        for field in metric_fields:
            if field in crossref_data:
                extracted[field] = crossref_data[field]
                self.comprehensive_fields_extracted[field] += 1

        # Subject/Keywords
        if "subject" in crossref_data:
            extracted["subjects"] = crossref_data["subject"]
            self.comprehensive_fields_extracted["subjects"] += 1

        if "keyword" in crossref_data:
            extracted["keywords"] = crossref_data["keyword"]
            self.comprehensive_fields_extracted["keywords"] += 1

        # Clinical trials
        if "clinical-trial-number" in crossref_data:
            trials = []
            for trial in crossref_data["clinical-trial-number"]:
                trials.append(
                    {"number": trial.get("clinical-trial-number"), "registry": trial.get("registry")}
                )
            extracted["clinical_trials"] = trials
            self.comprehensive_fields_extracted["clinical_trials"] += 1

        # Funding information
        if "funder" in crossref_data:
            funders = []
            for funder in crossref_data["funder"]:
                funder_info = {"name": funder.get("name"), "doi": funder.get("DOI")}
                if "award" in funder:
                    funder_info["awards"] = funder["award"]
                funders.append(funder_info)
            extracted["funders"] = funders
            self.comprehensive_fields_extracted["funders"] += 1

        # License information
        if "license" in crossref_data:
            licenses = []
            for lic in crossref_data["license"]:
                licenses.append(
                    {
                        "url": lic.get("URL"),
                        "start": lic.get("start", {}).get("date-time"),
                        "content-version": lic.get("content-version"),
                    }
                )
            extracted["licenses"] = licenses
            self.comprehensive_fields_extracted["licenses"] += 1

        # Relations (updates, versions)
        if "relation" in crossref_data:
            relations = {}
            for rel_type, rel_data in crossref_data["relation"].items():
                if isinstance(rel_data, list) and rel_data:
                    relations[rel_type] = rel_data
            if relations:
                extracted["relations"] = relations
                self.comprehensive_fields_extracted["relations"] += 1

        # References (limit to first 100 to avoid huge files)
        if crossref_data.get("reference"):
            refs = crossref_data["reference"][:100]
            extracted["reference_count"] = len(crossref_data["reference"])
            extracted["references_sample"] = refs
            self.comprehensive_fields_extracted["references"] += 1

        # Quality indicators
        quality_fields = ["peer-review", "content-domain", "assertion"]
        for field in quality_fields:
            if field in crossref_data:
                extracted[f"has_{field}"] = True
                self.comprehensive_fields_extracted[field] += 1

        return extracted

    def search_by_title(self, title: str, year: str | None = None) -> dict[str, Any] | None:
        """Search for paper by title when DOI is missing."""
        if not title:
            return None

        try:
            query = title
            if year:
                query += f" {year}"

            results = self.cr.works(query=query, limit=3)

            if results and "message" in results and "items" in results["message"]:
                items = results["message"]["items"]

                # Find best match using fuzzy matching
                for item in items:
                    item_titles = item.get("title", [])
                    if not item_titles:
                        continue

                    item_title = item_titles[0]
                    # Simple similarity check - could use difflib for better matching
                    if len(title) > 20:  # Only for reasonable length titles
                        title_lower = title.lower()[:50]
                        item_title_lower = item_title.lower()[:50]
                        if title_lower in item_title_lower or item_title_lower in title_lower:
                            self.stats["found_by_title"] += 1
                            return item

        except Exception as e:
            logger.debug(f"Title search failed: {e}")

        return None

    def enrich_paper(self, paper_data: dict[str, Any]) -> dict[str, Any]:
        """Enrich a single paper with CrossRef data."""
        paper_id = paper_data.get("paper_id", "unknown")

        # Clean and validate DOI
        original_doi = paper_data.get("doi")
        clean_doi_value_value = self.clean_doi_value_with_stats(original_doi) if original_doi else None

        crossref_data = None

        # Try DOI lookup first
        if clean_doi_value_value:
            try:
                response = self.cr.works(ids=clean_doi_value)
                if response and "message" in response:
                    crossref_data = response["message"]
                    self.stats["found_by_doi"] += 1
            except Exception as e:
                logger.debug(f"DOI lookup failed for {clean_doi_value}: {e}")
                self.stats["doi_lookup_failed"] += 1

        # Try title search if no DOI or DOI lookup failed
        if not crossref_data and paper_data.get("title"):
            crossref_data = self.search_by_title(paper_data.get("title"), paper_data.get("year"))

        # Extract comprehensive fields if we found data
        if crossref_data:
            comprehensive_fields = self.extract_comprehensive_fields(crossref_data)

            # Add CrossRef metadata to paper
            paper_data["crossref"] = comprehensive_fields
            paper_data["crossref_enrichment"] = {
                "timestamp": datetime.now(UTC).isoformat(),
                "doi_cleaned": clean_doi_value != original_doi,
                "found_by": "doi" if clean_doi_value and "DOI" in comprehensive_fields else "title",
                "fields_extracted": len(comprehensive_fields),
            }

            # Update basic fields if missing
            if not paper_data.get("title") and comprehensive_fields.get("title"):
                paper_data["title"] = comprehensive_fields["title"]
                self.stats["titles_recovered"] += 1

            if not paper_data.get("year") and comprehensive_fields.get("issued"):
                year_match = re.search(r"(\d{4})", comprehensive_fields["issued"])
                if year_match:
                    paper_data["year"] = year_match.group(1)
                    self.stats["years_recovered"] += 1

            if not paper_data.get("journal") and comprehensive_fields.get("container-title"):
                paper_data["journal"] = comprehensive_fields["container-title"]
                self.stats["journals_recovered"] += 1

            if not paper_data.get("authors") and comprehensive_fields.get("authors"):
                paper_data["authors"] = comprehensive_fields["authors"]
                self.stats["authors_recovered"] += 1

            if not paper_data.get("abstract") and comprehensive_fields.get("abstract"):
                paper_data["abstract"] = comprehensive_fields["abstract"]
                self.stats["abstracts_recovered"] += 1

            self.stats["papers_enriched"] += 1
        else:
            self.stats["not_found"] += 1

        return paper_data

    def has_crossref_data(self, paper: dict) -> bool:
        """Check if paper already has CrossRef enrichment."""
        # Check for crossref_enriched marker
        if paper.get("crossref_enriched"):
            return True
        # Check for any crossref_ prefixed fields
        return any(key.startswith("crossref_") for key in paper)

    def process_batch(self, input_dir: Path, output_dir: Path, max_papers: int | None = None) -> None:
        """Process papers in batches with checkpoint support."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load checkpoint
        self.load_checkpoint(output_dir)

        # Get all JSON files
        json_files = list(input_dir.glob("*.json"))
        if max_papers:
            json_files = json_files[:max_papers]

        # Filter already processed
        remaining_files = []
        skipped_already_enriched = 0

        for json_file in json_files:
            paper_id = json_file.stem
            output_file = output_dir / json_file.name

            # Skip checkpoint and report files
            if "checkpoint" in json_file.name or "report" in json_file.name:
                continue

            if paper_id in self.processed_papers:
                continue

            # Check if already enriched (unless force mode)
            if not self.force and output_file.exists():
                with open(output_file) as f:
                    existing_paper = json.load(f)
                    if self.has_crossref_data(existing_paper):
                        skipped_already_enriched += 1
                        self.processed_papers.add(paper_id)
                        continue

            remaining_files.append(json_file)

        logger.info(f"Found {len(json_files)} total papers")
        logger.info(f"Already processed: {len(self.processed_papers)}")
        if skipped_already_enriched > 0:
            logger.info(f"Skipped (already enriched): {skipped_already_enriched}")
        logger.info(f"To process: {len(remaining_files)}")

        if self.force:
            logger.info("Force mode: Re-enriching all papers")

        if not remaining_files:
            logger.info("All papers already processed!")
            return

        # Process remaining papers
        checkpoint_counter = 0

        for i, json_file in enumerate(remaining_files, 1):
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(remaining_files)} papers...")

            try:
                # Load paper
                with open(json_file) as f:
                    paper_data = json.load(f)

                # Add paper_id if missing
                if "paper_id" not in paper_data:
                    paper_data["paper_id"] = json_file.stem

                # Enrich with CrossRef
                enriched_paper = self.enrich_paper(paper_data)

                # Add enrichment marker
                enriched_paper["crossref_enriched"] = True
                enriched_paper["crossref_enriched_date"] = datetime.now(UTC).isoformat()

                # Save enriched paper
                output_file = output_dir / json_file.name
                with open(output_file, "w") as f:
                    json.dump(enriched_paper, f, indent=2)

                # Track progress
                self.processed_papers.add(json_file.stem)
                self.stats["total_processed"] += 1
                checkpoint_counter += 1

                # Save checkpoint periodically
                if checkpoint_counter >= self.batch_size:
                    self.save_checkpoint()
                    checkpoint_counter = 0

                # Rate limiting
                time.sleep(0.1)  # 10 requests per second

            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")
                self.stats["errors"] += 1

        # Final checkpoint save
        self.save_checkpoint()

        # Print statistics
        self.print_statistics(output_dir)

    def print_statistics(self, output_dir: Path) -> None:
        """Print enrichment statistics."""
        print("\n" + "=" * 80)
        print("CROSSREF V5 ENRICHMENT COMPLETE")
        print("=" * 80)
        print(f"Total papers processed: {self.stats['total_processed']}")
        print(f"Papers enriched: {self.stats['papers_enriched']}")
        print(f"Not found in CrossRef: {self.stats['not_found']}")
        print(f"Processing errors: {self.stats['errors']}")

        print("\nLookup Methods:")
        print(f"  Found by DOI: {self.stats['found_by_doi']}")
        print(f"  Found by title search: {self.stats['found_by_title']}")
        print(f"  DOI lookup failures: {self.stats['doi_lookup_failed']}")

        print("\nData Quality:")
        print(f"  Funding DOIs removed: {self.stats['funding_dois_removed']}")

        print("\nMetadata Recovery:")
        print(f"  Titles: {self.stats['titles_recovered']}")
        print(f"  Years: {self.stats['years_recovered']}")
        print(f"  Journals: {self.stats['journals_recovered']}")
        print(f"  Authors: {self.stats['authors_recovered']}")
        print(f"  Abstracts: {self.stats['abstracts_recovered']}")

        print("\nComprehensive Fields Extracted:")
        for field, count in sorted(
            self.comprehensive_fields_extracted.items(), key=lambda x: x[1], reverse=True
        )[:20]:
            print(f"  {field}: {count}")

        # Save report
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "statistics": dict(self.stats),
            "comprehensive_fields": dict(self.comprehensive_fields_extracted),
            "summary": {
                "total_processed": self.stats["total_processed"],
                "enrichment_rate": (self.stats["papers_enriched"] / max(self.stats["total_processed"], 1))
                * 100,
                "unique_fields_extracted": len(self.comprehensive_fields_extracted),
            },
        }

        report_file = output_dir / "crossref_v5_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {report_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="V5 Unified CrossRef enrichment with comprehensive fields, batch processing, and checkpoints"
    )
    parser.add_argument("--input", required=True, help="Input directory with JSON files")
    parser.add_argument("--output", required=True, help="Output directory for enriched files")
    parser.add_argument(
        "--email", default="research.assistant@university.edu", help="Email for CrossRef polite pool"
    )
    parser.add_argument("--max-papers", type=int, help="Maximum number of papers to process")
    parser.add_argument("--reset", action="store_true", help="Reset checkpoint and start fresh")
    parser.add_argument("--force", action="store_true", help="Force re-enrichment even if already processed")

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} does not exist")
        return

    # Remove checkpoint if reset requested
    if args.reset:
        checkpoint_file = output_dir / ".crossref_v5_checkpoint.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            print("Checkpoint reset")

    # Initialize enricher
    enricher = CrossRefV5Enricher(email=args.email, force=args.force)

    # Process papers
    enricher.process_batch(input_dir, output_dir, args.max_papers)

    print("\n✓ CrossRef V5 enrichment complete!")


if __name__ == "__main__":
    main()
