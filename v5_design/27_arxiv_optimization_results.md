# arXiv Enrichment Optimization Results

## Date: December 3, 2024

## Implementation Summary

Successfully implemented batch querying for arXiv enrichment using the `id_list` parameter, allowing up to 100 papers to be queried in a single API request.

## Key Changes

### 1. Added Batch Query Function
- `search_by_arxiv_ids_batch()`: Queries up to 100 arXiv IDs in one request
- Uses comma-separated `id_list` parameter
- Maintains 3-second delay between batch requests

### 2. Separated Processing Logic
Papers are now processed in two groups:
- **Papers WITH arXiv IDs**: Batch processed (100 at a time)
- **Papers WITHOUT arXiv IDs**: Individual title searches (as before)

### 3. Updated Checkpoint Logic
- Saves checkpoint after each batch of 100 papers with IDs
- Saves checkpoint after each chunk of 10 papers without IDs
- Maintains full recovery capability

## Performance Improvements

### Before Optimization

| Scenario | Papers | Time per Paper | Total Time | Papers/Hour |
|----------|--------|----------------|------------|-------------|
| All papers | 2,200 | 3 seconds | 6,600 sec (110 min) | 1,200 |

### After Optimization

| Scenario | Papers | Processing Method | Time | Papers/Hour |
|----------|--------|------------------|------|-------------|
| **Papers with arXiv IDs** | Variable | 100 per batch | 3 sec/batch | **120,000** |
| **Papers without IDs** | Variable | Individual | 3 sec/paper | 1,200 |

### Real-World Scenarios

Assuming different percentages of papers already have arXiv IDs from previous enrichment:

| % with IDs | Papers with IDs | Papers without | Batch Time | Individual Time | Total Time | Speedup |
|------------|-----------------|----------------|------------|-----------------|------------|---------|
| **0%** | 0 | 2,200 | 0 sec | 6,600 sec | **110 min** | 1x |
| **10%** | 220 | 1,980 | 9 sec | 5,940 sec | **99 min** | 1.1x |
| **25%** | 550 | 1,650 | 18 sec | 4,950 sec | **83 min** | 1.3x |
| **50%** | 1,100 | 1,100 | 36 sec | 3,300 sec | **56 min** | 2x |
| **75%** | 1,650 | 550 | 54 sec | 1,650 sec | **28 min** | 3.9x |
| **90%** | 1,980 | 220 | 63 sec | 660 sec | **12 min** | 9.2x |

## Expected Impact

### Conservative Estimate (25% have IDs)
- **Before**: 110 minutes
- **After**: 83 minutes
- **Savings**: 27 minutes (25% faster)

### Optimistic Estimate (75% have IDs)
- **Before**: 110 minutes
- **After**: 28 minutes
- **Savings**: 82 minutes (75% faster)

## Code Example

```python
# Before: Every paper queried individually
for paper in papers:
    if paper.get("arxiv_id"):
        result = search_by_arxiv_id(paper["arxiv_id"])  # 3 seconds
        time.sleep(3)

# After: Batch processing for papers with IDs
papers_with_ids = [p for p in papers if p.get("arxiv_id")]
for i in range(0, len(papers_with_ids), 100):
    batch = papers_with_ids[i:i+100]
    results = search_by_arxiv_ids_batch([p["arxiv_id"] for p in batch])  # 3 seconds for 100!
    time.sleep(3)
```

## Additional Benefits

1. **Reduced API Calls**: From 2,200 to as few as 242 (assuming 90% have IDs)
2. **Better Resource Usage**: Less network overhead, fewer HTTP connections
3. **Improved Reliability**: Fewer chances for network timeouts
4. **Cleaner Logs**: Batch progress instead of per-paper spam

## Future Optimizations

1. **Pre-fetch arXiv IDs** during CrossRef/S2 enrichment stages
2. **Cache results** to avoid re-querying the same IDs
3. **Use OAI-PMH** for daily metadata harvesting
4. **Increase batch size** to 200-500 if API allows

## Conclusion

The optimization provides significant speedup (2-9x) depending on how many papers already have arXiv IDs. Since papers often get arXiv IDs from CrossRef or S2 enrichment, the real-world improvement is likely substantial (3-5x faster on average).

### Bottom Line
- **Worst case** (no IDs): No slower than before
- **Best case** (90% have IDs): 9x faster
- **Typical case** (50% have IDs): 2x faster
