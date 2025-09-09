# Development Documentation

This is a personal project for demonstration purposes.

## Development Setup

### Prerequisites
- Python 3.9+
- Git

### Environment Setup
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
```

## Code Style
- Use **Ruff** for formatting and linting
- Follow existing code patterns
- Keep dependencies minimal and lightweight

## Testing
- All core functionality must pass compliance tests
- Run `python tests/test_compliance.py -v` before deployment
