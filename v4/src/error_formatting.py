#!/usr/bin/env python3
"""Unified error message formatting for Research Assistant.

Provides consistent error presentation across all modules with:
- Standardized formatting with clear visual hierarchy
- Context-aware error messages with actionable guidance
- Consistent exit codes and error handling patterns
- Integration with command usage analytics

Usage:
    from error_formatting import format_error, safe_exit, ErrorFormatter

    # Simple error with auto-exit
    safe_exit("Knowledge base not found", "Run 'python src/build_kb.py --demo' to create one")

    # Custom formatting
    formatter = ErrorFormatter(module="cli", command="search")
    formatter.error("Search failed", "Invalid query format", exit_code=2)
"""

import sys
from typing import Any


class ErrorFormatter:
    """Consistent error message formatter for Research Assistant modules."""

    def __init__(self, module: str = "unknown", command: str | None = None):
        """Initialize error formatter with module and command context."""
        self.module = module
        self.command = command

    def format_error(
        self, error_type: str, context: str = "", suggestion: str = "", technical_details: str = ""
    ) -> str:
        """Format error message with consistent structure.

        Args:
            error_type: Brief error description (e.g., "Knowledge base not found")
            context: What the user was trying to do
            suggestion: Actionable next step
            technical_details: Optional technical information

        Returns:
            Formatted error message string
        """
        lines = []

        # Error header with module context
        if self.command:
            lines.append(f"❌ {self.module}.{self.command}: {error_type}")
        else:
            lines.append(f"❌ {self.module}: {error_type}")

        # Context if provided
        if context:
            lines.append(f"   Context: {context}")

        # Suggestion with clear action
        if suggestion:
            lines.append(f"   Solution: {suggestion}")

        # Technical details for debugging
        if technical_details:
            lines.append(f"   Details: {technical_details}")

        return "\n".join(lines)

    def error(
        self,
        error_type: str,
        context: str = "",
        suggestion: str = "",
        technical_details: str = "",
        exit_code: int = 1,
    ) -> None:
        """Print formatted error and exit.

        Args:
            error_type: Brief error description
            context: What the user was trying to do
            suggestion: Actionable next step
            technical_details: Optional technical information
            exit_code: Exit code (default: 1)
        """
        message = self.format_error(error_type, context, suggestion, technical_details)
        print(message, file=sys.stderr)
        sys.exit(exit_code)


def format_error(
    error_type: str,
    context: str = "",
    suggestion: str = "",
    technical_details: str = "",
    module: str = "system",
) -> str:
    """Quick error formatting function.

    Args:
        error_type: Brief error description
        context: What the user was trying to do
        suggestion: Actionable next step
        technical_details: Optional technical information
        module: Module name for context

    Returns:
        Formatted error message string
    """
    formatter = ErrorFormatter(module=module)
    return formatter.format_error(error_type, context, suggestion, technical_details)


def safe_exit(
    error_type: str,
    suggestion: str = "",
    context: str = "",
    technical_details: str = "",
    module: str = "system",
    exit_code: int = 1,
) -> None:
    """Print formatted error and exit safely.

    Args:
        error_type: Brief error description
        suggestion: Actionable next step
        context: What the user was trying to do
        technical_details: Optional technical information
        module: Module name for context
        exit_code: Exit code (default: 1)
    """
    formatter = ErrorFormatter(module=module)
    formatter.error(error_type, context, suggestion, technical_details, exit_code)


# Common error patterns with pre-configured messages
COMMON_ERRORS = {
    "kb_not_found": {
        "error_type": "Knowledge base not found",
        "context": "Attempting to access knowledge base files",
        "suggestion": "Run 'python src/build_kb.py --demo' to create a demo KB",
        "technical_details": "Missing kb_data/ directory or required files",
    },
    "zotero_connection": {
        "error_type": "Cannot connect to Zotero API",
        "context": "Attempting to access local Zotero library",
        "suggestion": "Start Zotero and enable API in Preferences → Advanced → Config Editor",
        "technical_details": "Zotero local API not responding on default port",
    },
    "faiss_import": {
        "error_type": "FAISS library not available",
        "context": "Attempting to load search index",
        "suggestion": "Install with: pip install faiss-cpu",
        "technical_details": "faiss-cpu package required for vector similarity search",
    },
    "paper_not_found": {
        "error_type": "Paper not found in knowledge base",
        "context": "Attempting to retrieve specific paper",
        "suggestion": "Use 'python src/cli.py info' to see available papers",
        "technical_details": "Paper ID not found in metadata index",
    },
    "invalid_paper_id": {
        "error_type": "Invalid paper ID format",
        "context": "Paper ID validation failed",
        "suggestion": "Use 4-digit format (e.g., 0001, 0042, 1234)",
        "technical_details": "Paper IDs must be 4-digit integers with zero-padding",
    },
}


def get_common_error(error_key: str, module: str = "system", **kwargs: Any) -> dict[str, Any]:
    """Get pre-configured common error with module context.

    Args:
        error_key: Key from COMMON_ERRORS dictionary
        module: Module name for context
        **kwargs: Override any error fields

    Returns:
        Error configuration dictionary
    """
    if error_key not in COMMON_ERRORS:
        raise ValueError(f"Unknown error key: {error_key}")

    error_config = COMMON_ERRORS[error_key].copy()
    error_config.update(kwargs)
    error_config["module"] = module

    return error_config


def exit_with_common_error(error_key: str, module: str = "system", exit_code: int = 1, **kwargs: Any) -> None:
    """Exit with pre-configured common error message.

    Args:
        error_key: Key from COMMON_ERRORS dictionary
        module: Module name for context
        exit_code: Exit code (default: 1)
        **kwargs: Override any error fields
    """
    error_config = get_common_error(error_key, module, **kwargs)
    formatter = ErrorFormatter(module=module)
    formatter.error(
        error_config["error_type"],
        error_config["context"],
        error_config["suggestion"],
        error_config["technical_details"],
        exit_code,
    )
