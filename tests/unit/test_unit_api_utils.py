"""Unit tests for API retry utilities."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
import asyncio
import aiohttp

from src.api_utils import sync_api_request_with_retry, async_api_request_with_retry


class TestSyncApiRequestWithRetry:
    """Test synchronous API request retry logic."""

    def test_successful_request_first_attempt(self):
        """Test successful API request on first attempt."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "success"}
            mock_get.return_value = mock_response
            
            result = sync_api_request_with_retry("http://test.com/api")
            
            assert result == {"data": "success"}
            assert mock_get.call_count == 1

    def test_rate_limited_then_success(self):
        """Test retry on rate limiting (429) then success."""
        with patch('requests.get') as mock_get:
            with patch('time.sleep') as mock_sleep:  # Prevent actual sleep
                # First call returns 429, second succeeds
                mock_response_429 = Mock()
                mock_response_429.status_code = 429
                
                mock_response_200 = Mock()
                mock_response_200.status_code = 200
                mock_response_200.json.return_value = {"data": "success"}
                
                mock_get.side_effect = [mock_response_429, mock_response_200]
                
                result = sync_api_request_with_retry("http://test.com/api")
                
                assert result == {"data": "success"}
                assert mock_get.call_count == 2
                # Check exponential backoff was applied
                mock_sleep.assert_called_once()
                assert mock_sleep.call_args[0][0] >= 0.1  # At least base delay

    def test_timeout_with_retry(self):
        """Test timeout handling with retry."""
        with patch('requests.get') as mock_get:
            with patch('time.sleep') as mock_sleep:
                # First call times out, second succeeds
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": "success"}
                
                mock_get.side_effect = [
                    requests.exceptions.Timeout("Connection timed out"),
                    mock_response
                ]
                
                result = sync_api_request_with_retry("http://test.com/api")
                
                assert result == {"data": "success"}
                assert mock_get.call_count == 2
                mock_sleep.assert_called_once()

    def test_max_retries_exceeded(self):
        """Test that function returns None after max retries."""
        with patch('requests.get') as mock_get:
            with patch('time.sleep') as mock_sleep:
                mock_response = Mock()
                mock_response.status_code = 429
                mock_get.return_value = mock_response
                
                result = sync_api_request_with_retry(
                    "http://test.com/api",
                    max_retries=3
                )
                
                assert result is None
                assert mock_get.call_count == 3
                # Should have slept between retries (not after last one)
                assert mock_sleep.call_count == 2

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff increases correctly."""
        with patch('requests.get') as mock_get:
            with patch('time.sleep') as mock_sleep:
                mock_response = Mock()
                mock_response.status_code = 429
                mock_get.return_value = mock_response
                
                sync_api_request_with_retry(
                    "http://test.com/api",
                    max_retries=4,
                    base_delay=0.1,
                    max_delay=10.0
                )
                
                # Check sleep delays follow exponential pattern
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert len(sleep_calls) == 3  # 3 retries = 3 sleeps
                assert sleep_calls[0] == 0.1  # First retry: base_delay
                assert sleep_calls[1] == 0.2  # Second retry: base_delay * 2
                assert sleep_calls[2] == 0.4  # Third retry: base_delay * 4

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        with patch('requests.get') as mock_get:
            with patch('time.sleep') as mock_sleep:
                mock_response = Mock()
                mock_response.status_code = 429
                mock_get.return_value = mock_response
                
                sync_api_request_with_retry(
                    "http://test.com/api",
                    max_retries=10,
                    base_delay=1.0,
                    max_delay=5.0
                )
                
                # Check that no sleep exceeds max_delay
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert all(delay <= 5.0 for delay in sleep_calls)
                # Later delays should be capped at 5.0
                assert sleep_calls[-1] == 5.0

    def test_non_retryable_error(self):
        """Test that non-429 errors don't trigger retries."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = sync_api_request_with_retry("http://test.com/api")
            
            assert result is None
            assert mock_get.call_count == 1  # No retries for 404


class TestAsyncApiRequestWithRetry:
    """Test asynchronous API request retry logic."""

    @pytest.mark.asyncio
    async def test_successful_request_first_attempt(self):
        """Test successful async API request on first attempt."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = MagicMock(return_value=asyncio.Future())
        mock_response.json.return_value.set_result({"data": "success"})
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await async_api_request_with_retry(
            mock_session,
            "http://test.com/api"
        )
        
        assert result == {"data": "success"}
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limited_then_success(self):
        """Test async retry on rate limiting then success."""
        mock_session = MagicMock()
        
        # First response: 429
        mock_response_429 = MagicMock()
        mock_response_429.status = 429
        
        # Second response: 200
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.json = MagicMock(return_value=asyncio.Future())
        mock_response_200.json.return_value.set_result({"data": "success"})
        
        # Configure side effects
        mock_session.get.return_value.__aenter__.side_effect = [
            mock_response_429,
            mock_response_200
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.return_value = asyncio.Future()
            mock_sleep.return_value.set_result(None)
            
            result = await async_api_request_with_retry(
                mock_session,
                "http://test.com/api"
            )
            
            assert result == {"data": "success"}
            assert mock_session.get.call_count == 2
            mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_async(self):
        """Test async function returns None after max retries."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 429
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.return_value = asyncio.Future()
            mock_sleep.return_value.set_result(None)
            
            result = await async_api_request_with_retry(
                mock_session,
                "http://test.com/api",
                max_retries=3
            )
            
            assert result is None
            assert mock_session.get.call_count == 3
            assert mock_sleep.call_count == 2  # Sleep between retries, not after last