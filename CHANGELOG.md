# Changelog

## [Unreleased] - 2025-08-17

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