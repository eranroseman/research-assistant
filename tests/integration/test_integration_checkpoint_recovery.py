"""Integration tests for checkpoint recovery in build_kb.py."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from src.build_kb import get_semantic_scholar_data_batch


class TestCheckpointRecovery:
    """Test checkpoint recovery functionality in knowledge base building."""

    def setup_method(self):
        """Setup test environment before each test."""
        self.checkpoint_file = Path(".checkpoint.json")
        # Clean up any existing checkpoint
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

    def teardown_method(self):
        """Clean up after each test."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

    def test_checkpoint_creation_on_batch_processing(self):
        """Test that checkpoint file is created during batch processing."""
        test_papers = [
            {"key": f"TEST_{i:04d}", "doi": f"10.1234/test{i}", "title": f"Test Paper {i}"}
            for i in range(60)  # More than checkpoint interval (50)
        ]
        
        with patch('requests.post') as mock_post:
            # Mock successful API responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"title": f"Paper {i}", "citationCount": i}
                for i in range(500)  # Enough for any batch size
            ]
            mock_post.return_value = mock_response
            
            # Process papers - should create checkpoint
            results = get_semantic_scholar_data_batch(test_papers)
            
            # Verify results were returned
            assert len(results) == 60
            
            # Note: Checkpoint should be cleaned up after successful completion
            assert not self.checkpoint_file.exists(), "Checkpoint should be cleaned up after success"

    def test_checkpoint_recovery_after_interruption(self):
        """Test recovery from checkpoint after simulated interruption."""
        # Create a checkpoint file simulating partial progress
        checkpoint_data = {
            "results": {
                "PAPER_001": {"title": "Already Processed", "citationCount": 100},
                "PAPER_002": {"title": "Also Processed", "citationCount": 50},
            },
            "processed_keys": ["PAPER_001", "PAPER_002"],
            "timestamp": "2025-08-25T12:00:00Z"
        }
        
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)
        
        # Prepare test papers including the already processed ones
        test_papers = [
            {"key": "PAPER_001", "doi": "10.1234/001", "title": "Paper 1"},
            {"key": "PAPER_002", "doi": "10.1234/002", "title": "Paper 2"},
            {"key": "PAPER_003", "doi": "10.1234/003", "title": "Paper 3"},
            {"key": "PAPER_004", "doi": "10.1234/004", "title": "Paper 4"},
        ]
        
        with patch('requests.post') as mock_post:
            # Mock API response for only the unprocessed papers
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"title": "Paper 3", "citationCount": 30},
                {"title": "Paper 4", "citationCount": 40},
            ]
            mock_post.return_value = mock_response
            
            # Call function - should skip already processed papers
            results = get_semantic_scholar_data_batch(test_papers)
            
            # Verify all papers in results
            assert len(results) == 4
            
            # Verify checkpoint data was preserved
            assert results["PAPER_001"]["citationCount"] == 100
            assert results["PAPER_002"]["citationCount"] == 50
            
            # Verify only unprocessed papers were fetched
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            sent_data = call_args[1]["json"]["ids"]
            # Should only have requested PAPER_003 and PAPER_004
            assert len(sent_data) == 2
            assert "DOI:10.1234/003" in sent_data
            assert "DOI:10.1234/004" in sent_data

    def test_checkpoint_cleanup_on_success(self):
        """Test that checkpoint file is cleaned up after successful completion."""
        test_papers = [
            {"key": f"TEST_{i:04d}", "doi": f"10.1234/test{i}", "title": f"Test Paper {i}"}
            for i in range(5)
        ]
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"title": f"Paper {i}", "citationCount": i} for i in range(5)
            ]
            mock_post.return_value = mock_response
            
            # Process papers
            results = get_semantic_scholar_data_batch(test_papers)
            
            # Verify success
            assert len(results) == 5
            
            # Verify checkpoint was cleaned up
            assert not self.checkpoint_file.exists()

    def test_checkpoint_preserves_error_results(self):
        """Test that checkpoint preserves papers that had errors."""
        # Create checkpoint with some error results
        checkpoint_data = {
            "results": {
                "PAPER_001": {"error": "not_found", "message": "Paper not found"},
                "PAPER_002": {"title": "Success", "citationCount": 25},
            },
            "processed_keys": ["PAPER_001", "PAPER_002"],
            "timestamp": "2025-08-25T12:00:00Z"
        }
        
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)
        
        test_papers = [
            {"key": "PAPER_001", "doi": "10.1234/001", "title": "Paper 1"},
            {"key": "PAPER_002", "doi": "10.1234/002", "title": "Paper 2"},
            {"key": "PAPER_003", "doi": "10.1234/003", "title": "Paper 3"},
        ]
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"title": "Paper 3", "citationCount": 30}
            ]
            mock_post.return_value = mock_response
            
            results = get_semantic_scholar_data_batch(test_papers)
            
            # Verify error result was preserved
            assert results["PAPER_001"]["error"] == "not_found"
            # Verify success result was preserved
            assert results["PAPER_002"]["citationCount"] == 25
            # Verify new paper was processed
            assert "PAPER_003" in results

    def test_corrupted_checkpoint_recovery(self):
        """Test graceful handling of corrupted checkpoint file."""
        # Create corrupted checkpoint file
        with open(self.checkpoint_file, "w") as f:
            f.write("{ invalid json content")
        
        test_papers = [
            {"key": "PAPER_001", "doi": "10.1234/001", "title": "Paper 1"},
        ]
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"title": "Paper 1", "citationCount": 10}
            ]
            mock_post.return_value = mock_response
            
            # Should handle corrupted checkpoint gracefully
            results = get_semantic_scholar_data_batch(test_papers)
            
            assert len(results) == 1
            assert "PAPER_001" in results
            # Should have processed the paper despite corrupted checkpoint
            mock_post.assert_called_once()

    def test_papers_without_dois_checkpoint(self):
        """Test checkpoint handling for papers without DOIs."""
        test_papers = [
            {"key": f"NO_DOI_{i:04d}", "doi": "", "title": f"Paper without DOI {i}"}
            for i in range(55)  # More than checkpoint interval
        ]
        
        with patch('src.build_kb.get_semantic_scholar_data_sync') as mock_sync:
            # Mock individual API calls for papers without DOIs
            mock_sync.return_value = {"title": "Found paper", "citationCount": 5}
            
            results = get_semantic_scholar_data_batch(test_papers)
            
            # All papers should be processed
            assert len(results) == 55
            
            # Checkpoint should be cleaned up after success
            assert not self.checkpoint_file.exists()

    @pytest.mark.parametrize("batch_size,total_papers", [
        (50, 100),  # Exactly 2 checkpoints
        (50, 151),  # 3 checkpoints + 1 paper
        (50, 49),   # Less than one checkpoint interval
    ])
    def test_checkpoint_intervals(self, batch_size, total_papers):
        """Test checkpoint saving at correct intervals."""
        from unittest.mock import MagicMock
        
        test_papers = [
            {"key": f"TEST_{i:04d}", "doi": f"10.1234/test{i}", "title": f"Test Paper {i}"}
            for i in range(total_papers)
        ]
        
        # Track checkpoint saves
        checkpoint_saves = []
        original_open = open
        
        def track_checkpoint_open(filename, *args, **kwargs):
            if str(filename) == ".checkpoint.json" and "w" in str(args):
                checkpoint_saves.append(len(checkpoint_saves))
            return original_open(filename, *args, **kwargs)
        
        with patch('builtins.open', side_effect=track_checkpoint_open):
            with patch('requests.post') as mock_post:
                # Mock successful responses for all papers
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = [
                    {"title": f"Paper {i}", "citationCount": i}
                    for i in range(500)  # Enough for any test case
                ]
                mock_post.return_value = mock_response
                
                results = get_semantic_scholar_data_batch(test_papers)
                
                assert len(results) == total_papers