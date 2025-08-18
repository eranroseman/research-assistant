"""Test configuration and fixtures for research assistant tests."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_kb_dir():
    """Create a temporary knowledge base directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_kb_")
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_metadata():
    """Provide sample metadata for testing."""
    return {
        "papers": [
            {
                "id": "0001",
                "doi": "10.1234/test1",
                "title": "Digital Health Interventions for Diabetes Management",
                "authors": ["Smith J", "Doe A"],
                "year": 2023,
                "journal": "Test Journal",
                "abstract": "This study examines digital health interventions for diabetes.",
                "study_type": "rct",
                "sample_size": 487,
                "has_full_text": True,
                "filename": "paper_0001.md",
                "embedding_index": 0,
            },
            {
                "id": "0002",
                "doi": "10.1234/test2",
                "title": "Telemedicine in Rural Healthcare",
                "authors": ["Johnson M"],
                "year": 2022,
                "journal": "Rural Health",
                "abstract": "Exploring telemedicine adoption in rural settings.",
                "study_type": "systematic_review",
                "has_full_text": False,
                "filename": "paper_0002.md",
                "embedding_index": 1,
            },
        ],
        "total_papers": 2,
        "last_updated": "2025-01-01T00:00:00Z",
        "embedding_model": "allenai-specter",
        "embedding_dimensions": 768,
    }


@pytest.fixture
def corrupt_cache_file(temp_kb_dir):
    """Create a corrupted cache file for testing error handling."""
    cache_path = temp_kb_dir / ".pdf_text_cache.json"
    with open(cache_path, "w") as f:
        f.write("{corrupted json data{{}}")
    return cache_path


@pytest.fixture
def valid_cache_file(temp_kb_dir):
    """Create a valid cache file for testing."""
    cache_path = temp_kb_dir / ".pdf_text_cache.json"
    cache_data = {
        "TEST_KEY": {
            "text": "Sample PDF text content",
            "file_size": 1024,
            "file_mtime": 1234567890.0,
            "cached_at": "2025-01-01T00:00:00Z",
        }
    }
    with open(cache_path, "w") as f:
        json.dump(cache_data, f)
    return cache_path
