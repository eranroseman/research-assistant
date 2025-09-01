# V5 Post-Processing Pipeline Design

**Note: This document represents the original complex design. For the production implementation, see [22_simplified_post_processing_final.md](22_simplified_post_processing_final.md) which incorporates lessons learned and real-world usage patterns.**

## Overview
Post-processing pipeline for the V5 extraction system that prioritizes quality outcomes over processing speed. Takes enriched JSON data from Grobid/API extraction and produces a production-ready knowledge base.

## Design Principles
1. **Quality First**: Process all content before filtering to maximize signal extraction
2. **Content-Aware Scoring**: Use actual content quality to inform filtering decisions
3. **Efficient Filtering**: Filter after quality scoring but before expensive embeddings
4. **Comprehensive Analytics**: Maintain quality scores for all papers for analysis

## Pipeline Architecture

```
extraction_pipeline_20250901/
├── 08_pubmed_enrichment/        # Input: Enriched JSON files
└── post_processing/
    ├── 11_validated_data/       # Stage 1: Data Validation & Cleaning
    ├── 12_processed_content/    # Stage 2: Content Processing (ALL papers)
    ├── 13_quality_scored/       # Stage 3: Quality Assessment (content-aware)
    ├── 14_filtered_papers/      # Stage 3.5: Apply quality threshold
    ├── 15_embeddings/          # Stage 4: Embedding Generation (filtered only)
    ├── 16_indexes/             # Stage 5: Index Building
    ├── 17_knowledge_synthesis/  # Stage 6: Knowledge Synthesis
    ├── 18_final_kb/            # Stage 7: Export Generation
    └── 19_qa_reports/          # Stage 8: Quality Control
```

## Stage Specifications

### Stage 1: Data Validation & Cleaning
**Input**: `08_pubmed_enrichment/*.json`
**Output**: `11_validated_data/*.json`
**Operations**:
- Validate JSON structure and required fields
- Remove duplicates (by DOI, then title similarity >95%)
- Fix malformed data (dates, DOIs, author names)
- Normalize author names and affiliations
- Language detection and filtering
- **Time**: ~1 minute for 2000 papers
- **Checkpoint**: Every 100 papers

### Stage 2: Content Processing
**Input**: `11_validated_data/*.json`
**Output**: `12_processed_content/*.json`
**Operations**:
- Extract and clean full text sections
- Smart chunking (50KB limit per section)
- Extract structured information:
  - Research methods and tools
  - Key findings and conclusions
  - Datasets and code repositories mentioned
  - Statistical methods used
- Generate keywords (TF-IDF only, skip BERT for speed)
- **Time**: ~7 minutes for 2000 papers (auto-scales to 16 cores if available)
- **Checkpoint**: Every 50 papers
- **Error handling**: Skip failed papers, log to `papers_failed.json`

### Stage 3: Quality Assessment
**Input**: `12_processed_content/*.json`
**Output**: `13_quality_scored/*.json`
**Quality Score Components** (0-100):
```python
quality_score = {
    # Metadata-based (50 points)
    "citation_impact": 20,      # Normalized by field/year
    "venue_quality": 10,        # Journal impact factor
    "author_metrics": 10,       # H-index, affiliation
    "recency": 10,              # Years since publication

    # Content-based (50 points)
    "extraction_quality": 15,   # Grobid success, completeness
    "methodology_rigor": 15,    # Study design detection
    "content_depth": 10,        # Section completeness
    "relevance": 10,           # Domain-specific keywords
}
```
**Time**: ~2 minutes for 2000 papers
**Checkpoint**: Every 100 papers

### Stage 3.5: Quality Filtering
**Input**: `13_quality_scored/*.json`
**Output**: `14_filtered_papers/*.json`
**Operations**:
- Apply configurable quality threshold (CLI flag: `--quality-threshold`, default: 30)
- Save filtering report with statistics
- Preserve full quality distribution data
- **Expected**: Keep ~60-70% of papers (1200-1400 from 2000)

### Stage 4: Embedding Generation
**Input**: `14_filtered_papers/*.json`
**Output**: `15_embeddings/`
**Operations**:
- Generate embeddings using Multi-QA MPNet
  - Paper-level: title + abstract
  - Section-level: each major section
  - Chunk-level: for sections >2000 tokens
- Cache embeddings in `.npy` format
- GPU acceleration when available
- **Time**: ~7 minutes for 1400 papers (GPU)
- **Checkpoint**: Every 50 papers

### Stage 5: Index Building
**Input**: `15_embeddings/` + `14_filtered_papers/*.json`
**Output**: `16_indexes/`
**Components**:
- FAISS vector index for semantic search
- Metadata index for filtering
- Full-text search index (Whoosh/SQLite FTS)
- Citation graph (NetworkX)
- **Time**: ~2 minutes for 1400 papers

### Stage 6: Knowledge Synthesis
**Input**: All processed data
**Output**: `17_knowledge_synthesis/`
**Analytics**:
- Gap analysis: Identify under-researched areas
- Topic modeling: LDA/BERTopic clustering
- Trend analysis: Research evolution over time
- Quality distribution: Score patterns by topic/year
- Citation network: Key papers and connections
- **Time**: ~3 minutes

### Stage 7: Export Generation
**Input**: All stages
**Output**: `18_final_kb/`
**Formats**:
- Primary KB format (JSON with embeddings)
- Markdown summaries per paper
- BibTeX/RIS for reference managers
- API-ready paginated JSON
- Statistics and coverage report
- **Time**: ~1 minute

