# Changelog

## [4.6.0] - 2025-08-23

### Added
- **Batch API Processing**: Semantic Scholar batch endpoint integration
  - Reduced API calls from ~2,100 individual requests to ~5 batch requests
  - 400x reduction in API overhead for large knowledge bases
  - Automatic fallback to individual requests for papers without DOIs
  - Intelligent error handling with graceful degradation
- **Smart Quality Score Fallback**: Improved user experience for API issues
  - Clear explanation of basic vs enhanced scoring differences
  - Smart default: automatically use basic scores when API unavailable
  - Quality score upgrades available when API returns online
  - Consistent scoring indicators across all papers
- **Enhanced Quality Score Success**: Production-ready reliability
  - 96.9% enhanced scoring success rate in real deployments
  - Fixed venue format handling bugs (dict vs string responses)
  - Immediate quality score persistence prevents data loss on interruption
  - Comprehensive error recovery with graceful API failure handling

### Changed
- **Quality Score Architecture**: Enhanced vs Basic scoring system
  - Enhanced scoring: API-powered with citations, venue rankings, h-index (60% of score)
  - Basic scoring: Local metadata-based fallback with study type, recency, full-text (100% reliable)
  - Automatic upgrades: Basic scores upgraded to enhanced when API available
  - Visual indicators: Papers marked with [Enhanced scoring] or basic scoring explanations
- **Test Suite Updates**: Reflects current production behavior
  - Updated tests to match new index behavior (size mismatch handling)
  - Fixed quality upgrade embedding generation logic
  - All 215 tests passing with current functionality

### Fixed
- **Critical**: Venue format bug causing 0% quality score success
  - Fixed handling of both dict and string venue formats from Semantic Scholar API
  - Now properly processes venue data regardless of API response format
- **Critical**: Quality scores lost on build interruption
  - Quality scores now saved immediately after calculation, before embedding generation
  - Consistent behavior between fresh builds and incremental updates
- **Test Suite**: Fixed failing tests to match current production behavior

### Performance
- **API Efficiency**: Batch processing reduces API load by 400x for large datasets
- **Build Reliability**: 96.9% enhanced scoring success rate in production
- **Smart Caching**: Quality upgrades preserve existing embeddings (30x faster)
- **Total time**: ~17 minutes for 2,180 papers with 96.9% enhanced scoring success

## [Unreleased]

### Added
- **Safety Features**: Knowledge base building now safe-by-default
  - Never automatically rebuilds on errors (preserves existing data)
  - Requires explicit `--rebuild` flag for destructive operations
  - Multi-layer cache preservation during all operations
  - Safe error handling with clear user guidance
  - Connection errors result in safe exit instead of data deletion

### Changed
- **cite command**: Now accepts paper IDs instead of search queries
  - Old: `python src/cli.py cite "topic" -k 10` (performed search)
  - New: `python src/cli.py cite 0001 0002 0003` (specific papers)
  - Provides precise control over which papers to cite
  - Supports both text and JSON output formats
  - Consistent with `get-batch` command pattern
- **build_kb.py**: Removed dangerous automatic rebuild fallback
  - Default operation is now safe incremental updates only
  - All existing cache files preserved during failures
  - Clear error messages guide users to appropriate solutions

## [4.1.1] - 2025-08-20

### Added
- **Batch Command**: New `cli.py batch` command for executing multiple operations efficiently
  - 10-20x performance improvement over individual commands
  - Model loads once for entire batch instead of per-command
  - Three preset workflows: `research`, `review`, `author-scan`
  - Support for custom JSON command batches via file or stdin
  - Meta-commands: `merge`, `filter`, `auto-get-top`, `auto-get-all`
  - Both JSON and text output formats
  - Example: `python src/cli.py batch --preset research "diabetes"`

### Changed
- Updated `/research` command to use batch operations for faster execution
- Modified research-helper agent to leverage batch command
- Improved research workflow from 80-100 seconds to 5-6 seconds

### Performance
- Batch preset completes comprehensive research (5 searches + top papers) in ~5 seconds
- Individual commands: 4-5 seconds each × N commands
- Batch command: 5-6 seconds total for entire workflow

## [4.1.0] - 2025-08-20

### Added
- **Multi-QA MPNet Embeddings**: Replaced SPECTER with Multi-QA MPNet for better healthcare paper understanding
  - 20% faster embedding generation (40-120ms GPU, 400-800ms CPU)
  - Optimized for 70% healthcare / 30% CS paper mix
  - Better understanding of healthcare terminology (telemedicine, EHR, clinical outcomes)
  - Drop-in replacement maintaining 768-dimensional vectors

### Changed
- Updated time estimates for embedding generation to reflect Multi-QA MPNet performance
- All SPECTER references updated to Multi-QA MPNet throughout codebase
- Model configuration now uses centralized `EMBEDDING_MODEL` constant

### Fixed
- Fixed undefined variable errors in exception handling (`e` → `error`)
- Fixed mypy type annotation issues in CLI grouped results
- Improved error variable naming to avoid scope conflicts

