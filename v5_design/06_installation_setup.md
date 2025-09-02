# Installation and Setup Guide

## Prerequisites

### 1. Install Docker

Docker is required to run Grobid service.

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io
sudo usermod -aG docker $USER  # Add user to docker group
# Log out and back in for group change to take effect

# macOS
brew install docker
# Start Docker Desktop from Applications

# Windows
# Download Docker Desktop from https://docs.docker.com/desktop/install/windows/
```

### 2. Install Python Dependencies

```bash
# Core requirements
pip install -r requirements.txt

# Optional: Intel CPU optimization (2-3x speedup)
pip install intel-extension-for-pytorch

# Optional: GPU support (if CUDA available)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. Install and Start Grobid

```bash
# Pull Grobid Docker image with full models (one-time, 17.3GB)
docker pull lfoppiano/grobid:0.8.2-full

# Start Grobid service locally
sudo docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Verify it's running
curl http://localhost:8070/api/isalive
# Should return: true
```

### 4. Configure Zotero

1. Open Zotero
2. Go to Preferences → Advanced → Config Editor
3. Search for `extensions.zotero.httpServer.enabled`
4. Set to `true` if not already
5. Note: Zotero must be running during KB builds

## System Requirements

### Minimum Requirements

```yaml
RAM: 4 GB (for <1000 papers)
Disk: 10 GB free
CPU: 2 cores
Network: 10 Mbps (for S2 API)
Python: 3.8+
```

### Recommended Requirements

```yaml
RAM: 8 GB (for 2000+ papers)
Disk: 20 GB free
CPU: 4+ cores (Intel for 2-3x speedup)
Network: 50+ Mbps
Python: 3.10+
```

### Docker Resources

```yaml
Grobid Container:
  RAM: 4-8 GB allocated
  Disk: 17.3 GB for full image
  CPU: 2-4 cores
```

### Data Usage Estimates

```yaml
Per Paper:
  Grobid extraction: ~500 KB
  S2 API calls: ~100 KB
  Embeddings: ~50 KB
  Total: ~650 KB

2,200 Papers:
  Storage: ~2-4 GB
  Network: ~1.3 GB
  Time: ~9.5 hours (with two-pass strategy)

API Limits:
  S2 Unauthenticated: 1 req/sec
  S2 Batch: 100 papers/request
  Grobid: No limits (local)
```

## First Build - Step by Step

### 1. Verify Setup

```bash
# Check all requirements
# Check Python version and dependencies
python --version  # Should be 3.11+

# Output should show:
# ✓ Python 3.10+ found
# ✓ Docker installed
# ✓ Grobid accessible at http://localhost:8070
# ✓ Zotero API accessible
# ✓ All Python packages installed
# ✓ 15 GB disk space available
# Exit code 0 = ready
```

### 2. Estimate Build Time

```bash
# Check how long the build will take
python src/extraction_pipeline_runner_checkpoint.py --estimate

# Example output:
# Found 2,221 papers in Zotero library
# Estimated time: 9.5 hours
# ✓ Safe for overnight run
# Recommended: Start before leaving work or overnight
```

### 3. Start the Build

```bash
# For first-time setup, do a full rebuild
python src/extraction_pipeline_runner_checkpoint.py --rebuild

# What happens:
# 1. Auto-starts Grobid if not running
# 2. Fetches papers from Zotero
# 3. Extracts with Grobid (15s average/paper, two-pass strategy)
# 4. Applies post-processing fixes
# 5. Gets S2 metrics (if available)
# 6. Creates embeddings
# 7. Builds FAISS indices
# 8. Generates quality report
# 9. Runs gap analysis (15-25 min)
```

### 4. Monitor Progress

```bash
# In another terminal, check progress
cat kb_data/build_progress.txt

# Output:
# Build Progress: 847/1234 (68.7%)
# Current: paper_0847.pdf
# Elapsed: 4.2 hours
# ETA: 1.9 hours
# Rate: 202 papers/hour

# Or check detailed log
tail -f kb_data/build_progress.log
```

### 5. Review Results

After build completes:

```bash
# Check build summary
cat kb_data/build_summary.txt

# Review quality report (if issues found)
cat exports/analysis_pdf_quality.md

# Review gap analysis
cat exports/gap_analysis_*.md

# Test search
python v4/src/cli.py search "diabetes" --limit 5
```

