---
description: Research literature using local knowledge base (v3.1 with smart section chunking)
argument-hint: <topic or research question>
allowed-tools: Bash, Read, Grep, Task
---

# Research Assistant v3.1 - Smart Section Chunking & Incremental Updates

I'll search the academic knowledge base for papers related to: $ARGUMENTS

## New Features in v3.1

**🚀 Performance Improvements:**
- 40-50% faster searches with optimized batch processing
- O(1) cache lookups for instant repeated searches
- Dynamic memory-based batch sizing for optimal performance
- 10x faster incremental KB updates with `--update` flag
- Sections index for O(1) section retrieval

**🔍 SPECTER Search Modes:**
- `--mode auto`: Automatically detect search intent (default)
- `--mode question`: Optimized for answering specific research questions
- `--mode similar`: Find papers similar to a topic or concept
- `--mode explore`: Broad exploration of research areas

**📊 Quality Scoring:**
- `--show-quality`: Display quality scores (0-100) for each paper
- `--quality-min N`: Filter results by minimum quality score
- Quality factors: study type hierarchy, recency, sample size, full-text availability

**🧠 Smart Features:**
- **Smart section chunking**: `smart-get` and `get --sections` reduce text by 70%
- **Automatic query expansion**: Medical/research synonyms added automatically
- **Personal shortcuts**: `--shortcut` command with `.research_shortcuts.yaml`
- **Duplicate detection**: `duplicates` command identifies similar papers
- **Evidence gap analysis**: `--analyze-gaps` flag for systematic review insights
- **KB portability**: Export/import for syncing between computers

## Available Search Options

**Core parameters:**
- `-k N`: Number of results (default: 10, use 30-50 for comprehensive reviews)
- `--after YEAR`: Filter by publication year (use for "recent" or "latest" queries)
- `--type TYPE`: Filter by study type (multiple allowed with separate flags)
  - Types: `systematic_review`, `rct`, `cohort`, `case_control`, `cross_sectional`, `case_report`, `study`
- `--verbose`: Include abstracts in output
- `--json`: Output as JSON for processing

**Enhanced SPECTER parameters:**
- `--mode [auto|question|similar|explore]`: Search mode optimization
- `--show-quality`: Show quality scores in results
- `--quality-min N`: Minimum quality score (0-100)
- `--analyze-gaps`: Perform evidence gap analysis for systematic reviews
- `--shortcut NAME`: Use predefined search shortcuts from `.research_shortcuts.yaml`

**Smart retrieval commands:**
- `smart-get PAPER_ID`: Get paper with intelligent section chunking (70% less text)
- `get PAPER_ID --sections`: Retrieve specific sections only
- `duplicates`: Identify and manage duplicate papers in knowledge base

**When to apply filters:**
- Research questions (containing "?", "what", "how", "why") → Mode automatically detects as "question"
- Finding similar work → Use `--mode similar` with paper title or concept
- Medical/clinical queries → Add `--quality-min 70` for high-quality evidence
- Technical/implementation topics → Use `--mode explore` for broader coverage
- Temporal queries (containing "recent", "latest", "current", "emerging") → Add `--after 2020`
- Quick specific answers → Keep default `-k 10`
- Comprehensive literature reviews → Increase to `-k 30-50`
- Common research topics → Use `--shortcut NAME` for predefined queries
- Systematic reviews → Add `--analyze-gaps` to identify evidence gaps

**Understanding enhanced output:**
- Quality scores: ⭐ 80-100 (excellent), ● 60-79 (good), ○ 40-59 (moderate), · <40 (lower)
- Study types with visual hierarchy: ⭐ = systematic review, ● = RCT, ◐ = cohort, ○ = case-control
- RCTs display sample size: `Type: RCT (n=487) | Quality: 85/100`
- Score indicates relevance (1.0 = perfect match, <0.5 = weak match)
- Evidence hierarchy: systematic reviews > RCTs > cohort > case-control > cross-sectional > case reports

## Personal Shortcuts System

**Create and use personal shortcuts** for frequently searched topics:

1. **Create a shortcut**: Save common search patterns in `.research_shortcuts.yaml`
2. **Use shortcuts**: Reference saved searches with `--shortcut NAME`
3. **Example shortcuts**:
   - `diabetes_treatment`: "diabetes treatment clinical trials systematic review"
   - `covid_mental_health`: "COVID-19 mental health depression anxiety --after 2020 --quality-min 70"
   - `ml_healthcare`: "machine learning artificial intelligence healthcare --mode explore"

