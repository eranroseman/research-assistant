#!/usr/bin/env python3
"""arXiv V5 Unified Enrichment with Checkpoint Support.

Single-file implementation for arXiv preprint discovery and enrichment.
Tracks preprint versions and updates for STEM papers.

Features:
- Checkpoint recovery support for resuming after interruption
- arXiv ID and version history (v1, v2, etc.)
- Categories (cs.AI, math.CO, physics.quant-ph, etc.)
- LaTeX source availability
- Author comments and notes
- Preprint to publication tracking
- ~10-15% coverage (STEM-focused)
- 3-second delay between API calls (arXiv requirement)
"""

import json
import time
import argparse
import sys
import re
from pathlib import Path
from datetime import datetime, UTC
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict, Counter
from defusedxml import ElementTree
from xml.etree import ElementTree as ET
from src.config import (
    ARXIV_MAX_TITLE_LENGTH,
    ARXIV_MIN_TITLE_LENGTH,
    ARXIV_TITLE_MATCH_THRESHOLD,
    HTTP_NOT_FOUND,
)


def create_session() -> requests.Session:
    """Create HTTP session with retry logic and proper user agent."""
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set user agent as required by arXiv
    session.headers.update({"User-Agent": "Research Assistant v5.0 (https://github.com/research-assistant)"})

    return session


def clean_title(title: str) -> str | None:
    """Clean title for arXiv search."""
    if not title:
        return None

    # Remove special characters that might break search
    clean = title.strip()

    # Remove HTML tags if present
    clean = re.sub(r"<[^>]+>", "", clean)

    # Remove excessive whitespace
    clean = re.sub(r"\s+", " ", clean)

    # Truncate very long titles (arXiv has limits)
    if len(clean) > ARXIV_MAX_TITLE_LENGTH:
        clean = clean[:ARXIV_MAX_TITLE_LENGTH]

    return clean if len(clean) > ARXIV_MIN_TITLE_LENGTH else None


def clean_arxiv_id(arxiv_id: str) -> str | None:
    """Clean and validate arXiv ID."""
    if not arxiv_id:
        return None

    clean = arxiv_id.strip()

    # Remove common prefixes
    clean = clean.replace("arXiv:", "")
    clean = clean.replace("arxiv:", "")

    # Remove version number for search (we'll get all versions)
    clean = re.sub(r"v\d+$", "", clean)

    # Validate format
    # New format: YYMM.NNNNN
    if re.match(r"^\d{4}\.\d{4,5}$", clean):
        return clean
    # Old format: archive/YYMMNNN
    if re.match(r"^[a-z\-]+/\d{7}$", clean):
        return clean

    return None


def extract_last_name(author: str) -> str | None:
    """Extract last name from author string."""
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


def find_best_match(entries: list[ET.Element], title: str, authors: list[str] | None) -> ET.Element | None:
    """Find best matching entry from search results using Jaccard similarity."""
    best_entry = None
    best_score = 0.0

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
        author_boost = 0.0
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
        if total_score > best_score and title_score >= ARXIV_TITLE_MATCH_THRESHOLD:
            best_score = total_score
            best_entry = entry

    return best_entry


def parse_arxiv_entry(entry: ET.Element) -> dict[str, Any]:
    """Parse arXiv entry XML into metadata."""
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    enriched: dict[str, Any] = {}

    # Basic metadata
    enriched["title"] = entry.findtext("atom:title", "", ns).strip()
    enriched["abstract"] = entry.findtext("atom:summary", "", ns).strip()

    # arXiv ID and URL
    arxiv_id = entry.findtext("atom:id", "", ns)
    if arxiv_id:
        # Extract ID from URL
        match = re.search(r"arxiv.org/abs/(.+)$", arxiv_id)
        if match:
            enriched["arxiv_id"] = match.group(1)

            # Extract version if present
            version_match = re.search(r"v(\d+)$", enriched["arxiv_id"])
            if version_match:
                enriched["version"] = int(version_match.group(1))  # This is correct, version should be int
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
        enriched["authors"] = authors  # This is correct, authors is a list

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
        enriched["categories"] = categories  # This is correct, categories is a list

    # DOI if available (when paper is published)
    doi_elem = entry.find("arxiv:doi", ns)
    if doi_elem is not None:
        doi = doi_elem.text
        if doi:
            enriched["published_doi"] = doi

    # Journal reference if published
    journal_ref = entry.findtext("arxiv:journal_ref", ns)
    if journal_ref:
        enriched["journal_ref"] = journal_ref  # This is correct, journal_ref is a string

    # Comments (author notes)
    comment = entry.findtext("arxiv:comment", ns)
    if comment:
        enriched["comment"] = comment  # This is correct, comment is a string

    return enriched


