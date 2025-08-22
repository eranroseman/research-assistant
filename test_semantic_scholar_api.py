#!/usr/bin/env python3
"""
Test script to measure actual Semantic Scholar API rate limits and performance.

This script tests:
1. Actual rate limits (requests per second)
2. Response times per request
3. Success/failure rates
4. Rate limiting behavior
5. Parallel request performance

Usage:
    python test_semantic_scholar_api.py
"""

import asyncio
import aiohttp
import time
import json
from typing import Any
import statistics

try:
    import aiofiles
except ImportError:
    aiofiles = None

# Test configuration
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1"
TEST_DURATION_SECONDS = 60  # How long to test for
CONCURRENT_REQUESTS = [1, 5, 10, 20, 50]  # Different concurrency levels to test
REQUEST_TIMEOUT = 10  # Timeout per request

# Sample DOIs and paper IDs for testing
TEST_DOIS = [
    "10.1038/nature12373",
    "10.1126/science.1235122",
    "10.1016/j.cell.2013.05.039",
    "10.1056/NEJMoa1200303",
    "10.1001/jama.2013.281053",
    "10.1371/journal.pone.0066844",
    "10.1109/TKDE.2013.130",
    "10.1145/2488388.2488451",
    "10.1038/ncomms4308",
    "10.1186/1471-2105-14-7",
]

# Test paper titles if DOIs fail
TEST_TITLES = [
    "CRISPR-Cas9 genome editing",
    "Deep learning neural networks",
    "Machine learning healthcare",
    "Systematic review meta-analysis",
    "Randomized controlled trial",
    "COVID-19 pandemic response",
    "Artificial intelligence applications",
    "Climate change mitigation",
    "Precision medicine genomics",
    "Digital health interventions",
]


