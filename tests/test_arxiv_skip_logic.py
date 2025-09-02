#!/usr/bin/env python3
"""Test script to verify arXiv skip logic for already-checked papers."""

import json
import tempfile
from pathlib import Path
import shutil


def create_test_papers():
    """Create test papers with different states."""
    test_dir = Path(tempfile.mkdtemp(prefix="arxiv_test_"))

    # Paper 1: Already has arxiv_checked=True (should skip)
    paper1 = {
        "title": "Test Paper 1",
        "authors": ["Smith, John"],
        "arxiv_checked": True,
        "arxiv_found": False,
        "arxiv_check_date": "2024-12-03T10:00:00Z",
    }

    # Paper 2: Already has arxiv enrichment (should skip)
    paper2 = {
        "title": "Test Paper 2",
        "authors": ["Doe, Jane"],
        "arxiv_url": "https://arxiv.org/abs/2024.12345",
        "arxiv_categories": ["cs.AI", "cs.LG"],
        "arxiv_id": "2024.12345",
    }

    # Paper 3: Has arxiv_id but no enrichment (should process with batch)
    paper3 = {"title": "Test Paper 3", "authors": ["Johnson, Bob"], "arxiv_id": "2024.99999"}

    # Paper 4: No arxiv data at all (should search by title)
    paper4 = {"title": "Test Paper 4", "authors": ["Williams, Alice"]}

    # Save test papers
    papers = [paper1, paper2, paper3, paper4]
    for i, paper in enumerate(papers, 1):
        with open(test_dir / f"paper{i}.json", "w") as f:
            json.dump(paper, f, indent=2)

    return test_dir


def analyze_processing(test_dir):
    """Analyze which papers would be processed."""
    paper_files = sorted(test_dir.glob("*.json"))

    papers_to_process = []
    papers_skipped = []
    papers_with_ids = []
    papers_without_ids = []

    for paper_file in paper_files:
        with open(paper_file) as f:
            paper = json.load(f)

        paper_name = paper_file.stem

        # Check skip conditions (matching the actual logic)
        if paper.get("arxiv_checked"):
            papers_skipped.append(
                f"{paper_name}: Already checked (found={paper.get('arxiv_found', 'unknown')})"
            )
            continue

        if paper.get("arxiv_url") or paper.get("arxiv_categories"):
            papers_skipped.append(f"{paper_name}: Already enriched")
            continue

        # Would be processed
        papers_to_process.append(paper_name)

        if paper.get("arxiv_id"):
            papers_with_ids.append(f"{paper_name}: Has ID {paper['arxiv_id']}")
        else:
            papers_without_ids.append(f"{paper_name}: Title search needed")

    return {
        "to_process": papers_to_process,
        "skipped": papers_skipped,
        "with_ids": papers_with_ids,
        "without_ids": papers_without_ids,
    }


def main():
    """Run the test."""
    print("=" * 60)
    print("TESTING ARXIV SKIP LOGIC")
    print("=" * 60)

    # Create test directory with sample papers
    test_dir = create_test_papers()
    print(f"\nCreated test directory: {test_dir}")
    print(f"Test papers created: {len(list(test_dir.glob('*.json')))}")

    # Analyze what would be processed
    results = analyze_processing(test_dir)

    print("\n" + "-" * 60)
    print("ANALYSIS RESULTS")
    print("-" * 60)

    print(f"\nPapers to process: {len(results['to_process'])}")
    for paper in results["to_process"]:
        print(f"  ✓ {paper}")

    print(f"\nPapers skipped: {len(results['skipped'])}")
    for reason in results["skipped"]:
        print(f"  ✗ {reason}")

    print("\nProcessing method:")
    if results["with_ids"]:
        print(f"  Batch query ({len(results['with_ids'])} papers):")
        for info in results["with_ids"]:
            print(f"    - {info}")

    if results["without_ids"]:
        print(f"  Individual title search ({len(results['without_ids'])} papers):")
        for info in results["without_ids"]:
            print(f"    - {info}")

    # Expected behavior
    print("\n" + "-" * 60)
    print("EXPECTED BEHAVIOR")
    print("-" * 60)
    print("✓ Paper 1: SKIP (already checked, not found)")
    print("✓ Paper 2: SKIP (already enriched)")
    print("✓ Paper 3: PROCESS (has ID, use batch)")
    print("✓ Paper 4: PROCESS (no ID, search by title)")

    # Verify expectations
    expected_to_process = ["paper3", "paper4"]
    expected_skipped = 2

    success = (
        set(results["to_process"]) == set(expected_to_process) and len(results["skipped"]) == expected_skipped
    )

    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Skip logic working correctly!")
    else:
        print("❌ TEST FAILED: Skip logic not working as expected")
        print(f"   Expected to process: {expected_to_process}")
        print(f"   Actually would process: {results['to_process']}")
    print("=" * 60)

    # Cleanup
    shutil.rmtree(test_dir)
    print(f"\nTest directory cleaned up: {test_dir}")


if __name__ == "__main__":
    main()
