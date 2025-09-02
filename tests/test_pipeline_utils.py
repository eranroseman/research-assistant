#!/usr/bin/env python3
"""Test pipeline utilities to ensure they work correctly."""

import tempfile
import time
from pathlib import Path
import sys
import os

# Add src to path (we're now in tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline_utils import (
    clean_doi,
    batch_iterator,
    load_checkpoint,
    save_checkpoint_atomic,
    rate_limit_wait,
    get_shard_path,
    format_time_estimate,
    create_session_with_retry,
)


def test_clean_doi():
    """Test DOI cleaning function."""
    print("Testing clean_doi...")

    # Test cases
    tests = [
        ("10.1234/test", "10.1234/test"),  # Already clean
        ("https://doi.org/10.1234/test", "10.1234/test"),  # URL prefix
        ("http://dx.doi.org/10.1234/test", "10.1234/test"),  # dx.doi.org
        ("10.1234/test.", "10.1234/test"),  # Trailing period
        ("10.1234/test)", "10.1234/test"),  # Trailing paren
        ("10.13039/funder", None),  # Funding DOI
        ("not-a-doi", None),  # Invalid
        (None, None),  # None input
        ("", None),  # Empty string
        ("10.1234/test.pdf", "10.1234/test"),  # PDF suffix
    ]

    for input_doi, expected in tests:
        result = clean_doi(input_doi)
        assert result == expected, f"Failed: {input_doi} -> {result} (expected {expected})"

    print("  ✓ All DOI cleaning tests passed")


def test_batch_iterator():
    """Test batch iteration."""
    print("Testing batch_iterator...")

    items = list(range(10))

    # Test different batch sizes
    batches = list(batch_iterator(items, 3))
    assert batches == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]

    batches = list(batch_iterator(items, 5))
    assert batches == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

    batches = list(batch_iterator(items, 20))
    assert batches == [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]

    # Empty list
    batches = list(batch_iterator([], 5))
    assert batches == []

    print("  ✓ Batch iterator tests passed")


def test_checkpoint_operations():
    """Test checkpoint loading and saving."""
    print("Testing checkpoint operations...")

    with tempfile.TemporaryDirectory() as tmpdir:
        checkpoint_file = Path(tmpdir) / "test_checkpoint.json"

        # Test loading non-existent file
        data = load_checkpoint(checkpoint_file)
        assert data == {}

        # Test saving and loading
        test_data = {"processed_papers": ["paper1", "paper2"], "stats": {"total": 100, "processed": 50}}

        success = save_checkpoint_atomic(checkpoint_file, test_data)
        assert success
        assert checkpoint_file.exists()

        # Load and verify
        loaded_data = load_checkpoint(checkpoint_file)
        assert loaded_data == test_data

        # Test atomic write (no .tmp file left)
        tmp_file = checkpoint_file.with_suffix(".tmp")
        assert not tmp_file.exists()

        # Test subdirectory creation
        nested_checkpoint = Path(tmpdir) / "subdir" / "nested" / "checkpoint.json"
        success = save_checkpoint_atomic(nested_checkpoint, {"test": "data"})
        assert success
        assert nested_checkpoint.exists()

    print("  ✓ Checkpoint operations tests passed")


def test_rate_limiting():
    """Test rate limiting function."""
    print("Testing rate_limit_wait...")

    # Test no wait needed
    last_time = time.time() - 10  # 10 seconds ago
    new_time = rate_limit_wait(last_time, 0.1)
    assert new_time >= last_time

    # Test wait needed
    last_time = time.time()
    start = time.time()
    new_time = rate_limit_wait(last_time, 0.1)
    elapsed = time.time() - start
    assert elapsed >= 0.09  # Should wait ~0.1 seconds

    print("  ✓ Rate limiting tests passed")


def test_shard_path():
    """Test sharding for filesystem organization."""
    print("Testing get_shard_path...")

    base = Path("/tmp/cache")

    # Normal cases
    assert get_shard_path(base, "PMC123456") == base / "PM"
    assert get_shard_path(base, "DOI_10.1234") == base / "DO"
    assert get_shard_path(base, "abc") == base / "AB"

    # Short identifier
    assert get_shard_path(base, "X") == base / "XX"
    assert get_shard_path(base, "") == base / "XX"

    # Custom shard length
    assert get_shard_path(base, "PMC123456", shard_length=3) == base / "PMC"

    print("  ✓ Shard path tests passed")


def test_format_time():
    """Test time formatting."""
    print("Testing format_time_estimate...")

    assert format_time_estimate(30) == "30 seconds"
    assert format_time_estimate(90) == "1.5 minutes"
    assert format_time_estimate(3600) == "1.0 hours"
    assert format_time_estimate(7200) == "2.0 hours"

    print("  ✓ Time formatting tests passed")


def test_session_creation():
    """Test HTTP session creation."""
    print("Testing create_session_with_retry...")

    # Basic session
    session = create_session_with_retry()
    assert session is not None
    assert len(session.adapters) > 0

    # With email
    session = create_session_with_retry(email="test@example.com")
    assert "User-Agent" in session.headers
    assert "test@example.com" in session.headers["User-Agent"]

    # Custom retry settings
    session = create_session_with_retry(max_retries=10, backoff_factor=2.0, status_forcelist=[500, 502])
    assert session is not None

    print("  ✓ Session creation tests passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING PIPELINE UTILITIES")
    print("=" * 60)

    try:
        test_clean_doi()
        test_batch_iterator()
        test_checkpoint_operations()
        test_rate_limiting()
        test_shard_path()
        test_format_time()
        test_session_creation()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
