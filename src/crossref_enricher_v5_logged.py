#!/usr/bin/env python3
"""V5 CrossRef Enrichment with new logging and display system.

Integrates the PipelineLogger and dashboard display for clean output
while maintaining comprehensive field extraction and checkpoint recovery.
"""

import json
import time
from pathlib import Path
from datetime import datetime, UTC
import argparse
from typing import Any
from collections import defaultdict

from src import config
from src.pipeline_utils import (
    clean_doi,
    load_checkpoint,
    save_checkpoint_atomic,
    batch_iterator,
    rate_limit_wait,
)
from src.pipeline_logger import PipelineLogger, PipelineDashboard, MinimalProgressBar

try:
    from habanero import Crossref
except ImportError:
    print("ERROR: habanero package not installed!")
    print("Install with: pip install habanero")
    exit(1)


class CrossRefV5Enricher:
    """V5 CrossRef enricher with integrated logging and display."""

    def __init__(
        self,
        email: str = "research.assistant@university.edu",
        force: bool = False,
        display_mode: str = "dashboard",
    ):
        """Initialize with polite pool settings and display mode.

        Args:
            email: Email for CrossRef polite pool
            force: Force re-enrichment even if already has data
            display_mode: "dashboard", "minimal", or "quiet"
        """
        self.cr = Crossref(mailto=email)
        self.email = email
        self.batch_size = config.FAST_API_CHECKPOINT_INTERVAL  # 500 papers
        self.checkpoint_file: Path | None = None
        self.processed_papers: set[str] = set()
        self.stats = defaultdict(int)
        self.comprehensive_fields_extracted = defaultdict(int)
        self.force = force

        # Initialize logging and display
        self.logger = PipelineLogger("crossref")
        self.display_mode = display_mode
        self.dashboard = None
        self.progress_bar = None

    def setup_display(self, total_papers: int):
        """Setup the appropriate display based on mode."""
        if self.display_mode == "dashboard":
            self.dashboard = PipelineDashboard(total_stages=8)
            # Add all pipeline stages
            stages = [
                ("CrossRef", total_papers),
                ("S2", total_papers),
                ("OpenAlex", total_papers),
                ("Unpaywall", total_papers),
                ("PubMed", total_papers),
                ("arXiv", total_papers),
                ("TEI", total_papers),
                ("PostProc", total_papers),
            ]
            for name, total in stages:
                self.dashboard.add_stage(name, total)
            # Start CrossRef stage
            self.dashboard.update_stage("CrossRef", status="Running", start_time=time.time())
        elif self.display_mode == "minimal":
            self.progress_bar = MinimalProgressBar("CrossRef", total_papers)

    def load_checkpoint(self, output_dir: Path) -> int:
        """Load checkpoint to resume processing."""
        self.checkpoint_file = output_dir / ".crossref_v5_checkpoint.json"

        if self.checkpoint_file.exists():
            try:
                checkpoint_data = load_checkpoint(self.checkpoint_file)
                self.processed_papers = set(checkpoint_data.get("processed_papers", []))
                self.stats = defaultdict(int, checkpoint_data.get("stats", {}))
                self.logger.info(
                    f"Resuming from checkpoint: {len(self.processed_papers)} papers already processed",
                    to_master=True,
                )
                return len(self.processed_papers)
            except Exception as e:
                self.logger.warning(f"Could not load checkpoint: {e}", to_master=True)
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
            save_checkpoint_atomic(self.checkpoint_file, checkpoint_data)
            self.logger.debug(f"Checkpoint saved: {len(self.processed_papers)} papers processed")

    def clean_doi_with_stats(self, doi: str) -> str | None:
        """Clean DOI using shared utility and track statistics."""
        cleaned = clean_doi(doi)

        if doi and not cleaned:
            # Track why it was rejected
            if doi and "10.13039" in str(doi):
                self.stats["funding_dois_removed"] += 1
                self.logger.debug(f"Removed funding DOI: {doi}")
            else:
                self.stats["invalid_dois"] += 1
                self.logger.debug(f"Invalid DOI format: {doi}")

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

        # References
        if "reference" in crossref_data:
            extracted["reference_count"] = len(crossref_data["reference"])
            self.comprehensive_fields_extracted["references"] += 1

        # Citations (is-referenced-by-count)
        if "is-referenced-by-count" in crossref_data:
            extracted["citation_count"] = crossref_data["is-referenced-by-count"]
            self.comprehensive_fields_extracted["citations"] += 1

        # Abstract
        if "abstract" in crossref_data:
            abstract = crossref_data["abstract"]
            # Remove XML/JATS markup
            abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "")
            abstract = abstract.replace("<jats:italic>", "").replace("</jats:italic>", "")
            extracted["abstract"] = abstract
            self.comprehensive_fields_extracted["abstract"] += 1

        # License info
        if crossref_data.get("license"):
            licenses = []
            for lic in crossref_data["license"]:
                license_info = {
                    "url": lic.get("URL"),
                    "content-version": lic.get("content-version"),
                    "delay-in-days": lic.get("delay-in-days", 0),
                }
                licenses.append(license_info)
            extracted["licenses"] = licenses
            self.comprehensive_fields_extracted["license"] += 1

        # Subject areas
        if "subject" in crossref_data:
            extracted["subjects"] = crossref_data["subject"]
            self.comprehensive_fields_extracted["subjects"] += 1

        # Funder information
        if crossref_data.get("funder"):
            funders = []
            for funder in crossref_data["funder"]:
                funder_info = {
                    "name": funder.get("name"),
                    "doi": funder.get("DOI"),
                    "award": funder.get("award", []),
                }
                funders.append(funder_info)
            extracted["funders"] = funders
            self.comprehensive_fields_extracted["funders"] += 1

        # Clinical trial numbers
        if "clinical-trial-number" in crossref_data:
            extracted["clinical_trial_numbers"] = crossref_data["clinical-trial-number"]
            self.comprehensive_fields_extracted["clinical_trials"] += 1

        # Update timestamp
        if "update-to" in crossref_data:
            extracted["updates"] = crossref_data["update-to"]
            self.comprehensive_fields_extracted["updates"] += 1

        # Links (full-text URLs)
        if crossref_data.get("link"):
            links = []
            for link in crossref_data["link"]:
                link_info = {
                    "url": link.get("URL"),
                    "content-type": link.get("content-type"),
                    "content-version": link.get("content-version"),
                    "intended-application": link.get("intended-application"),
                }
                links.append(link_info)
            extracted["links"] = links
            self.comprehensive_fields_extracted["links"] += 1

        return extracted

    def has_crossref_data(self, paper: dict) -> bool:
        """Check if paper already has CrossRef enrichment."""
        if self.force:
            return False

        # Check for CrossRef enrichment markers
        if paper.get("crossref_enriched"):
            return True

        # Check for CrossRef-specific fields
        crossref_fields = [
            "crossref_type",
            "container-title",
            "publisher",
            "is-referenced-by-count",
            "reference_count",
        ]
        return any(field in paper for field in crossref_fields)

    def enrich_paper_with_crossref(self, paper: dict) -> dict:
        """Enrich a single paper with CrossRef data."""
        paper_id = paper.get("paper_id", "unknown")

        # Skip if already processed (unless forced)
        if not self.force and self.has_crossref_data(paper):
            self.logger.debug(f"Skipping {paper_id}: already has CrossRef data")
            self.stats["already_enriched"] += 1
            return paper

        doi = paper.get("doi")
        if not doi:
            self.stats["no_doi"] += 1
            self.logger.debug(f"No DOI for {paper_id}")
            return paper

        cleaned_doi = self.clean_doi_with_stats(doi)
        if not cleaned_doi:
            self.stats["invalid_doi"] += 1
            return paper

        try:
            self.logger.debug(f"Querying CrossRef for {paper_id}: DOI {cleaned_doi}")
            result = self.cr.works(ids=cleaned_doi)

            if result and "message" in result:
                crossref_data = result["message"]
                comprehensive_fields = self.extract_comprehensive_fields(crossref_data)

                # Merge with existing paper data
                paper.update(comprehensive_fields)
                paper["crossref_enriched"] = True
                paper["crossref_enrichment_date"] = datetime.now(UTC).isoformat()
                paper["crossref_fields_count"] = len(comprehensive_fields)

                self.stats["enriched"] += 1
                self.logger.success(paper_id, f"Enriched with {len(comprehensive_fields)} fields")

                # Update display
                if self.dashboard:
                    self.dashboard.add_event(f"✓ {paper_id}: {len(comprehensive_fields)} fields")

                return paper
            self.stats["not_found"] += 1
            self.logger.debug(f"No CrossRef data for {paper_id}")
            return paper

        except Exception as e:
            self.stats["errors"] += 1
            self.logger.failure(paper_id, str(e)[:100])

            # Update display with error
            if self.dashboard:
                self.dashboard.add_event(f"✗ {paper_id}: {str(e)[:50]}")

            return paper

    def process_batch(self, papers: list[dict], output_dir: Path) -> None:
        """Process a batch of papers and save to sharded structure."""
        for paper in papers:
            paper_id = paper.get("paper_id", "unknown")

            # Skip if already processed in this session
            if paper_id in self.processed_papers:
                continue

            # Enrich the paper
            enriched = self.enrich_paper_with_crossref(paper)

            # Save to sharded structure
            shard = paper_id[:2] if len(paper_id) >= 2 else "00"
            shard_dir = output_dir / shard
            shard_dir.mkdir(exist_ok=True)

            output_file = shard_dir / f"{paper_id}.json"
            with open(output_file, "w") as f:
                json.dump(enriched, f, indent=2)

            self.processed_papers.add(paper_id)

            # Update display
            current = len(self.processed_papers)
            if self.dashboard:
                self.dashboard.update_stage(
                    "CrossRef",
                    current=current,
                    succeeded=self.stats["enriched"],
                    failed=self.stats["errors"],
                    current_file=f"{paper_id}.json",
                )
            elif self.progress_bar:
                self.progress_bar.update(current, self.stats["enriched"], self.stats["errors"])

    def run(self, input_dir: Path, output_dir: Path) -> None:
        """Run the enrichment pipeline."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load all papers
        self.logger.info("Loading papers from input directory", to_master=True)
        all_papers = []
        for json_file in sorted(input_dir.rglob("*.json")):
            with open(json_file) as f:
                paper = json.load(f)
                if "paper_id" not in paper:
                    paper["paper_id"] = json_file.stem
                all_papers.append(paper)

        total_papers = len(all_papers)
        self.logger.info(f"Found {total_papers} papers to process", to_master=True)

        # Setup display
        self.setup_display(total_papers)

        # Load checkpoint
        already_processed = self.load_checkpoint(output_dir)

        # Filter out already processed papers
        papers_to_process = [
            p for p in all_papers if p.get("paper_id", "unknown") not in self.processed_papers
        ]

        if not papers_to_process:
            self.logger.info("All papers already processed!", to_master=True)
            if self.dashboard:
                self.dashboard.update_stage("CrossRef", status="Complete")
                self.dashboard.finish()
            elif self.progress_bar:
                self.progress_bar.finish()
            return

        self.logger.info(f"Processing {len(papers_to_process)} remaining papers", to_master=True)

        # Process in batches
        start_time = time.time()
        last_request_time = 0

        for batch_idx, batch in enumerate(batch_iterator(papers_to_process, self.batch_size)):
            batch_start = time.time()

            # Process batch
            self.process_batch(batch, output_dir)

            # Save checkpoint after each batch
            self.save_checkpoint()

            # Add checkpoint event
            if batch_idx % 1 == 0:  # Every batch
                papers_done = len(self.processed_papers)
                self.logger.info(f"Checkpoint: {papers_done}/{total_papers} papers", to_master=True)
                if self.dashboard:
                    self.dashboard.add_event(f"💾 Checkpoint: {papers_done} papers")

            # Rate limiting between batches
            last_request_time = rate_limit_wait(last_request_time, 0.1)  # 100ms between batches

            # Log batch completion
            batch_time = time.time() - batch_start
            self.logger.debug(f"Batch {batch_idx + 1} completed in {batch_time:.1f}s")

        # Final statistics
        total_time = time.time() - start_time
        self.logger.info(f"Processing complete in {total_time:.1f}s", to_master=True)
        self.logger.info(f"Enriched: {self.stats['enriched']}", to_master=True)
        self.logger.info(f"Errors: {self.stats['errors']}", to_master=True)
        self.logger.info(f"No DOI: {self.stats['no_doi']}", to_master=True)
        self.logger.info(f"Already enriched: {self.stats['already_enriched']}", to_master=True)

        # Update display to complete
        if self.dashboard:
            self.dashboard.update_stage("CrossRef", status="Complete")
            self.dashboard.add_event(f"✓ CrossRef complete: {self.stats['enriched']} enriched")
            self.dashboard.finish()
        elif self.progress_bar:
            self.progress_bar.finish()

        # Print field coverage statistics
        print("\nField extraction coverage:")
        for field, count in sorted(
            self.comprehensive_fields_extracted.items(), key=lambda x: x[1], reverse=True
        )[:20]:
            coverage = (count / self.stats["enriched"] * 100) if self.stats["enriched"] > 0 else 0
            print(f"  {field:20s}: {count:5d} papers ({coverage:.1f}%)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="V5 CrossRef Enrichment Pipeline")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("extraction_pipeline/02_json_extraction"),
        help="Input directory with extracted JSON papers",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("extraction_pipeline/04_crossref_enrichment"),
        help="Output directory for enriched papers",
    )
    parser.add_argument(
        "--email", default="research.assistant@university.edu", help="Email for CrossRef polite pool"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-enrichment even if paper already has CrossRef data"
    )
    parser.add_argument(
        "--display",
        choices=["dashboard", "minimal", "quiet"],
        default="dashboard",
        help="Display mode: dashboard (40-line), minimal (progress bars), or quiet",
    )

    args = parser.parse_args()

    # Run enrichment
    enricher = CrossRefV5Enricher(email=args.email, force=args.force, display_mode=args.display)
    enricher.run(args.input, args.output)


if __name__ == "__main__":
    main()