## Troubleshooting

### Common Issues and Solutions

#### "Cannot connect to Grobid"

```bash
# Check if Grobid is running
docker ps | grep grobid

# If not running, start it
docker run -t --rm -p 8070:8070 grobid/grobid:0.8.1

# If port conflict
docker run -t --rm -p 8071:8070 grobid/grobid:0.8.1
# Then update your config to use port 8071
```

#### "Cannot connect to Zotero"

```bash
# 1. Make sure Zotero is running
# 2. Enable API in Zotero preferences
# 3. Check if firewall is blocking port 23119
curl http://localhost:23119/api/collections
```

#### "Out of memory during build"

```bash
# Increase Docker memory
# Docker Desktop → Settings → Resources → Memory: 4GB+

# Or process in smaller batches
python src/extraction_pipeline_runner_checkpoint.py --collection "Small Collection"
```

#### "Build interrupted/crashed"

```bash
# Just run again - automatically resumes from checkpoint
python src/extraction_pipeline_runner_checkpoint.py

# Checkpoint saved every 50 papers
# No work is lost
```

#### "S2 API rate limited"

```bash
# The system handles this automatically with adaptive delays
# If persistent, get free API key:
# 1. Sign up at https://www.semanticscholar.org/product/api
# 2. Export key: export S2_API_KEY=your_key
# 3. Run build again
```

#### "PDF extraction failed for many papers"

```bash
# Review the quality report
cat exports/analysis_pdf_quality.md

# Common causes:
# - Scanned PDFs without OCR
# - Password-protected PDFs
# - Corrupted files
# - Supplementary materials (not full papers)

# Solutions provided in the report
```

## Performance Optimization

### Enable Intel Extension (2-3x speedup)

```bash
# Install Intel Extension
pip install intel-extension-for-pytorch

# Verify it's working
python -c "import intel_extension_for_pytorch as ipex; print('IPEX available')"

# Automatic detection during build
# Look for: "✓ Intel Extension enabled - 2-3x speedup active"
```

### Use Collection-Based Building

```bash
# Process high-priority papers first
python src/extraction_pipeline_runner_checkpoint.py --collection "Current Project"

# Then process rest later
python src/extraction_pipeline_runner_checkpoint.py --collection "Archive"
```

### Skip Gap Analysis for Speed

```bash
# Save 15-25 minutes per build
python src/extraction_pipeline_runner_checkpoint.py --no-gaps

# Run gap analysis separately when needed
# Gap analysis not in v5 - legacy v4 command
# python v4/src/analyze_gaps.py
```

## Weekly Maintenance

### Regular Updates

```bash
# Every Monday morning
python src/extraction_pipeline_runner_checkpoint.py  # Incremental update

# Check for new papers
python v4/src/cli.py info
```

### Monthly Full Rebuild

```bash
# First Sunday of month (optional)
python src/extraction_pipeline_runner_checkpoint.py --rebuild

# Export backup after rebuild
python src/extraction_pipeline_runner_checkpoint.py --export kb_backup_$(date +%Y%m).json
```

### Cleanup Old Data

```bash
# Remove old checkpoints and logs
rm -f kb_data/.checkpoint.json
rm -f kb_data/build_progress.log

# Compress old gap analysis reports
tar -czf gap_reports_$(date +%Y%m).tar.gz exports/gap_analysis_*.md
rm exports/gap_analysis_*.md
```

## Advanced Configuration

### Custom Grobid Parameters

Edit `grobid_config.py` to adjust extraction parameters:

```python
# For faster extraction (not recommended)
params['consolidateHeader'] = '0'  # No enrichment
params['consolidateCitations'] = '0'  # No citation enrichment

# For specific needs
params['processEquations'] = '0'  # Skip equations
params['processTables'] = '0'  # Skip tables
```

### Custom Quality Weights

Edit `quality_scorer.py` to adjust scoring:

```python
WEIGHTS = {
    'citations': 30,      # Impact weight
    'methodology': 25,    # Study quality
    'reproducibility': 20,  # Code/data availability
    'recency': 15,        # Publication year
    'completeness': 10   # Extraction quality
}
```

### Parallel Processing

```python
# In build.py, adjust worker count
MAX_WORKERS = 5  # Default
MAX_WORKERS = 10  # For powerful machines
MAX_WORKERS = 1  # For debugging
```
