---
description: Quick DOI search for academic articles
argument-hint: <research topic or keywords> (optional - uses previous /research topic if empty)
allowed-tools: WebSearch, WebFetch, Read, Write
model: claude-3-haiku-20240307
---

# DOI Search: $ARGUMENTS

Searching for academic article DOIs on: $ARGUMENTS

If no topic provided, I'll check `reports/` for recent research gaps.

## Search Plan

1. Search PubMed, Google Scholar, and academic databases
2. Extract DOIs from results (pattern: `10.\d{4,}/[-._;()/:\w]+`)
3. Save to `reports/dois_<topic>_<timestamp>.txt`

## Results

```text
[DOIs will appear here]
```