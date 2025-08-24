#!/usr/bin/env python3
"""Test gap analysis with no rate limiting delays."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


class NoDelayTokenBucket:
    """Token bucket with no delays for testing."""

    def __init__(self, max_rps=1.0, burst_allowance=3):
        self.request_count = 0

    async def acquire(self):
        """No delay acquire for testing."""
        self.request_count += 1
        # No delay - just for testing


async def test_gap_no_delays():
    """Test gap analysis without rate limiting delays."""
    try:
        print("🔍 Testing gap analysis without delays...")

        analyzer = GapAnalyzer("kb_data")
        # Replace rate limiter with no-delay version
        analyzer.rate_limiter = NoDelayTokenBucket()

        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Test just one paper for citation gaps
        print("Testing citation gap detection with limit=1...")
        citation_gaps = await analyzer.find_citation_gaps(min_citations=0, limit=1)
        print(f"✅ Citation gaps found: {len(citation_gaps)}")

        print("🎉 Test completed!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gap_no_delays())
