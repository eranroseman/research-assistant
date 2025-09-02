# DEPRECATED: Azure Deployment Files

## Status: Deprecated as of v5.0 Final

The following Azure-related files are deprecated and no longer maintained:

- `07_azure_deployment.md`
- `azure_implementation_guide.md`
- `azure_quick_reference.md`
- `grobid_azure_master.sh`

## Why Deprecated?

Based on empirical testing with 2,221 papers:

1. **Local processing is reliable**: 99.95% success rate with two-pass strategy
2. **Predictable timing**: 9.5 hours for 2,200 papers (15s average)
3. **No cloud complexity**: No subscription issues, quotas, or network problems
4. **Full control**: Can pause/resume, monitor progress, debug issues
5. **Cost-effective**: No cloud costs for occasional extraction runs

## Current Strategy: Local-Only Processing

v5.0 uses a **two-pass local extraction strategy**:

- **First pass**: 90 seconds timeout (captures 99.82% of papers)
- **Second pass**: 180 seconds timeout (retries failures)
- **No fallback**: Papers that fail both passes are reported, not degraded

## Migration Guide

If you were planning to use Azure:

1. **Install Grobid locally**:
   ```bash
   docker pull lfoppiano/grobid:0.8.2-full
   sudo docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full
   ```

2. **Run extraction**:
   ```bash
   python grobid_overnight_runner.py
   ```

3. **Expected timing**:
   - 100 papers: ~30 minutes
   - 500 papers: ~2 hours
   - 1,000 papers: ~4 hours
   - 2,200 papers: ~9.5 hours

## When Azure Might Still Be Useful

Azure deployment could be reconsidered for:

1. **Massive datasets**: >10,000 papers requiring parallel processing
2. **Continuous processing**: Daily extraction of new papers
3. **Team environments**: Multiple users needing concurrent access
4. **CI/CD pipelines**: Automated extraction in cloud workflows

For typical research use (500-5,000 papers), local processing is recommended.

## Historical Context

Azure deployment was designed when:
- We expected 30-60s per paper (reality: 15s average)
- We didn't have the two-pass strategy
- We included books/proceedings (now excluded)
- We didn't have checkpoint/resume capability

With these improvements, local processing became the better choice for v5.0.
