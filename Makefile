# Makefile for AI-Native Knowledge Graph Project
# Cross-platform commands for testing, linting, and running
# Works on Windows (with Git Bash), macOS, and Linux

.PHONY: help test lint format clean install extract query app app-advanced setup

# Detect Python command (python3 or python)
PYTHON := $(shell command -v python3 2>/dev/null || echo python)
PIP := $(shell command -v pip3 2>/dev/null || echo pip)

# Default target
help:
	@echo "🚀 AI-Native Knowledge Graph - Available Commands"
	@echo "=================================================="
	@echo "Setup:"
	@echo "  make setup       - Full setup (install + extract)"
	@echo "  make install     - Install dependencies (Poetry or pip)"
	@echo "  make install-pip - Install with pip (cross-platform)"
	@echo ""
	@echo "Development:"
	@echo "  make test        - Run all tests and quality checks"
	@echo "  make test-fast   - Run tests without linting"
	@echo "  make test-advanced - Run advanced query tests"
	@echo "  make lint        - Run code linting (Ruff)"
	@echo "  make format      - Format code (Ruff)"
	@echo "  make clean       - Clean temporary files"
	@echo ""
	@echo "Core Functionality (Hiring Task):"
	@echo "  make extract     - Extract knowledge graph from README"
	@echo "  make query       - Test query interface with all 3 questions"
	@echo "  make query-advanced - Test advanced query with gitingest"
	@echo "  make compliance  - Run hiring task compliance tests"
	@echo ""
	@echo "Applications:"
	@echo "  make app         - Run basic Streamlit app (port 8501)"
	@echo "  make app-advanced - Run advanced Streamlit app (port 8502)"
	@echo "  make app-ai      - Run AI-enhanced app with Perplexity/OpenAI/Gemini (port 8503)"
	@echo ""
	@echo "Example workflow:"
	@echo "  make setup       # Install deps + extract knowledge"
	@echo "  make test        # Run all tests"
	@echo "  make app         # Launch demo app"

# Cross-platform setup and installation
setup: install extract
	@echo "🎯 Development environment setup complete!"
	@echo "Knowledge graph extracted and ready to use."
	@echo "Try: make query or make app"

install:
	@echo "📦 Installing dependencies..."
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Using Poetry..."; \
		poetry install; \
	else \
		echo "Poetry not found, using pip..."; \
		$(MAKE) install-pip; \
	fi

install-pip:
	@echo "📦 Installing with pip (cross-platform)..."
	@echo "Creating virtual environment..."
	@$(PYTHON) -m venv .venv || (echo "❌ Failed to create venv. Install Python 3.9+ and try again." && exit 1)
	@echo "Activating virtual environment and installing..."
	@if [ "$(OS)" = "Windows_NT" ]; then \
		.venv/Scripts/pip.exe install -r requirements.txt; \
	else \
		.venv/bin/pip install -r requirements.txt; \
	fi
	@echo "✅ Installation complete! To activate:"
	@if [ "$(OS)" = "Windows_NT" ]; then \
		echo "   .venv\\Scripts\\activate"; \
	else \
		echo "   source .venv/bin/activate"; \
	fi

# Development and testing commands
test:
	@echo "🧪 Running comprehensive test suite..."
	@$(PYTHON) scripts/run_tests.py

test-fast:
	@echo "⚡ Running fast tests (skip linting)..."
	@$(PYTHON) scripts/run_tests.py --skip-lint

test-advanced:
	@echo "🧪 Running advanced query system tests..."
	@$(PYTHON) tests/test_advanced_query.py

lint:
	@echo "🔍 Running linter..."
	@$(PYTHON) -m ruff check *.py

format:
	@echo "✨ Formatting code..."
	@$(PYTHON) -m ruff format *.py

format-check:
	@echo "🔍 Checking code formatting..."
	@$(PYTHON) -m ruff format --check *.py

clean:
	@echo "🧹 Cleaning temporary files..."
	@if [ "$(OS)" = "Windows_NT" ]; then \
		if exist __pycache__ rmdir /s /q __pycache__; \
		if exist .pytest_cache rmdir /s /q .pytest_cache; \
		if exist temp rmdir /s /q temp; \
		del /q *.pyc 2>nul || true; \
	else \
		rm -rf __pycache__/ .pytest_cache/ temp/ *.pyc 2>/dev/null || true; \
		find . -name "*.pyc" -delete 2>/dev/null || true; \
		find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true; \
	fi

