# `/discover` Slash Command Design v3.1

**Created**: 2024-08-21  
**Updated**: 2024-08-21  
**Status**: Design Phase - Semantic Scholar Foundation  
**Purpose**: Intelligent interface for comprehensive discovery leveraging Semantic Scholar-based discover.py tool  
**Dependencies**: Discovery Tool v3.1 (Semantic Scholar), Enhanced Quality Scoring v3.1

## Overview

The `/discover` slash command provides an intelligent interface for comprehensive paper discovery using Semantic Scholar. It reads research reports to identify gaps, extracts keywords with cross-domain expansion, calls the Semantic Scholar-based `src/discover.py` tool for comprehensive external paper search, and provides KB coverage assessment with traffic light status indicators.

## Core Workflow

```mermaid
graph TD
    A[/discover command] --> B{Input Type?}
    B -->|No args| C[Read latest research report]
    B -->|report_name.md| D[Read specific report] 
    B -->|"topic string"| E[Direct topic search]
    
    C --> F[Parse gaps from report]
    D --> F
    E --> G[Use topic as keywords]
    
    F --> H[Extract structured parameters]
    G --> H
    
    H --> I[Generate Semantic Scholar search parameters]
    I --> J[Call src/discover.py (Semantic Scholar comprehensive)]
    J --> K[Process results using enhanced scoring patterns]
    K --> L[Assess KB coverage (Red/Yellow/Green)]
    L --> M[Generate aligned discovery report with traffic light status]
```

## Command Interface

### Usage Patterns
```bash
# Use latest research report
/discover

# Use specific research report  
/discover research_diabetes_2024_08_21.md

# Direct topic search (bypass gap analysis)
/discover "mobile health apps 2023"
```

### Input Validation
- **Report names**: Must exist in `reports/` directory with `.md` extension
- **Topic strings**: Enclosed in quotes, 1-500 characters
- **No arguments**: Uses most recent `reports/research_*.md` file

## Gap Analysis Engine

### Cross-Domain Gap Detection Patterns
```python
# Enhanced gap patterns for comprehensive keyword extraction
gap_indicators = [
    'limited studies', 'few studies', 'gaps in', 'missing research',
    'insufficient evidence', 'more research needed', 'limited data',
    'underrepresented', 'lack of', 'limited coverage', 'future work',
    'technical challenges', 'implementation gaps', 'engineering limitations',
    'algorithm improvements', 'methodological gaps', 'design considerations'
]

# Focus on cross-domain terminology extraction
def extract_gap_keywords(text: str) -> List[str]:
    """Extract search keywords from gap descriptions for comprehensive search."""
    # Extract medical/research terms near gap indicators
    # Include technical and engineering terminology
    # Add cross-domain related terms
    # Return list of keywords for Semantic Scholar comprehensive search
```

### Simplified Parameter Extraction
```python
def extract_search_parameters(gap_text: str, research_topic: str) -> SearchParams:
    """Extract Semantic Scholar search parameters from gap descriptions."""
    
    # Extract keywords with cross-domain expansion
    keywords = extract_gap_keywords(gap_text) + extract_domain_terms(research_topic)
    
    # Infer study types from gap description (expanded for cross-domain)
    study_types = infer_study_types(gap_text)  # Includes technical papers, conference proceedings
    
    # Extract temporal parameters
    year_from = extract_year_requirements(gap_text)  # Default to 2020
    
    # Extract population focus for enhanced filtering
    population_focus = extract_population_terms(gap_text)
    
    # Extract quality threshold based on gap urgency
    quality_threshold = infer_quality_threshold(gap_text)
    
    return SearchParams(
        keywords=keywords[:10],  # Limit to 10 keywords for optimal search
        study_types=study_types,
        year_from=year_from,
        population_focus=population_focus,
        quality_threshold=quality_threshold,
        source='semantic_scholar'  # Comprehensive coverage in v3.1
    )
```

## Parameter Extraction

### Keyword Extraction
```python
def extract_keywords_from_gap(gap_description: str, research_topic: str) -> List[str]:
    """Extract relevant search keywords from gap descriptions."""
    
    # Primary keywords from gap description
    gap_keywords = extract_domain_terms(gap_description)
    
    # Context keywords from research topic
    topic_keywords = extract_domain_terms(research_topic)
    
    # Combine and deduplicate
    all_keywords = gap_keywords + topic_keywords
    
    # Add methodological terms based on gap type
    if 'intervention' in gap_description.lower():
        all_keywords.extend(['intervention', 'treatment', 'therapy'])
    
    if 'systematic review' in gap_description.lower():
        all_keywords.extend(['systematic review', 'meta-analysis'])
    
    # Add technical/engineering terms for cross-domain coverage
    if any(term in gap_description.lower() for term in ['technical', 'engineering', 'implementation']):
        all_keywords.extend(['algorithm', 'system design', 'implementation'])
    
    if any(term in gap_description.lower() for term in ['ai', 'machine learning', 'artificial intelligence']):
        all_keywords.extend(['machine learning', 'deep learning', 'neural networks'])
    
    return deduplicate_and_rank(all_keywords)
```

