"""Shared test utilities for research assistant tests."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np


def create_mock_cli(
    papers_count: int = 10,
    with_embeddings: bool = False,
    with_index: bool = False,
    kb_path: Path | None = None,
) -> MagicMock:
    """Create a standardized mock CLI instance for testing.

    Args:
        papers_count: Number of mock papers to include
        with_embeddings: Whether to include mock embeddings
        with_index: Whether to include mock FAISS index
        kb_path: Custom knowledge base path

    Returns:
        Mock ResearchCLI instance with test data
    """
    from src.cli import ResearchCLI

    # Create mock CLI without calling __init__
    with MagicMock() as mock_init:
        mock_init.return_value = None
        ResearchCLI.__init__ = mock_init
        cli = ResearchCLI.__new__(ResearchCLI)

    # Set up basic attributes
    cli.knowledge_base_path = kb_path or Path(".")
    cli.verbose = False

    # Generate mock papers
    papers = []
    for i in range(1, papers_count + 1):
        paper_id = f"{i:04d}"
        papers.append(
            {
                "id": paper_id,
                "doi": f"10.1234/test{i}",
                "title": f"Test Paper {i}: Research on Topic {i % 3}",
                "authors": [f"Author{i}", f"Coauthor{i}"],
                "year": 2020 + (i % 5),
                "journal": f"Journal {i % 4}",
                "abstract": f"This is the abstract for paper {i} about topic {i % 3}.",
                "study_type": ["rct", "systematic_review", "cohort", "cross_sectional"][i % 4],
                "sample_size": 100 * i if i % 2 == 0 else None,
                "has_full_text": i % 3 != 0,
                "filename": f"paper_{paper_id}.md",
                "embedding_index": i - 1,
                "quality_score": 50 + (i % 50),
            }
        )

    cli.metadata = {
        "papers": papers,
        "total_papers": len(papers),
        "last_updated": "2025-01-20T00:00:00Z",
        "embedding_model": "allenai-specter",
        "embedding_dimensions": 768,
    }

    # Add embeddings if requested
    if with_embeddings:
        cli.embeddings = np.random.randn(papers_count, 768).astype(np.float32)
        cli.embedding_data = cli.embeddings

    # Add FAISS index if requested
    if with_index:
        import faiss

        cli.index = faiss.IndexFlatL2(768)
        if with_embeddings:
            cli.index.add(cli.embeddings)

    # Add mock methods that might be needed
    cli.search = MagicMock(return_value=[])
    cli.smart_search = MagicMock(return_value=[])
    cli.get_paper = MagicMock(return_value=None)
    cli.author_search = MagicMock(return_value=[])

    return cli


def create_test_kb_structure(
    base_path: Path,
    include_papers: bool = True,
    include_index: bool = True,
    include_cache: bool = False,
) -> dict[str, Path]:
    """Create a complete test knowledge base directory structure.

    Args:
        base_path: Base directory for the test KB
        include_papers: Whether to create paper markdown files
        include_index: Whether to create index files
        include_cache: Whether to create cache files

    Returns:
        Dictionary of created paths
    """
    paths = {
        "base": base_path,
        "papers": base_path / "papers",
        "exports": base_path / "exports",
        "reviews": base_path / "reviews",
        "system": base_path / "system",
    }

    # Create directories
    paths["papers"].mkdir(parents=True, exist_ok=True)
    paths["exports"].mkdir(parents=True, exist_ok=True)
    paths["reviews"].mkdir(parents=True, exist_ok=True)
    paths["system"].mkdir(parents=True, exist_ok=True)

    # Create metadata file
    metadata = {
        "papers": [
            {
                "id": "0001",
                "title": "Test Paper 1",
                "authors": ["Smith J"],
                "year": 2023,
                "abstract": "Test abstract 1",
                "study_type": "rct",
                "embedding_index": 0,
            },
            {
                "id": "0002",
                "title": "Test Paper 2",
                "authors": ["Jones A"],
                "year": 2024,
                "abstract": "Test abstract 2",
                "study_type": "systematic_review",
                "embedding_index": 1,
            },
        ],
        "total_papers": 2,
        "last_updated": "2025-01-20T00:00:00Z",
    }

    metadata_path = base_path / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    paths["metadata"] = metadata_path

    # Create paper files if requested
    if include_papers:
        for paper in metadata["papers"]:
            paper_path = paths["papers"] / f"paper_{paper['id']}.md"
            paper_path.write_text(
                f"# {paper['title']}\n\n"
                f"**Authors:** {', '.join(paper['authors'])}\n"
                f"**Year:** {paper['year']}\n\n"
                f"## Abstract\n{paper['abstract']}\n"
            )

    # Create index files if requested
    if include_index:
        # Create dummy FAISS index
        import faiss

        index = faiss.IndexFlatL2(768)
        embeddings = np.random.randn(2, 768).astype(np.float32)
        index.add(embeddings)
        faiss.write_index(index, str(base_path / "index.faiss"))
        paths["index"] = base_path / "index.faiss"

        # Create sections index
        sections_index = {
            "0001": {"abstract": 0, "introduction": 100},
            "0002": {"abstract": 200, "methods": 300},
        }
        with open(base_path / "sections_index.json", "w") as f:
            json.dump(sections_index, f)
        paths["sections_index"] = base_path / "sections_index.json"

    # Create cache files if requested
    if include_cache:
        cache_data = {
            "test_key": {
                "text": "Cached text",
                "file_size": 1024,
                "file_mtime": 1234567890.0,
                "cached_at": "2025-01-20T00:00:00Z",
            }
        }
        with open(base_path / ".pdf_text_cache.json", "w") as f:
            json.dump(cache_data, f)
        paths["pdf_cache"] = base_path / ".pdf_text_cache.json"

    return paths


def assert_batch_command_output(
    result: list[dict[str, Any]],
    expected_commands: list[str],
    expected_results_count: int | None = None,
) -> None:
    """Assert batch command execution results match expectations.

    Args:
        result: The batch execution result list (actual CLI format)
        expected_commands: List of expected command types executed
        expected_results_count: Expected number of results (if applicable)
    """
    # Result should be a list of command results
    assert isinstance(result, list), f"Expected list, got {type(result)}"

    # Check results count if specified
    if expected_results_count is not None:
        assert len(result) == expected_results_count

    # Check commands executed match expected - check both 'type' and 'command.cmd'
    executed_cmds = []
    for r in result:
        if r.get("success"):
            # Check both type field and command.cmd field
            if "type" in r:
                executed_cmds.append(r["type"])
            elif "command" in r and "cmd" in r["command"]:
                executed_cmds.append(r["command"]["cmd"])

    for expected_cmd in expected_commands:
        assert (
            expected_cmd in executed_cmds
        ), f"Expected command '{expected_cmd}' not found. Got: {executed_cmds}"


def create_mock_paper(
    paper_id: str = "0001",
    title: str = "Test Paper",
    year: int = 2023,
    study_type: str = "rct",
    quality_score: int = 75,
    **kwargs,
) -> dict[str, Any]:
    """Create a mock paper dictionary with sensible defaults.

    Args:
        paper_id: 4-digit paper ID
        title: Paper title
        year: Publication year
        study_type: Type of study
        quality_score: Quality score (0-100)
        **kwargs: Additional paper fields to override

    Returns:
        Complete paper dictionary
    """
    paper = {
        "id": paper_id,
        "doi": f"10.1234/{paper_id}",
        "title": title,
        "authors": kwargs.get("authors", ["Test Author"]),
        "year": year,
        "journal": kwargs.get("journal", "Test Journal"),
        "abstract": kwargs.get("abstract", f"Abstract for {title}"),
        "study_type": study_type,
        "sample_size": kwargs.get("sample_size", 100),
        "has_full_text": kwargs.get("has_full_text", True),
        "filename": f"paper_{paper_id}.md",
        "embedding_index": int(paper_id) - 1,
        "quality_score": quality_score,
    }

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in paper:
            paper[key] = value

    return paper


def run_cli_command(command_args: list[str], check: bool = True) -> dict[str, Any]:
    """Run a CLI command and return structured output.

    Args:
        command_args: List of command arguments (excluding 'python src/cli.py')
        check: Whether to check for non-zero return code

    Returns:
        Dictionary with returncode, stdout, stderr
    """
    import subprocess

    full_command = ["python", "src/cli.py", *command_args]
    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        check=check,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0,
    }


def mock_embedding_search(
    query: str,
    papers: list[dict],
    k: int = 10,
    similarity_threshold: float = 0.5,
) -> list[tuple]:
    """Mock embedding-based search results.

    Args:
        query: Search query (unused in mock)
        papers: List of paper dictionaries
        k: Number of results to return
        similarity_threshold: Minimum similarity score

    Returns:
        List of (paper_dict, similarity_score) tuples
    """
    # Simple mock: return papers with decreasing similarity scores
    results = []
    for i, paper in enumerate(papers[:k]):
        similarity = 0.95 - (i * 0.05)
        if similarity >= similarity_threshold:
            results.append((paper, similarity))

    return results
