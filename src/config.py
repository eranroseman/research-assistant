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

# Enhanced Quality Scoring with Semantic Scholar API
ENABLE_ENHANCED_QUALITY = True  # Enable API-enhanced quality scoring
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1"

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

# Citation impact scoring thresholds
CITATION_COUNT_THRESHOLDS = {
    "exceptional": 1000,  # 25 points
    "high": 500,  # 20 points
    "good": 100,  # 15 points
    "moderate": 50,  # 10 points
    "some": 20,  # 7 points
    "few": 5,  # 4 points
    "minimal": 1,  # 2 points
    "none": 0,  # 0 points
}

# Venue prestige scoring (based on journal rankings)
VENUE_PRESTIGE_SCORES = {
    "Q1": 15,  # Top quartile journals
    "Q2": 12,  # Second quartile
    "Q3": 8,  # Third quartile
    "Q4": 4,  # Fourth quartile
    "unranked": 2,  # Unranked venues
}

# Author authority thresholds (based on h-index)
AUTHOR_AUTHORITY_THRESHOLDS = {
    "renowned": 50,  # 10 points
    "established": 30,  # 8 points
    "experienced": 15,  # 6 points
    "emerging": 5,  # 4 points
    "early_career": 1,  # 2 points
    "unknown": 0,  # 0 points
}

# ============================================================================
# ENHANCED QUALITY SCORING WITH SEMANTIC SCHOLAR API
# ============================================================================
# API Configuration - Critical Relationships:
# - API_REQUEST_TIMEOUT must be < API_TOTAL_TIMEOUT_BUDGET / API_MAX_RETRIES
# - API_TOTAL_TIMEOUT_BUDGET should accommodate expected paper count x retry attempts
# - API_RETRY_DELAY scales with API_MAX_RETRIES for exponential backoff
API_REQUEST_TIMEOUT = 10  # Timeout for individual API requests (must be < 200s for 3 retries)
API_TOTAL_TIMEOUT_BUDGET = 600  # Max 10 min for all API calls (must be > REQUEST_TIMEOUT x MAX_RETRIES)
API_MAX_RETRIES = 3  # Retry failed requests (increase if REQUEST_TIMEOUT is very low)
API_RETRY_DELAY = 1.0  # Base delay between retries (actual delay = RETRY_DELAY x attempt)

# Emergency fallback configuration
ENHANCED_SCORING_EMERGENCY_FALLBACK = True  # Enable fallback to basic scoring
API_HEALTH_CHECK_TIMEOUT = 5  # Seconds for health check
API_FAILURE_THRESHOLD = 3  # Consecutive failures before fallback
EMERGENCY_FALLBACK_DURATION = 1800  # 30 minutes before retry enhanced scoring

# Production reliability configuration
API_CIRCUIT_BREAKER_THRESHOLD = 10  # Failures before temporary disable
API_CIRCUIT_BREAKER_RESET_TIME = 300  # 5 min before retry after circuit opens
API_CONNECTION_POOL_SIZE = 10  # Max concurrent connections
API_CONNECTION_POOL_HOST_LIMIT = 5  # Max connections per host

# Unified scoring weights (100 points total) - CRITICAL: Must sum to 100
#
# Core paper attributes: 40 points max (STUDY_TYPE + RECENCY + SAMPLE_SIZE + FULL_TEXT = 40)
STUDY_TYPE_WEIGHT = 20  # Evidence hierarchy scoring (highest impact factor)
RECENCY_WEIGHT = 10  # Publication year scoring (decreases with age)
SAMPLE_SIZE_WEIGHT = 5  # Study size scoring (RCTs only - others get 0)
FULL_TEXT_WEIGHT = 5  # PDF availability (binary: 5 or 0)

# API-enhanced attributes: 60 points max (CITATION + VENUE + AUTHOR + CROSS_VALIDATION = 60)
# CRITICAL: These weights must match the scoring functions in calculate_*_score()
CITATION_IMPACT_WEIGHT = 25  # Citation count and influence (largest API component)
VENUE_PRESTIGE_WEIGHT = 15  # Journal/conference ranking (Q1=15, Q2=12, Q3=8, Q4=4, unranked=2)
AUTHOR_AUTHORITY_WEIGHT = 10  # Author h-index and reputation (max h-index among authors)
CROSS_VALIDATION_WEIGHT = 10  # Multi-source data verification (DOI, PubMed, types, fields)

