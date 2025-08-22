#!/usr/bin/env python3
"""
Knowledge Base Builder for Research Assistant v4.0.

This module builds and maintains a searchable knowledge base from Zotero libraries.

Key Features:
- Multi-QA MPNet embeddings: 768-dimensional vectors optimized for healthcare & scientific papers
- FAISS index: Enables fast similarity search across thousands of papers
- Smart incremental updates: Only processes new/changed papers
- PDF text extraction: Extracts and caches full text from PDFs
- Quality scoring: Rates papers 0-100 based on study type and metadata
- Section extraction: Identifies standard academic sections (methods, results, etc.)

Architecture:
- Connects to Zotero via local API (port 23119)
- Reads PDFs from Zotero storage directory
- Caches PDF text to avoid re-extraction
- Caches embeddings for unchanged papers
- Stores papers as markdown files for easy access

Usage:
    # Build from scratch or incremental update
    python src/build_kb.py

    # Force complete rebuild
    python src/build_kb.py --rebuild

    # Quick demo with 5 papers
    python src/build_kb.py --demo
"""

import contextlib
import json
import os
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import requests
from tqdm import tqdm

# ============================================================================
# CONFIGURATION - Import from centralized config.py
# ============================================================================

try:
    # For module imports (from tests)
    from .config import (
        # Version
        KB_VERSION,
        # Paths
        KB_DATA_PATH,
        DEFAULT_ZOTERO_PATH,
        DEFAULT_API_URL,
        PAPERS_DIR,
        INDEX_FILE,
        METADATA_FILE,
        SECTIONS_INDEX_FILE,
        PDF_CACHE_FILE,
        EMBEDDING_CACHE_FILE,
        EMBEDDING_DATA_FILE,
        # Model
        EMBEDDING_MODEL,
        EMBEDDING_DIMENSIONS,
        EMBEDDING_BATCH_SIZE,
        # Batch sizes
        BATCH_SIZE_GPU_HIGH,
        BATCH_SIZE_GPU_MEDIUM,
        BATCH_SIZE_GPU_LOW,
        BATCH_SIZE_CPU_HIGH,
        BATCH_SIZE_CPU_MEDIUM,
        BATCH_SIZE_CPU_LOW,
        # Text processing
        MAX_SECTION_LENGTH,
        ABSTRACT_PREVIEW_LENGTH,
        CONCLUSION_PREVIEW_LENGTH,
        MIN_FULL_TEXT_LENGTH,
        MIN_TEXT_FOR_CONCLUSION,
        # Sample size
        MIN_SAMPLE_SIZE,
        MAX_SAMPLE_SIZE,
        # Display limits
        MAX_MISSING_FILES_DISPLAY,
        MAX_SMALL_PDFS_DISPLAY,
        MAX_ORPHANED_FILES_WARNING,
        MAX_MISSING_PDFS_IN_REPORT,
        # API config
        ZOTERO_PORT,
        API_TIMEOUT_SHORT,
        API_TIMEOUT_LONG,
        API_BATCH_SIZE,
        # Time estimates
        TIME_PER_PAPER_GPU_MIN,
        TIME_PER_PAPER_GPU_MAX,
        TIME_PER_PAPER_CPU_MIN,
        TIME_PER_PAPER_CPU_MAX,
        LONG_OPERATION_THRESHOLD,
        # Paper ID
        PAPER_ID_DIGITS,
        VALID_PAPER_TYPES,
        # PDF processing
        PDF_TIMEOUT_SECONDS,
    )
except ImportError:
    # For direct script execution
    from config import (
        # Version
        KB_VERSION,
        # Paths
        KB_DATA_PATH,
        DEFAULT_ZOTERO_PATH,
        DEFAULT_API_URL,
        PAPERS_DIR,
        INDEX_FILE,
        METADATA_FILE,
        SECTIONS_INDEX_FILE,
        PDF_CACHE_FILE,
        EMBEDDING_CACHE_FILE,
        EMBEDDING_DATA_FILE,
        # Model
        EMBEDDING_MODEL,
        EMBEDDING_DIMENSIONS,
        EMBEDDING_BATCH_SIZE,
        # Batch sizes
        BATCH_SIZE_GPU_HIGH,
        BATCH_SIZE_GPU_MEDIUM,
        BATCH_SIZE_GPU_LOW,
        BATCH_SIZE_CPU_HIGH,
        BATCH_SIZE_CPU_MEDIUM,
        BATCH_SIZE_CPU_LOW,
        # Text processing
        MAX_SECTION_LENGTH,
        ABSTRACT_PREVIEW_LENGTH,
        CONCLUSION_PREVIEW_LENGTH,
        MIN_FULL_TEXT_LENGTH,
        MIN_TEXT_FOR_CONCLUSION,
        # Sample size
        MIN_SAMPLE_SIZE,
        MAX_SAMPLE_SIZE,
        # Display limits
        MAX_MISSING_FILES_DISPLAY,
        MAX_SMALL_PDFS_DISPLAY,
        MAX_ORPHANED_FILES_WARNING,
        MAX_MISSING_PDFS_IN_REPORT,
        # API config
        ZOTERO_PORT,
        API_TIMEOUT_SHORT,
        API_TIMEOUT_LONG,
        API_BATCH_SIZE,
        # Time estimates
        TIME_PER_PAPER_GPU_MIN,
        TIME_PER_PAPER_GPU_MAX,
        TIME_PER_PAPER_CPU_MIN,
        TIME_PER_PAPER_CPU_MAX,
        LONG_OPERATION_THRESHOLD,
        # Paper ID
        PAPER_ID_DIGITS,
        VALID_PAPER_TYPES,
        # PDF processing
        PDF_TIMEOUT_SECONDS,
    )


def detect_study_type(text: str) -> str:
    """Detect study type from paper text for quality scoring.

    Uses keyword matching to identify study design in order of evidence
    hierarchy (highest to lowest). This classification is used for the
    quality scoring system.

    Study types by evidence level:
    1. Systematic reviews/meta-analyses (highest evidence)
    2. Randomized controlled trials (RCTs)
    3. Cohort studies (longitudinal observation)
    4. Case-control studies (retrospective)
    5. Cross-sectional studies (snapshot)
    6. Case reports (individual cases)

    Args:
        text: Combined title and abstract text

    Returns:
        Study type identifier (e.g., 'systematic_review', 'rct', 'cohort')
    """
    text_lower = text.lower()

    # Check in order of evidence hierarchy
    if "systematic review" in text_lower or "meta-analysis" in text_lower or "meta analysis" in text_lower:
        return "systematic_review"
    if any(
        term in text_lower
        for term in [
            "randomized",
            "randomised",
            "randomized controlled",
            "randomised controlled",
            "rct",
        ]
    ):
        return "rct"
    if "cohort" in text_lower:
        return "cohort"
    if "case-control" in text_lower or "case control" in text_lower:
        return "case_control"
    if "cross-sectional" in text_lower or "cross sectional" in text_lower:
        return "cross_sectional"
    if "case report" in text_lower or "case series" in text_lower:
        return "case_report"
    return "study"  # Default type