class APIRateTester:
    def __init__(self):
        self.session = None
        self.results = []
        self.errors = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_single_request(self, doi: str | None = None, title: str | None = None) -> dict[str, Any]:
        """Test a single API request and measure performance."""
        start_time = time.time()

        try:
            if doi:
                url = f"{SEMANTIC_SCHOLAR_API_URL}/paper/DOI:{doi}"
                params = {"fields": "citationCount,venue,authors,externalIds,title"}
            elif title:
                url = f"{SEMANTIC_SCHOLAR_API_URL}/paper/search"
                params = {
                    "query": title,
                    "limit": 1,
                    "fields": "citationCount,venue,authors,externalIds,title",
                }
            else:
                raise ValueError("Must provide either DOI or title")

            async with self.session.get(url, params=params) as response:
                end_time = time.time()
                response_time = end_time - start_time

                result = {
                    "timestamp": start_time,
                    "response_time": response_time,
                    "status_code": response.status,
                    "success": response.status == 200,
                    "doi": doi,
                    "title": title,
                    "url": str(response.url),
                    "headers": dict(response.headers),
                }

                if response.status == 200:
                    try:
                        data = await response.json()
                        if doi:
                            result["data_received"] = bool(data.get("title"))
                        else:
                            result["data_received"] = bool(data.get("data") and len(data["data"]) > 0)
                    except Exception as e:
                        result["data_received"] = False
                        result["parse_error"] = str(e)
                elif response.status == 429:
                    result["rate_limited"] = True
                    # Check for rate limit headers
                    if "x-ratelimit-remaining" in response.headers:
                        result["rate_limit_remaining"] = response.headers["x-ratelimit-remaining"]
                    if "x-ratelimit-reset" in response.headers:
                        result["rate_limit_reset"] = response.headers["x-ratelimit-reset"]

                return result

        except Exception as e:
            end_time = time.time()
            return {
                "timestamp": start_time,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e),
                "doi": doi,
                "title": title,
            }

    async def test_burst_requests(self, count: int, delay: float = 0.0) -> list[dict[str, Any]]:
        """Test burst of requests with optional delay between them."""
        print(f"Testing burst of {count} requests with {delay}s delay...")

        tasks = []
        for i in range(count):
            doi = TEST_DOIS[i % len(TEST_DOIS)]
            task = self.test_single_request(doi=doi)
            tasks.append(task)

            if delay > 0 and i < count - 1:
                await asyncio.sleep(delay)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "timestamp": time.time(),
                        "success": False,
                        "error": str(result),
                        "doi": TEST_DOIS[i % len(TEST_DOIS)],
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    async def test_concurrent_requests(
        self, concurrent_count: int, total_requests: int
    ) -> list[dict[str, Any]]:
        """Test concurrent requests with controlled concurrency."""
        print(f"Testing {total_requests} requests with {concurrent_count} concurrent...")

        semaphore = asyncio.Semaphore(concurrent_count)

        async def limited_request(doi: str):
            async with semaphore:
                return await self.test_single_request(doi=doi)

        tasks = []
        for i in range(total_requests):
            doi = TEST_DOIS[i % len(TEST_DOIS)]
            tasks.append(limited_request(doi))

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time
        requests_per_second = total_requests / total_time if total_time > 0 else 0

        print(f"  Completed {total_requests} requests in {total_time:.2f}s = {requests_per_second:.2f} RPS")

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "timestamp": time.time(),
                        "success": False,
                        "error": str(result),
                        "doi": TEST_DOIS[i % len(TEST_DOIS)],
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    def analyze_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze test results and calculate statistics."""
        if not results:
            return {"error": "No results to analyze"}

        successful_results = [r for r in results if r.get("success", False)]
        failed_results = [r for r in results if not r.get("success", False)]
        rate_limited = [r for r in results if r.get("rate_limited", False)]

        response_times = [r["response_time"] for r in results if "response_time" in r]
        successful_response_times = [r["response_time"] for r in successful_results if "response_time" in r]

        # Calculate time span
        timestamps = [r["timestamp"] for r in results if "timestamp" in r]
        time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0

        analysis = {
            "total_requests": len(results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "rate_limited_requests": len(rate_limited),
            "success_rate": len(successful_results) / len(results) * 100 if results else 0,
            "rate_limit_percentage": len(rate_limited) / len(results) * 100 if results else 0,
            "time_span_seconds": time_span,
            "requests_per_second": len(results) / time_span if time_span > 0 else 0,
        }

        if response_times:
            analysis["response_time_stats"] = {
                "min": min(response_times),
                "max": max(response_times),
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            }

        if successful_response_times:
            analysis["successful_response_time_stats"] = {
                "min": min(successful_response_times),
                "max": max(successful_response_times),
                "mean": statistics.mean(successful_response_times),
                "median": statistics.median(successful_response_times),
            }

        # Error breakdown
        error_types = {}
        for result in failed_results:
            error_type = result.get("error", "Unknown")
            if result.get("rate_limited"):
                error_type = "Rate Limited"
            elif result.get("status_code"):
                error_type = f"HTTP {result['status_code']}"

            error_types[error_type] = error_types.get(error_type, 0) + 1

        analysis["error_breakdown"] = error_types

        return analysis


async def run_baseline_test(tester: APIRateTester) -> list[dict[str, Any]]:
    """Run baseline single requests test."""
    print("\n📊 Test 1: Baseline single requests")
    baseline_results = []
    for i in range(5):
        result = await tester.test_single_request(doi=TEST_DOIS[i])
        baseline_results.append(result)
        print(f"  Request {i+1}: {result['response_time']:.3f}s - {'✅' if result['success'] else '❌'}")
        await asyncio.sleep(0.1)  # Small delay between requests

    baseline_analysis = tester.analyze_results(baseline_results)
    print(
        f"  Baseline: {baseline_analysis['success_rate']:.1f}% success, {baseline_analysis['successful_response_time_stats']['mean']:.3f}s avg response"
    )
    return baseline_results


async def run_burst_test(tester: APIRateTester) -> list[dict[str, Any]]:
    """Run burst requests test."""
    print("\n🚀 Test 2: Burst requests (no rate limiting)")
    burst_results = await tester.test_burst_requests(20, delay=0.0)
    burst_analysis = tester.analyze_results(burst_results)
    print(
        f"  Burst: {burst_analysis['success_rate']:.1f}% success, {burst_analysis['rate_limit_percentage']:.1f}% rate limited"
    )
    print(f"  Effective RPS: {burst_analysis['requests_per_second']:.2f}")
    return burst_results


async def run_concurrency_test(tester: APIRateTester) -> list[dict[str, Any]]:
    """Run concurrency tests."""
    print("\n🔄 Test 3: Concurrency testing")
    all_concurrent_results = []

    for concurrent in [1, 5, 10, 20]:
        concurrent_results = await tester.test_concurrent_requests(concurrent, 20)
        concurrent_analysis = tester.analyze_results(concurrent_results)
        print(
            f"  {concurrent} concurrent: {concurrent_analysis['success_rate']:.1f}% success, {concurrent_analysis['requests_per_second']:.2f} RPS"
        )
        all_concurrent_results.extend(concurrent_results)

        # Break if we're getting heavily rate limited
        if concurrent_analysis["rate_limit_percentage"] > 50:
            print("  ⚠️  High rate limiting detected, stopping concurrency tests")
            break

        await asyncio.sleep(2)  # Cool down between tests

    return all_concurrent_results


async def run_sustained_test(tester: APIRateTester) -> list[dict[str, Any]]:
    """Run sustained load test."""
    print(f"\n⏱️ Test 4: Sustained load test ({TEST_DURATION_SECONDS}s)")
    sustained_results = []
    end_time = time.time() + TEST_DURATION_SECONDS
    request_count = 0

    while time.time() < end_time:
        doi = TEST_DOIS[request_count % len(TEST_DOIS)]
        result = await tester.test_single_request(doi=doi)
        sustained_results.append(result)
        request_count += 1

        # Adaptive delay based on recent rate limiting
        recent_results = sustained_results[-5:] if len(sustained_results) >= 5 else sustained_results
        recent_rate_limited = sum(1 for r in recent_results if r.get("rate_limited", False))

        if recent_rate_limited >= 2:  # If 2+ of last 5 were rate limited
            await asyncio.sleep(1.0)  # Longer delay
        elif recent_rate_limited >= 1:
            await asyncio.sleep(0.1)  # Short delay
        # else no delay

    sustained_analysis = tester.analyze_results(sustained_results)
    print(f"  Sustained: {request_count} requests in {TEST_DURATION_SECONDS}s")
    print(f"  Average RPS: {sustained_analysis['requests_per_second']:.2f}")
    print(f"  Success rate: {sustained_analysis['success_rate']:.1f}%")
    print(f"  Rate limited: {sustained_analysis['rate_limit_percentage']:.1f}%")
    return sustained_results


async def save_results(all_results: list[dict[str, Any]], overall_analysis: dict[str, Any]) -> str:
    """Save test results to file."""
    results_file = f"semantic_scholar_api_test_results_{int(time.time())}.json"
    results_data = {
        "test_config": {
            "api_url": SEMANTIC_SCHOLAR_API_URL,
            "test_duration": TEST_DURATION_SECONDS,
            "request_timeout": REQUEST_TIMEOUT,
            "test_dois": TEST_DOIS[:5],  # Don't save all
        },
        "overall_analysis": overall_analysis,
        "detailed_results": all_results[:100],  # Limit saved results
    }

    if aiofiles:
        async with aiofiles.open(results_file, "w") as f:
            await f.write(json.dumps(results_data, indent=2))
    else:
        # Fallback to sync I/O if aiofiles not available
        with open(results_file, "w") as f:  # noqa: ASYNC230
            json.dump(results_data, f, indent=2)

    return results_file


def print_recommendations(overall_analysis: dict[str, Any]) -> None:
    """Print recommendations based on test results."""
    print("\n💡 Recommendations")
    print("=" * 20)

    if overall_analysis["rate_limit_percentage"] > 20:
        print("⚠️  High rate limiting detected - recommend adding delays between requests")
        recommended_rps = overall_analysis["requests_per_second"] * 0.8
        print(f"🎯 Recommended max RPS: {recommended_rps:.2f}")
    elif overall_analysis["rate_limit_percentage"] > 5:
        print("⚡ Moderate rate limiting - current rate close to limit")
        recommended_rps = overall_analysis["requests_per_second"] * 0.9
        print(f"🎯 Recommended max RPS: {recommended_rps:.2f}")
    else:
        print("✅ Low rate limiting - can likely increase request rate")
        recommended_rps = overall_analysis["requests_per_second"] * 1.2
        print(f"🎯 Could try up to: {recommended_rps:.2f} RPS")


def print_kb_implications(overall_analysis: dict[str, Any]) -> None:
    """Print KB building performance implications."""
    print("\n🏗️ KB Building Performance Implications")
    print("=" * 40)

    avg_response_time = overall_analysis.get("successful_response_time_stats", {}).get("mean", 0.3)
    effective_rps = overall_analysis["requests_per_second"] if overall_analysis["success_rate"] > 80 else 0

    for paper_count in [100, 500, 1000, 2000]:
        if effective_rps > 0:
            time_needed = paper_count / effective_rps
            print(f"  {paper_count} papers: ~{time_needed/60:.1f} minutes")
        else:
            time_needed = paper_count * avg_response_time
            print(f"  {paper_count} papers: ~{time_needed/60:.1f} minutes (sequential)")


async def main():
    """Run comprehensive API rate testing."""
    print("🧪 Semantic Scholar API Rate Limit Test")
    print("=" * 50)

    async with APIRateTester() as tester:
        all_results = []

        # Run all tests
        baseline_results = await run_baseline_test(tester)
        all_results.extend(baseline_results)

        burst_results = await run_burst_test(tester)
        all_results.extend(burst_results)

        concurrent_results = await run_concurrency_test(tester)
        all_results.extend(concurrent_results)

        sustained_results = await run_sustained_test(tester)
        all_results.extend(sustained_results)

        # Overall analysis and reporting
        print("\n📈 Overall Results")
        print("=" * 30)
        overall_analysis = tester.analyze_results(all_results)

        print(f"Total requests: {overall_analysis['total_requests']}")
        print(f"Success rate: {overall_analysis['success_rate']:.1f}%")
        print(f"Rate limited: {overall_analysis['rate_limit_percentage']:.1f}%")
        print(f"Overall RPS achieved: {overall_analysis['requests_per_second']:.2f}")

        if "successful_response_time_stats" in overall_analysis:
            stats = overall_analysis["successful_response_time_stats"]
            print(f"Response times: {stats['min']:.3f}s - {stats['max']:.3f}s (avg: {stats['mean']:.3f}s)")

        if overall_analysis["error_breakdown"]:
            print("\nError breakdown:")
            for error_type, count in overall_analysis["error_breakdown"].items():
                print(f"  {error_type}: {count}")

        # Save results and print recommendations
        results_file = await save_results(all_results, overall_analysis)
        print(f"\n💾 Detailed results saved to: {results_file}")

        print_recommendations(overall_analysis)
        print_kb_implications(overall_analysis)


if __name__ == "__main__":
    asyncio.run(main())
