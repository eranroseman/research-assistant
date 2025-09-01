#!/usr/bin/env python3
"""Filter papers to keep only those with DOIs.
Removes the 28 problematic papers that lack DOIs.
"""

import json
from pathlib import Path
from datetime import datetime


def filter_papers_with_dois(input_dir: Path, output_dir: Path):
    """Filter papers to keep only those with DOIs.

    Args:
        input_dir: Directory with all papers
        output_dir: Output directory for filtered papers
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track statistics
    stats = {
        "total_papers": 0,
        "papers_with_dois": 0,
        "papers_without_dois": 0,
        "papers_without_title": 0,
        "papers_without_both": 0,
        "excluded_papers": [],
    }

    # Process all JSON files
    json_files = list(input_dir.glob("*.json"))
    stats["total_papers"] = len(json_files)

    print(f"Processing {len(json_files)} papers...")

    for json_file in json_files:
        with open(json_file, encoding="utf-8") as f:
            paper_data = json.load(f)

        # Check for DOI and title
        has_doi = bool(paper_data.get("doi", "").strip())
        has_title = bool(paper_data.get("title", "").strip())

        if has_doi:
            # Paper has DOI - keep it
            stats["papers_with_dois"] += 1

            # Copy to output directory
            output_file = output_dir / json_file.name
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(paper_data, f, indent=2)
        else:
            # No DOI - exclude it
            stats["papers_without_dois"] += 1
            stats["excluded_papers"].append(json_file.stem)

            if not has_title:
                stats["papers_without_both"] += 1
            else:
                stats["papers_without_title"] += 1

            print(f"  Excluding {json_file.stem}: No DOI")
            if has_title:
                print(f"    Title: {paper_data.get('title', '')[:60]}...")

    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "statistics": stats,
        "excluded_paper_ids": sorted(stats["excluded_papers"]),
    }

    report_file = output_dir / "filter_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("FILTERING COMPLETE")
    print("=" * 60)
    print(f"Total papers processed: {stats['total_papers']}")
    print(f"Papers with DOIs (kept): {stats['papers_with_dois']}")
    print(f"Papers without DOIs (excluded): {stats['papers_without_dois']}")
    print(f"  - Missing both DOI and title: {stats['papers_without_both']}")
    print(f"  - Missing DOI only: {stats['papers_without_dois'] - stats['papers_without_both']}")

    print("\nExcluded paper IDs:")
    for paper_id in sorted(stats["excluded_papers"])[:10]:
        print(f"  {paper_id}")
    if len(stats["excluded_papers"]) > 10:
        print(f"  ... and {len(stats['excluded_papers']) - 10} more")

    print(f"\nOutput directory: {output_dir}")
    print(f"Report: {report_file}")

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Filter papers to keep only those with DOIs")
    parser.add_argument("--input", default="crossref_batch_20250901", help="Input directory with papers")
    parser.add_argument(
        "--output", default="kb_filtered_20250901", help="Output directory for filtered papers"
    )

    args = parser.parse_args()

    filter_papers_with_dois(input_dir=Path(args.input), output_dir=Path(args.output))


if __name__ == "__main__":
    main()
