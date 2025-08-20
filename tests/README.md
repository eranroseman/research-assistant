# Test Organization

This directory contains the test suite for the Research Assistant project, organized following pytest best practices.

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and test configuration
├── test_critical.py            # Critical functionality that must never break
├── test_incremental_updates.py # Incremental update and caching tests
├── test_kb_index.py            # O(1) lookup and index functionality tests
├── test_reports.py             # Report generation tests
└── test_v4_features.py        # Version 4.0 specific features
```

## Test Categories

### Core Tests (`test_critical.py`)
- **Purpose**: Test critical functionality that must never fail
- **Classes**:
  - `TestCriticalFunctionality`: Core operations (build, search, PDF extraction)
  - `TestCacheIntegrity`: Cache corruption handling
  - `TestSearchFilters`: Search filtering (year, study type)
  - `TestKnowledgeBaseIntegrity`: KB structure and performance

### Feature Tests

#### `test_incremental_updates.py`
- Tests for smart incremental updates
- Embedding reuse and optimization
- Cache management during updates

#### `test_kb_index.py`
- O(1) paper lookups by ID
- Author search functionality
- Year range filtering
- Index consistency validation

#### `test_reports.py`
- Report generation to `reports/` directory
- Small PDFs report
- Missing PDFs report
- CSV export functionality

#### `test_v4_features.py`
- Version 4.0 specific features
- Quality scoring system
- Smart search with chunking
- Section retrieval
- Diagnose command

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run specific test file:
```bash
pytest tests/test_critical.py
```

### Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run specific test class:
```bash
pytest tests/test_critical.py::TestCriticalFunctionality
```

### Run specific test:
```bash
pytest tests/test_critical.py::TestCriticalFunctionality::test_kb_search_doesnt_crash
```

## Test Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Fixtures**: Use fixtures in `conftest.py` for shared test data
3. **Mocking**: Mock external dependencies (APIs, file I/O) when appropriate
4. **Clear Names**: Test names should clearly describe what they test
5. **Fast Tests**: Keep unit tests fast (<1 second each)
6. **Documentation**: Add docstrings explaining complex test logic

## Coverage Goals

- **Minimum**: 80% code coverage
- **Critical paths**: 100% coverage for critical functionality
- **New features**: All new code should include tests

## Adding New Tests

When adding new functionality:
1. Add unit tests to the appropriate test file
2. If creating a new module, create a corresponding test file
3. Update this README if adding new test categories
4. Ensure all tests pass before committing
