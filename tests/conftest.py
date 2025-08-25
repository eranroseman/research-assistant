"""Test configuration and fixtures for research assistant tests."""

import json
import os
import shutil
import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress the torch docstring warning that happens with multiple imports
warnings.filterwarnings("ignore", message=".*_has_torch_function.*already has a docstring")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*_has_torch_function.*")

# Fix torch import issue by handling it properly
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Disable tokenizers parallelism warnings

# Mock torch early to prevent multiple registration issues
if "torch" not in sys.modules:
    # Create a comprehensive mock for torch
    mock_torch = Mock()
    mock_torch.cuda = Mock()
    mock_torch.cuda.is_available = Mock(return_value=False)
    mock_torch.cuda.get_device_properties = Mock(return_value=Mock(total_memory=8 * 1024**3))
    mock_torch.set_num_threads = Mock()
    mock_torch.__version__ = "2.0.0"
    sys.modules["torch"] = mock_torch
else:
    # If torch is already imported, configure it for testing
    try:
        import torch

        torch.set_num_threads(1)  # Reduce thread usage for tests
    except (ImportError, AttributeError):
        pass


# ==================== File System Fixtures ====================


@pytest.fixture
def temp_kb_dir():
    """Create a temporary knowledge base directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_kb_")
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def isolated_test_dir(tmp_path):
    """Create an isolated test directory with proper cleanup."""
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()

    # Save current directory
    original_dir = Path.cwd()

    # Change to test directory
    import os

    os.chdir(test_dir)

    yield test_dir

    # Restore original directory
    os.chdir(original_dir)

    # Cleanup is automatic with tmp_path


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically clean up test files after each test."""
    yield

    # Clean up common test artifacts
    patterns = [
        "test_*.json",
        "temp_*.csv",
        "*.test.md",
        "test_export_*",
    ]

    for pattern in patterns:
        for file in Path(".").glob(pattern):
            try:
                if file.is_file():
                    file.unlink()
            except Exception:
                pass  # Ignore cleanup errors


# ==================== Click Testing Fixtures ====================


@pytest.fixture
def runner():
    """Provide a Click test runner for CLI testing."""
    return CliRunner()


