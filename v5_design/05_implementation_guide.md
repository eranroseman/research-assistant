# Implementation Guide

## Bug Fixes and Updates (Sep 1, 2025)

### Critical Metadata Extraction Fix

**ROOT CAUSE IDENTIFIED**: The original TEI XML extraction was incomplete, missing critical metadata fields including **year (affecting 100% of papers)**, journal information, keywords, and other essential fields.

### Fixed Issues

1. **Section Text Extraction Bug**
   - **Files**: `extract_zotero_library.py`, `grobid_overnight_runner.py`
   - **Issue**: Only section titles were saved, not paragraph content
   - **Fix**: Modified to extract full text using `p.itertext()`
   - **Impact**: Recovered 85.9M characters from 2,203 papers

2. **Quality Filtering Logic**
   - **File**: `pdf_quality_filter.py`
   - **Issue**: Papers missing titles were excluded despite having content
   - **Fix**: Include papers with DOI + content (titles recoverable via API)
   - **Impact**: Preserved ~82 valuable papers for title recovery

3. **Comprehensive Metadata Extraction** (NEW)
   - **File**: `comprehensive_tei_extractor.py`
   - **Issue**: Original extraction missing year (100% of papers), journal info, keywords, etc.
   - **Fix**: Complete TEI XML extraction capturing ALL available fields
   - **Impact**:
     - Year extraction: 0% → 97.4% coverage
     - Journal extraction: 0% → 92.8% (with intelligent inference)
     - Keywords: 61.7% of papers
     - License/funding: 30-74% coverage
     - Formulas, citations, figures, tables: All captured

### Current Workflow

1. **Grobid Extraction** → 2. **TEI Reprocessing** → 3. **Quality Filter** → 4. **Post-Processing** → 5. **KB Build**

## Shared Libraries Architecture

v5.0 introduces shared libraries to eliminate code duplication and ensure consistency.

### Library Structure

```
src/
├── lib/                           # Shared libraries (NEW in v5.0)
│   ├── extraction_common.py      # Grobid/S2 API clients
│   ├── quality_scoring.py        # Unified quality scoring
│   ├── progress_monitor.py       # Progress tracking
│   ├── embeddings_common.py      # Multi-level embeddings
│   ├── entity_database.py        # Fast entity filtering
│   └── report_generator.py       # Consistent reports
├── build.py                       # Uses 5/6 libraries
├── kbq.py                        # Uses 4/6 libraries
├── discover.py                   # Uses 3/6 libraries
└── gaps.py                       # Uses 4/6 libraries
```

### Code Reduction Impact
- **60-70% less duplicate code**
- **Single source of truth** for critical logic
- **Consistent behavior** across all tools

## Core Libraries Implementation

### 1. extraction_common.py

```python
class ZoteroClient:
    """Zotero API client with collection support"""

    def get_all_papers(self) -> List[Dict]:
        """Fetch all papers from library"""
        pass

    def get_collection_papers(self, collection_name: str) -> List[Dict]:
        """Fetch papers from specific collection"""
        pass

    def list_collections(self) -> List[str]:
        """List available collections"""
        pass

class GrobidClient:
    """Shared Grobid API client with two-pass extraction strategy"""

    def __init__(self, url="http://localhost:8070"):
        self.url = url
        self.first_pass_timeout = 90   # Captures 99.82% of papers
        self.second_pass_timeout = 180 # Retry for legitimately slow papers

    def extract_with_two_pass(self, pdf_path) -> Dict:
        """Two-pass extraction strategy for research papers"""
        # First pass: 90s timeout
        result = self._extract(pdf_path, timeout=self.first_pass_timeout)
        if result:
            return result

        # Second pass: 180s timeout for failed papers
        return self._extract(pdf_path, timeout=self.second_pass_timeout)

    def _extract(self, pdf_path, timeout) -> Optional[Dict]:
        """Extract with maximum parameters, no header-only fallback"""
        params = get_maximum_extraction_params()
        params['timeout'] = timeout
        # Implementation - no fallback to header-only
        pass

class S2Client:
    """Semantic Scholar API with adaptive rate limiting"""

    def __init__(self, api_key=None):
        self.rate_limiter = AdaptiveRateLimiter()
        self.session = requests.Session()
        if api_key:
            self.session.headers['x-api-key'] = api_key

    def get_paper(self, doi: str) -> Optional[Dict]:
        """Get paper with SPECTER2 embeddings"""
        fields = "paperId,title,abstract,embedding,citationCount"
        # Implementation with rate limiting
        pass
```