def search_by_title_author(
    session: requests.Session,
    title: str,
    last_request_time: list[float],
    stats: dict[str, int],
    authors: list[str] | None = None,
) -> dict[str, Any] | None:
    """Search arXiv by title and optionally authors with rate limiting."""
    base_url = "http://export.arxiv.org/api/query"
    delay = 3.0  # arXiv requires 3-second delay

    try:
        # Clean and prepare title
        clean_title_str = clean_title(title)
        if not clean_title_str:
            stats["invalid_title"] += 1
            return None

        # Build search query
        query = f'ti:"{clean_title_str}"'

        # Add author if provided
        if authors and len(authors) > 0:
            first_author = extract_last_name(authors[0])
            if first_author:
                query += f" AND au:{first_author}"

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - last_request_time[0]
        if time_since_last < delay:
            time.sleep(delay - time_since_last)
        last_request_time[0] = time.time()

        # Search arXiv
        params: dict[str, Any] = {
            "search_query": query,
            "max_results": 5,
            "sortBy": "relevance",
        }

        response = session.get(base_url, params=params, timeout=30)

        if response.status_code == HTTP_NOT_FOUND:
            stats["not_found"] += 1
            return None

        response.raise_for_status()

        # Parse XML response
        root = ElementTree.fromstring(response.content)

        # Find entries
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        if not entries:
            stats["not_found"] += 1
            return None

        # Find best matching entry
        best_match = find_best_match(entries, clean_title_str, authors)

        if best_match is not None:
            result = parse_arxiv_entry(best_match)
            stats["enriched"] += 1

            # Track domain distribution
            if result.get("categories"):
                for cat in result["categories"]:
                    domain = cat.split(".")[0] if "." in cat else cat
                    stats[f"domain_{domain}"] += 1

            return result

        stats["no_match"] += 1
        return None

    except requests.exceptions.Timeout:
        stats["timeout"] += 1
        print(f"Timeout searching for: {title[:50]}...")
    except Exception as e:
        stats["error"] += 1
        print(f"Error searching arXiv: {e}")

    return None


def search_by_arxiv_ids_batch(
    session: requests.Session, arxiv_ids: list[str], last_request_time: list[float], stats: dict[str, int]
) -> dict[str, dict[str, Any]]:
    """Get multiple papers by arXiv IDs in a single request (up to 100 at a time)."""
    base_url = "http://export.arxiv.org/api/query"
    delay = 3.0
    results: dict[str, dict[str, Any]] = {}

    if not arxiv_ids:
        return results

    try:
        # Clean all IDs
        clean_ids = []
        id_map = {}  # Map clean to original
        for arxiv_id in arxiv_ids:
            clean = clean_arxiv_id(arxiv_id)
            if clean:
                clean_ids.append(clean)
                id_map[clean] = arxiv_id

        if not clean_ids:
            return results

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - last_request_time[0]
        if time_since_last < delay:
            time.sleep(delay - time_since_last)
        last_request_time[0] = time.time()

        # Search by ID list (comma-separated)
        params: dict[str, Any] = {"id_list": ",".join(clean_ids), "max_results": len(clean_ids)}

        response = session.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        # Parse XML
        root = ElementTree.fromstring(response.content)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        for entry in entries:
            result = parse_arxiv_entry(entry)
            if result and result.get("arxiv_id"):
                # Map back to original ID format
                clean_id = result["arxiv_id"]
                # Find which original ID this corresponds to
                for orig_id, clean in id_map.items():
                    if clean == clean_id:
                        results[orig_id] = result
                        stats["enriched"] += 1

                        # Track domains
                        if result.get("categories"):
                            for cat in result["categories"]:
                                domain = cat.split(".")[0] if "." in cat else cat
                                stats[f"domain_{domain}"] += 1
                        break

        # Track not found
        for arxiv_id in arxiv_ids:
            if arxiv_id not in results:
                stats["not_found"] += 1

        return results

    except Exception as e:
        stats["error"] += 1
        print(f"Error fetching arXiv IDs batch: {e}")
        return results


