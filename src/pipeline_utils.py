#!/usr/bin/env python3
"""Shared utilities for v5 pipeline stages.

Only includes functions used by 3+ stages.
Keep API-specific logic in respective modules.
"""

import json
import re
import time
from pathlib import Path
from typing import Any
from collections.abc import Iterator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session_with_retry(
    max_retries: int = 5,
    backoff_factor: float = 1.0,
    status_forcelist: list[int] | None = None,
    email: str | None = None,
) -> requests.Session:
    """Create HTTP session with exponential backoff retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Backoff factor for exponential delay
        status_forcelist: HTTP status codes to retry on
        email: Optional email for polite pool/user agent

    Returns:
        Configured requests Session

    Used by:
        - crossref_enricher.py
        - semantic_scholar_enricher.py
        - openalex_enricher.py
        - unpaywall_enricher.py
        - pubmed_enricher.py
        - arxiv_enricher.py
    """
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    session = requests.Session()

    retry = Retry(total=max_retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist)

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Add user agent if email provided
    if email:
        session.headers.update({"User-Agent": f"ResearchAssistant/5.0 (mailto:{email})"})

    return session


def clean_doi(doi: str | None) -> str | None:
    """Clean and validate DOI string.

    Args:
        doi: Raw DOI string (may include URL prefix, suffixes, etc.)

    Returns:
        Cleaned DOI or None if invalid

    Examples:
        >>> clean_doi("10.1234/test")
        '10.1234/test'
        >>> clean_doi("https://doi.org/10.1234/test")
        '10.1234/test'
        >>> clean_doi("10.13039/funder")  # Funding DOI
        None

    Used by:
        - crossref_enricher.py
        - semantic_scholar_enricher.py
        - openalex_enricher.py
        - unpaywall_enricher.py
        - pubmed_enricher.py
    """
    if not doi:
        return None

    # Convert to string and strip whitespace
    doi = str(doi).strip()

    # Remove funding DOIs (10.13039 prefix is for funders)
    if "10.13039" in doi:
        return None

    # Remove URL prefixes
    doi = re.sub(r"https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"https?://dx\.doi\.org/", "", doi)

    # Remove trailing punctuation and malformed suffixes
    doi = re.sub(r"[\)\.]$", "", doi)
    doi = re.sub(r"\(reprinted.*", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"/-/DC.*", "", doi)
    doi = re.sub(r"(REVIEWS?|Date\d{4}|\.pdf|\.html|[Ss]upplemental).*$", "", doi)

    # Basic validation
    if not doi.startswith("10."):
        return None

    # Check reasonable length
    if len(doi) < 7 or len(doi) > 200:
        return None

    return doi


def batch_iterator(items: list, batch_size: int) -> Iterator[list]:
    """Yield batches from a list of items.

    Args:
        items: List to batch
        batch_size: Size of each batch

    Yields:
        Batches of items

    Example:
        >>> list(batch_iterator([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]

    Used by:
        - semantic_scholar_enricher.py
        - openalex_enricher.py
        - crossref_enricher.py
        - unpaywall_enricher.py
    """
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def load_checkpoint(checkpoint_file: Path) -> dict[str, Any]:
    """Load checkpoint data if it exists.

    Args:
        checkpoint_file: Path to checkpoint file

    Returns:
        Checkpoint data or empty dict if not found

    Used by:
        - All enrichment stages
        - Post-processing stages
    """
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load checkpoint {checkpoint_file}: {e}")

    return {}


def save_checkpoint_atomic(checkpoint_file: Path, data: dict[str, Any], indent: int = 2) -> bool:
    """Save checkpoint atomically to prevent corruption.

    Uses temp file + rename for atomic write.

    Args:
        checkpoint_file: Path to checkpoint file
        data: Data to save
        indent: JSON indentation (default 2)

    Returns:
        True if saved successfully

    Used by:
        - All enrichment stages
        - Post-processing stages
    """
    try:
        # Ensure parent directory exists
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        temp_file = checkpoint_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=indent)

        # Atomic rename
        temp_file.replace(checkpoint_file)
        return True

    except Exception as e:
        print(f"Error saving checkpoint to {checkpoint_file}: {e}")
        return False


def rate_limit_wait(last_request_time: float, min_interval: float) -> float:
    """Enforce rate limiting between API requests.

    Args:
        last_request_time: Time of last request (from time.time())
        min_interval: Minimum seconds between requests

    Returns:
        Current time after waiting if needed

    Example:
        >>> last_time = rate_limit_wait(last_time, 0.1)  # 10 req/sec

    Used by:
        - crossref_enricher.py (0.1 sec)
        - arxiv_enricher.py (3.0 sec)
        - unpaywall_enricher.py (0.1 sec)
    """
    current_time = time.time()
    time_since_last = current_time - last_request_time

    if time_since_last < min_interval:
        wait_time = min_interval - time_since_last
        time.sleep(wait_time)
        return time.time()

    return current_time


def get_shard_path(base_dir: Path, identifier: str, shard_length: int = 2) -> Path:
    """Get sharded directory path to avoid filesystem limits.

    Shards by first N characters of identifier to limit files per directory.

    Args:
        base_dir: Base directory for sharding
        identifier: Identifier to shard (paper_id, DOI, etc.)
        shard_length: Number of characters for shard (default 2)

    Returns:
        Path with shard directory

    Example:
        >>> get_shard_path(Path("cache"), "PMC123456")
        Path("cache/PM/PMC123456")

    Used by:
        - Post-processing cache management
        - Embedding storage
    """
    if len(identifier) >= shard_length:
        shard = identifier[:shard_length].upper()
    else:
        shard = "XX"  # Fallback for short identifiers

    return base_dir / shard


def format_time_estimate(seconds: float) -> str:
    """Format seconds into human-readable time estimate.

    Args:
        seconds: Number of seconds

    Returns:
        Formatted string like "5 min", "2.5 hours"

    Used by:
        - Progress reporting in multiple stages
    """
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    if seconds < 3600:
        return f"{seconds / 60:.1f} minutes"
    return f"{seconds / 3600:.1f} hours"


# Type hints for common data structures
PaperDict = dict[str, Any]
CheckpointData = dict[str, Any]
