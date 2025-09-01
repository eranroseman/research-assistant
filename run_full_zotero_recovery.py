#!/usr/bin/env python3
"""Full Zotero metadata recovery for v5 extraction pipeline.
Recovers missing metadata from local Zotero API.
"""

import json
import requests
from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict


def test_zotero_api():
    """Test connection to Zotero's local API."""
    base_url = "http://localhost:23119/api"

    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✓ Connected to Zotero API")
            return True
    except:
        pass

    print("✗ Cannot connect to Zotero. Make sure Zotero is running.")
    return False


def get_all_zotero_items():
    """Get all papers from Zotero with full metadata."""
    base_url = "http://localhost:23119/api"

    all_items = []
    start = 0
    limit = 100

    print("Fetching all items from Zotero...")

    while True:
        try:
            response = requests.get(
                f"{base_url}/users/0/items", params={"start": str(start), "limit": str(limit)}, timeout=10
            )

            if response.status_code != 200:
                break

            batch = response.json()
            if not batch:
                break

            # Filter for papers only
            for item in batch:
                data = item.get("data", {})
                if data.get("itemType") in [
                    "journalArticle",
                    "conferencePaper",
                    "preprint",
                    "book",
                    "bookSection",
                    "thesis",
                    "report",
                ]:
                    all_items.append(item)

            start += len(batch)

        except Exception as e:
            print(f"Error fetching batch: {e}")
            break

    print(f"Found {len(all_items)} papers in Zotero library")
    return all_items


def build_zotero_index(zotero_items):
    """Build lookup indices for Zotero items."""
    by_key = {}
    by_doi = {}
    by_title = {}

    for item in zotero_items:
        key = item.get("key", "")
        data = item.get("data", {})

        # Index by key
        if key:
            by_key[key] = item

        # Index by DOI
        doi = data.get("DOI", "").lower().strip()
        if doi:
            # Clean DOI
            doi = re.sub(r"https?://doi.org/", "", doi)
            by_doi[doi] = item

        # Index by title (first 50 chars, lowercase)
        title = data.get("title", "").lower().strip()
        if title:
            title_key = title[:50]
            by_title[title_key] = item

    return by_key, by_doi, by_title


def extract_year(date_str):
    """Extract year from date string."""
    if not date_str:
        return None
    year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
    if year_match:
        return year_match.group(0)
    return None


def format_authors(creators):
    """Format Zotero creators as author list."""
    authors = []
    for creator in creators:
        if creator.get("creatorType") in ["author", "contributor"]:
            first = creator.get("firstName", "")
            last = creator.get("lastName", "")
            name = f"{first} {last}".strip()
            if not name:
                name = creator.get("name", "")
            if name:
                authors.append({"name": name})
    return authors


def find_zotero_match(paper_data, by_key, by_doi, by_title):
    """Find matching Zotero item for a paper."""
    # Try by DOI first (most reliable)
    paper_doi = paper_data.get("doi", "").lower().strip()
    if paper_doi:
        paper_doi = re.sub(r"https?://doi.org/", "", paper_doi)
        if paper_doi in by_doi:
            return by_doi[paper_doi]

    # Try by title (fuzzy match)
    paper_title = paper_data.get("title", "").lower().strip()
    if paper_title:
        title_key = paper_title[:50]
        if title_key in by_title:
            return by_title[title_key]

    return None


