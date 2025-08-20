---
description: Research literature using local knowledge base
argument-hint: <research topic or keywords>
allowed-tools: Read, Write, Task, Bash(python src/cli.py:*)
---

# Literature Research: $ARGUMENTS

I'll conduct a comprehensive literature review on this topic.

## My Approach

For efficient research, I'll use a division of labor:

1. **Research Helper (Haiku)** - For mechanical tasks:
   - Searching the knowledge base
   - Reading papers and extracting sections
   - Providing raw data and summaries

2. **Main Analysis (Me)** - For intellectual work:
   - Planning the research strategy
   - Analyzing and interpreting findings
   - Synthesizing across multiple sources
   - Identifying patterns and gaps
   - Drawing conclusions
   - Writing the final report

This approach allows me to:

- Process more papers without context overflow
- Focus my reasoning on analysis rather than data retrieval
- Provide deeper insights and synthesis

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
