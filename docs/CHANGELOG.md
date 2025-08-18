# Changelog

All notable changes to the Research Assistant project are documented here.

## [3.0.0] - 2025-08-18

### 🚀 Performance Improvements
- **40-50% faster embedding generation**: Dynamic batch sizing (64-256) based on available memory
- **O(1) cache lookups**: Replaced linear search with hash-based dictionary for instant cache hits
- **Optimized SPECTER2 loading**: GPU detection and memory-aware processing
- **Efficient cache format**: Split into JSON metadata + NPY data for better performance

### 🔒 Security Enhancements
- **Command injection prevention**: Whitelist-based command execution in demo.py
- **Path traversal protection**: Strict 4-digit paper ID validation in cli.py
- **Safe serialization**: Replaced pickle with JSON/NPY format (CVE prevention)
- **Input validation**: All user inputs now properly validated and sanitized

### 🔍 SPECTER2 Intelligence
- **Smart search modes**: Automatically detects query intent
  - `question`: Optimized for research questions
  - `similar`: Find papers similar to a topic
  - `explore`: Broad exploration of research areas
  - `auto`: Intelligent mode selection (default)
- **Query preprocessing**: Mode-specific query optimization for better results
- **Graceful fallback**: Automatically uses SPECTER if SPECTER2 unavailable

### 📊 Quality Assessment System
- **Paper quality scores**: 0-100 scoring based on:
  - Study type hierarchy (35 points max)
  - Publication recency (10 points for 2022+)
  - Sample size (10 points for n>1000)
  - Full text availability (5 points)
- **Quality filtering**: `--quality-min` parameter to filter low-quality papers
- **Visual indicators**: ⭐ (80-100), ● (60-79), ○ (40-59), · (<40)

### 🛠️ API Enhancements
- **New CLI parameters**:
  - `--mode [auto|question|similar|explore]`: Search mode selection
  - `--show-quality`: Display quality scores in results
  - `--quality-min N`: Filter by minimum quality score
- **Enhanced `/research` command**: v3.0 features integrated into slash command
- **Better error messages**: Clear, actionable error messages with recovery suggestions

### 📁 Data Structure Changes
- **Cache format**: `.embedding_cache.json` + `.embedding_data.npy` (replaces .npz)
- **Paper IDs**: Enforced 4-digit format (0001, not 001)
- **Metadata enrichment**: Added quality scores and factors to metadata.json

### 🐛 Bug Fixes
- Fixed O(n) performance issue in embedding cache lookups
- Resolved security vulnerabilities in subprocess execution
- Improved error handling for missing knowledge base
- Better handling of Zotero connection failures

### 📝 Documentation
- Removed obsolete implementation/review documents
- Updated technical specifications for v3.0
- Enhanced API reference with new parameters
- Updated `/research` command with quality-driven workflow

## [2.0.0] - 2025-01-17

### Features
- **SPECTER Embeddings**: Scientific paper-optimized semantic search
- **Study Type Classification**: Automatic detection of systematic reviews, RCTs, etc.
- **RCT Sample Size Extraction**: Shows participant counts for trials
- **Advanced Filtering**: Filter by publication year and study type
- **Evidence Hierarchy**: Visual markers for study quality
- **Dual Caching**: PDF text cache + embedding cache for faster rebuilds

### Improvements
- Title emphasis in embeddings for better keyword matching
- Automatic backups before rebuilding indices
- Interactive build options for Zotero integration
- Support for 2000+ papers in knowledge base

## [1.0.0] - 2025-01-15

### Initial Release
- Basic knowledge base builder from Zotero
- FAISS-based semantic search
- IEEE citation generation
- Claude Code slash command integration
- PDF to markdown conversion
- Basic search and retrieval functionality
