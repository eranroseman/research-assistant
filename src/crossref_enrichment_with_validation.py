#!/usr/bin/env python3
"""Enhanced CrossRef enrichment with validation of existing metadata.

This version not only fills missing fields but also validates and optionally
corrects existing metadata against CrossRef's authoritative data.
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
import argparse
from dataclasses import dataclass
from difflib import SequenceMatcher

try:
    from habanero import Crossref
except ImportError:
    print("ERROR: habanero package not installed!")
    print("Install with: pip install habanero")
    exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Results from validating existing metadata."""

    field: str
    original_value: any
    crossref_value: any
    similarity: float
    action: str  # 'keep', 'update', 'flag'
    reason: str


class CrossRefEnricherWithValidation:
    """Enhanced enricher that validates existing metadata."""

    def __init__(self, validate_existing: bool = True, update_threshold: float = 0.8):
        """Initialize enricher.

        Args:
            validate_existing: Whether to validate existing fields
            update_threshold: Similarity threshold below which to flag discrepancies
        """
        self.cr = Crossref()
        self.validate_existing = validate_existing
        self.update_threshold = update_threshold
        self.stats = {
            "total_processed": 0,
            "api_queries": 0,
            "api_errors": 0,
            "papers_enriched": 0,
            "papers_validated": 0,
            "validation_discrepancies": 0,
            "fields_updated": 0,
            "fields_added": 0,
        }
        self.validation_log = []

    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        if not str1 or not str2:
            return 0.0
        str1_lower = str1.lower().strip()
        str2_lower = str2.lower().strip()
        return SequenceMatcher(None, str1_lower, str2_lower).ratio()

    def validate_field(self, field_name: str, original: any, crossref: any) -> ValidationResult:
        """Validate a single field against CrossRef data.

        Returns:
            ValidationResult with recommendation
        """
        # Handle missing values
        if not original:
            return ValidationResult(
                field=field_name,
                original_value=original,
                crossref_value=crossref,
                similarity=0.0,
                action="update" if crossref else "keep",
                reason="Missing original value",
            )

        if not crossref:
            return ValidationResult(
                field=field_name,
                original_value=original,
                crossref_value=crossref,
                similarity=1.0,
                action="keep",
                reason="No CrossRef value available",
            )

        # Field-specific validation
        if field_name == "year":
            # Years should match exactly
            if str(original) == str(crossref):
                return ValidationResult(
                    field=field_name,
                    original_value=original,
                    crossref_value=crossref,
                    similarity=1.0,
                    action="keep",
                    reason="Years match",
                )
            return ValidationResult(
                field=field_name,
                original_value=original,
                crossref_value=crossref,
                similarity=0.0,
                action="flag",
                reason=f"Year mismatch: {original} vs {crossref}",
            )

        if field_name == "doi":
            # DOIs should match exactly (case-insensitive)
            orig_doi = str(original).lower().strip()
            cr_doi = str(crossref).lower().strip()
            if orig_doi == cr_doi:
                return ValidationResult(
                    field=field_name,
                    original_value=original,
                    crossref_value=crossref,
                    similarity=1.0,
                    action="keep",
                    reason="DOIs match",
                )
            return ValidationResult(
                field=field_name,
                original_value=original,
                crossref_value=crossref,
                similarity=0.0,
                action="flag",
                reason="DOI mismatch",
            )

        if field_name == "title":
            # Titles can have minor variations
            similarity = self.similarity_score(original, crossref)
            if similarity >= self.update_threshold:
                return ValidationResult(
                    field=field_name,
                    original_value=original,
                    crossref_value=crossref,
                    similarity=similarity,
                    action="keep",
                    reason=f"Titles similar enough ({similarity:.2%})",
                )
            return ValidationResult(
                field=field_name,
                original_value=original,
                crossref_value=crossref,
                similarity=similarity,
                action="flag",
                reason=f"Title similarity low ({similarity:.2%})",
            )

        if field_name == "journal":
            # Journals can have abbreviations and variations
            similarity = self.similarity_score(original, crossref)
            if similarity >= 0.7:  # Lower threshold for journals
                return ValidationResult(
                    field=field_name,
                    original_value=original,
                    crossref_value=crossref,
                    similarity=similarity,
                    action="keep",
                    reason=f"Journals match ({similarity:.2%})",
                )
            # Check if one is abbreviation of the other
            if (
                original.replace(".", "").lower() in crossref.lower()
                or crossref.replace(".", "").lower() in original.lower()
            ):
                return ValidationResult(
                    field=field_name,
                    original_value=original,
                    crossref_value=crossref,
                    similarity=similarity,
                    action="keep",
                    reason="Journal abbreviation detected",
                )
            return ValidationResult(
                field=field_name,
                original_value=original,
                crossref_value=crossref,
                similarity=similarity,
                action="flag",
                reason=f"Journal mismatch ({similarity:.2%})",
            )

        if field_name == "authors":
            # Compare author counts
            orig_count = len(original) if isinstance(original, list) else 0
            cr_count = len(crossref) if isinstance(crossref, list) else 0

            if orig_count == 0:
                return ValidationResult(
                    field=field_name,
                    original_value=original,
                    crossref_value=crossref,
                    similarity=0.0,
                    action="update",
                    reason="No original authors",
                )

            if abs(orig_count - cr_count) <= 2:  # Allow small differences
                return ValidationResult(
                    field=field_name,
                    original_value=f"{orig_count} authors",
                    crossref_value=f"{cr_count} authors",
                    similarity=1.0 - abs(orig_count - cr_count) / max(orig_count, cr_count),
                    action="keep",
                    reason=f"Author counts similar ({orig_count} vs {cr_count})",
                )
            return ValidationResult(
                field=field_name,
                original_value=f"{orig_count} authors",
                crossref_value=f"{cr_count} authors",
                similarity=0.0,
                action="flag",
                reason=f"Author count mismatch ({orig_count} vs {cr_count})",
            )

        # Default validation
        return ValidationResult(
            field=field_name,
            original_value=original,
            crossref_value=crossref,
            similarity=1.0,
            action="keep",
            reason="No validation rule",
        )

    def query_crossref(self, paper_data: dict) -> dict | None:
        """Query CrossRef API for paper metadata."""
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
        """Find best matching paper from CrossRef results."""
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

            # Calculate similarity
            score = self.similarity_score(original_title, titles[0])

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

    def extract_metadata(self, crossref_data: dict) -> dict:
        """Extract relevant metadata from CrossRef response."""
        metadata = {}

        # Extract DOI
        if "DOI" in crossref_data:
            metadata["doi"] = crossref_data["DOI"]

        # Extract year
        date_parts = crossref_data.get("published-print", {}).get("date-parts")
        if not date_parts:
            date_parts = crossref_data.get("published-online", {}).get("date-parts")
        if not date_parts:
            date_parts = crossref_data.get("issued", {}).get("date-parts")

        if date_parts and len(date_parts) > 0 and len(date_parts[0]) > 0:
            metadata["year"] = date_parts[0][0]

        # Extract title
        titles = crossref_data.get("title", [])
        if titles:
            metadata["title"] = titles[0]

        # Extract authors
        authors = []
        for author in crossref_data.get("author", []):
            name_parts = []
            if "given" in author:
                name_parts.append(author["given"])
            if "family" in author:
                name_parts.append(author["family"])

            if name_parts:
                author_entry = {"name": " ".join(name_parts)}

                # Add affiliation if available
                if author.get("affiliation"):
                    aff = author["affiliation"][0]
                    if "name" in aff:
                        author_entry["affiliation"] = {"organization": aff["name"]}

                authors.append(author_entry)

        if authors:
            metadata["authors"] = authors

        # Extract journal
        journal = crossref_data.get("container-title", [])
        if journal:
            metadata["journal"] = journal[0]

        return metadata

    def enrich_and_validate_paper(
        self, paper_file: Path, output_dir: Path
    ) -> tuple[bool, list[ValidationResult]]:
        """Enrich and validate a single paper.

        Returns:
            Tuple of (was_modified, validation_results)
        """
        try:
            # Load paper data
            with open(paper_file) as f:
                paper_data = json.load(f)

            # Query CrossRef
            crossref_data = self.query_crossref(paper_data)

            if not crossref_data:
                # No CrossRef match found
                # Just copy the file
                output_file = output_dir / paper_file.name
                with open(output_file, "w") as f:
                    json.dump(paper_data, f, indent=2)
                return False, []

            # Extract CrossRef metadata
            new_metadata = self.extract_metadata(crossref_data)

            # Track modifications and validations
            was_modified = False
            validation_results = []

            # Process each field
            fields_to_check = ["doi", "year", "title", "authors", "journal"]

            for field in fields_to_check:
                original_value = paper_data.get(field)
                crossref_value = new_metadata.get(field)

                if field == "journal":
                    original_value = paper_data.get("publication", {}).get("journal")

                # Validate the field
                if self.validate_existing or not original_value:
                    result = self.validate_field(field, original_value, crossref_value)
                    validation_results.append(result)

                    # Apply the action
                    if result.action == "update":
                        if field == "journal":
                            if not paper_data.get("publication"):
                                paper_data["publication"] = {}
                            paper_data["publication"]["journal"] = crossref_value
                        else:
                            paper_data[field] = crossref_value
                        was_modified = True
                        self.stats["fields_added"] += 1

                    elif result.action == "flag":
                        # Add validation warning
                        if "validation_warnings" not in paper_data:
                            paper_data["validation_warnings"] = []
                        paper_data["validation_warnings"].append(
                            {
                                "field": field,
                                "reason": result.reason,
                                "original": str(original_value)[:100],
                                "crossref": str(crossref_value)[:100],
                                "similarity": result.similarity,
                            }
                        )
                        self.stats["validation_discrepancies"] += 1

            # Mark as processed
            if was_modified:
                paper_data["crossref_validated"] = True
                paper_data["validation_timestamp"] = datetime.utcnow().isoformat()
                self.stats["papers_enriched"] += 1

            if validation_results:
                self.stats["papers_validated"] += 1

            # Save enriched/validated paper
            output_file = output_dir / paper_file.name
            with open(output_file, "w") as f:
                json.dump(paper_data, f, indent=2)

            return was_modified, validation_results

        except Exception as e:
            logger.error(f"Error processing {paper_file}: {e}")
            # Copy original file on error
            output_file = output_dir / paper_file.name
            with open(paper_file) as f_in:
                with open(output_file, "w") as f_out:
                    f_out.write(f_in.read())
            return False, []

    def process_directory(self, input_dir: Path, output_dir: Path, max_papers: int | None = None):
        """Process all papers in a directory."""
        # Create output directory
        output_dir.mkdir(exist_ok=True, parents=True)

        # Get all JSON files
        json_files = sorted(input_dir.glob("*.json"))

        if max_papers:
            json_files = json_files[:max_papers]

        logger.info(f"Found {len(json_files)} papers to process")
        logger.info(f"Validation mode: {'ON' if self.validate_existing else 'OFF'}")

        # Process each paper
        for i, paper_file in enumerate(json_files, 1):
            if i % 10 == 0:
                logger.info(f"Processing {i}/{len(json_files)}...")

            was_modified, validation_results = self.enrich_and_validate_paper(paper_file, output_dir)

            # Log significant validations
            for result in validation_results:
                if result.action == "flag":
                    self.validation_log.append(
                        {
                            "paper": paper_file.stem,
                            "field": result.field,
                            "reason": result.reason,
                            "similarity": result.similarity,
                        }
                    )

            self.stats["total_processed"] += 1

            # Rate limiting
            if i % 5 == 0:
                time.sleep(0.5)  # Be nice to CrossRef API

        # Generate report
        self.generate_report(output_dir)

    def generate_report(self, output_dir: Path):
        """Generate enrichment and validation report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": self.stats,
            "validation_enabled": self.validate_existing,
            "update_threshold": self.update_threshold,
            "validation_summary": {
                "total_discrepancies": self.stats["validation_discrepancies"],
                "papers_with_warnings": len(set(v["paper"] for v in self.validation_log)),
                "field_distribution": {},
            },
            "sample_validations": self.validation_log[:20],  # First 20 validations
        }

        # Count discrepancies by field
        for val in self.validation_log:
            field = val["field"]
            if field not in report["validation_summary"]["field_distribution"]:
                report["validation_summary"]["field_distribution"][field] = 0
            report["validation_summary"]["field_distribution"][field] += 1

        # Save report
        report_file = output_dir / "validation_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "=" * 70)
        print("CROSSREF ENRICHMENT AND VALIDATION COMPLETE")
        print("=" * 70)
        print(f"Total processed: {self.stats['total_processed']}")
        print(f"Papers enriched: {self.stats['papers_enriched']}")
        print(f"Papers validated: {self.stats['papers_validated']}")
        print(f"Validation discrepancies: {self.stats['validation_discrepancies']}")
        print(f"Fields added: {self.stats['fields_added']}")
        print(f"\nReport: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Enhanced CrossRef enrichment with validation")
    parser.add_argument(
        "--input", default="comprehensive_extraction_20250831_211114", help="Input directory with JSON files"
    )
    parser.add_argument("--output", default="enriched_validated", help="Output directory for enriched files")
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process (for testing)")
    parser.add_argument(
        "--validate", action="store_true", default=True, help="Validate existing metadata (default: True)"
    )
    parser.add_argument(
        "--no-validate", dest="validate", action="store_false", help="Only add missing fields, no validation"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.8, help="Similarity threshold for validation (0-1)"
    )

    args = parser.parse_args()

    # Create enricher
    enricher = CrossRefEnricherWithValidation(
        validate_existing=args.validate, update_threshold=args.threshold
    )

    # Process papers
    enricher.process_directory(
        input_dir=Path(args.input), output_dir=Path(args.output), max_papers=args.max_papers
    )


if __name__ == "__main__":
    main()
