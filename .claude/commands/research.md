---
description: Research literature using local knowledge base
argument-hint: <research topic or keywords>
allowed-tools: Read, Write, Task, Bash(python src/cli.py:*)
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

The report will include appropriate citations, quality assessments where helpful, and identification of knowledge gaps in the research literature.

### Citation Guidelines
- **Strong claims need citations**: Statistics, clinical outcomes, definitive statements
- **IEEE format**: Numbered citations [1], [2], [3]; prioritize quality papers (>70 score)
- **References**: Generate with `python src/cli.py cite XXXX XXXX`

**Note on Knowledge Base Limitations:** If I find that our knowledge base appears incomplete for your research topic (e.g., fewer than 10 highly relevant papers, missing recent studies from 2023+, or obvious gaps in coverage), I'll notify you and ask for guidance on whether to:

- Proceed with available papers and note limitations in the report
- Suggest specific papers/DOIs to add to strengthen coverage
- Adjust the research scope to better match available evidence
- Focus on related topics where we have stronger coverage

Let me explore the literature and see what emerges.
