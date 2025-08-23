# Advanced Usage Guide

> **Navigation**: [Home](../README.md) | [API Reference](api-reference.md) | [Technical Specs](technical-specs.md)

## Table of Contents

- [Programmatic Access](#programmatic-access)
- [Web API Integration](#web-api-integration)
- [Custom Data Sources](#custom-data-sources)
- [Performance Tuning](#performance-tuning)
- [Large Dataset Optimization](#large-dataset-optimization)
- [Advanced Search Techniques](#advanced-search-techniques)
- [Automation and Scripting](#automation-and-scripting)
- [Troubleshooting](#troubleshooting)

---

## Programmatic Access

### Using the Knowledge Base in Python Scripts

Instead of using the CLI, you can directly access the knowledge base from Python:

```python
#!/usr/bin/env python3
"""Example: Programmatic access to Research Assistant."""

import sys
sys.path.append('src')  # Add src to path

from cli import ResearchCLI
from cli_kb_index import KnowledgeBaseIndex

# Initialize the knowledge base
kb = ResearchCLI(knowledge_base_path="kb_data")

# Perform searches programmatically
results = kb.search(
    query_text="machine learning diagnosis",
    top_k=20,
    min_year=2020,
    study_types=["systematic_review", "rct"]
)

# Process results
for idx, distance, paper in results:
    relevance = 1 / (1 + distance)
    print(f"[{paper['id']}] {paper['title']} (Relevance: {relevance:.2f})")
```

### Direct Index Access for Analysis

```python
from cli_kb_index import KnowledgeBaseIndex

# O(1) paper lookups
index = KnowledgeBaseIndex("kb_data")

# Get specific paper
paper = index.get_paper_by_id("0042")

# Search by author
papers = index.search_by_author("Smith")

# Filter by year range
recent_papers = index.search_by_year_range(2020, 2024)

# Get statistics
stats = index.stats()
print(f"Total papers: {stats['total_papers']}")
print(f"Year distribution: {stats['year_distribution']}")
```

### Batch Analysis Script

```python
#!/usr/bin/env python3
"""Analyze research trends across multiple topics."""

import json
from pathlib import Path
from cli import ResearchCLI

# Topics to analyze
topics = [
    "artificial intelligence diagnosis",
    "telemedicine outcomes",
    "wearable health monitoring",
    "digital therapeutics"
]

kb = ResearchCLI()
trend_analysis = {}

for topic in topics:
    results = kb.search(topic, top_k=50)

    # Analyze year distribution
    years = {}
    for _, _, paper in results:
        year = paper.get('year', 'Unknown')
        years[year] = years.get(year, 0) + 1

    # Analyze study types
    study_types = {}
    for _, _, paper in results:
        st = paper.get('study_type', 'unknown')
        study_types[st] = study_types.get(st, 0) + 1

    trend_analysis[topic] = {
        'total_papers': len(results),
        'year_distribution': years,
        'study_types': study_types,
        'avg_quality': sum(estimate_paper_quality(p)[0] for _, _, p in results) / len(results)
    }

# Save analysis
with open('trend_analysis.json', 'w') as f:
    json.dump(trend_analysis, f, indent=2)
```

## Web API Integration

### Flask REST API

Create a REST API wrapper for web applications:

```python
#!/usr/bin/env python3
"""REST API for Research Assistant."""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
sys.path.append('src')

from cli import ResearchCLI
from config import DEFAULT_K

app = Flask(__name__)
CORS(app)  # Enable CORS for web frontends

# Initialize once
kb = ResearchCLI()

@app.route('/api/search', methods=['GET'])
def search():
    """Search endpoint with query parameters."""
    query = request.args.get('q', '')
    top_k = int(request.args.get('k', DEFAULT_K))
    min_year = request.args.get('min_year', type=int)

    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400

    try:
        results = kb.search(query, top_k=top_k, min_year=min_year)

        papers = []
        for idx, dist, paper in results:
            papers.append({
                'id': paper['id'],
                'title': paper['title'],
                'authors': paper.get('authors', []),
                'year': paper.get('year'),
                'relevance': float(1 / (1 + dist)),
                'study_type': paper.get('study_type'),
                'has_full_text': paper.get('has_full_text', False)
            })

        return jsonify({
            'query': query,
            'count': len(papers),
            'papers': papers
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/paper/<paper_id>', methods=['GET'])
def get_paper(paper_id):
    """Get specific paper by ID."""
    try:
        content = kb.get_paper(paper_id)
        return jsonify({'id': paper_id, 'content': content})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/stats', methods=['GET'])
def stats():
    """Get knowledge base statistics."""
    from cli_kb_index import KnowledgeBaseIndex

    index = KnowledgeBaseIndex()
    return jsonify(index.stats())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### FastAPI Alternative

```python
#!/usr/bin/env python3
"""FastAPI implementation with automatic documentation."""

from fastapi import FastAPI, HTTPException, Query
from typing import Optional, List
import sys
sys.path.append('src')

from cli import ResearchCLI

app = FastAPI(title="Research Assistant API", version="4.0")
kb = ResearchCLI()

@app.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    k: int = Query(10, description="Number of results"),
    min_year: Optional[int] = Query(None, description="Minimum publication year")
):
    """Search the knowledge base."""
    results = kb.search(q, top_k=k, min_year=min_year)
    return {
        "query": q,
        "papers": [
            {
                "id": paper["id"],
                "title": paper["title"],
                "relevance": 1 / (1 + dist)
            }
            for _, dist, paper in results
        ]
    }

# Run with: uvicorn api:app --reload
```

## Custom Data Sources

### Building from Non-Zotero Sources

To integrate custom data sources, create a data adapter:

```python
#!/usr/bin/env python3
"""Custom data source adapter."""

import json
from pathlib import Path
from typing import List, Dict, Any

class CustomDataAdapter:
    """Adapter for custom paper sources."""

    @staticmethod
    def from_pubmed_xml(xml_file: Path) -> List[Dict[str, Any]]:
        """Convert PubMed XML to paper format."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_file)
        papers = []

        for article in tree.findall('.//PubmedArticle'):
            paper = {
                'title': article.findtext('.//ArticleTitle', ''),
                'abstract': article.findtext('.//AbstractText', ''),
                'authors': [],
                'year': None,
                'journal': article.findtext('.//Journal/Title', ''),
                'doi': article.findtext('.//ArticleId[@IdType="doi"]', '')
            }

            # Extract authors
            for author in article.findall('.//Author'):
                last = author.findtext('LastName', '')
                first = author.findtext('ForeName', '')
                if last:
                    paper['authors'].append(f"{first} {last}".strip())

            # Extract year
            year_elem = article.find('.//PubDate/Year')
            if year_elem is not None:
                paper['year'] = int(year_elem.text)

            papers.append(paper)

        return papers

    @staticmethod
    def from_csv(csv_file: Path) -> List[Dict[str, Any]]:
        """Import papers from CSV format."""
        import csv

        papers = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                papers.append({
                    'title': row.get('title', ''),
                    'authors': row.get('authors', '').split(';'),
                    'year': int(row.get('year', 0)) if row.get('year') else None,
                    'journal': row.get('journal', ''),
                    'doi': row.get('doi', ''),
                    'abstract': row.get('abstract', ''),
                    'full_text': row.get('full_text', '')
                })

        return papers

# Use with build_kb.py by modifying the process_zotero_local_library method
```

## Performance Tuning

### GPU Memory Optimization

For systems with limited GPU memory:

```python
# In src/build_kb.py, modify get_optimal_batch_size()
def get_optimal_batch_size(self) -> int:
    """Custom batch size for specific GPU."""
    if self.device == "cuda":
        import torch

        # Get available GPU memory
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)

        # Conservative sizing for stability
        if gpu_mem >= 24:  # RTX 3090/4090
            return 512
        elif gpu_mem >= 16:  # High-end GPUs
            return 384
        elif gpu_mem >= 12:  # RTX 3060/4070
            return 256
        elif gpu_mem >= 8:   # Mid-range
            return 128
        else:  # Low-end GPUs
            return 64

    # CPU batch sizing based on RAM
    import psutil
    ram_gb = psutil.virtual_memory().available / (1024**3)

    if ram_gb >= 32:
        return 256
    elif ram_gb >= 16:
        return 128
    else:
        return 64
```

### Large Dataset Processing with Real Checkpoint Recovery (v4.6)

```python
#!/usr/bin/env python3
"""Handle very large datasets with adaptive rate limiting."""

import time
import json
from pathlib import Path

class AdaptiveRateLimiter:
    """Adaptive rate limiting for API requests."""

    def __init__(self, initial_delay=0.1):
        self.delay = initial_delay
        self.processed_count = 0
        self.rate_limit_count = 0
        self.success_count = 0

    def wait_and_adjust(self, response_code=200):
        """Adjust delay based on response patterns."""
        time.sleep(self.delay)

        self.processed_count += 1

        if response_code == 429:  # Rate limited
            self.rate_limit_count += 1
            # Exponential backoff
            self.delay = min(self.delay * 2, 2.0)
        elif response_code == 200:
            self.success_count += 1
            # Adaptive increases after 400 papers
            if self.processed_count > 400:
                self.delay = max(0.5, self.delay)

        # Checkpoint every 50 papers
        if self.processed_count % 50 == 0:
            self.save_checkpoint()

    def save_checkpoint(self):
        """Save processing checkpoint."""
        checkpoint = {
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'rate_limit_count': self.rate_limit_count,
            'current_delay': self.delay
        }

        with open('checkpoint.json', 'w') as f:
            json.dump(checkpoint, f)

    def load_checkpoint(self):
        """Resume from saved checkpoint."""
        checkpoint_path = Path('checkpoint.json')
        if checkpoint_path.exists():
            with open(checkpoint_path) as f:
                checkpoint = json.load(f)
                self.processed_count = checkpoint.get('processed_count', 0)
                self.success_count = checkpoint.get('success_count', 0)
                self.rate_limit_count = checkpoint.get('rate_limit_count', 0)
                self.delay = checkpoint.get('current_delay', 0.1)
            return True
        return False

# Usage for large builds
def process_large_dataset():
    """Process with adaptive rate limiting and checkpoints."""
    limiter = AdaptiveRateLimiter()

    # Resume from checkpoint if exists
    if limiter.load_checkpoint():
        print(f"Resuming from checkpoint: {limiter.processed_count} papers processed")

    # Process each paper with adaptive delays
    for paper in papers[limiter.processed_count:]:
        try:
            response = process_paper_quality_score(paper)
            limiter.wait_and_adjust(response.status_code)
        except Exception as e:
            print(f"Error processing paper {paper['id']}: {e}")
            limiter.wait_and_adjust(500)  # Error case
```

## Large Dataset Optimization

### Streaming Processing for 10,000+ Papers

```python
#!/usr/bin/env python3
"""Handle very large paper collections."""

import json
from pathlib import Path
from typing import Iterator, Dict, Any

class StreamingKnowledgeBase:
    """Memory-efficient KB for large datasets."""

    def __init__(self, kb_path: str = "kb_data"):
        self.kb_path = Path(kb_path)
        self.metadata_file = self.kb_path / "metadata.json"

    def stream_papers(self, batch_size: int = 100) -> Iterator[List[Dict]]:
        """Stream papers in batches to avoid memory issues."""
        with open(self.metadata_file) as f:
            metadata = json.load(f)
            papers = metadata["papers"]

        for i in range(0, len(papers), batch_size):
            yield papers[i:i + batch_size]

    def search_streaming(self, query: str, top_k: int = 10):
        """Search using streaming to handle large indices."""
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/allenai-specter")
        query_embedding = model.encode([query])

        # Load index in chunks
        index = faiss.read_index(str(self.kb_path / "index.faiss"))

        # Search in batches if index is very large
        if index.ntotal > 50000:
            # Implement sharded search
            pass

        return index.search(query_embedding.astype('float32'), top_k)
```

### Index Optimization for Speed

```python
# For very large indices (>100k papers), use IVF index
def build_optimized_index(embeddings, nlist=100):
    """Build IVF index for faster search on large datasets."""
    import faiss
    import numpy as np

    dimension = embeddings.shape[1]

    # Create IVF index with clustering
    quantizer = faiss.IndexFlatL2(dimension)
    index = faiss.IndexIVFFlat(quantizer, dimension, nlist)

    # Train on subset
    training_size = min(50000, len(embeddings))
    training_data = embeddings[np.random.choice(len(embeddings), training_size)]
    index.train(training_data)

    # Add all vectors
    index.add(embeddings)

    # Set search parameters
    index.nprobe = 10  # Search 10 nearest clusters

    return index
```

## Advanced Search Techniques

### Hybrid Search with Keywords and Embeddings

```python
#!/usr/bin/env python3
"""Combine semantic and keyword search."""

from typing import List, Tuple
import re

class HybridSearch:
    """Combine embedding-based and keyword search."""

    def __init__(self, kb_path: str = "kb_data"):
        from cli import ResearchCLI
        self.kb = ResearchCLI(kb_path)
        self.build_keyword_index()

    def build_keyword_index(self):
        """Build inverted index for keyword search."""
        from collections import defaultdict
        import json

        self.keyword_index = defaultdict(set)

        with open(self.kb.metadata_file_path) as f:
            metadata = json.load(f)

        for paper in metadata["papers"]:
            # Index title and abstract
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            words = re.findall(r'\b\w+\b', text.lower())

            for word in words:
                if len(word) > 3:  # Skip short words
                    self.keyword_index[word].add(paper['id'])

    def hybrid_search(
        self,
        query: str,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Combine semantic and keyword scores."""

        # Semantic search
        semantic_results = self.kb.search(query, top_k=top_k * 2)
        semantic_scores = {
            paper['id']: 1 / (1 + dist)
            for _, dist, paper in semantic_results
        }

        # Keyword search
        words = re.findall(r'\b\w+\b', query.lower())
        keyword_scores = defaultdict(float)

        for word in words:
            if word in self.keyword_index:
                for paper_id in self.keyword_index[word]:
                    keyword_scores[paper_id] += 1 / len(words)

        # Combine scores
        final_scores = {}
        all_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())

        for paper_id in all_ids:
            sem_score = semantic_scores.get(paper_id, 0)
            key_score = keyword_scores.get(paper_id, 0)
            final_scores[paper_id] = (
                semantic_weight * sem_score +
                keyword_weight * key_score
            )

        # Sort and return top k
        sorted_results = sorted(
            final_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_results[:top_k]
```

### Query Expansion

```python
def expand_query(query: str) -> List[str]:
    """Expand query with synonyms and related terms."""

    # Medical/scientific term expansion
    expansions = {
        "AI": ["artificial intelligence", "machine learning", "deep learning"],
        "ML": ["machine learning", "artificial intelligence"],
        "RCT": ["randomized controlled trial", "randomised controlled trial"],
        "CVD": ["cardiovascular disease", "heart disease"],
        "T2D": ["type 2 diabetes", "diabetes mellitus type 2"],
    }

    expanded = [query]
    for term, synonyms in expansions.items():
        if term.lower() in query.lower():
            for synonym in synonyms:
                expanded.append(query.replace(term, synonym))

    return expanded
```

## Automation and Scripting

### Automated Literature Monitoring

```python
#!/usr/bin/env python3
"""Monitor for new papers on specific topics."""

import json
import schedule
import time
from datetime import datetime
from pathlib import Path

class LiteratureMonitor:
    """Automated monitoring for new relevant papers."""

    def __init__(self, topics: List[str], output_dir: str = "monitoring"):
        self.topics = topics
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.last_check = self.load_last_check()

    def load_last_check(self):
        """Load timestamp of last check."""
        check_file = self.output_dir / ".last_check"
        if check_file.exists():
            with open(check_file) as f:
                return datetime.fromisoformat(f.read().strip())
        return datetime(2020, 1, 1)

    def check_new_papers(self):
        """Check for new papers since last run."""
        from cli import ResearchCLI

        kb = ResearchCLI()
        new_papers = []

        for topic in self.topics:
            results = kb.search(
                topic,
                top_k=50,
                min_year=self.last_check.year
            )

            for _, _, paper in results:
                # Check if paper is new
                if paper.get('year', 0) >= self.last_check.year:
                    new_papers.append({
                        'topic': topic,
                        'paper': paper
                    })

        if new_papers:
            self.save_alert(new_papers)

        # Update last check
        self.last_check = datetime.now()
        with open(self.output_dir / ".last_check", 'w') as f:
            f.write(self.last_check.isoformat())

    def save_alert(self, papers):
        """Save alert about new papers."""
        alert_file = self.output_dir / f"alert_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(alert_file, 'w') as f:
            json.dump(papers, f, indent=2)

        print(f"Found {len(papers)} new papers! Saved to {alert_file}")

# Schedule monitoring
monitor = LiteratureMonitor([
    "COVID-19 treatment",
    "mRNA vaccines",
    "long COVID"
])

schedule.every(24).hours.do(monitor.check_new_papers)

while True:
    schedule.run_pending()
    time.sleep(3600)  # Check every hour
```

## Troubleshooting

### Common Issues and Solutions

#### Out of Memory During Embedding Generation

```python
# Solution 1: Process in smaller batches
def generate_embeddings_low_memory(texts, batch_size=32):
    """Generate embeddings with minimal memory usage."""
    from sentence_transformers import SentenceTransformer
    import numpy as np

    model = SentenceTransformer("sentence-transformers/allenai-specter")
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(batch)
        all_embeddings.append(embeddings)

        # Force garbage collection
        import gc
        gc.collect()

        if hasattr(torch, 'cuda'):
            torch.cuda.empty_cache()

    return np.vstack(all_embeddings)
```

#### Slow Search Performance

```python
# Solution: Preload and cache the index
class CachedSearch:
    """Cache search index in memory."""

    _instance = None
    _index = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.load_resources()
        return cls._instance

    def load_resources(self):
        """Load and cache expensive resources."""
        import faiss
        from sentence_transformers import SentenceTransformer

        if self._index is None:
            self._index = faiss.read_index("kb_data/index.faiss")

        if self._model is None:
            self._model = SentenceTransformer(
                "sentence-transformers/allenai-specter"
            )

    def search(self, query: str, k: int = 10):
        """Fast search using cached resources."""
        embedding = self._model.encode([query])
        return self._index.search(embedding.astype('float32'), k)
```

#### Corrupted Cache Files

```python
#!/usr/bin/env python3
"""Diagnose and repair cache issues."""

def repair_caches(kb_path: str = "kb_data"):
    """Detect and repair corrupted cache files."""
    from pathlib import Path
    import json

    kb_path = Path(kb_path)
    issues = []

    # Check PDF cache
    pdf_cache = kb_path / ".pdf_text_cache.json"
    if pdf_cache.exists():
        try:
            with open(pdf_cache) as f:
                json.load(f)
        except json.JSONDecodeError:
            issues.append("PDF cache corrupted")
            pdf_cache.rename(pdf_cache.with_suffix('.json.bak'))
            print("Backed up corrupted PDF cache")

    # Check embedding cache
    emb_cache = kb_path / ".embedding_cache.json"
    if emb_cache.exists():
        try:
            with open(emb_cache) as f:
                json.load(f)
        except json.JSONDecodeError:
            issues.append("Embedding cache corrupted")
            emb_cache.unlink()
            print("Removed corrupted embedding cache")

    # Check search cache
    search_cache = kb_path / ".search_cache.json"
    if search_cache.exists():
        try:
            with open(search_cache) as f:
                json.load(f)
        except json.JSONDecodeError:
            issues.append("Search cache corrupted")
            search_cache.unlink()
            print("Removed corrupted search cache")

    if issues:
        print(f"Fixed {len(issues)} cache issues")
        print("Run 'python src/build_kb.py' to rebuild")
    else:
        print("All caches healthy")

    return issues

if __name__ == "__main__":
    repair_caches()
```

## Next Steps

- See [API Reference](api-reference.md) for complete command documentation
- Check [Technical Specs](technical-specs.md) for architecture details
- Review the main [README](../README.md) for quick start guide

For custom implementations or enterprise deployments, consider:
1. Implementing authentication for web APIs
2. Adding database backend for metadata
3. Creating distributed processing for very large datasets
4. Implementing real-time paper ingestion pipelines
