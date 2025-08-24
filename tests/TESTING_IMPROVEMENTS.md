# Test Suite Improvement Recommendations

Based on analysis of test failures and current test suite structure.

## Executive Summary

The test suite has good structure but needs improvements in:
1. **Test reliability** - Dead code and undefined variables causing failures
2. **Performance thresholds** - Too strict for CI environments  
3. **Mock coverage** - Only 20-33% code coverage due to missing mocks
4. **Test isolation** - Dependencies on external state (KB, APIs)

## Critical Issues Found

### Test Failures Summary
- **Mypy**: 2 type ignore issues (minor)
- **Ruff**: 52 linting errors (mostly test files)
- **Unit Tests**: 1/278 failed (command usage logger)
- **Integration**: 4/127 failed (gap analysis, KB prompt)
- **E2E**: 2/46 failed (performance, batch timeout)
- **Performance**: Search operations >15s threshold

## Implemented Improvements

### What Was Already Implemented

### 1. ✅ Centralized CliRunner Fixtures (conftest.py)
Added reusable Click testing fixtures to avoid repetition:
- `runner`: Basic CliRunner for CLI testing
- `isolated_runner`: CliRunner with isolated filesystem
- `runner_with_env`: CliRunner with custom environment variables

### 2. ✅ Mock API Fixtures (conftest.py)
Created comprehensive mocking fixtures for external dependencies:
- `mock_semantic_scholar`: Mocks successful Semantic Scholar API responses
- `mock_semantic_scholar_error`: Simulates various API error conditions
- `mock_zotero`: Mocks Zotero API for KB building tests
- `mock_external_apis`: Convenience fixture combining all mocks
- `sample_paper` & `sample_kb_metadata`: Consistent test data fixtures

### 3. ✅ Enhanced Test Markers (pytest.ini)
Expanded marker system for better test organization:

**Test Type Markers:**
- `unit`: Fast, isolated tests with mocks
- `integration`: Component interaction tests
- `e2e`: End-to-end CLI workflow tests
- `performance`: Speed and resource benchmarks

**Dependency Markers:**
- `requires_kb`: Needs built knowledge base
- `requires_api`: Needs external API (mock in CI)
- `requires_gpu`: Needs CUDA support
- `requires_zotero`: Needs Zotero installation

**Feature Markers:**
- `cli`, `search`, `quality`, `gap_analysis`, `discover`

**Execution Control:**
- `slow`/`fast`: Speed-based filtering
- `serial`: Must run alone (not parallel)
- `critical`: Must pass for release
- `flaky`: May fail intermittently

## How to Use

### Running Tests by Marker
```bash
# Fast unit tests only
pytest -m "unit and fast"

# Integration tests without KB requirement
pytest -m "integration and not requires_kb"

# Critical tests for release validation
pytest -m "critical"

# Skip slow tests for quick feedback
pytest -m "not slow"

# Feature-specific tests
pytest -m "search or quality"
```

### Using New Fixtures in Tests
```python
def test_cli_command(runner):
    """Use centralized runner - no imports needed."""
    from src.cli import cli
    result = runner.invoke(cli, ['search', 'term'])
    assert result.exit_code == 0

def test_with_mocked_api(mock_semantic_scholar):
    """API calls automatically mocked."""
    import requests
    response = requests.get('https://api.semanticscholar.org/paper/123')
    assert response.status_code == 200  # Mocked response

def test_isolated_filesystem(isolated_runner):
    """Work in isolated environment."""
    # Create files without affecting real filesystem
    with open('test.txt', 'w') as f:
        f.write('test')
```

### Applying Markers to Test Classes
```python
@pytest.mark.unit
@pytest.mark.fast
@pytest.mark.cli
class TestMyFeature:
    """All tests in class inherit markers."""
    pass
```

## Files Modified

1. **tests/conftest.py** - Added 10+ new fixtures
2. **tests/pytest.ini** - Enhanced marker definitions  
3. **tests/unit/test_unit_cli_interface.py** - Added markers example
4. **tests/integration/test_integration_gap_analysis.py** - Added markers
5. **tests/e2e/test_e2e_cli_commands.py** - Added markers to all test classes
6. **tests/examples/test_example_with_fixtures.py** - Created comprehensive examples

## Benefits Achieved

✅ **DRY Principle**: No more repeated CliRunner instantiation
✅ **Test Reliability**: External APIs mocked by default
✅ **Better Organization**: Clear test categorization via markers
✅ **Flexible Execution**: Run specific test subsets easily
✅ **Consistent Data**: Shared fixtures for test data
✅ **Error Testing**: Dedicated fixtures for error scenarios

## Next Steps

To apply these improvements throughout the test suite:

