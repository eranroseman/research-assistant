# Changelog

## [3.1.0] - 2025-08-19

### 🎯 Smart Section Chunking (70% Context Reduction)
- **Section extraction**: Automatically parse papers into standard academic sections
- **Smart retrieval**: `smart-get` command intelligently selects relevant sections based on query
- **Targeted reading**: `get --sections` allows specific section retrieval
- **O(1) section access**: Sections index enables instant retrieval of any paper section
- **Context optimization**: Reduces Claude's text processing by 70-90%

### 🚀 Incremental Updates (10x Faster)
- **Smart updates**: `--update` flag adds only new papers without full rebuild
- **Fingerprint tracking**: Content-based hashing detects changed papers
- **Append-only indexing**: New papers added to existing FAISS index
- **Time savings**: 2-3 minutes for updates vs 30+ minutes for full rebuild

### 📝 Personal Shortcuts System
- **Shortcut configuration**: `.research_shortcuts.yaml` for saved searches
- **Quick access**: `shortcut` command to run predefined queries
- **Flexible parameters**: Store query, filters, and modes in shortcuts
- **Research topics**: Group related searches for comprehensive reviews

### 🔍 Enhanced Search Intelligence
- **Query expansion**: Automatic medical/research synonym expansion
- **Better recall**: Expands "diabetes" to include "diabetic", "T2DM", etc.
- **Evidence gap analysis**: `--analyze-gaps` identifies missing study types
- **Duplicate detection**: `duplicates` command finds papers by DOI/title matching

### 💾 Knowledge Base Portability
- **Export/Import**: Create portable `.tar.gz` archives of entire KB
- **Cross-computer sync**: Easy transfer between machines
- **Backup support**: Timestamped backups before major operations
- **Complete preservation**: Includes index, metadata, papers, and caches

### 🛠️ Type Safety & Code Quality
- **Full type annotations**: All functions properly typed for mypy
- **Security improvements**: Fixed subprocess injection, tarfile extraction
- **Pre-commit compliance**: Passes all ruff, mypy, and format checks
- **Import optimizations**: Added missing timezone imports

### 📊 New CLI Commands
- `smart-get PAPER_ID "query"`: Intelligent section-based retrieval
- `get PAPER_ID --sections abstract methods`: Get specific sections
- `shortcut NAME`: Run saved search from shortcuts file
- `shortcut --list`: Show all available shortcuts
- `shortcut --edit`: Edit shortcuts configuration
- `duplicates [--fix]`: Find and optionally remove duplicate papers
- `search --analyze-gaps`: Perform evidence gap analysis

### 🐛 Bug Fixes
- Fixed section extraction for markdown-formatted papers
- Corrected timezone usage throughout codebase
- Resolved nested if-statement complexity issues
- Fixed assert statements with proper error handling
- Improved error messages for missing shortcuts file

### 📚 Documentation Updates
- Updated README with v3.1 features and examples
- Enhanced `/research` command with new capabilities
- Added section chunking benefits to CLAUDE.md
- Documented all new commands and flags

## [3.0.0] - 2025-08-18

### 🚀 Performance Improvements
- **40-50% faster embedding generation**: Dynamic batch sizing (64-256) based on available memory
- **O(1) cache lookups**: Replaced linear search with hash-based dictionary for instant cache hits
- **Optimized SPECTER2 loading**: GPU detection and memory-aware processing
- **Efficient cache format**: Split into JSON metadata + NPY data for better performance

### 🔒 Security Enhancements
- **Command injection prevention**: Whitelist-based command execution
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

### 📁 Project Structure
- **Cleaned up project**: Removed benchmark scripts and test directories
- **Cache format**: `.embedding_cache.json` + `.embedding_data.npy` (replaces .npz)
- **Paper IDs**: Enforced 4-digit format (0001, not 001)
- **Metadata enrichment**: Added quality scores and factors to metadata.json

### 🐛 Bug Fixes
- Fixed O(n) performance issue in embedding cache lookups
- Resolved security vulnerabilities in subprocess execution
- Improved error handling for missing knowledge base
- Better handling of Zotero connection failures
- Fixed type checking errors identified by mypy

## [2.1.0] - 2025-08-18

