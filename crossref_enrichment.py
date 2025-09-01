#!/usr/bin/env python3
"""Enhanced CrossRef Enrichment - Finds and fills missing metadata.

This script enriches paper metadata by querying CrossRef API to find:
- Missing DOIs (primary goal)
- Missing years/dates
- Missing or incomplete titles
- Missing authors
- Missing journal information
- Additional metadata (citations, venue info, etc.)

Usage:
    python crossref_enrichment.py [--input DIR] [--output DIR] [--max-papers N]
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime, UTC
import argparse
import sys

# Try to import habanero (CrossRef client)
try:
    from habanero import Crossref
except ImportError:
    print("ERROR: habanero package not installed!")
    print("Install with: pip install habanero")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EnhancedCrossRefEnricher:
    """Enhanced CrossRef enrichment with comprehensive metadata recovery."""

    def __init__(self, input_dir: str = None, output_dir: str = None, max_papers: int = None):
        """Initialize the enricher.

        Args:
            input_dir: Directory containing JSON files to enrich
            output_dir: Directory to save enriched files
            max_papers: Maximum number of papers to process (for testing)
        """
        # Find latest extraction if not specified
        if not input_dir:
            extraction_dirs = sorted(Path(".").glob("comprehensive_extraction_*"))
            if not extraction_dirs:
                extraction_dirs = sorted(Path(".").glob("kb_*"))
            if not extraction_dirs:
                raise ValueError("No extraction directory found! Specify with --input")
            input_dir = str(extraction_dirs[-1])

        self.input_dir = Path(input_dir)
        if not self.input_dir.exists():
            raise ValueError(f"Input directory not found: {input_dir}")

        # Setup output directory
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_dir) if output_dir else Path(f"crossref_enriched_{timestamp}")
        self.output_dir.mkdir(exist_ok=True)

        self.max_papers = max_papers
        self.cr = Crossref()

        # Statistics tracking
        self.stats = {
            "total_processed": 0,
            "api_queries": 0,
            "dois_found": 0,
            "dois_already_present": 0,
            "years_found": 0,
            "years_already_present": 0,
            "titles_enriched": 0,
            "authors_enriched": 0,
            "journals_found": 0,
            "journals_already_present": 0,
            "api_errors": 0,
            "papers_needing_enrichment": [],
            "papers_enriched": [],
            "papers_failed": [],
        }

    def query_crossref(self, paper_data: dict) -> dict | None:
        """Query CrossRef API to find paper metadata.

        Tries multiple strategies:
        1. If DOI exists, query by DOI for full metadata
        2. If title + authors exist, search by bibliographic info
        3. If only title exists, search by title

        Args:
            paper_data: Dictionary with paper metadata

        Returns:
            CrossRef metadata if found, None otherwise
        """
        self.stats["api_queries"] += 1

        # Strategy 1: Query by DOI if available
        doi = paper_data.get("doi", "").strip()
        if doi:
            try:
                time.sleep(0.1)  # Rate limiting
                result = self.cr.works(ids=doi)
                if result and "message" in result:
                    return result["message"]
            except Exception as e:
                logger.debug(f"DOI query failed for {doi}: {e}")

        # Strategy 2: Search by title + authors
        title = paper_data.get("title", "").strip()
        if not title:
            return None

        # Build query
        query_parts = []

        # Add title (cleaned)
        clean_title = title.replace("\n", " ").replace("  ", " ")[:256]
        query_parts.append(clean_title)

        # Add first author if available
        authors = paper_data.get("authors", [])
        if authors and isinstance(authors, list) and len(authors) > 0:
            first_author = authors[0]
            if isinstance(first_author, dict):
                surname = first_author.get("surname", "")
                given = first_author.get("given", "")
                if surname:
                    query_parts.append(surname)
                    if given:
                        query_parts.append(given)
            elif isinstance(first_author, str):
                query_parts.append(first_author.split(",")[0])

        # Add year if available
        year = paper_data.get("year")
        if year:
            query_parts.append(str(year))

        # Add journal if available
        journal = paper_data.get("publication", {}).get("journal", "")
        if journal:
            query_parts.append(journal)

        # Perform search
        try:
            time.sleep(0.15)  # Slightly longer delay for searches
            query = " ".join(query_parts)

            # Search with different parameters based on what we have
            if year and authors:
                # Most specific search
                results = self.cr.works(
                    query=clean_title,
                    filter={"from-pub-date": f"{year}-01-01", "until-pub-date": f"{year}-12-31"},
                    limit=5,
                )
            else:
                # General search
                results = self.cr.works(query=query, limit=5)

            if results and "message" in results and "items" in results["message"]:
                items = results["message"]["items"]
                if items:
                    # Find best match by title similarity
                    best_match = self.find_best_match(title, items)
                    if best_match:
                        return best_match

        except Exception as e:
            logger.debug(f"CrossRef search failed: {e}")
            self.stats["api_errors"] += 1

        return None

    def find_best_match(self, original_title: str, items: list[dict]) -> dict | None:
        """Find best matching paper from CrossRef results.

        Args:
            original_title: The original paper title
            items: List of CrossRef search results

        Returns:
            Best matching item or None
        """
        if not items:
            return None

        # Normalize title for comparison
        def normalize(text: str) -> str:
            return text.lower().replace(" ", "").replace("-", "").replace(":", "").replace(",", "")

        original_normalized = normalize(original_title)

        best_match = None
        best_score = 0.0

        for item in items:
            cr_titles = item.get("title", [])
            if not cr_titles:
                continue

            cr_title = cr_titles[0] if isinstance(cr_titles, list) else cr_titles
            cr_normalized = normalize(cr_title)

            # Calculate similarity
            if cr_normalized == original_normalized:
                return item  # Exact match

            # Fuzzy matching - check if one contains the other
            if original_normalized in cr_normalized or cr_normalized in original_normalized:
                score = min(len(original_normalized), len(cr_normalized)) / max(
                    len(original_normalized), len(cr_normalized)
                )
                if score > best_score:
                    best_score = score
                    best_match = item

        # Return best match if similarity is high enough
        if best_score > 0.8:
            return best_match

        return None

    def extract_metadata(self, cr_data: dict) -> dict:
        """Extract all useful metadata from CrossRef response.

        Args:
            cr_data: CrossRef API response data

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}

        # DOI
        if "DOI" in cr_data:
            metadata["doi"] = cr_data["DOI"]

        # Title
        if "title" in cr_data:
            titles = cr_data["title"]
            if isinstance(titles, list) and titles:
                metadata["title"] = titles[0]
            elif isinstance(titles, str):
                metadata["title"] = titles

        # Year (multiple possible sources)
        year = None
        if "published-print" in cr_data:
            date_parts = cr_data["published-print"].get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
        elif "published-online" in cr_data:
            date_parts = cr_data["published-online"].get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
        elif "issued" in cr_data:
            date_parts = cr_data["issued"].get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
        elif "created" in cr_data:
            date_parts = cr_data["created"].get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]

        if year:
            metadata["year"] = str(year)

        # Journal/Publication
        journal_info = {}
        if "container-title" in cr_data:
            titles = cr_data["container-title"]
            if isinstance(titles, list) and titles:
                journal_info["journal"] = titles[0]
            elif isinstance(titles, str):
                journal_info["journal"] = titles

        if "publisher" in cr_data:
            journal_info["publisher"] = cr_data["publisher"]

        if "ISSN" in cr_data:
            journal_info["issn"] = cr_data["ISSN"]

        if "volume" in cr_data:
            journal_info["volume"] = cr_data["volume"]

        if "issue" in cr_data:
            journal_info["issue"] = cr_data["issue"]

        if "page" in cr_data:
            journal_info["pages"] = cr_data["page"]

        if journal_info:
            metadata["publication"] = journal_info

        # Authors
        if "author" in cr_data:
            authors = []
            for author in cr_data["author"]:
                author_dict = {}
                if "given" in author:
                    author_dict["given"] = author["given"]
                if "family" in author:
                    author_dict["surname"] = author["family"]
                if "ORCID" in author:
                    author_dict["orcid"] = author["ORCID"]

                if author_dict:
                    authors.append(author_dict)

            if authors:
                metadata["authors"] = authors

        # Additional metadata
        if "is-referenced-by-count" in cr_data:
            metadata["citation_count"] = cr_data["is-referenced-by-count"]

        if "type" in cr_data:
            metadata["publication_type"] = cr_data["type"]

        if "URL" in cr_data:
            metadata["url"] = cr_data["URL"]

        if "abstract" in cr_data:
            metadata["abstract"] = cr_data["abstract"]

        return metadata

    def enrich_paper(self, paper_file: Path) -> bool:
        """Enrich a single paper with CrossRef metadata.

        Args:
            paper_file: Path to paper JSON file

        Returns:
            True if enriched, False otherwise
        """
        try:
            # Load paper data
            with open(paper_file) as f:
                paper_data = json.load(f)

            # Check what's missing
            needs_enrichment = False
            missing_fields = []

            if not paper_data.get("doi"):
                needs_enrichment = True
                missing_fields.append("doi")

            if not paper_data.get("year"):
                needs_enrichment = True
                missing_fields.append("year")

            if not paper_data.get("title"):
                needs_enrichment = True
                missing_fields.append("title")

            if not paper_data.get("authors"):
                needs_enrichment = True
                missing_fields.append("authors")

            if not paper_data.get("publication", {}).get("journal"):
                needs_enrichment = True
                missing_fields.append("journal")

            if not needs_enrichment:
                # Already complete - just copy
                output_file = self.output_dir / paper_file.name
                with open(output_file, "w") as f:
                    json.dump(paper_data, f, indent=2)

                if paper_data.get("doi"):
                    self.stats["dois_already_present"] += 1
                if paper_data.get("year"):
                    self.stats["years_already_present"] += 1
                if paper_data.get("publication", {}).get("journal"):
                    self.stats["journals_already_present"] += 1

                return False

            # Track paper needing enrichment
            self.stats["papers_needing_enrichment"].append(
                {"file": paper_file.name, "missing": missing_fields}
            )

            # Query CrossRef
            cr_data = self.query_crossref(paper_data)

            if cr_data:
                # Extract metadata
                new_metadata = self.extract_metadata(cr_data)

                # Merge with existing data (don't overwrite existing good data)
                enriched = False

                # DOI
                if not paper_data.get("doi") and new_metadata.get("doi"):
                    paper_data["doi"] = new_metadata["doi"]
                    self.stats["dois_found"] += 1
                    enriched = True
                elif paper_data.get("doi"):
                    self.stats["dois_already_present"] += 1

                # Year
                if not paper_data.get("year") and new_metadata.get("year"):
                    paper_data["year"] = new_metadata["year"]
                    self.stats["years_found"] += 1
                    enriched = True
                elif paper_data.get("year"):
                    self.stats["years_already_present"] += 1

                # Title
                if not paper_data.get("title") and new_metadata.get("title"):
                    paper_data["title"] = new_metadata["title"]
                    self.stats["titles_enriched"] += 1
                    enriched = True

                # Authors
                if not paper_data.get("authors") and new_metadata.get("authors"):
                    paper_data["authors"] = new_metadata["authors"]
                    self.stats["authors_enriched"] += 1
                    enriched = True

                # Journal/Publication
                if new_metadata.get("publication"):
                    if not paper_data.get("publication"):
                        paper_data["publication"] = {}

                    # Merge publication info
                    for key, value in new_metadata["publication"].items():
                        if not paper_data["publication"].get(key):
                            paper_data["publication"][key] = value

                    if new_metadata["publication"].get("journal"):
                        if not paper_data.get("publication", {}).get("journal"):
                            self.stats["journals_found"] += 1
                        else:
                            self.stats["journals_already_present"] += 1
                        enriched = True

                # Additional metadata
                if new_metadata.get("citation_count"):
                    paper_data["crossref_citations"] = new_metadata["citation_count"]

                if new_metadata.get("publication_type"):
                    paper_data["publication_type"] = new_metadata["publication_type"]

                if new_metadata.get("url"):
                    paper_data["crossref_url"] = new_metadata["url"]

                # Mark as enriched
                if enriched:
                    paper_data["crossref_enriched"] = True
                    paper_data["crossref_enrichment_date"] = datetime.now(UTC).isoformat()
                    self.stats["papers_enriched"].append(paper_file.name)
            else:
                # No match found
                self.stats["papers_failed"].append(paper_file.name)

            # Save enriched data
            output_file = self.output_dir / paper_file.name
            with open(output_file, "w") as f:
                json.dump(paper_data, f, indent=2)

            return cr_data is not None

        except Exception as e:
            logger.error(f"Error enriching {paper_file.name}: {e}")
            self.stats["papers_failed"].append(paper_file.name)

            # Copy original file on error
            try:
                output_file = self.output_dir / paper_file.name
                with open(paper_file) as f:
                    data = json.load(f)
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
            except:
                pass

            return False

    def run(self):
        """Run the enrichment process on all papers."""
        # Find JSON files
        json_files = sorted(self.input_dir.glob("*.json"))

        # Filter out report files
        json_files = [f for f in json_files if "report" not in f.name.lower()]

        if self.max_papers:
            json_files = json_files[: self.max_papers]

        total_files = len(json_files)
        logger.info(f"Found {total_files} papers to process")
        logger.info(f"Input: {self.input_dir}")
        logger.info(f"Output: {self.output_dir}")

        # Process each file
        for i, json_file in enumerate(json_files, 1):
            if i % 100 == 0:
                logger.info(f"Processing {i}/{total_files}...")
                logger.info(f"  DOIs found: {self.stats['dois_found']}")
                logger.info(f"  Years found: {self.stats['years_found']}")
                logger.info(f"  Journals found: {self.stats['journals_found']}")

            self.enrich_paper(json_file)
            self.stats["total_processed"] += 1

            # Rate limiting
            if i % 10 == 0:
                time.sleep(0.5)  # Extra delay every 10 papers

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate enrichment report."""
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "input_directory": str(self.input_dir),
            "output_directory": str(self.output_dir),
            "statistics": {
                "total_processed": self.stats["total_processed"],
                "api_queries": self.stats["api_queries"],
                "api_errors": self.stats["api_errors"],
                "papers_needing_enrichment": len(self.stats["papers_needing_enrichment"]),
                "papers_enriched": len(self.stats["papers_enriched"]),
                "papers_failed": len(self.stats["papers_failed"]),
            },
            "enrichment_results": {
                "dois": {
                    "found": self.stats["dois_found"],
                    "already_present": self.stats["dois_already_present"],
                    "total": self.stats["dois_found"] + self.stats["dois_already_present"],
                    "coverage": f"{(self.stats['dois_found'] + self.stats['dois_already_present']) / self.stats['total_processed'] * 100:.1f}%",
                },
                "years": {
                    "found": self.stats["years_found"],
                    "already_present": self.stats["years_already_present"],
                    "total": self.stats["years_found"] + self.stats["years_already_present"],
                    "coverage": f"{(self.stats['years_found'] + self.stats['years_already_present']) / self.stats['total_processed'] * 100:.1f}%",
                },
                "journals": {
                    "found": self.stats["journals_found"],
                    "already_present": self.stats["journals_already_present"],
                    "total": self.stats["journals_found"] + self.stats["journals_already_present"],
                    "coverage": f"{(self.stats['journals_found'] + self.stats['journals_already_present']) / self.stats['total_processed'] * 100:.1f}%",
                },
                "titles_enriched": self.stats["titles_enriched"],
                "authors_enriched": self.stats["authors_enriched"],
            },
            "sample_enrichments": self.stats["papers_enriched"][:10],
            "sample_failures": self.stats["papers_failed"][:10],
        }

        # Save JSON report
        report_path = self.output_dir / "crossref_enrichment_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        # Save markdown report
        md_report = f"""# CrossRef Enrichment Report

