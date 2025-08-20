"""Research Assistant v4.0 - Semantic Literature Search Tool.

A knowledge base builder and search interface for academic literature,
optimized for use with Claude Code. Uses Multi-QA MPNet embeddings for
semantic search across scientific papers from Zotero libraries.

Main modules:
- build_kb: Build and maintain knowledge base from Zotero
- cli: Command-line interface for search and retrieval
- config: Central configuration for all settings

Features:
- Semantic search with Multi-QA MPNet embeddings
- Quality scoring based on study type (0-100 scale)
- Smart incremental updates
- PDF text extraction and caching
- Section extraction (methods, results, etc.)
- IEEE citation generation
- CSV export for analysis
"""

__version__ = "4.0.0"
