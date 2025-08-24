"""Simple API retry utilities for Research Assistant.

This module provides a minimal, focused solution to the API retry inconsistencies
that caused failures in v4.4-v4.6. No over-engineering, just fixing the actual bug.
"""

import asyncio
import time
from typing import Any
import aiohttp
import requests


async def async_api_request_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    params: dict[str, Any] | None = None,
    max_retries: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 10.0,
) -> dict[str, Any] | None:
    """Make an async API request with exponential backoff retry logic.
    
    This fixes the inconsistent retry patterns that caused rate limiting issues
    in v4.4-v4.6 of the Research Assistant.
    
    Args:
        session: Active aiohttp session
        url: API endpoint URL
        params: Query parameters
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        JSON response as dict if successful, None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()  # type: ignore[no-any-return]
                    
                if response.status == 429:  # Rate limited
                    # Exponential backoff with cap
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        continue
                        
                # Non-retryable HTTP error
                if attempt == max_retries - 1:
                    print(f"API request failed with status {response.status}")
                return None
                
        except TimeoutError:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                await asyncio.sleep(delay)
                continue
            print(f"API timeout after {max_retries} attempts")
            
        except Exception as e:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                await asyncio.sleep(delay)
                continue
            print(f"API request error: {e}")
            
    return None


def sync_api_request_with_retry(
    url: str,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
    max_retries: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 10.0,
) -> dict[str, Any] | None:
    """Make a synchronous API request with exponential backoff retry logic.
    
    This provides the same retry behavior as the async version for synchronous code.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        JSON response as dict if successful, None if all retries failed
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            
            if response.status_code == 200:
                return response.json()  # type: ignore[no-any-return]
                
            if response.status_code == 429:  # Rate limited
                # Exponential backoff with cap
                delay = min(base_delay * (2 ** attempt), max_delay)
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
                    
            # Non-retryable HTTP error
            if attempt == max_retries - 1:
                print(f"API request failed with status {response.status_code}")
            return None
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)
                continue
            print(f"API timeout after {max_retries} attempts")
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)
                continue
            print(f"API request error: {e}")
            
    return None
