# E2E User Journey Testing Guide

## Overview

The E2E journey tests simulate complete user workflows from start to finish, testing the integration of all components in realistic scenarios. These tests provide high confidence that the system works correctly for real users.

## Journey Test Coverage

### Journey 1: First-Time Researcher
**Purpose**: Validate new user onboarding and basic functionality
**Coverage**: 
- System setup and initialization
- Demo KB creation
- Basic search operations
- Paper retrieval
- Export functionality

**Key Assertions**:
- KB builds successfully with demo data
- Search returns relevant results
- Quality scores display correctly
- Export creates valid files

### Journey 2: Daily Research Workflow
**Purpose**: Test routine research tasks and advanced features
**Coverage**:
- Incremental KB updates
- Quality-filtered searches
- Smart search with chunking
- Citation generation
- Batch operations

**Key Assertions**:
- Updates preserve existing data
- Quality filters work correctly
- Batch commands execute in order
- Citations format properly

### Journey 3: Literature Review Project
**Purpose**: Validate systematic review capabilities
**Coverage**:
- External paper discovery
- Gap analysis
- Multi-strategy search
- Comprehensive exports
- Review report generation

**Key Assertions**:
- Discovery finds relevant external papers
- Gap analysis identifies missing work
- Multiple search strategies combine correctly
- Exports contain complete data

### Journey 4: Quality-Focused Research
**Purpose**: Test quality assessment and filtering
**Coverage**:
- Quality distribution analysis
- Strict quality thresholds
- Score upgrades
- Quality-based filtering
- High-quality exports

**Key Assertions**:
- Quality scores calculate correctly
- Filters exclude low-quality papers
- Upgrades improve scores
- Exports respect quality thresholds

### Journey 5: Collaborative Research
**Purpose**: Validate multi-user workflows
**Coverage**:
- KB export for sharing
- KB import and merging
- Deduplication
- Combined searching
- Collaborative citations

**Key Assertions**:
- Export preserves all data
- Import handles duplicates
- Merged KB searchable
- Citations include all sources

### Journey 6: Error Recovery & Resilience
**Purpose**: Test system robustness
**Coverage**:
- Corrupted KB handling
- Interrupted build recovery
- API failure fallbacks
- Rate limiting management
- Backup restoration

**Key Assertions**:
- Corruption detected gracefully
- Checkpoints enable recovery
- Fallbacks maintain functionality
- Backups restore successfully

## Test Structure

```python
tests/e2e/
├── test_e2e_user_journeys.py      # Main journey implementations
├── test_e2e_journey_fixtures.py   # Shared fixtures and utilities
└── README_JOURNEYS.md             # This documentation
```

## Running Journey Tests

### Run all journey tests:
```bash
pytest tests/e2e/test_e2e_user_journeys.py -v
```

### Run specific journey:
```bash
pytest tests/e2e/test_e2e_user_journeys.py::TestJourney1_FirstTimeResearcher -v
```

### Run with performance profiling:
```bash
pytest tests/e2e/test_e2e_user_journeys.py --profile -v
```

### Generate coverage report:
```bash
pytest tests/e2e/test_e2e_user_journeys.py --cov=src --cov-report=html
```

## Test Data Management

### Mock Papers
The `JourneyTestData` class generates realistic mock papers with:
- Varied quality scores (40-95)
- Multiple authors and venues
- Realistic citation counts
- Complete section content

### Batch Commands
Test batch operations with generated command sequences:
```python
commands = JourneyTestData.generate_batch_commands(
    ["search", "get", "cite", "export"]
)
```

## Validation Utilities

### Search Result Validation
```python
JourneyValidator.validate_search_results(
    results=output,
    expected_papers=5,
    required_fields=["Title", "Quality", "Year"]
)
```

### Export File Validation
```python
JourneyValidator.validate_export_file(
    export_path=Path("export.csv"),
    min_papers=10,
    required_columns=["paper_id", "title", "quality_score"]
)
```

## Performance Metrics

### Journey Profiling
Track journey performance with the `JourneyProfiler`:
```python
profiler = JourneyProfiler()
profiler.start_journey("first_time_setup")
profiler.record_step("build_kb", success=True, duration_ms=5000)
profiler.end_journey("first_time_setup")
report = profiler.generate_report()
```

### Expected Performance Targets
| Journey | Target Duration | Success Rate |
|---------|----------------|--------------|
| First-Time Setup | < 2 min | > 95% |
| Daily Workflow | < 1 min | > 98% |
| Literature Review | < 5 min | > 90% |
| Quality Focus | < 3 min | > 93% |
| Collaborative | < 1.5 min | > 92% |
| Error Recovery | < 2.5 min | > 88% |

## Best Practices

### 1. Use Fixtures Consistently
Always use the `journey_test_env` fixture for environment setup:
```python
def test_journey(journey_test_env):
    kb_dir = journey_test_env["paths"]["kb"]
    runner = journey_test_env["runner"]
    ...
```

### 2. Mock External Services
Use `mock_external_services` fixture for external dependencies:
```python
def test_with_apis(mock_external_services):
    zotero = mock_external_services["zotero"]
    semantic = mock_external_services["semantic_scholar"]
    ...
```

### 3. Validate Comprehensively
Check both success conditions and output format:
```python
assert result.exit_code == 0  # Command succeeded
assert "expected text" in result.output  # Output contains expected content
assert validator.validate_search_results(result.output, 5)  # Structured validation
```

### 4. Profile Critical Paths
Track performance for user-facing operations:
```python
profiler.record_step("search", success=True, duration_ms=response_time)
```

### 5. Test Error Paths
Include negative test cases:
```python
# Test with corrupted data
corrupted_kb.write_text("invalid json")
result = runner.invoke(cli, ["info"])
assert "error" in result.output.lower()
```

## Troubleshooting

### Common Issues

**Tests hang during KB operations**
- Check mock responses are configured
- Verify timeouts are set appropriately
- Ensure no blocking I/O operations

**Inconsistent test results**
- Use fixed random seeds for data generation
- Mock time-dependent operations
- Clear caches between tests

**Path-related failures**
- Always use tmp_path fixture
- Use absolute paths in tests
- Clean up temporary files

## Extending Journey Tests

### Adding New Journeys
1. Create new test class inheriting from `TestUserJourneys`
2. Implement test methods following naming convention
3. Use existing fixtures and validators
4. Document journey purpose and coverage

### Adding Validation Rules
1. Extend `JourneyValidator` class
2. Add new validation methods
3. Include in relevant journey tests
4. Update documentation

### Performance Benchmarks
1. Add metrics to `JourneyProfiler`
2. Set performance targets
3. Include in CI/CD pipeline
4. Monitor trends over time

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run E2E Journey Tests
  run: |
    pytest tests/e2e/test_e2e_user_journeys.py \
      --cov=src \
      --cov-report=xml \
      --junit-xml=journey-results.xml \
      -v
  timeout-minutes: 15
```

### Pre-commit Hook
```yaml
- repo: local
  hooks:
    - id: journey-tests
      name: E2E Journey Tests
      entry: pytest tests/e2e/test_e2e_user_journeys.py::TestJourney1_FirstTimeResearcher
      language: system
      pass_filenames: false
      always_run: true
```

## Maintenance

### Regular Updates
- Review and update mock data quarterly
- Adjust performance targets based on metrics
- Add new journeys for new features
- Remove obsolete test scenarios

### Test Health Monitoring
- Track flaky test frequency
- Monitor execution time trends
- Review failure patterns
- Update validation rules as needed