#!/usr/bin/env python3
"""Analyze the complete v5 pipeline results.
Compares metrics across all stages: TEI extraction, Zotero recovery, CrossRef enrichment.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def load_json_files(directory):
    """Load all JSON files from a directory."""
    papers = {}
    dir_path = Path(directory)

    if not dir_path.exists():
        return papers

    for json_file in dir_path.glob("*.json"):
        with open(json_file, encoding="utf-8") as f:
            papers[json_file.stem] = json.load(f)

    return papers


def calculate_field_coverage(papers, field_name):
    """Calculate coverage percentage for a specific field."""
    total = len(papers)
    if total == 0:
        return 0.0, 0

    count = sum(1 for p in papers.values() if p.get(field_name))
    return (count / total) * 100, count


def analyze_stage(papers, stage_name):
    """Analyze a single stage of the pipeline."""
    print(f"\n{'=' * 60}")
    print(f"{stage_name}")
    print(f"{'=' * 60}")

    if not papers:
        print("No data available for this stage")
        return {}

    print(f"Total papers: {len(papers)}")

    # Critical fields to track
    critical_fields = ["title", "doi", "year", "authors", "journal", "abstract"]
    coverage = {}

    print("\nField Coverage:")
    for field in critical_fields:
        pct, count = calculate_field_coverage(papers, field)
        coverage[field] = {"percentage": pct, "count": count}
        print(f"  {field:12s}: {count:4d}/{len(papers)} ({pct:5.1f}%)")

    # Additional metrics
    print("\nAdditional Metrics:")

    # Full text coverage
    papers_with_sections = sum(1 for p in papers.values() if p.get("sections"))
    print(
        f"  Papers with sections: {papers_with_sections}/{len(papers)} ({papers_with_sections / len(papers) * 100:.1f}%)"
    )

    # Reference coverage
    papers_with_refs = sum(1 for p in papers.values() if p.get("references") or p.get("cited_references"))
    print(
        f"  Papers with references: {papers_with_refs}/{len(papers)} ({papers_with_refs / len(papers) * 100:.1f}%)"
    )

    # Missing critical metadata
    missing_multiple = 0
    missing_details = defaultdict(list)

    for paper_id, paper in papers.items():
        missing = []
        for field in critical_fields:
            if not paper.get(field):
                missing.append(field)
                missing_details[field].append(paper_id)

        if len(missing) >= 2:
            missing_multiple += 1

    print(f"\nPapers missing 2+ critical fields: {missing_multiple}")

    # Show examples of papers missing each field (max 3)
    for field in critical_fields:
        if missing_details[field]:
            examples = missing_details[field][:3]
            more = f" (+{len(missing_details[field]) - 3} more)" if len(missing_details[field]) > 3 else ""
            print(f"  Missing {field}: {', '.join(examples)}{more}")

    return coverage


def compare_stages(stage_data):
    """Compare improvements across stages."""
    print("\n" + "=" * 60)
    print("STAGE COMPARISON")
    print("=" * 60)

    if len(stage_data) < 2:
        print("Need at least 2 stages for comparison")
        return

    stages = list(stage_data.keys())
    fields = ["title", "doi", "year", "authors", "journal", "abstract"]

    print("\nField Coverage Improvements:")
    print(f"{'Field':<12} " + " | ".join(f"{s[:10]:>10}" for s in stages))
    print("-" * (15 + 13 * len(stages)))

    for field in fields:
        values = []
        for stage in stages:
            if stage in stage_data and field in stage_data[stage]:
                pct = stage_data[stage][field]["percentage"]
                values.append(f"{pct:5.1f}%")
            else:
                values.append("   N/A")

        print(f"{field:<12} " + " | ".join(f"{v:>10}" for v in values))

    # Calculate overall improvements
    print("\n" + "=" * 60)
    print("IMPROVEMENT SUMMARY")
    print("=" * 60)

    if len(stages) >= 2:
        for i in range(1, len(stages)):
            prev_stage = stages[i - 1]
            curr_stage = stages[i]

            print(f"\n{prev_stage} → {curr_stage}:")

            for field in fields:
                if field in stage_data[prev_stage] and field in stage_data[curr_stage]:
                    prev_count = stage_data[prev_stage][field]["count"]
                    curr_count = stage_data[curr_stage][field]["count"]
                    improvement = curr_count - prev_count

                    if improvement > 0:
                        print(f"  {field}: +{improvement} papers recovered")


def main():
    """Main analysis function."""
    print("V5 PIPELINE ANALYSIS")
    print("=" * 60)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Stage 1: TEI Extraction
    tei_papers = load_json_files("comprehensive_extraction_20250831_225926")
    tei_coverage = analyze_stage(tei_papers, "STAGE 1: TEI EXTRACTION")

    # Stage 2: Zotero Recovery
    zotero_papers = load_json_files("zotero_recovered_20250901")
    zotero_coverage = analyze_stage(zotero_papers, "STAGE 2: ZOTERO RECOVERY")

    # Stage 3: CrossRef Enrichment (if available)
    crossref_papers = load_json_files("crossref_batch_20250901")
    if crossref_papers:
        crossref_coverage = analyze_stage(crossref_papers, "STAGE 3: CROSSREF ENRICHMENT")
    else:
        print("\n" + "=" * 60)
        print("STAGE 3: CROSSREF ENRICHMENT")
        print("=" * 60)
        print("Still running... Check back later.")
        crossref_coverage = {}

    # Compare stages
    stage_data = {"TEI Extraction": tei_coverage, "Zotero Recovery": zotero_coverage}

    if crossref_coverage:
        stage_data["CrossRef"] = crossref_coverage

    compare_stages(stage_data)

    # Final statistics
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)

    final_papers = crossref_papers if crossref_papers else zotero_papers

    if final_papers:
        # Papers with complete metadata
        complete = sum(
            1
            for p in final_papers.values()
            if all(p.get(f) for f in ["title", "doi", "year", "authors", "journal"])
        )

        print(
            f"Papers with complete metadata: {complete}/{len(final_papers)} ({complete / len(final_papers) * 100:.1f}%)"
        )

        # Papers with full text and references
        full_papers = sum(
            1
            for p in final_papers.values()
            if p.get("sections") and (p.get("references") or p.get("cited_references"))
        )

        print(
            f"Papers with full text + references: {full_papers}/{len(final_papers)} ({full_papers / len(final_papers) * 100:.1f}%)"
        )

        # Total text extracted
        total_chars = sum(len(str(p.get("sections", ""))) for p in final_papers.values())
        print(f"Total text extracted: {total_chars / 1_000_000:.1f}M characters")

        # Average references per paper
        ref_counts = [
            len(p.get("references", [])) + len(p.get("cited_references", [])) for p in final_papers.values()
        ]
        avg_refs = sum(ref_counts) / len(ref_counts) if ref_counts else 0
        print(f"Average references per paper: {avg_refs:.1f}")


if __name__ == "__main__":
    main()