@pytest.fixture
def isolated_runner():
    """Provide a Click test runner with isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


@pytest.fixture
def runner_with_env(runner):
    """Provide a Click test runner with custom environment variables."""

    def _runner_with_env(**env_vars):
        return CliRunner(env=env_vars)

    return _runner_with_env


# ==================== Mock API Fixtures ====================


@pytest.fixture
def mock_semantic_scholar():
    """Mock Semantic Scholar API responses for reliable testing."""
    with patch("requests.get") as mock_get:

        def side_effect(url, *args, **kwargs):
            response = Mock()
            response.status_code = 200

            # Default successful response
            if "paper" in url and "search" not in url:
                # Single paper endpoint
                response.json.return_value = {
                    "paperId": "test123",
                    "title": "Test Paper",
                    "citationCount": 50,
                    "venue": {"name": "Nature Medicine"},
                    "authors": [{"authorId": "1", "name": "Test Author", "hIndex": 20}],
                    "year": 2023,
                    "abstract": "Test abstract",
                    "externalIds": {"DOI": "10.1234/test"},
                    "publicationTypes": ["JournalArticle"],
                    "fieldsOfStudy": ["Medicine"],
                    "references": [],
                    "citations": [],
                }
            elif "search" in url:
                # Search endpoint
                response.json.return_value = {
                    "data": [
                        {
                            "paperId": f"search_{i}",
                            "title": f"Search Result {i}",
                            "citationCount": 10 * i,
                            "venue": {"name": "Test Journal"},
                            "authors": [{"name": f"Author {i}", "hIndex": 10}],
                        }
                        for i in range(1, 4)
                    ],
                    "total": 3,
                }
            elif "citations" in url:
                # Citations endpoint
                response.json.return_value = {
                    "data": [
                        {"paperId": f"citation_{i}", "title": f"Citation {i}", "citationCount": 5 * i}
                        for i in range(1, 3)
                    ]
                }
            else:
                # Generic response
                response.json.return_value = {"data": [], "message": "OK"}

            return response

        mock_get.side_effect = side_effect
        yield mock_get


@pytest.fixture
def mock_semantic_scholar_error():
    """Mock Semantic Scholar API error responses for error testing."""
    with patch("requests.get") as mock_get:

        def side_effect(url, *args, **kwargs):
            response = Mock()

            # Simulate different error conditions based on URL
            if "rate_limit" in url:
                response.status_code = 429
                response.json.return_value = {"error": "Rate limit exceeded"}
            elif "timeout" in url:
                response.status_code = 504
                response.json.return_value = {"error": "Gateway timeout"}
            elif "not_found" in url:
                response.status_code = 404
                response.json.return_value = {"error": "Paper not found"}
            else:
                response.status_code = 500
                response.json.return_value = {"error": "Internal server error"}

            return response

        mock_get.side_effect = side_effect
        yield mock_get


@pytest.fixture
def mock_zotero():
    """Mock Zotero API responses for reliable testing."""
    with patch("pyzotero.zotero.Zotero") as mock_zotero_class:
        mock_instance = Mock()
        mock_zotero_class.return_value = mock_instance

        # Mock Zotero methods
        mock_instance.items.return_value = [
            {
                "key": "TEST001",
                "data": {
                    "title": "Test Paper from Zotero",
                    "creators": [
                        {"firstName": "John", "lastName": "Doe"},
                        {"firstName": "Jane", "lastName": "Smith"},
                    ],
                    "date": "2023",
                    "DOI": "10.1234/zotero.test",
                    "abstractNote": "Abstract from Zotero",
                    "publicationTitle": "Journal of Testing",
                },
            }
        ]

        mock_instance.attachment_items.return_value = [{"key": "ATT001", "data": {"parentItem": "TEST001"}}]

        mock_instance.file.return_value = b"PDF content here"

        yield mock_instance


@pytest.fixture
def mock_external_apis(mock_semantic_scholar, mock_zotero):
    """Convenience fixture to mock all external APIs at once."""
    return {"semantic_scholar": mock_semantic_scholar, "zotero": mock_zotero}


# ==================== Test Data Fixtures ====================


@pytest.fixture
def sample_paper():
    """Provide a sample paper dictionary for testing."""
    return {
        "id": "0001",
        "title": "Sample Paper for Testing",
        "authors": ["Smith J", "Doe J"],
        "year": 2023,
        "journal": "Test Journal",
        "doi": "10.1234/test.0001",
        "abstract": "This is a test abstract for unit testing purposes.",
        "study_type": "rct",
        "sample_size": 500,
        "has_full_text": True,
        "quality_score": 75,
        "quality_explanation": "High quality RCT with good methodology",
    }


@pytest.fixture
def sample_kb_metadata(temp_kb_dir):
    """Create a sample knowledge base metadata file."""
    metadata = {
        "version": "4.0",
        "total_papers": 5,
        "last_updated": "2025-01-20T10:00:00Z",
        "embedding_model": "sentence-transformers/multi-qa-mpnet-base-dot-v1",
        "papers": [
            {
                "id": f"{i:04d}",
                "title": f"Test Paper {i}",
                "authors": [f"Author {i}"],
                "year": 2020 + i,
                "quality_score": 60 + i * 5,
                "doi": f"10.1234/test.{i:04d}",
            }
            for i in range(1, 6)
        ],
    }

    metadata_file = temp_kb_dir / "metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata_file


# ==================== Enhanced API Mock Fixtures ====================


@pytest.fixture
def mock_build_kb():
    """Mock the entire KB building process for faster testing."""
    with patch("src.build_kb.main") as mock_main:
        mock_main.return_value = 0  # Success

        # Also mock the actual building functions
        with patch("src.build_kb.build_knowledge_base") as mock_build:
            mock_build.return_value = (5, 0)  # 5 papers added, 0 failed
            yield mock_main


@pytest.fixture
def mock_embeddings():
    """Mock embedding generation for faster testing."""
    with patch("sentence_transformers.SentenceTransformer") as mock_model:
        import numpy as np

        # Create mock model instance
        mock_instance = Mock()
        mock_instance.encode.return_value = np.random.rand(10, 768).astype(np.float32)
        mock_instance.get_sentence_embedding_dimension.return_value = 768
        mock_model.return_value = mock_instance

        yield mock_instance


@pytest.fixture(autouse=True)
def patch_cli_imports():
    """Patch problematic imports in CLI module."""
    # Create a mock torch module to avoid import conflicts
    mock_torch = Mock()
    mock_torch.cuda = Mock()
    mock_torch.cuda.is_available = Mock(return_value=False)
    mock_torch.cuda.get_device_properties = Mock(return_value=Mock(total_memory=8 * 1024**3))
    mock_torch.set_num_threads = Mock()

    # Create mock transformers with all required submodules
    mock_transformers = Mock()
    mock_transformers.utils = Mock()
    mock_transformers.utils.PushToHubMixin = Mock
    mock_transformers.configuration_utils = Mock()

    # Create mock sentence_transformers
    mock_st = Mock()
    mock_st.SentenceTransformer = Mock
    mock_st.backend = Mock()
    mock_st.backend.load = Mock()

    # Patch the transformers import issue
    with patch.dict(
        "sys.modules",
        {
            "transformers": mock_transformers,
            "transformers.utils": mock_transformers.utils,
            "transformers.configuration_utils": mock_transformers.configuration_utils,
            "sentence_transformers": mock_st,
            "sentence_transformers.backend": mock_st.backend,
            "sentence_transformers.backend.load": mock_st.backend.load,
            # Mock torch if not already imported
            **({"torch": mock_torch} if "torch" not in sys.modules else {}),
        },
    ):
        yield


@pytest.fixture
def mock_faiss_index():
    """Mock FAISS index for search testing."""
    with patch("faiss.IndexFlatIP") as mock_index_class:
        mock_index = Mock()
        mock_index.ntotal = 100
        mock_index.d = 768

        # Mock search results
        import numpy as np

        distances = np.array([[0.9, 0.8, 0.7]], dtype=np.float32)
        indices = np.array([[0, 1, 2]], dtype=np.int64)
        mock_index.search.return_value = (distances, indices)

        mock_index_class.return_value = mock_index
        yield mock_index


@pytest.fixture
def mock_kb_with_papers(temp_kb_dir):
    """Create a complete mock KB with papers, index, and metadata."""
    import numpy as np

    # Create KB directory structure
    kb_dir = temp_kb_dir / "kb_data"
    kb_dir.mkdir()
    papers_dir = kb_dir / "papers"
    papers_dir.mkdir()

    # Create sample papers
    papers = []
    for i in range(1, 6):
        paper_id = f"{i:04d}"
        paper_content = f"""# Paper {paper_id}