### Study Type Inference
```python
def infer_study_types_from_gap(gap_description: str) -> List[str]:
    """Infer appropriate study types based on gap description."""
    
    study_types = []
    
    # Methodological gaps suggest specific study types
    if 'limited RCT' in gap_description:
        study_types.append('rct')
    if 'systematic review' in gap_description:
        study_types.append('systematic_review')
    if 'longitudinal' in gap_description:
        study_types.append('cohort')
    if 'intervention' in gap_description:
        study_types.extend(['rct', 'intervention'])
    
    # Add technical publication types for cross-domain coverage
    if any(term in gap_description.lower() for term in ['technical', 'engineering', 'algorithm']):
        study_types.extend(['conference_paper', 'technical_report'])
    
    if 'implementation' in gap_description.lower():
        study_types.extend(['case_study', 'pilot_study'])
    
    # Default to comprehensive study types for cross-domain search
    if not study_types:
        study_types = ['systematic_review', 'rct', 'cohort', 'conference_paper']
    
    return study_types
```

### Temporal Parameter Generation
```python
def extract_temporal_parameters(gap_description: str) -> Dict[str, Any]:
    """Extract temporal search parameters from gap description."""
    
    temporal_params = {}
    
    # Explicit year mentions
    year_pattern = r'\b(19|20)\d{2}\b'
    years = re.findall(year_pattern, gap_description)
    
    # Temporal keywords
    if any(keyword in gap_description.lower() for keyword in ['recent', 'current', 'latest']):
        temporal_params['year_from'] = 2020
    elif any(keyword in gap_description.lower() for keyword in ['post-pandemic', 'covid', '2020']):
        temporal_params['year_from'] = 2020
    elif years:
        temporal_params['year_from'] = max(int(year) for year in years)
    
    return temporal_params
```

## Search Strategy Generation

### Strategy Templates
```python
search_strategies = {
    'coverage_gap': {
        'description': 'Fill missing research areas',
        'approach': 'Comprehensive cross-domain keyword search',
        'primary_source': 'semantic_scholar',
        'study_type_preference': ['systematic_review', 'rct', 'conference_paper']
    },
    'methodological_gap': {
        'description': 'Address study design limitations',
        'approach': 'Focus on methodological improvements',
        'primary_source': 'semantic_scholar',
        'study_type_preference': ['rct', 'cohort', 'systematic_review']
    },
    'technical_gap': {
        'description': 'Address implementation and engineering challenges',
        'approach': 'Technical and engineering literature focus',
        'primary_source': 'semantic_scholar',
        'study_type_preference': ['conference_paper', 'technical_report', 'case_study']
    },
    'temporal_gap': {
        'description': 'Find recent developments',
        'approach': 'Recent papers across all domains with recency weighting',
        'primary_source': 'semantic_scholar',
        'study_type_preference': ['any']
    },
    'demographic_gap': {
        'description': 'Address population limitations',
        'approach': 'Population-specific search with cross-domain coverage',
        'primary_source': 'semantic_scholar',
        'study_type_preference': ['rct', 'cohort', 'case_study']
    }
}
```

### Dynamic Strategy Selection
```python
def generate_search_strategy(gap_type: str, gap_text: str) -> str:
    """Generate human-readable search strategy explanation."""
    
    strategy_template = search_strategies.get(gap_type, search_strategies['coverage_gap'])
    
    # Customize strategy based on gap specifics
    if 'pediatric' in gap_text.lower():
        strategy_note = "Focus on pediatric populations across medical and technical literature"
    elif 'developing countries' in gap_text.lower():
        strategy_note = "Include global health and implementation research"
    elif 'intervention' in gap_text.lower():
        strategy_note = "Prioritize intervention studies and implementation research"
    elif any(term in gap_text.lower() for term in ['technical', 'engineering', 'algorithm']):
        strategy_note = "Emphasis on technical implementation and engineering solutions"
    else:
        strategy_note = "Comprehensive cross-domain search across all study types"
    
    return f"{strategy_template['description']} - {strategy_note}"
```

## Tool Integration