# ============================================================================
# BUILD CONFIGURATION
# ============================================================================
# Text extraction and section limits
MAX_SECTION_LENGTH = 50000  # Generous safety limit for section length (10x previous limit)
MAX_QUALITY_SCORE = 100  # Maximum quality score value (moved from cli.py)
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
# RELATIONSHIPS: GPU is ~10x faster than CPU, batch size affects actual times
# Total time = (papers x TIME_PER_PAPER) / batch_efficiency_factor
TIME_PER_PAPER_GPU_MIN = 0.04  # Best case: 40ms per paper on GPU (with optimal batch size)
TIME_PER_PAPER_GPU_MAX = 0.12  # Worst case: 120ms per paper on GPU (small batches/overhead)
TIME_PER_PAPER_CPU_MIN = 0.4  # Best case: 400ms per paper on CPU (10x slower than GPU)
TIME_PER_PAPER_CPU_MAX = 0.8  # Worst case: 800ms per paper on CPU (memory constrained)
LONG_OPERATION_THRESHOLD = 300  # Prompt user if operation > 5 minutes (300s)

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
# COMMAND USAGE CONFIGURATION
# ============================================================================
# Command usage analytics logging for script improvement
COMMAND_USAGE_LOG_PATH = Path("system")  # Use existing system directory
COMMAND_USAGE_LOG_PREFIX = "command_usage_"  # Log file prefix
COMMAND_USAGE_LOG_LEVEL = "INFO"  # Logging level for command usage analytics
COMMAND_USAGE_LOG_ENABLED = True  # Enable/disable command usage logging

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================
# Study type markers for visual hierarchy
STUDY_TYPE_MARKERS = {
    "systematic_review": "SR",  # Systematic Review
    "meta_analysis": "MA",  # Meta-Analysis
    "rct": "RCT",  # Randomized Controlled Trial
    "cohort": "COH",  # Cohort Study
    "case_control": "CC",  # Case-Control
    "cross_sectional": "XS",  # Cross-Sectional
    "case_report": "CR",  # Case Report
    "study": "ST",  # Generic Study
}

# Quality score thresholds - CRITICAL: Must align with QUALITY_INDICATORS
# These thresholds determine grade boundaries for enhanced quality scoring
QUALITY_EXCELLENT = 85  # A+ grade: Enhanced high-impact papers (systematic reviews + high citations)
QUALITY_VERY_GOOD = 70  # A grade: Strong papers with good metrics (RCTs + decent citations)
QUALITY_GOOD = 60  # B grade: Quality studies (recent cohorts, established venues)
QUALITY_MODERATE = 45  # C grade: Moderate quality (older studies, some citations)
QUALITY_LOW = 30  # D grade: Lower quality (case reports, minimal validation)
QUALITY_VERY_LOW = 0  # F grade: Poor quality (no citations, unverified)
MAX_QUALITY_SCORE = 100  # Maximum possible quality score (all components maxed)

# Quality score display indicators - CRITICAL: Thresholds must match above values
QUALITY_INDICATORS = {
    "excellent": "A+",  # 85-100: Top tier papers
    "very_good": "A",  # 70-84: Strong evidence
    "good": "B",  # 60-69: Good quality
    "moderate": "C",  # 45-59: Moderate quality
    "low": "D",  # 30-44: Lower quality
    "very_low": "F",  # 0-29: Poor quality
}

# ============================================================================
# DISCOVERY TOOL CONFIGURATION (SEMANTIC SCHOLAR FOUNDATION)
# ============================================================================

# Discovery-specific settings (reuse everything else from enhanced scoring)
DISCOVERY_DEFAULT_SOURCE = "semantic_scholar"  # Leverage existing infrastructure
DISCOVERY_DEFAULT_LIMIT = 50  # Conservative default
DISCOVERY_MAX_KEYWORDS = 10  # Prevent overly complex queries
DISCOVERY_DEFAULT_YEAR_FROM = 2020  # Recent research focus
DISCOVERY_DEFAULT_INCLUDE_KB = False  # Exclude KB papers by default

# Command Usage Analytics Configuration (reuse cli.py logging infrastructure)
DISCOVERY_COMMAND_USAGE_LOG_ENABLED = True  # Enable usage pattern tracking
DISCOVERY_SESSION_TIMEOUT_MINUTES = 30  # Session boundary for analytics

# Coverage guidance text
COVERAGE_GUIDANCE = """
## When to Use Manual Database Access

**Semantic Scholar provides excellent comprehensive coverage (214M papers, 85% of digital health research).**

**Consider manual access for specialized needs:**

🔍 **PubMed** - When you need:
  • Clinical trial protocols and regulatory submissions
  • Medical Subject Heading (MeSH) precision
  • FDA/NIH regulatory evidence
  • Systematic review PRISMA compliance

🔍 **IEEE Xplore** - When you need:
  • Engineering implementation details
  • Technical standards and specifications
  • Conference proceedings in engineering/CS
  • Industry best practices and benchmarks

🔍 **arXiv** - When you need:
  • Latest AI/ML preprints (6-12 months ahead of journals)
  • Cutting-edge algorithm developments
  • Reproducible research with code availability
  • Early access to breakthrough methods

**Manual Access Links:**
• PubMed: https://pubmed.ncbi.nlm.nih.gov/
• IEEE: https://ieeexplore.ieee.org/
• arXiv: https://arxiv.org/search/

**Future Enhancement:** Specialized slash commands planned (/pubmed, /ieee, /arxiv)
"""

