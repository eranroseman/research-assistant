---
description: Research literature using local knowledge base
argument-hint: <research topic or keywords>
allowed-tools: Read, Write, Task, Bash(python src/cli.py:*)
---

# Literature Research: $ARGUMENTS

I'll conduct a comprehensive literature review on this topic.

## My Approach

I'll delegate data retrieval to a specialized research-helper agent while I focus on analysis:

### When I Use the Research Helper

1. **Initial comprehensive search** - "Use batch preset research for '[topic]' to get complete analysis"
2. **Custom batch operations** - "Run these searches as a batch: [list of queries]"
3. **Specific data extraction** - "Find sample sizes in paper 0123"
4. **Follow-up searches** - "Search for papers on [subtopic] from 2020-2024"
5. **Citation gathering** - "Generate citations for papers 0001-0010"

**IMPORTANT**: The helper now uses the batch command which is 10-20x faster for multiple operations.

### What the Helper Returns

- Paper IDs, titles, authors, quality scores
- Extracted sections (abstracts, methods, results)
- Search results with relevance rankings
- Raw data for my analysis

### My Focus

With the helper handling data retrieval, I concentrate on:

- Analyzing patterns across studies
- Synthesizing conflicting findings
- Identifying methodological strengths/weaknesses
- Drawing evidence-based conclusions
- Writing comprehensive reports

## Research Strategy

### For Best Results

- **Start broad, then narrow**: Initial search → Review high-quality papers → Targeted follow-ups
- **Prioritize by quality**: Focus on papers with quality scores >70 for core evidence
- **Check recency**: Recent systematic reviews (2022+) often summarize earlier work
- **Multiple searches**: Different keywords may reveal complementary literature

### Typical Workflow

1. **Discovery phase**: Helper uses `batch --preset research "[topic]"` for comprehensive analysis (5 searches + top papers in one command)
2. **Deep dive**: Automatic retrieval of top 10 papers with the preset
3. **Gap analysis**: I identify what's missing, helper does targeted batch searches
4. **Synthesis**: I analyze all findings and write comprehensive report

**Performance Note**: The batch preset completes in ~5 seconds what previously took 80-100 seconds!

## Available Resources

The knowledge base contains ~2,100 academic papers. For complete command documentation and options, see `docs/api-reference.md`. Key capabilities include:

- Semantic search with quality filtering (0-100 scale)
- Study type filtering (systematic reviews, RCTs, etc.)
- Direct paper access via 4-digit IDs
- IEEE citation generation
- Smart search for handling 20+ papers efficiently

## Output

I'll generate a comprehensive report saved to `reports/research_<topic>_<timestamp>.md` that includes:

- Executive summary
- Key findings with evidence quality assessment
- Synthesis across studies
- Knowledge gaps and future directions
- IEEE citations for all referenced papers

Let me know if you have specific requirements for the research focus or output format.