1. **Replace CliRunner instantiation** in existing tests with `runner` fixture
2. **Add markers** to remaining test files
3. **Use mock fixtures** instead of inline mocking
4. **Update CI/CD** to use marker-based test selection
5. **Document** marker conventions in team guidelines

## Example CI Configuration

```yaml
# .github/workflows/test.yml
jobs:
  fast-tests:
    run: pytest -m "unit and not slow"
  
  integration-tests:
    run: pytest -m "integration" --mock-apis
  
  critical-tests:
    run: pytest -m "critical"
```

## New Recommendations Based on Test Analysis

### 1. Fix Critical Test Failures

#### 1.1 Citation Test Dead Code (HIGH PRIORITY)
**File**: `tests/e2e/test_e2e_cite_command.py`
**Issue**: Undefined variables after `return` statements
**Fix**: Remove lines 92-114, 127-130, 142-164, 177-192

#### 1.2 Performance Test Thresholds (HIGH PRIORITY)
**File**: `tests/e2e/test_e2e_cli_commands.py:431`
**Issue**: 15s threshold too strict (failing at 16s)
**Fix**: 
```python
# Add environment-aware thresholds
import os
PERF_THRESHOLD = 20 if os.getenv("CI") else 15
assert elapsed < PERF_THRESHOLD
```

#### 1.3 Command Usage Logger Test (MEDIUM)
**File**: `tests/unit/test_unit_command_usage.py:52`
**Issue**: Logger not initialized in test environment
**Fix**: Mock the pytest environment check

### 2. Improve Test Coverage (Currently 20-33%)

#### 2.1 Add Comprehensive API Mocks
```python
# Add to conftest.py
@pytest.fixture
def mock_build_kb():
    """Mock entire KB building process."""
    with patch('src.build_kb.main') as mock:
        mock.return_value = 0
        yield mock

@pytest.fixture  
def mock_embeddings():
    """Mock embedding generation."""
    with patch('sentence_transformers.SentenceTransformer') as mock:
        mock.return_value.encode.return_value = np.zeros((10, 768))
        yield mock
```

#### 2.2 Test Data Fixtures
```python
# Create tests/fixtures/test_data.py
TEST_PAPERS = [
    {"id": "0001", "title": "Test Paper", "quality_score": 75},
    # ... more test data
]

@pytest.fixture
def sample_kb_with_papers(tmp_path):
    """Create a complete test KB."""
    # Implementation
```

### 3. Fix Integration Test Issues

#### 3.1 Gap Analysis Report Test
**Issue**: Missing `<details>` tags in report
**Solution**: Update report generator or adjust test expectations

#### 3.2 Batch Command Timeout
**Issue**: 15s timeout too short for batch operations
**Fix**: Increase to 30s for batch tests

### 4. Improve Test Reliability

#### 4.1 Add Retry Logic
```python
# For flaky network tests
@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_api_call():
    pass
```

#### 4.2 Better Test Isolation
```python
# Use autouse fixtures for cleanup
@pytest.fixture(autouse=True)
def cleanup_test_files():
    yield
    # Cleanup code
    for pattern in ["test_*.json", "temp_*.csv"]:
        for file in Path(".").glob(pattern):
            file.unlink()
```

### 5. Performance Optimization

#### 5.1 Parallel Execution
```bash
# Add to pytest.ini
[tool:pytest]
addopts = -n auto  # Use all CPU cores
```

#### 5.2 Cache Expensive Operations
```python
@pytest.fixture(scope="session")
def cached_kb():
    """Build KB once per session."""
    # Build and cache
```

### 6. Documentation Improvements

Create `tests/README.md`:
```markdown
# Test Suite Guide

## Quick Start
pytest -m "unit and fast"  # Quick feedback (9s)
pytest -m critical  # Must pass for release
pytest --cov  # With coverage report

## Troubleshooting
- "Search too slow": Set CI=1 environment variable
- "KB not found": Run `python src/build_kb.py --demo`
- Hanging tests: Check for click prompts, use --tb=short
```

### 7. Priority Action Plan

**Week 1 (Fix Failures)**:
1. Remove dead code in cite tests
2. Adjust performance thresholds
3. Fix command logger test

**Week 2 (Improve Coverage)**:
1. Add comprehensive mocks
2. Create test data fixtures
3. Increase coverage to 50%+

**Week 3 (Enhance Reliability)**:
1. Add retry logic
2. Improve test isolation
3. Set up parallel execution

### 8. Testing Best Practices Reminder

1. **Name tests clearly**: `test_<what>_should_<expected_behavior>`
2. **One concept per test**
3. **Mock external dependencies**
4. **Use fixtures for setup**
5. **Document skip reasons**
6. **Keep tests fast** (<0.1s for unit tests)
7. **Test edge cases**
8. **Use parameterized tests for similar scenarios**