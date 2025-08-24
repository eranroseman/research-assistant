#!/usr/bin/env python3
"""Test the improved report generation with sample data."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_improved_report():
    """Test improved report generation with sample data."""
    try:
        print("🚀 Testing Improved Report Generation")
        print("=" * 50)

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers):,} papers")

        # Create sample citation gaps
        citation_gaps = [
            {
                "title": "Implementation Science: A Framework for Understanding Evidence-Based Practice",
                "authors": ["Smith J", "Johnson M"],
                "year": 2007,
                "citation_count": 9030,
                "venue": "Science",
                "doi": "10.1891/9780826170118.0003",
                "citing_papers": [
                    {"id": "0004", "title": "Test Paper 1"},
                    {"id": "0122", "title": "Test Paper 2"},
                ],
                "gap_priority": "HIGH",
                "confidence_score": 1.0,
                "gap_type": "citation_network",
            },
            {
                "title": "Systematic review of the validity and reliability of consumer-wearable activity trackers",
                "authors": ["Evenson K", "Goto M", "Furberg R"],
                "year": 2015,
                "citation_count": 1086,
                "venue": "International Journal of Behavioral Nutrition and Physical Activity",
                "doi": "10.1186/s12966-015-0314-1",
                "citing_papers": [{"id": "0004", "title": "Test Paper"}],
                "gap_priority": "HIGH",
                "confidence_score": 1.0,
                "gap_type": "citation_network",
            },
            {
                "title": "The potential for artificial intelligence in healthcare",
                "authors": ["Davenport T", "Kalakota R"],
                "year": 2019,
                "citation_count": 2246,
                "venue": "Future healthcare journal",
                "doi": "10.7861/futurehosp.6-2-94",
                "citing_papers": [{"id": "0007", "title": "Test Paper"}],
                "gap_priority": "HIGH",
                "confidence_score": 1.0,
                "gap_type": "citation_network",
            },
        ]

        # Create sample author gaps (including some that should be filtered)
        author_gaps = [
            {
                "title": "2025 ACC/AHA Clinical Practice Guidelines",
                "authors": ["Williams S", "Johnson M"],
                "year": 2025,
                "citation_count": 100,
                "venue": "Journal of the American College of Cardiology",
                "doi": "10.1016/j.jacc.2024.11.009",
                "source_author": "Susan L. Williams",
                "gap_priority": "MEDIUM",
                "confidence_score": 1.0,
                "gap_type": "author_network",
            },
            {
                "title": "Book Review Column",  # Should be filtered out
                "authors": ["Reviewer A"],
                "year": 2024,
                "citation_count": 5,
                "venue": "Some Journal",
                "doi": "10.1145/example",
                "source_author": "Test Author",
                "gap_priority": "LOW",
                "confidence_score": 0.5,
                "gap_type": "author_network",
            },
            {
                "title": "2025 ACC/AHA Clinical Practice Guidelines",  # Duplicate - should be filtered
                "authors": ["Williams S", "Johnson M"],
                "year": 2025,
                "citation_count": 100,
                "venue": "Journal of the American College of Cardiology",
                "doi": "10.1016/j.jacc.2024.11.009",
                "source_author": "Another Author",
                "gap_priority": "MEDIUM",
                "confidence_score": 1.0,
                "gap_type": "author_network",
            },
        ]

        # Test metadata
        kb_metadata = {"version": "4.6", "total_papers": len(analyzer.papers)}

        # Generate improved report
        print("📄 Generating improved report with test data...")
        await analyzer.generate_report(
            citation_gaps=citation_gaps,
            author_gaps=author_gaps,
            output_path="exports/gap_analysis_improved_test.md",
            kb_metadata=kb_metadata,
        )

        print("🎉 Test completed successfully!")
        print("📄 Check exports/gap_analysis_improved_test.md to see the new format")

    except Exception as e:
        import traceback

        print("❌ Test failed:")
        print(f"Exception: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_improved_report())
