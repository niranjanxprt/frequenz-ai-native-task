# Development Documentation

This is a personal project for demonstration purposes.

## Development Setup

### Prerequisites
- Python 3.9+
- Git

### Environment Setup

#### Option 1: Using Poetry (Recommended)
```bash
# Install Poetry first: https://python-poetry.org/docs/#installation
poetry install
poetry shell  # Activate the virtual environment
```

#### Option 2: Using pip + requirements.txt
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Development Commands
```bash
# Run tests
make test
python scripts/run_tests.py

# Format code
make format
ruff format .

# Lint code
make lint
ruff check .

# Start applications
make app           # Basic app
make app-advanced  # Advanced app
```

## Project Structure
```
src/
├── extract.py          # Knowledge extraction
├── query.py           # Natural language queries
├── query_advanced.py  # Advanced queries with GitIngest
├── visualize.py       # Graph visualization
└── apps/
    ├── app.py         # Basic Streamlit demo
    └── app_advanced.py # Advanced demo

scripts/
├── run_basic_app.py   # Launch basic Streamlit app
├── run_advanced_app.py # Launch advanced Streamlit app
└── run_tests.py       # Test runner

tests/
└── test_compliance.py # Compliance tests

data/
├── frequenz-floss-frequenz-sdk-python-LLM.txt  # Source data
├── knowledge_graph.dot      # Generated knowledge graph
└── project_knowledge.jsonld # JSON-LD knowledge base
```

## Code Style
- Use **Ruff** for formatting and linting
- Follow existing code patterns
- Keep dependencies minimal and lightweight

## Testing
- All core functionality must pass compliance tests
- Run `python tests/test_compliance.py -v` before deployment
