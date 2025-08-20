#!/usr/bin/env python3
"""
Central configuration for Research Assistant v4.0.

This module contains all configuration constants used throughout the application.
Modify these values to customize behavior without changing code logic.

Categories:
- Model Configuration: Embedding models and batch processing
- Search Configuration: Query defaults and caching
- Quality Scoring: Paper quality assessment weights
- Build Configuration: PDF processing and limits
- Paths: File locations and structure
- Validation: Input validation patterns
- Zotero: API and library settings
- Display: UI/output formatting
"""

import re
from pathlib import Path

# ============================================================================
# VERSION
# ============================================================================
KB_VERSION = "4.0"  # Knowledge base format version (increment on breaking changes)

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
# Multi-QA MPNet model optimized for diverse question-answering including healthcare
# Better performance on healthcare systems research while maintaining CS accuracy
EMBEDDING_MODEL = "sentence-transformers/multi-qa-mpnet-base-dot-v1"
EMBEDDING_DIMENSIONS = 768  # Multi-QA MPNet also produces 768-dimensional vectors
EMBEDDING_BATCH_SIZE = 64  # Default batch size for embedding generation

# Batch size ranges based on available hardware resources
# Larger batches = faster processing but more memory usage
BATCH_SIZE_GPU_HIGH = 256  # GPU with >8GB VRAM
BATCH_SIZE_GPU_MEDIUM = 128  # GPU with 4-8GB VRAM
BATCH_SIZE_GPU_LOW = 64  # GPU with <4GB VRAM
BATCH_SIZE_CPU_HIGH = 256  # System with >16GB RAM
BATCH_SIZE_CPU_MEDIUM = 128  # System with 8-16GB RAM
BATCH_SIZE_CPU_LOW = 64  # System with <8GB RAM
BATCH_SIZE_FALLBACK = 128  # Used when hardware detection fails

# ============================================================================
# SEARCH CONFIGURATION
# ============================================================================
# Default search parameters
DEFAULT_K = 10  # Default number of search results to return
DEFAULT_QUALITY_MIN = 0  # Minimum quality score (0-100 scale)
MAX_SEARCH_RESULTS = 100  # Maximum results per search query
DEFAULT_CITATION_COUNT = 5  # Default papers for citation generation
DEFAULT_SMART_SEARCH_RESULTS = 20  # Results for smart-search command
DEFAULT_MAX_TOKENS = 10000  # Token limit for LLM context (~40k characters)

# Search result caching to improve performance
SEARCH_CACHE_EXPIRY_DAYS = 7  # Cache expires after 7 days
SEARCH_CACHE_MAX_SIZE = 100  # Maximum number of cached queries (LRU eviction)

# ============================================================================
# QUALITY SCORING CONFIGURATION
# ============================================================================
# Papers are scored 0-100 based on study type, recency, sample size, and full text
QUALITY_BASE_SCORE = 50  # Starting score for all papers

# Study type scores based on evidence hierarchy (max 35 points)
# Higher scores = stronger evidence quality
QUALITY_STUDY_TYPE_WEIGHTS = {
    "systematic_review": 35,  # Highest evidence: synthesis of multiple studies
    "meta_analysis": 35,  # Highest evidence: statistical synthesis
    "rct": 25,  # High evidence: randomized controlled trial
    "cohort": 15,  # Moderate evidence: longitudinal observation
    "case_control": 10,  # Lower evidence: retrospective comparison
    "cross_sectional": 5,  # Snapshot studies
    "case_report": 0,  # Individual cases, lowest evidence
    "study": 5,  # Generic/unclassified studies
}

# Recency bonuses - newer papers get higher scores
YEAR_VERY_RECENT = 2022  # Papers from this year or later get max bonus
YEAR_RECENT = 2020  # Papers from this year or later get partial bonus
BONUS_VERY_RECENT = 10  # Bonus points for very recent papers
BONUS_RECENT = 5  # Bonus points for recent papers

# Sample size bonuses for RCTs (only applied to randomized trials)
SAMPLE_SIZE_LARGE_THRESHOLD = 1000  # n > 1000 = large trial
SAMPLE_SIZE_MEDIUM_THRESHOLD = 500  # n > 500 = medium trial
SAMPLE_SIZE_SMALL_THRESHOLD = 100  # n > 100 = small trial
BONUS_LARGE_SAMPLE = 10  # Bonus for large RCTs
BONUS_MEDIUM_SAMPLE = 5  # Bonus for medium RCTs

# Additional scoring factors
BONUS_FULL_TEXT = 5  # Bonus for papers with full PDF text available

