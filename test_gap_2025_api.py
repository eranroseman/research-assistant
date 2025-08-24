#!/usr/bin/env python3
"""Test gap analysis with 2025 API compliance."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_gap_2025():
    """Test gap analysis with 2025 API requirements."""
    try:
        print("🔍 Testing gap analysis with 2025 API compliance...")
        print("Note: This will take time due to 1 RPS rate limit")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Test just 1 citation gap with very high min_citations to limit API calls
        print("Testing citation gap detection (limit=1, min_citations=1000)...")
        citation_gaps = await analyzer.find_citation_gaps(min_citations=1000, limit=1)
        print(f"✅ Citation gaps found: {len(citation_gaps)}")

        if citation_gaps:
            gap = citation_gaps[0]
            print(f"Sample gap: {gap['title'][:50]}...")
            print(f"Citations: {gap['citation_count']}")
            print(f"Priority: {gap.get('gap_priority', 'N/A')}")

        print("🎉 Test completed successfully!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gap_2025())