**Date**: {report["timestamp"]}
**Input**: {report["input_directory"]}
**Output**: {report["output_directory"]}

## Summary

- **Total Papers**: {report["statistics"]["total_processed"]}
- **Papers Needing Enrichment**: {report["statistics"]["papers_needing_enrichment"]}
- **Successfully Enriched**: {report["statistics"]["papers_enriched"]}
- **Failed to Enrich**: {report["statistics"]["papers_failed"]}
- **API Queries**: {report["statistics"]["api_queries"]}
- **API Errors**: {report["statistics"]["api_errors"]}

## Enrichment Results

### DOIs
- **Found via CrossRef**: {report["enrichment_results"]["dois"]["found"]}
- **Already Present**: {report["enrichment_results"]["dois"]["already_present"]}
- **Total Coverage**: {report["enrichment_results"]["dois"]["coverage"]}

### Years
- **Found via CrossRef**: {report["enrichment_results"]["years"]["found"]}
- **Already Present**: {report["enrichment_results"]["years"]["already_present"]}
- **Total Coverage**: {report["enrichment_results"]["years"]["coverage"]}

### Journals
- **Found via CrossRef**: {report["enrichment_results"]["journals"]["found"]}
- **Already Present**: {report["enrichment_results"]["journals"]["already_present"]}
- **Total Coverage**: {report["enrichment_results"]["journals"]["coverage"]}