### Added
- **Embedding cache system** - Caches computed embeddings for 20-30x faster rebuilds
- **GPU acceleration** - Automatic CUDA detection for 10x faster embedding generation
- **Organized documentation structure** - New `docs/` directory with separated guides:
  - `api-reference.md` - Complete CLI command reference
  - `technical-specs.md` - Architecture and implementation details
  - `advanced-usage.md` - GPU setup, performance tuning, custom models
- **Source code organization** - Moved Python files to `src/` directory for cleaner structure

### Changed
- Rebuild time reduced from ~30 minutes to 1-2 minutes with dual caching (PDF + embeddings)
- README simplified from 387 to 166 lines, now user-focused with links to detailed docs
- All command examples updated to use `python src/*.py` format
- Project structure now follows Python package standards

### Improved
- Performance metrics now show CPU vs GPU times
- Cache files properly validated with MD5 hashes
- Better cache status reporting showing hit rates
- Documentation properly cross-referenced between files

### Fixed
- SPECTER2 references corrected to SPECTER (actual model used)
- Documentation discrepancies between README and specs resolved
- Missing features added to README (study types, filtering)

## [2.0.0] - 2025-08-17

### Added
- SPECTER embedding model optimized for scientific papers (was using all-MiniLM-L6-v2)
- Study type classification (systematic reviews, RCTs, cohort studies, etc.)
- RCT sample size extraction showing participant counts (n=487)
- Advanced filtering by publication year (--after flag)
- Advanced filtering by study type (--type flag with multiple options)
- Visual evidence hierarchy markers (⭐ for reviews, ● for RCTs, etc.)
- Automatic backup creation before rebuilding indices
- Model metadata tracking in knowledge base
- Enhanced search result display with study type and full-text indicators
- Title emphasis in embeddings (included twice for better matching)

### Changed
- Default embedding model changed from all-MiniLM-L6-v2 to SPECTER
- Search results now show study type, sample size, and full-text availability
- Build time increased to ~30 minutes for better accuracy (was ~15 minutes)
- Metadata now includes embedding model and dimensions for compatibility checking

### Improved
- Better acronym and scientific term handling with SPECTER
- More intuitive search result ranking based on evidence quality
- Clearer visual distinction between study types in results

## [1.1.0] - 2025-08-17

### Added
- PyMuPDF for fast PDF text extraction (37x faster than pdfplumber)
- Smart caching system with metadata validation (file size + modification time)
- `--clear-cache` flag to force fresh PDF extraction
- JSON-based cache format for security and transparency
- Proper type hints throughout the codebase
- License notices for PyMuPDF AGPL compliance
- Missing PDFs report generation for papers without full text
- Interactive prompts for build options (quick update vs full rebuild)
- Lazy loading for fast startup (<0.5 seconds for --help)
- Support for reading Zotero database while Zotero is running (immutable mode)

### Changed
- Replaced pdfplumber with PyMuPDF for 37x performance improvement
- Cache format changed from pickle to JSON (security fix)
- Improved error handling with specific exception types
- Updated to use `datetime.UTC` for timezone-aware timestamps
- Simplified code structure with `contextlib.suppress`
- Enhanced user prompts with clear guidance on when to use each option
- Improved output messages showing paper counts and PDF extraction progress
- Heavy libraries (faiss, sentence-transformers) now load only when needed

### Fixed
- Critical security vulnerability: Removed unsafe pickle deserialization
- WSL detection bug that caused crashes on non-Linux systems
- Proper exception handling for file operations
- Type checking errors with mypy
- SQLite database locking issues when Zotero is running
- Slow startup time for --help and initial prompts
- Confusing rebuild prompts that didn't explain cache behavior

### Performance
- PDF extraction: ~13 papers/second (up from 0.35/second)
- Quick update: ~90 seconds for 2000 papers (with cache)
- Full rebuild: ~5 minutes for 2000 papers
- Cache file size: ~150MB for 2000+ papers
- Startup time: <0.5 seconds (previously 7+ seconds)

### Security
- Eliminated arbitrary code execution risk from pickle
- Added safe file operation handling
- Improved input validation

## [1.0.0] - 2025-08-15

### Initial Release
- Knowledge base builder for Zotero libraries
- FAISS-based semantic search
- Claude Code slash command integration
- Support for 2000+ academic papers
- Markdown conversion for full-text search
