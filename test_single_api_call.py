#!/usr/bin/env python3
"""Test a single Semantic Scholar API call."""

import asyncio
import aiohttp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_single_api_call():
    """Test a single API call to Semantic Scholar."""
    try:
        print("🔍 Testing single Semantic Scholar API call...")

        # Test a simple paper lookup
        url = "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b"
        params = {"fields": "title,authors,year"}

        print(f"URL: {url}")
        print(f"Params: {params}")

        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            print("Making API request...")
            async with session.get(url, params=params) as response:
                print(f"Response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: {data.get('title', 'No title')}")
                    print(f"Authors: {[a.get('name', 'No name') for a in data.get('authors', [])[:3]]}")
                else:
                    text = await response.text()
                    print(f"❌ Error: {response.status}")
                    print(f"Response: {text[:200]}...")

        print("🎉 Single API call test completed!")

    except Exception as e:
        import traceback

        print("❌ Error occurred:")
        print(f"Exception: {e}")
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_single_api_call())
