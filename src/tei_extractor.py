#!/usr/bin/env python3
"""Comprehensive TEI XML to JSON extractor with checkpoint recovery.

This enhanced version adds checkpoint recovery to resume processing after interruptions.
"""

from src import config
import json
from defusedxml import ElementTree
from pathlib import Path
from datetime import datetime, UTC
import re
from typing import Any
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ComprehensiveTEIExtractor:
    """Extract ALL information from TEI XML files with checkpoint support."""

    def __init__(self) -> None:
        """Initialize the TEI extractor with checkpoint recovery support."""
        self.ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        self.stats: dict[str, Any] = {"total": 0, "successful": 0, "failed": 0, "fields_extracted": {}}
        self.checkpoint_file: Path | None = None
        self.processed_files: set[str] = set()

    def load_checkpoint(self, output_dir: Path) -> set[str]:
        """Load checkpoint to resume processing."""
        self.checkpoint_file = output_dir / ".tei_extraction_checkpoint.json"

        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    checkpoint_data = json.load(f)
                    self.processed_files = set(checkpoint_data.get("processed_files", []))
                    self.stats = checkpoint_data.get("stats", self.stats)
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
                "stats": self.stats,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            with open(self.checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f, indent=2)

    def extract_year_from_date(self, date_str: str) -> int | None:
        """Extract year from various date formats."""
        if not date_str:
            return None

        # Try ISO format first (YYYY-MM-DD or YYYY)
        year_match = re.match(r"^(\d{4})", date_str)
        if year_match:
            year = int(year_match.group(1))
            if config.MIN_YEAR_VALID <= year <= datetime.now(UTC).year + 1:
                return year

        # Try finding 4-digit year anywhere
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date_str)
        if year_match:
            year = int(year_match.group(1))
            if config.MIN_YEAR_VALID <= year <= datetime.now(UTC).year + 1:
                return year

        return None

    def parse_tei_xml(self, tei_file: Path) -> dict[str, Any]:
        """Comprehensively parse TEI XML to extract ALL information."""
        try:
            tree = ElementTree.parse(tei_file)
            root = tree.getroot()

            data: dict[str, Any] = {"paper_id": tei_file.stem}

            # ============= 1. BASIC METADATA =============

            # Title (multiple sources)
            title = None
            # Try main title first
            title_elem = root.find(".//tei:fileDesc/tei:titleStmt/tei:title", self.ns)
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
            # Fallback to analytic title
            if not title:
                title_elem = root.find(".//tei:analytic/tei:title", self.ns)
                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip()
            if title:
                data["title"] = title

            # Abstract
            abstract_elem = root.find(".//tei:abstract", self.ns)
            if abstract_elem is not None:
                abstract_text = " ".join(abstract_elem.itertext()).strip()
                if abstract_text:
                    data["abstract"] = abstract_text

            # ============= config.MIN_MATCH_COUNT. DATE/YEAR EXTRACTION =============

            year = None
            date_string = None

            # Try multiple locations for dates
            date_locations = [
                ".//tei:biblStruct//tei:monogr/tei:imprint/tei:date[@when]",
                ".//tei:publicationStmt/tei:date[@when]",
                ".//tei:sourceDesc//tei:date[@when]",
                ".//tei:biblStruct//tei:date[@when]",
            ]

            for location in date_locations:
                date_elem = root.find(location, self.ns)
                if date_elem is not None:
                    when = date_elem.get("when")
                    if when:
                        extracted_year = self.extract_year_from_date(when)
                        if extracted_year:
                            year = extracted_year
                            date_string = when
                            break

            # Also check text content
            if not year:
                for location in date_locations:
                    date_elem = root.find(location.replace("[@when]", ""), self.ns)
                    if date_elem is not None and date_elem.text:
                        extracted_year = self.extract_year_from_date(date_elem.text)
                        if extracted_year:
                            year = extracted_year
                            date_string = date_elem.text
                            break

            if year:
                data["year"] = year
            if date_string:
                data["date"] = date_string

            # ============= config.MAX_RETRIES_DEFAULT. JOURNAL/PUBLICATION =============

            journal = None

            # Try multiple locations
            journal_locations = [
                ".//tei:monogr/tei:title[@level='j']",
                ".//tei:monogr/tei:title[@level='m']",
                ".//tei:monogr/tei:title",
                ".//tei:publicationStmt/tei:publisher",
            ]

            for location in journal_locations:
                journal_elem = root.find(location, self.ns)
                if journal_elem is not None and journal_elem.text:
                    journal = journal_elem.text.strip()
                    if journal:
                        break

            if journal:
                data["journal"] = journal
                data["publication"] = journal  # Also store as publication

            # ============= 4. AUTHORS =============

            authors: list[dict[str, Any]] = []
            author_elems = root.findall(".//tei:fileDesc//tei:author", self.ns)

            for author_elem in author_elems:
                author_info: dict[str, Any] = {}

                # Get names
                forename = author_elem.find(".//tei:forename", self.ns)
                surname = author_elem.find(".//tei:surname", self.ns)

                if forename is not None and forename.text:
                    author_info["forename"] = forename.text.strip()
                if surname is not None and surname.text:
                    author_info["surname"] = surname.text.strip()

                # Get full name
                if "forename" in author_info and "surname" in author_info:
                    author_info["name"] = f"{author_info['forename']} {author_info['surname']}"
                elif "surname" in author_info:
                    author_info["name"] = author_info["surname"]

                # Get affiliation
                affiliation_elem = author_elem.find(".//tei:affiliation", self.ns)
                if affiliation_elem is not None:
                    affiliation_text = " ".join(affiliation_elem.itertext()).strip()
                    if affiliation_text:
                        author_info["affiliation"] = affiliation_text

                # Get email
                email_elem = author_elem.find(".//tei:email", self.ns)
                if email_elem is not None and email_elem.text:
                    author_info["email"] = email_elem.text.strip()

                # Get ORCID
                idno_elem = author_elem.find(".//tei:idno[@type='ORCID']", self.ns)
                if idno_elem is not None and idno_elem.text:
                    author_info["orcid"] = idno_elem.text.strip()

                if author_info:
                    authors.append(author_info)

            if authors:
                data["authors"] = authors

            # ============= config.DEFAULT_MAX_RESULTS. IDENTIFIERS =============

            # DOI
            doi_elem = root.find(".//tei:idno[@type='DOI']", self.ns)
            if doi_elem is not None and doi_elem.text:
                data["doi"] = doi_elem.text.strip()

            # arXiv
            arxiv_elem = root.find(".//tei:idno[@type='arXiv']", self.ns)
            if arxiv_elem is not None and arxiv_elem.text:
                data["arxiv"] = arxiv_elem.text.strip()

            # PubMed
            pubmed_elem = root.find(".//tei:idno[@type='PMID']", self.ns)
            if pubmed_elem is not None and pubmed_elem.text:
                data["pmid"] = pubmed_elem.text.strip()

            # ============= 6. KEYWORDS =============

            keywords = []
            keyword_elems = root.findall(".//tei:keywords/tei:term", self.ns)
            for kw_elem in keyword_elems:
                if kw_elem.text:
                    keywords.append(kw_elem.text.strip())

            if keywords:
                data["keywords"] = keywords

            # ============= 7. SECTIONS =============

            sections = []
            body_elem = root.find(".//tei:body", self.ns)

            if body_elem is not None:
                for div in body_elem.findall(".//tei:div", self.ns):
                    section = {}

                    # Get title
                    head = div.find("tei:head", self.ns)
                    if head is not None and head.text:
                        section["title"] = head.text.strip()

                    # Get full text (including nested paragraphs)
                    paragraphs = []
                    for p in div.findall(".//tei:p", self.ns):
                        # Use itertext() to get all text including nested elements
                        text = " ".join(p.itertext()).strip()
                        if text:
                            paragraphs.append(text)

                    if paragraphs:
                        section["text"] = "\n\n".join(paragraphs)

                    if section:
                        sections.append(section)

            if sections:
                data["sections"] = sections

            # ============= 8. REFERENCES =============

            references = []
            ref_elems = root.findall(".//tei:listBibl/tei:biblStruct", self.ns)

            for ref_elem in ref_elems:
                ref = {}

                # Title
                title_elem = ref_elem.find(".//tei:title", self.ns)
                if title_elem is not None and title_elem.text:
                    ref["title"] = title_elem.text.strip()

                # Authors
                ref_authors = []
                for author in ref_elem.findall(".//tei:author", self.ns):
                    forename = author.find(".//tei:forename", self.ns)
                    surname = author.find(".//tei:surname", self.ns)
                    if surname is not None and surname.text:
                        name = surname.text.strip()
                        if forename is not None and forename.text:
                            name = f"{forename.text.strip()} {name}"
                        ref_authors.append(name)
                if ref_authors:
                    ref["authors"] = ref_authors

                # Year
                date_elem = ref_elem.find(".//tei:date[@when]", self.ns)
                if date_elem is not None:
                    year = self.extract_year_from_date(date_elem.get("when"))
                    if year:
                        ref["year"] = year

                # DOI
                doi_elem = ref_elem.find(".//tei:idno[@type='DOI']", self.ns)
                if doi_elem is not None and doi_elem.text:
                    ref["doi"] = doi_elem.text.strip()

                if ref:
                    references.append(ref)

            if references:
                data["references"] = references
                data["num_references"] = len(references)

            # Track extracted fields
            for field in data:
                if field != "paper_id":
                    self.stats["fields_extracted"][field] = self.stats["fields_extracted"].get(field, 0) + 1

            return data

        except ElementTree.ParseError as e:
            logger.error("XML parse error in %s: %s", tei_file.name, e)
            return {"paper_id": tei_file.stem, "parse_error": str(e)}
        except Exception as e:
            logger.error("Unexpected error processing %s: %s", tei_file.name, e)
            return {"paper_id": tei_file.stem, "error": str(e)}

    def process_directory(self, tei_dir: Path, output_dir: Path) -> None:
        """Process all TEI XML files in a directory with checkpoint support."""
        tei_files = list(tei_dir.glob("*.xml"))
        logger.info("Found %d TEI XML files", len(tei_files))

        output_dir.mkdir(exist_ok=True, parents=True)

        # Load checkpoint
        self.load_checkpoint(output_dir)

        # Filter out already processed files
        files_to_process = []
        for tei_file in tei_files:
            output_file = output_dir / f"{tei_file.stem}.json"
            if tei_file.stem in self.processed_files or output_file.exists():
                logger.debug("Skipping already processed: %s", tei_file.name)
                if tei_file.stem not in self.processed_files:
                    self.processed_files.add(tei_file.stem)
            else:
                files_to_process.append(tei_file)

        if not files_to_process:
            logger.info("All files already processed!")
            self.print_summary()
            return

        logger.info("Processing %d remaining files...", len(files_to_process))

        checkpoint_counter = 0
        for i, tei_file in enumerate(files_to_process, 1):
            if i % config.MIN_CONTENT_LENGTH == 0:
                logger.info("Processing %d/%d...", i, len(files_to_process))

            self.stats["total"] += 1

            # Extract data
            data = self.parse_tei_xml(tei_file)

            if "parse_error" in data or "error" in data:
                self.stats["failed"] += 1
                logger.error("Failed: %s", tei_file.name)
            else:
                self.stats["successful"] += 1

            # Save JSON
            output_file = output_dir / f"{tei_file.stem}.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

            # Track processed file
            self.processed_files.add(tei_file.stem)
            checkpoint_counter += 1

            # Save checkpoint periodically
            if checkpoint_counter >= config.TEI_CHECKPOINT_INTERVAL:
                self.save_checkpoint()
                logger.info("Checkpoint saved: %d total files processed", len(self.processed_files))
                checkpoint_counter = 0

        # Final checkpoint save
        self.save_checkpoint()

        # Print summary
        self.print_summary()

    def print_summary(self) -> None:
        """Print extraction summary."""
        print("\n" + "=" * 70)
        print("EXTRACTION COMPLETE")
        print("=" * 70)
        print(f"Total files: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")

        if self.stats["fields_extracted"]:
            print("\nFields extracted (coverage):")
            total = self.stats["successful"] if self.stats["successful"] > 0 else 1
            for field, count in sorted(self.stats["fields_extracted"].items()):
                percentage = (count / total) * 100
                print(f"  {field}: {count} ({percentage:.1f}%)")


def main() -> None:
    """Run the main program."""
    parser = argparse.ArgumentParser(description="TEI XML to JSON extraction with checkpoint recovery")
    parser.add_argument("--input-dir", default="tei_xml", help="Directory containing TEI XML files")
    parser.add_argument("--output-dir", default="json_extracted", help="Output directory for JSON files")
    parser.add_argument("--reset", action="store_true", help="Reset checkpoint and start fresh")

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        logger.error("Input directory not found: %s", input_dir)
        return

    # Remove checkpoint if reset requested
    if args.reset:
        checkpoint_file = output_dir / ".tei_extraction_checkpoint.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info("Checkpoint reset")

    extractor = ComprehensiveTEIExtractor()
    extractor.process_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()