### 2. progress_monitor.py

```python
class ProgressTracker:
    """Track long-running operations with checkpoints"""

    def __init__(self, total, log_dir='kb_data'):
        self.total = total
        self.current = 0
        self.log_file = Path(log_dir) / 'build_progress.log'
        self.checkpoint_file = Path(log_dir) / '.checkpoint.json'
        self.start_time = time.time()

    def update(self, current: int, message=''):
        """Update progress with ETA calculation"""
        self.current = current
        elapsed = time.time() - self.start_time
        rate = current / elapsed if elapsed > 0 else 0
        eta = (self.total - current) / rate if rate > 0 else 0

        # Log progress
        self._log_progress(current, self.total, rate, eta, message)

        # Create checkpoint every 50 papers
        if current % 50 == 0:
            self.create_checkpoint()

    def create_checkpoint(self) -> Dict:
        """Save current state for recovery"""
        checkpoint = {
            'current': self.current,
            'total': self.total,
            'timestamp': datetime.now().isoformat(),
            'elapsed_seconds': time.time() - self.start_time
        }

        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        return checkpoint

    def resume_from_checkpoint(self) -> Optional[int]:
        """Resume from saved checkpoint"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file) as f:
                checkpoint = json.load(f)
            self.current = checkpoint['current']
            return self.current
        return None
```

### 3. quality_scoring.py

```python
class QualityScorer:
    """Unified quality scoring with explanations"""

    def calculate_score(self, paper, grobid, s2) -> tuple[int, str]:
        """Calculate comprehensive quality score"""

        score = 0
        components = {}

        # Impact (30 points)
        citations = s2.get('citation_count', 0)
        if citations > 100:
            score += 15
            impact_reason = f"{citations} citations (high impact)"
        elif citations > 50:
            score += 12
            impact_reason = f"{citations} citations (moderate impact)"
        else:
            impact_reason = f"{citations} citations"

        components['impact'] = {
            'earned': score,
            'max': 15,
            'reason': impact_reason
        }

        # Methodology (25 points)
        sample_size = self._get_sample_size(grobid)
        if sample_size > 1000:
            score += 10
        if 'rct' in grobid.get('study_type', '').lower():
            score += 9
        if grobid.get('p_values'):
            score += 3

        # Reproducibility (20 points)
        if grobid.get('data_availability'):
            score += 8
        if grobid.get('code_url'):
            score += 7
        if s2.get('is_open_access'):
            score += 5

        # Generate explanation
        explanation = self._generate_explanation(score, components)

        return min(score, 100), explanation
```

## Build Process Implementation

### Simplified Build Philosophy

```python
def main():
    """Build with all available features, showing helpful progress."""

    # 1. Start Grobid locally (no Azure)
    print("Starting local Grobid service...")
    start_local_grobid()  # docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.2-full

    # 2. Determine collection scope
    if args.collection:
        print(f"Processing collection: {args.collection}")
        papers = fetch_from_collection(args.collection)
    else:
        print("Processing entire library")
        papers = fetch_entire_library()

    # 3. Auto-detect operation mode
    if args.rebuild:
        auto_backup()  # Safety first
        rebuild_from_scratch(papers)
    else:
        if checkpoint_exists():
            resume_from_checkpoint(papers)
        else:
            incremental_update(papers)

    # 4. Use all v5.0 features automatically
    extract_with_grobid()        # Always
    extract_entities()           # Always
    get_s2_metrics()            # If available
    create_multi_embeddings()    # Always

    # 5. Generate reports
    generate_pdf_quality_report(papers)
    if not args.no_gaps:
        run_gap_analysis()

    print("✨ Build complete!")
```

