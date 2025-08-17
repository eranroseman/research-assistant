# Research Assistant for Claude Code

A powerful literature research tool that integrates with Claude Code through slash commands, enabling semantic search across a local knowledge base of academic papers.

## Features

- **Semantic Search**: Uses FAISS and sentence transformers for intelligent paper discovery
- **Local Knowledge Base**: Portable, version-controlled collection of papers
- **Claude Integration**: Custom `/research` slash command for seamless workflow
- **IEEE Citations**: Automatic generation of properly formatted references
- **Offline Operation**: No internet required after initial setup
- **Fast Performance**: Sub-second searches across thousands of papers

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Demo

```bash
# Build demo knowledge base and test functionality
python demo.py
```

### 3. Use in Claude Code

```
/research digital health interventions
```

## Installation

### Prerequisites

- Python 3.8+
- Claude Code (for slash command integration)
- ~2GB disk space for knowledge base

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/eranroseman/research-assistant.git
   cd research-assistant
   ```

2. **Install Python packages**
   ```bash
   pip install -r requirements.txt
   ```

3. **Build knowledge base** (choose one):
   
   a. Demo database (5 sample papers):
   ```bash
   python build_kb.py --demo
   ```
   
   b. From local Zotero library:
   ```bash
   # Ensure Zotero is running with local API enabled
   python build_kb.py
   ```

4. **Test the CLI**
   ```bash
   python cli.py info
   python cli.py search "your topic"
   ```

5. **Claude Code integration** is automatic - the `/research` command will be available immediately

## Usage

### CLI Commands

#### Search for papers
```bash
# Basic search
python cli.py search "digital health barriers"

# With more results and abstracts
python cli.py search "telemedicine" -k 20 -v

# JSON output for scripting
python cli.py search "AI diagnosis" --json
```

#### Retrieve full paper
```bash
# Display paper
python cli.py get 0001

# Save to file
python cli.py get 0001 -o paper.md
```

#### Generate citations
```bash
python cli.py cite "wearable devices" -k 5
```

#### Check knowledge base
```bash
python cli.py info
```

### Claude Code Slash Command

In any Claude Code conversation:

```
/research barriers to digital health adoption in elderly populations
```

Claude will:
1. Search the knowledge base for relevant papers
2. Analyze the top 10-20 matches
3. Extract key findings and evidence
4. Generate a comprehensive research report
5. Include IEEE-style citations

### Research Report Format

Reports include:
- **Executive Summary**: Overview of findings
- **Key Findings**: Bulleted insights with citations
- **Evidence Quality**: Confidence levels for different findings
- **References**: IEEE-formatted bibliography

## Building Your Own Knowledge Base

### From Local Zotero Library

1. **Enable Zotero Local API**:
   - Open Zotero (version 7 or later recommended)
   - Go to Edit → Settings → Advanced
   - Check "Allow other applications on this computer to communicate with Zotero"
   - Restart Zotero if needed

2. **Run builder**:
   ```bash
   # With Zotero running
   python build_kb.py
   ```

3. **Processing time**: 10-30 minutes for 2000 papers

Note: The local API connects to `http://localhost:23119/api/` and doesn't require API keys.

### From Custom Sources

Modify `build_kb.py` to implement a custom `process_papers()` function that returns a list of dictionaries with:

```python
{
    'title': str,
    'authors': List[str],
    'year': int,
    'journal': str,
    'volume': str,
    'issue': str,
    'pages': str,
    'doi': str,
    'abstract': str,
    'full_text': str  # Optional
}
```

## File Structure

```
research-assistant/
├── .claude/
│   └── commands/
│       └── research.md      # Slash command definition
├── kb_data/                 # Knowledge base (git-ignored)
│   ├── index.faiss          # Semantic search index
│   ├── metadata.json        # Paper metadata
│   └── papers/              # Full text markdown files
├── build_kb.py              # Knowledge base builder
├── cli.py                   # Command-line interface
├── demo.py                  # Demo and test script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Advanced Usage

### Custom Embedding Models

Edit `build_kb.py` and `cli.py` to change the model:

```python
self.model = SentenceTransformer('your-model-name')
```

Popular alternatives:
- `all-mpnet-base-v2`: Higher quality, slower
- `all-MiniLM-L12-v2`: Good balance
- `multi-qa-mpnet-base-dot-v1`: Optimized for Q&A

### Adjusting Search Parameters

In `cli.py`, modify the FAISS index type:

```python
# For larger databases (>100k papers)
index = faiss.IndexIVFFlat(nlist=100)

# For similarity threshold filtering
index = faiss.IndexFlatL2(dimension)
```

### Batch Processing

Process multiple queries:

```bash
for topic in "AI" "telemedicine" "wearables"; do
    python cli.py search "$topic" --json > "results_$topic.json"
done
```

## Troubleshooting

### "Knowledge base not found"
Run `python build_kb.py --demo` to create the database.

### Slow searches
- Reduce search scope with more specific queries
- Use fewer results: `-k 5` instead of `-k 20`
- Check if antivirus is scanning the FAISS index

### Memory errors
- Use `faiss-cpu` instead of `faiss-gpu`
- Process papers in batches in `build_kb.py`
- Reduce embedding model size

### Zotero connection issues
- Ensure Zotero is running
- Check "Allow other applications" is enabled in Settings → Advanced
- Verify Zotero is accessible at http://localhost:23119/api/
- Try restarting Zotero after enabling the API

### WSL-specific setup (Zotero on Windows host)
When running in WSL with Zotero on the Windows host:

1. **Enable Zotero API**: In Zotero → Edit → Settings → Advanced → Check "Allow other applications"

2. **Configure Windows Firewall**:
   - Open Windows Defender Firewall with Advanced Security
   - Add Inbound Rule for TCP port 23119
   - Allow connections from WSL subnet (usually 172.x.x.x)

3. **Run with auto-detection**:
   ```bash
   python build_kb.py  # Auto-detects WSL and Windows host IP
   ```

4. **Or specify manually**:
   ```bash
   # Find Windows host IP in WSL
   cat /etc/resolv.conf | grep nameserver
   
   # Use that IP
   python build_kb.py --api-url http://<windows-ip>:23119/api
   ```

## Performance

- **Build time**: 10-30 min for 2000 papers
- **Search time**: <1 second for 2000 papers
- **Storage**: ~1MB per paper (including full text)
- **Memory**: ~500MB during search operations

## Contributing

Contributions welcome! Areas for improvement:

- Additional citation formats (APA, MLA, Chicago)
- PDF extraction improvements
- Multi-language support
- Web UI for knowledge base management
- Integration with other reference managers

## License

MIT License - See LICENSE file for details

## Acknowledgments

- FAISS by Facebook Research
- Sentence Transformers by UKPLab
- Claude Code by Anthropic

## Support

For issues or questions:
1. Check troubleshooting section
2. Review demo.py for examples
3. Open an issue with error messages and steps to reproduce