def search_by_arxiv_id(
    session: requests.Session, arxiv_id: str, last_request_time: list[float], stats: dict[str, int]
) -> dict[str, Any] | None:
    """Get paper directly by arXiv ID."""
    base_url = "http://export.arxiv.org/api/query"
    delay = 3.0

    try:
        # Clean arXiv ID
        clean_id = clean_arxiv_id(arxiv_id)
        if not clean_id:
            stats["invalid_id"] += 1
            return None

        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - last_request_time[0]
        if time_since_last < delay:
            time.sleep(delay - time_since_last)
        last_request_time[0] = time.time()

        # Search by ID
        params: dict[str, Any] = {"id_list": clean_id, "max_results": 1}

        response = session.get(base_url, params=params, timeout=30)
        response.raise_for_status()

        # Parse XML
        root = ElementTree.fromstring(response.content)
        entry = root.find("{http://www.w3.org/2005/Atom}entry")

        if entry is not None:
            result = parse_arxiv_entry(entry)
            stats["enriched"] += 1

            # Track domains
            if result.get("categories"):
                for cat in result["categories"]:
                    domain = cat.split(".")[0] if "." in cat else cat
                    stats[f"domain_{domain}"] += 1

            return result

        stats["not_found"] += 1
        return None

    except Exception as e:
        stats["error"] += 1
        print(f"Error fetching arXiv ID {arxiv_id}: {e}")

    return None


def load_checkpoint(checkpoint_file: Path) -> dict[str, Any]:
    """Load checkpoint data if it exists."""
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            data: dict[str, Any] = json.load(f)
            return data
    return {"processed_papers": [], "last_chunk": 0, "stats": {}, "all_results": {}}


def save_checkpoint(checkpoint_file: Path, checkpoint_data: dict[str, Any]) -> None:
    """Save checkpoint data."""
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f, indent=2)


def generate_report(
    output_path: Path, total_files: int, total_processed: int, stats: dict[str, int], elapsed_time: float
) -> None:
    """Generate final enrichment report."""
    # Calculate derived statistics
    total = stats.get("enriched", 0) + stats.get("failed", 0)
    enrichment_rate = f"{(stats['enriched'] / total * 100):.1f}%" if total else "0%"

    # Extract domains
    domains = {}
    for key, value in stats.items():
        if key.startswith("domain_"):
            domain = key.replace("domain_", "")
            domains[domain] = value

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pipeline_stage": "arxiv_enrichment",
        "statistics": {
            "total_papers": total_files,
            "papers_processed": total_processed,
            "papers_enriched": stats.get("enriched", 0),
            "papers_failed": stats.get("failed", 0),
            "enrichment_rate": enrichment_rate,
            "processing_time_seconds": round(elapsed_time, 1),
            "avg_time_per_paper": round(elapsed_time / total_processed, 2) if total_processed else 0,
        },
        "preprint_discovery": {
            "papers_found": stats.get("enriched", 0),
            "not_found": stats.get("not_found", 0),
            "no_match": stats.get("no_match", 0),
            "domains": domains,
        },
        "errors": {
            "invalid_title": stats.get("invalid_title", 0),
            "invalid_id": stats.get("invalid_id", 0),
            "no_title": stats.get("no_title", 0),
            "timeout": stats.get("timeout", 0),
            "other": stats.get("error", 0),
        },
    }

    report_file = output_path / "arxiv_enrichment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\nEnrichment complete!")
    print(f"  Papers enriched: {stats.get('enriched', 0)}/{total_processed} ({enrichment_rate})")
    if domains:
        print("  Domain distribution:")
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {domain}: {count} papers")
    print(f"  Processing time: {elapsed_time:.1f} seconds")
    print(f"  Report saved to: {report_file}")


