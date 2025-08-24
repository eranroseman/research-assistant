#!/usr/bin/env python3
"""Test just the GapAnalyzer initialization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_gap_init():
    """Test gap analyzer initialization only."""
    try:
        print("Testing GapAnalyzer import...")
        from src.gap_detection import GapAnalyzer

        print("✅ Import successful")

        print("Testing GapAnalyzer initialization...")
        analyzer = GapAnalyzer("kb_data")
        print("✅ Initialization successful")

        print(f"Papers loaded: {len(analyzer.papers)}")
        print(f"KB path: {analyzer.kb_path}")

        print("🎉 Basic initialization test passed!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    test_gap_init()
