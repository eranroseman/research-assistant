#!/usr/bin/env python3
"""Test the full citation gaps function with limited scope."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_full_citation_gaps():
    """Test the complete citation gaps function with very limited scope."""
    try:
        print("🔍 Testing full citation gaps function...")
        print("Note: This will take a few minutes due to 1 RPS rate limit")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Test with very restrictive parameters to limit API calls
        print("Running citation gap analysis:")
        print("  - min_citations: 100 (high threshold)")
        print("  - limit: 5 (max 5 results)")
        print("  - Processing only first 3 papers to limit API calls")

        # Temporarily limit papers for testing
        original_papers = analyzer.papers
        analyzer.papers = analyzer.papers[:3]  # Only first 3 papers

        citation_gaps = await analyzer.find_citation_gaps(min_citations=100, limit=5)

        # Restore original papers
        analyzer.papers = original_papers

        print(f"✅ Citation gaps found: {len(citation_gaps)}")

        if citation_gaps:
            print("\nSample citation gaps:")
            for i, gap in enumerate(citation_gaps[:3]):
                print(f"  Gap {i + 1}: {gap['title'][:50]}...")
                print(f"    Citations: {gap['citation_count']}")
                print(f"    Priority: {gap.get('gap_priority', 'N/A')}")
                print(f"    DOI: {gap.get('doi', 'No DOI')}")
                print(f"    Citing papers: {len(gap.get('citing_papers', []))}")
                print()

        print("🎉 Full citation gaps test completed successfully!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_citation_gaps())