## Title
Test Paper {i}

## Authors
Author {i}, Co-Author {i}

## Abstract
This is the abstract for test paper {i}.

## Methods
Test methodology description.

## Results
Test results description.
"""
        paper_file = papers_dir / f"paper_{paper_id}.md"
        paper_file.write_text(paper_content)

        papers.append(
            {
                "id": paper_id,
                "title": f"Test Paper {i}",
                "authors": [f"Author {i}", f"Co-Author {i}"],
                "year": 2020 + i,
                "quality_score": 60 + i * 5,
                "doi": f"10.1234/test.{paper_id}",
            }
        )

    # Create metadata
    metadata = {
        "version": "4.6",
        "total_papers": len(papers),
        "papers": papers,
        "last_updated": "2025-01-20T10:00:00Z",
        "embedding_model": "sentence-transformers/multi-qa-mpnet-base-dot-v1",
    }

    metadata_file = kb_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    # Create mock embeddings
    embeddings = np.random.rand(len(papers), 768).astype(np.float32)
    np.save(kb_dir / ".embedding_data.npy", embeddings)

    # Create sections index
    sections_index = {
        paper_id: {
            "abstract": f"Abstract for paper {paper_id}",
            "methods": f"Methods for paper {paper_id}",
            "results": f"Results for paper {paper_id}",
        }
        for paper_id in [p["id"] for p in papers]
    }

    sections_file = kb_dir / "sections_index.json"
    sections_file.write_text(json.dumps(sections_index, indent=2))

    return kb_dir


@pytest.fixture
def mock_cli_with_kb(mock_kb_with_papers):
    """Mock CLI with a complete KB for integration testing."""
    from src.cli import cli
    from click.testing import CliRunner

    runner = CliRunner()

    # Set KB path environment variable
    import os

    os.environ["KB_PATH"] = str(mock_kb_with_papers)

    yield runner, cli

    # Cleanup
    if "KB_PATH" in os.environ:
        del os.environ["KB_PATH"]
