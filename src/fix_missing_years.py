#!/usr/bin/env python3
"""Fix missing years in KB by extracting from TEI XML files.

This script addresses the critical bug where ALL papers in the KB are missing year metadata.
Years exist in the TEI XML but were not extracted by the original pipeline.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import re


def extract_year_from_tei(tei_file: Path) -> int | None:
    """Extract year from TEI XML file.

    Looks for dates in multiple locations:
    1. biblStruct/monogr/imprint/date[@when]
    2. publicationStmt/date[@when]
    3. Date text content with year patterns
    """
    try:
        tree = ET.parse(tei_file)
        root = tree.getroot()
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}

        # Try 1: biblStruct monogr date (most reliable)
        monogr_date = root.find(".//tei:biblStruct//tei:monogr/tei:imprint/tei:date[@when]", ns)
        if monogr_date is not None:
            when = monogr_date.get("when")
            if when:
                # Extract year from ISO date (YYYY-MM-DD or YYYY)
                year_match = re.match(r"(\d{4})", when)
                if year_match:
                    return int(year_match.group(1))

        # Try 2: publicationStmt date
        pub_date = root.find(".//tei:publicationStmt/tei:date[@when]", ns)
        if pub_date is not None:
            when = pub_date.get("when")
            if when:
                year_match = re.match(r"(\d{4})", when)
                if year_match:
                    return int(year_match.group(1))

        # Try 3: Any date element with @when attribute
        for date_elem in root.findall(".//tei:date[@when]", ns):
            when = date_elem.get("when")
            if when:
                year_match = re.match(r"(\d{4})", when)
                if year_match:
                    year = int(year_match.group(1))
                    # Sanity check - reasonable publication years
                    if 1900 <= year <= datetime.now().year + 1:
                        return year

        # Try 4: Date text content
        for date_elem in root.findall(".//tei:date", ns):
            if date_elem.text:
                # Look for 4-digit year
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date_elem.text)
                if year_match:
                    year = int(year_match.group(1))
                    if 1900 <= year <= datetime.now().year + 1:
                        return year

    except Exception as e:
        print(f"Error parsing {tei_file.name}: {e}")

    return None


def extract_year_from_references(json_data: dict) -> int | None:
    """Extract year from paper's own references as a fallback.

    Look for the most recent year in references that could be the paper's year.
    """
    years = []

    # Check references
    for ref in json_data.get("references", []):
        if isinstance(ref, dict):
            # Check year field
            if ref.get("year"):
                try:
                    year = int(ref["year"])
                    if 1900 <= year <= datetime.now().year + 1:
                        years.append(year)
                except:
                    pass

            # Check raw text for years
            raw_text = ref.get("raw", "")
            year_matches = re.findall(r"\b(19\d{2}|20\d{2})\b", raw_text)
            for y in year_matches:
                try:
                    year = int(y)
                    if 1900 <= year <= datetime.now().year + 1:
                        years.append(year)
                except:
                    pass

    if years:
        # Paper year is likely close to the most recent reference
        max_ref_year = max(years)
        # Papers usually cite works from their year or earlier
        # Assume paper is from max_ref_year to max_ref_year + 2
        return min(max_ref_year + 1, datetime.now().year)

    return None


def main():
    """Fix missing years in KB."""
    # Find latest KB directory
    kb_dirs = sorted(Path(".").glob("kb_final_cleaned_*"))
    if not kb_dirs:
        kb_dirs = sorted(Path(".").glob("kb_articles_only_*"))

    if not kb_dirs:
        print("ERROR: No KB directory found!")
        return

    kb_dir = kb_dirs[-1]
    print(f"Processing KB: {kb_dir}")

    # Find TEI XML directory
    tei_dir = Path("zotero_extraction_20250830_235521/tei_xml")
    if not tei_dir.exists():
        print(f"ERROR: TEI XML directory not found: {tei_dir}")
        return

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"kb_years_fixed_{timestamp}")
    output_dir.mkdir(exist_ok=True)

    # Process statistics
    stats = {"total": 0, "years_from_tei": 0, "years_from_refs": 0, "still_missing": 0, "errors": []}

    # Process each paper
    json_files = list(kb_dir.glob("*.json"))

    for json_file in json_files:
        if "report" in json_file.name:
            # Copy report as-is
            output_file = output_dir / json_file.name
            output_file.write_text(json_file.read_text())
            continue

        stats["total"] += 1

        # Load paper data
        with open(json_file) as f:
            data = json.load(f)

        paper_id = data.get("paper_id", json_file.stem)
        current_year = data.get("year")

        # Skip if already has a valid year
        if current_year and current_year not in [None, "Unknown", ""]:
            try:
                year_int = int(current_year)
                if 1900 <= year_int <= datetime.now().year + 1:
                    # Already has valid year, copy as-is
                    output_file = output_dir / json_file.name
                    with open(output_file, "w") as f:
                        json.dump(data, f, indent=2)
                    continue
            except:
                pass

        # Try to extract year from TEI XML
        year = None
        tei_file = tei_dir / f"{paper_id}.xml"

        if tei_file.exists():
            year = extract_year_from_tei(tei_file)
            if year:
                stats["years_from_tei"] += 1
                data["year"] = year
                data["year_source"] = "tei_xml"
                print(f"✓ {paper_id}: Year {year} from TEI XML")

        # Fallback: try to infer from references
        if not year:
            year = extract_year_from_references(data)
            if year:
                stats["years_from_refs"] += 1
                data["year"] = year
                data["year_source"] = "references_inference"
                print(f"~ {paper_id}: Year {year} inferred from references")

        if not year:
            stats["still_missing"] += 1
            print(f"✗ {paper_id}: Year still missing")

        # Save updated file
        output_file = output_dir / json_file.name
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

    # Generate report
    report = {
        "timestamp": timestamp,
        "source_dir": str(kb_dir),
        "output_dir": str(output_dir),
        "statistics": stats,
    }

    report_file = output_dir / "year_fix_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n{'=' * 70}")
    print("YEAR FIX COMPLETE")
    print(f"{'=' * 70}")
    print(f"Total papers: {stats['total']}")
    print(
        f"Years from TEI XML: {stats['years_from_tei']} ({stats['years_from_tei'] / stats['total'] * 100:.1f}%)"
    )
    print(
        f"Years from references: {stats['years_from_refs']} ({stats['years_from_refs'] / stats['total'] * 100:.1f}%)"
    )
    print(f"Still missing: {stats['still_missing']} ({stats['still_missing'] / stats['total'] * 100:.1f}%)")
    print(f"\nOutput: {output_dir}")
    print(f"Report: {report_file}")

    if stats["still_missing"] > 0:
        print(f"\n⚠️ {stats['still_missing']} papers still missing years")
        print("These may need manual inspection or additional recovery methods")

    print("\n✅ Next step: Re-run CrossRef enrichment to find missing DOIs")
    print(f"   python crossref_enrichment_v2.py --input {output_dir}")


if __name__ == "__main__":
    main()