def analyze_enrichment_results(output_dir: Path) -> None:
    """Analyze and report enrichment statistics."""
    report_file = output_dir / "arxiv_enrichment_report.json"
    if not report_file.exists():
        print("No report file found")
        return

    with open(report_file) as f:
        report = json.load(f)

    print("\n" + "=" * 80)
    print("ARXIV ENRICHMENT RESULTS")
    print("=" * 80)

    stats = report["statistics"]
    print("\nProcessing Statistics:")
    print(f"  Total papers: {stats['total_papers']}")
    print(f"  Papers processed: {stats['papers_processed']}")
    print(f"  Papers enriched: {stats['papers_enriched']}")
    print(f"  Enrichment rate: {stats['enrichment_rate']}")
    print(f"  Processing time: {stats['processing_time_seconds']} seconds")

    if "preprint_discovery" in report:
        pd = report["preprint_discovery"]
        print("\nPreprint Discovery:")
        print(f"  Papers found on arXiv: {pd['papers_found']}")
        print(f"  Papers not found: {pd['not_found']}")
        print(f"  No match (low similarity): {pd['no_match']}")

        if pd.get("domains"):
            print("\nDomain Distribution:")
            for domain, count in sorted(pd["domains"].items(), key=lambda x: x[1], reverse=True):
                print(f"    - {domain}: {count} papers")

    # Sample analysis
    papers = list(output_dir.glob("*.json"))[:20]
    if papers:
        categories = []
        versions = []
        published_dois = 0

        for paper_file in papers:
            if paper_file.name in ["arxiv_enrichment_report.json", ".arxiv_checkpoint.json"]:
                continue

            with open(paper_file) as f:
                paper = json.load(f)
                if paper.get("arxiv_categories"):
                    categories.extend(paper["arxiv_categories"])
                if paper.get("arxiv_version"):
                    versions.append(paper["arxiv_version"])
                if paper.get("arxiv_published_doi"):
                    published_dois += 1

        if categories:
            cat_counts = Counter(categories)
            print("\n  Top arXiv Categories in Sample:")
            for cat, count in cat_counts.most_common(5):
                print(f"    - {cat}: {count} papers")

        print(f"\n  Papers with published DOIs: {published_dois} (published after preprint)")


