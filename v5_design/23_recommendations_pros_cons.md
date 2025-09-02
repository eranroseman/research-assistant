# Batch Size Recommendations: Pros and Cons Analysis

## Date: December 3, 2024

## Recommendation 1: Standardize by Time (2-minute intervals)

### Pros ✅
- **Predictable progress saves** - Users know data is saved every 2 minutes
- **Consistent across all services** - Same checkpoint rhythm regardless of API speed
- **Adapts to performance variations** - Slow network? Still saves every 2 minutes
- **Easier monitoring** - Can set alerts for "no checkpoint in 5 minutes"
- **Better for mixed-speed pipelines** - Fast and slow stages checkpoint uniformly

### Cons ❌
- **Variable data per checkpoint** - Fast APIs might save 500 papers, slow ones only 20
- **Checkpoint file size inconsistency** - Harder to predict disk usage
- **May interrupt batch operations** - Could checkpoint mid-batch for bulk APIs
- **Complex resumption** - Need to track partial batch states
- **More code changes required** - Every enricher needs timer logic

### Implementation Risk: **Medium**
```python
# Could complicate batch processing
if time_elapsed > 120 and in_middle_of_batch:
    # Awkward: save partial batch or wait?
```

---

## Recommendation 2: Increase arXiv batch from 10 to 30

### Pros ✅
- **3x fewer checkpoint writes** - Reduces I/O overhead significantly
- **Still reasonable recovery time** - Only 90 seconds of work to redo
- **Better disk performance** - Fewer file system operations
- **Cleaner checkpoint files** - Less fragmentation

### Cons ❌
- **3x more work lost on failure** - 30 papers vs 10 to re-process
- **Longer wait for first checkpoint** - 90 seconds vs 30 seconds
- **User perception** - Might seem "stuck" for longer periods
- **Memory usage** - Holding 30 papers in memory vs 10

### Implementation Risk: **Low**
```python
# Simple change
BATCH_SIZE = 30  # was 10
```

---

## Recommendation 3: Increase CrossRef batch from 50 to 100

### Pros ✅
- **Better API efficiency** - Fewer checkpoint interruptions
- **CrossRef is reliable** - Low failure risk, can afford larger batches
- **Faster overall processing** - Less checkpoint overhead
- **Already proven** - Semantic Scholar uses larger batches successfully

### Cons ❌
- **Doubles potential work loss** - 100 papers to reprocess on failure
- **Larger checkpoint files** - More memory/disk per save
- **May hit API rate limits** - 100 rapid requests might trigger throttling
- **Harder debugging** - More papers to examine if something goes wrong

### Implementation Risk: **Low-Medium**
```python
# Need to monitor for rate limit issues
if batch_size == 100 and getting_429_errors:
    # May need adaptive reduction
```

---

## Recommendation 4: Adaptive Checkpointing (time + count hybrid)

### Pros ✅
- **Best of both worlds** - Saves on time OR count, whichever comes first
- **Optimal for all speeds** - Fast APIs use count, slow APIs use time
- **Failure recovery bounded** - Maximum 2 minutes OR batch size of work lost
- **Self-tuning** - Automatically adjusts to actual performance
- **Production-ready pattern** - Common in enterprise systems

### Cons ❌
- **More complex logic** - Two conditions to track and test
- **Harder to predict** - Checkpoint timing becomes variable
- **Potential for frequent saves** - If both thresholds are low
- **More state to maintain** - Need to track time AND count
- **Testing complexity** - More edge cases to consider

### Implementation Risk: **Medium-High**
```python
def should_checkpoint():
    return (papers_since_checkpoint >= BATCH_SIZE or
            time_since_checkpoint >= 120 or
            approaching_api_limit or
            memory_usage_high)
    # Multiple conditions = more complexity
```

---

## Recommendation 5: Service-Specific Optimal Batch Sizes

### Pros ✅
- **Tailored to each API's characteristics** - Optimal for each service
- **Maximizes efficiency** - Each service runs at peak performance
- **Respects API limits** - Won't trigger rate limiting
- **Based on empirical data** - Proven safe thresholds
- **Gradual rollout possible** - Can update one service at a time

### Cons ❌
- **Inconsistent user experience** - Different progress patterns per service
- **Maintenance burden** - Need to maintain different configs
- **Hard to document** - "It depends on which enricher" complexity
- **New services need research** - Can't just copy a standard value
- **Config sprawl** - Another place where magic numbers live

### Implementation Risk: **Low**
```python
# Easy but scattered
BATCH_SIZES = {
    "semantic_scholar": 500,  # API maximum
    "openalex": 100,          # Balanced
    "crossref": 100,          # Balanced
    "arxiv": 30,              # Rate limited
    # But what about the next service?
}
```

---

## Recommendation Comparison Matrix

| Aspect | Time-Based | Increase arXiv | Increase CrossRef | Adaptive | Service-Specific |
|--------|------------|----------------|-------------------|----------|------------------|
| **Implementation Effort** | High | Low | Low | High | Medium |
| **Risk of Data Loss** | Medium | Medium | Medium | Low | Low |
| **Performance Gain** | Medium | High | Medium | High | High |
| **Maintainability** | High | High | High | Medium | Low |
| **User Experience** | High | Medium | Medium | Medium | Low |
| **Flexibility** | High | Low | Low | High | Medium |

---

## Combined Recommendation Strategy

### Phase 1: Quick Wins (Do Now)
1. **Increase arXiv to 30** - Low risk, immediate benefit
2. **Increase CORE to 20** - Low risk, immediate benefit
3. **Document current batch sizes** - Add comments explaining why

### Phase 2: Measured Improvements (Next Sprint)
1. **Increase CrossRef to 100** - Monitor for rate limits
2. **Increase PubMed to 50** - Test with large datasets
3. **Add batch size to config.py** - Centralize magic numbers

### Phase 3: Architectural Improvements (Future)
1. **Implement adaptive checkpointing** - For new enrichers
2. **Add checkpoint metrics** - Track save frequency, size, recovery time
3. **Create checkpoint strategy base class** - Standardize pattern

---

## Risk Mitigation Strategies

### For Larger Batches:
```python
# Add recovery metrics
checkpoint_data = {
    "batch_size_used": current_batch_size,
    "papers_in_batch": len(batch),
    "estimated_recovery_time": len(batch) * seconds_per_paper,
    "checkpoint_reason": "batch_complete|time_elapsed|error_recovery"
}
```

### For Time-Based:
```python
# Allow override for critical operations
def save_checkpoint(force=False):
    if force or time_elapsed > threshold:
        # Save even if mid-batch
        checkpoint_data["partial_batch"] = True
```

### For Adaptive:
```python
# Start conservative, learn optimal
class AdaptiveCheckpointer:
    def __init__(self):
        self.batch_size = 10  # Start small
        self.success_count = 0

    def on_success(self):
        self.success_count += 1
        if self.success_count > 100:
            self.batch_size = min(self.batch_size * 1.5, MAX_BATCH)
```

---

## Conclusion

**Best Overall Approach**: **Hybrid Strategy**

1. **Immediate**: Increase batch sizes for slow services (arXiv, CORE)
2. **Short-term**: Service-specific optimization based on API characteristics
3. **Long-term**: Adaptive checkpointing for robustness

This provides immediate benefits while building toward a more sophisticated solution.

**Do NOT do**: Pure time-based checkpointing alone - too disruptive to batch operations

**Key Insight**: Different services have fundamentally different characteristics (rate limits, bulk support, reliability) that justify different checkpoint strategies. One size does NOT fit all.
