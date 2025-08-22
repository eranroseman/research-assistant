# Network Gap Analysis Design v1.2

**Created**: 2024-08-21  
**Updated**: 2024-08-21  
**Status**: Design Phase - Citation Networks + Simplified Author Networks  
**Dependencies**: Enhanced Quality Scoring (v3.1)  
**Breaking Changes**: Requires fresh KB rebuild, no backwards compatibility

## Overview

The Network Gap Analysis module identifies missing papers in a knowledge base by analyzing citation networks and simplified author networks. It produces actionable DOI lists for Zotero import, organized by gap type and research theme.

**Phase 1 Implementation**: Citation networks (highest ROI) + simplified author networks (recent work from KB authors)
**Phase 2+**: Additional algorithms based on user feedback and validation

## Core Concept

After users build their KB with `python src/build_kb.py`, they are prompted to run gap analysis as part of the setup workflow. Users can then run `python src/analyze_gaps.py` manually with custom filters to discover literature gaps using existing KB infrastructure (Multi-QA MPNet embeddings, FAISS index, citation data).

## Two-Part Workflow

### Part 1: One-Time Setup (build_kb → analyze_gaps)
**Run once and forget** - establishes the foundational gap analysis

### Part 2: Research-Driven Discovery (/research → /doi)
**On-demand research workflow** - discovers specific gaps during research activities

## Module Architecture

### Primary Module: `src/analyze_gaps.py`
- Command-line interface for gap analysis
- Orchestrates gap detection algorithms
- Generates comprehensive markdown reports
- Outputs organized DOI lists for Zotero import

### Supporting Module: `src/gap_detection.py` 
- Core gap detection algorithms
- Citation network analysis (Phase 1)
- Simplified author network analysis (Phase 1)
- Future algorithms: Co-citation clustering, temporal gaps, semantic similarity (Phase 2+)

### Configuration: `src/config.py` (additions)
- Gap analysis thresholds and weights
- Output formatting preferences
- Performance optimization settings

## Gap Detection Algorithms (Phase 1)

### 1. Citation Network Gaps ⭐⭐⭐ **Primary Algorithm**
**Method**: Analyze papers cited by KB papers but not in KB
**Data Source**: Semantic Scholar API citation data (reuses enhanced scoring infrastructure)
**Priority Scoring**: Citation frequency × paper quality score
**Output**: High-impact papers frequently referenced by existing collection
**Development Time**: 1-2 weeks
**User Value**: VERY HIGH - clear relevance signal ("papers my collection cites")

### 2. Simplified Author Network Gaps ⭐⭐ **Secondary Algorithm**
**Method**: Find recent papers from authors already in KB (no disambiguation needed)
**Data Source**: Semantic Scholar author IDs from enhanced scoring + recent papers API
**Priority Scoring**: Recency × topic similarity to KB × citation impact
**Output**: Recent work from researchers user already follows
**Development Time**: 1 week additional
**User Value**: HIGH - clear value proposition ("recent work from your authors")

**Key Simplifications:**
- No author disambiguation (uses existing Semantic Scholar author IDs from enhanced scoring)
- No "productivity" assessment (all KB authors considered relevant)
- Simple recency filter (configurable --year-from flag, default 2022)
- Topic similarity filtering using existing KB embeddings

## Future Algorithms (Phase 2+ Based on User Feedback)

### 3. Co-citation Clustering ⭐⭐
**Status**: Future implementation based on Phase 1 validation

### 4. Temporal Gaps ⭐
**Status**: Future implementation based on user demand

### 5. Semantic Similarity Gaps ⭐
**Status**: Optional - highest complexity, lowest ROI

## Command-Line Interface

### Basic Usage
```bash
python src/analyze_gaps.py
```

### Optional Filtering
```bash
python src/analyze_gaps.py [OPTIONS]

Options:
  --min-citations N     Only suggest papers with ≥N citations (default: 0)
  --year-from YYYY      Author networks: only papers from YYYY onwards (default: 2022)
  --limit N            Return top N gaps by priority (default: unlimited)
  --help               Show help message
```

