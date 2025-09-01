#!/usr/bin/env python3
"""CORE Enrichment for V5 Pipeline
Finds additional full-text sources and download statistics.

Features:
- Full text URLs from repositories
- Download and view statistics
- Repository information
- Similar paper recommendations
- ~40% overlap with existing papers
- ~10% unique full-text not found elsewhere
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
import re


class COREEnricher:
    """Enrich papers with CORE repository metadata."""

    def __init__(self, api_key: str | None = None):
        """Initialize CORE enricher.

        Args:
            api_key: Optional API key for higher rate limits

        Note: CORE API v3 uses token-based rate limiting:
        - Unauthenticated: 1,000 tokens/day, max 10 tokens/min
        - Registered: 10,000 tokens/day, max 10 tokens/min
        - Academic: ~200,000 tokens/day (dynamically adjusted)
        - Simple queries cost 1 token, complex queries 3-5 tokens
        """
        self.base_url = "https://api.core.ac.uk/v3"
        self.api_key = api_key
        self.session = self._create_session()
        self.stats = defaultdict(int)

        # Token tracking
        self.tokens_used = 0
        self.daily_limit = 10000 if api_key else 1000
        self.minute_limit = 10

        # Rate limiting - respect token limits
        # With 10 tokens/min max, we need 6+ seconds between requests
        self.delay = 6.0  # Conservative to avoid hitting minute limit

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=2,  # More aggressive backoff for CORE
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers - CORE prefers Bearer token in header
        headers = {
            "User-Agent": "Research Assistant v5.0 (https://github.com/research-assistant)",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        session.headers.update(headers)

        return session

    def _track_rate_limits(self, response: requests.Response):
        """Track rate limit information from response headers."""
        try:
            # Check for rate limit headers
            remaining = response.headers.get("X-RateLimitRemaining")
            limit = response.headers.get("X-RateLimit-Limit")
            retry_after = response.headers.get("X-RateLimit-Retry-After")

            if remaining:
                self.stats["tokens_remaining"] = int(remaining)
            if retry_after:
                self.stats["retry_after"] = int(retry_after)

            # Increment token usage
            self.tokens_used += 1

        except Exception:
            pass  # Silently ignore header parsing errors

    def enrich_single_by_doi(self, doi: str) -> dict[str, Any] | None:
        """Enrich a single paper by DOI.

        Args:
            doi: Paper DOI

        Returns:
            Enriched metadata or None if not found
        """
        try:
            # Clean DOI
            clean_doi = self._clean_doi(doi)
            if not clean_doi:
                self.stats["invalid_doi"] += 1
                return None

            # Search CORE by DOI
            params = {"q": f'doi:"{clean_doi}"', "limit": 1}

            response = self.session.get(
                f"{self.base_url}/search/works",
                params=params,
                timeout=10,  # Shorter timeout to avoid long waits
            )

            # Track token usage from headers
            self._track_rate_limits(response)

            if response.status_code == 404:
                self.stats["not_found"] += 1
                return None
            if response.status_code == 429:
                self.stats["rate_limited"] += 1
                print("Rate limited. Wait and retry.")
                return None

            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if results:
                return self._process_core_work(results[0])
            self.stats["not_found"] += 1
            return None

        except requests.exceptions.Timeout:
            self.stats["timeout"] += 1
            print(f"Timeout for {doi}")
        except requests.exceptions.RequestException as e:
            self.stats["error"] += 1
            print(f"Error enriching {doi}: {e}")

        return None

    def enrich_single_by_title(self, title: str) -> dict[str, Any] | None:
        """Enrich a single paper by title.

        Args:
            title: Paper title

        Returns:
            Enriched metadata or None if not found
        """
        try:
            # Clean and escape title for search
            clean_title = self._clean_title(title)
            if not clean_title:
                self.stats["invalid_title"] += 1
                return None

            # Search CORE by title
            params = {"q": f'title:"{clean_title}"', "limit": 1}

            response = self.session.get(
                f"{self.base_url}/search/works",
                params=params,
                timeout=10,  # Shorter timeout
            )

            # Track token usage
            self._track_rate_limits(response)

            if response.status_code == 404:
                self.stats["not_found"] += 1
                return None
            if response.status_code == 429:
                self.stats["rate_limited"] += 1
                print("Rate limited. Wait and retry.")
                return None

            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if results:
                # Verify title match (fuzzy)
                result_title = results[0].get("title", "").lower()
                if self._fuzzy_title_match(clean_title.lower(), result_title):
                    return self._process_core_work(results[0])
                self.stats["title_mismatch"] += 1
                return None
            self.stats["not_found"] += 1
            return None

        except requests.exceptions.Timeout:
            self.stats["timeout"] += 1
            print("Timeout for title search")
        except requests.exceptions.RequestException as e:
            self.stats["error"] += 1
            print(f"Error searching by title: {e}")

        return None

    def _clean_doi(self, doi: str) -> str | None:
        """Clean and validate a DOI (reuses logic from other enrichers).

        Args:
            doi: Raw DOI string

        Returns:
            Cleaned DOI or None if invalid
        """
        if not doi:
            return None

        # Remove whitespace and convert to lowercase
        clean = doi.strip().lower()

        # Handle URLs
        if clean.startswith("http"):
            if "doi.org/" in clean:
                clean = clean.split("doi.org/")[-1]
            elif "doi=" in clean:
                match = re.search(r"doi=([^&]+)", clean)
                if match:
                    clean = match.group(1)
                else:
                    return None
            else:
                return None

        # Remove common suffixes from extraction errors
        clean = clean.split(".from")[0]
        clean = clean.split("keywords")[0]
        clean = clean.rstrip(".)•")

        # Validate basic DOI format
        if not clean.startswith("10."):
            return None
        if len(clean) < 10 or len(clean) > 100:
            return None

        return clean

    def _clean_title(self, title: str) -> str | None:
        """Clean title for search query.

        Args:
            title: Raw title string

        Returns:
            Cleaned title or None if invalid
        """
        if not title:
            return None

        # Remove special characters that might break search
        clean = re.sub(r'["\'\(\)\[\]{}]', " ", title)
        clean = re.sub(r"\s+", " ", clean)
        clean = clean.strip()

        # Truncate very long titles
        if len(clean) > 200:
            clean = clean[:200]

        return clean if len(clean) > 10 else None

    def _fuzzy_title_match(self, title1: str, title2: str, threshold: float = 0.85) -> bool:
        """Check if two titles are similar enough.

        Args:
            title1: First title (lowercase)
            title2: Second title (lowercase)
            threshold: Similarity threshold (0-1)

        Returns:
            True if titles match
        """
        # Simple approach: check word overlap
        words1 = set(title1.split())
        words2 = set(title2.split())

        if not words1 or not words2:
            return False

        # Remove common words
        stopwords = {
            "the",
            "a",
            "an",
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "and",
            "or",
            "but",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
        }
        words1 = words1 - stopwords
        words2 = words2 - stopwords

        if not words1 or not words2:
            return title1 == title2  # Fall back to exact match

        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        similarity = intersection / union if union > 0 else 0

        return similarity >= threshold

    def _process_core_work(self, work: dict[str, Any]) -> dict[str, Any]:
        """Process CORE work into enriched metadata.

        Args:
            work: Raw CORE work data

        Returns:
            Processed metadata
        """
        enriched = {
            "core_id": work.get("id"),
            "title": work.get("title"),
            "doi": work.get("doi"),
            "year": work.get("yearPublished"),
            "abstract": work.get("abstract"),
        }

        # Full text availability
        enriched["has_fulltext"] = work.get("fullText") is not None

        # Download URL
        download_url = work.get("downloadUrl")
        if download_url:
            enriched["download_url"] = download_url
            enriched["has_pdf"] = download_url.endswith(".pdf")

        # Repository information
        data_provider = work.get("dataProvider")
        if data_provider:
            enriched["repository"] = {
                "id": data_provider.get("id"),
                "name": data_provider.get("name"),
                "url": data_provider.get("url"),
            }

        # Authors
        authors = work.get("authors", [])
        if authors:
            enriched["authors"] = [author.get("name") for author in authors if author.get("name")]

        # Journal/Publisher info
        publisher = work.get("publisher")
        if publisher:
            enriched["publisher"] = publisher

        journal = work.get("journal")
        if journal:
            enriched["journal"] = {
                "title": journal.get("title"),
                "issn": journal.get("identifiers", [None])[0] if journal.get("identifiers") else None,
            }

        # Language
        language = work.get("language")
        if language:
            enriched["language"] = language.get("name") if isinstance(language, dict) else language

        # Document type
        doc_type = work.get("documentType")
        if doc_type:
            enriched["document_type"] = doc_type

        # OAI identifier (useful for harvesting)
        oai = work.get("oai")
        if oai:
            enriched["oai_identifier"] = oai

        # Links
        links = work.get("links", [])
        if links:
            enriched["links"] = []
            for link in links:
                if link.get("url"):
                    enriched["links"].append({"url": link.get("url"), "type": link.get("type")})

        # Statistics (if available)
        # Note: CORE v3 may not always provide these
        if work.get("downloadCount"):
            enriched["download_count"] = work.get("downloadCount")
        if work.get("viewCount"):
            enriched["view_count"] = work.get("viewCount")

        # Track statistics
        if enriched.get("has_fulltext"):
            self.stats["has_fulltext"] += 1
        if enriched.get("has_pdf"):
            self.stats["has_pdf"] += 1
        if enriched.get("repository"):
            self.stats["has_repository"] += 1

        self.stats["enriched"] += 1

        return enriched

    def enrich_batch(
        self, papers: list[dict[str, str]], use_title_fallback: bool = True
    ) -> dict[str, dict[str, Any]]:
        """Enrich multiple papers. CORE doesn't support true batch queries,
        so we process individually with rate limiting.

        Args:
            papers: List of dicts with 'doi' and/or 'title' keys
            use_title_fallback: Try title search if DOI fails

        Returns:
            Dictionary mapping original identifier to enriched metadata
        """
        results = {}

        for paper in papers:
            doi = paper.get("doi")
            title = paper.get("title")

            # Try DOI first
            enriched = None
            if doi:
                enriched = self.enrich_single_by_doi(doi)
                if enriched:
                    results[doi] = enriched

            # Fallback to title if DOI failed and we have a title
            if not enriched and title and use_title_fallback:
                enriched = self.enrich_single_by_title(title)
                if enriched:
                    # Use title as key if no DOI
                    key = doi if doi else title
                    results[key] = enriched

            if not enriched:
                self.stats["failed"] += 1

            # Rate limiting
            time.sleep(self.delay)

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get enrichment statistics."""
        total = self.stats["enriched"] + self.stats["failed"]

        return {
            "total_processed": total,
            "enriched": self.stats["enriched"],
            "failed": self.stats["failed"],
            "enrichment_rate": f"{(self.stats['enriched'] / total * 100):.1f}%" if total else "0%",
            "has_fulltext": self.stats["has_fulltext"],
            "fulltext_rate": f"{(self.stats['has_fulltext'] / self.stats['enriched'] * 100):.1f}%"
            if self.stats["enriched"]
            else "0%",
            "has_pdf": self.stats["has_pdf"],
            "pdf_rate": f"{(self.stats['has_pdf'] / self.stats['enriched'] * 100):.1f}%"
            if self.stats["enriched"]
            else "0%",
            "has_repository": self.stats["has_repository"],
            "errors": {
                "not_found": self.stats.get("not_found", 0),
                "invalid_doi": self.stats.get("invalid_doi", 0),
                "invalid_title": self.stats.get("invalid_title", 0),
                "title_mismatch": self.stats.get("title_mismatch", 0),
                "timeout": self.stats.get("timeout", 0),
                "other": self.stats.get("error", 0),
            },
        }