### Stage 8: Quality Control
**Input**: `18_final_kb/`
**Output**: `19_qa_reports/`
**Validation**:
- Test search functionality
- Verify index integrity
- Check data completeness
- Generate quality metrics report
- Coverage analysis vs original Zotero library
- **Time**: ~1 minute

## Performance Specifications

### Time Estimates (2000 papers, 8 cores)
```
Stage 1: Validation        ~1 min
Stage 2: Content          ~7 min
Stage 3: Quality          ~2 min
Stage 4: Embeddings       ~7 min (1400 papers after filtering)
Stage 5: Indexing         ~2 min
Stage 6: Synthesis        ~3 min
Stage 7: Export           ~1 min
Stage 8: QA               ~1 min
---------------------------------
Total:                   ~24 minutes
```

### Resource Requirements
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: ~500MB for processed data + indexes
- **GPU**: Optional but 10x faster for embeddings
- **CPU**: Benefits from multiple cores (up to 16)

## Configuration Schema

```python
{
    "pipeline": {
        "checkpoint_frequency": 50,
        "parallel_workers": "auto",  # Auto-scales to min(cpu_count(), 16)
        "gpu_enabled": true,
        "show_progress": true  # Enable tqdm progress bars
    },
    "validation": {
        "required_fields": ["title", "abstract", "authors"],
        "duplicate_threshold": 0.95,
        "min_abstract_length": 100
    },
    "quality": {
        "threshold": 30,  # Overridable via CLI --quality-threshold
        "weights": {
            "citation_impact": 20,
            "venue_quality": 10,
            # ... etc
        }
    },
    "embeddings": {
        "model": "sentence-transformers/multi-qa-mpnet-base-dot-v1",
        "batch_size": 32,
        "max_seq_length": 512
    },
    "export": {
        "formats": ["json", "markdown", "bibtex"],
        "compress": true
    }
}
```

## Error Recovery

Each stage implements:
1. **Checkpointing**: Save progress every N papers
2. **Resumption**: Continue from last checkpoint on failure
3. **Partial Processing**: Skip already-processed papers
4. **Error Logging**: Failed papers saved to `papers_failed.json` with error details
5. **Graceful Degradation**: Pipeline continues even if individual papers fail
6. **Progress Tracking**: Visual progress bars (tqdm) for all stages

## Incremental Updates

For adding new papers to existing KB:
1. New papers enter at Stage 1
2. Reuse existing embeddings/indexes where possible
3. Update only affected indexes
4. Merge with existing KB
5. **Time**: ~2-3 minutes per 100 new papers

## Quality Metrics

Track and report:
- Papers processed vs filtered at each stage
- Quality score distribution
- Processing time per stage
- Error rates and types
- Coverage vs original library
- Embedding quality (via clustering metrics)

## Implementation Priority

1. **Phase 1**: Core pipeline (Stages 1-3) - Data processing and quality
2. **Phase 2**: Search capabilities (Stages 4-5) - Embeddings and indexing
3. **Phase 3**: Analytics (Stage 6) - Knowledge synthesis
4. **Phase 4**: Polish (Stages 7-8) - Export formats and QA

## Design Decisions

### Why Filter After Quality Scoring?
- **Balanced approach**: Get content signals for scoring, but don't waste compute on embeddings
- **Saves ~3 minutes**: Don't embed 600 filtered papers
- **Preserves analytics**: Still have quality scores for all papers
- **Clean architecture**: Downstream stages only process "good" data

### Why Process All Content First?
- **Better scoring**: Content quality informs the score
- **No premature filtering**: Might rescue papers with poor metadata but good content
- **Complete picture**: Understanding what we're filtering out is valuable
- **One-time cost**: Build process runs infrequently, quality matters more than speed

### Why This Stage Order?
1. Validation before processing: Clean data prevents downstream errors
2. Content before quality: Need content signals for accurate scoring
3. Filter before embeddings: Most expensive operation, minimize waste
4. Embeddings before synthesis: Need vectors for clustering/similarity
5. Synthesis before export: Insights inform final KB structure
6. QA last: Validate the complete pipeline output

## Implementation Simplifications

Based on practical experience, the following simplifications improve the pipeline:

### Essential Features Only
1. **Error Handling**: Papers that fail processing are logged to `papers_failed.json` and skipped
2. **Progress Bars**: tqdm provides visual feedback during long operations
3. **CLI Configuration**: Quality threshold adjustable via `--quality-threshold` flag
4. **Auto-scaling**: Automatically uses up to 16 cores if available

### Avoided Complexity
- **No abstract similarity deduplication**: Title + DOI matching is sufficient (adds complexity for ~5 duplicates)
- **No BERT keywords**: TF-IDF is 10x faster with similar quality
- **No distributed processing**: 24 minutes is acceptable for full rebuild
- **No complex monitoring**: tqdm progress bars provide sufficient feedback
- **No ML-based quality scoring**: Formula-based scoring is interpretable and tunable

### Usage Example
```bash
# Standard run with default settings
python post_process.py --input extraction_pipeline_20250901/08_pubmed_enrichment

# Adjust quality threshold for different use cases
python post_process.py --input extraction_pipeline_20250901/08_pubmed_enrichment --quality-threshold 40

# Resume from checkpoint after interruption
python post_process.py --input extraction_pipeline_20250901/08_pubmed_enrichment --resume
```