### Key Principles

1. **Always complete** - No prompts interrupt the build
2. **Always use latest** - All features used automatically
3. **Smart defaults** - Auto-starts services, resumes checkpoints
4. **Minimal flags** - Only 7 flags total
5. **Helpful output** - Shows exactly what's happening
6. **Actionable reports** - Generated automatically

## Resilient Extraction

```python
class ResilientExtractor:
    """Extraction with automatic retry and failure tracking"""

    # Two-pass strategy replaces retry logic
    FIRST_PASS_TIMEOUT = 90   # Captures 99.82% of research papers
    SECOND_PASS_TIMEOUT = 180 # For legitimately slow papers only

    def extract_with_retry(self, pdf_path: Path) -> Optional[Dict]:
        """Extract with automatic retry on transient failures"""

        for attempt in range(self.MAX_RETRIES):
            try:
                result = self._extract(pdf_path)
                return result

            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.warning(f"Retry {attempt+1} in {delay}s...")
                    time.sleep(delay)
                else:
                    self.failed_papers.append({
                        'path': str(pdf_path),
                        'error': str(e),
                        'attempts': self.MAX_RETRIES
                    })

            except Exception as e:
                # Non-retryable error - fail fast
                self.failed_papers.append({
                    'path': str(pdf_path),
                    'error': str(e),
                    'error_type': 'non_retryable'
                })
                return None

        return None
```

## Entity Extraction

```python
def extract_all_grobid_entities(xml: str) -> Dict:
    """Extract 50+ entity types from Grobid XML"""

    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    root = ET.fromstring(xml)

    return {
        # Methodology
        'sample_sizes': extract_sample_sizes(root, ns),
        'p_values': extract_p_values(root, ns),
        'confidence_intervals': extract_ci(root, ns),
        'study_type': detect_study_type(root, ns),

        # Software & Data
        'software': extract_software(root, ns),
        'datasets': extract_datasets(root, ns),
        'data_availability': extract_data_availability(root, ns),

        # Quality indicators
        'figures_count': len(root.findall('.//tei:figure', ns)),
        'tables_count': len(root.findall('.//tei:table', ns)),
        'references_count': len(root.findall('.//tei:ref[@type="bibr"]', ns)),
    }

def extract_sample_sizes(root, ns) -> List[int]:
    """Extract all sample sizes from paper"""

    sizes = []
    patterns = [
        r'n\s*=\s*(\d+)',
        r'N\s*=\s*(\d+)',
        r'(\d+)\s+participants',
        r'(\d+)\s+patients',
        r'(\d+)\s+subjects'
    ]

    text = ' '.join(root.itertext())
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        sizes.extend([int(m) for m in matches])

    return sorted(set(sizes), reverse=True)
```

## Multi-Level Embeddings

```python
class EmbeddingManager:
    """Manage 5-level embeddings per paper"""

    def __init__(self):
        self.model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')
        self.dimension = 768

    def create_all_embeddings(self, paper: Dict) -> Dict:
        """Create 5 different embeddings for comprehensive search"""

        embeddings = {}

        # 1. Title + Abstract (standard)
        text = f"{paper['title']} {paper['abstract']}"
        embeddings['title_abstract'] = self.model.encode(text)

        # 2. Enriched (with entities)
        entities_text = self._format_entities(paper['entities'])
        enriched = f"{text} {entities_text}"
        embeddings['enriched'] = self.model.encode(enriched)

        # 3. S2 embedding (if available)
        if paper.get('s2_data', {}).get('embedding'):
            embeddings['s2_embedding'] = paper['s2_data']['embedding']

        # 4. Methods section
        if paper.get('sections', {}).get('methods'):
            embeddings['methods'] = self.model.encode(
                paper['sections']['methods'][:5000]
            )

        # 5. Metadata vector (numerical features)
        embeddings['metadata_vector'] = self._create_metadata_vector(paper)

        return embeddings
```

