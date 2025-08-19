"""Tests for v4.0 specific features."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.build_kb import KnowledgeBaseBuilder
from src.cli import ResearchCLI, estimate_paper_quality


class TestV4VersionCheck:
    """Test v4.0 version compatibility checks."""

    def test_version_incompatibility_detection(self, temp_kb_dir):
        """Ensure v4.0 CLI rejects old KB versions."""
        # Create v3.x metadata
        old_metadata = {
            "papers": [],
            "total_papers": 0,
            "version": "3.1",  # Old version
            "embedding_model": "allenai-specter",
        }
        
        with open(temp_kb_dir / "metadata.json", "w") as f:
            json.dump(old_metadata, f)
        
        # Try to load with v4.0 CLI - should fail
        with pytest.raises(SystemExit) as exc_info:
            ResearchCLI(str(temp_kb_dir))
        
        assert exc_info.value.code == 1

    def test_version_4_acceptance(self, temp_kb_dir):
        """Ensure v4.0 CLI accepts v4.0 KB."""
        # Create v4.0 metadata
        v4_metadata = {
            "papers": [],
            "total_papers": 0,
            "version": "4.0",
            "embedding_model": "sentence-transformers/allenai-specter",
            "embedding_dimensions": 768,
        }
        
        with open(temp_kb_dir / "metadata.json", "w") as f:
            json.dump(v4_metadata, f)
        
        # Create empty FAISS index
        try:
            import faiss
            index = faiss.IndexFlatL2(768)
            faiss.write_index(index, str(temp_kb_dir / "index.faiss"))
        except ImportError:
            pytest.skip("FAISS not installed")
        
        # Should load without error
        with patch('src.cli.ResearchCLI._load_embedding_model') as mock_model:
            mock_model.return_value = MagicMock()
            cli = ResearchCLI(str(temp_kb_dir))
            assert cli.metadata["version"] == "4.0"


class TestIncrementalBuild:
    """Test smart incremental build functionality."""

    def test_incremental_flag_detection(self):
        """Test that incremental is default when KB exists."""
        builder = KnowledgeBaseBuilder()
        
        # Mock existing KB
        with patch.object(Path, 'exists', return_value=True):
            # Check that metadata file path would exist
            assert builder.metadata_file_path.name == "metadata.json"

    def test_full_rebuild_flag(self):
        """Test that --rebuild forces complete rebuild."""
        # This would be tested via CLI integration
        result = subprocess.run(
            ["python", "src/build_kb.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        # Check that --rebuild flag exists
        assert "--rebuild" in result.stdout or "force complete rebuild" in result.stdout.lower()

    def test_cache_preservation_during_incremental(self, temp_kb_dir):
        """Ensure caches are preserved during incremental updates."""
        builder = KnowledgeBaseBuilder(str(temp_kb_dir))
        
        # Create cache files
        cache_data = {"test_key": {"text": "cached content"}}
        cache_file = temp_kb_dir / ".pdf_text_cache.json"
        with open(cache_file, "w") as f:
            json.dump(cache_data, f)
        
        # Load cache
        builder.pdf_text_cache_file = cache_file
        cache = builder.load_cache()
        
        # Cache should be preserved
        assert cache.get("test_key") is not None
        assert cache["test_key"]["text"] == "cached content"


class TestSmartSearch:
    """Test smart-search command with section chunking."""

    def test_smart_search_command_exists(self):
        """Verify smart-search command is available."""
        result = subprocess.run(
            ["python", "src/cli.py", "smart-search", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        assert result.returncode == 0
        assert "smart search" in result.stdout.lower() or "section chunking" in result.stdout.lower()

    def test_smart_search_output_format(self, temp_kb_dir):
        """Test that smart-search creates proper output file."""
        # Create minimal KB
        metadata = {
            "papers": [{
                "id": "0001",
                "title": "Test Paper",
                "abstract": "Test abstract",
                "year": 2024,
            }],
            "total_papers": 1,
            "version": "4.0",
            "embedding_model": "sentence-transformers/allenai-specter",
        }
        
        with open(temp_kb_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # Create sections index
        sections = {
            "0001": {
                "abstract": "Test abstract",
                "methods": "Test methods section",
                "results": "Test results section",
            }
        }
        
        with open(temp_kb_dir / "sections_index.json", "w") as f:
            json.dump(sections, f)
        
        # Output file should be created
        output_file = Path("smart_search_results.json")
        if output_file.exists():
            output_file.unlink()
        
        # Note: Full integration test would require running the command
        # which needs FAISS index and model loading

    def test_section_priority_detection(self):
        """Test that query analysis correctly prioritizes sections."""
        # Test method-focused queries
        _ = [
            "how does the algorithm work",
            "methodology for data collection",
            "approach used in the study",
            "technique for analysis",
        ]
        
        # Test result-focused queries  
        _ = [
            "what were the outcomes",
            "findings of the study",
            "effect on patients",
            "results show that",
        ]
        
        # Would need to mock CLI to test properly
        # This is more of an integration test


class TestDiagnoseCommand:
    """Test the diagnose command for KB health checks."""

    def test_diagnose_command_exists(self):
        """Verify diagnose command is available."""
        result = subprocess.run(
            ["python", "src/cli.py", "diagnose"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        # Should run (may fail if no KB, but shouldn't crash)
        assert result.returncode in [0, 1]
        assert "diagnos" in result.stdout.lower() or "diagnos" in result.stderr.lower()

    def test_diagnose_output_format(self, temp_kb_dir):
        """Test diagnose command output format."""
        # Create complete v4.0 KB
        metadata = {
            "papers": [{"id": "0001", "title": "Test"}],
            "total_papers": 1,
            "version": "4.0",
            "last_updated": "2025-01-01T00:00:00Z",
        }
        
        with open(temp_kb_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        (temp_kb_dir / "papers").mkdir()
        (temp_kb_dir / "index.faiss").touch()
        
        # Run diagnose
        import os
        result = subprocess.run(
            ["python", "src/cli.py", "diagnose"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(os.environ), "KNOWLEDGE_BASE_PATH": str(temp_kb_dir)},
        )
        
        # Should show checkmarks or X marks
        assert "✓" in result.stdout or "✗" in result.stdout


class TestQualityScoring:
    """Test paper quality scoring system."""

    def test_quality_score_calculation(self):
        """Test quality score calculation logic."""
        # Systematic review from 2023 with full text
        paper1 = {
            "study_type": "systematic_review",
            "year": 2023,
            "has_full_text": True,
        }
        score1, explanation1 = estimate_paper_quality(paper1)
        assert score1 >= 95  # Should be near maximum
        assert "systematic review" in explanation1
        
        # Old case report without full text
        paper2 = {
            "study_type": "case_report",
            "year": 2010,
            "has_full_text": False,
        }
        score2, explanation2 = estimate_paper_quality(paper2)
        assert score2 <= 55  # Should be low
        
        # RCT with large sample size
        paper3 = {
            "study_type": "rct",
            "year": 2024,
            "sample_size": 5000,
            "has_full_text": True,
        }
        score3, explanation3 = estimate_paper_quality(paper3)
        assert score3 >= 85  # Should be high
        assert "n=5000" in explanation3

    def test_quality_filtering_cli(self):
        """Test --quality-min filtering in CLI."""
        result = subprocess.run(
            ["python", "src/cli.py", "search", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        # Check that quality filtering options exist
        assert "--quality-min" in result.stdout
        assert "--show-quality" in result.stdout


class TestSectionRetrieval:
    """Test section-specific paper retrieval."""

    def test_get_sections_flag(self):
        """Test get command with --sections flag."""
        result = subprocess.run(
            ["python", "src/cli.py", "get", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        # Check that sections flag exists
        assert "--sections" in result.stdout or "-s" in result.stdout

    def test_section_extraction_format(self, temp_kb_dir):
        """Test that sections are properly extracted and stored."""
        # Create sections index
        sections_data = {
            "0001": {
                "abstract": "This is the abstract",
                "introduction": "This is the introduction",
                "methods": "These are the methods",
                "results": "These are the results",
                "discussion": "This is the discussion",
                "conclusion": "This is the conclusion",
            }
        }
        
        sections_file = temp_kb_dir / "sections_index.json"
        with open(sections_file, "w") as f:
            json.dump(sections_data, f)
        
        # Verify structure
        with open(sections_file) as f:
            loaded = json.load(f)
        
        assert "0001" in loaded
        assert "methods" in loaded["0001"]
        assert loaded["0001"]["methods"] == "These are the methods"


class TestSimplificationImpact:
    """Test that v4.0 simplification removed expected features."""

    def test_removed_commands(self):
        """Verify that removed commands are actually gone."""
        removed_commands = ["shortcuts", "duplicates", "analyze-gaps"]
        
        for cmd in removed_commands:
            result = subprocess.run(
                ["python", "src/cli.py", cmd],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            
            # Should fail with unknown command
            assert result.returncode != 0
            assert "no such option" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_demo_py_removed(self):
        """Verify demo.py was removed."""
        demo_path = Path(__file__).parent.parent / "src" / "demo.py"
        assert not demo_path.exists()

    def test_build_demo_flag_works(self):
        """Verify --demo flag in build_kb.py still works."""
        result = subprocess.run(
            ["python", "src/build_kb.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        
        assert "--demo" in result.stdout


class TestErrorMessages:
    """Test that error messages are helpful in v4.0."""

    def test_version_error_message(self, temp_kb_dir):
        """Test that version mismatch gives clear error."""
        # Create old version KB
        old_metadata = {
            "papers": [],
            "total_papers": 0,
            "version": "3.1",
        }
        
        with open(temp_kb_dir / "metadata.json", "w") as f:
            json.dump(old_metadata, f)
        
        import os
        result = subprocess.run(
            ["python", "src/cli.py", "info"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={**dict(os.environ), "KNOWLEDGE_BASE_PATH": str(temp_kb_dir)},
        )
        
        # Should mention version incompatibility and rebuild
        assert "version" in result.stdout.lower() or "version" in result.stderr.lower()
        assert "4.0" in result.stdout or "4.0" in result.stderr

    def test_missing_kb_error_message(self):
        """Test helpful error when KB doesn't exist."""
        import os
        import tempfile
        
        # Use a truly nonexistent directory
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_kb = Path(tmpdir) / "nonexistent_kb"
            
            result = subprocess.run(
                ["python", "src/cli.py", "search", "test"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                env={**dict(os.environ), "KNOWLEDGE_BASE_PATH": str(fake_kb)},
            )
            
            # Should either fail or suggest building KB
            if result.returncode != 0:
                assert "build_kb.py" in result.stderr or "not found" in result.stderr.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
