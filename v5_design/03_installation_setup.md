# Installation & Setup Guide

## System Requirements

### Minimum Requirements
- **OS**: Linux, macOS, or Windows with WSL2
- **Python**: 3.11 or higher
- **RAM**: 16GB minimum
- **Storage**: 10GB free space
- **CPU**: 4+ cores recommended
- **Network**: Stable internet connection

### Recommended Specifications
- **RAM**: 32GB for large collections
- **Storage**: 50GB for complete pipeline
- **CPU**: 8+ cores for faster processing
- **GPU**: Optional, not required

## Prerequisites

### 1. Python Environment

```bash
# Check Python version (must be 3.11+)
python --version

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Docker Installation

Required for GROBID server:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo usermod -aG docker $USER

# macOS
# Install Docker Desktop from https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
```

### 3. Git Setup

```bash
# Install git if needed
sudo apt install git  # Ubuntu/Debian
brew install git      # macOS

# Clone repository
git clone https://github.com/yourusername/research-assistant.git
cd research-assistant
```

## Installation Steps

### 1. Install Python Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# Verify critical packages
python -c "import requests, lxml, tqdm; print('Core packages OK')"
```

### 2. Start GROBID Server

```bash
# Pull and run GROBID container
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Verify GROBID is running
curl http://localhost:8070/api/version
```

Keep this terminal open or run with `-d` for background:

```bash
docker run -d -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full
```

### 3. Configure src/config.py

```python
# Check configuration (usually no changes needed)
cat src/config.py

# Key settings to verify:
GROBID_SERVER = "http://localhost:8070"
PIPELINE_DIR = "extraction_pipeline"
BATCH_SIZE = 50  # Adjust based on RAM
```

### 4. Prepare Input Data

```bash
# Option 1: Extract from Zotero
python src/extract_zotero_library.py \
    --zotero-dir ~/Zotero/storage \
    --output-dir pdfs/

# Option 2: Use existing PDFs
mkdir -p pdfs/
cp /path/to/your/papers/*.pdf pdfs/
```

## First Run Checklist

### Pre-flight Checks

```bash
# 1. Verify GROBID is running
curl http://localhost:8070/api/isalive

# 2. Check Python environment
python --version  # Should be 3.11+
pip list | grep -E "requests|lxml|tqdm"

# 3. Verify PDF input
ls -la pdfs/ | head -5  # Should show PDF files

# 4. Check disk space
df -h .  # Need ~10GB free

# 5. Test type checking
mypy src/config.py  # Should pass without errors
```

### Running the Pipeline

```bash
# Full pipeline with checkpoints (RECOMMENDED)
python src/extraction_pipeline_runner_checkpoint.py

# Monitor progress
# You'll see a 40-line dashboard with real-time updates
```

## Common Issues & Solutions

### GROBID Connection Issues

```bash
# Error: "Connection refused" or "GROBID server not responding"

# Solution 1: Check if Docker is running
docker ps  # Should show grobid container

# Solution 2: Restart GROBID
docker stop $(docker ps -q --filter ancestor=lfoppiano/grobid)
docker run -d -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Solution 3: Check port availability
lsof -i :8070  # Should show docker process
```

### Memory Issues

```bash
# Error: "MemoryError" or system becomes unresponsive

# Solution 1: Reduce batch size in src/config.py
BATCH_SIZE = 25  # Lower from default 50

# Solution 2: Increase swap space
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Solution 3: Process in smaller chunks
python src/extraction_pipeline_runner_checkpoint.py --max-papers 500
```

### Permission Issues

```bash
# Error: "Permission denied" when writing files

# Solution 1: Check directory permissions
ls -la extraction_pipeline/

# Solution 2: Fix ownership
sudo chown -R $USER:$USER extraction_pipeline/

# Solution 3: Use different output directory
python src/extraction_pipeline_runner_checkpoint.py \
    --pipeline-dir /tmp/extraction_pipeline
```

### API Rate Limiting

```bash
# Error: "429 Too Many Requests"

# Solution 1: Built-in delays handle this automatically
# CrossRef: 0.5s, arXiv: 3s, others: adaptive

# Solution 2: Resume from checkpoint
python src/extraction_pipeline_runner_checkpoint.py
# Automatically resumes from last successful batch

# Solution 3: Run enrichment stages separately
python src/crossref_batch_enrichment_checkpoint.py
python src/s2_batch_enrichment.py  # Run later
```

### Checkpoint Recovery

```bash
# Pipeline interrupted? No problem!

# Resume automatically
python src/extraction_pipeline_runner_checkpoint.py
# Detects and resumes from last checkpoint

# Force fresh start
python src/extraction_pipeline_runner_checkpoint.py --reset-checkpoints

# Resume from specific stage
python src/extraction_pipeline_runner_checkpoint.py --start-from crossref
```

## Troubleshooting Commands

### Diagnostic Tools

```bash
# Check system resources
htop  # or top
df -h
free -h

# Monitor GROBID logs
docker logs $(docker ps -q --filter ancestor=lfoppiano/grobid)

# Check Python imports
python -c "import sys; print(sys.path)"
python -c "from src import config; print('Config OK')"

# Verify file counts
find extraction_pipeline -name "*.json" | wc -l
find extraction_pipeline -name "*.xml" | wc -l

# Check for errors in logs
grep -r "ERROR" logs/
grep -r "Exception" logs/
```

### Performance Monitoring

```bash
# Monitor pipeline progress
tail -f logs/pipeline_*.log

# Check stage completion
ls -la extraction_pipeline/*/checkpoint.json

# Analyze success rates
python src/analyze_pipeline_completeness.py

# Find problematic papers
python src/analyze_problematic_papers.py
```

## Environment Variables

Optional environment variables for API keys:

```bash
# Semantic Scholar (optional, improves rate limits)
export S2_API_KEY="your_key_here"

# Unpaywall (required for that enrichment)
export UNPAYWALL_EMAIL="your.email@example.com"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export S2_API_KEY="your_key"' >> ~/.bashrc
```

## Testing Installation

### Quick Test

```bash
# Test with 5 papers
python src/extraction_pipeline_runner_checkpoint.py --max-papers 5

# Check results
ls -la extraction_pipeline*/10_final_output/
```

### Validation Tests

```bash
# Run type checking
mypy src/

# Run linting
ruff check src/

# Test individual components
python -c "from src.config import GROBID_SERVER; print(f'GROBID: {GROBID_SERVER}')"
python -c "from src.pipeline_utils import clean_doi; print(clean_doi('10.1234/test'))"
```

## Next Steps

1. ✅ System requirements verified
2. ✅ Dependencies installed
3. ✅ GROBID server running
4. ✅ Input PDFs prepared
5. ➡️ Run pipeline: See [Pipeline Architecture](03_pipeline_architecture.md)
6. ➡️ Monitor progress: See [Logging & Monitoring](09_logging_monitoring.md)
7. ➡️ Handle issues: Check troubleshooting above

## Getting Help

- Check [FAQ](FAQ.md) for common questions
- Review [Command Reference](11_commands_reference.md) for options
- See [Performance Optimization](08_performance_optimization.md) for tuning
- File issues at: https://github.com/yourusername/research-assistant/issues

---

*Installation typically takes 10-15 minutes. Pipeline processing time depends on collection size.*
