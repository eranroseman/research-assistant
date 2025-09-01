#!/usr/bin/env python3
"""arXiv Enrichment for V5 Pipeline
Tracks preprint versions and updates for STEM papers.

Features:
- arXiv ID and version history (v1, v2, etc.)
- Categories (cs.AI, math.CO, physics.quant-ph, etc.)
- LaTeX source availability
- Author comments and notes
- Preprint to publication tracking
- ~10-15% coverage (STEM-focused)
"""

import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
import re


class ArXivEnricher:
    """Enrich papers with arXiv preprint metadata."""

    def __init__(self):
        """Initialize arXiv enricher.

        Note: arXiv API has no authentication but requires:
        - 3-second delay between requests (recommended)
        - User-Agent header with contact info
        """
        self.base_url = "http://export.arxiv.org/api/query"
        self.session = self._create_session()
        self.stats = defaultdict(int)

        # Rate limiting - arXiv recommends 3 seconds between requests
        self.delay = 3.0
        self.last_request_time = 0

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic."""
        session = requests.Session()
        retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set user agent as required by arXiv
        session.headers.update(
            {"User-Agent": "Research Assistant v5.0 (https://github.com/research-assistant)"}
        )

        return session

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.delay:
            time.sleep(self.delay - time_since_last)
        self.last_request_time = time.time()

    def search_by_title_author(self, title: str, authors: list[str] | None = None) -> dict[str, Any] | None:
        """Search arXiv by title and optionally authors.

        Args:
            title: Paper title
            authors: Optional list of author names

        Returns:
            Enriched metadata or None if not found
        """
        try:
            # Clean and prepare title for search
            clean_title = self._clean_title(title)
            if not clean_title:
                self.stats["invalid_title"] += 1
                return None

            # Build search query
            # Use title in quotes for exact phrase matching
            query = f'ti:"{clean_title}"'

            # Add author if provided (helps with disambiguation)
            if authors and len(authors) > 0:
                # Use first author's last name
                first_author = self._extract_last_name(authors[0])
                if first_author:
                    query += f" AND au:{first_author}"

            # Rate limiting
            self._rate_limit()

            # Search arXiv
            params = {
                "search_query": query,
                "max_results": 5,  # Get top 5 to find best match
                "sortBy": "relevance",
            }

            response = self.session.get(self.base_url, params=params, timeout=30)

            if response.status_code == 404:
                self.stats["not_found"] += 1
                return None

            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            # Find entries (papers)
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")

            if not entries:
                self.stats["not_found"] += 1
                return None

            # Find best matching entry
            best_match = self._find_best_match(entries, clean_title, authors)

            if best_match is not None:
                return self._parse_arxiv_entry(best_match)
            self.stats["no_match"] += 1
            return None

        except requests.exceptions.Timeout:
            self.stats["timeout"] += 1
            print(f"Timeout searching for: {title[:50]}...")
        except Exception as e:
            self.stats["error"] += 1
            print(f"Error searching arXiv: {e}")

        return None

    def search_by_arxiv_id(self, arxiv_id: str) -> dict[str, Any] | None:
        """Get paper directly by arXiv ID.

        Args:
            arxiv_id: arXiv identifier (e.g., "2010.12345" or "cs/0101001")

        Returns:
            Enriched metadata or None if not found
        """
        try:
            # Clean arXiv ID
            clean_id = self._clean_arxiv_id(arxiv_id)
            if not clean_id:
                self.stats["invalid_id"] += 1
                return None

            # Rate limiting
            self._rate_limit()

            # Search by ID
            params = {"id_list": clean_id, "max_results": 1}

            response = self.session.get(self.base_url, params=params, timeout=30)

            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            # Find entry
            entry = root.find("{http://www.w3.org/2005/Atom}entry")

            if entry is not None:
                result = self._parse_arxiv_entry(entry)
                if result:
                    self.stats["enriched"] += 1
                return result
            self.stats["not_found"] += 1
            return None

        except Exception as e:
            self.stats["error"] += 1
            print(f"Error fetching arXiv ID {arxiv_id}: {e}")

        return None

    def _clean_title(self, title: str) -> str | None:
        """Clean title for arXiv search.

        Args:
            title: Raw title string

        Returns:
            Cleaned title or None if invalid
        """
        if not title:
            return None

        # Remove special characters that might break search
        # But keep mathematical notation
        clean = title.strip()

        # Remove HTML tags if present
        clean = re.sub(r"<[^>]+>", "", clean)

        # Remove excessive whitespace
        clean = re.sub(r"\s+", " ", clean)

        # Truncate very long titles (arXiv has limits)
        if len(clean) > 250:
            clean = clean[:250]

        return clean if len(clean) > 5 else None

    def _clean_arxiv_id(self, arxiv_id: str) -> str | None:
        """Clean and validate arXiv ID.

        Args:
            arxiv_id: Raw arXiv ID

        Returns:
            Cleaned ID or None if invalid
        """
        if not arxiv_id:
            return None

        clean = arxiv_id.strip()

        # Remove common prefixes
        clean = clean.replace("arXiv:", "")
        clean = clean.replace("arxiv:", "")

        # Remove version number for search (we'll get all versions)
        clean = re.sub(r"v\d+$", "", clean)

        # Validate format (YYMM.NNNNN or old style like cs/0101001)
        # New format: YYMM.NNNNN
        if re.match(r"^\d{4}\.\d{4,5}$", clean):
            return clean
        # Old format: archive/YYMMNNN
        if re.match(r"^[a-z\-]+/\d{7}$", clean):
            return clean
        return None

    def _extract_last_name(self, author: str) -> str | None:
        """Extract last name from author string.

        Args:
            author: Author name

        Returns:
            Last name or None
        """
        if not author:
            return None

        # Handle "Last, First" format
        if "," in author:
            return author.split(",")[0].strip()

        # Handle "First Last" format
        parts = author.strip().split()
        if parts:
            return parts[-1]

        return None

    def _find_best_match(
        self, entries: list[ET.Element], title: str, authors: list[str] | None
    ) -> ET.Element | None:
        """Find best matching entry from search results.

        Args:
            entries: List of arXiv entries
            title: Clean title to match
            authors: Optional author list

        Returns:
            Best matching entry or None
        """
        best_entry = None
        best_score = 0

        title_lower = title.lower()
        title_words = set(title_lower.split())

        for entry in entries:
            # Get entry title
            entry_title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
            entry_title = re.sub(r"\s+", " ", entry_title).strip()
            entry_title_lower = entry_title.lower()
            entry_words = set(entry_title_lower.split())

            # Calculate title similarity (Jaccard index)
            if title_words and entry_words:
                intersection = len(title_words & entry_words)
                union = len(title_words | entry_words)
                title_score = intersection / union if union > 0 else 0
            else:
                title_score = 0

            # Boost score if authors match
            author_boost = 0
            if authors:
                entry_authors = []
                for author_elem in entry.findall("{http://www.w3.org/2005/Atom}author"):
                    name = author_elem.findtext("{http://www.w3.org/2005/Atom}name", "")
                    if name:
                        entry_authors.append(name.lower())

                # Check if any authors match
                for author in authors:
                    author_lower = author.lower()
                    for entry_author in entry_authors:
                        if author_lower in entry_author or entry_author in author_lower:
                            author_boost = 0.2
                            break

            total_score = title_score + author_boost

            # Require at least 70% title match
            if total_score > best_score and title_score >= 0.7:
                best_score = total_score
                best_entry = entry

        return best_entry

    def _parse_arxiv_entry(self, entry: ET.Element) -> dict[str, Any]:
        """Parse arXiv entry XML into metadata.

        Args:
            entry: XML entry element

        Returns:
            Parsed metadata
        """
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        enriched = {}

        # Basic metadata
        enriched["title"] = entry.findtext("atom:title", "", ns).strip()
        enriched["abstract"] = entry.findtext("atom:summary", "", ns).strip()

        # arXiv ID and URL
        arxiv_id = entry.findtext("atom:id", "", ns)
        if arxiv_id:
            # Extract ID from URL (http://arxiv.org/abs/XXXX.XXXXX)
            match = re.search(r"arxiv.org/abs/(.+)$", arxiv_id)
            if match:
                enriched["arxiv_id"] = match.group(1)

                # Extract version if present
                version_match = re.search(r"v(\d+)$", enriched["arxiv_id"])
                if version_match:
                    enriched["version"] = int(version_match.group(1))
                    # Remove version from ID
                    enriched["arxiv_id"] = enriched["arxiv_id"][: -len(version_match.group(0))]

                # URLs
                enriched["arxiv_url"] = f"https://arxiv.org/abs/{enriched['arxiv_id']}"
                enriched["pdf_url"] = f"https://arxiv.org/pdf/{enriched['arxiv_id']}.pdf"

        # Authors
        authors = []
        for author_elem in entry.findall("atom:author", ns):
            name = author_elem.findtext("atom:name", "", ns)
            if name:
                author_data = {"name": name}

                # Some entries have affiliation
                affiliation = author_elem.findtext("arxiv:affiliation", "", ns)
                if affiliation:
                    author_data["affiliation"] = affiliation

                authors.append(author_data)

        if authors:
            enriched["authors"] = authors

        # Publication dates
        published = entry.findtext("atom:published", "", ns)
        if published:
            enriched["first_submitted"] = published[:10]  # YYYY-MM-DD

        updated = entry.findtext("atom:updated", "", ns)
        if updated and updated != published:
            enriched["last_updated"] = updated[:10]

        # Categories
        categories = []

        # Primary category
        primary_cat = entry.find("arxiv:primary_category", ns)
        if primary_cat is not None:
            primary = primary_cat.get("term")
            if primary:
                categories.append(primary)
                enriched["primary_category"] = primary

        # All categories
        for cat_elem in entry.findall("atom:category", ns):
            cat = cat_elem.get("term")
            if cat and cat not in categories:
                categories.append(cat)

        if categories:
            enriched["categories"] = categories

        # DOI if available (when paper is published)
        doi_elem = entry.find("arxiv:doi", ns)
        if doi_elem is not None:
            doi = doi_elem.text
            if doi:
                enriched["published_doi"] = doi

        # Journal reference if published
        journal_ref = entry.findtext("arxiv:journal_ref", ns)
        if journal_ref:
            enriched["journal_ref"] = journal_ref

        # Comments (author notes)
        comment = entry.findtext("arxiv:comment", ns)
        if comment:
            enriched["comment"] = comment

        # Track statistics
        self.stats["enriched"] += 1
        if categories:
            # Track domain distribution
            for cat in categories:
                domain = cat.split(".")[0] if "." in cat else cat
                self.stats[f"domain_{domain}"] += 1

        return enriched

    def enrich_batch(self, papers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Enrich multiple papers. arXiv doesn't support batch queries,
        so we process individually with rate limiting.

        Args:
            papers: List of paper dicts with 'title' and optionally 'authors'

        Returns:
            Dictionary mapping paper ID to enriched metadata
        """
        results = {}

        for paper in papers:
            paper_id = paper.get("id", paper.get("title", "unknown"))

            # Check if paper already has arXiv ID
            if paper.get("arxiv_id"):
                enriched = self.search_by_arxiv_id(paper["arxiv_id"])
                if enriched:
                    results[paper_id] = enriched
                continue

            # Otherwise search by title and authors
            title = paper.get("title")
            authors = paper.get("authors", [])

            if title:
                enriched = self.search_by_title_author(title, authors)
                if enriched:
                    results[paper_id] = enriched
                else:
                    self.stats["failed"] += 1
            else:
                self.stats["no_title"] += 1

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get enrichment statistics."""
        total = self.stats["enriched"] + self.stats["failed"]

        # Count domains
        domains = {}
        for key, value in self.stats.items():
            if key.startswith("domain_"):
                domain = key.replace("domain_", "")
                domains[domain] = value

        return {
            "total_processed": total,
            "enriched": self.stats["enriched"],
            "failed": self.stats["failed"],
            "enrichment_rate": f"{(self.stats['enriched'] / total * 100):.1f}%" if total else "0%",
            "not_found": self.stats["not_found"],
            "no_match": self.stats["no_match"],
            "domains": domains,
            "errors": {
                "invalid_title": self.stats.get("invalid_title", 0),
                "invalid_id": self.stats.get("invalid_id", 0),
                "no_title": self.stats.get("no_title", 0),
                "timeout": self.stats.get("timeout", 0),
                "other": self.stats.get("error", 0),
            },
        }


def process_directory(input_dir: str, output_dir: str, max_papers: int | None = None):
    """Process all papers in a directory with arXiv enrichment.

    Args:
        input_dir: Directory containing paper JSON files
        output_dir: Directory to save enriched papers
        max_papers: Maximum number of papers to process (for testing)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize enricher
    enricher = ArXivEnricher()

    # Load papers
    paper_files = list(input_path.glob("*.json"))
    if max_papers:
        paper_files = paper_files[:max_papers]

    print(f"Found {len(paper_files)} papers to process")

    # Prepare papers for enrichment
    papers_to_process = []
    papers_by_id = {}

    for paper_file in paper_files:
        # Skip report files
        if "report" in paper_file.name:
            continue

        with open(paper_file) as f:
            paper = json.load(f)

            # Prepare paper dict
            paper_dict = {"id": paper_file.stem, "title": paper.get("title"), "authors": []}

            # Extract authors if available
            if paper.get("authors"):
                paper_dict["authors"] = paper["authors"]
            elif paper.get("pubmed_authors"):
                paper_dict["authors"] = paper["pubmed_authors"]
            elif paper.get("openalex_authors"):
                paper_dict["authors"] = [a.get("name") for a in paper["openalex_authors"] if a.get("name")]

            # Check for existing arXiv ID
            if paper.get("arxiv_id"):
                paper_dict["arxiv_id"] = paper["arxiv_id"]

            papers_to_process.append(paper_dict)
            papers_by_id[paper_file.stem] = paper

    print(f"Processing {len(papers_to_process)} papers")

    # Process papers
    start_time = time.time()

    print("\nSearching arXiv for preprints...")
    print("Note: arXiv requires 3-second delays between requests")
    print("Expected coverage: ~10-15% for STEM papers")

    # Process in chunks for progress tracking
    chunk_size = 10
    all_results = {}

    for i in range(0, len(papers_to_process), chunk_size):
        chunk = papers_to_process[i : i + chunk_size]
        chunk_num = i // chunk_size + 1
        total_chunks = (len(papers_to_process) + chunk_size - 1) // chunk_size

        print(f"\nProcessing chunk {chunk_num}/{total_chunks} ({len(chunk)} papers)...")

        # Enrich chunk
        chunk_results = enricher.enrich_batch(chunk)
        all_results.update(chunk_results)

        # Show progress
        stats = enricher.get_statistics()
        print(f"  Enriched: {stats['enriched']}/{stats['total_processed']}")
        if stats["domains"]:
            print(f"  Domains: {', '.join(f'{k}:{v}' for k, v in stats['domains'].items())}")

    # Save enriched papers
    print("\nSaving enriched papers...")
    for paper_id, original_paper in papers_by_id.items():
        if paper_id in all_results:
            enrichment = all_results[paper_id]

            # Add arXiv fields with prefix
            for field, value in enrichment.items():
                if value is not None:
                    original_paper[f"arxiv_{field}"] = value

        # Save paper (enriched or not)
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(original_paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate report
    final_stats = enricher.get_statistics()
    report = {
        "timestamp": datetime.now().isoformat(),
        "pipeline_stage": "9_arxiv_enrichment",
        "statistics": {
            "total_papers": len(paper_files),
            "papers_processed": len(papers_to_process),
            "papers_enriched": final_stats["enriched"],
            "papers_failed": final_stats["failed"],
            "enrichment_rate": final_stats["enrichment_rate"],
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / len(papers_to_process), 2) if papers_to_process else 0,
        },
        "preprint_discovery": {
            "papers_found": final_stats["enriched"],
            "not_found": final_stats["not_found"],
            "no_match": final_stats["no_match"],
            "domains": final_stats["domains"],
        },
        "errors": final_stats["errors"],
    }

    report_file = output_path / "arxiv_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\nEnrichment complete!")
    print(
        f"  Papers enriched: {final_stats['enriched']}/{len(papers_to_process)} ({final_stats['enrichment_rate']})"
    )
    if final_stats["domains"]:
        print("  Domain distribution:")
        for domain, count in sorted(final_stats["domains"].items(), key=lambda x: x[1], reverse=True):
            print(f"    - {domain}: {count} papers")
    print(f"  Processing time: {elapsed_time:.1f} seconds")
    print(f"  Report saved to: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enrich papers with arXiv preprint metadata")
    parser.add_argument("--input", default="pubmed_enriched_final", help="Input directory with papers")
    parser.add_argument("--output", default="arxiv_enriched", help="Output directory")
    parser.add_argument("--test", action="store_true", help="Test with single paper")

    args = parser.parse_args()

    if args.test:
        # Test with a known arXiv paper
        enricher = ArXivEnricher()

        # Test with a CS paper likely on arXiv
        test_title = "Attention Is All You Need"
        test_authors = ["Vaswani", "Shazeer"]

        print(f"Testing with title: {test_title}")
        result = enricher.search_by_title_author(test_title, test_authors)

        if result:
            print("\nEnrichment successful!")
            print(json.dumps(result, indent=2))
        else:
            # Try another paper
            test_title_2 = "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
            print(f"\nTrying another title: {test_title_2}")
            result = enricher.search_by_title_author(test_title_2)

            if result:
                print("\nEnrichment successful!")
                print(f"Title: {result.get('title', 'N/A')[:60]}")
                print(f"arXiv ID: {result.get('arxiv_id', 'N/A')}")
                print(f"Categories: {result.get('categories', [])}")
                print(f"PDF URL: {result.get('pdf_url', 'N/A')}")

        # Show statistics
        stats = enricher.get_statistics()
        print(f"\nStatistics: {json.dumps(stats, indent=2)}")
    else:
        # Process directory
        max_papers = 20 if args.test else None
        process_directory(args.input, args.output, max_papers)
