---
description: Research literature using local knowledge base
argument-hint: <research topic or keywords>
allowed-tools: Read, Write, Task, Bash(python src/cli.py:*)
---

# Literature Research: $ARGUMENTS

I'll conduct a comprehensive literature review on this topic.

## My Approach

I'll adapt my approach based on what will yield the most insightful results for this specific topic.

### Research-helper subagents are useful when

- Complex multi-step data retrieval is needed
- Multiple coordinated searches would benefit from batch operations
- Specific data extraction from multiple papers is required
- The research question requires systematic literature mapping

**Performance note**: Batch operations can be 10-20x faster for multiple commands.

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

## Research Approach

I'll adapt my approach based on what will yield the most insightful results for this specific topic.

### Quality considerations

- Papers with higher quality scores often provide stronger evidence
- Recent systematic reviews may summarize earlier work effectively
- Multiple search approaches can reveal complementary literature

**Key capabilities at my disposal:**

- Batch operations (10-20x faster for multiple commands)
- Direct paper access via `kb_data/papers/paper_XXXX.md`
- IEEE citations using `python src/cli.py cite XXXX XXXX XXXX`
- Knowledge base coverage assessment

## Execution Considerations

The nature of "$ARGUMENTS" will guide my approach:

**Direct CLI execution when:**

- The research question is focused and targeted
- I want to iterate immediately based on results
- The query is straightforward and well-defined

## Available Resources

The knowledge base contains ~2,100 academic papers. For complete command documentation and options, see `docs/api-reference.md`. Key capabilities include:

- Semantic search with quality filtering (0-100 scale)
- Study type filtering (systematic reviews, RCTs, etc.)
- Direct paper access via 4-digit IDs
- IEEE citation generation
- Smart search for handling 20+ papers efficiently

## Output

I'll generate a comprehensive report saved to `reports/research_<topic>_<timestamp>.md`. The specific format will depend on your research question - it might be:

- A systematic evidence synthesis
- A comparative analysis with detailed evidence synthesis
- An implementation-focused review with practical insights
- A methodological assessment for research planning

The report will include appropriate citations, quality assessments where helpful, and identification of knowledge gaps in the research literature.

**Note on Knowledge Base Limitations:** If I find that our knowledge base appears incomplete for your research topic (e.g., very few relevant papers, missing recent studies, or gaps in coverage), I'll notify you and ask for guidance on whether to:

- Proceed with available papers
- Suggest specific papers/DOIs to add
- Adjust the research scope

Let me explore the literature and see what emerges.
