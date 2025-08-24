#!/usr/bin/env python3
"""Check what fields are available in KB papers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


def check_kb_fields():
    """Check available fields in KB papers."""
    try:
        print("🔍 Checking KB paper fields...")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        if analyzer.papers:
            # Check first few papers
            for i, paper in enumerate(analyzer.papers[:3]):
                print(f"\nPaper {i + 1} fields:")
                for key, value in paper.items():
                    if isinstance(value, str) and len(value) > 50:
                        print(f"  {key}: {value[:50]}...")
                    else:
                        print(f"  {key}: {value}")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    check_kb_fields()