### Examples
```bash
# Comprehensive analysis (citation + recent author networks)
python src/analyze_gaps.py

# High-impact gaps with conservative recency 
python src/analyze_gaps.py --min-citations 50 --year-from 2022

# Top 50 gaps by priority
python src/analyze_gaps.py --limit 50

# Recent work from your authors only
python src/analyze_gaps.py --year-from 2024 --limit 30

# Broader historical view of author networks
python src/analyze_gaps.py --year-from 2018
```

## Output Structure

### File Location
`exports/gap_analysis_YYYY_MM_DD.md`

### Report Format (Phase 1)
```markdown
# Knowledge Base Gap Analysis
Generated: 2024-08-21
KB Version: 4.0
Total Papers in KB: 2,157
Analysis Duration: 1.8 minutes
Recency Threshold: 2022 (for author networks)

## Executive Summary
- Total gaps identified: 62
- Citation network gaps: 47 papers (highest confidence)
- Author network gaps: 15 papers (recent work from your authors)

## Citation Network Gaps (47 papers)

### Block 1: Diabetes Management Protocols
**Why relevant**: Heavily cited by your diabetes research papers but missing from KB
**DOI Import List**:
10.1038/s41586-2023-12345
10.1056/NEJMoa2023-456

**Paper 1**: DOI: 10.1038/s41586-2023-12345 (487 citations)
- **Title**: "Advanced diabetes management protocols in primary care"
- **Authors**: Smith J, Johnson M, et al.
- **Year**: 2023
- **Relevance**: Cited by 8 papers in your KB (0045, 0156, 0234, 0445, 0567, 0678, 0789, 0890)
- **Key connection**: Foundational work for continuous glucose monitoring approaches
- **Gap priority**: HIGH (multiple citations from high-quality KB papers)
- **Confidence**: HIGH (strong citation evidence)

[Additional papers in block...]

## Author Network Gaps (15 papers)

### Recent Work from Your Authors (2022+)
**Why relevant**: Latest publications from authors already in your collection

**Paper 1**: DOI: 10.1016/j.diabres.2024-98765 (12 citations)
- **Title**: "Digital therapeutics for pediatric diabetes management"
- **Authors**: Dr. Sarah Johnson (already have 3 papers from her in your KB)
- **Year**: 2024
- **Relevance**: Extension of diabetes intervention research you already found valuable
- **Topic similarity**: 0.84 match with existing KB papers
- **Gap priority**: MEDIUM (recent work from known relevant author)
- **Confidence**: MEDIUM (author relevance + topic similarity)

[Additional recent author papers...]

## Complete DOI Lists for Bulk Import

### All Citation Network Gaps (47 DOIs)
10.1038/s41586-2023-12345
10.1056/NEJMoa2023-456
[...]

### All Author Network Gaps (15 DOIs)  
10.1016/j.diabres.2024-98765
10.1093/jamia/ocad.2024.123
[...]

### All Suggested Papers (62 DOIs)
[Combined list for bulk Zotero import]
```

## Technical Implementation

### Data Flow
1. **KB Analysis**: Load existing embeddings, metadata, and FAISS index
2. **API Integration**: Query Semantic Scholar for citation/author data
3. **Gap Detection**: Run 5 gap detection algorithms in parallel
4. **Priority Scoring**: Rank gaps by relevance and impact
5. **Thematic Clustering**: Group related papers into blocks
6. **Report Generation**: Create structured markdown with DOI lists

### Performance Considerations
- **Parallel Processing**: Run gap detection algorithms concurrently
- **API Rate Limiting**: Token bucket pattern (3 RPS max, 10 burst allowance)
- **Caching**: Cache API responses with 7-day expiry for development iteration
- **Memory Management**: Stream large result sets to prevent OOM with large KBs
- **Fail Fast**: Hard failures instead of graceful degradation for clarity

### Dependencies
- **KB v4.0+ Only**: Requires FAISS index, Multi-QA MPNet embeddings, enhanced metadata
- **Semantic Scholar API**: Citation data, author information, paper details
- **Enhanced Quality Scoring**: Required - citation impact and venue prestige data

## Configuration Additions