### Simplified Command Construction
```python
def build_discover_command(search_params: SearchParams, output_file: str) -> List[str]:
    """Build comprehensive command to call src/discover.py with Semantic Scholar."""
    
    cmd = ['python', 'src/discover.py']
    
    # Add required parameters
    cmd.extend(['--keywords', ','.join(search_params.keywords)])
    
    # Add optional parameters
    if search_params.study_types:
        cmd.extend(['--study-types', ','.join(search_params.study_types)])
    
    if search_params.year_from:
        cmd.extend(['--year-from', str(search_params.year_from)])
    
    if search_params.population_focus:
        cmd.extend(['--population-focus', search_params.population_focus])
    
    if search_params.quality_threshold:
        cmd.extend(['--quality-threshold', search_params.quality_threshold])
    
    # Add output file
    cmd.extend(['--output-file', output_file])
    
    # Source is Semantic Scholar in v3.1 for comprehensive coverage
    cmd.extend(['--source', 'semantic_scholar'])
    
    return cmd
```

### Simplified Result Processing
```python
def process_discovery_results(raw_output: str, search_params: SearchParams, gaps_found: List[str]) -> str:
    """Process discover.py output with minimal context enhancement."""
    
    # Add comprehensive header with gap context
    context_header = f"""
# Semantic Scholar Discovery Results

**Search Keywords**: {', '.join(search_params.keywords)}
**Research Context**: Comprehensive external paper discovery based on identified literature gaps
**Coverage**: Cross-domain search across 214M papers (medical, engineering, CS, behavioral research)

## Identified Gaps
{format_gaps_list(gaps_found)}

## Coverage Information
For specialized needs beyond comprehensive coverage, consider manual access:
- 🔍 **PubMed**: Clinical trial protocols, regulatory submissions
- 🔍 **IEEE**: Engineering standards, technical implementation details  
- 🔍 **arXiv**: Latest AI/ML preprints (6-12 months ahead)

---

"""
    
    # Combine with discovery tool output (already formatted correctly)
    enhanced_report = context_header + raw_output
    
    # Add simple next steps
    next_steps = """
## Next Steps
1. **Import high-confidence papers**: Use DOI lists below for Zotero import
2. **Review abstracts**: Focus on papers scoring 70+ for relevance
3. **Check coverage**: If specialized sources needed, use manual access links above
4. **Update research strategy**: Consider how discovered papers inform your direction
5. **Cross-domain insights**: Look for unexpected connections between disciplines
"""
    enhanced_report += next_steps
    
    return enhanced_report
```

## Output Enhancement

### Gap-Contextualized Results
```markdown
# Discovery Results: Cross-Domain Coverage Gap

**Gap Analysis**: Fill missing research areas - Focus on pediatric populations with technical implementation
**Research Context**: Based on identified gaps in research literature across medical and technical domains

## Identified Gap
"Limited coverage of mobile health apps in diabetes management, particularly for pediatric populations in developing countries, with insufficient technical implementation guidance"

**Why this matters**: Pediatric diabetes management approaches differ significantly from adult protocols, mobile health solutions need age-appropriate design and cultural adaptation, and successful implementation requires both clinical validation and technical feasibility studies.

**Search approach**: Comprehensive cross-domain keyword search - Focus on pediatric populations with technical implementation coverage

---

# Discovery Results
**Generated**: 2024-08-21 10:30:00  
**Search Strategy**: Cross-domain coverage gap for mobile health interventions  
**Duration**: 1.8 minutes
**Coverage**: Semantic Scholar comprehensive search (214M papers)

## Search Parameters
- **Keywords**: diabetes, mobile health, pediatric, developing countries, implementation
- **Gap Type**: coverage_gap
- **Study Types**: systematic_review, rct, conference_paper, case_study
- **Year Range**: 2020-2024
- **Quality Threshold**: MEDIUM
- **Population Focus**: pediatric

[Rest of discover.py output...]

## Gap Analysis Summary
- **Gap Addressed**: ✅ Found 18 high-confidence papers addressing pediatric mobile health
- **Cross-domain Coverage**: ✅ Found 8 technical implementation papers + 10 clinical studies
- **Geographic Coverage**: ✅ Found 9 papers focusing on developing countries
- **Study Quality**: ✅ Located 6 systematic reviews, 7 RCTs, and 5 technical conference papers
- **Recent Research**: ✅ All high-confidence papers from 2022-2024

## Recommendations
Based on the identified gap and discovered papers:

1. **Prioritize Implementation Studies**: Focus on papers with real-world deployment data
2. **Cultural Adaptation**: Review papers addressing cultural factors in developing countries
3. **Age-Appropriate Design**: Examine studies with pediatric-specific design considerations
4. **Long-term Outcomes**: Look for studies with >6 month follow-up periods
```

### Integration with Research Workflow
```markdown
## Next Steps
1. **Import high-confidence papers**: Use provided DOI lists for Zotero import
2. **Update research strategy**: Consider how discovered papers inform your research direction  
3. **Identify collaborations**: Note key authors for potential research partnerships
4. **Gap reassessment**: Determine if identified gap is adequately addressed or requires further search

## Follow-up Analysis
Consider running additional targeted searches:
- `/discover "pediatric diabetes cultural adaptation"`
- `/discover "mobile health app usability children"`
```

