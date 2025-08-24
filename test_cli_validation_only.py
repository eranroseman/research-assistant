#!/usr/bin/env python3
"""Test just the CLI validation without running analysis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.analyze_gaps import validate_kb_requirements


def test_cli_validation():
    """Test CLI validation only."""
    try:
        print("🔍 Testing CLI validation...")

        metadata, papers = validate_kb_requirements("kb_data")

        print("✅ KB validation passed!")
        print(f"  Version: {metadata.get('version')}")
        print(f"  Papers: {len(papers)}")
        print(f"  Papers with metadata: {len([p for p in papers if p.get('title') and p.get('authors')])}")

        print("🎉 CLI validation test completed!")

    except SystemExit as e:
        print(f"❌ System exit: {e.code}")
    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    test_cli_validation()