### Other Metadata
- **Titles Enriched**: {report["enrichment_results"]["titles_enriched"]}
- **Authors Enriched**: {report["enrichment_results"]["authors_enriched"]}

## Next Steps

1. Review enriched data: `ls {report["output_directory"]}/*.json | head | xargs -I {{}} python -m json.tool {{}} | head -50`
2. Run non-article filtering: `python filter_non_articles.py --input {report["output_directory"]}`
3. Fix malformed DOIs: `python fix_malformed_dois.py --input {report["output_directory"]}`
4. Build final KB: `python src/build_kb.py --input {report["output_directory"]}`
"""

        md_path = self.output_dir / "crossref_enrichment_report.md"
        with open(md_path, "w") as f:
            f.write(md_report)

        # Print summary
        print("=" * 70)
        print("CROSSREF ENRICHMENT COMPLETE")
        print("=" * 70)
        print(f"Total processed: {report['statistics']['total_processed']}")
        print(f"Papers enriched: {report['statistics']['papers_enriched']}")
        print("\nMetadata Coverage:")
        print(f"  DOIs: {report['enrichment_results']['dois']['coverage']}")
        print(f"  Years: {report['enrichment_results']['years']['coverage']}")
        print(f"  Journals: {report['enrichment_results']['journals']['coverage']}")
        print(f"\nOutput: {self.output_dir}")
        print(f"Report: {report_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Enhanced CrossRef enrichment for paper metadata")
    parser.add_argument("--input", help="Input directory with JSON files")
    parser.add_argument("--output", help="Output directory for enriched files")
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process (for testing)")

    args = parser.parse_args()

    try:
        enricher = EnhancedCrossRefEnricher(
            input_dir=args.input, output_dir=args.output, max_papers=args.max_papers
        )
        enricher.run()
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