## Configuration

### Slash Command Settings (Simplified)
```python
# Add to .claude/commands/discover.md frontmatter
---
description: Discover external papers via comprehensive Semantic Scholar search based on research gaps
argument-hint: [report_name.md] or ["search topic"] (optional - uses latest report if empty)
allowed-tools: Read, Bash(python src/discover.py:*)
model: claude-3-5-sonnet-20241022
---
```

### Simplified Default Parameters
```python
DISCOVER_DEFAULTS = {
    'max_gaps_per_report': 3,           # Analyze top 3 gaps only (manageable)
    'default_year_from': 2020,          # Default recent cutoff
    'default_limit': 50,                # Reasonable result limit for comprehensive coverage
    'max_keywords': 10,                 # Prevent overly complex queries
    'source': 'semantic_scholar',       # Comprehensive coverage in v3.1
    'default_quality_threshold': 'MEDIUM', # Balance between coverage and quality
    'cross_domain_expansion': True      # Enable cross-domain keyword expansion
}
```

## Error Handling

### Common Scenarios
```python
def handle_discover_errors(error_type: str, context: str) -> str:
    """Provide helpful error messages for common failure scenarios."""
    
    error_messages = {
        'no_report_found': """
No research reports found. Please:
1. Run `/research "your topic"` first to generate a research report
2. Or specify a topic directly: `/discover "your search topic"`
        """,
        
        'no_gaps_identified': """
No clear research gaps identified in the report. Try:
1. `/discover "specific topic"` for direct search
2. Review the research report for sections mentioning limitations or future work
        """,
        
        'api_error': """
External search temporarily unavailable. Please try again in a few minutes.
        """,
        
        'invalid_report': """
Report format not recognized. Ensure the file:
1. Is a markdown file (.md)
2. Contains research analysis with gap indicators
3. Is located in the reports/ directory
        """
    }
    
    return error_messages.get(error_type, f"Error: {context}")
```

## Testing Strategy

### Gap Detection Testing
```python
def test_gap_detection():
    """Test gap identification from various report formats."""
    
    test_reports = [
        "report_with_explicit_gaps.md",
        "report_with_implicit_limitations.md", 
        "report_with_methodological_concerns.md"
    ]
    
    for report in test_reports:
        gaps = parse_gaps_from_report(report)
        assert len(gaps) > 0, f"No gaps found in {report}"
        assert all(gap.priority > 0 for gap in gaps)
```

### Parameter Extraction Testing
```python
def test_simplified_parameter_extraction():
    """Test simplified conversion of gaps to PubMed search parameters."""
    
    gap_text = "Limited studies on mobile health apps in pediatric diabetes management"
    
    params = extract_search_parameters(gap_text, "diabetes research")
    
    assert "pediatric" in params.keywords
    assert "diabetes" in params.keywords  
    assert "mobile health" in params.keywords
    assert len(params.keywords) <= 10  # Simplified constraint
    assert params.source == "semantic_scholar"   # Comprehensive source
```

### Integration Testing
```python
def test_end_to_end_workflow():
    """Test complete workflow from report to results."""
    
    # Mock research report
    test_report = create_test_report_with_gaps()
    
    # Run discover command
    result = run_discover_command(test_report)
    
    # Validate output
    assert "Discovery Results" in result
    assert "DOI Lists for Zotero Import" in result
    assert len(extract_dois_from_result(result)) > 0
```

## Implementation Benefits

### Cross-Domain Intelligence
- **Comprehensive gap detection**: Pattern matching with cross-domain expansion
- **Semantic Scholar optimization**: 214M papers across all research domains
- **Enhanced parameter extraction**: Population focus, quality thresholds, technical terms
- **Consistent output format**: Matches gap analysis and discovery tool structure with coverage info

### Integration Efficiency
- **Reuses enhanced discovery tool infrastructure**: Same Semantic Scholar client, quality scoring, caching
- **Maximum infrastructure reuse**: Leverages all v3.1 enhanced scoring improvements
- **Minimal custom logic**: Focus on intelligent gap-to-parameter extraction
- **Clear expansion path**: Add specialized slash commands based on user feedback

### User Value
- **"What's out there?" capability**: Comprehensive external search across all domains
- **Cross-domain discovery**: Finds connections between medical, technical, and behavioral research
- **Coverage transparency**: Clear guidance on when specialized sources are needed
- **Research report integration**: Natural workflow from /research to /discover with comprehensive results
- **Professional capability**: Supports interdisciplinary research with 85% coverage of digital health

---

**This comprehensive design delivers intelligent cross-domain paper discovery while maximizing infrastructure reuse and maintaining consistency with the broader research assistant ecosystem. The Semantic Scholar foundation provides superior coverage with clear guidance for specialized database access when needed.**