def extract_rct_sample_size(text: str, study_type: str) -> int | None:
    """Extract sample size from RCT abstracts for quality scoring.

    Searches for common patterns indicating total sample size in
    randomized controlled trials. Used to award quality bonus points
    for larger trials (more statistical power).

    Common patterns detected:
    - "randomized N patients/participants"
    - "N patients were randomized"
    - "n = N were randomized"
    - "enrolled and randomized N"
    - "trial with N patients"

    Args:
        text: Paper abstract text to search
        study_type: Study type (only processes if 'rct')

    Returns:
        Sample size as integer (validated 10-100,000 range), or
        None if not found, not an RCT, or outside valid range
    """
    if study_type != "rct":
        return None

    text_lower = text.lower()

    # RCT-specific patterns for sample size extraction
    patterns = [
        r"randomized\s+(\d+)\s+patients?",
        r"randomised\s+(\d+)\s+patients?",
        r"(\d+)\s+patients?\s+were\s+randomized",
        r"(\d+)\s+patients?\s+were\s+randomised",
        r"randomized\s+n\s*=\s*(\d+)",
        r"randomised\s+n\s*=\s*(\d+)",
        r"n\s*=\s*(\d+)\s*were\s+randomized",
        r"n\s*=\s*(\d+)\s*were\s+randomised",
        r"enrolled\s+and\s+randomized\s+(\d+)",
        r"enrolled\s+and\s+randomised\s+(\d+)",
        r"(\d+)\s+participants?\s+were\s+randomly",
        r"(\d+)\s+subjects?\s+were\s+randomized",
        r"(\d+)\s+subjects?\s+were\s+randomised",
        r"enrolling\s+(\d+)\s+patients?",  # For "enrolling 324 patients"
        r"trial\s+with\s+(\d+)\s+patients?",  # For "trial with 150 patients"
        r"enrolled\s+(\d+)\s+patients?",  # For "enrolled 1234 patients"
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            n = int(match.group(1))
            # Validate reasonable sample size range
            if MIN_SAMPLE_SIZE <= n <= MAX_SAMPLE_SIZE:
                return n

    return None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def estimate_processing_time(num_items: int, device: str = "cpu") -> tuple[float, float, str]:
    """Calculate processing time estimates for user feedback.

    Provides realistic time estimates based on hardware capabilities
    to set user expectations for long-running operations.

    Args:
        num_items: Number of papers to process
        device: Processing device ('cpu' or 'cuda')

    Returns:
        Tuple containing:
        - min_seconds: Best-case time estimate
        - max_seconds: Worst-case time estimate
        - formatted_message: Human-readable time range (e.g., "2-5 minutes")
    """
    if device == "cuda":
        seconds_per_item_min = TIME_PER_PAPER_GPU_MIN
        seconds_per_item_max = TIME_PER_PAPER_GPU_MAX
    else:
        seconds_per_item_min = TIME_PER_PAPER_CPU_MIN
        seconds_per_item_max = TIME_PER_PAPER_CPU_MAX

    time_min = num_items * seconds_per_item_min
    time_max = num_items * seconds_per_item_max

    if time_min > 60:
        minutes_min = int(time_min / 60)
        minutes_max = int(time_max / 60)
        message = f"{minutes_min}-{minutes_max} minutes"
    else:
        message = f"{int(time_min)}-{int(time_max)} seconds"

    return time_min, time_max, message


def confirm_long_operation(estimated_seconds: float, operation_name: str = "Processing") -> bool:
    """Ask user confirmation for long operations.

    Args:
        estimated_seconds: Estimated time in seconds
        operation_name: Name of the operation for context

    Returns:
        True to continue, False to abort
    """
    if estimated_seconds > LONG_OPERATION_THRESHOLD:
        response = input("Continue? (Y/n): ").strip().lower()
        if response == "n":
            print("Aborted by user")
            return False
    return True


def display_operation_summary(
    operation: str,
    item_count: int,
    time_estimate: str | None = None,
    device: str | None = None,
    storage_estimate_mb: float | None = None,
) -> None:
    """Display consistent operation summary.

    Args:
        operation: Name of the operation
        item_count: Number of items to process
        time_estimate: Formatted time estimate
        device: Processing device
        storage_estimate_mb: Estimated storage in MB
    """
    print(f"\n{operation}:")
    print(f"  Items to process: {item_count:,}")
    if time_estimate:
        print(f"  Estimated time: {time_estimate}")
    if device:
        print(f"  Device: {device.upper()}")
    if storage_estimate_mb:
        print(f"  Storage needed: ~{storage_estimate_mb:.0f} MB")


def format_truncated_list(
    items: list[Any],
    max_display: int = 10,
    item_formatter: Any = str,
    continuation_message: str | None = None,
) -> list[str]:
    """Format a list with truncation for display.

    Args:
        items: List of items to format
        max_display: Maximum number of items to show
        item_formatter: Function to format each item
        continuation_message: Custom message for remaining items

    Returns:
        List of formatted strings
    """
    lines = []
    for item in items[:max_display]:
        lines.append(item_formatter(item))

    if len(items) > max_display:
        remaining = len(items) - max_display
        if continuation_message:
            lines.append(continuation_message.format(count=remaining))
        else:
            lines.append(f"... and {remaining} more")

    return lines


def format_error_message(
    error_type: str, details: str, suggestion: str | None = None, context: dict[str, Any] | None = None
) -> str:
    """Format consistent, helpful error messages.

    Args:
        error_type: Type of error
        details: Error details
        suggestion: How to fix the error
        context: Additional context information

    Returns:
        Formatted error message
    """
    lines = [f"\nERROR: {error_type}"]
    lines.append(f"  Details: {details}")

    if context:
        for key, value in context.items():
            lines.append(f"  {key}: {value}")

    if suggestion:
        lines.append(f"\n  How to fix: {suggestion}")

    return "\n".join(lines)


class KnowledgeBaseBuilder:
    """Build and maintain a searchable knowledge base from Zotero library.

    Main class responsible for the entire knowledge base lifecycle:

    **Data Sources:**
    - Zotero SQLite database: Paper metadata and attachment paths
    - Zotero storage directory: PDF files for full text extraction
    - Zotero API (port 23119): Real-time library synchronization

    **Processing Pipeline:**
    1. Extract papers from Zotero (metadata + PDFs)
    2. Deduplicate by DOI and normalized title
    3. Extract text sections from PDFs
    4. Generate Multi-QA MPNet embeddings for semantic search
    5. Build FAISS index for fast similarity search
    6. Save as markdown files with metadata

    **Optimization Features:**
    - PDF text caching: Avoids re-extracting unchanged PDFs
    - Embedding caching: Reuses embeddings for unchanged papers
    - Incremental updates: Only processes new/changed papers
    - Batch processing: Optimizes GPU/CPU utilization

    **Output Structure:**
    - kb_data/papers/: Individual paper markdown files
    - kb_data/index.faiss: Search index
    - kb_data/metadata.json: Paper metadata and mappings
    - kb_data/.pdf_text_cache.json: Cached PDF text
    - kb_data/.embedding_cache.json: Cached embeddings
    """

    def __init__(self, knowledge_base_path: str = "kb_data", zotero_data_dir: str | None = None):
        """Initialize the knowledge base builder.

        Sets up paths, detects available hardware (GPU/CPU), and prepares
        for lazy loading of models and caches.

        Args:
            knowledge_base_path: Directory to store the knowledge base
                Default: "kb_data" in current directory
            zotero_data_dir: Path to Zotero data directory
                Default: ~/Zotero (standard Zotero location)
        """
        self.knowledge_base_path = Path(knowledge_base_path)
        self.papers_path = self.knowledge_base_path / "papers"
        self.index_file_path = self.knowledge_base_path / "index.faiss"
        self.metadata_file_path = self.knowledge_base_path / "metadata.json"
        self.cache_file_path = self.knowledge_base_path / ".pdf_text_cache.json"

        self.knowledge_base_path.mkdir(exist_ok=True)
        self.papers_path.mkdir(exist_ok=True)

        # Set Zotero data directory (default to ~/Zotero)
        if zotero_data_dir:
            self.zotero_data_dir = Path(zotero_data_dir)
        else:
            self.zotero_data_dir = Path.home() / "Zotero"

        self.zotero_db_path = self.zotero_data_dir / "zotero.sqlite"
        self.zotero_storage_path = self.zotero_data_dir / "storage"

        self._embedding_model: Any = None
        self.cache: dict[str, dict[str, Any]] | None = None  # PDF text cache, loaded on demand
        self.embedding_cache: dict[str, Any] | None = None  # Embedding vectors cache, loaded on demand

        # Detect device early for time estimates
        try:
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            self.device = "cpu"

    @property
    def embedding_model(self) -> Any:
        """Lazy load the Multi-QA MPNet embedding model.

        Multi-QA MPNet (Multi-Question-Answer Mean Pooling Network) is optimized
        for diverse question-answering tasks including healthcare and scientific
        literature. Produces 768-dimensional vectors with excellent performance
        on healthcare systems research while maintaining CS accuracy.

        The model is loaded only when first needed to reduce startup time.
        Automatically detects and uses GPU if available for faster processing.

        Returns:
            SentenceTransformer model configured for Multi-QA MPNet embeddings
        """
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            # Device already detected in __init__, just report it
            if self.device == "cuda":
                print("GPU detected! Using CUDA for faster embeddings")
            else:
                print("No GPU detected, using CPU")

            # Load Multi-QA MPNet model optimized for healthcare and scientific papers
            print("Loading Multi-QA MPNet embedding model...")
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL, device=self.device)
            self.model_version = "Multi-QA MPNet"
            print(f"Multi-QA MPNet model loaded successfully on {self.device}")

        return self._embedding_model

    def load_cache(self) -> dict[str, dict[str, Any]]:
        """Load the PDF text cache from disk.

        The cache stores extracted PDF text to avoid re-processing unchanged
        files. Each entry includes the text, file size, modification time,
        and extraction timestamp for validation.

        Returns:
            Dictionary mapping Zotero paper keys to cached PDF text and metadata
        """
        if self.cache is not None:
            return self.cache

        if self.cache_file_path.exists():
            try:
                with self.cache_file_path.open(encoding="utf-8") as f:
                    self.cache = json.load(f)
                    # Silent - cache loading is an implementation detail
                    return self.cache
            except (json.JSONDecodeError, ValueError):
                # Handle corrupted cache by starting fresh
                print("Warning: Cache file corrupted, starting fresh")
                self.cache = {}
                return self.cache

        self.cache = {}
        return self.cache

    def save_cache(self) -> None:
        """Save the PDF text cache to disk for reuse in future builds."""
        if self.cache is None:
            return
        with self.cache_file_path.open("w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
            # Silent - cache saving is an implementation detail

    def clear_cache(self) -> None:
        """Clear the PDF text cache."""
        self.cache = {}
        if self.cache_file_path.exists():
            self.cache_file_path.unlink()
            print("Cleared PDF text cache")

    def load_embedding_cache(self) -> dict[str, Any]:
        """Load the embedding cache from disk.

        Returns:
            Dictionary with 'embeddings' numpy array and 'hashes' list
        """
        if self.embedding_cache is not None:
            return self.embedding_cache

        # Simple JSON cache only
        json_cache_path = self.knowledge_base_path / ".embedding_cache.json"
        npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"

        if json_cache_path.exists() and npy_cache_path.exists():
            import numpy as np

            with json_cache_path.open() as f:
                cache_meta = json.load(f)
            embeddings = np.load(npy_cache_path, allow_pickle=False)
            self.embedding_cache = {
                "embeddings": embeddings,
                "hashes": cache_meta["hashes"],
                "model_name": cache_meta["model_name"],
            }
            # Silent - just return the cache
            return self.embedding_cache

        self.embedding_cache = {"embeddings": None, "hashes": []}
        return self.embedding_cache

    def save_embedding_cache(self, embeddings: Any, hashes: list[str]) -> None:
        """Save embeddings to cache files (JSON metadata + NPY data).

        Args:
            embeddings: Numpy array of embedding vectors
            hashes: List of content hashes for cache validation
        """
        import numpy as np

        # Save metadata to JSON
        json_cache_path = self.knowledge_base_path / ".embedding_cache.json"
        cache_meta = {
            "hashes": hashes,
            "model_name": "Multi-QA MPNet",
            "created_at": datetime.now(UTC).isoformat(),
        }
        with json_cache_path.open("w") as f:
            json.dump(cache_meta, f, indent=2)

        # Save embeddings to NPY
        npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"
        np.save(npy_cache_path, embeddings, allow_pickle=False)
        # Silent - cache saved

    def clear_embedding_cache(self) -> None:
        """Clear the embedding cache."""
        self.embedding_cache = None
        json_cache_path = self.knowledge_base_path / ".embedding_cache.json"
        npy_cache_path = self.knowledge_base_path / ".embedding_data.npy"
        if json_cache_path.exists():
            json_cache_path.unlink()
        if npy_cache_path.exists():
            npy_cache_path.unlink()
        print("Cleared embedding cache")

    def get_embedding_hash(self, text: str) -> str:
        """Generate SHA256 hash for embedding cache key.

        Args:
            text: Text to hash

        Returns:
            Hexadecimal hash string
        """
        import hashlib

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get_optimal_batch_size(self) -> int:
        """Determine optimal batch size based on available memory.

        Returns:
            Batch size optimized for GPU/CPU memory constraints
        """
        try:
            import psutil

            mem = psutil.virtual_memory()
            available_gb = mem.available / (1024**3)
            total_gb = mem.total / (1024**3)

            # Adjust batch size for GPU if available
            if hasattr(self, "device") and self.device == "cuda":
                try:
                    import torch

                    if torch.cuda.is_available():
                        # Get GPU memory in GB
                        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                        if gpu_memory > 8:
                            batch_size = 256
                        elif gpu_memory > 4:
                            batch_size = 128
                        else:
                            batch_size = 64
                        print(f"Using batch size {batch_size} for GPU with {gpu_memory:.1f}GB memory")
                        return batch_size
                except Exception:  # noqa: S110
                    pass

            # CPU memory-based batch sizing
            if available_gb > 16:
                batch_size = 256
            elif available_gb > 8:
                batch_size = 128
            else:
                batch_size = 64

            print(
                f"Using batch size {batch_size} based on {available_gb:.1f}GB available (of {total_gb:.1f}GB total)"
            )

            # Note: On CPU, batch size has minimal impact on speed since the bottleneck
            # is model computation, not memory bandwidth. Larger batches may even be slower.
            return batch_size

        except ImportError:
            # If psutil not available, use conservative default
            return 128  # Better than original 64

    def _test_zotero_connection(self, api_url: str | None = None) -> None:
        """Test Zotero API connection without side effects."""
        base_url = api_url or "http://localhost:23119/api"
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code != 200:
                raise ConnectionError("Zotero API returned non-200 status")
        except requests.exceptions.RequestException as error:
            raise ConnectionError(f"Cannot connect to Zotero local API: {error}") from error

    def clean_knowledge_base(self) -> None:
        """Clean up existing knowledge base files before rebuilding.

        Removes:
        - Old paper markdown files in papers/ directory
        - Previous FAISS index
        - Previous metadata.json

        Preserves:
        - PDF text cache (.pdf_text_cache.json) - expensive to rebuild
        - Embedding cache (.embedding_cache.json) - can be reused
        """
        # Remove old paper files
        if self.papers_path.exists():
            paper_files = list(self.papers_path.glob("paper_*.md"))
            if paper_files:
                for paper_file in paper_files:
                    paper_file.unlink()
                print(f"Cleaned {len(paper_files)} old paper files")

        # Remove old index and metadata
        if self.index_file_path.exists():
            self.index_file_path.unlink()
            print("Removed old FAISS index")

        if self.metadata_file_path.exists():
            self.metadata_file_path.unlink()
            print("Removed old metadata file")

    def check_for_changes(self, api_url: str | None = None) -> dict[str, Any]:
        """Detect changes in Zotero library since last build.

        Performs integrity checks and identifies:
        - New papers added to Zotero
        - Papers with updated PDFs (checks file size/modification time)
        - Papers deleted from Zotero

        Args:
            api_url: Optional custom Zotero API URL

        Returns:
            Dictionary with counts of new, updated, and deleted papers

        Raises:
            ValueError: If knowledge base is corrupted or incompatible version
        """
        with open(self.metadata_file_path) as f:
            metadata = json.load(f)

        # Version must be 4.0
        if metadata.get("version") != "4.0":
            raise ValueError("Knowledge base must be rebuilt. Delete kb_data/ and run build_kb.py")

        # Integrity check: Check for duplicate IDs
        paper_ids = [p["id"] for p in metadata["papers"]]
        unique_ids = set(paper_ids)
        if len(unique_ids) != len(paper_ids):
            duplicates = [id for id in unique_ids if paper_ids.count(id) > 1]
            print(f"\nINTEGRITY ERROR: Found duplicate paper IDs: {duplicates}")
            print(f"  {len(paper_ids)} papers but only {len(unique_ids)} unique IDs")
            print("  Knowledge base is corrupted! Please rebuild with build_kb.py --rebuild")
            raise ValueError("Knowledge base integrity check failed: duplicate IDs detected")

        # Integrity check: Verify paper files exist
        papers_dir = self.knowledge_base_path / "papers"
        if papers_dir.exists():
            expected_files = {p["filename"] for p in metadata["papers"]}
            actual_files = {f.name for f in papers_dir.glob("paper_*.md")}
            missing_files = expected_files - actual_files
            extra_files = actual_files - expected_files

            if missing_files:
                print(f"\nWARNING: {len(missing_files)} paper files missing from disk")
                if len(missing_files) <= 10:
                    print(f"   Missing: {missing_files}")

            if extra_files and len(extra_files) > 5:  # Allow a few extra files
                print(f"\nWARNING: {len(extra_files)} orphaned paper files on disk")

        existing_keys = {p["zotero_key"] for p in metadata["papers"]}

        # Get current items from Zotero (minimal fetch)
        current_items = self.get_zotero_items_minimal(api_url)
        current_keys = {item["key"] for item in current_items}

        new = current_keys - existing_keys
        deleted = existing_keys - current_keys

        # Quick PDF check (just size/mtime)
        updated = []
        pdf_map = self.get_pdf_paths_from_sqlite()

        for paper in metadata["papers"]:
            key = paper["zotero_key"]
            if key in current_keys and key in pdf_map:
                old_info = paper.get("pdf_info", {})
                new_info = self.get_pdf_info(pdf_map[key])
                if old_info != new_info:
                    updated.append(key)

        # Check if FAISS index exists and has correct number of embeddings
        index_exists = self.index_file_path.exists()
        index_size_correct = False

        if index_exists:
            try:
                import faiss

                index = faiss.read_index(str(self.index_file_path))
                index_size_correct = index.ntotal == len(metadata["papers"])
                if not index_size_correct:
                    diff = len(metadata["papers"]) - index.ntotal
                    if diff > 0:
                        print(
                            f"\nNote: Index has {index.ntotal} embeddings, {len(metadata['papers'])} papers exist"
                        )
                        print(f"  Will generate embeddings for {diff} missing papers")
            except Exception as error:
                print(f"\nWARNING: Could not validate index: {error}")
                index_exists = False

        # Only force reindex if index is completely missing or corrupted
        needs_reindex = not index_exists

        return {
            "new": len(new),
            "updated": len(updated),
            "deleted": len(deleted),
            "needs_reindex": needs_reindex,
            "total": len(new)
            + len(updated)
            + len(deleted)
            + (len(metadata["papers"]) if needs_reindex else 0),
            "new_keys": new,
            "updated_keys": updated,
            "deleted_keys": deleted,
        }

    def get_zotero_items_minimal(self, api_url: str | None = None) -> list[dict[str, Any]]:
        """Get minimal paper info from Zotero for change detection.

        Args:
            api_url: Optional custom Zotero API URL

        Returns:
            List of paper dictionaries with 'key' field
        """
        base_url = api_url or "http://localhost:23119/api"

        # Test connection
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code != 200:
            raise ConnectionError("Cannot connect to Zotero API")

        all_items = []
        start = 0
        limit = 100

        while True:
            response = requests.get(
                f"{base_url}/users/0/items",
                params={"start": str(start), "limit": str(limit), "fields": "key,itemType"},
                timeout=10,
            )
            response.raise_for_status()
            batch = response.json()

            if not batch:
                break

            # Filter for papers only
            for item in batch:
                if item.get("data", {}).get("itemType") in [
                    "journalArticle",
                    "conferencePaper",
                    "preprint",
                    "book",
                    "bookSection",
                    "thesis",
                    "report",
                ]:
                    all_items.append({"key": item.get("key")})

            start += len(batch)

        return all_items

    def get_pdf_info(self, pdf_path: Path) -> dict[str, Any]:
        """Get PDF file metadata for change detection.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with 'size' and 'mtime' fields
        """
        if pdf_path and pdf_path.exists():
            stat = pdf_path.stat()
            return {"size": stat.st_size, "mtime": stat.st_mtime}
        return {}

    def apply_incremental_update(self, changes: dict[str, Any], api_url: str | None = None) -> None:
        """Apply incremental updates to existing knowledge base.

        Processes only changed papers to minimize computation time.
        Preserves existing paper IDs and ensures new papers get sequential IDs.

        Args:
            changes: Dictionary with 'new_keys', 'updated_keys', 'deleted_keys' sets
            api_url: Optional custom Zotero API URL
        """
        # Load existing
        with open(self.metadata_file_path) as f:
            metadata = json.load(f)
        papers_dict = {p["zotero_key"]: p for p in metadata["papers"]}

        # Process new and updated papers
        to_process = changes["new_keys"] | set(changes["updated_keys"])

        if to_process:
            print(f"Processing {len(to_process)} paper changes...")

            # Get full data for papers to process
            all_papers = self.process_zotero_local_library(api_url)
            papers_to_process = [p for p in all_papers if p.get("zotero_key") in to_process]

            # Add PDFs
            self.augment_papers_with_pdfs(papers_to_process, use_cache=True)

            # Get PDF map once for all papers
            pdf_map = self.get_pdf_paths_from_sqlite()

            # Find the highest existing ID to continue from
            existing_ids = [int(p["id"]) for p in metadata["papers"] if p.get("id", "").isdigit()]
            next_id = max(existing_ids) + 1 if existing_ids else 1

            # Process each paper
            for paper in papers_to_process:
                key = paper["zotero_key"]

                # Generate paper ID
                if key in papers_dict:
                    # Update existing paper
                    paper_id = papers_dict[key]["id"]
                else:
                    # New paper - use next available ID
                    paper_id = f"{next_id:04d}"
                    next_id += 1

                # Extract metadata
                text_for_classification = f"{paper.get('title', '')} {paper.get('abstract', '')}"
                study_type = detect_study_type(text_for_classification)
                sample_size = extract_rct_sample_size(text_for_classification, study_type)

                # Get PDF info
                pdf_info = self.get_pdf_info(pdf_map.get(key, Path())) if key in pdf_map else {}

                # Create paper metadata
                paper_metadata = {
                    "id": paper_id,
                    "doi": paper.get("doi", ""),
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "year": paper.get("year"),
                    "journal": paper.get("journal", ""),
                    "volume": paper.get("volume", ""),
                    "issue": paper.get("issue", ""),
                    "pages": paper.get("pages", ""),
                    "abstract": paper.get("abstract", ""),
                    "study_type": study_type,
                    "sample_size": sample_size,
                    "has_full_text": bool(paper.get("full_text")),
                    "filename": f"paper_{paper_id}.md",
                    "zotero_key": key,
                    "pdf_info": pdf_info,
                }

                papers_dict[key] = paper_metadata

                # Save paper file
                md_content = self.format_paper_as_markdown(paper)
                paper_file = self.papers_path / f"paper_{paper_id}.md"
                with paper_file.open("w", encoding="utf-8") as f:
                    f.write(md_content)

        # Remove deleted papers
        for key in changes["deleted_keys"]:
            papers_dict.pop(key, None)

        # Rebuild metadata
        metadata["papers"] = list(papers_dict.values())
        metadata["total_papers"] = len(metadata["papers"])
        metadata["last_updated"] = datetime.now(UTC).isoformat()
        metadata["version"] = "4.0"

        # Save metadata
        with self.metadata_file_path.open("w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Update index incrementally
        if to_process or changes["deleted_keys"]:
            self.update_index_incrementally(metadata["papers"], changes)
        elif changes.get("needs_reindex"):
            # Only rebuild if explicitly needed
            self.rebuild_simple_index(metadata["papers"])

    def update_index_incrementally(self, papers: list[dict[str, Any]], changes: dict[str, Any]) -> None:
        """Update FAISS index incrementally for changed papers only.

        Args:
            papers: List of all paper metadata dictionaries
            changes: Dictionary with 'new_keys', 'updated_keys', 'deleted_keys'
        """
        # For simplicity and reliability, just rebuild the index
        # but only generate embeddings for new/changed papers
        import faiss
        import numpy as np

        # Identify papers that need new embeddings
        changed_keys = changes["new_keys"] | set(changes.get("updated_keys", set()))

        # Try to load existing embeddings
        existing_embeddings = {}
        if self.index_file_path.exists():
            try:
                # Load previous metadata to map papers to embeddings
                with open(self.metadata_file_path) as f:
                    old_metadata = json.load(f)
                old_papers = {p["zotero_key"]: i for i, p in enumerate(old_metadata["papers"])}

                # Load existing index
                index = faiss.read_index(str(self.index_file_path))

                # Extract embeddings for unchanged papers
                for paper in papers:
                    key = paper["zotero_key"]
                    if key not in changed_keys and key in old_papers:
                        old_idx = old_papers[key]
                        if old_idx < index.ntotal:
                            existing_embeddings[key] = index.reconstruct(old_idx)
            except Exception as error:
                print(f"Could not reuse existing embeddings: {error}")
                existing_embeddings = {}

        # Generate embeddings for all papers, reusing where possible
        print(f"Updating index for {len(papers)} papers...")
        if changed_keys:
            print(f"  Generating new embeddings for {len(changed_keys)} papers")
        if existing_embeddings:
            print(f"  Reusing embeddings for {len(existing_embeddings)} unchanged papers")

        all_embeddings: list[Any] = []
        papers_to_embed: list[int] = []
        texts_to_embed: list[str] = []

        for paper in papers:
            key = paper["zotero_key"]

            if key in existing_embeddings:
                # Reuse existing embedding
                all_embeddings.append(existing_embeddings[key])
            else:
                # Need new embedding
                title = paper.get("title", "").strip()
                abstract = paper.get("abstract", "").strip()
                embedding_text = f"{title} [SEP] {abstract}" if abstract else title
                texts_to_embed.append(embedding_text)
                papers_to_embed.append(len(all_embeddings))
                all_embeddings.append(None)  # Placeholder

        # Generate new embeddings if needed
        if texts_to_embed:
            batch_size = self.get_optimal_batch_size()
            new_embeddings = self.embedding_model.encode(
                texts_to_embed, show_progress_bar=True, batch_size=batch_size
            )

            # Fill in the placeholders
            for i, idx in enumerate(papers_to_embed):
                all_embeddings[idx] = new_embeddings[i]

        # Create new index
        all_embeddings_array = np.array(all_embeddings, dtype="float32")
        new_index = faiss.IndexFlatL2(768)
        new_index.add(all_embeddings_array)

        # Save updated index
        faiss.write_index(new_index, str(self.index_file_path))
        print(f"Index updated with {new_index.ntotal} papers")

    def rebuild_simple_index(self, papers: list[dict[str, Any]]) -> None:
        """Rebuild FAISS index from paper abstracts.

        Args:
            papers: List of paper metadata dictionaries
        """
        import faiss

        print("Rebuilding search index from scratch...")

        # Generate embeddings for all papers
        abstracts = []
        for paper in papers:
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()
            embedding_text = f"{title} [SEP] {abstract}" if abstract else title
            abstracts.append(embedding_text)

        if abstracts:
            # Estimate time for embeddings
            num_papers = len(abstracts)
            batch_size = self.get_optimal_batch_size()

            # Estimate and display processing time
            time_min, time_max, time_message = estimate_processing_time(num_papers, self.device)

            display_operation_summary(
                "Embedding Generation",
                item_count=num_papers,
                time_estimate=time_message,
                device=self.device,
                storage_estimate_mb=num_papers * 0.15,
            )

            if not confirm_long_operation(time_min, "Embedding generation"):
                sys.exit(0)

            print(f"Generating embeddings for {num_papers} papers...")

            # Generate embeddings
            embeddings = self.embedding_model.encode(abstracts, show_progress_bar=True, batch_size=batch_size)

            # Create new index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype("float32"))

            # Save index
            faiss.write_index(index, str(self.index_file_path))
            print(f"Index rebuilt with {len(embeddings)} papers")
        else:
            # Empty index
            index = faiss.IndexFlatL2(768)
            faiss.write_index(index, str(self.index_file_path))
            print("Created empty index")

    def get_pdf_paths_from_sqlite(self) -> dict[str, Path]:
        """Get mapping of paper keys to PDF file paths from Zotero SQLite database.

        Queries Zotero's SQLite database to find PDF attachments for each paper.
        This avoids having to traverse the file system and ensures we get the
        correct PDF for each paper.

        Returns:
            Dictionary mapping Zotero paper keys to PDF file paths
        """
        if not self.zotero_db_path.exists():
            print(
                f"WARNING: Zotero database not found\n  Expected location: {self.zotero_db_path}\n  PDF paths will not be available"
            )
            return {}

        pdf_map = {}

        try:
            # Connect to SQLite database with immutable mode to work while Zotero is running
            conn = sqlite3.connect(f"file:{self.zotero_db_path}?immutable=1", uri=True)
            cursor = conn.cursor()

            # Query to get parent item keys and their PDF attachment keys
            query = """
            SELECT
                parent.key as paper_key,
                child.key as attachment_key
            FROM itemAttachments ia
            JOIN items parent ON ia.parentItemID = parent.itemID
            JOIN items child ON ia.itemID = child.itemID
            WHERE ia.contentType = 'application/pdf'
            """

            cursor.execute(query)

            for paper_key, attachment_key in cursor.fetchall():
                # Build path to PDF in storage folder
                pdf_dir = self.zotero_storage_path / attachment_key

                if pdf_dir.exists():
                    # Find PDF file in the directory
                    pdf_files = list(pdf_dir.glob("*.pdf"))
                    if pdf_files:
                        pdf_map[paper_key] = pdf_files[0]

            conn.close()
            # Don't print this - it will be shown when extracting PDFs

        except sqlite3.Error as error:
            print(f"WARNING: Could not read Zotero database\n  Error: {error}")
        except Exception as error:
            print(f"WARNING: Error accessing PDF paths\n  Error: {error}")

        return pdf_map

    def extract_pdf_text(
        self, pdf_path: str | Path, paper_key: str | None = None, use_cache: bool = True
    ) -> str | None:
        """Extract text from PDF using PyMuPDF with caching support.

        Args:
            pdf_path: Path to PDF file
            paper_key: Zotero key for cache lookup
            use_cache: Whether to use/update cache

        Returns:
            Extracted text or None if extraction fails
        """
        import fitz

        pdf_path = Path(pdf_path)

        # Check cache if enabled and key provided
        if use_cache and paper_key:
            if self.cache is None:
                self.load_cache()
            if self.cache and paper_key in self.cache:
                cache_entry = self.cache[paper_key]
                # Check if file metadata matches
                stat = os.stat(pdf_path)
                if (
                    cache_entry.get("file_size") == stat.st_size
                    and cache_entry.get("file_mtime") == stat.st_mtime
                ):
                    return cache_entry.get("text")

        # Extract text from PDF
        try:
            pdf = fitz.open(str(pdf_path))
            text = ""
            for page in pdf:
                text += page.get_text() + "\n"
            pdf.close()
            stripped_text = text.strip() if text else None

            # Update cache if enabled and key provided
            if use_cache and paper_key and stripped_text:
                if self.cache is None:
                    self.load_cache()
                stat = os.stat(pdf_path)
                if self.cache is not None:
                    self.cache[paper_key] = {
                        "text": stripped_text,
                        "file_size": stat.st_size,
                        "file_mtime": stat.st_mtime,
                        "cached_at": datetime.now(UTC).isoformat(),
                    }

            return stripped_text
        except Exception as error:
            print(f"Error extracting PDF {pdf_path}: {error}")
            return None

    def extract_sections(self, text: str) -> dict[str, str]:
        """Extract common academic paper sections from full text.

        Identifies and extracts standard sections like abstract, introduction,
        methods, results, discussion, and conclusion. Handles both markdown-formatted
        papers and raw text with section headers.

        Args:
            text: Full text of the paper

        Returns:
            Dictionary mapping section names to their content (max 5000 chars per section)
        """
        import re

        sections = {
            "abstract": "",
            "introduction": "",
            "methods": "",
            "results": "",
            "discussion": "",
            "conclusion": "",
            "references": "",
            "supplementary": "",
        }

        if not text:
            return sections

        # First check for markdown headers (## Section)
        has_markdown_headers = bool(re.search(r"^## \w+", text, re.MULTILINE))

        if has_markdown_headers:
            # Parse markdown structure
            current_section = None
            section_content: list[str] = []

            for line in text.split("\n"):
                if line.startswith("## "):
                    # Save previous section
                    if current_section and section_content:
                        sections[current_section] = "\n".join(section_content).strip()[:MAX_SECTION_LENGTH]

                    # Identify new section
                    header = line[3:].strip().lower()
                    if "abstract" in header:
                        current_section = "abstract"
                    elif "introduction" in header or "background" in header:
                        current_section = "introduction"
                    elif "method" in header:
                        current_section = "methods"
                    elif "result" in header or "finding" in header:
                        current_section = "results"
                    elif "discussion" in header:
                        current_section = "discussion"
                    elif "conclusion" in header:
                        current_section = "conclusion"
                    elif "reference" in header or "bibliography" in header:
                        current_section = "references"
                    elif "supplement" in header or "appendix" in header:
                        current_section = "supplementary"
                    elif "full text" in header:
                        # For demo papers that have "## Full Text" section
                        current_section = "introduction"  # Will parse subsections below
                    else:
                        current_section = None
                    section_content = []
                elif current_section:
                    section_content.append(line)

            # Save last section
            if current_section and section_content:
                sections[current_section] = "\n".join(section_content).strip()[:MAX_SECTION_LENGTH]

        # Look for inline section headers (Introduction\n, Methods\n, etc.)
        if has_markdown_headers and "## Full Text" in text:
            # Parse the Full Text section for inline headers
            full_text_match = re.search(r"## Full Text\n(.*)", text, re.DOTALL)
            if full_text_match:
                full_text = full_text_match.group(1)

                # Common inline section patterns
                inline_patterns = [
                    (r"^Introduction\s*$", "introduction"),
                    (r"^Methods?\s*$", "methods"),
                    (r"^Results?\s*$", "results"),
                    (r"^Discussion\s*$", "discussion"),
                    (r"^Conclusions?\s*$", "conclusion"),
                    (r"^References?\s*$", "references"),
                ]

                lines = full_text.split("\n")
                current_section = None
                section_content = []

                for line in lines:
                    found_section = None
                    for pattern, section_name in inline_patterns:
                        if re.match(pattern, line.strip(), re.IGNORECASE):
                            found_section = section_name
                            break

                    if found_section:
                        # Save previous section
                        if (
                            current_section and section_content and not sections[current_section]
                        ):  # Don't overwrite
                            sections[current_section] = "\n".join(section_content).strip()[
                                :MAX_SECTION_LENGTH
                            ]
                        current_section = found_section
                        section_content = []
                    elif current_section:
                        section_content.append(line)

                # Save last section
                if current_section and section_content and not sections[current_section]:
                    sections[current_section] = "\n".join(section_content).strip()[:MAX_SECTION_LENGTH]

        # Fallback: use regex patterns for general text
        if not any(sections.values()):
            section_patterns = {
                "abstract": r"(?i)(?:abstract|summary)\s*[\n:]",
                "introduction": r"(?i)(?:introduction|background)\s*[\n:]",
                "methods": r"(?i)(?:methods?|methodology)\s*[\n:]",
                "results": r"(?i)(?:results?|findings?)\s*[\n:]",
                "discussion": r"(?i)(?:discussion)\s*[\n:]",
                "conclusion": r"(?i)(?:conclusions?)\s*[\n:]",
                "references": r"(?i)(?:references?|bibliography)\s*[\n:]",
            }

            for section_name, pattern in section_patterns.items():
                match = re.search(pattern, text)
                if match:
                    start = match.end()
                    # Find next section or end of text
                    next_match = None
                    for other_pattern in section_patterns.values():
                        next_m = re.search(other_pattern, text[start:])
                        if next_m and (next_match is None or next_m.start() < next_match):
                            next_match = next_m.start()

                    if next_match:
                        sections[section_name] = text[start : start + next_match].strip()[:MAX_SECTION_LENGTH]
                    else:
                        sections[section_name] = text[start : start + MAX_SECTION_LENGTH].strip()

        # If still no sections found, use heuristics
        if not any(sections.values()) and text:
            sections["abstract"] = text[:ABSTRACT_PREVIEW_LENGTH].strip()
            if len(text) > MIN_TEXT_FOR_CONCLUSION:
                sections["conclusion"] = text[-CONCLUSION_PREVIEW_LENGTH:].strip()

        return sections

    def format_paper_as_markdown(self, paper_data: dict[str, Any]) -> str:
        """Format paper data as markdown for storage.

        Args:
            paper_data: Dictionary with paper metadata and text

        Returns:
            Formatted markdown string
        """
        markdown_content = f"# {paper_data['title']}\n\n"

        if paper_data.get("authors"):
            markdown_content += f"**Authors:** {', '.join(paper_data['authors'])}  \n"
        markdown_content += f"**Year:** {paper_data.get('year', 'Unknown')}  \n"

        if paper_data.get("journal"):
            markdown_content += f"**Journal:** {paper_data['journal']}  \n"
        if paper_data.get("volume"):
            markdown_content += f"**Volume:** {paper_data['volume']}  \n"
        if paper_data.get("issue"):
            markdown_content += f"**Issue:** {paper_data['issue']}  \n"
        if paper_data.get("pages"):
            markdown_content += f"**Pages:** {paper_data['pages']}  \n"
        if paper_data.get("doi"):
            markdown_content += f"**DOI:** {paper_data['doi']}  \n"

        markdown_content += "\n## Abstract\n"
        markdown_content += paper_data.get("abstract", "No abstract available.") + "\n\n"

        if paper_data.get("full_text"):
            markdown_content += "## Full Text\n"
            markdown_content += paper_data["full_text"] + "\n"

        return str(markdown_content)

    def process_zotero_local_library(self, api_url: str | None = None) -> list[dict[str, Any]]:
        """Extract papers from Zotero local library using HTTP API.

        Args:
            api_url: Optional custom Zotero API URL

        Returns:
            List of paper dictionaries with metadata
        """
        base_url = api_url or "http://localhost:23119/api"

        # Test connection to local Zotero
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code != 200:
                raise ConnectionError(
                    "Zotero local API not accessible. Ensure Zotero is running and 'Allow other applications' is enabled in Advanced settings."
                )
        except requests.exceptions.RequestException as error:
            raise ConnectionError(f"Cannot connect to Zotero local API: {error}") from error

        # Get all items from library with pagination
        all_items = []
        start = 0
        limit = 100

        print("Fetching items from Zotero API...")
        while True:
            try:
                response = requests.get(
                    f"{base_url}/users/0/items",
                    params={"start": str(start), "limit": str(limit)},
                    timeout=30,
                )
                response.raise_for_status()
                batch = response.json()

                if not batch:
                    break

                all_items.extend(batch)
                start += len(batch)
                print(f"  Fetched {len(all_items)} items...", end="\r")

            except requests.exceptions.RequestException as error:
                print(
                    format_error_message(
                        "Cannot fetch Zotero items",
                        str(error),
                        suggestion="Check that Zotero is running and accessible",
                        context={"API URL": api_url},
                    )
                )
                raise RuntimeError("Cannot fetch Zotero items") from error

        print(f"  Fetched {len(all_items)} total items from Zotero")

        papers = []

        # Process items to extract paper metadata
        pbar = tqdm(all_items, desc="Filtering for research papers", unit="item")
        for item in pbar:
            if item.get("data", {}).get("itemType") not in [
                "journalArticle",
                "conferencePaper",
                "preprint",
                "book",
                "bookSection",
                "thesis",
                "report",
            ]:
                continue

            paper_data = {
                "title": item["data"].get("title", ""),
                "authors": [],
                "year": None,
                "journal": item["data"].get("publicationTitle", ""),
                "volume": item["data"].get("volume", ""),
                "issue": item["data"].get("issue", ""),
                "pages": item["data"].get("pages", ""),
                "doi": item["data"].get("DOI", ""),
                "abstract": item["data"].get("abstractNote", ""),
                "zotero_key": item.get("key", ""),
            }

            for creator in item["data"].get("creators", []):
                if creator.get("lastName"):
                    name = f"{creator.get('firstName', '')} {creator['lastName']}".strip()
                    paper_data["authors"].append(name)

            if item["data"].get("date"):
                with contextlib.suppress(ValueError, IndexError, KeyError):
                    paper_data["year"] = int(item["data"]["date"][:4])

            papers.append(paper_data)

        print(f"  Found {len(papers)} research papers (from {len(all_items)} total items)")
        return papers

    def augment_papers_with_pdfs(
        self, papers: list[dict[str, Any]], use_cache: bool = True
    ) -> tuple[int, int]:
        """Add full text from PDFs to paper dictionaries.

        Extracts text from PDF attachments found in Zotero's storage directory.
        Uses aggressive caching to avoid re-processing PDFs that haven't changed.

        Args:
            papers: List of paper dictionaries to augment with full text
            use_cache: Whether to use cached PDF text (speeds up rebuilds)

        Returns:
            Tuple of (papers_with_pdfs_count, cache_hits_count)
        """
        # Ensure cache is loaded
        if use_cache and self.cache is None:
            self.load_cache()

        pdf_map = self.get_pdf_paths_from_sqlite()

        if not pdf_map:
            print("No PDF paths found in SQLite database")
            return 0, 0

        papers_with_pdfs_available = sum(1 for p in papers if p["zotero_key"] in pdf_map)
        print(f"Extracting text from {papers_with_pdfs_available:,} PDFs...")
        papers_with_pdfs = 0
        cache_hits = 0

        pbar = tqdm(papers, desc="Extracting PDF text", unit="paper")
        for paper in pbar:
            if paper["zotero_key"] in pdf_map:
                pdf_path = pdf_map[paper["zotero_key"]]

                # Check if this PDF was already processed and cached
                was_cached = False
                if use_cache:
                    if self.cache is None:
                        self.load_cache()
                    if self.cache is None:
                        raise RuntimeError("Failed to load cache")
                    if paper["zotero_key"] in self.cache:
                        cache_entry = self.cache[paper["zotero_key"]]
                        try:
                            stat = os.stat(pdf_path)
                            if (
                                cache_entry.get("file_size") == stat.st_size
                                and cache_entry.get("file_mtime") == stat.st_mtime
                            ):
                                was_cached = True
                        except (OSError, AttributeError, KeyError):
                            pass

                full_text = self.extract_pdf_text(pdf_path, paper["zotero_key"], use_cache)
                if full_text:
                    paper["full_text"] = full_text
                    papers_with_pdfs += 1
                    if was_cached:
                        cache_hits += 1

        if use_cache and cache_hits > 0:
            print(
                f"Extracted text from {papers_with_pdfs:,}/{len(papers):,} papers ({cache_hits:,} from cache)"
            )
        else:
            print(f"Extracted text from {papers_with_pdfs:,}/{len(papers):,} papers")

        # Save cache after extraction
        if use_cache:
            self.save_cache()

        return papers_with_pdfs, cache_hits

    def build_from_zotero_local(
        self,
        api_url: str | None = None,
        use_cache: bool = True,
    ) -> None:
        """Build complete knowledge base from local Zotero library.

        Args:
            api_url: Optional custom Zotero API URL
            use_cache: Whether to use PDF text cache
        """
        print("Connecting to local Zotero library...")

        # Clean up old files
        self.clean_knowledge_base()

        # Get papers from Zotero
        papers = self.process_zotero_local_library(api_url)
        # Don't print this - it's redundant with the "Found X research papers" message above

        # Add full text from PDFs
        pdf_stats = self.augment_papers_with_pdfs(papers, use_cache)

        # Build the knowledge base
        self.build_from_papers(papers, pdf_stats)

    def generate_pdf_quality_report(self, papers: list[dict[str, Any]]) -> Path:
        """Generate comprehensive PDF quality report covering missing and small PDFs.

        Combines analysis of papers missing PDFs and those with minimal extracted text.
        Provides a complete overview of PDF-related issues in the knowledge base.

        Args:
            papers: List of paper dictionaries

        Returns:
            Path to generated report file
        """
        # Categorize papers by PDF status
        missing_pdfs = []  # No PDF at all
        small_pdfs = []  # PDF exists but minimal text extracted
        good_pdfs = []  # PDF exists with adequate text

        for paper in papers:
            if "full_text" not in paper or not paper.get("full_text"):
                missing_pdfs.append(paper)
            elif len(paper.get("full_text", "")) < MIN_FULL_TEXT_LENGTH:
                small_pdfs.append(paper)
            else:
                good_pdfs.append(paper)

        # Start building report
        report_lines = []
        report_lines.append("# PDF Quality Report\n")
        report_lines.append(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        report_lines.append("Comprehensive analysis of PDF availability and text extraction quality.\n")

        # Summary statistics
        total_papers = len(papers)
        report_lines.append("## Summary Statistics\n")
        report_lines.append(f"- **Total papers:** {total_papers:,}")
        report_lines.append(
            f"- **Papers with good PDFs:** {len(good_pdfs):,} ({len(good_pdfs) * 100 / total_papers:.1f}%)"
        )
        report_lines.append(
            f"- **Papers with small PDFs:** {len(small_pdfs):,} ({len(small_pdfs) * 100 / total_papers:.1f}%)"
        )
        report_lines.append(
            f"- **Papers missing PDFs:** {len(missing_pdfs):,} ({len(missing_pdfs) * 100 / total_papers:.1f}%)"
        )
        report_lines.append(
            f"- **Text extraction threshold:** {MIN_FULL_TEXT_LENGTH:,} characters ({MIN_FULL_TEXT_LENGTH // 1000}KB)\n"
        )

        # Section 1: Missing PDFs
        if missing_pdfs:
            report_lines.append("## Papers Missing PDFs\n")
            report_lines.append("These papers have no PDF attachments in Zotero or PDF extraction failed:\n")

            # Sort by year (newest first), then by title
            missing_pdfs.sort(
                key=lambda p: (-p.get("year", 0) if p.get("year") else -9999, p.get("title", ""))
            )

            # Limit to first 50 to avoid huge reports
            for i, paper in enumerate(missing_pdfs[:50], 1):
                year = paper.get("year", "n.d.")
                title = paper.get("title", "Untitled")
                authors = paper.get("authors", [])
                first_author = authors[0].split()[-1] if authors else "Unknown"
                journal = paper.get("journal", "Unknown journal")[:50]

                report_lines.append(f"{i}. **[{year}] {title}**")
                report_lines.append(
                    f"   - Authors: {first_author} et al."
                    if len(authors) > 1
                    else f"   - Author: {first_author}"
                )
                report_lines.append(f"   - Journal: {journal}")
                if paper.get("doi"):
                    report_lines.append(f"   - DOI: {paper['doi']}")
                report_lines.append("")

            if len(missing_pdfs) > 50:
                report_lines.append(f"... and {len(missing_pdfs) - 50} more papers\n")
        else:
            report_lines.append("## Papers Missing PDFs\n")
            report_lines.append("✅ All papers have PDF attachments!\n")

        # Section 2: Small PDFs
        if small_pdfs:
            report_lines.append("## Papers with Small PDFs\n")
            report_lines.append(
                f"These papers have PDFs but extracted less than {MIN_FULL_TEXT_LENGTH // 1000}KB of text:"
            )
            report_lines.append("(Usually indicates supplementary materials, not full papers)\n")

            # Sort by year (newest first), then by title
            small_pdfs.sort(key=lambda p: (-p.get("year", 0) if p.get("year") else -9999, p.get("title", "")))

            for i, paper in enumerate(small_pdfs, 1):
                text_len = len(paper.get("full_text", ""))
                year = paper.get("year", "n.d.")
                title = paper.get("title", "Untitled")
                authors = paper.get("authors", [])
                first_author = authors[0].split()[-1] if authors else "Unknown"
                journal = paper.get("journal", "Unknown journal")

                report_lines.append(f"{i}. **[{year}] {title}**")
                report_lines.append(
                    f"   - Authors: {first_author} et al."
                    if len(authors) > 1
                    else f"   - Author: {first_author}"
                )
                report_lines.append(f"   - Journal: {journal}")
                report_lines.append(f"   - Text extracted: {text_len:,} characters")
                if paper.get("doi"):
                    report_lines.append(f"   - DOI: {paper['doi']}")
                report_lines.append("")
        else:
            report_lines.append("## Papers with Small PDFs\n")
            report_lines.append("✅ No papers with small PDFs found!")
            report_lines.append("All PDFs extracted at least 5KB of text.\n")

        # Recommendations section
        report_lines.append("## Recommendations\n")

        if missing_pdfs:
            report_lines.append("**For papers missing PDFs:**\n")
            report_lines.append("1. **Attach PDFs in Zotero**: Use Zotero's 'Find Available PDF' feature")
            report_lines.append("2. **Manual download**: Search journal websites or preprint servers")
            report_lines.append(
                "3. **Check attachments**: Verify PDFs are attached to parent items, not child items"
            )
            report_lines.append(
                "4. **Access permissions**: Ensure institutional access for paywalled papers\n"
            )

        if small_pdfs:
            report_lines.append("**For papers with small PDFs:**\n")
            report_lines.append(
                "1. **Verify content**: Check if PDF contains full paper or just supplementary material"
            )
            report_lines.append(
                "2. **Replace with full paper**: Download complete version if current is incomplete"
            )
            report_lines.append(
                "3. **OCR for scanned PDFs**: Some PDFs may be image-based and need text recognition"
            )
            report_lines.append("4. **Check file integrity**: Re-download if PDF appears corrupted\n")

        report_lines.append("**After fixing PDFs:**")
        report_lines.append("- Run `python src/build_kb.py` to update the knowledge base")
        report_lines.append("- Cache will speed up processing of unchanged papers")

        # Save unified report
        exports_dir = Path("exports")
        exports_dir.mkdir(exist_ok=True)
        report_path = exports_dir / "analysis_pdf_quality.md"
        with report_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        return report_path

    def build_from_papers(
        self, papers: list[dict[str, Any]], pdf_stats: tuple[int, int] | None = None
    ) -> None:
        """Build complete knowledge base from list of papers.

        This is the main pipeline that:
        1. Removes duplicate papers
        2. Assigns unique IDs to each paper
        3. Extracts sections from full text
        4. Generates embeddings for semantic search
        5. Builds FAISS index for similarity search
        6. Saves all metadata and index files

        Args:
            papers: List of paper dictionaries with metadata and full_text
            pdf_stats: Optional tuple of (papers_with_pdfs, cache_hits) for reporting
        """
        import time

        build_start_time = time.time()

        # Extract PDF stats if provided
        papers_with_pdfs = pdf_stats[0] if pdf_stats else 0
        pdf_cache_hits = pdf_stats[1] if pdf_stats else 0

        # Detect and remove duplicates
        print("Checking for duplicate papers...")
        unique_papers = []
        seen_dois = set()
        seen_titles = set()
        duplicates_removed = 0

        for paper in papers:
            # Check for duplicate DOI
            doi = paper.get("doi", "").strip().lower()
            if doi and doi in seen_dois:
                duplicates_removed += 1
                continue

            # Check for duplicate title (normalized)
            title = paper.get("title", "").strip().lower()
            # Remove common variations in titles
            normalized_title = re.sub(r"[^\w\s]", "", title)  # Remove punctuation
            normalized_title = re.sub(r"\s+", " ", normalized_title)  # Normalize whitespace

            if normalized_title and normalized_title in seen_titles:
                duplicates_removed += 1
                continue

            # Add to unique papers
            unique_papers.append(paper)
            if doi:
                seen_dois.add(doi)
            if normalized_title:
                seen_titles.add(normalized_title)

        if duplicates_removed > 0:
            print(f"  Removed {duplicates_removed} duplicate papers")
            print(f"  Processing {len(unique_papers):,} unique papers")
        else:
            print("  No duplicates found")

        papers = unique_papers  # Use deduplicated list

        metadata: dict[str, Any] = {
            "papers": [],
            "total_papers": len(papers),
            "last_updated": datetime.now(UTC).isoformat(),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dimensions": EMBEDDING_DIMENSIONS,
            "model_version": "Multi-QA MPNet",
            "version": "4.0",
        }

        abstracts = []
        sections_index = {}  # Store extracted sections for each paper

        pbar = tqdm(papers, desc="Processing papers", unit="paper")
        for i, paper in enumerate(pbar):
            paper_id = f"{i + 1:04d}"

            # Combine title and abstract for classification
            text_for_classification = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            study_type = detect_study_type(text_for_classification)
            sample_size = extract_rct_sample_size(text_for_classification, study_type)

            paper_metadata = {
                "id": paper_id,
                "doi": paper.get("doi", ""),
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year", None),
                "journal": paper.get("journal", ""),
                "volume": paper.get("volume", ""),
                "issue": paper.get("issue", ""),
                "pages": paper.get("pages", ""),
                "abstract": paper.get("abstract", ""),
                "study_type": study_type,
                "sample_size": sample_size,
                "has_full_text": bool(paper.get("full_text")),
                "filename": f"paper_{paper_id}.md",
                "embedding_index": i,
                "zotero_key": paper.get("zotero_key", ""),  # Store for future comparisons
            }

            metadata["papers"].append(paper_metadata)

            # Extract sections if full text is available
            if paper.get("full_text"):
                extracted_sections = self.extract_sections(paper["full_text"])
                sections_index[paper_id] = extracted_sections
            else:
                # Use abstract as the only section if no full text
                sections_index[paper_id] = {
                    "abstract": paper.get("abstract", ""),
                    "introduction": "",
                    "methods": "",
                    "results": "",
                    "discussion": "",
                    "conclusion": "",
                    "references": "",
                    "supplementary": "",
                }

            md_content = self.format_paper_as_markdown(paper)
            markdown_file_path = self.papers_path / f"paper_{paper_id}.md"
            with open(markdown_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)

            # Format for Multi-QA MPNet: Title and Abstract with separator
            # Multi-QA MPNet handles title and abstract concatenated with a separator
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()

            # Multi-QA MPNet handles papers with missing abstracts well
            embedding_text = f"{title} [SEP] {abstract}" if abstract else title

            abstracts.append(embedding_text)

        print(f"\nBuilding search index for {len(abstracts):,} papers...")
        import faiss
        import numpy as np

        if abstracts:
            # Load embedding cache
            cache = self.load_embedding_cache()
            cached_embeddings = []
            new_abstracts = []
            new_indices = []
            all_hashes = []

            # Build hash-to-embedding dictionary for O(1) lookups
            hash_to_embedding = {}
            if cache["embeddings"] is not None and cache["hashes"]:
                hash_to_embedding = {h: cache["embeddings"][idx] for idx, h in enumerate(cache["hashes"])}

            # Check cache for each abstract
            for i, abstract_text in enumerate(abstracts):
                text_hash = self.get_embedding_hash(abstract_text)
                all_hashes.append(text_hash)

                # Try to find in cache (O(1) lookup)
                if text_hash in hash_to_embedding:
                    cached_embeddings.append(hash_to_embedding[text_hash])
                else:
                    new_abstracts.append(abstract_text)
                    new_indices.append(i)

            # Report cache usage
            cache_hits = len(cached_embeddings)
            if cache_hits > 0:
                print(
                    f"  Using cached embeddings: {cache_hits:,}/{len(abstracts):,} papers ({cache_hits * 100 // len(abstracts)}%)"
                )

            # Compute new embeddings if needed
            if new_abstracts:
                print(f"Computing embeddings for {len(new_abstracts):,} papers...")
                # Use dynamic batch size based on available memory
                batch_size = self.get_optimal_batch_size()

                # Estimate time for embeddings
                num_papers = len(new_abstracts)

                # Rough estimates based on device (Multi-QA MPNet is ~20% faster than SPECTER)
                if self.device == "cuda":
                    seconds_per_paper_min = 0.04  # Best case: 40ms per paper
                    seconds_per_paper_max = 0.12  # Worst case: 120ms per paper
                else:
                    seconds_per_paper_min = 0.4  # Best case on CPU: 400ms per paper
                    seconds_per_paper_max = 0.8  # Worst case on CPU: 800ms per paper

                estimated_time_min = num_papers * seconds_per_paper_min
                estimated_time_max = num_papers * seconds_per_paper_max

                if estimated_time_min > 60:
                    minutes_min = int(estimated_time_min / 60)
                    minutes_max = int(estimated_time_max / 60)
                    print(
                        f"Embedding generation will take approximately {minutes_min}-{minutes_max} minutes ({num_papers:,} papers on {self.device.upper()})"
                    )

                    if estimated_time_min > 300:  # More than 5 minutes
                        response = input("Continue? (Y/n): ").strip().lower()
                        if response == "n":
                            print("Aborted by user")
                            sys.exit(0)

                # Show batch processing details
                print(f"  Processing in batches of {batch_size}...")
                total_batches = (len(new_abstracts) + batch_size - 1) // batch_size
                print(f"  Total batches to process: {total_batches}")

                new_embeddings = self.embedding_model.encode(
                    new_abstracts, show_progress_bar=True, batch_size=batch_size
                )
            else:
                new_embeddings = []

            # Combine cached and new embeddings in correct order
            all_embeddings = np.zeros((len(abstracts), 768), dtype="float32")

            # Place embeddings in correct positions
            cache_idx = 0
            new_idx = 0
            for i in range(len(abstracts)):
                if i in new_indices:
                    all_embeddings[i] = new_embeddings[new_idx]
                    new_idx += 1
                else:
                    all_embeddings[i] = cached_embeddings[cache_idx]
                    cache_idx += 1

            # Save cache
            print("Saving embedding cache...")
            self.save_embedding_cache(all_embeddings, all_hashes)

            # Build FAISS index
            print("Creating searchable index...")
            dimension = all_embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(all_embeddings.astype("float32"))
            print(f"  Index created with {len(all_embeddings)} vectors of dimension {dimension}")
        else:
            # Create empty index with default dimension
            dimension = EMBEDDING_DIMENSIONS  # Multi-QA MPNet dimension
            index = faiss.IndexFlatL2(dimension)

        faiss.write_index(index, str(self.index_file_path))

        with open(self.metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Save sections index for fast retrieval
        sections_index_path = self.knowledge_base_path / "sections_index.json"
        with sections_index_path.open("w", encoding="utf-8") as f:
            json.dump(sections_index, f, indent=2, ensure_ascii=False)
        print(f"  - Sections index: {sections_index_path}")

        # Calculate build time
        build_time = (time.time() - build_start_time) / 60  # Convert to minutes

        # Count statistics
        embeddings_created = len(papers)  # All papers get embeddings (from abstract or full text)

        # Build verification and summary
        print("\nKnowledge base built successfully!")
        print(f"  - Papers indexed: {len(papers)}")
        print(
            f"  - PDFs extracted: {papers_with_pdfs}/{len(papers)} ({papers_with_pdfs / len(papers) * 100:.1f}%)"
        )
        print(f"  - Embeddings created: {embeddings_created}")
        if pdf_cache_hits > 0:
            print(
                f"  - Cache hits: {pdf_cache_hits}/{papers_with_pdfs} ({pdf_cache_hits / papers_with_pdfs * 100:.1f}%)"
            )
        print(f"  - Build time: {build_time:.1f} minutes")
        print(f"  - Index: {self.index_file_path}")
        print(f"  - Metadata: {self.metadata_file_path}")

        # Sanity checks and warnings
        warnings = []
        if papers_with_pdfs < len(papers) * 0.9:
            warnings.append(f"Low PDF coverage: only {papers_with_pdfs}/{len(papers)} papers have PDFs")
        if embeddings_created != len(papers):
            warnings.append(
                f"Embedding count mismatch: {embeddings_created} embeddings for {len(papers)} papers"
            )
        if not self.index_file_path.exists():
            warnings.append("FAISS index file not created")
        if not self.metadata_file_path.exists():
            warnings.append("Metadata file not created")

        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"  - {warning}")

        # Generate comprehensive PDF quality report (replaces separate missing/small reports)
        missing_count = sum(1 for p in papers if "full_text" not in p or not p.get("full_text"))
        small_pdfs_count = sum(
            1 for p in papers if p.get("full_text") and len(p.get("full_text", "")) < MIN_FULL_TEXT_LENGTH
        )

        if missing_count > 0 or small_pdfs_count > 0:
            print("\n📋 Generating PDF quality report...")
            if missing_count > 0:
                print(f"   - {missing_count} papers missing PDFs ({missing_count * 100 / len(papers):.1f}%)")
            if small_pdfs_count > 0:
                print(f"   - {small_pdfs_count} papers with small PDFs (<5KB text)")

            report_path = self.generate_pdf_quality_report(papers)
            print(f"✅ PDF quality report saved to: {report_path}")
        else:
            print("\n✅ All papers have good PDF quality - no report needed")

    def build_demo_kb(self) -> None:
        """Build a demo knowledge base with 5 sample papers for testing."""
        # Clean up old knowledge base first (no prompt for demo)
        self.clean_knowledge_base()

        demo_papers = [
            {
                "title": "Digital Health Interventions for Depression, Anxiety, and Enhancement of Psychological Well-Being",
                "authors": ["John Smith", "Jane Doe", "Alice Johnson"],
                "year": 2023,
                "journal": "Nature Digital Medicine",
                "volume": "6",
                "issue": "3",
                "pages": "123-145",
                "doi": "10.1038/s41746-023-00789-9",
                "abstract": "Digital health interventions have shown promise in addressing mental health challenges. This systematic review examines the effectiveness of mobile apps, web-based platforms, and digital therapeutics for treating depression and anxiety disorders. We analyzed 127 randomized controlled trials involving over 50,000 participants. Results indicate moderate to large effect sizes for guided digital interventions compared to waitlist controls.",
                "full_text": "Introduction\n\nThe proliferation of digital technologies has created new opportunities for mental health interventions. Mobile health (mHealth) applications, web-based cognitive behavioral therapy (CBT), and digital therapeutics represent a rapidly growing field...\n\nMethods\n\nWe conducted a systematic search of PubMed, PsycINFO, and Cochrane databases for randomized controlled trials published between 2010 and 2023. Inclusion criteria required studies to evaluate digital interventions for depression or anxiety...\n\nResults\n\nOf 3,421 articles screened, 127 met inclusion criteria. Digital CBT showed the strongest evidence base with an average effect size of d=0.73 for depression and d=0.67 for anxiety. Smartphone-based interventions demonstrated moderate effects (d=0.45-0.52) with higher engagement rates than web-based platforms...\n\nDiscussion\n\nDigital health interventions offer scalable solutions for mental health treatment gaps. However, challenges remain regarding engagement, personalization, and integration with traditional care models...",
            },
            {
                "title": "Barriers to Digital Health Adoption in Elderly Populations: A Mixed-Methods Study",
                "authors": ["Michael Chen", "Sarah Williams", "Robert Brown"],
                "year": 2024,
                "journal": "Journal of Medical Internet Research",
                "volume": "26",
                "issue": "2",
                "pages": "e45678",
                "doi": "10.2196/45678",
                "abstract": "Understanding barriers to digital health adoption among elderly populations is crucial for equitable healthcare delivery. This mixed-methods study combines survey data from 2,500 adults aged 65+ with qualitative interviews from 150 participants. Key barriers identified include technological literacy (67%), privacy concerns (54%), lack of perceived benefit (43%), and physical/cognitive limitations (38%). Facilitators included family support, simplified interfaces, and integration with existing care.",
                "full_text": "Background\n\nThe digital divide in healthcare disproportionately affects elderly populations, potentially exacerbating health disparities. As healthcare systems increasingly adopt digital solutions, understanding adoption barriers becomes critical...\n\nObjective\n\nThis study aims to identify and quantify barriers to digital health technology adoption among adults aged 65 and older, and to explore potential facilitators for increased engagement...\n\nMethods\n\nWe employed a sequential explanatory mixed-methods design. Phase 1 involved a nationally representative survey of 2,500 older adults. Phase 2 consisted of semi-structured interviews with 150 participants selected through purposive sampling...\n\nResults\n\nTechnological literacy emerged as the primary barrier, with 67% reporting difficulty navigating digital interfaces. Privacy and security concerns affected 54% of respondents, particularly regarding health data sharing. Perceived lack of benefit was cited by 43%, often due to preference for in-person care...\n\nConclusions\n\nAddressing digital health adoption barriers requires multi-faceted approaches including user-centered design, digital literacy programs, and hybrid care models that maintain human connection while leveraging technology benefits...",
            },
            {
                "title": "Artificial Intelligence in Clinical Decision Support: A Systematic Review of Diagnostic Accuracy",
                "authors": ["Emily Zhang", "David Martinez", "Lisa Anderson"],
                "year": 2023,
                "journal": "The Lancet Digital Health",
                "volume": "5",
                "issue": "8",
                "pages": "e523-e535",
                "doi": "10.1016/S2589-7500(23)00089-0",
                "abstract": "AI-based clinical decision support systems (CDSS) show promising diagnostic accuracy across multiple medical specialties. This systematic review analyzed 89 studies comparing AI diagnostic performance to clinical experts. In radiology, AI achieved 94.5% sensitivity and 95.3% specificity for detecting malignancies. Dermatology applications showed 91.2% accuracy for skin cancer detection. However, real-world implementation faces challenges including algorithm bias, interpretability, and integration with clinical workflows.",
                "full_text": "Introduction\n\nArtificial intelligence has emerged as a transformative technology in healthcare, particularly in diagnostic imaging and pattern recognition. This systematic review evaluates the current state of AI diagnostic accuracy across clinical specialties...\n\nMethods\n\nWe searched MEDLINE, Embase, and IEEE Xplore for studies published between 2018 and 2023 comparing AI diagnostic performance to human experts or established diagnostic standards. Quality assessment used QUADAS-2 criteria...\n\nResults\n\nRadiology applications dominated the literature (n=42 studies), with deep learning models achieving expert-level performance in chest X-ray interpretation (AUC 0.94), mammography (AUC 0.92), and CT lung nodule detection (sensitivity 94.5%). Dermatology studies (n=18) showed comparable accuracy to dermatologists for melanoma detection...\n\nChallenges and Limitations\n\nDespite impressive accuracy metrics, several challenges impede clinical translation. Dataset bias remains problematic, with most training data from high-resource settings. Algorithmic interpretability is limited, creating trust barriers among clinicians...\n\nConclusions\n\nAI demonstrates diagnostic accuracy comparable to or exceeding human experts in specific domains. Successful implementation requires addressing technical, ethical, and workflow integration challenges...",
            },
            {
                "title": "Telemedicine Effectiveness During COVID-19: A Global Meta-Analysis",
                "authors": ["James Wilson", "Maria Garcia", "Thomas Lee"],
                "year": 2023,
                "journal": "BMJ Global Health",
                "volume": "8",
                "issue": "4",
                "pages": "e011234",
                "doi": "10.1136/bmjgh-2023-011234",
                "abstract": "The COVID-19 pandemic accelerated telemedicine adoption globally. This meta-analysis of 156 studies across 42 countries evaluates telemedicine effectiveness for various conditions during 2020-2023. Patient satisfaction rates averaged 86%, with no significant differences in clinical outcomes compared to in-person care for chronic disease management. Cost savings averaged 23% per consultation. However, disparities in access persisted, particularly in low-resource settings.",
                "full_text": "Introduction\n\nThe COVID-19 pandemic necessitated rapid healthcare delivery transformation, with telemedicine emerging as a critical tool for maintaining care continuity. This meta-analysis synthesizes global evidence on telemedicine effectiveness during the pandemic period...\n\nMethods\n\nWe conducted a comprehensive search of multiple databases for studies evaluating telemedicine interventions during COVID-19 (March 2020 - March 2023). Random-effects meta-analysis was performed for clinical outcomes, patient satisfaction, and cost-effectiveness...\n\nResults\n\nFrom 4,567 articles screened, 156 studies met inclusion criteria, representing 2.3 million patients across 42 countries. Chronic disease management via telemedicine showed non-inferior outcomes for diabetes (HbA1c difference: -0.08%, 95% CI: -0.15 to -0.01), hypertension (systolic BP difference: -1.2 mmHg, 95% CI: -2.4 to 0.1), and mental health conditions...\n\nPatient Experience\n\nPatient satisfaction rates were high across regions (mean 86%, range 71-94%). Key satisfaction drivers included convenience (92%), reduced travel time (89%), and maintained care quality (78%). Dissatisfaction related to technical difficulties (31%) and lack of physical examination (28%)...\n\nConclusions\n\nTelemedicine proved effective for maintaining healthcare delivery during COVID-19, with outcomes comparable to traditional care for many conditions. Post-pandemic integration should address equity concerns and optimize hybrid care models...",
            },
            {
                "title": "Wearable Devices for Continuous Health Monitoring: Clinical Validation and Real-World Evidence",
                "authors": ["Kevin Park", "Jennifer White", "Christopher Davis"],
                "year": 2024,
                "journal": "npj Digital Medicine",
                "volume": "7",
                "issue": "1",
                "pages": "45",
                "doi": "10.1038/s41746-024-01012-z",
                "abstract": "Consumer wearable devices increasingly claim health monitoring capabilities, but clinical validation remains inconsistent. This study evaluated 25 popular wearables against medical-grade equipment for heart rate, blood oxygen, and activity tracking. While heart rate monitoring showed excellent accuracy (r=0.96), SpO2 measurements varied significantly (r=0.72-0.89). Real-world data from 10,000 users revealed high engagement initially (82%) declining to 34% at 6 months, highlighting adherence challenges.",
                "full_text": "Introduction\n\nThe wearable device market has expanded rapidly, with manufacturers increasingly positioning products as health monitoring tools. This study provides comprehensive clinical validation of consumer wearables and analyzes real-world usage patterns...\n\nMethods\n\nPhase 1: Laboratory validation compared 25 consumer wearables (smartwatches, fitness trackers, rings) against gold-standard medical devices. Measurements included heart rate, SpO2, sleep stages, and physical activity. Phase 2: Prospective cohort study followed 10,000 users for 12 months, tracking engagement patterns and health outcomes...\n\nValidation Results\n\nHeart rate monitoring demonstrated excellent agreement with ECG (mean absolute error: 2.3 bpm, r=0.96). Performance was consistent across activities except high-intensity exercise (MAE: 5.7 bpm). SpO2 accuracy varied by device, with newer models showing improved performance (r=0.89 vs 0.72 for older generations)...\n\nReal-World Engagement\n\nInitial engagement was high (82% daily use in month 1) but declined significantly over time. At 6 months, only 34% maintained daily use. Factors associated with sustained engagement included goal setting (OR 2.3), social features (OR 1.8), and health condition monitoring (OR 3.1)...\n\nClinical Implications\n\nWhile wearables show promise for continuous monitoring, clinical integration requires careful consideration of accuracy limitations and engagement sustainability. Hybrid models combining wearable data with periodic clinical validation may optimize outcomes...",
            },
        ]

        self.build_from_papers(demo_papers)


@click.command()
@click.option("--demo", is_flag=True, help="Build demo KB with 5 sample papers (no Zotero needed)")
@click.option("--rebuild", is_flag=True, help="Force complete rebuild, ignore existing KB and cached data")
@click.option(
    "--api-url",
    help="Custom Zotero API URL for WSL/Docker (default: http://localhost:23119/api)",
)
@click.option(
    "--knowledge-base-path", default="kb_data", help="Directory to store KB files (default: kb_data)"
)
@click.option("--zotero-data-dir", help="Path to Zotero data folder with PDFs (default: ~/Zotero)")
@click.option("--export", "export_path", help="Export KB to tar.gz for backup/sharing (e.g., my_kb.tar.gz)")
@click.option("--import", "import_path", help="Import KB from tar.gz archive (replaces existing KB)")
def main(
    demo: bool,
    rebuild: bool,
    api_url: str | None,
    knowledge_base_path: str,
    zotero_data_dir: str | None,
    export_path: str | None,
    import_path: str | None,
) -> None:
    """Build and maintain knowledge base from Zotero library for semantic search.

    \b
    SAFE DEFAULT BEHAVIOR (NEW v4.1):
      🛡️  DEFAULT MODE: UPDATE ONLY - NEVER auto-rebuilds or deletes data
      • No KB exists → Full build from Zotero library
      • KB exists → Safe incremental update (only new/changed papers)
      • Failures → Safe exit with clear guidance (data preserved)
      • Rebuilds → Require explicit --rebuild flag with user confirmation

    \b
    SAFETY FEATURES:
      🔒 Data Protection: No automatic deletion of existing papers or cache
      📝 Update Only: Default operation adds/updates papers safely
      🔧 Explicit Rebuilds: Destructive operations require --rebuild flag
      💾 Cache Preservation: All cache files preserved during failures
      📋 Clear Guidance: Detailed error messages with specific solutions

    \b
    CORE FEATURES:
      • Extracts full text from PDF attachments in Zotero
      • Generates Multi-QA MPNet embeddings optimized for healthcare & scientific papers
      • Creates FAISS index for ultra-fast similarity search
      • Detects study types (RCT, systematic review, cohort, etc.)
      • Extracts sample sizes from RCT abstracts
      • Aggressive caching for faster rebuilds
      • Generates reports for missing/small PDFs

    \b
    GENERATED REPORTS (saved to exports/ directory):
      • analysis_pdf_quality.md - Comprehensive analysis of missing and small PDFs

    \b
    EXAMPLES:
      python src/build_kb.py                    # 🛡️ SAFE: Update only (recommended)
      python src/build_kb.py --demo             # Quick 5-paper demo for testing
      python src/build_kb.py --rebuild          # ⚠️  Explicit rebuild with confirmation
      python src/build_kb.py --export kb.tar.gz # Export for backup/sharing
      python src/build_kb.py --import kb.tar.gz # Import from another machine

    \b
    REQUIREMENTS:
      • Zotero must be running (for non-demo builds)
      • Enable "Allow other applications" in Zotero Settings → Advanced
      • PDFs should be attached to papers in Zotero
    """
    import tarfile

    # Handle export first (doesn't need builder)
    if export_path:
        kb_path = Path(knowledge_base_path)
        if not kb_path.exists():
            print(f"❌ Knowledge base not found at {kb_path}")
            sys.exit(1)

        print(f"📦 Exporting knowledge base to {export_path}...")

        # Create tar.gz archive
        with tarfile.open(export_path, "w:gz") as tar:
            # Add all KB files
            tar.add(kb_path, arcname="kb_data")

        # Calculate size
        size_mb = os.path.getsize(export_path) / (1024 * 1024)
        print(f"✅ Exported KB to {export_path} ({size_mb:.1f} MB)")
        print("\nTransfer this file to your other computer and import with:")
        print(f"  python src/build_kb.py --import {export_path}")
        return

    # Handle import
    if import_path:
        if not Path(import_path).exists():
            print(f"❌ Archive file not found: {import_path}")
            sys.exit(1)

        kb_path = Path(knowledge_base_path)

        # Check if KB already exists
        if kb_path.exists():
            response = input(f"⚠️  Knowledge base already exists at {kb_path}. Overwrite? [y/N]: ")
            if response.lower() != "y":
                print("Import cancelled.")
                return

            # Backup existing KB
            import shutil
            from datetime import datetime, UTC

            backup_path = f"{kb_path}_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(kb_path), backup_path)
            print(f"📁 Backed up existing KB to {backup_path}")

        print(f"📦 Importing knowledge base from {import_path}...")

        # Extract archive
        with tarfile.open(import_path, "r:gz") as tar:
            # Extract to parent directory
            # Safe extraction with path validation
            for member in tar.getmembers():
                # Validate that extracted files stay within target directory
                member_path = os.path.normpath(os.path.join(str(kb_path.parent), member.name))
                if not member_path.startswith(str(kb_path.parent)):
                    raise ValueError(f"Unsafe tar file: {member.name}")
            tar.extractall(kb_path.parent)  # noqa: S202

        # Verify import
        metadata_file = kb_path / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                paper_count = metadata.get("total_papers", 0)
                last_updated = metadata.get("last_updated", "Unknown")

            print(f"✅ Successfully imported {paper_count} papers")
            print(f"   Last updated: {last_updated}")
            print(f"   Location: {kb_path}")
        else:
            print("⚠️  Import completed but metadata not found")

        return

    # Initialize builder
    builder = KnowledgeBaseBuilder(knowledge_base_path, zotero_data_dir)

    if demo:
        if builder.metadata_file_path.exists():
            print(f"❌ Demo mode cannot run - knowledge base already exists at {knowledge_base_path}")
            print("Demo mode is designed for development when no knowledge base exists.")
            print("It creates 5 sample papers for testing purposes.")
            sys.exit(1)
        print("Building demo knowledge base...")
        builder.build_demo_kb()
        return

    # Check if KB exists
    kb_exists = builder.metadata_file_path.exists()

    if not kb_exists:
        # No KB exists, do full build
        print("No existing knowledge base found. Building from scratch...")
        try:
            builder.build_from_zotero_local(api_url, use_cache=True)
        except Exception as error:
            print(f"Error building knowledge base: {error}")
            print("\nTip: For a quick demo, run: python src/build_kb.py --demo")
            sys.exit(1)
    elif rebuild:
        # Force complete rebuild
        print("Complete rebuild requested...")

        # Test Zotero connection BEFORE deleting anything
        try:
            builder._test_zotero_connection(api_url)
        except ConnectionError:
            print("❌ Cannot connect to Zotero local API")
            print("To fix this:")
            print("1. Start Zotero application")
            print("2. Go to Preferences → Advanced → Config Editor")
            print("3. Set 'extensions.zotero.httpServer.enabled' to true")
            print("4. Restart Zotero")
            print("5. Verify API is accessible at http://localhost:23119")
            print()
            print("Then retry: python src/build_kb.py --rebuild")
            sys.exit(1)

        # Create backup if KB exists
        if builder.metadata_file_path.exists():
            import shutil
            from datetime import datetime, UTC

            backup_path = f"kb_data_backup_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            shutil.move(knowledge_base_path, backup_path)
            print(f"📁 Backed up existing KB to {backup_path}")

        try:
            builder.build_from_zotero_local(api_url, use_cache=True)
        except Exception as error:
            print(f"Error building knowledge base: {error}")
            sys.exit(1)
    else:
        # Try smart incremental update (default)
        try:
            changes = builder.check_for_changes(api_url)

            # Check if we need to rebuild index
            if changes["needs_reindex"]:
                print("Index is out of sync with papers. Will regenerate embeddings after update.")
                # Don't return - continue with incremental update

            if changes["total"] == 0 and not changes["needs_reindex"]:
                print("Knowledge base is up to date! No changes detected.")
                return

            if changes["total"] > 0:
                print("Found changes in Zotero library:")
                if changes["new"] > 0:
                    print(f"  - {changes['new']} new papers to add")
                if changes["updated"] > 0:
                    print(f"  - {changes['updated']} papers with updated PDFs")
                if changes["deleted"] > 0:
                    print(f"  - {changes['deleted']} papers to remove")

            builder.apply_incremental_update(changes, api_url)
            print("Update complete!")

        except Exception as error:
            # Handle connection errors specifically
            if isinstance(error, ConnectionError) or "Connection refused" in str(error):
                print("❌ Cannot connect to Zotero local API")
                print("To fix this:")
                print("1. Start Zotero application")
                print("2. Go to Preferences → Advanced → Config Editor")
                print("3. Set 'extensions.zotero.httpServer.enabled' to true")
                print("4. Restart Zotero")
                print("5. Verify API is accessible at http://localhost:23119")
                print()
                print("Then retry: python src/build_kb.py")
                sys.exit(1)

            # For non-connection errors, show the detailed error
            print(f"❌ Incremental update failed: {error}")

            # For all other errors: preserve data and guide user
            print("Your knowledge base has been preserved.")
            print("SOLUTION: python src/build_kb.py --rebuild")
            sys.exit(1)


if __name__ == "__main__":
    main()
