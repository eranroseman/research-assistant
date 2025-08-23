---
description: Research literature using local knowledge base
argument-hint: <research topic or keywords>
allowed-tools: Read, Write, Task, Bash(python src/cli.py:*), Bash(python src/discover.py:*)
---

# Literature Research: $ARGUMENTS

I'll conduct a comprehensive literature review, adapting my approach based on what will yield the most insightful results.

### When to use subagents

**Research-helper subagents for:**

- Complex multi-step data retrieval
- Multiple coordinated searches benefiting from batch operations
- Specific data extraction from multiple papers
- Systematic literature mapping

**Literature-analyzer subagents for:**

- Deep methodological assessment of retrieved papers (>10 papers)
- Evidence synthesis requiring systematic quality evaluation
- Cross-paper pattern analysis and theme extraction
- Implementation science or systematic review approaches

**Avoid literature-analyzer when:**

- Few papers (<10) where direct analysis is faster
- Simple background research not requiring methodological rigor
- Time-sensitive queries where speed over depth is priority

### When direct CLI execution is more effective

- Quick iterative searches based on initial results
- Testing different search terms or quality thresholds
- Single focused queries rather than comprehensive mapping
- Immediate analysis of specific papers found

### Performance optimization
- **Batch operations**: 10-20x faster for multiple commands
- **Parallel subagents**: Launch multiple subagents simultaneously
- **Smart search**: Use for 20+ papers efficiently

## Available Resources

**Knowledge Base:** ~2,100 academic papers with quality scoring (0-100 scale)
**Documentation:** Complete command options in `docs/api-reference.md`

### Key Commands

- Search: `python src/cli.py search "query" [--min-quality N] [--show-quality]`
- Get paper: `python src/cli.py get XXXX [--sections abstract methods results]`
- Batch operations: `python src/cli.py batch --preset research "topic"`
- Smart search: `python src/cli.py smart-search "query" -k 30` (for 20+ papers)
- Citations: `python src/cli.py cite XXXX XXXX XXXX` (space-separated IDs)

### Quality considerations
- Higher quality scores provide stronger evidence
- Recent systematic reviews may summarize earlier work
- Multiple search approaches reveal complementary literature

## Analysis Workflow

### Helper provides

- Paper IDs, titles, authors, quality scores
- Extracted sections (abstracts, methods, results)
- Search results with relevance rankings
- Raw data for analysis

### I concentrate on

- Analyzing patterns across studies
- Synthesizing conflicting findings
- Identifying methodological strengths/weaknesses
- Drawing evidence-based conclusions
- Writing comprehensive reports

## Output

I'll generate a comprehensive report saved to `reports/research_<topic>_<timestamp>.md`. The specific format will depend on your research question - it might be:

- A systematic evidence synthesis
- A comparative analysis with detailed evidence synthesis
- An implementation-focused review with practical insights
- A methodological assessment for research planning

The report will include appropriate citations, quality assessments where helpful, and identification of knowledge gaps. When coverage assessment reveals significant gaps, the report will distinguish between "what we know from current evidence" and "what's missing from the literature" with specific recommendations for KB expansion.

### Citation Guidelines
- **Strong claims need citations**: Statistics, clinical outcomes, definitive statements
- **IEEE format**: Numbered citations [1], [2], [3]; prioritize quality papers (>70 score)
- **References**: Generate with `python src/cli.py cite XXXX XXXX`

## Coverage Assessment Strategy

Discovery is a powerful tool for identifying knowledge gaps - trust your research instincts about when to use it.

### When Discovery Adds Value

Research coverage gaps often occur when topics have **specificity** that may not be well-represented in a general knowledge base. Trust your intuition when something feels incomplete.

**Research Intuition Signals** - if you find yourself thinking:
- "This seems important, but results are surprisingly limited"
- "The evidence feels too general for this specific context"
- "I expected more targeted research on this intersection"
- "There should be more recent work on this emerging area"
- "The geographical/cultural/population focus seems underrepresented"

→ These intuitions often indicate coverage gaps worth exploring

### Discovery Commands
```bash
python src/discover.py --keywords "your,main,terms" --quality-threshold HIGH
python src/discover.py --coverage-info  # Workflow integration guidance
```

### Coverage Assessment Integration
- **🟢 Traffic Light**: Proceed confidently with KB analysis
- **🟡 Traffic Light**: Note limitations, consider targeted discovery for specific gaps
- **🔴 Traffic Light**: Significant gaps likely - discovery recommended for comprehensive analysis

**Comprehensive research approach**: Analyze what we know + identify what we're missing + provide specific recommendations

Let me explore the literature and see what emerges.