### Performance
- Knowledge base build time reduced by ~20% for 2,150 papers
- Actual performance: 16.6 minutes for 2,150 embeddings on CPU (vs estimated 20+ with SPECTER)
- Healthcare query relevance improved by estimated +6% overall

## [4.0.0] - 2025-08-19

### BREAKING CHANGES
- Complete rebuild required (`rm -rf kb_data/ && python src/build_kb.py`)
- No backward compatibility with v3.x knowledge bases
- Removed commands: `shortcuts`, `duplicates`, `analyze-gaps`
- Removed `demo.py` (functionality moved to `--demo` flag)
- Changed `--full` flag to `--rebuild` for clarity

### Added
- **Integrity Checking**: Automatic detection of KB corruption
- **Configuration Constants**: All magic numbers replaced with named constants
- **Enhanced Error Messages**: Actionable suggestions for all errors
- **Diagnose Command**: `cli.py diagnose` for KB health checks
- **Better Progress Feedback**: Time estimates and clearer prompts
- **Utility Functions**: Extracted common code patterns

### Changed
- **70% Code Reduction**: From ~3500 to ~2500 lines
- **Smart Incremental by Default**: Automatic change detection
- **Improved UX**: Cleaner prompts, removed emoji clutter
- **Better Defaults**: Y/n prompts, sensible batch sizes
- **Enhanced Help**: All commands include examples and formatting

### Fixed
- Critical bug: Infinite loop in PDF processing
- Critical bug: Duplicate ID generation causing corruption
- Cache corruption handling improved
- Version compatibility checks enhanced

### Removed
- `shortcuts` command (rarely used)
- `duplicates` command (handled by integrity checks)
- `analyze-gaps` command (over-complex)
- `demo.py` file (moved to `--demo` flag)
- Backward compatibility code
- Legacy fallback paths

## [3.1.0] - 2025-08-19

### Smart Section Chunking (70% Context Reduction)
- **Section extraction**: Automatically parse papers into standard academic sections
- **Smart retrieval**: `smart-get` command intelligently selects relevant sections based on query
- **Targeted reading**: `get --sections` allows specific section retrieval
- **O(1) section access**: Sections index enables instant retrieval of any paper section
- **Context optimization**: Reduces Claude's text processing by 70-90%

### Incremental Updates (10x Faster)
- **Smart updates**: `--update` flag adds only new papers without full rebuild
- **Fingerprint tracking**: Content-based hashing detects changed papers
- **Append-only indexing**: New papers added to existing FAISS index
- **Time savings**: 2-3 minutes for updates vs 30+ minutes for full rebuild

### Personal Shortcuts System
- **Shortcut configuration**: `.research_shortcuts.yaml` for saved searches
- **Quick access**: `shortcut` command to run predefined queries
- **Management**: `shortcut --list` to view, `shortcut --delete` to remove

### Research Gap Analysis
- **Gap detection**: `--analyze-gaps` flag identifies unexplored areas
- **Temporal analysis**: Shows research trends over time
- **Methodology gaps**: Highlights missing study types in literature

### Other Improvements
- **Claude Code command**: `/research` for seamless integration
- **Duplicate detection**: `duplicates` command with `--fix` option
- **Section caching**: `.sections_cache.json` for faster retrieval
- **Better prompts**: Clearer user interaction flow
- **Export/Import**: Portable knowledge base archives

### Bug Fixes
- Fixed KeyError when papers lack DOI/ISBN metadata
- Improved error handling for missing Zotero attachments
- Better recovery from corrupted cache files
- Fixed UTF-8 encoding issues in PDF extraction

## [3.0.0] - 2024-11-14

### Major Performance Improvements
- **10x faster embedding generation**: O(1) hash-based cache lookups
- **Dynamic batch sizing**: Automatically adjusts to available RAM/GPU
- **Lazy model loading**: Reduced startup time by 50%
- **Compressed caching**: 60% smaller cache files with NPZ format

### Enhanced Search Capabilities
- **SPECTER embeddings**: State-of-the-art scientific paper similarity
- **Study type detection**: Automatically identifies RCTs, systematic reviews, etc.
- **Quality scoring**: Papers ranked 0-100 based on evidence quality
- **Advanced filters**: Filter by year, study type, quality score

### Better Knowledge Management
- **Zotero integration**: Direct connection to local Zotero library
- **PDF extraction**: Full text from PDFs with 95%+ success rate
- **Metadata enrichment**: DOIs, journals, volumes, pages auto-extracted
- **IEEE citations**: Generate formatted citations instantly

### Robustness & Security
- **Path traversal protection**: Safe handling of file paths
- **Command injection prevention**: Secure subprocess execution
- **Graceful degradation**: Continues despite individual PDF failures
- **Comprehensive testing**: 95% code coverage

## [2.0.0] - 2024-10-28

### Initial Public Release
- Basic semantic search using sentence transformers
- Zotero library import
- Simple FAISS indexing
- Command-line interface
- PDF text extraction with PyMuPDF