# Core functionality (hiring task requirements)
extract:
	@echo "📊 Extracting knowledge graph from README..."
	@$(PYTHON) src/extract.py --repo-url https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python/v1.x.x/README.md

query:
	@echo "❓ Testing query interface with all 3 required questions..."
	@echo "========================================================="
	@echo "Query 1: What is the Frequenz SDK for?"
	@$(PYTHON) src/query.py "What is the Frequenz SDK for?"
	@echo ""
	@echo "Query 2: How do I install the sdk?"
	@$(PYTHON) src/query.py "How do I install the sdk?"
	@echo ""
	@echo "Query 3: Show me an example of how to use it."
	@$(PYTHON) src/query.py "Show me an example of how to use it."

query-advanced:
	@echo "🚀 Testing advanced query interface with gitingest..."
	@echo "==================================================="
	@echo "Advanced Query 1: What are the main features?"
	@$(PYTHON) src/query_advanced.py "What are the main features?"
	@echo ""
	@echo "Advanced Query 2: How to install?"
	@$(PYTHON) src/query_advanced.py "How to install?"
	@echo ""
	@echo "Repository Structure Analysis:"
	@$(PYTHON) src/query_advanced.py --analyze-structure

compliance:
	@echo "✅ Running hiring task compliance tests..."
	@$(PYTHON) tests/test_compliance.py

# Applications
app:
	@echo "🌐 Starting basic Streamlit app..."
	@echo "Navigate to: http://localhost:8501"
	@$(PYTHON) -m streamlit run src/apps/app.py

app-advanced:
	@echo "🚀 Starting advanced Streamlit app..."
	@echo "Navigate to: http://localhost:8502"
	@$(PYTHON) -m streamlit run src/apps/app_advanced.py --server.port 8502

app-ai:
	@echo "🤖 Starting AI-enhanced Streamlit app..."
	@echo "Navigate to: http://localhost:8503"
	@echo "Configure API keys in sidebar for Perplexity, OpenAI, or Gemini"
	@$(PYTHON) -m streamlit run src/apps/app_enhanced.py --server.port 8503

# Visualization
visualize-dot:
	@echo "📈 Generating DOT visualization..."
	@$(PYTHON) src/visualize.py --format dot --out data/knowledge_graph.dot

visualize-svg:
	@echo "📈 Generating SVG visualization..."
	@$(PYTHON) src/visualize.py --format svg --out data/knowledge_graph.svg

# Poetry-specific commands (when Poetry is available)
poetry-install:
	@echo "📦 Installing with Poetry..."
	@poetry install

poetry-test:
	@echo "🧪 Running tests with Poetry..."
	@poetry run python scripts/run_tests.py

poetry-extract:
	@echo "📊 Extracting with Poetry..."
	@poetry run extract --repo-url https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python/v1.x.x/README.md

poetry-query:
	@echo "❓ Querying with Poetry..."
	@poetry run query "What is the Frequenz SDK for?"

# Quality gates for CI/CD
ci-test: lint test compliance
	@echo "🎉 All CI checks passed!"

# Development workflow shortcuts
dev: setup test
	@echo "🚀 Development environment ready!"
	@echo "Next steps:"
	@echo "  make query    # Test queries"
	@echo "  make app      # Launch demo"

full-test: clean lint test compliance
	@echo "✅ Full test suite completed!"

# Cross-platform status check
status:
	@echo "🔍 System Status Check"
	@echo "======================"
	@echo "Python: $(PYTHON)"
	@echo "Pip: $(PIP)"
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Poetry: ✅ Available"; \
	else \
		echo "Poetry: ❌ Not installed (using pip fallback)"; \
	fi
	@if command -v ruff >/dev/null 2>&1; then \
		echo "Ruff: ✅ Available"; \
	else \
		echo "Ruff: ❌ Not installed (run make install first)"; \
	fi
	@if command -v streamlit >/dev/null 2>&1; then \
		echo "Streamlit: ✅ Available"; \
	else \
		echo "Streamlit: ❌ Not installed (run make install first)"; \
	fi
	@if [ -f "project_knowledge.jsonld" ]; then \
		echo "Knowledge Graph: ✅ Generated"; \
	else \
		echo "Knowledge Graph: ❌ Missing (run make extract)"; \
	fi