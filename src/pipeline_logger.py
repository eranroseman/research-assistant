#!/usr/bin/env python3
"""Logging and display utilities for V5 pipeline.

Provides dual output:
1. Clean console display (40-line dashboard)
2. Detailed log files for debugging
"""

import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Any
from dataclasses import dataclass


@dataclass
class StageStats:
    """Statistics for a pipeline stage."""

    name: str
    current: int = 0
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    start_time: float | None = None
    elapsed: float = 0.0
    status: str = "Waiting"
    current_file: str = ""


class PipelineLogger:
    """Separate logging from display for clean output + detailed logs."""

    def __init__(self, stage_name: str, log_dir: Path = Path("logs")):
        """Initialize dual logging system.

        Args:
            stage_name: Name of the pipeline stage
            log_dir: Directory for log files
        """
        self.stage_name = stage_name
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)

        # Create timestamp for this run
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Setup file logging (detailed)
        self.file_logger = self._setup_file_logger()

        # Setup master pipeline log (summary)
        self.master_logger = self._setup_master_logger()

    def _setup_file_logger(self) -> logging.Logger:
        """Setup detailed stage-specific file logger."""
        log_file = self.log_dir / f"{self.stage_name}_{self.timestamp}.log"

        logger = logging.getLogger(f"{self.stage_name}_file")
        logger.setLevel(logging.DEBUG)

        # Remove any existing handlers
        logger.handlers = []

        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)

        return logger

    def _setup_master_logger(self) -> logging.Logger:
        """Setup master pipeline summary logger."""
        master_log = self.log_dir / f"pipeline_{self.timestamp}.log"

        logger = logging.getLogger("pipeline_master")
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not logger.handlers:
            handler = logging.FileHandler(master_log, mode="a")
            handler.setFormatter(logging.Formatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"))
            logger.addHandler(handler)

        return logger

    def debug(self, message: str, **kwargs):
        """Log debug message (file only)."""
        self.file_logger.debug(message, **kwargs)

    def info(self, message: str, to_master: bool = False):
        """Log info message."""
        self.file_logger.info(message)
        if to_master:
            self.master_logger.info(f"[{self.stage_name}] {message}")

    def warning(self, message: str, to_master: bool = True):
        """Log warning message."""
        self.file_logger.warning(message)
        if to_master:
            self.master_logger.warning(f"[{self.stage_name}] {message}")

    def error(self, message: str, exc_info: bool = False, to_master: bool = True):
        """Log error message."""
        self.file_logger.error(message, exc_info=exc_info)
        if to_master:
            # Don't include full traceback in master log
            self.master_logger.error(f"[{self.stage_name}] {message}")

    def success(self, paper_id: str, details: str | None = None):
        """Log successful processing."""
        if details:
            self.file_logger.info(f"✓ {paper_id}: {details}")
        else:
            self.file_logger.info(f"✓ {paper_id}")
        self.master_logger.info(f"[{self.stage_name}] ✓ {paper_id}")

    def failure(self, paper_id: str, reason: str):
        """Log failed processing."""
        self.file_logger.error(f"✗ {paper_id}: {reason}")
        self.master_logger.error(f"[{self.stage_name}] ✗ {paper_id}: {reason[:50]}")


class PipelineDashboard:
    """40-line dashboard display that updates in place."""

    def __init__(self, total_stages: int = 8):
        """Initialize dashboard.

        Args:
            total_stages: Total number of pipeline stages
        """
        self.stages: dict[str, StageStats] = {}
        self.total_stages = total_stages
        self.recent_events = []
        self.start_time = time.time()
        self.last_draw_time = 0
        self.min_redraw_interval = 0.1  # Don't redraw more than 10x per second

        # Terminal control
        self.lines_drawn = 0

    def add_stage(self, name: str, total: int):
        """Add a stage to track."""
        self.stages[name] = StageStats(name=name, total=total)

    def update_stage(self, name: str, **kwargs):
        """Update stage statistics."""
        if name not in self.stages:
            return

        stage = self.stages[name]
        for key, value in kwargs.items():
            if hasattr(stage, key):
                setattr(stage, key, value)

        # Update elapsed time if running
        if stage.status == "Running" and stage.start_time:
            stage.elapsed = time.time() - stage.start_time

        self._redraw()

    def add_event(self, event: str):
        """Add a recent event to display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_events.append(f"[{timestamp}] {event}")

        # Keep only last 5 events
        if len(self.recent_events) > 5:
            self.recent_events.pop(0)

        self._redraw()

    def _redraw(self):
        """Redraw the dashboard (rate-limited)."""
        current_time = time.time()
        if current_time - self.last_draw_time < self.min_redraw_interval:
            return

        self.last_draw_time = current_time

        # Clear previous output
        if self.lines_drawn > 0:
            # Move cursor up and clear
            sys.stdout.write(f"\033[{self.lines_drawn}A")  # Move up
            sys.stdout.write("\033[J")  # Clear from cursor down

        # Draw new output
        lines = self._generate_display()
        for line in lines:
            print(line)

        self.lines_drawn = len(lines)
        sys.stdout.flush()

    def _generate_display(self) -> list[str]:
        """Generate the 40-line display."""
        lines = []

        # Header (3 lines)
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)

        lines.append("V5 PIPELINE | 2000 papers")
        lines.append("=" * 70)
        lines.append(
            f"Elapsed: {elapsed_str} | Started: {datetime.fromtimestamp(self.start_time).strftime('%H:%M:%S')}"
        )
        lines.append("")

        # Stage progress table header (2 lines)
        lines.append("STAGE           PROGRESS                     DONE   OK    FAIL  TIME")
        lines.append("-" * 70)

        # Stage rows (8 lines)
        for i, (name, stage) in enumerate(self.stages.items(), 1):
            progress_bar = self._make_progress_bar(stage.current, stage.total)
            percent = (stage.current / stage.total * 100) if stage.total else 0
            time_str = self._format_time(stage.elapsed) if stage.elapsed else "-"

            # Status indicator
            if stage.status == "Complete":
                status_char = "✓"
            elif stage.status == "Running":
                status_char = "⟳"
            elif stage.status == "Failed":
                status_char = "✗"
            else:
                status_char = " "

            line = f"{i}. {name:12} {progress_bar} {percent:3.0f}%  {stage.current:4}  {stage.succeeded:4}  {stage.failed:4}  {time_str:6} {status_char}"
            lines.append(line)

        # Add empty stages if needed
        for i in range(len(self.stages), self.total_stages):
            lines.append(f"{i + 1}. {'':12} {'░' * 20}   0%     0     0     0      -")

        lines.append("-" * 70)

        # Current activity (3 lines)
        current_stage = self._get_current_stage()
        if current_stage:
            lines.append("")
            lines.append(f"► ACTIVE: {current_stage.name}")
            if current_stage.current_file:
                lines.append(f"  Current: {current_stage.current_file}")
            else:
                lines.append("")
        else:
            lines.extend(["", "", ""])

        # Recent events (7 lines)
        lines.append("")
        lines.append("► RECENT LOG:")
        for event in self.recent_events[-5:]:
            lines.append(f"  {event}")

        # Pad if needed
        while len(lines) < 30:
            lines.append("")

        # Statistics (5 lines)
        total_processed = sum(s.current for s in self.stages.values())
        total_succeeded = sum(s.succeeded for s in self.stages.values())
        total_failed = sum(s.failed for s in self.stages.values())
        total_possible = sum(s.total for s in self.stages.values())

        success_rate = (total_succeeded / total_processed * 100) if total_processed else 0
        overall_progress = (total_processed / total_possible * 100) if total_possible else 0

        lines.append("")
        lines.append("► STATISTICS:")
        lines.append(
            f"  Total: {total_processed}/{total_possible} ({overall_progress:.1f}%) | Success: {success_rate:.1f}%"
        )
        lines.append(f"  Succeeded: {total_succeeded} | Failed: {total_failed}")

        # Footer (1 line)
        lines.append("=" * 70)

        # Ensure exactly 40 lines
        while len(lines) < 40:
            lines.append("")

        return lines[:40]

    def _get_current_stage(self) -> StageStats | None:
        """Get the currently running stage."""
        for stage in self.stages.values():
            if stage.status == "Running":
                return stage
        return None

    def _make_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Create a progress bar string."""
        if total == 0:
            return "░" * width

        percent = current / total
        filled = int(percent * width)
        empty = width - filled

        return "█" * filled + "░" * empty

    def _format_time(self, seconds: float) -> str:
        """Format seconds as compact time string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m{secs}s"
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h{mins}m"

    def finish(self):
        """Clean finish of dashboard."""
        # Leave the final display on screen


class MinimalProgressBar:
    """Simple progress bar for quiet mode."""

    def __init__(self, stage_name: str, total: int):
        """Initialize minimal progress bar.

        Args:
            stage_name: Name of the stage
            total: Total items to process
        """
        self.stage_name = stage_name
        self.total = total
        self.current = 0
        self.succeeded = 0
        self.failed = 0
        self.start_time = time.time()

    def update(self, current: int, succeeded: int, failed: int):
        """Update progress."""
        self.current = current
        self.succeeded = succeeded
        self.failed = failed

        # Single line update
        percent = (current / self.total * 100) if self.total else 0
        elapsed = time.time() - self.start_time
        rate = current / elapsed if elapsed > 0 else 0

        # Progress bar
        bar_width = 20
        filled = int(percent / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Format output
        output = f"\r[{self.stage_name:12}] {bar} {current:4}/{self.total:4} "
        output += f"✓{succeeded:4} ✗{failed:4} "
        output += f"[{self._format_time(elapsed)}] "

        if percent >= 100:
            output += "✓"

        sys.stdout.write(output)
        sys.stdout.flush()

    def finish(self):
        """Finish the progress bar."""
        print()  # New line after progress bar

    def _format_time(self, seconds: float) -> str:
        """Format time compactly."""
        if seconds < 60:
            return f"{int(seconds)}s"
        if seconds < 3600:
            return f"{int(seconds / 60)}m{int(seconds % 60)}s"
        return f"{int(seconds / 3600)}h{int((seconds % 3600) / 60)}m"


def get_progress_reporter(verbose: int = 0, quiet: bool = False, dashboard: bool = True) -> Any:
    """Get appropriate progress reporter based on settings.

    Args:
        verbose: Verbosity level (0=normal, 1=verbose, 2=debug)
        quiet: Minimal output mode
        dashboard: Use full dashboard display

    Returns:
        Progress reporter instance
    """
    if quiet:
        return MinimalProgressBar
    if dashboard and sys.stdout.isatty():
        return PipelineDashboard
    # Fallback to simple logging
    return MinimalProgressBar
