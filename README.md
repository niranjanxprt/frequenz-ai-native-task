# Frequenz SDK — AI‑Native Knowledge Graph (Hiring Task)

This mini-project turns the **Frequenz SDK for Python** into AI-friendly, machine-readable knowledge.

## Contents
- `extract.py` — Scrape README and generate **JSON‑LD** → `project_knowledge.jsonld`.
- `query.py` — Load that JSON‑LD and answer simple NL questions (keyword retrieval).
- `requirements.txt` — Minimal deps.

## Quickstart
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Generate JSON-LD from upstream README (defaults shown)
python extract.py --repo-url https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python

# Use a GitHub web URL (with /blob/); extractor converts to raw automatically
python extract.py --repo-url https://github.com/frequenz-floss/frequenz-sdk-python/blob/v1.x.x/README.md

# Ask questions
python query.py "What is the Frequenz SDK for?"
python query.py "How do I install the sdk?"
python query.py "Show me an example of how to use it."
```

## Poetry
- Install: `pipx install poetry` (or follow Poetry docs)
- Setup env and deps: `poetry install`
- Run tools via Poetry:
  - `poetry run extract --repo-url https://raw.githubusercontent.com/frequenz-floss/frequenz-sdk-python`
  - `poetry run extract --repo-url https://github.com/frequenz-floss/frequenz-sdk-python/blob/v1.x.x/README.md`
  - `poetry run query "How do I install the sdk?"`
  - `poetry run visualize --format dot --out project_knowledge.dot`

## Visualize the graph
- Generate Graphviz DOT: `python visualize.py --in project_knowledge.jsonld --out project_knowledge.dot`
- Optional SVG (requires Graphviz `dot`): `python visualize.py --format svg --out project_knowledge.svg`
- With Poetry: `poetry run visualize --format svg --out project_knowledge.svg`

The visualization includes nodes for the software, author, license, repository, programming language,
requirements, install steps, features, and examples.

## Streamlit app
- Install deps via Poetry: `poetry install`
- Run the app: `poetry run streamlit run app.py`
- In the sidebar, either load an existing `project_knowledge.jsonld` or click "Extract from README.md" to fetch and build it.
- The app shows:
  - A summary of the software metadata
  - An interactive graph (Graphviz) built from JSON‑LD
  - A question box to ask about purpose, installation, examples, features, license, and dependencies

## Schema design
Root type: `SoftwareApplication` (schema.org) with:
- `name`, `description`, `programmingLanguage`, `codeRepository`, `license`, `softwareRequirements`
- Installation via `HowTo` + `HowToStep`
- Examples via `SoftwareSourceCode`
- Features via `featureList` (flat list for simplicity)

## Process
- Fetch raw README from GitHub, render Markdown → HTML, parse sections/bullets/code
- Heuristics assemble a compact JSON‑LD
- Retrieval: semantic matching with TF‑IDF cosine over purpose/install/example/features/license/dependencies
  (falls back to keyword buckets if sklearn is unavailable)

## Improvements
- Add embeddings + BM25 hybrid over per-section chunks (PGVector)
- JSON answers with Pydantic schemas + citations + confidence
- GitHub Action to auto‑regenerate on README changes
- Publish JSON‑LD on docs + create/maintain Wikidata/SEO signals

## Tests
- Run with stdlib unittest (no extra deps):
  - `python -m unittest discover -s tests -p "test_*.py" -v`
  - Or via Poetry: `poetry run python -m unittest discover -s tests -v`

Tests cover bucket detection and answer generation for: purpose, installation, example, features, license, and dependencies.