# ============================================================================
# BUILD CONFIGURATION
# ============================================================================
# Text extraction and section limits
MAX_SECTION_LENGTH = 5000  # Max characters per paper section (methods, results, etc.)
ABSTRACT_PREVIEW_LENGTH = 1000  # Fallback abstract length when full text unavailable
CONCLUSION_PREVIEW_LENGTH = 1000  # Fallback conclusion length
MIN_FULL_TEXT_LENGTH = 5000  # PDFs with less text are flagged as incomplete
MIN_TEXT_FOR_CONCLUSION = 2000  # Minimum text needed to extract conclusion section

# PDF processing settings
PDF_TIMEOUT_SECONDS = 30  # Timeout for PDF text extraction (prevents hanging)

# Sample size validation for RCTs
MIN_SAMPLE_SIZE = 10  # Minimum believable sample size
MAX_SAMPLE_SIZE = 100000  # Maximum believable sample size (filters outliers)

# Display limits for build reports and warnings
MAX_MISSING_FILES_DISPLAY = 10  # Max missing files to show in warnings
MAX_SMALL_PDFS_DISPLAY = 20  # Max incomplete PDFs to list
MAX_ORPHANED_FILES_WARNING = 5  # Warn if more orphaned files than this
MAX_MISSING_PDFS_IN_REPORT = 100  # Truncate report after this many missing PDFs

# Zotero API Configuration
ZOTERO_PORT = 23119  # Default port for Zotero local API
API_TIMEOUT_SHORT = 10  # Timeout for quick API requests (seconds)
API_TIMEOUT_LONG = 30  # Timeout for data-heavy requests (seconds)
API_BATCH_SIZE = 100  # Papers per API request (pagination size)

# Processing time estimates for user feedback (Multi-QA MPNet)
TIME_PER_PAPER_GPU_MIN = 0.04  # Best case: 40ms per paper on GPU
TIME_PER_PAPER_GPU_MAX = 0.12  # Worst case: 120ms per paper on GPU
TIME_PER_PAPER_CPU_MIN = 0.4  # Best case: 400ms per paper on CPU
TIME_PER_PAPER_CPU_MAX = 0.8  # Worst case: 800ms per paper on CPU
LONG_OPERATION_THRESHOLD = 300  # Prompt user if operation > 5 minutes

# ============================================================================
# PATHS
# ============================================================================
KB_DATA_PATH = Path("kb_data")
PAPERS_DIR = KB_DATA_PATH / "papers"
INDEX_FILE = KB_DATA_PATH / "index.faiss"
METADATA_FILE = KB_DATA_PATH / "metadata.json"
SECTIONS_INDEX_FILE = KB_DATA_PATH / "sections_index.json"
SEARCH_CACHE_FILE = KB_DATA_PATH / ".search_cache.json"
PDF_CACHE_FILE = KB_DATA_PATH / ".pdf_text_cache.json"
EMBEDDING_CACHE_FILE = KB_DATA_PATH / ".embedding_cache.json"
EMBEDDING_DATA_FILE = KB_DATA_PATH / ".embedding_data.npy"

# ============================================================================
# VALIDATION PATTERNS
# ============================================================================
VALID_PAPER_ID_PATTERN = re.compile(r"^\d{4}$")
PAPER_ID_DIGITS = 4
MAX_QUERY_LENGTH = 500
VALID_SECTION_NAMES = {
    "abstract",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "references",
    "supplementary",
    "all",
}

# ============================================================================
# ZOTERO CONFIGURATION
# ============================================================================
DEFAULT_ZOTERO_PATH = Path.home() / "Zotero"
DEFAULT_API_URL = f"http://127.0.0.1:{ZOTERO_PORT}/api"

# Valid paper item types in Zotero
VALID_PAPER_TYPES = [
    "journalArticle",
    "conferencePaper",
    "preprint",
    "book",
    "bookSection",
    "thesis",
    "report",
]

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================
# Study type markers for visual hierarchy
STUDY_TYPE_MARKERS = {
    "systematic_review": "⭐",  # Best evidence
    "meta_analysis": "⭐",  # Best evidence
    "rct": "●",  # High quality
    "cohort": "◐",  # Good evidence
    "case_control": "○",  # Moderate evidence
    "cross_sectional": "◔",  # Lower evidence
    "case_report": "·",  # Case level
    "study": "·",  # Generic
}

# Quality score thresholds
QUALITY_EXCELLENT = 80  # Systematic reviews, meta-analyses
QUALITY_GOOD = 60  # RCTs, recent high-quality studies
QUALITY_MODERATE = 40  # Cohort studies, older papers
QUALITY_LOW = 0  # Case reports, generic studies
