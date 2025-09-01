#!/usr/bin/env python3
"""Zotero Metadata Recovery Script
Recovers missing metadata from local Zotero library before attempting API calls.
This is Stage 3 in the v5 extraction pipeline.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from pyzotero import zotero
import re
from collections import defaultdict


class ZoteroMetadataRecovery:
    def __init__(self, library_id: str, library_type: str = "user", api_key: str = None):
        """Initialize Zotero connection.

        Args:
            library_id: Zotero library ID
            library_type: 'user' or 'group'
            api_key: Zotero API key (optional for local library)
        """
        self.library_id = library_id
        self.library_type = library_type
        self.api_key = api_key
        self.zot = None
        self.items_cache = {}
        self.stats = defaultdict(int)

    def connect(self):
        """Establish connection to Zotero library."""
        try:
            self.zot = zotero.Zotero(self.library_id, self.library_type, self.api_key)
            # Test connection
            self.zot.num_items()
            print(f"✓ Connected to Zotero library {self.library_id}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Zotero: {e}")
            return False

    def load_zotero_items(self):
        """Load all items from Zotero library into cache."""
        print("Loading Zotero library items...")
        try:
            items = self.zot.everything(self.zot.items())
            print(f"Loaded {len(items)} items from Zotero")

            # Index by various identifiers
            for item in items:
                # Index by key
                key = item.get("key")
                if key:
                    self.items_cache[key] = item

                # Index by title (lowercase for matching)
                title = item.get("data", {}).get("title")
                if title:
                    self.items_cache[title.lower()] = item

                # Index by DOI
                doi = item.get("data", {}).get("DOI")
                if doi:
                    self.items_cache[doi.lower()] = item
                    # Also index without URL prefix
                    if doi.startswith("http"):
                        doi_clean = re.sub(r"https?://doi.org/", "", doi)
                        self.items_cache[doi_clean.lower()] = item

            return True
        except Exception as e:
            print(f"Error loading Zotero items: {e}")
            return False

    def find_zotero_item(self, paper_data: dict) -> dict | None:
        """Find matching Zotero item for a paper.

        Matching strategies:
        1. By paper ID (if it matches Zotero key)
        2. By DOI (exact match)
        3. By title (fuzzy match)
        4. By filename (if stored in attachments)
        """
        # Try by paper ID (might be Zotero key)
        paper_id = paper_data.get("paper_id", "")
        if paper_id in self.items_cache:
            return self.items_cache[paper_id]

        # Try by DOI
        doi = paper_data.get("doi")
        if doi:
            doi_lower = doi.lower()
            if doi_lower in self.items_cache:
                return self.items_cache[doi_lower]

        # Try by title (exact match first)
        title = paper_data.get("title")
        if title:
            title_lower = title.lower()
            if title_lower in self.items_cache:
                return self.items_cache[title_lower]

            # Fuzzy title match (first 50 chars)
            title_prefix = title_lower[:50]
            for key, item in self.items_cache.items():
                if isinstance(key, str) and key.startswith(title_prefix):
                    return item

        # Try by filename in attachments
        filename = paper_data.get("filename", f"{paper_id}.pdf")
        for item in self.items_cache.values():
            if isinstance(item, dict):
                attachments = item.get("data", {}).get("relations", {}).get("attachments", [])
                for attachment in attachments:
                    if filename in str(attachment):
                        return item

        return None

    def extract_year(self, date_str: str) -> str | None:
        """Extract year from various date formats."""
        if not date_str:
            return None

        # Try to find 4-digit year
        year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if year_match:
            return year_match.group(0)

        return None

    def format_authors(self, creators: list[dict]) -> list[dict]:
        """Format Zotero creators into standard author format."""
        authors = []
        for creator in creators:
            if creator.get("creatorType") in ["author", "contributor"]:
                author = {"name": f"{creator.get('firstName', '')} {creator.get('lastName', '')}".strip()}
                if not author["name"]:
                    author["name"] = creator.get("name", "")
                if author["name"]:
                    authors.append(author)
        return authors

    def recover_metadata(self, paper_data: dict) -> dict:
        """Recover missing metadata from Zotero.

        Returns:
            Dict with recovered fields and recovery stats
        """
        recovered = {}
        recovery_source = {}

        # Find matching Zotero item
        zotero_item = self.find_zotero_item(paper_data)

        if not zotero_item:
            self.stats["no_match"] += 1
            return {"recovered": recovered, "source": recovery_source}

        self.stats["matched"] += 1
        zotero_data = zotero_item.get("data", {})

        # Recover title
        if not paper_data.get("title") and zotero_data.get("title"):
            recovered["title"] = zotero_data["title"]
            recovery_source["title"] = "zotero"
            self.stats["title_recovered"] += 1

        # Recover DOI
        if not paper_data.get("doi") and zotero_data.get("DOI"):
            doi = zotero_data["DOI"]
            # Clean DOI
            doi = re.sub(r"https?://doi.org/", "", doi)
            recovered["doi"] = doi
            recovery_source["doi"] = "zotero"
            self.stats["doi_recovered"] += 1

        # Recover year
        if not paper_data.get("year") and zotero_data.get("date"):
            year = self.extract_year(zotero_data["date"])
            if year:
                recovered["year"] = year
                recovery_source["year"] = "zotero"
                self.stats["year_recovered"] += 1

        # Recover authors
        if (not paper_data.get("authors") or len(paper_data.get("authors", [])) == 0) and zotero_data.get(
            "creators"
        ):
            authors = self.format_authors(zotero_data["creators"])
            if authors:
                recovered["authors"] = authors
                recovery_source["authors"] = "zotero"
                self.stats["authors_recovered"] += 1

        # Recover journal
        if not paper_data.get("journal") and zotero_data.get("publicationTitle"):
            recovered["journal"] = zotero_data["publicationTitle"]
            recovery_source["journal"] = "zotero"
            self.stats["journal_recovered"] += 1

        # Recover abstract (if available)
        if not paper_data.get("abstract") and zotero_data.get("abstractNote"):
            recovered["abstract"] = zotero_data["abstractNote"]
            recovery_source["abstract"] = "zotero"
            self.stats["abstract_recovered"] += 1

        # Add tags/keywords
        if zotero_data.get("tags"):
            tags = [tag.get("tag") for tag in zotero_data["tags"] if tag.get("tag")]
            if tags:
                recovered["keywords"] = tags
                recovery_source["keywords"] = "zotero"
                self.stats["keywords_recovered"] += 1

        # Add other useful fields
        if zotero_data.get("volume"):
            recovered["volume"] = zotero_data["volume"]
        if zotero_data.get("issue"):
            recovered["issue"] = zotero_data["issue"]
        if zotero_data.get("pages"):
            recovered["pages"] = zotero_data["pages"]
        if zotero_data.get("ISSN"):
            recovered["issn"] = zotero_data["ISSN"]
        if zotero_data.get("ISBN"):
            recovered["isbn"] = zotero_data["ISBN"]
        if zotero_data.get("url"):
            recovered["url"] = zotero_data["url"]

        return {
            "recovered": recovered,
            "source": recovery_source,
            "zotero_item_type": zotero_data.get("itemType", "unknown"),
        }

    def process_paper(self, json_file: Path) -> dict:
        """Process a single paper JSON file."""
        try:
            with open(json_file, encoding="utf-8") as f:
                paper_data = json.load(f)

            # Check what's missing
            missing_fields = []
            critical_fields = ["title", "doi", "year", "authors", "journal"]

            for field in critical_fields:
                if not paper_data.get(field):
                    missing_fields.append(field)

            if not missing_fields:
                self.stats["complete"] += 1
                return paper_data

            self.stats["incomplete"] += 1

            # Attempt recovery
            recovery_result = self.recover_metadata(paper_data)

            # Merge recovered data
            if recovery_result["recovered"]:
                for field, value in recovery_result["recovered"].items():
                    if field not in paper_data or not paper_data[field]:
                        paper_data[field] = value

                # Add recovery metadata
                paper_data["zotero_recovery"] = {
                    "fields_recovered": list(recovery_result["recovered"].keys()),
                    "recovery_source": recovery_result["source"],
                    "zotero_item_type": recovery_result["zotero_item_type"],
                    "timestamp": datetime.now().isoformat(),
                }

                self.stats["papers_improved"] += 1

            return paper_data

        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            self.stats["errors"] += 1
            return None

    def process_directory(self, input_dir: Path, output_dir: Path, max_papers: int | None = None):
        """Process all JSON files in directory."""
        output_dir.mkdir(parents=True, exist_ok=True)

        json_files = list(input_dir.glob("*.json"))
        if max_papers:
            json_files = json_files[:max_papers]

        print(f"\nProcessing {len(json_files)} papers...")
        print("=" * 80)

        for i, json_file in enumerate(json_files, 1):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(json_files)} papers processed...")

            # Process paper
            updated_paper = self.process_paper(json_file)

            if updated_paper:
                # Save updated paper
                output_file = output_dir / json_file.name
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(updated_paper, f, indent=2)

        self.print_statistics()
        self.save_report(output_dir)

    def print_statistics(self):
        """Print recovery statistics."""
        print("\n" + "=" * 80)
        print("ZOTERO RECOVERY STATISTICS")
        print("=" * 80)

        print(f"Total papers processed: {self.stats['complete'] + self.stats['incomplete']}")
        print(f"  - Already complete: {self.stats['complete']}")
        print(f"  - Missing metadata: {self.stats['incomplete']}")
        print(f"  - Matched in Zotero: {self.stats['matched']}")
        print(f"  - No Zotero match: {self.stats['no_match']}")
        print(f"  - Papers improved: {self.stats['papers_improved']}")
        print(f"  - Processing errors: {self.stats['errors']}")

        print("\nFields Recovered:")
        print(f"  - Titles: {self.stats['title_recovered']}")
        print(f"  - DOIs: {self.stats['doi_recovered']}")
        print(f"  - Years: {self.stats['year_recovered']}")
        print(f"  - Authors: {self.stats['authors_recovered']}")
        print(f"  - Journals: {self.stats['journal_recovered']}")
        print(f"  - Abstracts: {self.stats['abstract_recovered']}")
        print(f"  - Keywords: {self.stats['keywords_recovered']}")

        if self.stats["incomplete"] > 0:
            recovery_rate = (self.stats["papers_improved"] / self.stats["incomplete"]) * 100
            print(f"\nOverall recovery rate: {recovery_rate:.1f}%")

    def save_report(self, output_dir: Path):
        """Save detailed recovery report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": dict(self.stats),
            "summary": {
                "total_processed": self.stats["complete"] + self.stats["incomplete"],
                "papers_improved": self.stats["papers_improved"],
                "recovery_rate": (self.stats["papers_improved"] / max(self.stats["incomplete"], 1)) * 100,
            },
        }

        report_file = output_dir / "zotero_recovery_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Recover missing metadata from Zotero library")
    parser.add_argument("--input", type=str, required=True, help="Input directory with JSON files")
    parser.add_argument("--output", type=str, required=True, help="Output directory for recovered files")
    parser.add_argument("--library-id", type=str, required=True, help="Zotero library ID")
    parser.add_argument(
        "--library-type", type=str, default="user", choices=["user", "group"], help="Zotero library type"
    )
    parser.add_argument("--api-key", type=str, help="Zotero API key (optional for local library)")
    parser.add_argument("--max-papers", type=int, help="Maximum number of papers to process (for testing)")

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} does not exist")
        return

    # Initialize recovery system
    recovery = ZoteroMetadataRecovery(
        library_id=args.library_id, library_type=args.library_type, api_key=args.api_key
    )

    # Connect to Zotero
    if not recovery.connect():
        print("Failed to connect to Zotero. Please check your credentials.")
        return

    # Load Zotero items
    if not recovery.load_zotero_items():
        print("Failed to load Zotero library items.")
        return

    # Process papers
    recovery.process_directory(input_dir, output_dir, args.max_papers)

    print("\n✓ Zotero metadata recovery complete!")


if __name__ == "__main__":
    main()
