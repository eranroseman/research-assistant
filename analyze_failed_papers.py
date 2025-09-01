#!/usr/bin/env python3
"""Analyze the 6 papers that failed OpenAlex enrichment."""

import json
from pathlib import Path

# The 6 papers that failed (from the output above)
failed_papers = ["RS5QV7TB", "UPUUKSG8", "D33YRU76", "A9Y2LLAH", "JDVDS7P3", "REWIHFW7"]

input_dir = Path("s2_enriched_20250901_small")

print("=" * 80)
print("ANALYSIS OF 6 FAILED PAPERS")
print("=" * 80)

for paper_id in failed_papers:
    paper_file = input_dir / f"{paper_id}.json"
    if paper_file.exists():
        with open(paper_file) as f:
            paper = json.load(f)

        print(f"\nPaper ID: {paper_id}")
        print(f"  DOI: {paper.get('doi', 'None')}")
        print(f"  Title: {paper.get('title', 'Unknown')[:80]}")
        print(f"  Year: {paper.get('year', 'Unknown')}")
        print(f"  Journal: {paper.get('journal', 'Unknown')}")

        # Check for DOI issues
        doi = paper.get("doi", "")
        if doi:
            if ".From" in doi or ".from" in doi:
                print("  ⚠️ Issue: Malformed DOI (contains '.From' suffix)")
            elif "http" in doi.lower():
                print("  ⚠️ Issue: DOI is a URL, not a standard DOI")
            elif "KEYWORDS" in doi:
                print("  ⚠️ Issue: DOI contains 'KEYWORDS' - likely extraction error")
            elif len(doi) > 100:
                print("  ⚠️ Issue: DOI too long - likely extraction error")
            elif not doi.startswith("10."):
                print("  ⚠️ Issue: Non-standard DOI format")

print("\n" + "-" * 40)
print("SUMMARY OF ISSUES:")
print("-" * 40)
print("These papers failed likely due to:")
print("1. Malformed DOIs (extraction errors from PDFs)")
print("2. Non-standard DOI formats")
print("3. Papers not yet indexed in OpenAlex")
print("4. Preprints or conference papers with different identifiers")

print("\nRECOMMENDATIONS:")
print("1. Clean DOIs before sending to OpenAlex")
print("2. Implement fallback to title search for failed DOIs")
print("3. Try alternative identifiers (PubMed ID, arXiv ID)")
print("4. Accept 94% as a good enrichment rate")
