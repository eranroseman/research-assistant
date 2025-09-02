# Pipeline Runtime Analysis: Checkpoint Every 50 vs 500 Papers

## Date: December 3, 2024

## Assumptions
- **Dataset**: 2,200 papers
- **Checkpoint save time**: ~1 second per save (JSON serialization + disk write)
- **Processing speeds** (from our analysis):
  - CrossRef: 10 papers/sec (0.1s delay)
  - S2: 500 papers/batch (~5 sec/batch with API response time)
  - OpenAlex: 50 papers/batch (~2 sec/batch)
  - Unpaywall: 10 papers/sec
  - PubMed: Variable, ~5 papers/sec
  - TEI/Zotero: Local, ~50 papers/sec

## Scenario 1: Checkpoint Every 50 Papers

### Stage-by-Stage Breakdown

| Stage | Papers | Process Time | Checkpoints | Checkpoint Time | Total Time |
|-------|--------|--------------|-------------|-----------------|------------|
| **TEI Extraction** | 2,200 | 44 sec | 44 | 44 sec | **88 sec** |
| **Zotero Recovery** | 2,200 | 44 sec | 44 | 44 sec | **88 sec** |
| **CrossRef** | 2,200 | 220 sec | 44 | 44 sec | **264 sec** |
| **S2** | 2,200 | 25 sec | 44 | 44 sec | **69 sec** |
| **OpenAlex** | 2,200 | 90 sec | 44 | 44 sec | **134 sec** |
| **Unpaywall** | 2,200 | 220 sec | 44 | 44 sec | **264 sec** |
| **PubMed** | 2,200 | 440 sec | 44 | 44 sec | **484 sec** |

**Total (excluding arXiv): 1,391 seconds = 23.2 minutes**

## Scenario 2: Checkpoint Every 500 Papers

### Stage-by-Stage Breakdown

| Stage | Papers | Process Time | Checkpoints | Checkpoint Time | Total Time |
|-------|--------|--------------|-------------|-----------------|------------|
| **TEI Extraction** | 2,200 | 44 sec | 5 | 5 sec | **49 sec** |
| **Zotero Recovery** | 2,200 | 44 sec | 5 | 5 sec | **49 sec** |
| **CrossRef** | 2,200 | 220 sec | 5 | 5 sec | **225 sec** |
| **S2** | 2,200 | 25 sec | 5 | 5 sec | **30 sec** |
| **OpenAlex** | 2,200 | 90 sec | 5 | 5 sec | **95 sec** |
| **Unpaywall** | 2,200 | 220 sec | 5 | 5 sec | **225 sec** |
| **PubMed** | 2,200 | 440 sec | 5 | 5 sec | **445 sec** |

**Total (excluding arXiv): 1,118 seconds = 18.6 minutes**

## Comparison Summary

| Metric | Every 50 | Every 500 | Difference |
|--------|----------|-----------|------------|
| **Total Runtime** | 23.2 min | 18.6 min | **4.6 min faster** |
| **Checkpoint Saves** | 308 | 35 | 273 fewer |
| **Checkpoint Overhead** | 308 sec | 35 sec | **273 sec saved** |
| **Max Data Loss** | 50 papers | 500 papers | 10x more risk |
| **Max Time to Recover** | ~5 sec | ~50 sec | 10x longer |

## Real-World Considerations

### Why the Difference is Actually LARGER

1. **Checkpoint files grow** - By the end, checkpoint files can be 10-50MB
   - Every 50: Writing 50MB file 44 times = more like 2-3 sec per save
   - Every 500: Writing 50MB file 5 times = still ~2-3 sec but only 5 times

2. **File system caching** - Frequent writes prevent efficient caching
   - Every 50: Cache constantly flushing
   - Every 500: Better cache utilization

3. **JSON parsing overhead** - Loading checkpoint gets slower as it grows
   - Every 50: Parse large JSON 44 times
   - Every 500: Parse large JSON 5 times

**Realistic time difference: 6-8 minutes (25-35% faster with 500)**

### Why This Matters Less Than You Think

1. **Parallel stages** - Some stages can run simultaneously
2. **Human time** - 5 minutes in a 30-minute pipeline is negligible
3. **Failure recovery** - One crash requiring re-run wipes out all gains

## Recommendations

### Use Checkpoint Every 500 for:
- **CrossRef** - Reliable, fast API
- **S2** - Bulk API, very fast
- **OpenAlex** - Batch API, reliable
- **Unpaywall** - Simple, reliable

### Keep Checkpoint Every 50-100 for:
- **TEI/Zotero** - Local, but file I/O can fail
- **PubMed** - Sometimes flaky API

### Never Change:
- **arXiv** - Keep at 10 (3-second delays make recovery painful)

## Bottom Line

**Switching from 50 to 500 for fast APIs saves ~5-8 minutes (20-30%) on a full pipeline run.**

For a pipeline that runs overnight or unattended, the 10x increase in potential data loss is acceptable given the performance gain. For interactive/debugging runs, keeping checkpoints at 50 might be worth the slower performance for faster recovery.
