# Shared Utilities Module Analysis: Pros and Cons

## Date: December 3, 2024

## Current State

The v5 pipeline has ~7-8 enrichment stages plus post-processing, with duplicated code for:
- HTTP session creation with retry logic
- DOI cleaning and validation
- Checkpoint loading/saving
- Progress reporting
- Rate limiting
- Batch processing helpers
- Error handling patterns

## Proposed Structure

```python
# src/pipeline_utils.py
"""Shared utilities for v5 pipeline stages."""

def create_session_with_retry(email=None, max_retries=5):
    """Create HTTP session with exponential backoff."""

def clean_doi(doi):
    """Clean and validate DOI string."""

def load_checkpoint(checkpoint_file):
    """Load checkpoint data if exists."""

def save_checkpoint(checkpoint_file, data):
    """Save checkpoint atomically."""

def batch_iterator(items, batch_size):
    """Yield batches from items."""

def rate_limit(last_request_time, min_interval):
    """Enforce rate limiting between requests."""
```

## Pros of Shared Utilities Module

### 1. Practical Code Reuse ✅
- **No Over-Engineering**: Just functions, no complex inheritance
- **Pick and Choose**: Use only what you need
- **Clear Dependencies**: Explicit imports show what's being used

```python
# In crossref_enricher.py
from pipeline_utils import create_session_with_retry, clean_doi, batch_iterator

# In s2_enricher.py
from pipeline_utils import create_session_with_retry, batch_iterator
# Don't need clean_doi for S2
```

### 2. Maintainability 🔧
- **Single Source of Truth**: Fix DOI cleaning once, helps all stages
- **Consistent Behavior**: Same retry logic everywhere
- **Easy to Test**: Pure functions are simple to unit test

```python
# tests/test_pipeline_utils.py
def test_clean_doi():
    assert clean_doi("10.1234/test") == "10.1234/test"
    assert clean_doi("https://doi.org/10.1234/test") == "10.1234/test"
    assert clean_doi("10.13039/funder") is None  # Funding DOI
```

### 3. Flexibility 🎯
- **No Forced Structure**: Each stage keeps its unique flow
- **Easy Overrides**: Can still use custom logic when needed
- **Gradual Adoption**: Can migrate one function at a time

```python
# Can mix utility functions with custom logic
session = create_session_with_retry(email="test@example.com")

# But use custom batch size logic for this specific API
for batch in batch_iterator(papers, batch_size=500 if api == "s2" else 50):
    process_batch(batch)
```

### 4. Low Coupling 🔗
- **Independent Evolution**: Stages can update independently
- **No Version Lock**: Using utils doesn't force specific patterns
- **Easy to Remove**: Can inline a function if it becomes too specialized

### 5. Documentation Benefits 📚
- **Central Reference**: One place to document common patterns
- **Usage Examples**: Can show best practices in docstrings
- **Type Hints**: Shared type definitions improve IDE support

```python
from typing import Optional, Dict, Any

def clean_doi(doi: str) -> Optional[str]:
    """Clean and validate a DOI string.

    Args:
        doi: Raw DOI string (may include URL prefix)

    Returns:
        Cleaned DOI or None if invalid

    Examples:
        >>> clean_doi("10.1234/test")
        '10.1234/test'
        >>> clean_doi("https://doi.org/10.1234/test")
        '10.1234/test'
        >>> clean_doi("not-a-doi")
        None
    """
```

## Cons of Shared Utilities Module

### 1. Dependency Management 📦
- **Import Overhead**: Every stage needs to import utils
- **Path Issues**: Need to ensure utils are in Python path
- **Circular Dependencies**: Risk if utils import from stages

```python
# Can get messy with relative imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.pipeline_utils import clean_doi
```

### 2. Over-Generalization Risk ⚠️
- **Lowest Common Denominator**: Functions become too generic
- **Parameter Explosion**: Adding options for every use case
- **Performance Loss**: Generic code may be slower than specialized

```python
# Bad: Too many parameters trying to handle everything
def make_api_request(url, method="GET", headers=None, params=None,
                     json_data=None, timeout=30, retries=3,
                     backoff_factor=1, verify_ssl=True,
                     rate_limit=None, session=None, ...):
    # 50 lines of conditionals
```

### 3. Hidden Complexity 🎭
- **Abstraction Leaks**: Utils hide important details
- **Debugging Harder**: Extra layer in stack traces
- **Magic Behavior**: Too much happening behind the scenes

```python
# User doesn't know this retries 5 times with exponential backoff
response = fetch_with_retry(url)  # What's actually happening?
```

### 4. Versioning Challenges 🔄
- **Breaking Changes**: Updating util affects all stages
- **Backward Compatibility**: Hard to maintain for shared code
- **Testing Burden**: Need to test utils with all stages

```python
# Change in utils
def clean_doi(doi, strict=True):  # Added parameter
    ...

# Now all stages need update or break
```

### 5. Scope Creep 📈
- **Kitchen Sink**: Utils module grows unbounded
- **Unclear Boundaries**: What belongs in utils vs stages?
- **Maintenance Burden**: Utils become dumping ground

```python
# pipeline_utils.py after 6 months:
# 2000 lines of random functions
def clean_doi()
def parse_author_name()
def calculate_h_index()
def generate_embeddings()  # Wait, this is too specific
def format_date()
def send_email_notification()  # How did this get here?
```

