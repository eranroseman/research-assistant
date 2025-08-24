#!/usr/bin/env python3
"""Test multiple DOIs to find ones that work with Semantic Scholar."""

import asyncio
import aiohttp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gap_detection import GapAnalyzer


async def test_multiple_dois():
    """Test multiple DOIs to find working ones."""
    try:
        print("🔍 Testing multiple DOIs with Semantic Scholar...")

        analyzer = GapAnalyzer("kb_data")
        print(f"✅ Loaded {len(analyzer.papers)} papers")

        # Test first 10 papers with DOIs
        working_dois = []
        failed_dois = []

        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for i, paper in enumerate(analyzer.papers[:10]):
                doi = paper.get("doi")
                if not doi:
                    continue

                print(f"Testing paper {i + 1}: {paper.get('title', 'No title')[:40]}...")
                print(f"  DOI: {doi}")

                url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}"
                params = {"fields": "title,citationCount"}

                try:
                    await asyncio.sleep(1.1)  # Rate limit
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            working_dois.append(
                                {
                                    "doi": doi,
                                    "title": data.get("title", "No title"),
                                    "citations": data.get("citationCount", 0),
                                    "kb_title": paper.get("title", "No title"),
                                }
                            )
                            print(f"  ✅ Found in S2: {data.get('title', 'No title')[:40]}...")
                        elif response.status == 404:
                            failed_dois.append(doi)
                            print("  ❌ Not found in S2 (404)")
                        else:
                            print(f"  ⚠️ API error: {response.status}")
                except Exception as e:
                    print(f"  ❌ Request failed: {e}")

        print("\nResults:")
        print(f"  Working DOIs: {len(working_dois)}")
        print(f"  Failed DOIs: {len(failed_dois)}")
        print(f"  Success rate: {len(working_dois) / (len(working_dois) + len(failed_dois)) * 100:.1f}%")

        if working_dois:
            print("\nSample working paper:")
            sample = working_dois[0]
            print(f"  DOI: {sample['doi']}")
            print(f"  KB title: {sample['kb_title'][:50]}...")
            print(f"  S2 title: {sample['title'][:50]}...")
            print(f"  Citations: {sample['citations']}")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_multiple_dois())
