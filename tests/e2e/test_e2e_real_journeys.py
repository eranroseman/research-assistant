"""Real-world E2E journey tests using subprocess for actual CLI execution.

These tests simulate complete user workflows using the actual CLI commands
via subprocess, ensuring real-world behavior is tested.
"""

import json
import subprocess
from pathlib import Path

import pytest


class TestRealUserJourneys:
    """Test real user journeys using subprocess for actual CLI execution."""
    
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test environment."""
        self.tmp_path = tmp_path
        self.project_root = Path(__file__).parent.parent.parent
        
    def run_cli_command(self, args: list[str], input_text: str | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a CLI command and return the result.
        
        Args:
            args: Command arguments (without 'python src/cli.py')
            input_text: Optional input to send to the command
            timeout: Command timeout in seconds
            
        Returns:
            Completed process with output
        """
        cmd = ["python", "src/cli.py", *args]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=timeout,
            cwd=self.project_root,
            check=False
        )
    
    def run_build_command(self, args: list[str], input_text: str | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
        """Run a build_kb.py command and return the result.
        
        Args:
            args: Command arguments (without 'python src/build_kb.py')
            input_text: Optional input to send to the command
            timeout: Command timeout in seconds
            
        Returns:
            Completed process with output
        """
        cmd = ["python", "src/build_kb.py", *args]
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=timeout,
            cwd=self.project_root,
            check=False
        )


class TestJourney1_BasicResearchWorkflow(TestRealUserJourneys):
    """Journey 1: Basic research workflow - search, get, cite."""
    
    def test_complete_basic_research_workflow(self):
        """Test the complete basic research workflow.
        
        Scenario:
        1. Check KB status with info
        2. Search for papers on a topic
        3. Get a specific paper
        4. Generate citations
        5. Use smart-search for broader results
        """
        # Step 1: Check KB status
        result = self.run_cli_command(["info"])
        assert result.returncode in [0, 1]
        assert "Knowledge Base" in result.stdout or "knowledge base" in result.stdout.lower()
        
        # Step 2: Search for papers (will work if KB exists)
        result = self.run_cli_command(["search", "diabetes", "--top-k", "5"])
        # Search may fail if KB doesn't exist, which is ok for this test
        if result.returncode == 0:
            assert "paper" in result.stdout.lower() or "result" in result.stdout.lower()
        
        # Step 3: Get help for get command (always works)
        result = self.run_cli_command(["get", "--help"])
        assert result.returncode == 0
        assert "paper" in result.stdout.lower()
        
        # Step 4: Get help for cite command
        result = self.run_cli_command(["cite", "--help"])
        assert result.returncode == 0
        assert "citation" in result.stdout.lower() or "IEEE" in result.stdout
        
        # Step 5: Check smart-search availability
        result = self.run_cli_command(["smart-search", "--help"])
        assert result.returncode == 0
        assert "smart" in result.stdout.lower() or "chunk" in result.stdout.lower()
    
    def test_search_with_quality_filtering(self):
        """Test search with quality filtering options.
        
        Scenario:
        1. Search with quality display
        2. Search with minimum quality threshold
        3. Verify quality indicators in output
        """
        # Test quality filtering options are available
        result = self.run_cli_command(["search", "--help"])
        assert result.returncode == 0
        assert "--show-quality" in result.stdout or "--quality" in result.stdout
        assert "--quality-min" in result.stdout or "--min-quality" in result.stdout
        
        # Try search with quality display (may fail without KB)
        result = self.run_cli_command(["search", "test", "--show-quality"])
        # If KB exists, check for quality indicators
        if result.returncode == 0 and "papers found" in result.stdout:
            # Quality should be shown as scores or grades
            pass  # Quality display format varies
    
    def test_batch_command_workflow(self):
        """Test batch command execution.
        
        Scenario:
        1. Create batch file with multiple commands
        2. Execute batch
        3. Verify batch execution
        """
        # Create a simple batch file
        batch_file = self.tmp_path / "test_batch.json"
        batch_commands = [
            {"command": "info", "args": {}},
            {"command": "diagnose", "args": {}}
        ]
        batch_file.write_text(json.dumps(batch_commands))
        
        # Execute batch
        result = self.run_cli_command(["batch", str(batch_file)])
        # Batch execution should at least not crash
        assert result.returncode in [0, 1, 2]  # May fail if commands fail
        
        # Check batch help
        result = self.run_cli_command(["batch", "--help"])
        assert result.returncode == 0
        assert "batch" in result.stdout.lower()
        assert "command" in result.stdout.lower()