def recover_all_metadata():
    """Main recovery function for all papers."""
    # Check Zotero connection
    if not test_zotero_api():
        return

    # Paths
    input_dir = Path("comprehensive_extraction_20250901_102227")
    output_dir = Path("zotero_recovered_20250901")

    if not input_dir.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Load all extracted papers
    print(f"\nLoading extracted papers from {input_dir}...")
    json_files = list(input_dir.glob("*.json"))
    print(f"Found {len(json_files)} extracted papers")

    # Get all Zotero items and build indices
    zotero_items = get_all_zotero_items()
    if not zotero_items:
        print("No items found in Zotero")
        return

    print("\nBuilding Zotero lookup indices...")
    by_key, by_doi, by_title = build_zotero_index(zotero_items)
    print(f"Indexed: {len(by_key)} keys, {len(by_doi)} DOIs, {len(by_title)} titles")

    # Statistics
    stats = defaultdict(int)
    recovery_details = []

    # Process each paper
    print(f"\nProcessing {len(json_files)} papers...")

    for i, json_file in enumerate(json_files, 1):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(json_files)} papers processed...")

        # Load paper data
        with open(json_file, encoding="utf-8") as f:
            paper_data = json.load(f)

        paper_id = json_file.stem

        # Check what fields are missing
        missing_fields = []
        critical_fields = ["title", "doi", "year", "authors", "journal"]

        for field in critical_fields:
            if not paper_data.get(field):
                missing_fields.append(field)

        if not missing_fields:
            stats["already_complete"] += 1
            # Just copy the file as-is
            output_file = output_dir / json_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(paper_data, f, indent=2)
            continue

        stats["missing_metadata"] += 1

        # Try to find matching Zotero item
        zotero_item = find_zotero_match(paper_data, by_key, by_doi, by_title)

        if zotero_item:
            stats["matched"] += 1
            zotero_data = zotero_item.get("data", {})
            recovered_fields = []

            # Recover missing fields
            if "title" in missing_fields and zotero_data.get("title"):
                paper_data["title"] = zotero_data["title"]
                recovered_fields.append("title")
                stats["title_recovered"] += 1

            if "doi" in missing_fields and zotero_data.get("DOI"):
                doi = zotero_data["DOI"]
                # Clean DOI
                doi = re.sub(r"https?://doi.org/", "", doi)
                paper_data["doi"] = doi
                recovered_fields.append("doi")
                stats["doi_recovered"] += 1

            if "year" in missing_fields and zotero_data.get("date"):
                year = extract_year(zotero_data["date"])
                if year:
                    paper_data["year"] = year
                    recovered_fields.append("year")
                    stats["year_recovered"] += 1

            if "journal" in missing_fields and zotero_data.get("publicationTitle"):
                paper_data["journal"] = zotero_data["publicationTitle"]
                recovered_fields.append("journal")
                stats["journal_recovered"] += 1

            if "authors" in missing_fields and zotero_data.get("creators"):
                authors = format_authors(zotero_data["creators"])
                if authors:
                    paper_data["authors"] = authors
                    recovered_fields.append("authors")
                    stats["authors_recovered"] += 1

            # Also add other useful fields if available
            if not paper_data.get("abstract") and zotero_data.get("abstractNote"):
                paper_data["abstract"] = zotero_data["abstractNote"]
                stats["abstract_recovered"] += 1

            if zotero_data.get("volume"):
                paper_data["volume"] = zotero_data["volume"]

            if zotero_data.get("issue"):
                paper_data["issue"] = zotero_data["issue"]

            if zotero_data.get("pages"):
                paper_data["pages"] = zotero_data["pages"]

            if recovered_fields:
                stats["papers_improved"] += 1
                recovery_details.append(
                    {
                        "paper_id": paper_id,
                        "recovered": recovered_fields,
                        "zotero_item_type": zotero_data.get("itemType"),
                    }
                )

                # Add recovery metadata
                paper_data["zotero_recovery"] = {
                    "fields_recovered": recovered_fields,
                    "timestamp": datetime.now().isoformat(),
                    "zotero_item_type": zotero_data.get("itemType"),
                }
        else:
            stats["no_match"] += 1

        # Save paper (whether recovered or not)
        output_file = output_dir / json_file.name
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(paper_data, f, indent=2)

    # Print final statistics
    print("\n" + "=" * 80)
    print("ZOTERO RECOVERY COMPLETE")
    print("=" * 80)
    print(f"Total papers processed: {len(json_files)}")
    print(f"  - Already complete: {stats['already_complete']}")
    print(f"  - Missing metadata: {stats['missing_metadata']}")
    print(f"  - Matched in Zotero: {stats['matched']}")
    print(f"  - No Zotero match: {stats['no_match']}")
    print(f"  - Papers improved: {stats['papers_improved']}")

    print("\nFields Recovered:")
    print(f"  - Titles: {stats['title_recovered']}")
    print(f"  - DOIs: {stats['doi_recovered']}")
    print(f"  - Years: {stats['year_recovered']}")
    print(f"  - Journals: {stats['journal_recovered']}")
    print(f"  - Authors: {stats['authors_recovered']}")
    print(f"  - Abstracts: {stats['abstract_recovered']}")

    if stats["missing_metadata"] > 0:
        recovery_rate = (stats["papers_improved"] / stats["missing_metadata"]) * 100
        print(f"\nOverall recovery rate: {recovery_rate:.1f}%")

    # Save recovery report
    report = {
        "timestamp": datetime.now().isoformat(),
        "statistics": dict(stats),
        "recovery_details": recovery_details[:100],  # Sample of first 100
        "summary": {
            "total_processed": len(json_files),
            "papers_improved": stats["papers_improved"],
            "recovery_rate": (stats["papers_improved"] / max(stats["missing_metadata"], 1)) * 100,
        },
    }

    report_file = output_dir / "zotero_recovery_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nOutput saved to: {output_dir}/")
    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    recover_all_metadata()
