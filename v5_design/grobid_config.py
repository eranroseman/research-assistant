#!/usr/bin/env python3
"""Grobid Maximum Extraction Configuration.

This module defines the maximum extraction parameters for Grobid processing.
Philosophy: Always extract EVERYTHING since we run Grobid rarely.
"""

from src import config


def get_maximum_extraction_params():
    """Maximum Grobid parameters for overnight/weekend extraction.

    Rationale: Since we run Grobid rarely (overnight/weekend), maximize data extraction
    and save everything for flexible post-processing experimentation.

    Processing time: ~25-40s/paper (acceptable for overnight runs)
    Data extracted: 95% of all possible entities and structures

    Returns:
        dict: Complete parameter set for maximum extraction
    """
    return {
        # Maximum consolidation (external enrichment)
        # IMPORTANT: Testing on Aug 2025 proved consolidation=2 adds only ~1s overhead!
        # Azure test results: Local consolidation: 17.1s avg, Biblio-glutton: 17.9s avg
        "consolidateHeader": "2",  # Biblio-glutton - tested <1s overhead, max enrichment
        "consolidateCitations": "2",  # Full citation enrichment - minimal overhead confirmed
        "consolidateFunders": "1",  # Extract all funding information
        # Preserve ALL raw data for post-processing flexibility
        "includeRawCitations": "1",  # Keep original citation strings
        "includeRawAffiliations": "1",  # Keep original affiliation strings
        "includeRawAuthors": "1",  # Keep original author strings
        "includeRawCopyrights": "1",  # Keep copyright information
        # Extract ALL structures
        "processFigures": "1",  # Extract figure captions (often contain results)
        "processTables": "1",  # Extract table data (sample sizes, baselines)
        "processEquations": "1",  # Extract equations
        "segmentSentences": "1",  # Sentence-level segmentation
        # Complete coordinate mapping for spatial analysis
        "teiCoordinates": "all",  # Get coordinates for ALL elements
        # Full XML structure
        "generateIDs": "1",  # Generate unique IDs for all elements
        "addElementId": "1",  # Add xml:id to all elements
        # Extended timeout for complex papers
        "timeout": 300,  # 5 minutes per paper (fine for overnight)
    }


def get_balanced_extraction_params():
    """DEPRECATED - We NEVER use this in practice.

    Kept for reference only.

    Processing time: ~16s/paper
    Data extracted: 70% of entities
    """
    return {
        "consolidateHeader": "1",  # Basic consolidation
        "consolidateCitations": "1",  # Basic citation enrichment
        "consolidateFunders": "0",  # Skip funding
        "includeRawCitations": "0",  # Don't keep raw
        "includeRawAffiliations": "0",
        "processFigures": "0",  # Skip figures
        "processTables": "0",  # Skip tables
        "timeout": 60,
    }


def get_minimal_extraction_params():
    """DEPRECATED - We NEVER use this in practice.

    Kept for reference only.

    Processing time: ~4s/paper
    Data extracted: 30% of entities
    """
    return {
        "consolidateHeader": "0",  # No consolidation
        "consolidateCitations": "0",  # No enrichment
        "timeout": 30,
    }


# The ONLY configuration we use in practice
GROBID_PARAMS = get_maximum_extraction_params()


def estimate_processing_time(num_papers: int, mode: str = "maximum") -> dict:
    """Estimate processing time for different extraction modes.

    Updated Aug 2025 based on actual Azure testing:
    - Consolidation=2 (biblio-glutton): 17.9s average
    - Consolidation=1 (local): 17.1s average
    - Consolidation=0 (none): 14.2s average

    Args:
        num_papers: Number of papers to process
        mode: Extraction mode ('maximum', 'balanced', 'minimal')

    Returns:
        dict: Time estimates and recommendations
    """
    rates = {
        "maximum": 18,  # 17.9s per paper (tested on Azure, Aug 2025)
        "balanced": 17,  # 17.1s per paper (NOT USED - local consolidation)
        "minimal": 14,  # 14.2s per paper (NOT USED - no consolidation)
    }

    seconds_per_paper = rates.get(mode, 35)
    total_seconds = num_papers * seconds_per_paper
    hours = total_seconds / 3600

    # Add 20% overhead for network, I/O, etc.
    hours_with_overhead = hours * 1.2

    # Uncertainty range (±30%)
    min_hours = hours_with_overhead * 0.7
    max_hours = hours_with_overhead * 1.3

    return {
        "estimated_hours": hours_with_overhead,
        "range": (min_hours, max_hours),
        "formatted": f"{hours_with_overhead:.1f} hours ({min_hours:.1f} - {max_hours:.1f} hours)",
        "recommendation": get_timing_recommendation(num_papers),
        "when_to_run": get_run_schedule(hours_with_overhead),
    }


def get_timing_recommendation(num_papers: int) -> str:
    """Get recommendation based on paper count.

    .
    """
    if num_papers < config.SMALL_PAPERS_BATCH:
        return "Run anytime - will complete in < 1 hour"
    if num_papers < config.MEDIUM_PAPERS_BATCH:
        return "Run during lunch or meeting - will complete in 3-4 hours"
    if num_papers < config.LARGE_PAPERS_BATCH:
        return "Run overnight - will complete in 7-8 hours"
    if num_papers < config.VERY_LARGE_PAPERS_BATCH:
        return "Run overnight or weekend - will complete in 14-16 hours"
    return "Run over weekend - will take 1-2 days"


def get_run_schedule(hours: float) -> str:
    """Suggest when to run based on estimated time.

    .
    """
    if hours < 1:
        return "Anytime"
    if hours < config.PROCESSING_TIME_SHORT:
        return "Lunch break"
    if hours < config.PROCESSING_TIME_MEDIUM:
        return "Overnight"
    if hours < config.PROCESSING_TIME_LONG:
        return "Weekend"
    return "Long weekend"


# Entity extraction patterns
ENTITY_PATTERNS = {
    "sample_sizes": [
        r"n\s*=\s*(\d+)",
        r"N\s*=\s*(\d+)",
        r"(\d+)\s+participants?",
        r"(\d+)\s+patients?",
        r"(\d+)\s+subjects?",
    ],
    "p_values": [r"p\s*[<=]\s*0\.\d+", r"P\s*[<=]\s*0\.\d+", r"p-value[s]?\s*[<=]\s*0\.\d+"],
    "confidence_intervals": [r"95%\s*CI", r"99%\s*CI", r"confidence interval", r"CI:\s*\[?[\d\.\-\s,]+\]?"],
    "software": [
        r"SPSS\s*v?[\d\.]*",
        r"R\s+(?:version\s*)?[\d\.]+",
        r"Python\s*[\d\.]*",
        r"MATLAB",
        r"SAS\s*v?[\d\.]*",
        r"Stata\s*v?[\d\.]*",
    ],
    "datasets": [r"MIMIC-(?:III|IV)", r"UK\s*Biobank", r"NHANES", r"eICU", r"PhysioNet"],
}
