#!/usr/bin/env python3
"""Comprehensive CrossRef enrichment extracting ALL available metadata fields.

This version extracts and verifies all possible fields from CrossRef API including:
- Basic metadata (DOI, title, year, authors, journal)
- Publication details (volume, issue, pages, publisher, ISSN)
- Metrics (citation count, reference count)
- Content (abstract, keywords, subjects)
- Research context (funders, clinical trials, licenses)
- Enhanced author info (ORCID, affiliations)
- Dates (published online/print, accepted, created)
- Quality indicators (peer review, assertions)
"""

import json
import logging
import time
import re
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
    # Fallback if config not available
    CROSSREF_POLITE_EMAIL = "research.assistant@university.edu"

try:
    from habanero import Crossref
except ImportError:
    print("ERROR: habanero package not installed!")
    print("Install with: pip install habanero")
    exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ComprehensiveCrossRefEnricher:
    """Comprehensive CrossRef enricher extracting all available fields."""

    def __init__(self, mailto=None):
        """Initialize enricher with polite pool access."""
        # Use polite pool by providing email - gets better performance and reliability
        # Default to config email if not provided
        if mailto is None:
            mailto = CROSSREF_POLITE_EMAIL
        self.cr = Crossref(mailto=mailto)
        logger.info(f"Using CrossRef polite pool with email: {mailto}")
        self.stats = {
            "total_processed": 0,
            "api_queries": 0,
            "api_errors": 0,
            "papers_enriched": 0,
            "papers_failed": 0,
            "fields_extracted": {},
        }

    def query_crossref(self, paper_data: dict) -> dict | None:
        """Query CrossRef API for paper metadata.

        Args:
            paper_data: Paper data with DOI or title

        Returns:
            CrossRef response or None
        """
        self.stats["api_queries"] += 1

        try:
            # Strategy 1: Query by DOI if available
            if paper_data.get("doi"):
                try:
                    work = self.cr.works(ids=paper_data["doi"])
                    if work and "message" in work:
                        return work["message"]
                except Exception as e:
                    logger.debug(f"DOI query failed: {e}")

            # Strategy 2: Search by title + authors
            title = paper_data.get("title")
            if title:
                # Build query
                query = title
                authors = paper_data.get("authors", [])
                if authors and len(authors) > 0:
                    # Add first author's last name
                    first_author = authors[0]
                    if isinstance(first_author, dict):
                        name = first_author.get("name", "")
                        # Try to extract last name
                        name_parts = name.split()
                        if name_parts:
                            query += f" {name_parts[-1]}"

                # Search CrossRef
                works = self.cr.works(query=query, limit=5)
                if works and "message" in works and "items" in works["message"]:
                    items = works["message"]["items"]
                    if items:
                        # Find best match by title similarity
                        best_match = self.find_best_match(title, items)
                        if best_match:
                            return best_match

            return None

        except Exception as e:
            logger.error(f"CrossRef API error: {e}")
            self.stats["api_errors"] += 1
            return None

    def find_best_match(self, original_title: str, items: list[dict]) -> dict | None:
        """Find best matching paper from CrossRef results.

        Args:
            original_title: Original paper title
            items: List of CrossRef results

        Returns:
            Best matching item or None
        """
        if not original_title or not items:
            return None

        original_lower = original_title.lower().strip()
        best_score = 0
        best_match = None

        for item in items:
            # Get item title
            titles = item.get("title", [])
            if not titles:
                continue

            item_title = titles[0].lower().strip()

            # Calculate similarity using simple character overlap
            from difflib import SequenceMatcher

            score = SequenceMatcher(None, original_lower, item_title).ratio()

            if score > best_score:
                best_score = score
                best_match = item

            # Early exit for exact match
            if score >= 0.95:
                return item

        # Return best match if similarity is high enough
        if best_score >= 0.8:
            return best_match

        return None

    def clean_abstract(self, abstract: str) -> str:
        """Clean abstract by removing XML/HTML tags.

        Args:
            abstract: Raw abstract with potential tags

        Returns:
            Cleaned abstract text
        """
        if not abstract:
            return ""

        # Remove common XML/HTML tags
        cleaned = re.sub(r"<jats:[^>]+>", "", abstract)
        cleaned = re.sub(r"</jats:[^>]+>", "", cleaned)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)

        # Clean up whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def extract_comprehensive_metadata(self, crossref_data: dict) -> dict:
        """Extract ALL available metadata from CrossRef response.

        Args:
            crossref_data: Raw CrossRef API response

        Returns:
            Comprehensive metadata dictionary
        """
        metadata = {}

        # ========== 1. BASIC METADATA ==========
        # DOI
        if "DOI" in crossref_data:
            metadata["doi"] = crossref_data["DOI"]
            self.track_field("doi")

        # URL
        if "URL" in crossref_data:
            metadata["url"] = crossref_data["URL"]
            self.track_field("url")

        # Type (journal-article, book-chapter, etc.)
        if "type" in crossref_data:
            metadata["publication_type"] = crossref_data["type"]
            self.track_field("publication_type")

        # Title
        titles = crossref_data.get("title", [])
        if titles:
            metadata["title"] = titles[0]
            self.track_field("title")

        # Subtitle
        subtitles = crossref_data.get("subtitle", [])
        if subtitles:
            metadata["subtitle"] = subtitles[0]
            self.track_field("subtitle")

        # Short title
        short_titles = crossref_data.get("short-title", [])
        if short_titles:
            metadata["short_title"] = short_titles[0]
            self.track_field("short_title")

        # ========== 2. DATES ==========
        # Extract year (primary)
        date_parts = crossref_data.get("published-print", {}).get("date-parts")
        if not date_parts:
            date_parts = crossref_data.get("published-online", {}).get("date-parts")
        if not date_parts:
            date_parts = crossref_data.get("issued", {}).get("date-parts")

        if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
            metadata["year"] = date_parts[0][0]
            self.track_field("year")

            # Full date if available
            if len(date_parts[0]) >= 3:
                metadata["publication_date"] = {
                    "year": date_parts[0][0],
                    "month": date_parts[0][1] if len(date_parts[0]) > 1 else None,
                    "day": date_parts[0][2] if len(date_parts[0]) > 2 else None,
                }
                self.track_field("publication_date")

        # Additional dates
        dates_info = {}

        # Published online
        if "published-online" in crossref_data:
            online_date = crossref_data["published-online"]
            if online_date.get("date-parts"):
                dates_info["published_online"] = online_date["date-parts"][0]
                self.track_field("published_online")

        # Published print
        if "published-print" in crossref_data:
            print_date = crossref_data["published-print"]
            if print_date.get("date-parts"):
                dates_info["published_print"] = print_date["date-parts"][0]
                self.track_field("published_print")

        # Created date
        if "created" in crossref_data:
            created = crossref_data["created"]
            if "date-time" in created:
                dates_info["created"] = created["date-time"]
                self.track_field("created")

        # Deposited date
        if "deposited" in crossref_data:
            deposited = crossref_data["deposited"]
            if "date-time" in deposited:
                dates_info["deposited"] = deposited["date-time"]
                self.track_field("deposited")

        # Indexed date
        if "indexed" in crossref_data:
            indexed = crossref_data["indexed"]
            if "date-time" in indexed:
                dates_info["indexed"] = indexed["date-time"]
                self.track_field("indexed")

        # Accepted date
        if "accepted" in crossref_data:
            accepted = crossref_data["accepted"]
            if accepted.get("date-parts"):
                dates_info["accepted"] = accepted["date-parts"][0]
                self.track_field("accepted")

        # Approved date
        if "approved" in crossref_data:
            approved = crossref_data["approved"]
            if approved.get("date-parts"):
                dates_info["approved"] = approved["date-parts"][0]
                self.track_field("approved")

        if dates_info:
            metadata["dates"] = dates_info

        # ========== 3. PUBLICATION DETAILS ==========
        publication_info = {}

        # Journal
        journal = crossref_data.get("container-title", [])
        if journal:
            metadata["journal"] = journal[0]
            publication_info["journal"] = journal[0]
            self.track_field("journal")

        # Journal abbreviation
        journal_short = crossref_data.get("container-title-short", [])
        if journal_short:
            publication_info["journal_abbreviation"] = journal_short[0]
            self.track_field("journal_abbreviation")

        # Publisher
        if "publisher" in crossref_data:
            publication_info["publisher"] = crossref_data["publisher"]
            self.track_field("publisher")

        # Publisher location
        if "publisher-location" in crossref_data:
            publication_info["publisher_location"] = crossref_data["publisher-location"]
            self.track_field("publisher_location")

        # Volume
        if "volume" in crossref_data:
            publication_info["volume"] = crossref_data["volume"]
            self.track_field("volume")

        # Issue
        if "issue" in crossref_data:
            publication_info["issue"] = crossref_data["issue"]
            self.track_field("issue")

        # Pages
        if "page" in crossref_data:
            publication_info["pages"] = crossref_data["page"]
            self.track_field("pages")

        # Article number
        if "article-number" in crossref_data:
            publication_info["article_number"] = crossref_data["article-number"]
            self.track_field("article_number")

        if publication_info:
            metadata["publication"] = publication_info

        # ========== 4. AUTHORS & CONTRIBUTORS ==========
        # Authors with enhanced info
        authors = []
        for author in crossref_data.get("author", []):
            author_entry = {}

            # Name
            name_parts = []
            if "given" in author:
                name_parts.append(author["given"])
            if "family" in author:
                name_parts.append(author["family"])

            if name_parts:
                author_entry["name"] = " ".join(name_parts)

            # ORCID
            if "ORCID" in author:
                author_entry["orcid"] = author["ORCID"]
                self.track_field("author_orcid")

            # Affiliation
            if author.get("affiliation"):
                affiliations = []
                for aff in author["affiliation"]:
                    aff_entry = {}
                    if "name" in aff:
                        aff_entry["organization"] = aff["name"]
                    if "department" in aff:
                        aff_entry["department"] = aff["department"]
                    if "place" in aff:
                        aff_entry["location"] = aff["place"]
                    if aff_entry:
                        affiliations.append(aff_entry)

                if affiliations:
                    author_entry["affiliations"] = affiliations
                    self.track_field("author_affiliations")

            # Sequence (first, additional)
            if "sequence" in author:
                author_entry["sequence"] = author["sequence"]

            if author_entry:
                authors.append(author_entry)

        if authors:
            metadata["authors"] = authors
            self.track_field("authors")

        # Editors
        editors = []
        for editor in crossref_data.get("editor", []):
            editor_entry = {}

            name_parts = []
            if "given" in editor:
                name_parts.append(editor["given"])
            if "family" in editor:
                name_parts.append(editor["family"])

            if name_parts:
                editor_entry["name"] = " ".join(name_parts)
                editors.append(editor_entry)

        if editors:
            metadata["editors"] = editors
            self.track_field("editors")

        # ========== 5. IDENTIFIERS ==========
        identifiers = {}

        # ISSN
        if "ISSN" in crossref_data:
            identifiers["issn"] = crossref_data["ISSN"]
            self.track_field("issn")

        # ISBN
        if "ISBN" in crossref_data:
            identifiers["isbn"] = crossref_data["ISBN"]
            self.track_field("isbn")

        # Archive
        if "archive" in crossref_data:
            identifiers["archive"] = crossref_data["archive"]
            self.track_field("archive")

        # Member ID
        if "member" in crossref_data:
            identifiers["crossref_member"] = crossref_data["member"]
            self.track_field("crossref_member")

        # Prefix
        if "prefix" in crossref_data:
            identifiers["doi_prefix"] = crossref_data["prefix"]
            self.track_field("doi_prefix")

        if identifiers:
            metadata["identifiers"] = identifiers

        # ========== 6. METRICS ==========
        metrics = {}

        # Citation count
        if "is-referenced-by-count" in crossref_data:
            metrics["citation_count"] = crossref_data["is-referenced-by-count"]
            self.track_field("citation_count")

        # Reference count
        if "references-count" in crossref_data:
            metrics["reference_count"] = crossref_data["references-count"]
            self.track_field("reference_count")

        # CrossRef score
        if "score" in crossref_data:
            metrics["crossref_score"] = crossref_data["score"]
            self.track_field("crossref_score")

        if metrics:
            metadata["metrics"] = metrics

        # ========== 7. CONTENT ==========
        # Abstract
        if "abstract" in crossref_data:
            abstract = self.clean_abstract(crossref_data["abstract"])
            if abstract:
                metadata["abstract"] = abstract
                self.track_field("abstract")

        # ========== 8. CLASSIFICATION ==========
        classification = {}

        # Subjects
        if "subject" in crossref_data:
            subjects = crossref_data["subject"]
            if subjects:
                classification["subjects"] = subjects
                self.track_field("subjects")

        # Keywords
        if "keyword" in crossref_data:
            keywords = crossref_data["keyword"]
            if keywords:
                classification["keywords"] = keywords
                self.track_field("keywords")

        if classification:
            metadata["classification"] = classification

        # ========== 9. CLINICAL TRIALS ==========
        if "clinical-trial-number" in crossref_data:
            trials = []
            for trial in crossref_data["clinical-trial-number"]:
                trial_entry = {}
                if "clinical-trial-number" in trial:
                    trial_entry["number"] = trial["clinical-trial-number"]
                if "registry" in trial:
                    trial_entry["registry"] = trial["registry"]
                if trial_entry:
                    trials.append(trial_entry)

            if trials:
                metadata["clinical_trials"] = trials
                self.track_field("clinical_trials")

        # ========== 10. FUNDING ==========
        if "funder" in crossref_data:
            funders = []
            for funder in crossref_data["funder"]:
                funder_entry = {}

                if "name" in funder:
                    funder_entry["name"] = funder["name"]

                if "DOI" in funder:
                    funder_entry["doi"] = funder["DOI"]

                if "award" in funder:
                    awards = funder["award"]
                    if isinstance(awards, list) and awards:
                        funder_entry["awards"] = awards

                if funder_entry:
                    funders.append(funder_entry)

            if funders:
                metadata["funding"] = funders
                self.track_field("funding")

        # ========== 11. REFERENCES ==========
        if "reference" in crossref_data:
            refs = crossref_data["reference"]
            if refs:
                # Store count and sample
                metadata["reference_details"] = {
                    "count": len(refs),
                    "sample": refs[:5] if len(refs) > 5 else refs,  # Store first 5 as sample
                }
                self.track_field("references")

        # ========== 12. LICENSE ==========
        if "license" in crossref_data:
            licenses = []
            for lic in crossref_data["license"]:
                lic_entry = {}

                if "URL" in lic:
                    lic_entry["url"] = lic["URL"]

                if "start" in lic:
                    start = lic["start"]
                    if "date-time" in start:
                        lic_entry["start_date"] = start["date-time"]
                    elif "date-parts" in start:
                        lic_entry["start_date"] = start["date-parts"]

                if "content-version" in lic:
                    lic_entry["content_version"] = lic["content-version"]

                if "delay-in-days" in lic:
                    lic_entry["delay_days"] = lic["delay-in-days"]

                if lic_entry:
                    licenses.append(lic_entry)

            if licenses:
                metadata["licenses"] = licenses
                self.track_field("licenses")

        # ========== 13. QUALITY INDICATORS ==========
        quality_indicators = {}

        # Peer review
        if "peer-review" in crossref_data:
            quality_indicators["has_peer_review"] = True
            self.track_field("peer_review")

        # Content domain
        if "content-domain" in crossref_data:
            quality_indicators["content_domain"] = crossref_data["content-domain"]
            self.track_field("content_domain")

        # Assertions
        if "assertion" in crossref_data:
            assertions = []
            for assertion in crossref_data["assertion"]:
                assert_entry = {}

                if "name" in assertion:
                    assert_entry["name"] = assertion["name"]

                if "value" in assertion:
                    assert_entry["value"] = assertion["value"]

                if "label" in assertion:
                    assert_entry["label"] = assertion["label"]

                if assert_entry:
                    assertions.append(assert_entry)

            if assertions:
                quality_indicators["assertions"] = assertions
                self.track_field("assertions")

        if quality_indicators:
            metadata["quality_indicators"] = quality_indicators

        # ========== 14. RELATIONS ==========
        if "relation" in crossref_data:
            relations = crossref_data["relation"]
            if relations:
                relation_summary = {}
                for rel_type, rel_data in relations.items():
                    if isinstance(rel_data, list) and rel_data:
                        relation_summary[rel_type] = {
                            "count": len(rel_data),
                            "items": rel_data[:3],  # Store first 3 as sample
                        }

                if relation_summary:
                    metadata["relations"] = relation_summary
                    self.track_field("relations")

        # ========== 15. UPDATE HISTORY ==========
        if "update-to" in crossref_data:
            updates = []
            for update in crossref_data["update-to"]:
                update_entry = {}

                if "DOI" in update:
                    update_entry["doi"] = update["DOI"]

                if "type" in update:
                    update_entry["type"] = update["type"]

                if "label" in update:
                    update_entry["label"] = update["label"]

                if update_entry:
                    updates.append(update_entry)

            if updates:
                metadata["update_history"] = updates
                self.track_field("update_history")

        # ========== 16. LANGUAGE ==========
        if "language" in crossref_data:
            metadata["language"] = crossref_data["language"]
            self.track_field("language")

        return metadata

    def track_field(self, field_name: str):
        """Track which fields are being extracted.

        Args:
            field_name: Name of the field extracted
        """
        if field_name not in self.stats["fields_extracted"]:
            self.stats["fields_extracted"][field_name] = 0
        self.stats["fields_extracted"][field_name] += 1

    def enrich_paper(self, paper_file: Path, output_dir: Path) -> bool:
        """Enrich a single paper with comprehensive CrossRef metadata.

        Args:
            paper_file: Path to paper JSON file
            output_dir: Output directory for enriched files

        Returns:
            True if enriched, False otherwise
        """
        try:
            # Load paper data
            with open(paper_file) as f:
                paper_data = json.load(f)

            # Check if already enriched
            if paper_data.get("crossref_comprehensive"):
                # Just copy the file
                output_file = output_dir / paper_file.name
                with open(output_file, "w") as f:
                    json.dump(paper_data, f, indent=2)
                return False

            # Query CrossRef
            crossref_data = self.query_crossref(paper_data)

            if not crossref_data:
                # No match found - copy original
                output_file = output_dir / paper_file.name
                with open(output_file, "w") as f:
                    json.dump(paper_data, f, indent=2)
                self.stats["papers_failed"] += 1
                return False

            # Extract comprehensive metadata
            new_metadata = self.extract_comprehensive_metadata(crossref_data)

            # Merge with existing data
            # Keep original basic fields if they exist
            for field in ["paper_id", "md5", "sections", "num_citations", "notes", "processing_software"]:
                if field in paper_data:
                    new_metadata[field] = paper_data[field]

            # Add enrichment metadata
            new_metadata["crossref_comprehensive"] = True
            new_metadata["crossref_enrichment_date"] = datetime.utcnow().isoformat()
            new_metadata["original_extraction"] = {
                "title": paper_data.get("title"),
                "year": paper_data.get("year"),
                "doi": paper_data.get("doi"),
                "authors": len(paper_data.get("authors", [])),
                "journal": paper_data.get("journal") or paper_data.get("publication", {}).get("journal"),
            }

            # Save enriched paper
            output_file = output_dir / paper_file.name
            with open(output_file, "w") as f:
                json.dump(new_metadata, f, indent=2)

            self.stats["papers_enriched"] += 1
            return True

        except Exception as e:
            logger.error(f"Error processing {paper_file}: {e}")
            # Copy original file on error
            try:
                output_file = output_dir / paper_file.name
                with open(paper_file) as f_in:
                    with open(output_file, "w") as f_out:
                        f_out.write(f_in.read())
            except:
                pass
            self.stats["papers_failed"] += 1
            return False

    def process_directory(self, input_dir: Path, output_dir: Path, max_papers: int | None = None):
        """Process all papers in a directory.

        Args:
            input_dir: Input directory with JSON files
            output_dir: Output directory for enriched files
            max_papers: Maximum papers to process (for testing)
        """
        # Create output directory
        output_dir.mkdir(exist_ok=True, parents=True)

        # Get all JSON files
        json_files = sorted(input_dir.glob("*.json"))

        if max_papers:
            json_files = json_files[:max_papers]

        logger.info(f"Found {len(json_files)} papers to process")
        logger.info(f"Input: {input_dir}")
        logger.info(f"Output: {output_dir}")

        # Process each paper
        for i, paper_file in enumerate(json_files, 1):
            if i % 10 == 0:
                logger.info(f"Processing {i}/{len(json_files)}...")
                logger.info(f"  Papers enriched: {self.stats['papers_enriched']}")
                logger.info(f"  Papers failed: {self.stats['papers_failed']}")

            self.enrich_paper(paper_file, output_dir)
            self.stats["total_processed"] += 1

            # Rate limiting
            if i % 5 == 0:
                time.sleep(0.5)  # Be nice to CrossRef API

        # Generate report
        self.generate_report(output_dir)

    def generate_report(self, output_dir: Path):
        """Generate comprehensive enrichment report.

        Args:
            output_dir: Output directory for report
        """
        # Calculate field coverage
        field_coverage = {}
        if self.stats["papers_enriched"] > 0:
            for field, count in self.stats["fields_extracted"].items():
                coverage = (count / self.stats["papers_enriched"]) * 100
                field_coverage[field] = f"{coverage:.1f}%"

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": {
                "total_processed": self.stats["total_processed"],
                "papers_enriched": self.stats["papers_enriched"],
                "papers_failed": self.stats["papers_failed"],
                "api_queries": self.stats["api_queries"],
                "api_errors": self.stats["api_errors"],
                "enrichment_rate": f"{(self.stats['papers_enriched'] / max(1, self.stats['total_processed'])) * 100:.1f}%",
            },
            "fields_extracted": self.stats["fields_extracted"],
            "field_coverage": field_coverage,
            "comprehensive_fields": {
                "basic": ["doi", "title", "subtitle", "year", "url", "publication_type"],
                "publication": ["journal", "volume", "issue", "pages", "publisher", "issn"],
                "authors": ["name", "orcid", "affiliations"],
                "metrics": ["citation_count", "reference_count"],
                "content": ["abstract", "keywords", "subjects"],
                "research": ["funding", "clinical_trials"],
                "quality": ["peer_review", "assertions", "licenses"],
                "dates": ["published_online", "published_print", "accepted", "created"],
            },
        }

        # Save report
        report_file = output_dir / "crossref_comprehensive_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 70)
        print("COMPREHENSIVE CROSSREF ENRICHMENT COMPLETE")
        print("=" * 70)
        print(f"Total processed: {self.stats['total_processed']}")
        print(f"Papers enriched: {self.stats['papers_enriched']}")
        print(f"Papers failed: {self.stats['papers_failed']}")
        print(
            f"Enrichment rate: {(self.stats['papers_enriched'] / max(1, self.stats['total_processed'])) * 100:.1f}%"
        )

        print("\nTop extracted fields:")
        sorted_fields = sorted(self.stats["fields_extracted"].items(), key=lambda x: x[1], reverse=True)
        for field, count in sorted_fields[:15]:
            coverage = (count / max(1, self.stats["papers_enriched"])) * 100
            print(f"  {field}: {count} papers ({coverage:.1f}%)")

        print(f"\nReport: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Comprehensive CrossRef enrichment extracting ALL fields")
    parser.add_argument(
        "--input", default="comprehensive_extraction_20250831_211114", help="Input directory with JSON files"
    )
    parser.add_argument(
        "--output", default="crossref_comprehensive", help="Output directory for enriched files"
    )
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process (for testing)")
    parser.add_argument(
        "--mailto",
        default=CROSSREF_POLITE_EMAIL,
        help="Email for CrossRef polite pool access (better performance)",
    )

    args = parser.parse_args()

    # Create enricher with polite pool access
    enricher = ComprehensiveCrossRefEnricher(mailto=args.mailto)

    # Process papers
    enricher.process_directory(
        input_dir=Path(args.input), output_dir=Path(args.output), max_papers=args.max_papers
    )


if __name__ == "__main__":
    main()
