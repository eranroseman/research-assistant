# Research Assistant - Pragmatic Improvement Plan

## Executive Summary

This document outlines a **5-day improvement plan** that delivers maximum value with minimal risk. We focus on fixing critical issues first, then reducing complexity only where it causes real pain. No over-engineering, no breaking changes, just practical improvements.

**Key Principle**: Fix what's broken, improve what's painful, leave what works.

## Current State Analysis

### Critical Issues (Must Fix)

1. **API Failures**: v4.4-v4.6 rate limiting causes build failures
2. **Lost Work**: No checkpoint recovery when builds fail
3. **4,293-line Monster**: `build_kb.py` is unmaintainable

### Non-Critical Issues (Can Wait)

- Test suite is large but works
- Some code duplication exists but doesn't block work
- Import patterns are inconsistent but functional

## Implementation Plan

### Day 1: Stop the Bleeding (4-6 hours)

#### 1.1 Integrate Existing API Solution

**File**: `src/api_utils.py` (already exists)
**Action**: Replace inline API calls in `build_kb.py`
**Risk**: Zero - code is tested and working

```python
# Before (in build_kb.py)
response = requests.get(url)  # Fails on rate limits

# After
from src.api_utils import sync_api_request_with_retry
response = sync_api_request_with_retry(url)  # Handles retries
```

**Validation**: Run `python src/build_kb.py --demo` with 5 papers

#### 1.2 Add Minimal Checkpointing

**Location**: `build_kb.py` (30 lines added)
**Risk**: Very low - simple JSON file

```python
def build_knowledge_base(papers, checkpoint_interval=500):
    checkpoint_file = Path(".checkpoint")
    start_idx = 0

    # Resume from checkpoint
    if checkpoint_file.exists():
        with open(checkpoint_file) as f:
            start_idx = json.load(f).get('last_processed', 0)
        print(f"Resuming from paper {start_idx}")

    for i, paper in enumerate(papers[start_idx:], start=start_idx):
        try:
            process_paper(paper)

            # Save checkpoint
            if (i + 1) % checkpoint_interval == 0:
                with open(checkpoint_file, 'w') as f:
                    json.dump({'last_processed': i + 1}, f)

        except Exception as e:
            print(f"Failed on paper {i}: {e}")
            continue

    # Clean up on success
    checkpoint_file.unlink(missing_ok=True)
```

**Validation**: Kill process mid-build, restart, verify resume works

### Day 2-3: Split the Monster (1.5 days)

#### 2.1 Extract Quality Scoring

**New File**: `src/kb_quality.py` (~800 lines)
**Move from `build_kb.py`**:

- `calculate_quality_score()`
- `enhance_quality_with_api()`
- Quality-related constants and helpers

```python
# src/kb_quality.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class QualityScore:
    score: float
    explanation: str
    components: dict

def calculate_quality_score(paper: dict, api_data: Optional[dict] = None) -> QualityScore:
    """Calculate paper quality score with optional API enhancement."""
    # Existing logic moved here
    pass
```

#### 2.2 Extract FAISS Indexing

**New File**: `src/kb_indexer.py` (~1,000 lines)
**Move from `build_kb.py`**:

- FAISS index creation
- Embedding generation
- Index saving/loading

```python
# src/kb_indexer.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class KBIndexer:
    def __init__(self, model_name: str, use_gpu: bool = True):
        self.model = SentenceTransformer(model_name)
        self.use_gpu = use_gpu and torch.cuda.is_available()

    def create_index(self, papers: list) -> faiss.Index:
        """Create FAISS index from papers."""
        # Existing logic moved here
        pass
```

**Result**: `build_kb.py` reduced from 4,293 to ~2,500 lines (42% reduction)

### Day 4: Clean Up Imports (3 hours)

#### 4.1 Fix Dual Import Pattern

**Current Problem**:

```python
# Inconsistent everywhere
try:
    from src.config import Config
except ImportError:
    from config import Config
```

**Solution**: Single pattern everywhere

```python
from src.config import Config  # Always use src prefix
```

**Implementation**:

```bash
# Find all dual imports
grep -r "except ImportError" src/

# Replace with single pattern
find src -name "*.py" -exec sed -i 's/try:.*from config/from src.config/g' {} \;
```

### Day 5: Testing & Documentation (1 day)

#### 5.1 Update Critical Tests

Focus only on tests that break due to changes:

- Tests importing from `build_kb.py` that need `kb_quality.py`
- Tests for checkpoint recovery (add 2-3 new tests)

#### 5.2 Update Documentation

- Update README with new file structure
- Document checkpoint recovery
- Add migration notes for existing users

## What We're NOT Doing (And Why)

### Not Creating Abstract Base Classes

**Why**: Adds complexity without solving real problems

```python
# NOT doing this
class AbstractQualityScorer(ABC):
    @abstractmethod
    def calculate_score(self, paper: Paper) -> QualityScore:
        pass
```

### Not Implementing Dependency Injection

**Why**: Module-level instances work fine

```python
# NOT doing this
class ServiceContainer:
    def __init__(self):
        self.register('api_client', APIClient)
        self.register('kb_builder', KBBuilder)
```

### Not Splitting Into 11+ Files

**Why**: 3-4 files solve 80% of the problem

- `build_kb.py` → 3 files is enough
- Other files are manageable as-is

### Not Refactoring Working Code

**Why**: If it works and isn't causing pain, leave it

- `cli.py` at 2,625 lines is large but functional
- Search functionality works well
- Gap analysis is stable

## Success Metrics

### Must Achieve (Day 1)

✅ Zero API failures on builds
✅ Checkpoint recovery works
✅ No breaking changes

### Should Achieve (Day 2-3)

✅ `build_kb.py` under 2,500 lines
✅ Clear separation of concerns
✅ Tests still pass

### Nice to Have (Day 4-5)

✅ Consistent imports
✅ Updated documentation
✅ Cleaner test structure

## Risk Mitigation

### Rollback Plan

Each change is isolated and reversible:

1. API changes: Keep original code commented
2. Checkpoints: Can disable with flag
3. File splits: Git revert if needed
4. Import cleanup: Sed script to reverse

### Testing Strategy

- Run after each major change
- Focus on integration tests
- Use `--demo` mode for quick validation

## Implementation Checklist

### Day 1 - Critical Fixes

- [ ] Backup current codebase
- [ ] Integrate `api_utils.py` into `build_kb.py`
- [ ] Add checkpoint system (30 lines)
- [ ] Test with 5-paper demo
- [ ] Test with full build (interrupt and resume)

### Day 2-3 - Complexity Reduction

- [ ] Create `src/kb_quality.py`
- [ ] Move quality scoring logic
- [ ] Create `src/kb_indexer.py`
- [ ] Move FAISS/embedding logic
- [ ] Update imports in `build_kb.py`
- [ ] Run full test suite

### Day 4 - Polish

- [ ] Fix dual import patterns
- [ ] Update affected tests
- [ ] Verify no import errors

### Day 5 - Documentation

- [ ] Update README
- [ ] Document checkpoint recovery
- [ ] Create migration guide
- [ ] Final test run

## Expected Outcomes

### Immediate Benefits (Day 1)

- **100% build success rate** (vs current failures)
- **Zero data loss** on interruptions
- **Resume capability** saves hours

### Week 1 Benefits

- **42% reduction** in largest file
- **Easier debugging** with separated concerns
- **Faster development** with modular code

### What Won't Change

- No breaking API changes
- No new dependencies
- No configuration changes
- No data format changes

## Alternative: Even More Minimal (2 Days)

If 5 days is too much, here's a 2-day version:

### Day 1: Fix Critical Issues

1. Integrate `api_utils.py` (2 hours)
2. Add checkpoints (1 hour)
3. Test thoroughly (1 hour)

### Day 2: Quick Split

1. Extract only `kb_quality.py` (4 hours)
2. Update tests (2 hours)

**Result**: 80% of critical value in 40% of time

## Decision Framework

### Choose 5-Day Plan If

- You have a week available
- Want sustainable improvements
- Team needs cleaner code

### Choose 2-Day Plan If

- Need immediate relief
- Limited time available
- Can revisit later

### Choose Status Quo If

- System is working adequately
- Major changes planned soon
- Risk tolerance is zero

## Conclusion

This pragmatic plan delivers:

1. **Immediate stability** (Day 1)
2. **Improved maintainability** (Days 2-3)
3. **Consistent codebase** (Days 4-5)

No over-engineering. No unnecessary abstractions. Just practical improvements that solve real problems.

**Recommended Action**: Start with Day 1 fixes today. They're low-risk and high-value. Evaluate after Day 1 whether to continue with the full plan.
