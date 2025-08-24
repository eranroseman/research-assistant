#!/usr/bin/env python3
"""Test what happens when running gap analysis multiple times in the same day."""

import sys
from pathlib import Path
from datetime import UTC, datetime

sys.path.insert(0, str(Path(__file__).parent))


def test_report_naming():
    """Test the report naming and overwrite behavior."""
    try:
        print("🔍 Testing Gap Analysis Report Naming Behavior")
        print("=" * 55)

        # Simulate the current naming logic
        timestamp = datetime.now(UTC).strftime("%Y_%m_%d")
        exports_dir = Path("exports")
        report_path = exports_dir / f"gap_analysis_{timestamp}.md"

        print(f"Current timestamp format: {timestamp}")
        print(f"Report path would be: {report_path}")

        # Check if file exists
        if report_path.exists():
            stat = report_path.stat()
            print("📄 Existing report found:")
            print(f"   Size: {stat.st_size:,} bytes")
            print(f"   Modified: {datetime.fromtimestamp(stat.st_mtime, tz=UTC)}")
            print("   ⚠️  PROBLEM: Running again will OVERWRITE this file!")
        else:
            print("📄 No existing report found - will create new file")

        print("\n🔧 What happens with current design:")
        print(f"   • First run today: Creates {report_path.name}")
        print(f"   • Second run today: OVERWRITES {report_path.name}")
        print(f"   • Third run today: OVERWRITES {report_path.name}")
        print("   • Result: Only the LAST run of the day is preserved!")

        print("\n💡 Better approach would include time:")
        better_timestamp = datetime.now(UTC).strftime("%Y_%m_%d_%H%M")
        exports_dir / f"gap_analysis_{better_timestamp}.md"
        print(f"   • Format: gap_analysis_{better_timestamp}.md")
        print("   • Preserves ALL runs from the same day")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_report_naming()
