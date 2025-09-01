# Troubleshooting Guide

## Common Issues and Solutions

### 1. Grobid Connection Issues

**Problem**: Cannot connect to Grobid on localhost:8070

**Solutions**:
```bash
# Check if Grobid is running
curl http://localhost:8070/api/isalive

# If not, start Grobid
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# Alternative: use docker-compose
docker-compose up grobid
```

**Common causes**:
- Docker not installed/running
- Port 8070 already in use
- Insufficient memory (needs 4GB minimum)

### 2. Extraction Failures

**Problem**: Papers failing extraction with HTTP 500 errors

**Diagnosis**:
```python
# Check failed papers
python analyze_grobid_extraction.py

# Review error logs
cat zotero_extraction_*/errors/*.txt
```

**Common causes and fixes**:
- **Books/proceedings** (>15MB): Expected, exclude from processing
- **Corrupted PDFs**: Re-download or exclude
- **Memory issues**: Restart Grobid, increase Docker memory

### 3. Missing Text Content

**Problem**: Papers have sections but no text

**Fix**:
```bash
# Run the text recovery script
python reprocess_tei_xml.py

# This fixes the extraction bug and recovers full text
```

**Prevention**: Use the latest extraction scripts that include the fix

### 4. Missing Titles

**Problem**: Papers without titles after extraction

**Progressive recovery**:
```bash
# Stage 1: CrossRef enrichment
python crossref_enrichment.py

# Stage 2: Clean malformed DOIs and retry
python fix_malformed_dois.py

# Stage 3: Final cleanup (exclude if still missing)
python final_cleanup_no_title.py
```

**Success rates**:
- CrossRef: ~90% recovery
- DOI cleaning: ~80% of remaining
- Final: 100% coverage (by exclusion)

### 5. Quality Issues

**Problem**: Low-quality papers in KB

**Filter stages**:
```bash
# Remove abstract-only and empty papers
python pdf_quality_filter.py

# Remove non-articles (supplements, datasets)
python filter_non_articles.py
```

**Quality thresholds**:
- Minimum 1000 chars of text
- Must have title OR DOI
- Must be research article (not supplement/dataset)

### 6. Pipeline Interruptions

**Problem**: Pipeline stopped midway

**Resume options**:
```bash
# Option 1: Use consolidated pipeline (auto-resumes)
python v5_extraction_pipeline.py --skip-extraction

# Option 2: Run remaining stages manually
python crossref_enrichment.py  # Start from where it stopped
python filter_non_articles.py
# etc.
```

### 7. Performance Issues

**Problem**: Extraction taking too long

**Optimizations**:
```python
# Check current progress
ls zotero_extraction_*/json/*.json | wc -l

# Estimate remaining time
# Formula: (total_papers - completed) * 15 / 3600 = hours_remaining
```

**Speed tips**:
- Use SSD for faster I/O
- Ensure 8GB+ RAM available
- Close other applications
- Run overnight with `caffeinate` (Mac) or `systemd-inhibit` (Linux)

### 8. API Rate Limiting

**Problem**: CrossRef API returning 429 errors

**Solutions**:
```python
# Increase delay in script
self.delay = 0.5  # Instead of 0.2

# Or use polite pool
self.headers = {
    'User-Agent': 'YourApp/1.0 (mailto:your-email@example.com)'
}
```

### 9. Storage Issues

**Problem**: Running out of disk space

**Check usage**:
```bash
# Check extraction size
du -sh zotero_extraction_*

# Typical sizes:
# - TEI XML: ~500MB for 2000 papers
# - JSON: ~300MB for 2000 papers
# - Total: ~1GB per 1000 papers
```

**Cleanup**:
```bash
# Remove intermediate directories after final KB
rm -rf kb_quality_filtered_*
rm -rf kb_crossref_enriched_*
rm -rf kb_articles_only_*
# Keep only kb_final_cleaned_*
```

### 10. Validation Issues

**Problem**: How to verify extraction quality?

**Validation commands**:
```bash
# Check extraction statistics
python analyze_grobid_extraction.py

# Review sample papers
python -c "
import json
from pathlib import Path
import random

kb_dir = Path('kb_final_cleaned_*')
files = list(kb_dir.glob('*.json'))
sample = random.sample(files, 5)

for f in sample:
    with open(f) as file:
        data = json.load(file)
        print(f\"\\n{f.name}:\")
        print(f\"  Title: {data.get('title', 'MISSING')[:60]}...\")
        print(f\"  DOI: {data.get('doi', 'MISSING')}\")
        print(f\"  Sections: {len(data.get('sections', []))}\")
        print(f\"  Text length: {sum(len(s.get('text', '')) for s in data.get('sections', []) if isinstance(s, dict)):,}\")
"
```

## Error Messages Explained

### "Failed to extract: HTTP 500"
- **Meaning**: Grobid internal error
- **Action**: Check if PDF is a book (>15MB), corrupted, or Grobid needs restart

### "No content extracted"
- **Meaning**: Grobid returned empty result
- **Action**: Check PDF quality, might be scanned image without OCR

### "Missing title and DOI"
- **Meaning**: Cannot identify paper
- **Action**: Will be excluded in final cleanup

### "Malformed DOI"
- **Meaning**: DOI has extra text appended
- **Action**: Run `fix_malformed_dois.py` to clean

### "Connection refused"
- **Meaning**: Grobid not running
- **Action**: Start Grobid with Docker command

## Best Practices

### Before Starting
1. Ensure 10GB free disk space
2. Start Grobid and verify with `/api/isalive`
3. Close unnecessary applications
4. Use `caffeinate` or `systemd-inhibit` to prevent sleep

### During Extraction
1. Monitor progress in `checkpoint.json`
2. Check error directory for patterns
3. Don't interrupt unless necessary
4. If interrupted, note last successful paper

### After Extraction
1. Run `analyze_grobid_extraction.py` first
2. Follow the 7-stage pipeline in order
3. Validate final statistics
4. Keep only final cleaned directory

### For Production
1. Use `v5_extraction_pipeline.py` for consistency
2. Schedule overnight runs
3. Keep backups of final KB
4. Document any custom modifications

## Getting Help

### Diagnostic Information to Collect
```bash
# System info
python --version
docker --version
df -h  # Disk space
free -h  # Memory (Linux) or top (Mac)

# Extraction info
ls -la zotero_extraction_*/
wc -l zotero_extraction_*/errors/*.txt
head zotero_extraction_*/checkpoint.json

# Sample error
head -50 zotero_extraction_*/errors/*.txt | head -1
```

### Quick Fixes Checklist
- [ ] Grobid running and accessible
- [ ] Sufficient disk space (10GB+)
- [ ] Sufficient memory (4GB+ free)
- [ ] Latest scripts from git
- [ ] Running scripts in correct order
- [ ] Not processing books/proceedings
- [ ] CrossRef API not rate limited

### When All Else Fails
1. Start fresh with clean directory
2. Use smaller test batch first
3. Run consolidated pipeline script
4. Check GitHub issues for similar problems
5. Review the complete logs in error directories