## Real Examples from Current Code

### Good Candidates for Utils

```python
# 1. DOI cleaning (used in 5+ places)
def clean_doi(doi: str) -> Optional[str]:
    """Clean and validate DOI."""
    if not doi:
        return None
    # Remove URL prefixes
    doi = re.sub(r"https?://(dx\.)?doi\.org/", "", doi)
    # Remove funding DOIs
    if "10.13039" in doi:
        return None
    # Validate format
    if not doi.startswith("10."):
        return None
    return doi

# 2. Session creation (used everywhere)
def create_session_with_retry(max_retries=5, backoff_factor=1):
    """Create requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# 3. Checkpoint operations (identical in all stages)
def save_checkpoint_atomic(filepath, data):
    """Save checkpoint atomically to prevent corruption."""
    temp_file = filepath.with_suffix('.tmp')
    with open(temp_file, 'w') as f:
        json.dump(data, f, indent=2)
    temp_file.replace(filepath)
```

### Bad Candidates for Utils

```python
# Too specific to arXiv
def search_by_arxiv_ids_batch(session, arxiv_ids, last_request_time, stats):
    """This is too specific for utils."""
    # 50 lines of arXiv-specific logic

# Too specific to quality scoring
def calculate_quality_with_components(paper):
    """This belongs in post-processor."""
    # Complex scoring logic

# API-specific enrichment
def extract_s2_metadata(s2_response):
    """Too specific to S2 response format."""
    # S2-specific field extraction
```

## Recommended Approach

### 1. Start Small
Create `src/pipeline_utils.py` with only the most obvious shared functions:

```python
"""Minimal shared utilities for v5 pipeline."""

from typing import Optional
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def clean_doi(doi: str) -> Optional[str]:
    """Clean and validate DOI string."""
    # 10 lines of code used in 5+ places

def create_session(max_retries: int = 5) -> requests.Session:
    """Create HTTP session with retry logic."""
    # 8 lines of code used in every enricher

def batch_iterator(items: list, batch_size: int):
    """Yield batches from list."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]
```

### 2. Gradual Migration
- Start with new code using utils
- Migrate existing code only when touching it
- Don't force a big refactor

### 3. Keep Boundaries Clear
```python
# pipeline_utils.py - Generic, reusable
# crossref_enricher.py - CrossRef-specific
# s2_enricher.py - S2-specific
# post_processor.py - KB building specific
```

### 4. Document Usage
```python
def clean_doi(doi: str) -> Optional[str]:
    """Clean and validate DOI string.

    Used by:
    - crossref_enricher.py
    - s2_enricher.py
    - openalex_enricher.py
    - pubmed_enricher.py
    - unpaywall_enricher.py
    """
```

## Decision Matrix

| Factor | Shared Utils | Copy-Paste | Base Class |
|--------|-------------|------------|------------|
| **Complexity** | Low | Very Low | High |
| **Maintainability** | Good | Poor | Good |
| **Flexibility** | High | Highest | Low |
| **Testing** | Easy | Redundant | Complex |
| **Debugging** | Moderate | Easy | Hard |
| **Refactor Risk** | Low | None | High |
| **Time to Implement** | 1 day | 0 days | 3 days |

## Recommendation

**YES to shared utilities module, BUT:**

1. **Keep it minimal** - Only truly shared functions (DOI cleaning, session creation, batch iteration)
2. **No business logic** - Just technical utilities
3. **No forced adoption** - Stages can choose what to use
4. **Clear scope** - If it's specific to one API, keep it in that module
5. **Start with 5-6 functions** - Grow organically based on actual need

### Initial `pipeline_utils.py` Contents

```python
"""Shared utilities for v5 pipeline stages.

Only include functions used by 3+ stages.
Keep API-specific logic in respective modules.
"""

# 1. HTTP session creation (all stages)
def create_session_with_retry(...)

# 2. DOI cleaning (5+ stages)
def clean_doi(...)

# 3. Batch iteration (4+ stages)
def batch_iterator(...)

# 4. Checkpoint operations (all stages)
def load_checkpoint(...)
def save_checkpoint_atomic(...)

# 5. Rate limiting (3+ stages)
def rate_limit_wait(...)

# That's it! No more than 150 lines total
```

## What NOT to Put in Utils

❌ API-specific response parsing
❌ Quality scoring logic
❌ Embedding generation
❌ Database operations
❌ Complex business rules
❌ Stage-specific configurations
❌ Field extraction logic
❌ Enrichment strategies

## Conclusion

A minimal shared utilities module provides 80% of the reuse benefits with 20% of the complexity of a base class. It's the sweet spot for the v5 pipeline:

- **Eliminates the most annoying duplication** (DOI cleaning, sessions)
- **Preserves stage independence** (no forced patterns)
- **Easy to implement and test** (just functions)
- **Low risk** (can always inline back if needed)

The key is **restraint**: Resist adding "might be useful" functions. Only add what's actively duplicated in 3+ places. The moment you find yourself adding parameters to handle different cases, stop and keep it in the specific modules.

**Bottom line**: Create `pipeline_utils.py` with 5-6 obvious functions. You'll eliminate ~500 lines of duplication with ~150 lines of shared code, and you can always expand (or contract) based on real needs.
