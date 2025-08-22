#!/usr/bin/env python3
"""Optimized knowledge base index for O(1) paper lookups.

This module provides fast, constant-time access to papers by ID,
avoiding the O(n) linear search through all papers. Also provides
author search, year filtering, and consistency validation.

Key features:
- O(1) paper lookup by ID using dictionary
- O(1) mapping between paper IDs and FAISS indices
- Author search with partial matching
- Year range filtering
- Consistency validation for data integrity

Usage:
    kb_index = KnowledgeBaseIndex()
    paper = kb_index.get_paper_by_id("0042")  # O(1) lookup
    papers = kb_index.search_by_author("Smith")  # Author search
"""

import json
from pathlib import Path
from typing import Any


class KnowledgeBaseIndex:
    """Efficient index for knowledge base operations.

    Provides O(1) lookups and maintains consistency between paper IDs
    and FAISS indices. Builds a dictionary mapping on initialization
    for fast access without repeated linear searches.

    Attributes:
        papers: List of all paper metadata dictionaries
        id_to_index: Dict mapping paper IDs to list indices
        metadata: Full KB metadata including version and stats
    """

    def __init__(self, kb_path: str = "kb_data"):
        """Initialize KB index with O(1) lookup structures.

        Loads metadata once and builds dictionary mappings for
        constant-time access to papers by ID.

        Args:
            kb_path: Path to knowledge base directory (default: kb_data)

        Raises:
            FileNotFoundError: If knowledge base doesn't exist
            ValueError: If metadata file is corrupted
        """
        self.kb_path = Path(kb_path)
        self.metadata_file = self.kb_path / "metadata.json"
        self.papers: list[dict[str, Any]] = []
        self.id_to_index: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        """Load metadata and build O(1) lookup index.

        Builds dictionary mapping paper IDs to list indices,
        enabling constant-time lookups instead of O(n) searches.
        """
        if not self.metadata_file.exists():
            raise FileNotFoundError(
                f"Knowledge base not found at {self.kb_path}. Run 'python src/build_kb.py' first.",
            )

        try:
            with self.metadata_file.open() as f:
                metadata = json.load(f)
        except json.JSONDecodeError as error:
            raise ValueError(f"Corrupted metadata file: {error}") from error

        self.papers = metadata.get("papers", [])
        self.metadata = metadata  # Store full metadata

        # Build ID lookup index - O(n) once at startup
        self.id_to_index = {paper["id"]: idx for idx, paper in enumerate(self.papers)}

    def get_paper_by_id(self, paper_id: str) -> dict[str, Any] | None:
        """Get paper by ID - O(1) lookup.

        Args:
            paper_id: Paper ID (will be zero-padded if needed)

        Returns:
            Paper dict or None if not found
        """
        # Normalize paper ID
        paper_id = self._normalize_id(paper_id)

        idx = self.id_to_index.get(paper_id)
        if idx is not None:
            return self.papers[idx]
        return None

    def get_paper_with_index(self, paper_id: str) -> tuple[dict[str, Any], int] | None:
        """Get paper and its FAISS index - O(1) lookup.

        Args:
            paper_id: Paper ID

        Returns:
            Tuple of (paper dict, FAISS index) or None
        """
        paper_id = self._normalize_id(paper_id)

        idx = self.id_to_index.get(paper_id)
        if idx is not None:
            return self.papers[idx], idx
        return None

    def get_paper_by_index(self, index: int) -> dict[str, Any] | None:
        """Get paper by FAISS index - O(1) lookup.

        Args:
            index: FAISS index

        Returns:
            Paper dict or None if index out of range
        """
        if 0 <= index < len(self.papers):
            return self.papers[index]
        return None

    def get_papers_by_ids(self, paper_ids: list[str]) -> list[dict[str, Any]]:
        """Get multiple papers by IDs efficiently.

        Args:
            paper_ids: List of paper IDs

        Returns:
            List of paper dicts (skips not found)
        """
        papers = []
        for paper_id in paper_ids:
            paper = self.get_paper_by_id(paper_id)
            if paper:
                papers.append(paper)
        return papers

    def search_by_author(self, author_name: str) -> list[dict[str, Any]]:
        """Search papers by author name.

        Performs case-insensitive partial matching against all author names
        in each paper. Useful for finding all works by a researcher.

        Args:
            author_name: Author name (case-insensitive partial match)

        Returns:
            List of matching papers

        Examples:
            >>> kb_index.search_by_author("Smith")
            [{"id": "0001", "authors": ["John Smith", "Jane Doe"], ...}, ...]

            >>> kb_index.search_by_author("jane doe")  # Case insensitive
            [{"id": "0042", "authors": ["Jane Doe", "Bob Wilson"], ...}, ...]

            >>> kb_index.search_by_author("rodriguez")  # Partial match
            [{"id": "0123", "authors": ["Maria Rodriguez-Garcia"], ...}, ...]
        """
        author_lower = author_name.lower()
        results = []

        for paper in self.papers:
            authors = paper.get("authors", [])
            if any(author_lower in author.lower() for author in authors):
                results.append(paper)

        return results

    def search_by_year_range(self, start_year: int, end_year: int) -> list[dict[str, Any]]:
        """Get papers within year range.

        Args:
            start_year: Start year (inclusive)
            end_year: End year (inclusive)

        Returns:
            List of papers in range
        """
        results = []
        for paper in self.papers:
            year = paper.get("year", 0)
            if start_year <= year <= end_year:
                results.append(paper)
        return results

    def _normalize_id(self, paper_id: str) -> str:
        """Normalize paper ID to 4-digit format.

        Args:
            paper_id: Raw paper ID

        Returns:
            Normalized 4-digit ID

        Raises:
            ValueError: If paper ID is invalid

        Note:
            Error cases:
            - "abc" → ValueError: Invalid paper ID (non-numeric)
            - "10000" → ValueError: Invalid paper ID (out of range 1-9999)
            - "" → ValueError: Invalid paper ID (empty string)
            - "0" → ValueError: Invalid paper ID (must be 1-9999)

            Valid transformations:
            - "1" → "0001"
            - "42" → "0042"
            - "0123" → "0123"
            - " 234 " → "0234" (strips whitespace)
        """
        # Remove any dangerous characters
        paper_id = paper_id.strip()

        # Try to parse as number and zero-pad
        try:
            num = int(paper_id)
            if 1 <= num <= 9999:
                return f"{num:04d}"
        except ValueError:
            pass

        # If already 4 digits, return as is
        if len(paper_id) == 4 and paper_id.isdigit():
            return paper_id

        raise ValueError(f"Invalid paper ID: {paper_id}")

    def validate_consistency(self) -> dict[str, Any]:
        """Validate index consistency.

        Returns:
            Dictionary with validation results
        """
        issues = []

        # Check for duplicate IDs
        seen_ids = set()
        for paper in self.papers:
            paper_id = paper.get("id")
            if paper_id in seen_ids:
                issues.append(f"Duplicate ID: {paper_id}")
            seen_ids.add(paper_id)

        # Check index mapping
        for paper_id, idx in self.id_to_index.items():
            if idx >= len(self.papers):
                issues.append(f"Index out of range: {paper_id} -> {idx}")
            elif self.papers[idx]["id"] != paper_id:
                issues.append(f"Index mismatch: {paper_id} != {self.papers[idx]['id']}")

        # Check FAISS index alignment
        import faiss

        index_file = self.kb_path / "index.faiss"
        if index_file.exists():
            try:
                faiss_index = faiss.read_index(str(index_file))
                if faiss_index.ntotal != len(self.papers):
                    issues.append(f"FAISS index size mismatch: {faiss_index.ntotal} != {len(self.papers)}")
            except Exception as error:
                issues.append(f"Cannot read FAISS index: {error}")

        return {
            "valid": len(issues) == 0,
            "total_papers": len(self.papers),
            "unique_ids": len(self.id_to_index),
            "issues": issues,
        }

    def get_papers_by_quality_range(self, min_quality: int, max_quality: int = 100) -> list[dict[str, Any]]:
        """Get papers within quality score range.

        Args:
            min_quality: Minimum quality score (inclusive)
            max_quality: Maximum quality score (inclusive, default 100)

        Returns:
            List of papers within the specified quality range
        """
        return [paper for paper in self.papers if min_quality <= paper.get("quality_score", 0) <= max_quality]

    def get_top_quality_papers(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get highest quality papers.

        Args:
            limit: Maximum number of papers to return

        Returns:
            List of papers sorted by quality score (highest first)
        """
        return sorted(self.papers, key=lambda p: p.get("quality_score", 0), reverse=True)[:limit]

    def get_quality_distribution(self) -> dict[str, int]:
        """Get distribution of papers across quality levels.

        Returns:
            Dictionary with quality level names and counts
        """
        # Use hardcoded thresholds to avoid import redefinition issues
        # These match the values in config.py
        excellent_threshold = 85  # QUALITY_EXCELLENT
        very_good_threshold = 70  # QUALITY_VERY_GOOD
        good_threshold = 60  # QUALITY_GOOD
        moderate_threshold = 45  # QUALITY_MODERATE
        low_threshold = 30  # QUALITY_LOW

        distribution = {
            "excellent": 0,  # 85+
            "very_good": 0,  # 70-84
            "good": 0,  # 60-69
            "moderate": 0,  # 45-59
            "low": 0,  # 30-44
            "very_low": 0,  # 0-29
        }

        for paper in self.papers:
            quality = paper.get("quality_score", 0)
            if quality >= excellent_threshold:
                distribution["excellent"] += 1
            elif quality >= very_good_threshold:
                distribution["very_good"] += 1
            elif quality >= good_threshold:
                distribution["good"] += 1
            elif quality >= moderate_threshold:
                distribution["moderate"] += 1
            elif quality >= low_threshold:
                distribution["low"] += 1
            else:
                distribution["very_low"] += 1

        return distribution

    def stats(self) -> dict[str, Any]:
        """Get enhanced index statistics including quality distribution."""
        year_counts: dict[int | str, int] = {}
        for paper in self.papers:
            year = paper.get("year", "Unknown")
            year_counts[year] = year_counts.get(year, 0) + 1

        # Add quality statistics - all papers should have quality scores
        quality_scores = [
            p.get("quality_score", 0) for p in self.papers if p.get("quality_score") is not None
        ]

        base_stats = {
            "total_papers": len(self.papers),
            "unique_ids": len(self.id_to_index),
            "year_distribution": year_counts,
            "has_faiss_index": (self.kb_path / "index.faiss").exists(),
        }

        # Add quality statistics if papers have quality scores
        if quality_scores:
            base_stats.update(
                {
                    "quality_stats": {
                        "average_quality": sum(quality_scores) / len(quality_scores),
                        "highest_quality": max(quality_scores),
                        "lowest_quality": min(quality_scores),
                        "papers_with_quality": len(quality_scores),
                        "total_papers": len(self.papers),
                    },
                    "quality_distribution": self.get_quality_distribution(),
                },
            )
        else:
            base_stats["quality_stats"] = {"message": "No papers with quality scores found"}

        return base_stats