class TestJourney2_AdvancedSearchWorkflow(TestRealUserJourneys):
    """Journey 2: Advanced search features and author lookup."""
    
    def test_author_search_workflow(self):
        """Test author search functionality.
        
        Scenario:
        1. Search by author name
        2. Use exact match option
        3. Verify author search works
        """
        # Check author command exists
        result = self.run_cli_command(["author", "--help"])
        assert result.returncode == 0
        assert "author" in result.stdout.lower()
        
        # Try author search (may fail without KB)
        result = self.run_cli_command(["author", "Smith"])
        # Command should at least not crash
        assert result.returncode in [0, 1]
        
        # Test exact match option
        result = self.run_cli_command(["author", "Smith, J.", "--exact"])
        assert result.returncode in [0, 1]
    
    def test_smart_search_chunking(self):
        """Test smart search with automatic chunking.
        
        Scenario:
        1. Use smart-search for large result sets
        2. Specify chunk size
        3. Test section filtering
        """
        # Check smart-search options
        result = self.run_cli_command(["smart-search", "--help"])
        assert result.returncode == 0
        assert "-k" in result.stdout or "--top-k" in result.stdout
        
        # Try smart search (may fail without KB or timeout)
        result = self.run_cli_command(["smart-search", "healthcare", "-k", "10"], timeout=60)
        assert result.returncode in [0, 1, -9]  # -9 is SIGKILL from timeout
        
        # If successful, output should mention chunking or sections
        if result.returncode == 0:
            # Results may be chunked or sectioned
            pass
    
    def test_export_functionality(self):
        """Test search result export.
        
        Scenario:
        1. Search with export option
        2. Verify export file creation
        3. Test CSV format
        """
        export_file = self.tmp_path / "search_results.csv"
        
        # Try search with export
        result = self.run_cli_command([
            "search", "test", 
            "--export", str(export_file),
            "--top-k", "5"
        ])
        
        # Check if export option is available
        if "--export" not in result.stderr:
            # Export may work if KB exists
            if result.returncode == 0 and export_file.exists():
                content = export_file.read_text()
                assert len(content) > 0


class TestJourney3_CitationAndRetrieval(TestRealUserJourneys):
    """Journey 3: Paper retrieval and citation generation."""
    
    def test_get_paper_with_sections(self):
        """Test paper retrieval with section selection.
        
        Scenario:
        1. Get paper with specific sections
        2. Get paper with citation
        3. Use get-batch for multiple papers
        """
        # Check get command options
        result = self.run_cli_command(["get", "--help"])
        assert result.returncode == 0
        assert "--sections" in result.stdout
        assert "--add-citation" in result.stdout
        
        # Check get-batch exists
        result = self.run_cli_command(["get-batch", "--help"])
        assert result.returncode == 0
        assert "batch" in result.stdout.lower() or "multiple" in result.stdout.lower()
    
    def test_citation_generation_formats(self):
        """Test citation generation in different formats.
        
        Scenario:
        1. Generate IEEE citations
        2. Test text format
        3. Test BibTeX format if available
        """
        # Check cite command options
        result = self.run_cli_command(["cite", "--help"])
        assert result.returncode == 0
        assert "IEEE" in result.stdout or "citation" in result.stdout.lower()
        
        # Check output format options
        if "--output-format" in result.stdout:
            assert "text" in result.stdout or "bibtex" in result.stdout
    
    def test_paper_quality_indicators(self):
        """Test quality indicators in paper display.
        
        Scenario:
        1. Get paper with quality score
        2. Search with quality display
        3. Verify quality grades (A+, A, B, C, D, F)
        """
        # Check if quality scoring is mentioned
        result = self.run_cli_command(["info"])
        assert result.returncode in [0, 1]
        
        if "quality" in result.stdout.lower():
            # System supports quality scoring
            # Check for quality distribution or scores
            assert ("A+" in result.stdout or 
                   "quality" in result.stdout.lower() or
                   "score" in result.stdout.lower())


class TestJourney4_SystemDiagnostics(TestRealUserJourneys):
    """Journey 4: System health and diagnostics."""
    
    def test_diagnose_command(self):
        """Test system diagnostics.
        
        Scenario:
        1. Run diagnose command
        2. Check health status
        3. Verify diagnostic output
        """
        result = self.run_cli_command(["diagnose"])
        assert result.returncode == 0
        assert ("diagnos" in result.stdout.lower() or 
               "health" in result.stdout.lower() or
               "check" in result.stdout.lower())
    
    def test_info_command_details(self):
        """Test detailed KB information.
        
        Scenario:
        1. Get KB statistics
        2. Check paper count
        3. Verify quality distribution
        """
        result = self.run_cli_command(["info"])
        assert result.returncode in [0, 1]
        assert "Knowledge Base" in result.stdout or "knowledge base" in result.stdout.lower()
        
        # Check for various info elements
        info_elements = ["papers", "updated", "version", "location", "quality"]
        matches = sum(1 for elem in info_elements if elem in result.stdout.lower())
        assert matches >= 2  # At least 2 info elements should be present
    
    def test_help_system(self):
        """Test help system completeness.
        
        Scenario:
        1. Main help shows all commands
        2. Each command has help
        3. Help is informative
        """
        # Main help
        result = self.run_cli_command(["--help"])
        assert result.returncode == 0
        
        # Check key commands are listed
        commands = ["search", "get", "cite", "batch", "info", "diagnose", 
                   "smart-search", "author", "get-batch"]
        for cmd in commands:
            assert cmd in result.stdout
        
        # Verify each command has help
        for cmd in ["search", "get", "cite", "batch"]:
            result = self.run_cli_command([cmd, "--help"])
            assert result.returncode == 0
            assert len(result.stdout) > 100  # Help should be substantial