def main() -> None:
    """Main entry point for arXiv enrichment with checkpoint support."""
    parser = argparse.ArgumentParser(description="arXiv V5 Unified Enrichment with Checkpoint Support")
    parser.add_argument("--input", required=True, help="Input directory with papers to enrich")
    parser.add_argument("--output", required=True, help="Output directory for enriched papers")
    parser.add_argument("--reset", action="store_true", help="Reset checkpoint and start fresh")
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process (for testing)")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze existing results")

    args = parser.parse_args()

    # Setup paths
    input_path = Path(args.input)
    output_path = Path(args.output)
    checkpoint_file = output_path / ".arxiv_checkpoint.json"

    # Analyze only mode
    if args.analyze_only:
        if not output_path.exists():
            print(f"Output directory {output_path} does not exist")
            return
        analyze_enrichment_results(output_path)
        return

    # Check input directory
    if not input_path.exists():
        print(f"Error: Input directory {input_path} does not exist")
        sys.exit(1)

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Reset checkpoint if requested
    if args.reset and checkpoint_file.exists():
        checkpoint_file.unlink()
        print("Checkpoint reset")

    # Load checkpoint
    checkpoint_data = load_checkpoint(checkpoint_file)
    processed_papers = set(checkpoint_data.get("processed_papers", []))
    # Note: last_chunk was unused, removed per ruff F841
    all_results = checkpoint_data.get("all_results", {})

    # Initialize statistics
    stats = defaultdict(int, checkpoint_data.get("stats", {}))

    print("=" * 80)
    print("ARXIV V5 UNIFIED ENRICHMENT")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print("Checkpoint support: ENABLED")

    if processed_papers:
        print(f"Resuming from checkpoint: {len(processed_papers)} papers already processed")

    # Create session
    session = create_session()
    last_request_time = [0.0]  # Mutable container for rate limiting

    # Load all papers
    paper_files = list(input_path.glob("*.json"))
    if not paper_files:
        print("No papers found in input directory")
        return

    print(f"\nFound {len(paper_files)} total papers")

    # Prepare papers for enrichment
    papers_to_process: list[dict[str, Any]] = []
    papers_by_id = {}

    for paper_file in paper_files:
        # Skip report and checkpoint files
        if "report" in paper_file.name or paper_file.name.startswith("."):
            continue

        paper_id = paper_file.stem

        # Skip if already processed
        if paper_id in processed_papers:
            continue

        # Apply max papers limit if specified
        if args.max_papers and len(papers_to_process) >= args.max_papers:
            break

        with open(paper_file) as f:
            paper = json.load(f)

            # Skip if already checked in a previous run (either found or not found)
            if paper.get("arxiv_checked"):
                # Still need to keep it for final output
                papers_by_id[paper_id] = paper
                processed_papers.add(paper_id)
                continue

            # Skip if already has arXiv enrichment data
            if paper.get("arxiv_url") or paper.get("arxiv_categories"):
                papers_by_id[paper_id] = paper
                processed_papers.add(paper_id)
                continue

            # Prepare paper dict
            paper_dict = {"id": paper_id, "title": paper.get("title"), "authors": []}

            # Extract authors if available
            if paper.get("authors"):
                authors = paper["authors"]
                if authors and isinstance(authors[0], dict):
                    paper_dict["authors"] = [a.get("name") for a in authors if a.get("name")]
                else:
                    paper_dict["authors"] = authors
            elif paper.get("pubmed_authors"):
                paper_dict["authors"] = paper["pubmed_authors"]
            elif paper.get("openalex_authors"):
                paper_dict["authors"] = [a.get("name") for a in paper["openalex_authors"] if a.get("name")]

            # Check for existing arXiv ID
            if paper.get("arxiv_id"):
                paper_dict["arxiv_id"] = paper["arxiv_id"]

            papers_to_process.append(paper_dict)
            papers_by_id[paper_id] = paper

    # Also load already processed papers for final save
    for paper_id in processed_papers:
        paper_file = input_path / f"{paper_id}.json"
        if paper_file.exists():
            with open(paper_file) as f:
                papers_by_id[paper_id] = json.load(f)

    print(f"Papers to process: {len(papers_to_process)}")

    if not papers_to_process:
        print("\nAll papers already processed!")
        if papers_by_id:
            elapsed_time = checkpoint_data.get("elapsed_time", 0)
            generate_report(output_path, len(paper_files), len(papers_by_id), stats, elapsed_time)
        return

    # Process papers
    start_time = time.time()
    if "elapsed_time" in checkpoint_data:
        start_time -= checkpoint_data["elapsed_time"]

    # Separate papers with arXiv IDs from those without
    papers_with_ids = [p for p in papers_to_process if p.get("arxiv_id")]
    papers_without_ids = [p for p in papers_to_process if not p.get("arxiv_id")]

    print("\nSearching arXiv for preprints...")
    print(f"Papers with arXiv IDs: {len(papers_with_ids)} (will batch process)")
    print(f"Papers without IDs: {len(papers_without_ids)} (need title search)")
    print("Note: arXiv requires 3-second delays between requests")
    print("Expected coverage: ~10-15% for STEM papers")

    # Process papers with arXiv IDs in batches (much faster!)
    if papers_with_ids:
        batch_size = 100  # arXiv can handle up to 100 IDs per request
        total_batches = (len(papers_with_ids) + batch_size - 1) // batch_size

        print(f"\nBatch processing papers with IDs ({total_batches} batches)...")
        for i in range(0, len(papers_with_ids), batch_size):
            batch = papers_with_ids[i : i + batch_size]
            batch_num = i // batch_size + 1

            # Extract IDs for batch query
            batch_ids = {p["id"]: p["arxiv_id"] for p in batch}
            arxiv_ids = list(batch_ids.values())

            print(f"  Batch {batch_num}/{total_batches}: {len(arxiv_ids)} IDs...")

            # Batch query
            batch_results = search_by_arxiv_ids_batch(session, arxiv_ids, last_request_time, stats)

            # Map results back to paper IDs
            for paper_id, arxiv_id in batch_ids.items():
                if arxiv_id in batch_results:
                    all_results[paper_id] = batch_results[arxiv_id]
                else:
                    # Mark as checked but not found (even though it had an ID)
                    all_results[paper_id] = {"checked": True, "found": False, "had_id": arxiv_id}
                processed_papers.add(paper_id)

            # Show progress
            print(f"    Found: {len(batch_results)}/{len(arxiv_ids)}")

            # Save checkpoint after each batch of papers with IDs
            elapsed_so_far = time.time() - start_time
            checkpoint_data = {
                "processed_papers": list(processed_papers),
                "last_chunk": 0,  # Reset for papers without IDs
                "all_results": all_results,
                "stats": dict(stats),
                "elapsed_time": elapsed_so_far,
            }
            save_checkpoint(checkpoint_file, checkpoint_data)

    # Process papers without arXiv IDs (slower, need title search)
    if papers_without_ids:
        print("\nProcessing papers without IDs (individual searches)...")
        chunk_size = 10  # Process in small chunks with checkpoint saves
        total_chunks = (len(papers_without_ids) + chunk_size - 1) // chunk_size

        for chunk_idx in range(total_chunks):
            chunk_start = chunk_idx * chunk_size
            chunk_end = min(chunk_start + chunk_size, len(papers_without_ids))
            chunk = papers_without_ids[chunk_start:chunk_end]
            chunk_num = chunk_idx + 1

            print(f"\nChunk {chunk_num}/{total_chunks} ({len(chunk)} papers)...")

            for paper_dict in chunk:
                paper_id = paper_dict["id"]

                # Skip if already processed (from checkpoint)
                if paper_id in processed_papers:
                    continue

                # Search by title and authors
                title = paper_dict.get("title")
                authors = paper_dict.get("authors", [])

                if title:
                    result = search_by_title_author(session, title, last_request_time, stats, authors)
                    if result:
                        all_results[paper_id] = result
                    else:
                        # Mark as checked but not found
                        all_results[paper_id] = {"checked": True, "found": False}
                        stats["failed"] += 1
                else:
                    # No title, mark as checked but unable to search
                    all_results[paper_id] = {"checked": True, "found": False, "no_title": True}
                    stats["no_title"] += 1
                    stats["failed"] += 1

                # Update processed papers
                processed_papers.add(paper_id)

        # Show progress
        print(f"  Enriched: {stats['enriched']}/{stats.get('enriched', 0) + stats.get('failed', 0)}")
        domains = {k.replace("domain_", ""): v for k, v in stats.items() if k.startswith("domain_")}
        if domains:
            print(f"  Domains: {', '.join(f'{k}:{v}' for k, v in domains.items())}")

        # Save checkpoint after each chunk
        elapsed_so_far = time.time() - start_time
        checkpoint_data = {
            "processed_papers": list(processed_papers),
            "last_chunk": chunk_idx + 1,
            "all_results": all_results,
            "stats": dict(stats),
            "elapsed_time": elapsed_so_far,
        }
        save_checkpoint(checkpoint_file, checkpoint_data)

    # Save enriched papers
    print("\nSaving enriched papers...")
    for paper_id, original_paper in papers_by_id.items():
        if paper_id in all_results:
            enrichment = all_results[paper_id]

            # Check if this is a "checked but not found" marker
            if enrichment.get("checked") and not enrichment.get("found"):
                # Add marker that we already checked
                original_paper["arxiv_checked"] = True
                original_paper["arxiv_found"] = False
                original_paper["arxiv_check_date"] = datetime.now(UTC).isoformat()
                if enrichment.get("had_id"):
                    original_paper["arxiv_checked_id"] = enrichment["had_id"]
                if enrichment.get("no_title"):
                    original_paper["arxiv_check_failed_no_title"] = True
            else:
                # Add actual arXiv fields with prefix
                for field, value in enrichment.items():
                    if value is not None:
                        original_paper[f"arxiv_{field}"] = value

        # Save paper (enriched or not)
        output_file = output_path / f"{paper_id}.json"
        with open(output_file, "w") as f:
            json.dump(original_paper, f, indent=2)

    elapsed_time = time.time() - start_time

    # Generate report
    generate_report(output_path, len(paper_files), len(papers_by_id), stats, elapsed_time)

    # Remove checkpoint file after successful completion
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        print("Checkpoint removed after successful completion")

    # Analyze results
    if stats.get("enriched", 0) > 0:
        analyze_enrichment_results(output_path)


if __name__ == "__main__":
    main()
