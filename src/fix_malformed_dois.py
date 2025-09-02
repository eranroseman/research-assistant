#!/usr/bin/env python3
"""Fix malformed DOIs and retry CrossRef for papers without titles."""

from src import config
import json
import time
import requests
from pathlib import Path


class DOIFixer:
    """Fix malformed DOIs and retrieve titles from CrossRef."""

    def __init__(self) -> None:
        """Initialize DOI fixer with CrossRef API configuration."""
        self.crossref_url = "https://api.crossref.org/works"
        self.headers = {"User-Agent": "ResearchAssistant/1.0 (mailto:research@example.com)"}
        self.delay = 0.2  # Rate limiting

    def clean_doi(self, doi: str) -> str:
        """Aggressively clean malformed DOIs."""
        if not doi:
            return doi

        original = doi

        # Remove trailing punctuation
        doi = doi.rstrip(".")

        # Remove common suffixes
        if "/-/DC" in doi:
            doi = doi.split("/-/DC")[0]

        # Remove appended text
        patterns_to_remove = [
            "REvIEWS",
            "REVIEWS",
            "Date2024",
            "Date2023",
            "Date2022",
            "Date2021",
            "Date2020",
            ".pdf",
            ".html",
            "Supplemental",
            "supplemental",
        ]

        for pattern in patterns_to_remove:
            if pattern in doi:
                doi = doi.replace(pattern, "")

        # Clean up any double slashes or spaces
        doi = doi.replace("//", "/").strip()

        # Remove trailing punctuation again after cleaning
        doi = doi.rstrip(".,;:")

        if doi != original:
            print(f"  Cleaned: {original} -> {doi}")

        return doi

    def get_title_from_crossref(self, doi: str) -> str | None:
        """Fetch title from CrossRef."""
        try:
            time.sleep(self.delay)
            url = f"{self.crossref_url}/{doi}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == config.MIN_SECTION_TEXT_LENGTH:
                data = response.json()
                message = data.get("message", {})

                # Get title
                title = message.get("title", [])
                if isinstance(title, list) and title:
                    return str(title[0])
                if isinstance(title, str):
                    return title

        except Exception as e:
            print(f"    CrossRef error: {str(e)[:100]}")

        return None


def main() -> None:
    """Main entry point."""
    print("=" * 70)
    print("MALFORMED DOI FIXER")
    print("=" * 70)

    # Papers to fix
    papers_to_fix = [
        ("89UKJCJD", "10.1016/0191-2607(82)90002-4."),
        ("6IP6AXAI", "10.31557/APJEC.2022.5.S1.51"),
        ("8Y46MCFY", "10.1038/s41569-022-00690-0REvIEWS"),
        ("NHTLYCX2", "10.12968/bjcn.2024.0022Date2024"),
        ("BRE9DTGV", "10.1161/HYPERTENSIONAHA.120.14742."),
    ]

    fixer = DOIFixer()
    kb_dir = Path("kb_articles_only_20250831_165102")

    if not kb_dir.exists():
        print(f"Error: KB directory not found: {kb_dir}")
        return

    print(f"\nProcessing {len(papers_to_fix)} papers with missing titles...")
    print("=" * 70)

    updated = 0
    results = []

    for paper_id, original_doi in papers_to_fix:
        print(f"\n{paper_id}:")
        print(f"  Original DOI: {original_doi}")

        # Clean the DOI
        clean_doi = fixer.clean_doi(original_doi)

        # Try to get title from CrossRef
        title = fixer.get_title_from_crossref(clean_doi)

        if title:
            print(f"  ✓ Found title: {title[:80]}...")

            # Update the paper
            json_file = kb_dir / f"{paper_id}.json"
            if json_file.exists():
                with open(json_file) as f:
                    data = json.load(f)

                data["title"] = title
                data["doi"] = clean_doi  # Use cleaned DOI
                data["title_source"] = "crossref_retry"
                data["doi_cleaned"] = True

                with open(json_file, "w") as f:
                    json.dump(data, f, indent=2)

                updated += 1
                results.append(
                    {"paper_id": paper_id, "status": "success", "title": title, "clean_doi": clean_doi}
                )
            else:
                print(f"  ✗ File not found: {json_file}")
        else:
            print("  ✗ Title not found in CrossRef")

            # Still update with cleaned DOI
            json_file = kb_dir / f"{paper_id}.json"
            if json_file.exists() and clean_doi != original_doi:
                with open(json_file) as f:
                    data = json.load(f)

                data["doi"] = clean_doi
                data["doi_cleaned"] = True

                with open(json_file, "w") as f:
                    json.dump(data, f, indent=2)

                print(f"  → Updated with cleaned DOI: {clean_doi}")

            results.append({"paper_id": paper_id, "status": "failed", "clean_doi": clean_doi})

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Papers processed: {len(papers_to_fix)}")
    print(f"Titles recovered: {updated}")
    print(f"Success rate: {updated / len(papers_to_fix) * 100:.0f}%")

    if updated > 0:
        print("\nRecovered titles:")
        for r in results:
            if r["status"] == "success":
                print(f"  {r['paper_id']}: {r['title'][:60]}...")

    failed = [r for r in results if r["status"] == "failed"]
    if failed:
        print("\nStill missing titles:")
        for r in failed:
            print(f"  {r['paper_id']}: DOI {r['clean_doi']}")

    # Check final status
    print("\n" + "=" * 70)
    print("FINAL KB STATUS")
    print("=" * 70)

    missing_count = 0
    for json_path in kb_dir.glob("*.json"):
        if "report" in json_path.name:
            continue
        with open(json_path) as file:
            data = json.load(file)
            if not data.get("title", "").strip():
                missing_count += 1

    total = len(list(kb_dir.glob("*.json"))) - 1  # Exclude report
    print(f"Total articles: {total}")
    print(f"Articles with titles: {total - missing_count} ({(total - missing_count) / total * 100:.1f}%)")
    print(f"Articles still missing titles: {missing_count} ({missing_count / total * 100:.2f}%)")


if __name__ == "__main__":
    main()
