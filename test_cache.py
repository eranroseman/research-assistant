#!/usr/bin/env python3
"""Test the caching system with a small subset of papers."""

import time

from build_kb import KnowledgeBaseBuilder


def test_cache():
    builder = KnowledgeBaseBuilder()

    # Get just the first 50 papers
    print("Fetching papers from Zotero...")
    papers = builder.process_zotero_local_library()[:50]
    print(f"Testing with {len(papers)} papers")

    # First run - no cache
    print("\nRun 1: Building cache...")
    start = time.time()
    builder.augment_papers_with_pdfs(papers, use_cache=True)
    time1 = time.time() - start
    print(f"Time: {time1:.2f} seconds")

    # Second run - with cache
    print("\nRun 2: Using cache...")
    start = time.time()
    builder.augment_papers_with_pdfs(papers, use_cache=True)
    time2 = time.time() - start
    print(f"Time: {time2:.2f} seconds")

    # Calculate speedup
    if time2 > 0:
        speedup = time1 / time2
        print(f"\nSpeedup: {speedup:.1f}x faster with cache")
        print(f"Time saved: {time1 - time2:.2f} seconds")

    # Test clear cache
    print("\nTesting clear cache...")
    builder.clear_cache()

    # Run again without cache
    print("\nRun 3: After clearing cache...")
    start = time.time()
    builder.augment_papers_with_pdfs(papers, use_cache=True)
    time3 = time.time() - start
    print(f"Time: {time3:.2f} seconds")

    print("\nCache test complete!")

if __name__ == "__main__":
    test_cache()
