# Test Organization

This directory contains the test suite for the Research Assistant project, organized following pytest best practices.

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and test configuration
├── pytest.ini                 # Pytest configuration settings
├── utils.py                   # Shared test utilities and helpers
├── README.md                  # This documentation
├── fixtures/                  # Test data and mock files
│   └── mock_pdfs/
├── unit/                      # Unit tests (fast, isolated)
│   ├── test_build_kb.py          # KB building unit tests
│   ├── test_build_kb_safety.py   # KB safety feature tests
│   ├── test_cli_comprehensive.py # Comprehensive CLI functionality
│   ├── test_cli_core.py          # Core CLI operations
│   ├── test_kb_index_full.py     # KB index unit tests
│   ├── test_quality_scoring.py   # Quality scoring algorithm
│   └── test_search_parametrized.py # Parametrized search tests
├── integration/               # Integration tests (component interactions)
│   ├── test_batch_operations.py  # Batch command workflows
│   ├── test_incremental_updates_full.py # Incremental update workflows
│   ├── test_kb_building.py       # Full KB building process
│   ├── test_reports_full.py      # Report generation workflows
│   └── test_search_workflow.py   # Search workflow integration
├── e2e/                       # End-to-end tests (full system)
│   ├── test_cite_command_e2e.py  # Citation command E2E tests
│   └── test_cli_commands.py      # Critical CLI functionality
└── performance/               # Performance and benchmark tests
    └── test_benchmarks.py        # Performance benchmarks
```

## Test Categories

### Unit Tests (`unit/`)
**Purpose**: Test individual functions and classes in isolation
- **Fast execution**: Each test < 1 second
- **No external dependencies**: Mock all I/O, APIs, file operations
- **High coverage**: Focus on edge cases and error conditions

**Key Files**:
- `test_cli_comprehensive.py`: Core CLI functionality, quality scoring
- `test_search_parametrized.py`: Search filtering with multiple parameter combinations
- `test_build_kb.py`: KB building components (PDF extraction, embeddings)
- `test_quality_scoring.py`: Paper quality scoring algorithm

### Integration Tests (`integration/`)
**Purpose**: Test component interactions and workflows
- **Medium execution time**: 5-15 seconds per test
- **Mock external services**: Mock Zotero, file system when appropriate
- **Real component interaction**: Test actual class interactions

**Key Files**:
- `test_search_workflow.py`: Complete search workflows with quality filtering
- `test_batch_operations.py`: Batch command execution and preset workflows
- `test_kb_building.py`: Full KB building process integration
- `test_incremental_updates_full.py`: Incremental update workflows

### End-to-End Tests (`e2e/`)
**Purpose**: Test complete user workflows through CLI
- **Slower execution**: 10-30 seconds per test
- **Real CLI execution**: Test actual command-line interface
- **Critical functionality**: Must-work features that users depend on

**Key Files**:
- `test_cli_commands.py`: Critical CLI commands (search, info, diagnose)
- `test_cite_command_e2e.py`: Citation generation workflows

### Performance Tests (`performance/`)
**Purpose**: Benchmark performance and detect regressions
- **Timing focused**: Measure execution time and memory usage
- **Large datasets**: Test with realistic data sizes
- **Regression detection**: Ensure performance doesn't degrade

## Running Tests

### By Category

```bash
# Unit tests (fast, run frequently)
pytest tests/unit/ -v

# Integration tests (medium speed)
pytest tests/integration/ -v

# End-to-end tests (slower, critical functionality)
pytest tests/e2e/ -v

# Performance tests (benchmarking)
pytest tests/performance/ -v
```

### All Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run with verbose output
pytest tests/ -v
```

### Specific Tests

```bash
# Run specific test file
pytest tests/unit/test_cli_comprehensive.py

# Run specific test class
pytest tests/e2e/test_cli_commands.py::TestCriticalE2EFunctionality

# Run specific test
pytest tests/e2e/test_cli_commands.py::TestCriticalE2EFunctionality::test_kb_search_doesnt_crash

# Run tests matching pattern
pytest tests/ -k "search"
```

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto

# Run specific categories in parallel
pytest tests/unit/ -n 4
```

## Test Status

### ✅ Currently Working (193 total tests)
- **Unit Tests**: 7 files - Core functionality tests
- **Integration Tests**: 4/5 files working - Some batch format issues
- **E2E Tests**: ✅ All critical tests passing
- **Performance Tests**: 1 file - Benchmarking tests

### 🔧 Known Issues
- Some integration tests expect different batch command output format
- Parametrized search tests may have parameter mismatches
- Mock setup complexity in some integration tests

## Test Configuration

### `pytest.ini`
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --strict-markers --disable-warnings
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
```

### `conftest.py`
Contains shared fixtures for:
- Mock knowledge base structures
- Test data creation
- Common setup/teardown operations

## Test Best Practices

### 1. Test Organization
- **Unit tests**: Test single functions/methods in isolation
- **Integration tests**: Test component interactions
- **E2E tests**: Test complete user workflows
- **Performance tests**: Measure speed and resource usage

### 2. Naming Conventions
```python
def test_function_behavior_when_condition():
    """Test that function behaves correctly when condition is met."""
    # Arrange
    # Act  
    # Assert
```

### 3. Fixtures and Mocking
```python
@pytest.fixture
def mock_kb(tmp_path):
    """Create a mock knowledge base for testing."""
    # Setup test KB structure
    return kb_path

@patch("src.cli.SentenceTransformer")
def test_search_functionality(mock_transformer):
    # Test with mocked dependencies
```

### 4. Test Documentation
- Clear docstrings explaining test purpose
- Use Given/When/Then format for complex tests
- Document any special setup requirements

## Coverage Goals

- **Unit Tests**: 90%+ coverage of core functions
- **Integration Tests**: Cover all major workflows
- **E2E Tests**: Cover all CLI commands and critical paths
- **Overall**: 80%+ code coverage minimum

## Adding New Tests

### For New Features
1. **Start with unit tests**: Test individual functions
2. **Add integration tests**: Test component interactions
3. **Add E2E tests**: Test user-facing functionality
4. **Consider performance**: Add benchmarks for critical paths

### Test Placement Guidelines
- **`unit/`**: Testing individual functions, classes, methods
- **`integration/`**: Testing workflows, component interactions
- **`e2e/`**: Testing CLI commands, user workflows
- **`performance/`**: Benchmarking, performance regression tests

### Before Committing
```bash
# Run relevant test categories
pytest tests/unit/ tests/e2e/ -v

# Check critical functionality
pytest tests/e2e/test_cli_commands.py::TestCriticalE2EFunctionality -v

# Verify no regressions
python src/cli.py search "test" --export validation.csv
```

This test organization supports safe refactoring by providing clear separation of concerns and comprehensive coverage of the Research Assistant functionality.