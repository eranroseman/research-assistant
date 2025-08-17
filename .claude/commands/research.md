---
description: Research literature using local knowledge base
argument-hint: <topic or research question>
allowed-tools: Bash, Read, Grep, Task
---

# Research Assistant

I'll search the academic knowledge base for papers related to: $ARGUMENTS

## Step 1: Execute Search

First, I'll search for relevant papers using semantic similarity:

!python cli.py search "$ARGUMENTS" -k 20 --json > /tmp/search_results.json 2>&1 && echo "✓ Search completed" || echo "✗ Search failed"

## Step 2: Verify Search Results

Now I'll verify the search results were saved correctly:

!test -s /tmp/search_results.json && echo "✓ Results file contains data" || echo "✗ Results file is empty or missing"

## Step 3: Review Search Results

Let me examine the search results to identify the most relevant papers:

@/tmp/search_results.json

## Step 4: Retrieve Full Papers

Based on the search results above, I'll now retrieve the full text of the most relevant papers (top 5-10 with highest similarity scores):

For each paper with ID from the search results, I'll read: kb_data/papers/paper_{id}.md

## Step 5: Clean Up

Remove the temporary search results file:

!rm -f /tmp/search_results.json && echo "✓ Temporary search results deleted" || echo "✗ Failed to delete search results"

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

### 5. Knowledge Gaps

- Areas lacking sufficient research
- Contradictory findings requiring clarification
- Future research directions

### 6. References (IEEE format)

Format: [#] Author(s), "Title," Journal, vol. X, no. Y, pp. ZZZ-ZZZ, Month Year.

## Quality Criteria

When analyzing papers, consider:

- Study design and methodology
- Sample size and population
- Statistical significance and effect sizes
- Reproducibility and validation
- Recency and relevance
- Author expertise and institutional affiliation

## Citation Guidelines

- Use bracketed numbers for in-text citations: [1], [2], [3]
- For multiple citations, use ranges [1]-[3] or lists [1], [4], [7]
- Place citations immediately after the relevant statement
- Ensure every citation in the text has a corresponding reference

Generate the research report based on the papers found, ensuring all claims are properly cited and the evidence quality is clearly indicated.