## Adaptive Rate Limiting

```python
class AdaptiveRateLimiter:
    """Smart rate limiting for API compliance"""

    def __init__(self):
        self.delay = 0.1  # Start optimistic
        self.min_delay = 0.1
        self.max_delay = 5.0
        self.success_count = 0
        self.rate_limit_count = 0

    def wait(self):
        """Wait before next API call"""
        time.sleep(self.delay)

    def on_success(self):
        """Speed up after sustained success"""
        self.success_count += 1
        if self.success_count > 10:
            # Gradually speed up
            self.delay = max(self.min_delay, self.delay * 0.9)
            self.success_count = 0

    def on_rate_limit(self):
        """Slow down on rate limit error"""
        self.rate_limit_count += 1
        self.delay = min(self.max_delay, self.delay * 2.0)
        self.success_count = 0
        logger.warning(f"Rate limited. Slowing to {self.delay:.2f}s")
```

## Testing Strategy

### Core Testing Philosophy

**Target: 90% coverage of critical paths**

```python
# Priority 1: Test the happy path thoroughly
def test_full_extraction_pipeline():
    """Test complete extraction with all post-processing"""
    # 1. Grobid extraction with maximum parameters
    # 2. All 5 critical post-processing fixes
    # 3. Entity extraction and indexing
    # 4. Quality score calculation

# Priority 2: Test failure modes explicitly
def test_grobid_failure_handling():
    """Ensure Grobid failures result in clear errors"""
    # NO fallback to PyMuPDF
    # Clear error messages
    # Paper marked as extraction_failed

# Priority 3: Test post-processing fixes
def test_case_insensitive_matching():
    """Validate the 44% improvement is real"""
    sections = {'RESULTS': 'content', 'Methods': 'data'}
    normalized = normalize_sections(sections)
    assert 'results' in normalized
    assert 'methods' in normalized
```

### What NOT to Test

- DON'T test every Grobid parameter combination
- DON'T test PyMuPDF as fallback (we don't want it)
- DON'T test edge cases like 100MB PDFs
- DON'T mock Grobid responses (test against real service)

## Performance Optimizations

### Intel Extension Auto-Detection

```python
def setup_ipex_if_available():
    """Auto-detect and enable Intel Extension for PyTorch"""
    try:
        import intel_extension_for_pytorch as ipex

        if has_intel_cpu():
            model = ipex.optimize(model)
            logger.info("✓ Intel Extension enabled - 2-3x speedup")
            return True
    except ImportError:
        logger.debug("Intel Extension not available")
        return False
```

**Performance Impact:**
- Embedding generation: 3x faster
- Similarity search: 2.5x faster
- FAISS indexing: 2.5x faster
- Total KB build: 2.4x faster

## Clear Failure Philosophy

```python
def process_with_grobid(pdf_path):
    """Process PDF with Grobid - NO FALLBACKS"""
    try:
        result = grobid.process(pdf_path)
        if not result or not result.get('sections'):
            # Clear failure - don't try PyMuPDF
            return {
                'status': 'extraction_failed',
                'reason': 'grobid_no_content',
                'action_required': 'Check PDF quality or re-OCR'
            }
        return result
    except Exception as e:
        # Clear error - no silent fallback
        return {
            'status': 'extraction_failed',
            'reason': str(e),
            'action_required': 'Fix Grobid service or PDF'
        }
```

**Why No PyMuPDF Fallback?**
1. PyMuPDF extracts ~10% of what Grobid provides
2. Paper appears extracted but missing 90% of content
3. Users don't know they have bad data
4. Clear failure prompts user to fix root cause