def process_directory(
    input_dir: str,
    output_dir: str,
    api_key: str | None = None,
    use_title_fallback: bool = True,
    max_papers: int | None = None,
):
    """Process all papers in a directory with CORE enrichment.

    Args:
        input_dir: Directory containing paper JSON files
        output_dir: Directory to save enriched papers
        api_key: Optional API key for higher rate limits
        use_title_fallback: Try title search if DOI fails
        max_papers: Maximum number of papers to process (for testing)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize enricher
    enricher = COREEnricher(api_key=api_key)

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    if max_papers:
        paper_files = paper_files[:max_papers]

    print(f"Found {len(paper_files)} papers to process")

    # Collect papers with identifiers
    papers_to_process = []
    papers_by_id = {}

    for paper_file in paper_files:
        # Skip report files
        if "report" in paper_file.name:
            continue

        with open(paper_file) as f:
            paper = json.load(f)

            # Prepare paper dict
            paper_dict = {}
            if paper.get("doi"):
                paper_dict["doi"] = paper["doi"]
            if paper.get("title"):
                paper_dict["title"] = paper["title"]

            if paper_dict:
                # Use DOI as key if available, otherwise title
                key = paper_dict.get("doi") or paper_dict.get("title")
                papers_to_process.append(paper_dict)
                papers_by_id[key] = (paper_file.stem, paper)

    print(f"Found {len(papers_to_process)} papers with DOI or title")

    # Process papers
    start_time = time.time()

    print("\nProcessing papers with CORE API...")
    if not api_key:
        print("Note: No API key provided. Using conservative rate limiting.")
        print("Get an API key at: https://core.ac.uk/services/api")

    # Process in chunks for progress tracking
    chunk_size = 10
    all_results = {}

    for i in range(0, len(papers_to_process), chunk_size):
        chunk = papers_to_process[i : i + chunk_size]
        chunk_num = i // chunk_size + 1
        total_chunks = (len(papers_to_process) + chunk_size - 1) // chunk_size

        print(f"\nProcessing chunk {chunk_num}/{total_chunks} ({len(chunk)} papers)...")

        # Enrich chunk
        chunk_results = enricher.enrich_batch(chunk, use_title_fallback=use_title_fallback)
        all_results.update(chunk_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Enriched: {stats['enriched']}/{stats['total_processed']}")
        if stats["enriched"] > 0:
            print(f"  Full text found: {stats['has_fulltext']} ({stats['fulltext_rate']})")
            print(f"  PDFs available: {stats['has_pdf']} ({stats['pdf_rate']})")

    # Save enriched papers
    print("\nSaving enriched papers...")
    for key, (paper_id, original_paper) in papers_by_id.items():
        if key in all_results:
            enrichment = all_results[key]

            # Add CORE fields with prefix
            for field, value in enrichment.items():
                if value is not None:  # Only add non-null values
                    original_paper[f"core_{field}"] = value

        # Save paper (enriched or not)
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(original_paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate report
    final_stats = enricher.get_statistics()
    report = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_stage": "8_core_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_processed": len(papers_to_process),
            "papers_enriched": final_stats["enriched"],
            "papers_failed": final_stats["failed"],
            "enrichment_rate": final_stats["enrichment_rate"],
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / len(papers_to_process), 2) if papers_to_process else 0,
        },
        "fulltext_discovery": {
            "papers_with_fulltext": final_stats["has_fulltext"],
            "fulltext_rate": final_stats["fulltext_rate"],
            "papers_with_pdf": final_stats["has_pdf"],
            "pdf_rate": final_stats["pdf_rate"],
            "papers_with_repository": final_stats["has_repository"],
        },
        "errors": final_stats["errors"],
    }

    report_file = output_path / "core_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\nEnrichment complete!")
    print(
        f"  Papers enriched: {final_stats['enriched']}/{len(papers_to_process)} ({final_stats['enrichment_rate']})"
    )
    print(f"  Full text found: {final_stats['has_fulltext']} ({final_stats['fulltext_rate']})")
    print(f"  PDFs available: {final_stats['has_pdf']} ({final_stats['pdf_rate']})")
    print(f"  Processing time: {elapsed_time:.1f} seconds")
    print(f"  Report saved to: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enrich papers with CORE repository metadata")
    parser.add_argument("--input", default="pubmed_enriched_final", help="Input directory with papers")
    parser.add_argument("--output", default="core_enriched", help="Output directory")
    parser.add_argument("--api-key", help="CORE API key for higher rate limits")
    parser.add_argument("--no-title-fallback", action="store_true", help="Don't use title search as fallback")
    parser.add_argument("--test", action="store_true", help="Test with small dataset")

    args = parser.parse_args()

    if args.test:
        # Test with a single paper
        enricher = COREEnricher(api_key=args.api_key)

        # Test DOI lookup
        test_doi = "10.1038/s41586-020-2649-2"  # Nature paper

        print(f"Testing with DOI: {test_doi}")
        result = enricher.enrich_single_by_doi(test_doi)

        if result:
            print("\nEnrichment successful!")
            print(json.dumps(result, indent=2))
        else:
            print("Paper not found in CORE")

            # Try title search
            test_title = "A pneumonia outbreak associated with a new coronavirus of probable bat origin"
            print(f"\nTrying title search: {test_title}")
            result = enricher.enrich_single_by_title(test_title)

            if result:
                print("\nEnrichment successful!")
                print(f"Title: {result.get('title', 'N/A')[:60]}")
                print(f"Repository: {result.get('repository', {}).get('name', 'N/A')}")
                print(f"Has PDF: {result.get('has_pdf', False)}")
                print(
                    f"Download URL: {result.get('download_url', 'N/A')[:80] if result.get('download_url') else 'N/A'}"
                )

        # Show statistics
        stats = enricher.get_statistics()
        print(f"\nStatistics: {json.dumps(stats, indent=2)}")
    else:
        # Process directory
        max_papers = 20 if args.test else None  # Limit for testing
        process_directory(
            args.input,
            args.output,
            args.api_key,
            use_title_fallback=not args.no_title_fallback,
            max_papers=max_papers,
        )