# Population focus mappings for enhanced search
POPULATION_FOCUS_TERMS = {
    "pediatric": ["children", "pediatric", "adolescent", "youth", "minors"],
    "elderly": ["elderly", "geriatric", "older adults", "seniors", "aging"],
    "women": ["women", "female", "maternal", "pregnancy", "reproductive"],
    "developing_countries": ["developing countries", "low-income", "global health", "LMIC"],
}

# Quality threshold mappings (reuse enhanced scoring thresholds)
QUALITY_THRESHOLD_MAPPING = {
    "HIGH": 80,  # CONFIDENCE_HIGH_THRESHOLD from enhanced scoring
    "MEDIUM": 60,  # CONFIDENCE_MEDIUM_THRESHOLD from enhanced scoring
    "LOW": 40,  # CONFIDENCE_LOW_THRESHOLD from enhanced scoring
}

# Reuse ALL enhanced scoring configuration:
# - SEMANTIC_SCHOLAR_API_URL
# - SEMANTIC_SCHOLAR_RATE_LIMIT (1 RPS unauthenticated)
# - API_CACHE_EXPIRY_DAYS (7 days)
# - ENHANCED_QUALITY_* constants (citation impact, venue prestige, etc.)
# - All confidence thresholds and scoring weights

# Output alignment with gap analysis
DISCOVERY_OUTPUT_FORMAT = "markdown"  # Match gap analysis exactly
DISCOVERY_EXPORT_PREFIX = "discovery"  # exports/discovery_YYYY_MM_DD.md

# ============================================================================
# GAP ANALYSIS CONFIGURATION
# ============================================================================

# Gap detection thresholds
GAP_ANALYSIS_MIN_CITATIONS_DEFAULT = 0
GAP_ANALYSIS_MIN_KB_CONNECTIONS = 2  # Min KB papers that must cite a gap
GAP_ANALYSIS_MAX_GAPS_PER_TYPE = 1000  # Prevent overwhelming results

# Author network recency settings
GAP_ANALYSIS_AUTHOR_RECENCY_DEFAULT = 2022  # Conservative default (3 years)
GAP_ANALYSIS_AUTHOR_RECENCY_MIN = 2015  # Minimum allowed value (10 years)
GAP_ANALYSIS_AUTHOR_RECENCY_MAX = 2024  # Maximum allowed value (current year)

# API rate limiting (token bucket pattern)
API_RATE_LIMIT_RPS = 1.0  # Semantic Scholar actual limit: 1 RPS (unauthenticated shared pool)
API_RATE_LIMIT_BURST = 3  # Conservative burst allowance
API_RATE_LIMIT_RETRY_DELAY = 1.0  # Base delay for exponential backoff

# Citation network analysis
CITATION_NETWORK_MAX_DEPTH = 2  # How deep to traverse citation networks
CITATION_RELEVANCE_THRESHOLD = 0.1  # Min relevance score for inclusion

# Simplified author network analysis
AUTHOR_NETWORK_USE_EXISTING_IDS = True  # Use Semantic Scholar IDs from KB metadata
AUTHOR_NETWORK_MAX_RECENT_PAPERS = 20  # Limit papers per author to prevent overwhelming
AUTHOR_NETWORK_TOPIC_SIMILARITY_THRESHOLD = 0.6  # Minimum topic similarity to KB

# Report generation
GAP_REPORT_MAX_PAPERS_PER_BLOCK = 20  # Max papers per thematic block
GAP_REPORT_BLOCK_MIN_SIZE = 3  # Min papers needed to form a block
GAP_REPORT_EXPLANATION_MAX_LENGTH = 200  # Max chars for relevance explanations

# Confidence indicators for user guidance
CONFIDENCE_HIGH_THRESHOLD = 0.8  # HIGH priority gaps
CONFIDENCE_MEDIUM_THRESHOLD = 0.6  # MEDIUM priority gaps
CONFIDENCE_LOW_THRESHOLD = 0.4  # LOW priority gaps

# Performance settings
GAP_ANALYSIS_SEQUENTIAL_PROCESSING = True  # Sequential processing due to rate limits
GAP_ANALYSIS_API_BATCH_SIZE = 500  # Papers per API batch request (use bulk endpoints)
GAP_ANALYSIS_CACHE_EXPIRY_DAYS = 7  # Cache API responses for 7 days
GAP_ANALYSIS_PROACTIVE_DELAY = 1.0  # Pre-emptive delay between API requests (seconds)
GAP_ANALYSIS_ADAPTIVE_DELAY = 2.0  # Increased delay when rate limiting detected
