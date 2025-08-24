#!/usr/bin/env python3
"""Unified help text and usage example formatting for Research Assistant.

Provides consistent help presentation across all modules with:
- Standardized command descriptions and examples
- Consistent formatting and visual hierarchy
- Reusable help text templates for common patterns
- Integration with Click command system

Usage:
    from help_formatting import format_command_help, format_examples, HelpFormatter

    @click.command()
    @format_command_help(
        "Search papers by semantic similarity",
        examples=[
            'python src/cli.py search "diabetes machine learning"',
            'python src/cli.py search "telemedicine" --quality-min 70 --show-quality'
        ]
    )
    def search_command():
        pass
"""

from typing import Any
from collections.abc import Callable


class HelpFormatter:
    """Consistent help text formatter for Research Assistant commands."""

    def __init__(self) -> None:
        """Initialize help formatter with default settings."""
        self.width = 80
        self.indent = "  "

    def format_command_help(
        self,
        description: str,
        examples: list[str] | None = None,
        notes: list[str] | None = None,
        see_also: list[str] | None = None,
    ) -> str:
        """Format comprehensive command help text.

        Args:
            description: Brief command description
            examples: List of usage examples
            notes: Additional notes or tips
            see_also: Related commands or resources

        Returns:
            Formatted help text string
        """
        lines = [description]

        if examples:
            lines.append("")
            lines.append("Examples:")
            for example in examples:
                lines.append(f"{self.indent}{example}")

        if notes:
            lines.append("")
            lines.append("Notes:")
            for note in notes:
                lines.append(f"{self.indent}• {note}")

        if see_also:
            lines.append("")
            lines.append("See also:")
            for item in see_also:
                lines.append(f"{self.indent}• {item}")

        return "\n".join(lines)

    def format_examples(self, examples: list[str], title: str = "Examples:") -> str:
        """Format just the examples section.

        Args:
            examples: List of usage examples
            title: Section title

        Returns:
            Formatted examples string
        """
        lines = [title]
        for example in examples:
            lines.append(f"{self.indent}{example}")
        return "\n".join(lines)

    def format_option_help(
        self,
        option_name: str,
        description: str,
        examples: list[str] | None = None,
        default: str | None = None,
    ) -> str:
        """Format help for individual options.

        Args:
            option_name: Name of the option (e.g., "--quality-min")
            description: Option description
            examples: Usage examples for this option
            default: Default value if any

        Returns:
            Formatted option help string
        """
        lines = [f"{option_name}: {description}"]

        if default:
            lines.append(f"{self.indent}Default: {default}")

        if examples:
            lines.append(f"{self.indent}Examples:")
            for example in examples:
                lines.append(f"{self.indent}{self.indent}{example}")

        return "\n".join(lines)


# Global formatter instance
_formatter = HelpFormatter()


def format_command_help(
    description: str,
    examples: list[str] | None = None,
    notes: list[str] | None = None,
    see_also: list[str] | None = None,
) -> str:
    """Format comprehensive command help text.

    Args:
        description: Brief command description
        examples: List of usage examples
        notes: Additional notes or tips
        see_also: Related commands or resources

    Returns:
        Formatted help text string
    """
    return _formatter.format_command_help(description, examples, notes, see_also)


def format_examples(examples: list[str], title: str = "Examples:") -> str:
    """Format just the examples section.

    Args:
        examples: List of usage examples
        title: Section title

    Returns:
        Formatted examples string
    """
    return _formatter.format_examples(examples, title)


# Pre-configured help templates for common Research Assistant patterns
COMMAND_HELP_TEMPLATES = {
    "search": {
        "description": "Find papers by semantic similarity with advanced filtering options",
        "examples": [
            'python src/cli.py search "machine learning healthcare"',
            'python src/cli.py search "diabetes" --quality-min 70 --show-quality',
            'python src/cli.py search "telemedicine" --year-from 2020 -k 20',
        ],
        "notes": [
            "Results ranked by semantic similarity using Multi-QA MPNet embeddings",
            "Quality scores range from 0-100 (study type, citations, recency)",
            "Use --show-quality to see quality scores and confidence indicators",
        ],
        "see_also": [
            "smart-search: For handling large result sets (20+ papers)",
            "author: Search by specific author name",
        ],
    },
    "get": {
        "description": "Retrieve specific paper by ID with optional section filtering",
        "examples": [
            "python src/cli.py get 0042",
            "python src/cli.py get 0001 --sections abstract methods results",
            "python src/cli.py get 1234 --cite",
        ],
        "notes": [
            "Paper IDs are 4-digit numbers (0001, 0042, 1234)",
            "Available sections: abstract, introduction, methods, results, discussion, conclusion",
            "Use --cite to include IEEE-format citation",
        ],
        "see_also": [
            "get-batch: Retrieve multiple papers efficiently",
            "cite: Generate citations for multiple papers",
        ],
    },
    "build_kb": {
        "description": "Build or update knowledge base from Zotero library",
        "examples": [
            "python src/build_kb.py",
            "python src/build_kb.py --demo",
            "python src/build_kb.py --rebuild",
        ],
        "notes": [
            "Safe by default - never auto-rebuilds, preserves existing data",
            "Use --demo for 5-paper test knowledge base (no Zotero needed)",
            "Use --rebuild only when explicitly needed (destructive operation)",
        ],
        "see_also": ["diagnose: Check knowledge base health", "info: View knowledge base statistics"],
    },
    "discover": {
        "description": "Discover external papers via Semantic Scholar (214M paper database)",
        "examples": [
            'python src/discover.py --keywords "diabetes,mobile health"',
            'python src/discover.py --keywords "AI,diagnostics" --quality-threshold HIGH',
            'python src/discover.py --keywords "telemedicine" --population-focus pediatric',
        ],
        "notes": [
            "Excludes papers already in your knowledge base by default",
            "Quality thresholds: HIGH (80+), MEDIUM (60+), LOW (40+)",
            "Population focus options: pediatric, elderly, women, men, developing_countries",
        ],
        "see_also": [
            "Coverage info: python src/discover.py --coverage-info",
            "Gap analysis: Run after successful KB builds",
        ],
    },
}


def get_command_help(command_name: str, **kwargs: Any) -> str:
    """Get pre-configured help for common commands.

    Args:
        command_name: Command name from COMMAND_HELP_TEMPLATES
        **kwargs: Override any help fields

    Returns:
        Formatted command help string
    """
    if command_name not in COMMAND_HELP_TEMPLATES:
        raise ValueError(f"Unknown command template: {command_name}")

    help_config = COMMAND_HELP_TEMPLATES[command_name].copy()
    help_config.update(kwargs)

    return format_command_help(
        str(help_config["description"]),
        list(help_config.get("examples", [])) if help_config.get("examples") else None,
        list(help_config.get("notes", [])) if help_config.get("notes") else None,
        list(help_config.get("see_also", [])) if help_config.get("see_also") else None,
    )


def click_help_decorator(
    command_name: str, **kwargs: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to apply consistent help text to Click commands.

    Args:
        command_name: Command name from COMMAND_HELP_TEMPLATES
        **kwargs: Override any help fields

    Returns:
        Click command decorator
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        help_text = get_command_help(command_name, **kwargs)
        func.__doc__ = help_text
        return func

    return decorator
