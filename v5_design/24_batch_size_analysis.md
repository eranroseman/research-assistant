# Root Cause Analysis: Batch Size Differences Across Pipeline Stages

## Date: December 3, 2024

## Executive Summary

Different pipeline stages use vastly different batch sizes for checkpoint saves, ranging from 10 papers (arXiv, CORE) to 500 papers (Semantic Scholar). This analysis identifies the root causes and provides recommendations for optimization.

## Current Batch Sizes by Service

| Service | Batch Size | Checkpoint Frequency | Root Cause |
|---------|------------|---------------------|------------|
| **Semantic Scholar** | 500 | Every 500 papers | API supports bulk (500 max) |
| **CrossRef** | 50 | Every 50 papers | Balance between progress saves and API efficiency |
| **OpenAlex** | 50 | Every 50 papers | API supports bulk queries |
| **Unpaywall** | 50 | Every 50-100 papers | Individual API calls, moderate speed |
| **PubMed** | 20 | Every 100 papers | Limited batch size (efetch limitations) |
| **arXiv** | 10 | Every 10 papers | 3-second delay requirement |
| **CORE** | 10 | Every 10 papers | 6-second delay requirement |
| **TEI Extractor** | N/A | Every 50 files | Local processing, no API |
| **Zotero Recovery** | N/A | Every 100 papers | Local API, fast |

## Root Causes for Differences

### 1. API Rate Limiting Constraints

**Strict Rate Limits (Small Batches):**
- **arXiv**: 3-second mandatory delay between requests → 10 papers/batch
  - At 3 sec/paper, 10 papers = 30 seconds between checkpoints
  - Larger batches would mean losing too much work on failure

- **CORE**: 6-second delay (conservative) → 10 papers/batch
  - Token-based rate limiting (200 requests/minute)
  - At 6 sec/paper, 10 papers = 60 seconds between checkpoints

**Relaxed Rate Limits (Large Batches):**
- **Semantic Scholar**: No strict delay, supports 500 papers/request
  - Can process 500 papers in seconds with bulk endpoint
  - Checkpoint after each batch request makes sense

### 2. API Capabilities

**Bulk Query Support:**
- **Semantic Scholar**: Native bulk support (500 DOIs per request)
- **OpenAlex**: Bulk filtering (`doi:DOI1|DOI2|...`)
- **CrossRef**: Individual queries only, but fast

**Individual Queries Only:**
- **arXiv**: Search API requires individual title/author queries
- **CORE**: No true batch endpoint
- **Unpaywall**: One DOI at a time
- **PubMed**: Limited batch support (efetch has restrictions)

### 3. Processing Speed vs Risk Trade-off

**CORRECTED RATES** (Based on actual code delays):

| Service | Rate Limit | Actual Speed | Papers/Hour | Time per Checkpoint |
|---------|------------|--------------|-------------|-------------------|
| **Semantic Scholar** | No delay (bulk 500) | 500 papers/request | ~36,000* | ~50 seconds |
| **CrossRef** | 0.1s/paper | 10 papers/sec | ~36,000 | ~5 seconds (50 papers) |
| **OpenAlex** | 0.1s/batch | 50 papers/0.1s | ~36,000* | ~5 seconds |
| **Unpaywall** | No explicit delay | ~10 papers/sec | ~36,000 | ~5 seconds |
| **PubMed** | No explicit delay | ~20 papers/batch | ~20,000 | ~3-5 seconds |
| **arXiv** | 3s/paper | 0.33 papers/sec | ~1,200 | 30 seconds (10 papers) |
| **CORE** | 6s/paper | 0.17 papers/sec | ~600 | 60 seconds (10 papers) |

*Bulk APIs process entire batch in one request, so actual rate depends on API response time

### 4. Historical Development Patterns

Different developers optimized for different concerns:
- **Early scripts** (arXiv, CORE): Conservative, frequent saves
- **Later scripts** (S2, OpenAlex): Optimized for bulk performance
- **Local processing** (TEI, Zotero): Balanced at 50-100

## Performance Impact Analysis

