# Advanced Usage Guide

> **📚 Back to main docs**: [README.md](../README.md) | [Technical Specs](technical-specs.md) | [API Reference](api-reference.md)

## GPU Acceleration

The system automatically detects and uses CUDA GPUs if available:

```bash
# Check GPU availability
python -c "import torch; print('GPU available' if torch.cuda.is_available() else 'CPU only')"
```

**v3.0 Enhancement**: Dynamic batch sizing adjusts based on GPU memory:
- 8GB+ GPU: batch_size=256
- 4-8GB GPU: batch_size=128
- <4GB GPU: batch_size=64

GPU provides ~10x speedup for embedding generation (2 min vs 20 min for 2000 papers).

## Embedding Models

**v3.0 Default**: The system now uses SPECTER2 by default with automatic SPECTER fallback:

```python
# Automatic in v3.0 - no code changes needed
# Tries SPECTER2 first, falls back to SPECTER if unavailable
```

### Model Hierarchy

1. **allenai/specter2** (Default in v3.0)
   - Best for scientific papers
   - Task-specific adapters
   - Query preprocessing optimization

2. **allenai-specter** (Fallback)
   - Reliable baseline
   - Works without additional dependencies

### Custom Models

To force a specific model, edit `src/build_kb.py`:

```python
self._embedding_model = SentenceTransformer('your-model-name', device=self.device)
```
- `multi-qa-mpnet-base-dot-v1`: Optimized for Q&A

## Adjusting Search Parameters

In `src/cli.py`, modify the FAISS index type:

```python
# For larger databases (>100k papers)
index = faiss.IndexIVFFlat(nlist=100)

# For similarity threshold filtering
index = faiss.IndexFlatL2(dimension)
```

## Batch Processing

Process multiple queries:

```bash
for topic in "AI" "telemedicine" "wearables"; do
    python src/cli.py search "$topic" --json > "results_$topic.json"
done
```

## Building from Custom Sources

Modify `src/build_kb.py` to implement a custom `process_papers()` function that returns a list of dictionaries with:

```python
{
    'title': str,
    'authors': List[str],
    'year': int,
    'journal': str,
    'volume': str,
    'issue': str,
    'pages': str,
    'doi': str,
    'abstract': str,
    'full_text': str  # Optional
}
```

## WSL-Specific Setup (Zotero on Windows Host)

When running in WSL with Zotero on the Windows host:

### 1. Enable Zotero API
In Zotero → Edit → Settings → Advanced → Check "Allow other applications"

### 2. Configure Windows Firewall
- Open Windows Defender Firewall with Advanced Security
- Add Inbound Rule for TCP port 23119
- Allow connections from WSL subnet (usually 172.x.x.x)

### 3. Run with Auto-Detection

```bash
python src/build_kb.py  # Auto-detects WSL and Windows host IP
```

### 4. Or Specify Manually

```bash
# Find Windows host IP in WSL
cat /etc/resolv.conf | grep nameserver

# Use that IP
python src/build_kb.py --api-url http://<windows-ip>:23119/api
```

## Performance Optimization

### Caching Strategy

The system uses dual caching:
- **PDF Cache** (~150MB): Stores extracted text from PDFs
- **Embedding Cache** (~500MB): Stores computed embeddings

Clear caches when:
- Changing embedding models
- Updating PDF extraction logic
- Experiencing cache corruption

```bash
python src/build_kb.py --clear-cache  # Clears both caches
```

### Memory Management

For large libraries (>5000 papers):
- Process papers in batches
- Use `faiss-cpu` instead of `faiss-gpu`
- Reduce embedding model size
- Increase system swap space

### Search Optimization

- Use specific queries rather than broad terms
- Limit results with `-k` parameter
- Use study type filters to narrow scope
- Enable verbose mode only when needed

### Benchmarking Tools

Test performance with built-in diagnostic scripts:

```bash
# Test cache performance (50 papers)
python scripts/benchmark_cache.py

# Compare PDF extraction libraries
python scripts/benchmark_pdf_extractors.py
```

## Extending the System

### Adding Citation Formats

To add APA, MLA, or Chicago formats, modify the citation generation in `src/cli.py`:

```python
def format_citation_apa(paper):
    # Implement APA format
    pass
```

### Integration with Other Tools

The knowledge base can be accessed programmatically:

```python
from src.cli import KnowledgeBase

kb = KnowledgeBase()
results = kb.search("your query", k=10)
```

### Web API

To create a REST API, wrap the CLI functions:

```python
from flask import Flask, jsonify
from src.cli import KnowledgeBase

app = Flask(__name__)
kb = KnowledgeBase()

@app.route('/search/<query>')
def search(query):
    results = kb.search(query)
    return jsonify(results)
```

## Troubleshooting Performance

### Slow Embedding Generation
- Check GPU availability: `nvidia-smi`
- Verify CUDA installation: `torch.cuda.is_available()`
- Consider using a faster model
- Enable batch processing

### High Memory Usage
- Reduce batch size in `src/build_kb.py`
- Use streaming for large PDFs
- Clear unused caches
- Monitor with `htop` or `nvidia-smi`

### Slow Searches
- Rebuild FAISS index
- Check for antivirus interference
- Use SSD storage for knowledge base
- Consider index optimization (IVF)
