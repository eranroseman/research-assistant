# Contributing to Research Assistant

Thank you for your interest in contributing to Research Assistant! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use issue templates when available
3. Include:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version)
   - Error messages and logs

### Suggesting Features

1. Open an issue with the "enhancement" label
2. Describe the feature and its use case
3. Explain why it would benefit users
4. Consider implementation approach if possible

### Submitting Pull Requests

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/research-assistant.git
   cd research-assistant
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set up development environment**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Make your changes**
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed
   - Keep commits focused and atomic

5. **Run tests and checks**
   ```bash
   # Run tests
   python -m pytest

   # Type checking
   mypy src/

   # Code formatting
   ruff format .

   # Linting
   ruff check .
   ```

6. **Submit pull request**
   - Write clear PR description
   - Reference related issues
   - Ensure CI checks pass
   - Respond to review feedback

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to all public functions

### Testing

- Write unit tests for new features
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use pytest for testing framework

### Documentation

- Update README for user-facing changes
- Add docstrings following Google style
- Include examples in documentation
- Update CLI help text if needed

## Project Structure

```
research-assistant/
├── .claude/                 # Claude Code integration
│   └── commands/           # Slash commands
├── kb_data/                # Knowledge base data
│   ├── index.faiss        # Vector search index
│   ├── metadata.json      # Paper metadata
│   └── papers/            # Full text papers
├── exports/                # User-valuable analysis and exports
├── reviews/                # Literature review reports 
├── system/                 # Development and system artifacts
├── build_kb.py            # Knowledge base builder
├── cli.py                 # Command-line interface
├── requirements.txt       # Python dependencies
├── requirements-dev.txt   # Development dependencies
├── README.md             # Project documentation
├── LICENSE               # MIT license
└── CONTRIBUTING.md       # This file
```

## Areas for Contribution

Current areas where contributions are especially welcome:

- **Citation Formats**: Add support for APA, MLA, Chicago styles
- **PDF Processing**: Improve text extraction from PDFs
- **Multi-language**: Support for non-English papers
- **Web Interface**: Create a web UI for the tool
- **Performance**: Optimize search and indexing
- **Testing**: Increase test coverage
- **Documentation**: Improve user guides and examples
- **Integration**: Support for more reference managers

## Questions?

Feel free to open an issue for questions about contributing or join discussions in existing issues.

Thank you for contributing to Research Assistant!
