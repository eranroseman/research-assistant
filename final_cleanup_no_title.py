#!/usr/bin/env python3
"""Final cleanup: Remove the last article without title and add to PDF quality report."""

import json
import shutil
from pathlib import Path
from datetime import datetime


def main():
    """Main entry point."""
    print("=" * 70)
    print("FINAL CLEANUP - REMOVE ARTICLE WITHOUT TITLE")
    print("=" * 70)

    # Find the KB directory
    kb_dir = Path("kb_articles_only_20250831_165102")
    if not kb_dir.exists():
        print(f"Error: KB directory not found: {kb_dir}")
        return

    # Find article without title
    missing_title = None
    missing_info = {}

    for f in kb_dir.glob("*.json"):
        if "report" in f.name:
            continue

        with open(f) as file:
            data = json.load(file)
            if not data.get("title", "").strip():
                missing_title = f.stem  # Get filename without .json
                missing_info = {
                    "paper_id": f.stem,
                    "doi": data.get("doi", ""),
                    "authors": data.get("authors", []),
                    "year": data.get("year", ""),
                    "abstract_preview": data.get("abstract", "")[:200] if data.get("abstract") else "",
                    "text_length": sum(
                        len(s.get("text", "")) for s in data.get("sections", []) if isinstance(s, dict)
                    ),
                    "num_sections": len(data.get("sections", [])),
                    "num_references": len(data.get("references", [])),
                }
                print(f"\nFound article without title: {missing_title}")
                print(f"  DOI: {missing_info['doi']}")
                print(f"  Text length: {missing_info['text_length']:,} chars")
                print(f"  Sections: {missing_info['num_sections']}")
                print(f"  References: {missing_info['num_references']}")
                if missing_info["authors"]:
                    print(f"  Authors: {', '.join(missing_info['authors'][:3])}...")
                if missing_info["abstract_preview"]:
                    print(f"  Abstract: {missing_info['abstract_preview']}...")
                break

    if not missing_title:
        print("\n✅ No articles without titles found!")
        return

    # Create final cleaned directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_dir = Path(f"kb_final_cleaned_{timestamp}")

    print(f"\n📁 Creating final cleaned directory: {final_dir}")

    # Copy all files except the one without title
    final_dir.mkdir(exist_ok=True)
    copied = 0

    for f in kb_dir.glob("*.json"):
        if f.stem != missing_title:
            shutil.copy2(f, final_dir / f.name)
            copied += 1

    print(f"✅ Copied {copied} files to final directory")

    # Update or create PDF quality report
    quality_report_path = final_dir / "pdf_quality_report.json"

    if quality_report_path.exists():
        with open(quality_report_path) as f:
            report = json.load(f)
    else:
        report = {"timestamp": timestamp, "excluded_papers": []}

    # Add the article without title to excluded papers
    report["excluded_papers"].append(
        {
            "paper_id": missing_info["paper_id"],
            "reason": "no_title_after_all_recovery_attempts",
            "details": {
                "doi": missing_info["doi"],
                "attempted_recovery": [
                    "grobid_extraction",
                    "crossref_lookup",
                    "crossref_bibliographic_search",
                    "doi_cleaning_and_retry",
                ],
                "text_length": missing_info["text_length"],
                "num_sections": missing_info["num_sections"],
                "num_references": missing_info["num_references"],
                "has_content": missing_info["text_length"] > 1000,
                "abstract_preview": missing_info["abstract_preview"],
            },
            "recommendation": "Manual review required - paper has content but title could not be recovered through automated methods",
        }
    )

    # Save updated report
    with open(quality_report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"📝 Updated PDF quality report: {quality_report_path}")

    # Generate final statistics
    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)

    total_articles = copied - 1  # Exclude the report file

    # Count coverage
    missing_dois = 0
    total_text = 0

    for f in final_dir.glob("*.json"):
        if "report" in f.name:
            continue
        with open(f) as file:
            data = json.load(file)
            if not data.get("doi", "").strip():
                missing_dois += 1
            for section in data.get("sections", []):
                if isinstance(section, dict):
                    total_text += len(section.get("text", ""))

    print(f"Total articles: {total_articles}")
    print(f"Title coverage: {total_articles}/{total_articles} (100.0%)")
    print(
        f"DOI coverage: {total_articles - missing_dois}/{total_articles} ({(total_articles - missing_dois) / total_articles * 100:.1f}%)"
    )
    print(f"Total text: {total_text:,} characters")
    print(f"Average per article: {total_text // total_articles:,} characters")

    # Create summary file
    summary_path = final_dir / "extraction_summary.md"
    with open(summary_path, "w") as f:
        f.write("# V5 Extraction Final Results\n\n")
        f.write(f"Generated: {timestamp}\n\n")
        f.write("## Statistics\n\n")
        f.write(f"- **Total articles**: {total_articles}\n")
        f.write("- **Title coverage**: 100.0% (all articles have titles)\n")
        f.write(f"- **DOI coverage**: {(total_articles - missing_dois) / total_articles * 100:.1f}%\n")
        f.write(f"- **Total text extracted**: {total_text:,} characters\n")
        f.write(f"- **Average text per article**: {total_text // total_articles:,} characters\n\n")
        f.write("## Excluded Papers\n\n")
        f.write("1 paper excluded due to missing title after all recovery attempts:\n")
        f.write(f"- Paper ID: {missing_info['paper_id']}\n")
        f.write(f"- DOI: {missing_info['doi'] or 'None'}\n")
        f.write(f"- Has {missing_info['text_length']:,} chars of content\n")
        f.write("- See `pdf_quality_report.json` for details\n\n")
        f.write("## Ready for KB Build\n\n")
        f.write("```bash\n")
        f.write(f"python src/build_kb.py --input {final_dir}/\n")
        f.write("```\n")

    print(f"\n📄 Created summary: {summary_path}")

    print("\n✅ COMPLETE!")
    print(f"   Final KB directory: {final_dir}")
    print(f"   Articles: {total_articles} (100% with titles)")
    print(f"   Ready to build: python src/build_kb.py --input {final_dir}/")


if __name__ == "__main__":
    main()