### New Config Constants (`src/config.py`)
```python
# ============================================================================
# GAP ANALYSIS CONFIGURATION  
# ============================================================================

# Gap detection thresholds
GAP_ANALYSIS_MIN_CITATIONS_DEFAULT = 0
GAP_ANALYSIS_MIN_KB_CONNECTIONS = 2  # Min KB papers that must cite a gap
GAP_ANALYSIS_MAX_GAPS_PER_TYPE = 1000  # Prevent overwhelming results

# Author network recency settings
GAP_ANALYSIS_AUTHOR_RECENCY_DEFAULT = 2022  # Conservative default (3 years)
GAP_ANALYSIS_AUTHOR_RECENCY_MIN = 2015      # Minimum allowed value (10 years)
GAP_ANALYSIS_AUTHOR_RECENCY_MAX = 2024      # Maximum allowed value (current year)

# API rate limiting (token bucket pattern)
API_RATE_LIMIT_RPS = 3  # Conservative rate limit
API_RATE_LIMIT_BURST = 10  # Burst allowance for initial requests
API_RATE_LIMIT_RETRY_DELAY = 1.0  # Base delay for exponential backoff

# Citation network analysis
CITATION_NETWORK_MAX_DEPTH = 2  # How deep to traverse citation networks
CITATION_RELEVANCE_THRESHOLD = 0.1  # Min relevance score for inclusion

# Simplified author network analysis  
AUTHOR_NETWORK_USE_EXISTING_IDS = True     # Use Semantic Scholar IDs from enhanced scoring
AUTHOR_NETWORK_MAX_RECENT_PAPERS = 20      # Limit papers per author to prevent overwhelming
AUTHOR_NETWORK_TOPIC_SIMILARITY_THRESHOLD = 0.6  # Minimum topic similarity to KB

# Future algorithms (Phase 2+) - disabled in Phase 1
# CO_CITATION_MIN_FREQUENCY = 3
# SEMANTIC_SIMILARITY_HIGH = 0.8  
# TEMPORAL_GAP_MIN_YEAR_COVERAGE = 0.5

# Report generation
GAP_REPORT_MAX_PAPERS_PER_BLOCK = 20  # Max papers per thematic block
GAP_REPORT_BLOCK_MIN_SIZE = 3  # Min papers needed to form a block
GAP_REPORT_EXPLANATION_MAX_LENGTH = 200  # Max chars for relevance explanations

# Confidence indicators for user guidance
CONFIDENCE_HIGH_THRESHOLD = 0.8    # HIGH priority gaps
CONFIDENCE_MEDIUM_THRESHOLD = 0.6  # MEDIUM priority gaps
CONFIDENCE_LOW_THRESHOLD = 0.4     # LOW priority gaps

# Performance settings
GAP_ANALYSIS_PARALLEL_WORKERS = 4  # Parallel gap detection workers
GAP_ANALYSIS_API_BATCH_SIZE = 10  # Papers per API batch request
GAP_ANALYSIS_CACHE_EXPIRY_DAYS = 7  # Cache API responses for 7 days
```

## Error Handling & Requirements

### Hard Requirements
- **KB v4.0+ Required**: Exit with clear error if KB version incompatible
- **Enhanced Quality Scoring Required**: Exit if enhanced scoring not available
- **Minimum KB Size**: Require ≥20 papers with enhanced quality scores
- **API Access Required**: Exit if Semantic Scholar API unavailable

### Fail Fast Error Handling
- **API Failures**: Exit immediately with clear error message
- **Corrupted KB**: Exit if KB structure invalid or missing required data
- **Network Issues**: Limited retries (3x), then fail with actionable error
- **Insufficient Data**: Exit if KB lacks required citation/author data

### Validation (No Fallbacks)
- **Paper ID Validation**: Exit if any KB papers have invalid structure
- **Duplicate Detection**: Simple check against KB paper IDs
- **Quality Filtering**: Require enhanced quality scores for all papers

## Integration Points

### With Enhanced Quality Scoring
- **Required Integration**: Use existing Semantic Scholar API integration (no fallbacks)
- **Quality Metrics**: Apply enhanced quality scoring to gap candidates (required)
- **Shared Infrastructure**: Use same API client and caching

### With Existing CLI
- **Consistent Interface**: Follow same argument patterns as `src/cli.py`
- **Error Handling**: Use same error message formatting (fail fast)
- **Output Structure**: Consistent with other exports in `exports/` directory