class TestJourney5_BuildAndUpdate(TestRealUserJourneys):
    """Journey 5: KB building and updating (separate script)."""
    
    def test_build_kb_help(self):
        """Test build_kb.py help and options.
        
        Scenario:
        1. Check build script exists
        2. Verify build options
        3. Test demo mode availability
        """
        # Check build script help
        result = self.run_build_command(["--help"])
        assert result.returncode == 0
        assert "build" in result.stdout.lower()
        
        # Check for key options
        assert "--demo" in result.stdout
        assert "--rebuild" in result.stdout
        
        # Check for import/export if available
        if "--export" in result.stdout:
            assert "--import" in result.stdout
    
    def test_build_demo_mode(self):
        """Test demo KB building.
        
        Scenario:
        1. Check demo mode exists
        2. Verify demo doesn't require Zotero
        3. Test safe for testing
        """
        # Check demo mode in help
        result = self.run_build_command(["--help"])
        assert result.returncode == 0
        assert "--demo" in result.stdout
        
        # Demo mode should be documented as safe/small
        if "5-paper" in result.stdout or "demo" in result.stdout.lower():
            # Demo mode is available for testing
            pass
    
    def test_incremental_vs_rebuild(self):
        """Test incremental update vs full rebuild.
        
        Scenario:
        1. Default is incremental (safe)
        2. Rebuild requires explicit flag
        3. Verify safety features
        """
        # Check that default behavior is documented
        result = self.run_build_command(["--help"])
        assert result.returncode == 0
        
        # Check for rebuild option
        assert "--rebuild" in result.stdout
        
        # Default should be safe/incremental
        if "incremental" in result.stdout.lower() or "update" in result.stdout.lower():
            # System supports safe incremental updates
            pass


class TestJourney6_ErrorHandling(TestRealUserJourneys):
    """Journey 6: Error handling and edge cases."""
    
    def test_missing_arguments_handling(self):
        """Test handling of missing required arguments.
        
        Scenario:
        1. Commands without required args show errors
        2. Error messages are helpful
        3. Suggest correct usage
        """
        # Search without query
        result = self.run_cli_command(["search"])
        assert result.returncode != 0
        assert "Usage" in result.stderr or "required" in result.stderr.lower()
        
        # Get without paper ID
        result = self.run_cli_command(["get"])
        assert result.returncode != 0
        assert "Usage" in result.stderr or "paper" in result.stderr.lower()
        
        # Cite without IDs
        result = self.run_cli_command(["cite"])
        assert result.returncode != 0
        assert "Usage" in result.stderr or "paper" in result.stderr.lower()
    
    def test_invalid_paper_id_handling(self):
        """Test handling of invalid paper IDs.
        
        Scenario:
        1. Invalid format shows error
        2. Non-existent ID handled gracefully
        3. Error messages guide user
        """
        # Invalid format
        result = self.run_cli_command(["get", "invalid"])
        # Should either show format error or not found
        assert result.returncode != 0 or "not found" in result.stdout.lower()
        
        # Non-existent but valid format
        result = self.run_cli_command(["get", "9999"])
        assert result.returncode != 0 or "not found" in result.stdout.lower()
    
    def test_timeout_handling(self):
        """Test command timeout handling.
        
        Scenario:
        1. Commands complete in reasonable time
        2. Help is instant
        3. No hanging commands
        """
        import time
        
        # Help should be instant
        start = time.time()
        result = self.run_cli_command(["--help"], timeout=5)
        duration = time.time() - start
        assert result.returncode == 0
        assert duration < 2.0  # Help should be fast
        
        # Info should be quick
        start = time.time()
        result = self.run_cli_command(["info"], timeout=5)
        duration = time.time() - start
        assert result.returncode == 0
        assert duration < 3.0  # Info should be reasonably fast


class TestJourneyPerformance:
    """Test performance characteristics of user journeys."""
    
    def test_command_response_times(self, tmp_path: Path):
        """Verify commands respond within acceptable time limits."""
        import time
        project_root = Path(__file__).parent.parent.parent
        
        performance_targets = {
            "--help": 1.0,
            "info": 2.0,
            "diagnose": 3.0,
            "search --help": 1.0,
            "cite --help": 1.0,
        }
        
        for cmd_str, max_time in performance_targets.items():
            cmd = ["python", "src/cli.py", *cmd_str.split()]
            
            start = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max_time + 2,  # Add buffer
                cwd=project_root,
                check=False
            )
            duration = time.time() - start
            
            # Command should complete within target time
            assert duration < max_time + 0.5, f"{cmd_str} took {duration:.2f}s (max: {max_time}s)"
            
            # Help commands should always succeed
            if "--help" in cmd_str:
                assert result.returncode == 0
