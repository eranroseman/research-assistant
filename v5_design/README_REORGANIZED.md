# Research Assistant v5.0 - Documentation

A streamlined, production-ready literature extraction and enrichment pipeline with GROBID TEI processing and multi-source metadata enrichment.

## 🚀 Quick Start

```bash
# 1. Start GROBID server (required)
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

# 2. Run complete pipeline with checkpoint support (RECOMMENDED)
python src/extraction_pipeline_runner_checkpoint.py

# 3. Resume after interruption (automatic)
python src/extraction_pipeline_runner_checkpoint.py --pipeline-dir extraction_pipeline_20250901
```

## 📊 Pipeline Performance

| Stage | Time | Success Rate | Output |
|-------|------|-------------|---------|
| **GROBID TEI** | ~10 hours | 100% | 2,210 papers |
| **JSON Extraction** | ~30 min | 86% | Structure parsing |
| **CrossRef** | ~2 hours | 72% | DOI matching |
| **Multi-API Enrichment** | ~5 hours | 65-98% | Various sources |
| **Total Pipeline** | ~15 hours | **97.7%** | ~2,160 papers |

## 📚 Documentation Structure

### 1️⃣ Getting Started
- **[01_system_overview.md](01_system_overview.md)** - Architecture, philosophy, and v4→v5 migration
- **[02_grobid_extraction.md](02_grobid_extraction.md)** - GROBID configuration and TEI extraction
- **[03_installation_setup.md](03_installation_setup.md)** - Setup, requirements, and troubleshooting

### 2️⃣ Core Pipeline
- **[04_extraction_optimizations.md](04_extraction_optimizations.md)** - Extraction optimization strategies
- **[09_complete_workflow.md](09_complete_workflow.md)** - Complete step-by-step workflow
- **[11_pipeline_architecture.md](11_pipeline_architecture.md)** - Detailed pipeline architecture

### 3️⃣ Enrichment & Processing
- **[14_zotero_integration.md](14_zotero_integration.md)** - Zotero metadata recovery
- **[15_s2_optimization_complete.md](15_s2_optimization_complete.md)** - Semantic Scholar optimization
- **[16_extended_enrichment_pipeline.md](16_extended_enrichment_pipeline.md)** - Multi-API enrichment
- **[17_api_evaluation_summary.md](17_api_evaluation_summary.md)** - API evaluation and selection

### 4️⃣ Quality & Recovery
- **[12_quality_filtering_stage.md](12_quality_filtering_stage.md)** - Paper classification and filtering
- **[18_checkpoint_recovery_system.md](18_checkpoint_recovery_system.md)** - Checkpoint and recovery system
- **[19_pipeline_completeness_analysis.md](19_pipeline_completeness_analysis.md)** - Completeness analysis
- **[20_simplified_post_processing_final.md](20_simplified_post_processing_final.md)** - Production post-processing

### 5️⃣ Implementation & Optimization
- **[06_commands_reference.md](06_commands_reference.md)** - Complete CLI documentation
- **[24_checkpoint_performance_analysis.md](24_checkpoint_performance_analysis.md)** - Performance tuning
- **[34_40_line_pipeline_display.md](34_40_line_pipeline_display.md)** - Dashboard UI implementation
- **[36_logging_display_implementation.md](36_logging_display_implementation.md)** - Logging system

### 6️⃣ Reference Documents
- **[08_final_pipeline_results.md](08_final_pipeline_results.md)** - Complete pipeline statistics
- **[10_comprehensive_extraction_fix.md](10_comprehensive_extraction_fix.md)** - Critical metadata fix
- **[13_filtering_rationale.md](13_filtering_rationale.md)** - Filtering decision rationale
- **[25_arxiv_optimization_results.md](25_arxiv_optimization_results.md)** - arXiv batch optimization

## 🗂️ Pipeline Directory Structure

```
extraction_pipeline_YYYYMMDD/
├── 01_tei_xml/              # GROBID TEI XML (100% success)
├── 02_json_extraction/      # TEI → JSON (86% extraction)
├── 03_zotero_recovery/      # Metadata recovery (91% improved)
├── 04_crossref_enrichment/  # DOI enrichment (72% matched)
├── 05_s2_enrichment/        # Semantic Scholar (94% enriched)
├── 06_openalex_enrichment/  # Topics & SDGs (98% classified)
├── 07_unpaywall_enrichment/ # Open access (52% OA found)
├── 08_pubmed_enrichment/    # Biomedical (30% medical papers)
├── 09_arxiv_enrichment/     # Preprints (15% STEM papers)
└── 10_final_output/         # Merged results (~2,160 papers)
```

## 🔑 Key Features

| Feature | Description | Impact |
|---------|------------|---------|
| **Checkpoint Recovery** | Auto-resume from any stage | Zero data loss |
| **Batch Processing** | Efficient API calls | 60x speedup |
| **Quality Filtering** | Remove non-articles | 97% precision |
| **Incremental Updates** | Process only new papers | 5-min updates |
| **40-Line Dashboard** | Clean progress display | Professional UX |

## 💡 Key Insights

- **Philosophy**: Maximum extraction over speed (we run GROBID rarely)
- **Success Rate**: 97.7% overall (industry-leading, typical is 85-90%)
- **Data Completeness**: 94.77% all critical fields
- **Full Text**: 99.72% extraction success
- **Root Cause**: 0.7% unfixable (scanned/encrypted PDFs)
- **Two-Pass Strategy**: GROBID retry IS the fallback (90s → 180s timeout)

## 🛠️ Core Scripts

### Essential Pipeline Scripts
```bash
# Main pipeline runner with checkpoints
extraction_pipeline_runner_checkpoint.py

# Individual stage processors
comprehensive_tei_extractor_checkpoint.py  # TEI → JSON extraction
crossref_batch_enrichment_checkpoint.py    # CrossRef batch API
s2_batch_enrichment.py                     # Semantic Scholar
openalex_enricher.py                       # OpenAlex topics
unpaywall_enricher.py                      # Open access
pubmed_enricher.py                         # Biomedical
arxiv_enricher.py                          # Preprints
```

### Utility Scripts
```bash
# Analysis and quality control
analyze_pipeline_completeness.py           # Coverage metrics
analyze_problematic_papers.py              # Identify issues
filter_non_articles.py                     # Remove books/proceedings
final_cleanup_no_title.py                  # Ensure 100% titles

# Recovery and fixes
run_full_zotero_recovery.py               # Metadata recovery
fix_malformed_dois.py                     # DOI cleaning
recover_dois_crossref.py                  # Missing DOI recovery
```

## 🏆 Production Results

- **Input**: 2,210 Zotero papers
- **GROBID Success**: 2,210 (100%)
- **Extracted**: ~1,900 (86%)
- **Enriched**: ~2,160 (97.7%)
- **Final Quality**: 2,150 research articles
- **Data Volume**: 83.8M characters
- **Processing Time**: ~15 hours total

## 📈 Development Standards

```bash
# Required before committing
mypy src/                    # Type checking (passing)
ruff check src/ --fix        # Linting
pre-commit run --all-files   # All hooks
```

## 🚦 System Requirements

- Python 3.11+
- GROBID server (Docker)
- 16GB RAM recommended
- ~10GB disk space
- Internet for API enrichment

## 📝 Version History

- **v5.0** (Sep 2025) - Production-ready pipeline
  - 97.7% success rate achieved
  - Checkpoint recovery implemented
  - Multi-API enrichment complete
  - 40-line dashboard UI
- **v4.6** - Previous version (deprecated)

---

*For detailed documentation on any topic, refer to the numbered documents in this directory.*
