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

GPU provides ~2x speedup for embedding generation (~10 min vs ~20 min for 2000 papers).

## Embedding Models

**v3.0+ Default**: The system uses SPECTER embeddings optimized for scientific literature:

```python
# SPECTER model is loaded automatically
# Provides superior performance for academic paper search
```

### Model Configuration

**allenai-specter** (Default)
   - Optimized for scientific papers
   - Proven reliability for academic literature
   - 768-dimensional embeddings

### Custom Models

To force a specific model, edit `src/build_kb.py`:

```python
self._embedding_model = SentenceTransformer('your-model-name', device=self.device)
```
- `multi-qa-mpnet-base-dot-v1`: Optimized for Q&A

## Adjusting Search Parameters

The system uses `faiss.IndexFlatL2` for exact similarity search. To modify the index type, edit `src/build_kb.py` where the index is created:

```python
# Current implementation uses:
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

To use custom sources, modify the paper processing logic in `src/build_kb.py` to return a list of dictionaries with:

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

### Performance Monitoring

Monitor performance using system tools:

```bash
# Monitor GPU usage
nvidia-smi -l 1

# Monitor CPU and memory
htop
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
from src.cli import ResearchCLI

kb = ResearchCLI()
results = kb.search("your query", top_k=10)
```

### Web API

To create a REST API, wrap the CLI functions:

```python
from flask import Flask, jsonify
from src.cli import ResearchCLI

app = Flask(__name__)
kb = ResearchCLI()

@app.route('/search/<query>')
def search(query):
    results = kb.search(query, top_k=10)
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