### With Build Pipeline
- **Post-Build Integration**: `build_kb.py` prompts user to run gap analysis after successful build
- **Metadata Integration**: Use v4.0+ paper metadata and embeddings only
- **No Version Compatibility**: KB v4.0+ required, no legacy support
- **User Workflow**: One-time setup → ongoing research-driven discovery

## Success Metrics

### Analysis Quality
- **Gap Relevance**: % of suggested papers user finds relevant to their research
- **Discovery Value**: Number of high-impact papers identified that user was unaware of
- **Actionability**: % of suggested papers user actually imports into Zotero

### Performance
- **Analysis Speed**: Complete analysis in <5 minutes for 2000-paper KB
- **API Efficiency**: <500 API requests for typical gap analysis
- **Memory Usage**: Keep memory footprint <2GB during analysis

### User Experience
- **Report Clarity**: Users can quickly understand why papers are suggested
- **Import Workflow**: Seamless DOI import into Zotero
- **Filtering Effectiveness**: Optional flags provide useful result refinement

## Future Enhancements

### Phase 2 Features
- **Interactive Mode**: Allow users to accept/reject gaps during analysis
- **Comparative Analysis**: Compare KB gaps against other researchers' libraries
- **Trend Detection**: Identify emerging research trends missing from KB

### Advanced Algorithms
- **Graph Neural Networks**: Use citation graph structure for more sophisticated gap detection
- **Topic Modeling**: Dynamic topic modeling for temporal gap analysis
- **Collaborative Filtering**: "Researchers like you also have these papers"

### Integration Opportunities
- **Zotero Plugin**: Direct integration with Zotero for one-click imports
- **Citation Managers**: Support for Mendeley, EndNote DOI import formats
- **Research Dashboards**: Web interface for gap analysis visualization

## Implementation Timeline

### Phase 1A: Citation Networks (Week 1) - Highest ROI
- [ ] Create `src/analyze_gaps.py` CLI interface with basic filtering
- [ ] Reuse enhanced scoring's Semantic Scholar client and rate limiting
- [ ] Implement citation network gap detection with confidence scoring
- [ ] Basic report generation matching gap analysis format
- [ ] DOI lists for Zotero import

### Phase 1B: Simplified Author Networks (Week 2) - Additional Value  
- [ ] Extract author IDs from enhanced scoring data (no disambiguation)
- [ ] Implement recency filtering with configurable --year-from flag
- [ ] Add topic similarity filtering using existing KB embeddings
- [ ] Integrate author gaps into unified report structure

### Phase 2: Validation and Refinement (Week 3-4) - Based on User Feedback
- [ ] Comprehensive testing with different KB sizes (100, 500, 1000, 2000 papers)
- [ ] Performance optimization and error handling
- [ ] User feedback analysis and algorithm refinement
- [ ] Documentation and usage examples

### Phase 3+: Additional Algorithms (Future) - Based on Validation
- [ ] Co-citation clustering (if users request broader discovery)
- [ ] Temporal gap analysis (if users need historical perspective)
- [ ] Semantic similarity gaps (lowest priority, highest complexity)

## Dependencies & Prerequisites

### Required
- Enhanced Quality Scoring v3.0+ (no fallback to basic scoring)
- KB v4.0+ with Multi-QA MPNet embeddings and enhanced metadata
- Python packages: `aiohttp`, `networkx`, `scikit-learn`

### Optional  
- `matplotlib`, `seaborn` for future visualization features
- `plotly` for interactive gap analysis reports

## Testing Strategy

### Unit Tests
- Gap detection algorithm accuracy with mock data
- API integration with mock Semantic Scholar responses
- Token bucket rate limiting behavior
- Confidence scoring calculation
- Report generation formatting

### Integration Tests
- End-to-end gap analysis workflow with real KB
- Performance benchmarks with 100, 500, 1000, 2000 paper KBs
- API rate limiting compliance and error recovery
- Cache persistence and invalidation
- Memory usage monitoring for large result sets

### User Testing
- Report clarity and confidence indicator usefulness
- DOI import workflow validation with Zotero
- Filter effectiveness (--min-citations, --year-from, --limit)
- Time-to-value measurement (useful gaps found per minute)

## Build Pipeline Integration

### Post-Build Educational Prompt in `src/build_kb.py`

After successful KB build, `build_kb.py` will prompt users with educational context:

```python
def prompt_gap_analysis_after_build(total_papers: int, build_time: float) -> None:
    """Educational prompt for gap analysis after successful KB build."""
    print(f"\n✅ Knowledge base built successfully!")
    print(f"   {total_papers:,} papers indexed in {build_time:.1f} minutes")
    
    if has_enhanced_scoring() and total_papers >= 20:
        print(f"\n🔍 Run gap analysis to discover missing papers in your collection?")
        print(f"\nGap analysis identifies 5 types of literature gaps:")
        print(f"• Papers cited by your KB but missing from your collection")
        print(f"• Recent work from authors already in your KB")
        print(f"• Papers frequently co-cited with your collection")
        print(f"• Recent developments in your research areas")
        print(f"• Semantically similar papers you don't have")
        
        print(f"\nIf you choose 'Y', will run: python src/analyze_gaps.py (comprehensive analysis, no filters)")
        print(f"\nFor filtered analysis, run manually later with flags:")
        print(f"  --min-citations N     Only papers with N+ citations")
        print(f"  --year-from YYYY      Only papers from YYYY onwards")
        print(f"  --limit N            Top N results by priority")
        print(f"\nExample: python src/analyze_gaps.py --min-citations 50 --year-from 2020 --limit 100")
        
        response = input("\nRun comprehensive gap analysis now? (Y/n): ").strip().lower()
        if response != 'n':
            print("\n🔍 Running comprehensive gap analysis...")
            import subprocess
            subprocess.run(["python", "src/analyze_gaps.py"], check=False)
    else:
        print("\n   Gap analysis requires enhanced quality scoring and ≥20 papers")
        print("   Run with enhanced scoring to enable gap detection.")
```

### Integration Benefits
- **Educational Without Overwhelming**: Clear explanation of 5 gap types and available flags
- **User Control**: Simple Y/n choice with explicit explanation of what 'Y' does
- **Future Reference**: Users learn flags for manual customized runs
- **Separation of Concerns**: KB building vs. gap detection remain separate operations

## Technical Implementation Notes

### Critical Implementation Decisions (Simplified)

#### Fail Fast Validation
```python
def validate_kb_requirements():
    """Exit immediately if requirements not met"""
    if not kb_has_enhanced_scoring():
        sys.exit("ERROR: Enhanced Quality Scoring required. Run: rm -rf kb_data/ && python src/build_kb.py")
    if kb_version() < "4.0":
        sys.exit("ERROR: KB v4.0+ required. Delete kb_data/ and rebuild.")
    if len(load_kb_papers()) < 20:
        sys.exit("ERROR: Minimum 20 papers required for gap analysis.")
```

#### Rate Limiting Strategy
```python
class TokenBucket:
    def __init__(self, max_rps=3, burst_allowance=10):
        self.max_rps = max_rps
        self.burst_allowance = burst_allowance
        self.tokens = burst_allowance
        self.last_update = time.time()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary"""
        # Implementation ensures sustainable API usage
```

#### Confidence Scoring Framework (Enhanced Scores Only)
```python
def calculate_gap_confidence(gap_paper, kb_connections):
    """Multi-factor confidence using enhanced quality scores"""
    # Assumes enhanced quality scoring available - no fallbacks
    enhanced_score = gap_paper.enhanced_quality_score  # Required field
    connection_score = len(kb_connections) / 10
    return (enhanced_score / 100 + connection_score) / 2
```

### Implementation Priority Rationale

1. **Rate Limiting First**: Without this, API blocks will halt development
2. **Caching Second**: Essential for development iteration and user re-runs
3. **Citation Networks Third**: Highest ROI gap detection method
4. **Confidence Indicators Fourth**: Critical UX improvement for actionability
5. **Additional Algorithms**: Based on user feedback and adoption

### Risk Mitigation (Simplified)

- **API Dependency**: Fail fast with clear rebuild instructions when API unavailable
- **Large KB Performance**: Streaming and batch processing from day 1
- **User Overwhelm**: Conservative result limits with clear confidence indicators
- **Development Velocity**: Robust caching to enable rapid iteration
- **Version Conflicts**: Hard KB version check prevents compatibility issues

---

*This design document provides a battle-tested foundation for implementing network gap analysis, incorporating lessons learned from technical review and focusing on reliability over feature completeness for initial release.*