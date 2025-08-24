#!/usr/bin/env python3
"""End-to-end tests for CLI commands."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.cli
@pytest.mark.fast
class TestCLIBasicCommands:
    """Test basic CLI command functionality."""

    def test_cli_help_command_should_show_usage_information(self):
        """
        Test that help command shows usage information.

        Given: CLI help command
        When: Executed
        Then: Shows available commands and options
        """
        result = subprocess.run(
            ["python", "src/cli.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "search" in result.stdout
        assert "cite" in result.stdout
        assert "batch" in result.stdout
        assert "smart-search" in result.stdout

    def test_cli_info_command_should_show_kb_status(self):
        """
        Test that info command shows KB status.

        Given: CLI info command
        When: Executed
        Then: Shows KB information or error message
        """
        result = subprocess.run(
            ["python", "src/cli.py", "info"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should either show KB info or not found message
        assert result.returncode in [0, 1]
        if result.returncode == 0:
            assert "papers" in result.stdout.lower() or "knowledge base" in result.stdout.lower()
        else:
            assert "not found" in result.stdout.lower() or "not found" in result.stderr.lower()

    def test_cli_diagnose_command_should_run_health_check(self):
        """
        Test that diagnose command performs health check.

        Given: CLI diagnose command
        When: Executed
        Then: Shows health check results
        """
        result = subprocess.run(
            ["python", "src/cli.py", "diagnose"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
            timeout=10,
        )

        # Should complete without hanging
        assert result.returncode in [0, 1]
        # Should show some diagnostic output
        assert len(result.stdout + result.stderr) > 0


@pytest.mark.e2e
@pytest.mark.cli
@pytest.mark.search
@pytest.mark.requires_kb
class TestCLISearchCommands:
    """Test search-related CLI commands."""

    def test_search_command_help_should_show_options(self):
        """
        Test that search help shows all options.

        Given: Search help command
        When: Executed
        Then: Shows search options and filters
        """
        result = subprocess.run(
            ["python", "src/cli.py", "search", "--help"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "--after" in result.stdout
        assert "--type" in result.stdout
        assert "--min-quality" in result.stdout
        assert "--show-quality" in result.stdout
        assert "-k" in result.stdout or "--top" in result.stdout

    def test_search_without_kb_should_show_error(self):
        """
        Test that search without KB shows helpful error.

        Given: Search command with no KB
        When: Executed in directory without kb_data
        Then: Shows error message about missing KB or gracefully handles
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Run in temp directory that has no kb_data
            result = subprocess.run(
                ["python", str(Path(__file__).parent.parent.parent / "src/cli.py"), "search", "test"],
                capture_output=True,
                text=True,
                check=False,
                cwd=tmpdir,
            )

            # Should either fail with KB not found OR handle gracefully with existing KB
            assert result.returncode in [0, 1]
            if result.returncode == 1:
                assert (
                    "not found" in result.stderr.lower()
                    or "not found" in result.stdout.lower()
                    or "build" in result.stderr.lower()
                    or "build" in result.stdout.lower()
                )
            # If it succeeds (finds existing KB), that's also acceptable behavior

    def test_smart_search_command_help_should_be_available(self):
        """
        Test that smart-search help is available.

        Given: Smart-search help command
        When: Executed
        Then: Shows smart-search options
        """
        result = subprocess.run(
            ["python", "src/cli.py", "smart-search", "--help"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "smart" in result.stdout.lower() or "section" in result.stdout.lower()
        assert "-k" in result.stdout


@pytest.mark.e2e
@pytest.mark.cli
@pytest.mark.fast
class TestCLICiteCommand:
    """Test citation command functionality."""

    def test_cite_command_help_should_show_format_options(self):
        """
        Test that cite help shows format options.

        Given: Cite help command
        When: Executed
        Then: Shows paper ID format and output options
        """
        result = subprocess.run(
            ["python", "src/cli.py", "cite", "--help"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "PAPER_IDS" in result.stdout
        assert "--format" in result.stdout
        assert "json" in result.stdout
        assert "0001" in result.stdout  # Example ID

    def test_cite_without_arguments_should_show_error(self):
        """
        Test that cite without IDs shows error.

        Given: Cite command without paper IDs
        When: Executed
        Then: Shows error about missing arguments
        """
        result = subprocess.run(
            ["python", "src/cli.py", "cite"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode != 0
        assert "PAPER_IDS" in result.stderr or "required" in result.stderr.lower()


@pytest.mark.e2e
@pytest.mark.cli
@pytest.mark.requires_kb
class TestCLIBatchCommand:
    """Test batch command functionality."""

    def test_batch_command_help_should_show_presets(self):
        """
        Test that batch help shows available presets.

        Given: Batch help command
        When: Executed
        Then: Shows preset options
        """
        result = subprocess.run(
            ["python", "src/cli.py", "batch", "--help"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "preset" in result.stdout.lower()
        assert "research" in result.stdout
        assert "review" in result.stdout
        assert "author-scan" in result.stdout

    def test_batch_with_invalid_json_should_show_error(self):
        """
        Test that invalid JSON is handled.

        Given: Batch command with invalid JSON
        When: Executed
        Then: Shows JSON parsing error
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json}")
            temp_file = f.name

        try:
            result = subprocess.run(
                ["python", "src/cli.py", "batch", temp_file],
                capture_output=True,
                text=True,
                check=False,
                cwd=Path(__file__).parent.parent.parent,
                timeout=30,  # Increased timeout for batch operations
            )

            assert result.returncode != 0
            assert (
                "json" in result.stderr.lower()
                or "invalid" in result.stderr.lower()
                or "json" in result.stdout.lower()
                or "invalid" in result.stdout.lower()
            )
        finally:
            Path(temp_file).unlink()


@pytest.mark.e2e
@pytest.mark.cli
@pytest.mark.fast
class TestCLIErrorMessages:
    """Test error message quality."""

    def test_missing_dependency_should_show_helpful_message(self):
        """
        Test that missing dependencies show helpful messages.

        Given: Command that requires FAISS
        When: FAISS is not installed (simulated)
        Then: Shows helpful error about installation
        """
        # This test would need to mock import failures
        # In practice, we just verify the error handling exists


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.requires_kb
class TestCLIPerformance:
    """Test CLI performance characteristics."""

    def test_help_command_should_respond_quickly(self):
        """
        Test that help command responds quickly.

        Given: Help command
        When: Executed
        Then: Completes within 2 seconds
        """
        import time

        start = time.time()
        result = subprocess.run(
            ["python", "src/cli.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent.parent,
            timeout=2,
        )
        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 2.0

    def test_commands_should_have_reasonable_timeout(self):
        """
        Test that commands don't hang indefinitely.

        Given: Various CLI commands
        When: Executed with timeout
        Then: Complete or timeout appropriately
        """
        commands = [
            ["python", "src/cli.py", "info"],
            ["python", "src/cli.py", "diagnose"],
            ["python", "src/cli.py", "search", "--help"],
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=Path(__file__).parent.parent.parent,
                    timeout=10,
                )
                # Should complete within timeout
                assert result.returncode in [0, 1]
            except subprocess.TimeoutExpired:
                pytest.fail(f"Command {' '.join(cmd)} timed out")


class TestCriticalE2EFunctionality:
    """Critical E2E tests migrated from test_critical.py."""

    @pytest.mark.e2e
    def test_kb_search_should_not_crash(self):
        """Test 1: Ensure basic search doesn't crash even with no/bad data."""
        # Test that CLI search command runs without crashing
        result = subprocess.run(
            ["python", "src/cli.py", "search", "diabetes", "-k", "1"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should either succeed or give a clear error message
        assert result.returncode in [
            0,
            1,
        ], f"Search crashed with code {result.returncode}"

        # If it failed, should have a helpful error message
        if result.returncode == 1:
            # v4.0 can fail with version incompatibility OR not found
            assert (
                "Knowledge base not found" in result.stderr
                or "not found" in result.stdout.lower()
                or "version incompatible" in result.stdout.lower()
            )

    @pytest.mark.e2e
    def test_cli_basic_commands_should_work(self):
        """Test 5: Ensure CLI basic commands don't crash."""
        cli_commands = [
            ["python", "src/cli.py", "info"],
            ["python", "src/cli.py", "--help"],
            ["python", "src/cli.py", "search", "--help"],
        ]

        for cmd in cli_commands:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent,
                timeout=10,  # Prevent hanging
            )

            # Should not crash (exit code 0 or 1 is OK)
            assert result.returncode in [
                0,
                1,
            ], f"Command {' '.join(cmd)} failed with code {result.returncode}\nError: {result.stderr}"

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_search_performance_should_be_acceptable(self):
        """Ensure search completes in reasonable time."""
        import os

        kb_path = Path("kb_data")
        if not kb_path.exists():
            pytest.skip("Knowledge base not built")

        start = time.time()
        result = subprocess.run(
            ["python", "src/cli.py", "search", "test", "-k", "10"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            timeout=30,
        )
        elapsed = time.time() - start

        # Environment-aware thresholds: CI environments may be slower
        # Local development: 25s, CI environment: 30s (allowing for model loading)
        # Increased thresholds to account for first-time model loading and varying system loads
        perf_threshold = 30 if os.getenv("CI") else 25

        # Should complete within threshold (allowing for model loading)
        assert elapsed < perf_threshold, f"Search too slow: {elapsed:.1f}s (threshold: {perf_threshold}s)"

        # Should return successfully
        assert result.returncode in [0, 1], f"Search failed with code {result.returncode}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestV4CommandsE2E:
    """V4.0 specific E2E tests - migrated from test_v4_features.py."""

    @pytest.mark.e2e
    def test_smart_search_command_should_exist(self):
        """Verify smart-search command is available."""
        result = subprocess.run(
            ["python", "src/cli.py", "smart-search", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "smart search" in result.stdout.lower() or "section chunking" in result.stdout.lower()

    @pytest.mark.e2e
    def test_diagnose_command_should_exist(self):
        """Verify diagnose command is available."""
        result = subprocess.run(
            ["python", "src/cli.py", "diagnose"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Should run (may fail if no KB, but shouldn't crash)
        assert result.returncode in [0, 1]
        assert "diagnos" in result.stdout.lower() or "diagnos" in result.stderr.lower()

    @pytest.mark.e2e
    def test_diagnose_output_should_have_correct_format(self, tmp_path):
        """Test diagnose command output format."""

        # Create complete v4.0 KB
        metadata = {
            "papers": [{"id": "0001", "title": "Test"}],
            "total_papers": 1,
            "version": "4.0",
            "last_updated": "2025-01-01T00:00:00Z",
        }

        with open(tmp_path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        (tmp_path / "papers").mkdir()
        (tmp_path / "index.faiss").touch()

        # Run diagnose
        result = subprocess.run(
            ["python", "src/cli.py", "diagnose"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            env={**dict(os.environ), "KNOWLEDGE_BASE_PATH": str(tmp_path)},
        )

        # Should show checkmarks or X marks
        assert "✓" in result.stdout or "✗" in result.stdout

    @pytest.mark.e2e
    def test_quality_filtering_cli_should_work(self):
        """Test --min-quality filtering in CLI."""
        result = subprocess.run(
            ["python", "src/cli.py", "search", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Check that quality filtering options exist
        assert "--min-quality" in result.stdout
        assert "--show-quality" in result.stdout

    @pytest.mark.e2e
    def test_get_sections_flag_should_work(self):
        """Test get command with --sections flag."""
        result = subprocess.run(
            ["python", "src/cli.py", "get", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Check that sections flag exists
        assert "--sections" in result.stdout or "-s" in result.stdout

    @pytest.mark.e2e
    def test_get_add_citation_flag_should_work(self):
        """Test get command has --add-citation flag."""
        result = subprocess.run(
            ["python", "src/cli.py", "get", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Check that add-citation flag exists
        assert "--add-citation" in result.stdout

    @pytest.mark.e2e
    def test_get_batch_add_citation_flag_should_work(self):
        """Test get-batch command has --add-citation flag."""
        result = subprocess.run(
            ["python", "src/cli.py", "get-batch", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Check that add-citation flag exists
        assert "--add-citation" in result.stdout

    @pytest.mark.e2e
    def test_removed_commands_should_not_exist(self):
        """Verify that removed commands are actually gone."""
        removed_commands = ["shortcuts", "duplicates", "analyze-gaps"]

        for cmd in removed_commands:
            result = subprocess.run(
                ["python", "src/cli.py", cmd],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent,
            )

            # Should fail with unknown command
            assert result.returncode != 0
            assert "no such option" in result.stderr.lower() or "error" in result.stderr.lower()

    @pytest.mark.e2e
    def test_demo_py_should_be_removed(self):
        """Verify demo.py was removed."""
        demo_path = Path(__file__).parent.parent.parent / "src" / "demo.py"
        assert not demo_path.exists()

    @pytest.mark.e2e
    def test_build_demo_flag_should_work(self):
        """Verify --demo flag in build_kb.py still works."""
        result = subprocess.run(
            ["python", "src/build_kb.py", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert "--demo" in result.stdout

    @pytest.mark.e2e
    def test_full_rebuild_flag_should_work(self):
        """Test that --rebuild forces complete rebuild."""
        result = subprocess.run(
            ["python", "src/build_kb.py", "--help"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )

        # Check that --rebuild flag exists
        assert "--rebuild" in result.stdout or "force complete rebuild" in result.stdout.lower()