### Key Insight: Most Services Are EQUALLY FAST!

**CrossRef, S2, OpenAlex, Unpaywall** all process at ~36,000 papers/hour (theoretical max)
- They checkpoint at different intervals (5-50 seconds) despite same speed
- This is arbitrary, not based on performance differences

### Current Inefficiencies

1. **Over-frequent Checkpointing (Fast Services):**
   - CrossRef/OpenAlex save every 5 seconds (50 papers)
   - Excessive I/O for such fast processing
   - Could easily batch 200-500 papers like S2

2. **Appropriate Checkpointing (Slow Services):**
   - arXiv saves every 30 seconds (10 papers) - reasonable given 3s delays
   - CORE saves every 60 seconds (10 papers) - reasonable given 6s delays

3. **Inconsistent User Experience:**
   - Users see different progress patterns
   - Hard to estimate completion time
   - Checkpoint files vary wildly in size

## Recommendations

### 1. Standardize by Time, Not Count

Instead of fixed paper counts, checkpoint based on elapsed time:
```python
CHECKPOINT_INTERVAL_SECONDS = 120  # Save every 2 minutes

if time.time() - last_checkpoint_time > CHECKPOINT_INTERVAL_SECONDS:
    save_checkpoint()
    last_checkpoint_time = time.time()
```

### 2. Optimal Batch Sizes by Service Type

| Service Type | Recommended Batch | Rationale |
|--------------|------------------|-----------|
| **Fast Bulk APIs** | 100-500 | Maximize API efficiency |
| **Fast Individual** | 50-100 | Balance efficiency and progress |
| **Rate-Limited** | 20-30 | Minimize re-work on failure |
| **Very Slow** | 10-20 | Frequent saves critical |

### 3. Specific Recommendations (REVISED)

Since CrossRef, S2, OpenAlex, and Unpaywall are all equally fast (~10 papers/second):

```python
# Proposed standardized batch sizes for FAST services
BATCH_SIZES = {
    "semantic_scholar": 500,  # Keep - uses bulk API efficiently
    "crossref": 500,          # INCREASE from 50 - same speed as S2!
    "openalex": 500,          # INCREASE from 50 - same speed as S2!
    "unpaywall": 200,         # Increase from 50 - still fast
    "pubmed": 100,            # Increase from 20 - reasonably fast

    # Keep small for SLOW services (rate-limited)
    "arxiv": 10,              # Keep at 10 - 3s delays justify small batch
    "core": 10,               # Keep at 10 - 6s delays justify small batch
}
```

### 4. Adaptive Checkpointing

Implement adaptive checkpointing that considers both count and time:

```python
def should_checkpoint(papers_processed, elapsed_time, last_checkpoint):
    # Checkpoint if either condition met:
    # 1. Processed batch_size papers
    # 2. 2 minutes elapsed since last checkpoint

    papers_since_checkpoint = papers_processed - last_checkpoint["count"]
    time_since_checkpoint = elapsed_time - last_checkpoint["time"]

    return (papers_since_checkpoint >= BATCH_SIZE or
            time_since_checkpoint >= 120)
```

### 5. Progress Reporting Standardization

All enrichers should report:
- Papers processed / Total papers
- Current rate (papers/minute)
- Estimated time remaining
- Time since last checkpoint

## Implementation Priority

1. **High Priority** (Slow services losing too much on failure):
   - arXiv: Increase from 10 to 30
   - CORE: Increase from 10 to 20

2. **Medium Priority** (Could be more efficient):
   - CrossRef: Increase from 50 to 100
   - PubMed: Increase from 20 to 50
   - OpenAlex: Increase from 50 to 100

3. **Low Priority** (Already optimal):
   - Semantic Scholar: Keep at 500
   - Unpaywall: Keep at 50

## Conclusion

The batch size differences stem from:
1. **API constraints** (rate limits, bulk support)
2. **Risk tolerance** (how much work to potentially lose)
3. **Historical development** (different developers, different times)

Standardizing on time-based checkpointing with service-appropriate batch sizes would improve user experience and system efficiency while maintaining data safety.