**Shortcut file format** (`.research_shortcuts.yaml`):
```yaml
diabetes_treatment:
  query: "diabetes treatment clinical trials"
  mode: "question"
  quality_min: 70
  after: 2020

covid_mental_health:
  query: "COVID-19 mental health depression anxiety"
  after: 2020
  quality_min: 70

ml_healthcare:
  query: "machine learning artificial intelligence healthcare"
  mode: "explore"
  k: 30
```

**Usage**: `python src/cli.py search --shortcut diabetes_treatment`

## Knowledge Base Portability

**Export/Import functionality** allows syncing knowledge bases between computers:

1. **Export KB**: `python src/cli.py export kb_backup.tar.gz`
   - Creates compressed archive with all KB data
   - Includes papers, embeddings, metadata, and cache files
   - Portable across different systems

2. **Import KB**: `python src/cli.py import kb_backup.tar.gz`
   - Restores complete knowledge base from archive
   - Overwrites existing KB if present
   - Maintains all search performance optimizations

3. **Use cases**:
   - Sync research libraries between work and home computers
   - Backup knowledge base before major updates
   - Share curated paper collections with colleagues
   - Move to new machine without rebuilding from Zotero

## Search Strategy

I'll use an enhanced multi-phase search approach leveraging SPECTER2's capabilities:

### Phase 1: Knowledge Base Check & Auto-Detection

First, check if the knowledge base exists:
!python src/cli.py info 2>/dev/null || echo "NO_KB"

If the knowledge base doesn't exist (returns "NO_KB" or error), prompt the user:
- "No knowledge base found. Would you like to build one from your Zotero library?"
- If yes: Run `python src/build_kb.py` to build the knowledge base
- For faster updates: Use `python src/build_kb.py --update` (10x faster incremental updates)
- The build process now features:
  - 🚀 40-50% faster with optimized batch sizing
  - 🔒 Secure JSON/NPY cache format (no pickle vulnerabilities)
  - 💾 O(1) cache lookups for instant rebuilds
  - 📚 Sections index for efficient text retrieval
  - 🔄 Automatic query expansion with medical/research synonyms
- After building, continue with the search

### Phase 2: Intelligent Search with Mode Detection

The search will automatically detect the best mode based on your query:
!python src/cli.py search "$ARGUMENTS" -k 10 --mode auto --show-quality --json > /tmp/initial_results.json

Query patterns and their automatic modes:
- Questions ("what causes...", "how does...", "?") → `question` mode
- Similarity requests ("papers like...", "similar to...") → `similar` mode
- Broad topics ("overview of...", "landscape...") → `explore` mode
- Specific topics → `standard` mode

**Automatic query expansion**: The system now automatically expands queries with medical and research synonyms to improve recall without requiring manual intervention.

### Phase 3: Quality-Based Filtering

For medical/clinical topics requiring high-quality evidence:
!python src/cli.py search "$ARGUMENTS" --quality-min 70 --type systematic_review --type rct -k 20 --json > /tmp/filtered_results.json

For exploratory research accepting broader evidence:
!python src/cli.py search "$ARGUMENTS" --mode explore -k 30 --json > /tmp/search_results.json

### Phase 4: Adaptive Expansion & Gap Analysis
Based on initial results quality scores:
- **Excellent results** (quality >80, relevance >0.85): Proceed with top 10
- **Good results** (quality 60-80, relevance 0.70-0.85): Expand to k=20
- **Moderate results** (quality 40-60, relevance <0.70): Broaden search with explore mode
- **Insufficient results** (<5 papers): Remove quality filters, increase k to 50

**Evidence Gap Analysis**: For systematic reviews or comprehensive searches, run:
!python src/cli.py search "$ARGUMENTS" --analyze-gaps --json > /tmp/gap_analysis.json

This identifies:
- Underrepresented study types or populations
- Temporal gaps in research
- Geographic or demographic coverage issues
- Methodological limitations across studies

**Duplicate Detection**: Check for and manage duplicates:
!python src/cli.py duplicates --json > /tmp/duplicates.json

## Evidence Distribution Assessment

After searching, I'll provide an enhanced quality summary:

**Evidence Distribution by Type & Quality:**
- ⭐ **Systematic Reviews/Meta-analyses**: [count] papers (avg quality: [score]/100)
- ● **RCTs**: [count] papers (total n=[sum] participants, avg quality: [score]/100)
- ◐ **Cohort Studies**: [count] papers (avg quality: [score]/100)
- ○ **Case-Control Studies**: [count] papers (avg quality: [score]/100)
- ◔ **Cross-Sectional Studies**: [count] papers (avg quality: [score]/100)
- · **Case Reports/Other**: [count] papers (avg quality: [score]/100)

