# Changelog

## [Unreleased] - 2025-08-17

### Added
- PyMuPDF for fast PDF text extraction (37x faster than pdfplumber)
- Smart caching system with metadata validation (file size + modification time)
- `--clear-cache` flag to force fresh PDF extraction
- JSON-based cache format for security and transparency
- Proper type hints throughout the codebase
- License notices for PyMuPDF AGPL compliance

### Changed
- Replaced pdfplumber with PyMuPDF for 37x performance improvement
- Cache format changed from pickle to JSON (security fix)
- Improved error handling with specific exception types
- Updated to use `datetime.UTC` for timezone-aware timestamps
- Simplified code structure with `contextlib.suppress`

### Fixed
- Critical security vulnerability: Removed unsafe pickle deserialization
- WSL detection bug that caused crashes on non-Linux systems
- Proper exception handling for file operations
- Type checking errors with mypy

### Performance
- PDF extraction: ~13 papers/second (up from 0.35/second)
- First build: ~5 minutes for 2000 papers
- Cached rebuild: <1 minute
- Cache file size: ~2-3MB per 100 papers

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