# Research Assistant Test Suite Guide

This directory contains the test suite for the Research Assistant project, organized following pytest best practices with consistent naming conventions.

## Quick Start

```bash
# Run fast unit tests (9 seconds)
pytest tests/unit/ -v

# Run critical tests that must pass for release
pytest -m critical

# Run all tests with coverage report
pytest tests/ --cov=src --cov-report=term-missing

# Skip slow tests for quick feedback
pytest -m "not slow"
```

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and test configuration
├── pytest.ini                 # Pytest configuration settings
├── utils.py                   # Shared test utilities and helpers
├── README.md                  # This documentation
├── fixtures/                  # Test data and mock files
│   └── mock_pdfs/
├── unit/                      # Unit tests (123 tests, fast, isolated)
│   ├── test_unit_citation_system.py      # IEEE citation formatting
│   ├── test_unit_cli_batch_commands.py   # CLI batch operations
│   ├── test_unit_cli_interface.py        # CLI utility functions
│   ├── test_unit_knowledge_base.py       # KB building, indexing, caching
│   ├── test_unit_quality_scoring.py      # Paper quality algorithms
│   ├── test_unit_search_engine.py        # Search, embedding, ranking
│   └── test_unit_command_usage.py        # Command usage logging
├── integration/               # Integration tests (40 tests, component interactions)
│   ├── test_integration_batch_operations.py    # Batch command workflows
│   ├── test_integration_incremental_updates.py # Incremental update workflows
│   ├── test_integration_kb_building.py         # Full KB building process
│   ├── test_integration_reports.py             # Report generation workflows
│   └── test_integration_search_workflow.py     # Search workflow integration
├── e2e/                       # End-to-end tests (23 tests, full system)
│   ├── test_e2e_cite_command.py          # Citation command E2E tests
│   └── test_e2e_cli_commands.py          # Critical CLI functionality
└── performance/               # Performance tests (7 tests, benchmarks)
    └── test_performance_benchmarks.py    # Speed and memory benchmarks
```

## File Naming Convention

**Pattern**: `test_{type}_{component/feature}.py`

This naming scheme provides several benefits:
- **Immediate clarity**: Test type and component are obvious from filename
- **Easy filtering**: Run specific test types with `pytest tests/unit/test_unit_*.py`
- **Scalable organization**: Pattern supports adding new tests consistently
- **IDE-friendly**: Better sorting and grouping in file explorers

## Test Categories

### Unit Tests (`unit/`)
**Purpose**: Test individual functions and classes in isolation
- **Fast execution**: Each test < 1 second
- **No external dependencies**: Mock all I/O, APIs, file operations
- **High coverage**: Focus on edge cases and error conditions

**Key Files**:
- `test_unit_cli_batch_commands.py`: Core CLI functionality, batch operations
- `test_unit_search_engine.py`: Search filtering with multiple parameter combinations
- `test_unit_knowledge_base.py`: KB building components (PDF extraction, embeddings)
- `test_unit_quality_scoring.py`: Paper quality scoring algorithm
- `test_unit_citation_system.py`: IEEE citation formatting
- `test_unit_cli_interface.py`: CLI utility functions and paper quality estimation
- `test_unit_command_usage.py`: Command usage logging functionality

### Integration Tests (`integration/`)
**Purpose**: Test component interactions and workflows
- **Medium execution time**: 5-15 seconds per test
- **Mock external services**: Mock Zotero, file system when appropriate
- **Real component interaction**: Test actual class interactions

**Key Files**:
- `test_integration_search_workflow.py`: Complete search workflows with quality filtering
- `test_integration_batch_operations.py`: Batch command execution and preset workflows
- `test_integration_kb_building.py`: Full KB building process integration
- `test_integration_incremental_updates.py`: Incremental update workflows
- `test_integration_reports.py`: Report generation workflows

### End-to-End Tests (`e2e/`)
**Purpose**: Test complete user workflows through CLI
- **Slower execution**: 10-30 seconds per test
- **Real CLI execution**: Test actual command-line interface
- **Critical functionality**: Must-work features that users depend on

**Key Files**:
- `test_e2e_cli_commands.py`: Critical CLI commands (search, info, diagnose)
- `test_e2e_cite_command.py`: Citation generation workflows

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
pytest tests/unit/test_unit_cli_batch_commands.py

# Run specific test class
pytest tests/e2e/test_e2e_cli_commands.py::TestCriticalE2EFunctionality

# Run specific test
pytest tests/e2e/test_e2e_cli_commands.py::TestCriticalE2EFunctionality::test_kb_search_doesnt_crash

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

### Current Test Suite (450+ tests)
- **Unit Tests**: 278 tests - Fast, isolated component tests (99.6% passing)
- **Integration Tests**: 127 tests - Workflow validation (96.9% passing)
- **E2E Tests**: 46 tests - Full CLI testing (95.7% passing)
- **Performance Tests**: Benchmarking and timing tests

### Known Issues and Solutions

#### "Search too slow" Test Failure
**Problem**: Performance test fails with search >15s
**Solution**: Set `CI=1` environment variable for CI (uses 20s threshold)

#### "KB not found" Errors
**Problem**: Tests skip or fail due to missing knowledge base
**Solution**: Run `python src/build_kb.py --demo` to build test KB

#### Hanging Tests with Click Commands
**Problem**: Some click-based tests hang indefinitely
**Solution**: Tests marked to skip problematic interactions, use `--tb=short`

#### Command Timeout in Batch Tests
**Problem**: Batch operations timeout at 15s
**Solution**: Already increased to 30s for batch operations

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
# Run pre-commit checks
mypy src/
ruff check src/ tests/ --fix

# Run relevant test categories
pytest tests/unit/ tests/e2e/ -v

# Check critical functionality
pytest tests/e2e/test_e2e_cli_commands.py::TestCriticalE2EFunctionality -v

# Verify no regressions
python src/cli.py search "test" --export validation.csv
```

## Test Markers

Use pytest markers to categorize and filter tests:

```python
@pytest.mark.unit           # Fast, isolated tests
@pytest.mark.integration    # Component interaction tests
@pytest.mark.e2e           # End-to-end tests
@pytest.mark.performance   # Speed benchmarks
@pytest.mark.slow          # Tests taking >5 seconds
@pytest.mark.critical      # Must pass for release
@pytest.mark.requires_kb   # Needs knowledge base
@pytest.mark.requires_api  # Needs external API
```

Run tests by marker:
```bash
pytest -m "unit and not slow"     # Fast unit tests
pytest -m critical                 # Release-critical tests
pytest -m "not requires_api"       # Offline tests only
```

## Debugging Failed Tests

```bash
# Verbose output
pytest tests/unit/test_failing.py -vv

# Show print statements
pytest tests/unit/test_failing.py -s

# Drop into debugger on failure
pytest tests/unit/test_failing.py --pdb

# Shorter traceback
pytest tests/unit/test_failing.py --tb=short

# Show local variables
pytest tests/unit/test_failing.py -l
```

## CI/CD Integration

For GitHub Actions or other CI systems:

```yaml
env:
  CI: "1"  # Enables CI-specific thresholds

steps:
  - name: Lint
    run: |
      mypy src/
      ruff check src/ tests/

  - name: Critical Tests
    run: pytest -m critical

  - name: Full Test Suite
    run: pytest tests/ --cov=src
```

This test organization supports safe refactoring by providing clear separation of concerns and comprehensive coverage of the Research Assistant functionality.