**Quality Score Distribution:**
- **Excellent (80-100)**: [count] papers - Prioritize for complete reading
- **Good (60-79)**: [count] papers - Review key sections
- **Moderate (40-59)**: [count] papers - Scan for unique insights
- **Lower (<40)**: [count] papers - Consider only if filling gaps

**Overall Confidence Assessment:**
- **High confidence**: ≥3 papers with quality >80 OR ≥5 RCTs with n>100
- **Medium confidence**: 1-2 papers with quality >80 OR 2-4 RCTs
- **Low confidence**: Primarily papers with quality <60 or observational studies

**If Evidence is Insufficient:**
- Note the evidence gap clearly in the report
- Suggest using `/doi` command to find additional papers beyond the current knowledge base
- Recommend specific search terms or study types needed
- Example: "Limited RCTs found. Use `/doi [topic] randomized controlled trial` to find more"

## Paper Selection Guidelines

When reviewing search results, I'll use the enhanced quality-relevance matrix:

**Quantity Guidelines by Research Goal:**

- For specific interventions/treatments: Focus on 5-10 papers with quality >70
- For broad overviews/comparisons: Review 10-20 papers across quality tiers
- For comprehensive landscape analysis: Consider 20-30+ papers including moderate quality
- For quick clinical questions: 3-5 papers with quality >80 may suffice

**Quality-Relevance Matrix for Paper Selection:**

```
High Quality (80-100) + High Relevance (>0.85): 📖 Complete reading
High Quality (80-100) + Moderate Relevance (0.70-0.85): 📑 Strategic sections
Moderate Quality (60-79) + High Relevance (>0.85): 📑 Strategic sections
Moderate Quality (60-79) + Moderate Relevance (0.70-0.85): 📋 Abstract + key results
Lower Quality (<60) + High Relevance (>0.85): 📋 Abstract only
Lower Quality (<60) + Lower Relevance (<0.70): ⏭️ Skip unless fills specific gap
```

**Natural Breakpoints Detection:**

- Quality score drops >20 points between consecutive papers
- Relevance score gaps >0.15 between consecutive papers
- Study type transitions (e.g., from RCTs to observational studies)
- Example: Papers 1-5 (quality 85-90), gap, Papers 6+ (quality <65)
- Stop detailed review at natural breakpoints unless specific insights needed

## Systematic Paper Reading Strategy

**Quality-Driven Tiered Reading Approach with Smart Retrieval:**

### Tier 1: Complete Reading (2-3 papers)
Selection criteria (must meet at least 2):
- Quality score ≥85 AND relevance >0.80
- Systematic reviews/meta-analyses with quality ≥80
- RCTs with n>500 participants AND quality ≥75
- Papers with contrarian findings AND quality ≥70
- Papers identified as "landmark" in metadata

**Smart reading approach:**
1. Use `smart-get PAPER_ID` for intelligent section chunking (70% less context)
2. Focus on methodology, results, and limitations sections
3. Note quality factors that contributed to high score

### Tier 2: Strategic Sections (5-10 papers)
Selection criteria:
- Quality score 70-84 OR relevance 0.75-0.90
- Important supporting studies with moderate quality
- Papers filling specific evidence gaps

**Efficient section-based reading:**
1. Use `get PAPER_ID --sections abstract,methods,results,discussion` for targeted retrieval
2. **Discussion & Limitations** sections are critical for quality papers
3. Focus on methodology validation and result interpretation
4. 70% reduction in text processing with smart chunking

### Tier 3: Abstract + Key Results (remaining papers)
Selection criteria:
- Quality score 50-69 OR relevance 0.60-0.74
- Confirmatory studies
- Papers for completeness

**Quick scan approach:**
- Use `get PAPER_ID --sections abstract,conclusions` for rapid review
- Abstract only if quality <60
- Skip if both quality <50 AND relevance <0.60

**Performance Benefits:**
- **70% less text**: Smart section chunking reduces Claude's context usage dramatically
- **O(1) section retrieval**: Sections index enables instant access to specific parts
- **Targeted reading**: Focus only on relevant sections for each quality tier

**Key Insight:** The discussion and limitations sections often contain critical caveats, alternative interpretations, and acknowledged weaknesses that may not appear in abstracts or conclusions. Smart section retrieval makes accessing these efficiently possible.

## Step 5: Clean Up

Remove the temporary search results file:

!rm -f /tmp/search_results.json /tmp/gap_analysis.json /tmp/duplicates.json && echo "✓ Temporary search results deleted" || echo "✗ Failed to delete search results"

## Step 6: Analyze and Synthesize

After retrieving the papers, I'll:

1. Analyze their content for key findings
2. Assess the quality and strength of evidence
3. Identify patterns and themes across papers
4. Note any conflicting evidence or gaps

