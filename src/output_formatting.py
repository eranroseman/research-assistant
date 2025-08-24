#!/usr/bin/env python3
"""Unified output formatting for Research Assistant.

Provides consistent output presentation across all modules with:
- Standardized progress indicators and status messages
- Consistent result formatting and visual hierarchy
- Reusable output templates for common patterns
- Integration with command usage analytics

Usage:
    from output_formatting import (
        format_progress, format_results, format_status,
        OutputFormatter, ProgressTracker
    )

    # Progress tracking
    progress = ProgressTracker("Processing papers", total=100)
    progress.update(25, "Enhanced quality scoring")

    # Results formatting
    formatter = OutputFormatter()
    formatter.print_results("Search Results", results, show_quality=True)
"""

import time
from typing import Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProgressItem:
    """Single progress tracking item."""

    current: int
    total: int
    message: str
    start_time: float
    last_update: float


class ProgressTracker:
    """Consistent progress tracking for long-running operations."""

    def __init__(self, operation: str, total: int, show_eta: bool = True):
        """Initialize progress tracker for long-running operations."""
        self.operation = operation
        self.total = total
        self.show_eta = show_eta
        self.start_time = time.time()
        self.current = 0
        self.last_update = self.start_time

    def update(self, current: int, message: str = "", force: bool = False):
        """Update progress with current count and optional message.

        Args:
            current: Current progress count
            message: Optional status message
            force: Force update even if time threshold not met
        """
        self.current = current
        now = time.time()

        # Only update display every 0.5 seconds unless forced
        if not force and (now - self.last_update) < 0.5:
            return

        self.last_update = now

        # Calculate progress percentage
        percentage = (current / self.total) * 100 if self.total > 0 else 0

        # Calculate ETA if enabled
        eta_str = ""
        if self.show_eta and current > 0:
            elapsed = now - self.start_time
            rate = current / elapsed
            remaining = (self.total - current) / rate if rate > 0 else 0
            eta_str = f" (ETA: {int(remaining // 60)}:{int(remaining % 60):02d})"

        # Format progress bar
        bar_width = 30
        filled = int(bar_width * percentage / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Print progress line
        status_line = f"\r🔄 {self.operation}: [{bar}] {percentage:.1f}% ({current}/{self.total}){eta_str}"
        if message:
            status_line += f" - {message}"

        print(status_line, end="", flush=True)

    def complete(self, message: str = ""):
        """Mark progress as complete.

        Args:
            message: Optional completion message
        """
        elapsed = time.time() - self.start_time
        elapsed_str = f"{int(elapsed // 60)}:{int(elapsed % 60):02d}"

        completion_msg = f"\r✅ {self.operation}: Complete ({self.total} items in {elapsed_str})"
        if message:
            completion_msg += f" - {message}"

        print(completion_msg + " " * 20)  # Clear any remaining characters


class OutputFormatter:
    """Consistent output formatting for Research Assistant commands."""

    def __init__(self, show_timestamps: bool = False):
        """Initialize output formatter with timestamp settings."""
        self.show_timestamps = show_timestamps

    def format_timestamp(self) -> str:
        """Get formatted timestamp if enabled."""
        if not self.show_timestamps:
            return ""
        return f"[{datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] "

    def print_header(self, title: str, subtitle: str = "") -> None:
        """Print consistent section header.

        Args:
            title: Main title
            subtitle: Optional subtitle
        """
        timestamp = self.format_timestamp()
        print(f"\n{timestamp}{'=' * 60}")
        print(f"{timestamp}{title}")
        if subtitle:
            print(f"{timestamp}{subtitle}")
        print(f"{timestamp}{'=' * 60}")

    def print_status(self, message: str, status_type: str = "info") -> None:
        """Print status message with consistent formatting.

        Args:
            message: Status message
            status_type: Type of status (info, success, warning, error)
        """
        timestamp = self.format_timestamp()
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌", "working": "🔄"}
        icon = icons.get(status_type, "•")
        print(f"{timestamp}{icon} {message}")

    def print_results(
        self,
        title: str,
        results: list[dict[str, Any]],
        show_quality: bool = False,
        show_citations: bool = False,
        max_results: int | None = None,
    ) -> None:
        """Print search results with consistent formatting.

        Args:
            title: Results section title
            results: List of result dictionaries
            show_quality: Show quality scores if available
            show_citations: Show citation counts if available
            max_results: Maximum number of results to display
        """
        if not results:
            self.print_status("No results found", "warning")
            return

        display_results = results[:max_results] if max_results else results
        truncated = len(results) > len(display_results) if max_results else False

        self.print_header(f"{title} ({len(display_results)} results)")

        for i, result in enumerate(display_results, 1):
            # Basic result info
            paper_id = result.get("id", "Unknown")
            title = result.get("title", "Unknown Title")
            authors = result.get("authors", ["Unknown"])
            year = result.get("year", "Unknown")

            # Format authors (limit to first 3)
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += f" et al. ({len(authors)} authors)"

            print(f"\n{i:2d}. [{paper_id}] {title}")
            print(f"    Authors: {author_str}")
            print(f"    Year: {year}")

            # Quality score if available and requested
            if show_quality and "quality_score" in result:
                quality = result["quality_score"]
                quality_grade = self._get_quality_grade(quality)
                print(f"    Quality: {quality}/100 ({quality_grade})")

            # Citations if available and requested
            if show_citations and "citation_count" in result:
                citations = result["citation_count"]
                print(f"    Citations: {citations}")

            # Similarity score if available
            if "similarity" in result:
                similarity = result["similarity"] * 100
                print(f"    Similarity: {similarity:.1f}%")

        if truncated:
            remaining = len(results) - len(display_results)
            print(f"\n... and {remaining} more results (use -k {len(results)} to see all)")

    def print_summary(self, stats: dict[str, Any]) -> None:
        """Print operation summary with consistent formatting.

        Args:
            stats: Dictionary of summary statistics
        """
        self.print_header("Summary")

        for key, value in stats.items():
            # Format key for display
            display_key = key.replace("_", " ").title()

            # Format value based on type
            if isinstance(value, float):
                if key.endswith(("_time", "_duration")):
                    # Time formatting
                    if value < 60:
                        display_value = f"{value:.1f}s"
                    else:
                        minutes = int(value // 60)
                        seconds = int(value % 60)
                        display_value = f"{minutes}:{seconds:02d}"
                else:
                    display_value = f"{value:.2f}"
            elif isinstance(value, int) and value > 1000:
                # Large number formatting
                display_value = f"{value:,}"
            else:
                display_value = str(value)

            print(f"  {display_key}: {display_value}")

    def _get_quality_grade(self, score: float) -> str:
        """Get letter grade for quality score.

        Args:
            score: Quality score (0-100)

        Returns:
            Letter grade (A+, A, B, C, D, F)
        """
        if score >= 85:
            return "A+"
        if score >= 70:
            return "A"
        if score >= 60:
            return "B"
        if score >= 45:
            return "C"
        if score >= 30:
            return "D"
        return "F"


# Global formatter instance
_formatter = OutputFormatter()


def format_progress(
    operation: str, current: int, total: int, message: str = "", show_eta: bool = True
) -> str:
    """Format progress string for display.

    Args:
        operation: Operation name
        current: Current progress count
        total: Total count
        message: Optional status message
        show_eta: Show estimated time to completion

    Returns:
        Formatted progress string
    """
    percentage = (current / total) * 100 if total > 0 else 0

    # Simple text progress bar
    bar_width = 20
    filled = int(bar_width * percentage / 100)
    bar = "█" * filled + "░" * (bar_width - filled)

    progress_str = f"{operation}: [{bar}] {percentage:.1f}% ({current}/{total})"
    if message:
        progress_str += f" - {message}"

    return progress_str


def format_status(message: str, status_type: str = "info") -> str:
    """Format status message with icon.

    Args:
        message: Status message
        status_type: Type of status (info, success, warning, error)

    Returns:
        Formatted status string
    """
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌", "working": "🔄"}
    icon = icons.get(status_type, "•")
    return f"{icon} {message}"


def print_header(title: str, subtitle: str = "") -> None:
    """Print consistent section header using global formatter."""
    _formatter.print_header(title, subtitle)


def print_status(message: str, status_type: str = "info") -> None:
    """Print status message using global formatter."""
    _formatter.print_status(message, status_type)


def print_results(title: str, results: list[dict[str, Any]], **kwargs: Any) -> None:
    """Print search results using global formatter."""
    _formatter.print_results(title, results, **kwargs)


def print_summary(stats: dict[str, Any]) -> None:
    """Print operation summary using global formatter."""
    _formatter.print_summary(stats)
