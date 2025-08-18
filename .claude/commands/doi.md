---
description: Search for peer-reviewed articles and return DOIs
argument-hint: <research topic or keywords> (optional - uses previous /research topic if empty)
allowed-tools: WebSearch, WebFetch, Grep, Read
model: claude-3-haiku-20240307
---

# DOI Finder for Academic Articles

## Determine Search Topic

First, I'll check if arguments were provided or if I should use the topic from a previous /research command:

If "$ARGUMENTS" is empty:
- Check for recent research reports in reports/ folder
- Extract the topic from the most recent research report filename
- Use that topic for the DOI search

Otherwise:
- Use the provided arguments: $ARGUMENTS

I'll search for peer-reviewed articles related to the determined topic.

## Step 1: Search for Academic Articles

Searching multiple academic sources for relevant peer-reviewed papers:

### Search on Google Scholar and Academic Databases

I'll search for scholarly articles using academic-focused queries to find DOIs.

## Step 2: Extract and Format DOIs

After finding relevant articles, I'll extract their DOIs and present them in a structured list.

## Output Format

The results will be presented as:

### Found Articles for "$ARGUMENTS":

1. **[Article Title]**
   - Authors: [Author Names]
   - Journal: [Journal Name, Year]

2. **[Article Title]**
   - Authors: [Author Names]
   - Journal: [Journal Name, Year]

[Continue for all found articles...]

### DOIs:

```
10.xxxx/xxxxx
10.xxxx/xxxxx
10.xxxx/xxxxx
10.xxxx/xxxxx
10.xxxx/xxxxx
```

### Search Strategy

- Focus on peer-reviewed journals
- Include recent publications (last 10 years unless specified otherwise)
- Prioritize high-impact journals
- Look for systematic reviews and meta-analyses when relevant

### Note

- Results limited to articles with valid DOIs
- Preprints and non-peer-reviewed sources excluded
- Conference proceedings included only if peer-reviewed