## Step 7: Generate Research Report

Now I'll compile the findings into a comprehensive research report. The report will be saved in the reports/ folder with a filename that includes the search topic and timestamp for easy identification.

### Report Filename Convention

The report will be saved as: `reports/research_[sanitized_arguments]_[YYYYMMDD_HHMMSS].md`

- Sanitized arguments: Replace spaces with underscores, remove special characters
- Example: For query "unidirectional vs bidirectional sms" on 2025-01-17 at 14:30:45
- Filename: `reports/research_unidirectional_vs_bidirectional_sms_20250117_143045.md`

First, ensure the reports directory exists:
!mkdir -p reports && echo "✓ Reports directory ready" || echo "✗ Failed to create reports directory"

## Research Report Structure

### 1. Executive Summary (2-3 paragraphs)

- Brief overview of the research question
- Main findings and conclusions
- Practical implications

### 2. Key Findings (bulleted list)

- Each finding supported by citations [1], [2], etc.
- Group related findings together
- Highlight consensus vs. conflicting evidence

### 3. Evidence Quality Assessment

- **High confidence**: Strong, consistent evidence across multiple studies
- **Medium confidence**: Moderate evidence with some limitations
- **Low confidence**: Limited evidence, needs more research

### 4. Detailed Analysis

- Synthesize information across papers
- Identify patterns and themes
- Note methodological strengths and limitations

### 5. Knowledge Gaps & Evidence Analysis

- Areas lacking sufficient research (from gap analysis if performed)
- Contradictory findings requiring clarification
- Future research directions
- **Duplicate concerns**: Note any identified duplicates and how they were handled
- **Evidence distribution gaps**: Highlight underrepresented populations, study types, or geographic regions
- **Expanding the evidence base**: If critical gaps exist, use `/doi [specific topic]` to find additional papers

### 6. References (IEEE format)

Format: [#] Author(s), "Title," Journal, vol. X, no. Y, pp. ZZZ-ZZZ, Month Year.

## Quality Criteria

When analyzing papers, consider:

- Study design and methodology (prioritize systematic reviews and RCTs)
- Sample size and population (especially important for RCTs)
- Statistical significance and effect sizes
- Reproducibility and validation
- Recency and relevance
- Author expertise and institutional affiliation

For RCTs specifically:

- Sample sizes are shown in search results: `Type: RCT (n=487)`
- Pilot RCTs (n<50): Limited power, interpret cautiously
- Standard RCTs (n=50-200): Generally reliable for effect estimates
- Large RCTs (n>500): Landmark studies, prioritize for full reading
- Total pooled sample size across all RCTs provides overall evidence strength

## Citation Guidelines

- Use bracketed numbers for in-text citations: [1], [2], [3]
- For multiple citations, use ranges [1]-[3] or lists [1], [4], [7]
- Place citations immediately after the relevant statement
- Ensure every citation in the text has a corresponding reference

Generate the research report based on the papers found, ensuring all claims are properly cited and the evidence quality is clearly indicated.

## Performance Notes

**v3.0 Improvements:**
- 🚀 **40-50% faster searches**: Optimized batch processing and O(1) cache lookups
- ⚡ **10x faster updates**: Incremental KB updates with `--update` flag
- 🔒 **Enhanced security**: Command injection prevention, path traversal protection, safe cache serialization
- 📊 **Better evidence assessment**: Quality scores help prioritize high-value papers
- 🎯 **Smarter search modes**: SPECTER2 automatically optimizes for your query type
- 💾 **Efficient rebuilds**: Cached embeddings persist across sessions for instant repeated searches
- 🧠 **Smart retrieval**: 70% less context usage with intelligent section chunking
- 🔄 **Automatic expansion**: Medical/research synonyms added to queries automatically
- 📚 **Personal shortcuts**: Save common search patterns in `.research_shortcuts.yaml`
- 🔍 **Duplicate detection**: Identify and manage similar papers across the knowledge base
- 📈 **Gap analysis**: Systematic identification of evidence gaps for comprehensive reviews
- 🌐 **KB portability**: Export/import functionality for syncing between computers

**Tips for Optimal Performance:**
- First search may take ~30s to load the model, subsequent searches are instant
- Use `--quality-min 70` to quickly filter for high-quality evidence
- Use `--mode question` for research questions to get more targeted results
- Use `smart-get` or `get --sections` to reduce context usage by 70%
- Create shortcuts for frequently searched topics with `--shortcut`
- Run `duplicates` command periodically to maintain KB quality
- Use `--update` flag for 10x faster incremental knowledge base updates
- Use `--analyze-gaps` for systematic reviews to identify evidence gaps
