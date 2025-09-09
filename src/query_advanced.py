#!/usr/bin/env python3
"""
query_advanced.py
-----------------
Advanced query system that combines JSON-LD knowledge with live repository analysis using gitingest.
Provides enhanced retrieval with real-time code context and repository insights.

Features:
- Live repository ingestion via gitingest
- Enhanced semantic search with code context
- Repository structure analysis
- Real-time dependency detection
- Advanced knowledge graph querying

Usage:
    python query_advanced.py "How to install this?"
    python query_advanced.py --repo https://github.com/frequenz-floss/frequenz-sdk-python "What are the main features?"
    python query_advanced.py --analyze-structure "Show me the project layout"
"""

import re
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

# Import base query functionality
from query import load_knowledge, TfidfRetriever, answer, pick_bucket, BUCKETS

try:
    from gitingest import ingest

    GITINGEST_AVAILABLE = True
except ImportError:
    GITINGEST_AVAILABLE = False
    print("Warning: gitingest not available. Install with: pip install gitingest")


@dataclass
class RepositoryContext:
    """Enhanced repository context from gitingest analysis."""

    summary: str
    tree: str
    content: str
    file_count: int
    total_size: int
    languages: List[str]
    dependencies: List[str]
    structure: Dict[str, Any]

    @classmethod
    def from_gitingest_file(
        cls, file_path: str = "data/frequenz-floss-frequenz-sdk-python-LLM.txt"
    ) -> Optional["RepositoryContext"]:
        """Create repository context from existing GitIngest file."""
        try:
            if not Path(file_path).exists():
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract basic structure from the beginning of the file
            lines = content.split("\n")
            structure_lines = []

            # Find where directory structure ends and content begins
            for i, line in enumerate(lines):
                if line.startswith("=====") or "File:" in line:
                    break
                structure_lines.append(line)

            # Extract file information
            key_files = []
            file_sections = re.findall(r"File: ([^\n]+)", content)
            key_files = [f.strip() for f in file_sections[:20]]  # First 20 files

            # Extract dependencies from pyproject.toml or requirements
            dependencies = []
            pyproject_match = re.search(
                r"pyproject\.toml.*?\n(.*?)(?=File:|=====|\Z)", content, re.DOTALL
            )
            if pyproject_match:
                deps_content = pyproject_match.group(1)
                deps = re.findall(r"([a-zA-Z][a-zA-Z0-9_-]+)\s*=", deps_content)
                dependencies.extend([dep for dep in deps if dep not in ["python"]])

            return cls(
                summary=f"GitIngest analysis of frequenz-sdk-python from file {file_path}",
                content=content,
                structure=structure_lines,
                key_files=key_files,
                dependencies=dependencies[:10],
                last_updated=datetime.now(),
            )

        except Exception as e:
            print(f"Error loading GitIngest file: {e}")
            return None

    @classmethod
    def from_gitingest(cls, repo_url: str) -> "RepositoryContext":
        """Create repository context from gitingest analysis."""
        if not GITINGEST_AVAILABLE:
            raise ImportError("gitingest is required for repository analysis")

        try:
            summary, tree, content = ingest(repo_url)

            # Parse additional metadata from content
            file_count = len(
                [
                    line
                    for line in tree.split("\n")
                    if line.strip()
                    and not line.startswith("├─")
                    and not line.startswith("└─")
                ]
            )
            total_size = len(content)

            # Extract languages from file extensions in tree
            languages = set()
            for line in tree.split("\n"):
                if "." in line and line.strip():
                    # Extract filename from tree structure
                    filename = line.split("/")[-1] if "/" in line else line
                    filename = filename.split()[-1] if " " in filename else filename
                    if "." in filename:
                        ext = filename.split(".")[-1].strip()
                        if ext in [
                            "py",
                            "js",
                            "ts",
                            "java",
                            "cpp",
                            "c",
                            "go",
                            "rs",
                            "rb",
                            "toml",
                            "yml",
                            "yaml",
                            "md",
                        ]:
                            languages.add(ext)

            # Extract dependencies from common files
            dependencies = []

            # Look for pyproject.toml dependencies
            pyproject_match = re.search(
                r"pyproject\.toml.*?\n(.*?)(?=\n\S|\Z)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if pyproject_match:
                toml_content = pyproject_match.group(1)
                # Extract dependencies from [tool.poetry.dependencies] or similar
                deps_section = re.search(
                    r"\[tool\.poetry\.dependencies\](.*?)(?=\[|\Z)",
                    toml_content,
                    re.DOTALL,
                )
                if deps_section:
                    deps_content = deps_section.group(1)
                    # Find package names
                    deps = re.findall(r"([a-zA-Z][a-zA-Z0-9_-]+)\s*=", deps_content)
                    dependencies.extend([dep for dep in deps if dep not in ["python"]])

            # Look for requirements.txt
            req_match = re.search(
                r"requirements.*?\.txt.*?\n(.*?)(?=\n\S|\Z)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if req_match:
                req_content = req_match.group(1)
                deps = [
                    line.strip().split("==")[0].split(">=")[0].split("<")[0]
                    for line in req_content.split("\n")
                    if line.strip() and not line.startswith("#")
                ]
                dependencies.extend(deps[:10])

            # Basic structure analysis
            structure = {
                "has_tests": any(
                    word in content.lower()
                    for word in ["test_", "tests/", "pytest", "unittest"]
                ),
                "has_docs": any(
                    word in content.lower()
                    for word in ["docs/", "readme", "documentation", "sphinx"]
                ),
                "has_ci": any(
                    word in content.lower()
                    for word in [".github", "ci.yml", "workflow", "action"]
                ),
                "has_docker": "dockerfile" in content.lower()
                or "docker-compose" in content.lower(),
                "has_makefile": "makefile" in content.lower(),
                "main_files": [],
                "config_files": [],
            }

            # Extract main files from tree
            for line in tree.split("\n"):
                line_lower = line.lower()
                if any(
                    main in line_lower
                    for main in ["main.py", "app.py", "__init__.py", "__main__.py"]
                ):
                    structure["main_files"].append(line.strip())
                if any(
                    conf in line_lower
                    for conf in [
                        "config",
                        "settings",
                        ".env",
                        "pyproject.toml",
                        ".yml",
                        ".yaml",
                    ]
                ):
                    structure["config_files"].append(line.strip())

            # Detect if it's a Python package
            structure["is_python_package"] = (
                "setup.py" in content.lower() or "pyproject.toml" in content.lower()
            )

            # Look for specific Frequenz SDK patterns
            structure["frequenz_patterns"] = {
                "has_actors": "actor" in content.lower(),
                "has_channels": "channel" in content.lower(),
                "has_microgrid": "microgrid" in content.lower(),
                "has_timeseries": "timeseries" in content.lower(),
                "has_battery": "battery" in content.lower(),
                "has_pv": "pv" in content.lower() or "solar" in content.lower(),
                "has_ev": "ev" in content.lower() or "charger" in content.lower(),
            }

            return cls(
                summary=summary,
                tree=tree,
                content=content,
                file_count=file_count,
                total_size=total_size,
                languages=list(languages),
                dependencies=list(set(dependencies)),  # Remove duplicates
                structure=structure,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to analyze repository: {e}")


class AdvancedQueryEngine:
    """Enhanced query engine with repository context and advanced retrieval."""

    def __init__(
        self,
        knowledge_path: str = "project_knowledge.jsonld",
        repo_context: Optional[RepositoryContext] = None,
    ):
        self.knowledge_data = load_knowledge(knowledge_path)
        self.repo_context = repo_context
        self.retriever = None

        # Initialize retriever if possible
        try:
            self.retriever = TfidfRetriever.from_data(self.knowledge_data)
        except (ImportError, ValueError):
            pass

    def enhance_buckets(self) -> Dict[str, List[str]]:
        """Enhanced bucket keywords with repository-specific terms."""
        enhanced = BUCKETS.copy()

        if self.repo_context:
            # Add language-specific terms
            for lang in self.repo_context.languages:
                if lang == "py":
                    enhanced["example"].extend(
                        ["python", "def", "class", "import", "async"]
                    )
                elif lang == "toml":
                    enhanced["dependencies"].extend(["pyproject", "poetry", "build"])
                elif lang == "md":
                    enhanced["documentation"].extend(["markdown", "readme", "guide"])

            # Add dependency-specific terms
            enhanced["dependencies"].extend(
                [dep.lower() for dep in self.repo_context.dependencies]
            )

            # Add Frequenz-specific terms
            if self.repo_context.structure.get("frequenz_patterns"):
                patterns = self.repo_context.structure["frequenz_patterns"]
                if patterns.get("has_actors"):
                    enhanced["features"] = enhanced.get("features", []) + [
                        "actor",
                        "orchestration",
                    ]
                if patterns.get("has_channels"):
                    enhanced["features"] = enhanced.get("features", []) + [
                        "channel",
                        "communication",
                    ]
                if patterns.get("has_microgrid"):
                    enhanced["features"] = enhanced.get("features", []) + [
                        "microgrid",
                        "energy",
                    ]
                if patterns.get("has_timeseries"):
                    enhanced["features"] = enhanced.get("features", []) + [
                        "timeseries",
                        "data",
                        "streaming",
                    ]
                if (
                    patterns.get("has_battery")
                    or patterns.get("has_pv")
                    or patterns.get("has_ev")
                ):
                    enhanced["features"] = enhanced.get("features", []) + [
                        "battery",
                        "pv",
                        "ev",
                        "charger",
                    ]

        return enhanced

    def analyze_repository_structure(self) -> str:
        """Provide detailed repository structure analysis."""
        if not self.repo_context:
            return (
                "No repository context available. Use --repo to analyze a repository."
            )

        ctx = self.repo_context
        analysis = [
            "🔍 Frequenz SDK Python Repository Analysis",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            f"📁 Total Files: {ctx.file_count}",
            f"💾 Content Size: {ctx.total_size:,} characters",
            f"🔤 Languages: {', '.join(ctx.languages) if ctx.languages else 'Unknown'}",
            "",
            "🏗️ Project Structure:",
            "─" * 20,
        ]

        # Project type identification
        structure = ctx.structure
        if structure.get("is_python_package"):
            analysis.append("📦 Python Package/Library")

        # Add structure insights with emojis
        features = []
        if structure.get("has_tests"):
            features.append("✅ Test Suite")
        if structure.get("has_docs"):
            features.append("📚 Documentation")
        if structure.get("has_ci"):
            features.append("🔄 CI/CD Pipeline")
        if structure.get("has_docker"):
            features.append("🐳 Docker Support")
        if structure.get("has_makefile"):
            features.append("🔨 Makefile")

        if features:
            analysis.extend([""] + features)

        # Frequenz-specific features
        freq_patterns = structure.get("frequenz_patterns", {})
        freq_features = []
        if freq_patterns.get("has_actors"):
            freq_features.append("🎭 Actor Model")
        if freq_patterns.get("has_channels"):
            freq_features.append("📡 Channel Communication")
        if freq_patterns.get("has_microgrid"):
            freq_features.append("⚡ Microgrid Support")
        if freq_patterns.get("has_timeseries"):
            freq_features.append("📊 Time Series")
        if freq_patterns.get("has_battery"):
            freq_features.append("🔋 Battery Management")
        if freq_patterns.get("has_pv"):
            freq_features.append("☀️ Solar PV")
        if freq_patterns.get("has_ev"):
            freq_features.append("🚗 EV Charging")

        if freq_features:
            analysis.extend(["", "🌟 Frequenz SDK Features:", "─" * 23] + freq_features)

        # Dependencies
        if ctx.dependencies:
            analysis.extend(["", "📋 Key Dependencies:", "─" * 19])
            analysis.extend([f"  • {dep}" for dep in ctx.dependencies[:10]])

        # Main files
        main_files = structure.get("main_files", [])
        if main_files:
            analysis.extend(["", "🚀 Entry Points:", "─" * 16])
            analysis.extend([f"  • {f}" for f in main_files[:5]])

        # Config files
        config_files = structure.get("config_files", [])
        if config_files:
            analysis.extend(["", "⚙️ Configuration:", "─" * 17])
            analysis.extend([f"  • {f}" for f in config_files[:5]])

        # Directory structure (truncated)
        analysis.extend(["", "📂 Directory Tree:", "─" * 18])
        tree_lines = ctx.tree.split("\n")[:25]  # First 25 lines
        analysis.extend(tree_lines)
        if len(ctx.tree.split("\n")) > 25:
            analysis.append("  ... (truncated)")

        return "\n".join(analysis)

    def enhanced_semantic_search(
        self, question: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Enhanced semantic search combining JSON-LD and repository context."""
        results = []

        # Traditional semantic search on JSON-LD
        if self.retriever:
            json_results = self.retriever.search(question, top_k=3)
            for result in json_results:
                result["source"] = "json-ld"
                result["confidence"] = result["score"] * 1.2  # Boost JSON-LD results
                results.append(result)

        # Repository context search
        if self.repo_context:
            repo_results = self._search_repository_content(question, top_k=3)
            results.extend(repo_results)

        # Sort by confidence and return top_k
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return results[:top_k]

    def _search_repository_content(
        self, question: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Search within repository content using TF-IDF."""
        if not self.repo_context:
            return []

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            return []

        # Create meaningful chunks from repository content
        content = self.repo_context.content
        chunks = []

        # Split by file markers and create chunks
        file_sections = re.split(r"\n\s*FILE:\s*[^\n]+\n", content)

        for section in file_sections:
            if len(section.strip()) > 100:  # Skip very short sections
                # Further split long sections
                if len(section) > 2000:
                    # Split by functions, classes, or paragraphs
                    sub_chunks = re.split(
                        r"\n(?=class |def |async def |# |## )", section
                    )
                    for chunk in sub_chunks:
                        if len(chunk.strip()) > 100:
                            chunks.append(chunk.strip())
                else:
                    chunks.append(section.strip())

        if not chunks:
            return []

        # Limit chunks to prevent memory issues
        chunks = chunks[:50]

        # TF-IDF search
        try:
            vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
            tfidf_matrix = vectorizer.fit_transform(chunks + [question])
            similarities = cosine_similarity(
                tfidf_matrix[-1], tfidf_matrix[:-1]
            ).ravel()
        except ValueError:
            # Handle case where no vocabulary overlap
            return []

        # Get top matches
        top_indices = similarities.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0.05:  # Lower threshold for code content
                chunk_text = chunks[idx]
                # Truncate very long chunks
                display_text = (
                    chunk_text[:400] + "..." if len(chunk_text) > 400 else chunk_text
                )

                results.append(
                    {
                        "label": "repository-code",
                        "text": display_text,
                        "score": float(similarities[idx]),
                        "source": "repository",
                        "confidence": float(similarities[idx]),
                    }
                )

        return results

    def answer_question(
        self, question: str, use_enhanced: bool = True
    ) -> Tuple[str, str, List[Dict[str, Any]]]:
        """Answer question with optional enhanced context."""
        # Special handling for structure analysis
        if any(
            word in question.lower()
            for word in ["structure", "layout", "organization", "architecture"]
        ):
            return self.analyze_repository_structure(), "structure-analysis", []

        if use_enhanced and (self.repo_context or self.retriever):
            # Enhanced search
            search_results = self.enhanced_semantic_search(question)

            if search_results:
                best_result = search_results[0]

                # Generate comprehensive answer
                answer_parts = []

                # Primary answer from best match
                if best_result["source"] == "json-ld":
                    primary_answer = answer(self.knowledge_data, best_result["label"])
                    answer_parts.append(f"📋 From Knowledge Base:\n{primary_answer}")
                else:
                    answer_parts.append(
                        f"📁 From Repository Code:\n{best_result['text']}"
                    )

                # Add relevant repository context
                if self.repo_context:
                    repo_context = self._get_relevant_repo_context(question)
                    if repo_context:
                        answer_parts.append(
                            f"\n🔍 Repository Insights:\n{repo_context}"
                        )

                return "\n\n".join(answer_parts), best_result["label"], search_results

        # Fallback to basic query
        bucket = pick_bucket(question)
        basic_answer = answer(self.knowledge_data, bucket)
        return basic_answer, bucket, []

    def _get_relevant_repo_context(self, question: str) -> str:
        """Get relevant repository context based on question type."""
        if not self.repo_context:
            return ""

        context_parts = []
        ctx = self.repo_context
        q_lower = question.lower()

        # Installation/setup context
        if any(
            word in q_lower for word in ["install", "setup", "dependencies", "require"]
        ):
            if ctx.dependencies:
                dep_list = ", ".join(ctx.dependencies[:8])
                context_parts.append(f"📦 Dependencies: {dep_list}")
            if ctx.structure.get("is_python_package"):
                context_parts.append("🐍 Python package (use pip install)")

        # Example/usage context
        if any(word in q_lower for word in ["example", "usage", "how to", "code"]):
            main_files = ctx.structure.get("main_files", [])
            if main_files:
                context_parts.append(f"🚀 Entry points: {', '.join(main_files[:3])}")

        # Features context
        if any(word in q_lower for word in ["feature", "capability", "what", "does"]):
            freq_patterns = ctx.structure.get("frequenz_patterns", {})
            features = []
            if freq_patterns.get("has_actors"):
                features.append("Actor orchestration")
            if freq_patterns.get("has_microgrid"):
                features.append("Microgrid management")
            if freq_patterns.get("has_timeseries"):
                features.append("Time series data")
            if freq_patterns.get("has_battery"):
                features.append("Battery systems")
            if freq_patterns.get("has_pv"):
                features.append("Solar PV")
            if freq_patterns.get("has_ev"):
                features.append("EV charging")

            if features:
                context_parts.append(f"⚡ Key capabilities: {', '.join(features)}")

        # Testing context
        if any(word in q_lower for word in ["test", "testing", "quality"]):
            if ctx.structure.get("has_tests"):
                context_parts.append("✅ Has comprehensive test suite")
            if ctx.structure.get("has_ci"):
                context_parts.append("🔄 Continuous integration enabled")

        # Documentation context
        if any(word in q_lower for word in ["doc", "documentation", "guide", "help"]):
            if ctx.structure.get("has_docs"):
                context_parts.append("📚 Documentation available")

        return " | ".join(context_parts)


def main():
    parser = argparse.ArgumentParser(
        description="Advanced Frequenz SDK query system with repository analysis"
    )
    parser.add_argument("question", nargs="*", help="Natural language question")
    parser.add_argument(
        "--repo",
        default="https://github.com/frequenz-floss/frequenz-sdk-python",
        help="Repository URL (default: Frequenz SDK Python)",
    )
    parser.add_argument(
        "--knowledge", default="project_knowledge.jsonld", help="Knowledge file path"
    )
    parser.add_argument(
        "--analyze-structure", action="store_true", help="Analyze repository structure"
    )
    parser.add_argument(
        "--search-results", type=int, default=3, help="Number of search results to show"
    )
    parser.add_argument(
        "--basic", action="store_true", help="Use basic query without enhancements"
    )
    parser.add_argument(
        "--no-repo", action="store_true", help="Skip repository analysis"
    )

    args = parser.parse_args()

    if not args.question and not args.analyze_structure:
        print("Please provide a question or use --analyze-structure")
        print("Examples:")
        print("  python query_advanced.py 'How to install the SDK?'")
        print("  python query_advanced.py 'What are the main features?'")
        print("  python query_advanced.py --analyze-structure")
        return

    # Initialize repository context if not disabled
    repo_context = None
    if not args.no_repo:
        if not GITINGEST_AVAILABLE:
            print("⚠️  gitingest not available. Install with: pip install gitingest")
            print("Continuing with basic knowledge base only...\n")
        else:
            print(f"🔍 Analyzing repository: {args.repo}")
            try:
                repo_context = RepositoryContext.from_gitingest(args.repo)
                print(
                    f"✅ Repository analyzed: {repo_context.file_count} files, {len(repo_context.languages)} languages\n"
                )
            except Exception as e:
                print(f"❌ Error analyzing repository: {e}")
                print("Continuing with basic knowledge base only...\n")

    # Initialize query engine
    try:
        engine = AdvancedQueryEngine(args.knowledge, repo_context)
    except FileNotFoundError:
        print(f"❌ Knowledge file not found: {args.knowledge}")
        return

    # Handle structure analysis
    if args.analyze_structure:
        result = engine.analyze_repository_structure()
        print(result)
        return

    # Process question
    question = " ".join(args.question)
    use_enhanced = not args.basic

    print(f"❓ Question: {question}")
    print("=" * 60)

    try:
        answer_text, label, search_results = engine.answer_question(
            question, use_enhanced
        )

        print(answer_text)

        # Show additional search results if available
        if search_results and len(search_results) > 1:
            print("\n\n📎 Additional Context:")
            print("─" * 50)
            for i, result in enumerate(search_results[1 : args.search_results], 1):
                source_icon = "📋" if result["source"] == "json-ld" else "📁"
                confidence = result.get("confidence", 0)
                print(
                    f"{i}. {source_icon} [{result['label']}] (confidence: {confidence:.2f})"
                )
                preview = result["text"][:150].replace("\n", " ")
                print(f"   {preview}{'...' if len(result['text']) > 150 else ''}\n")

    except Exception as e:
        print(f"❌ Error processing question: {e}")
        # Fallback to basic query
        try:
            bucket = pick_bucket(question)
            basic_answer = answer(load_knowledge(args.knowledge), bucket)
            print("🔄 Fallback Answer:")
            print("─" * 50)
            print(basic_answer)
        except Exception as e2:
            print(f"❌ Unable to process question: {e2}")


def get_repository_summary() -> Optional[Dict[str, Any]]:
    """
    Get repository summary using GitIngest from live GitHub repository.
    Falls back to local TXT file if GitIngest is not available.
    """
    # First try live GitIngest from the actual repository
    if GITINGEST_AVAILABLE:
        try:
            print("Fetching live repository content from GitHub...")
            summary, tree, content = ingest(
                "https://github.com/frequenz-floss/frequenz-sdk-python"
            )

            # Create repository context from live data
            repo_context = RepositoryContext(
                summary=summary or "Live GitIngest analysis of frequenz-sdk-python",
                content=content,
                structure=tree.split("\n") if tree else [],
                key_files=[],
                dependencies=[],
                last_updated=datetime.now(),
            )

            return {
                "content": content[:15000] if content else "",  # Limit for performance
                "summary": summary or "Live repository analysis",
                "structure": tree or "",
                "status": "loaded_from_live_github",
                "size": len(content) if content else 0,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Live GitIngest failed: {e}")

    # Fallback to local TXT file
    try:
        repo_context = RepositoryContext.from_gitingest_file()
        if repo_context:
            return {
                "content": repo_context.content[:15000],  # Limit for performance
                "summary": repo_context.summary,
                "structure": "\n".join(repo_context.structure[:50]),
                "status": "loaded_from_fallback_file",
                "size": len(repo_context.content),
            }
    except Exception as e:
        print(f"Fallback file loading failed: {e}")

    return None


def get_relevant_repository_context(question: str) -> str:
    """
    Get relevant repository context for a specific question using semantic search.
    Uses live GitIngest data or falls back to local file.
    """
    # Try live GitIngest first
    if GITINGEST_AVAILABLE:
        try:
            summary, tree, content = ingest(
                "https://github.com/frequenz-floss/frequenz-sdk-python"
            )
            if content:
                return _extract_relevant_context(content, question)
        except Exception as e:
            print(f"Live GitIngest context extraction failed: {e}")

    # Fallback to local file
    try:
        gitingest_path = "data/frequenz-floss-frequenz-sdk-python-LLM.txt"
        if Path(gitingest_path).exists():
            with open(gitingest_path, "r", encoding="utf-8") as f:
                content = f.read()
            return _extract_relevant_context(content, question)
    except Exception as e:
        print(f"Fallback context extraction failed: {e}")

    return ""


def _extract_relevant_context(
    content: str, question: str, max_chars: int = 6000
) -> str:
    """Extract relevant context from repository content based on question."""
    if not content:
        return ""

    lines = content.split("\n")
    question_lower = question.lower()

    # Build repository structure overview (always include)
    context_parts = ["=== FREQUENZ SDK REPOSITORY OVERVIEW ==="]
    structure_lines = []
    for line in lines[:50]:
        if line.strip() and not line.startswith("====="):
            structure_lines.append(line)
        if len("\n".join(structure_lines)) > 800:  # Limit structure size
            break
    context_parts.extend(structure_lines)

    # Define search patterns for different question types
    search_patterns = {
        "install": [
            "installation",
            "setup",
            "pip install",
            "requirements",
            "pyproject.toml",
            "getting started",
        ],
        "example": ["example", "tutorial", "sample", "demo", "usage", "how to"],
        "actor": ["actor", "microgrid", "power", "battery", "energy"],
        "config": ["config", "configuration", "settings", "parameters"],
        "async": ["async", "await", "asyncio", "coroutine", "concurrency"],
        "api": ["class", "def ", "function", "method", "interface"],
        "error": ["error", "exception", "troubleshoot", "debug", "fix"],
    }

    # Find the most relevant search pattern
    best_pattern = None
    for pattern_name, keywords in search_patterns.items():
        if any(keyword in question_lower for keyword in keywords):
            best_pattern = pattern_name
            break

    # Extract relevant content sections
    if best_pattern:
        context_parts.append(f"\n=== RELEVANT {best_pattern.upper()} CONTENT ===")
        relevant_lines = []

        for i, line in enumerate(lines):
            if any(
                keyword in line.lower() for keyword in search_patterns[best_pattern]
            ):
                # Get context around the match (5 lines before, 10 after)
                start_idx = max(0, i - 5)
                end_idx = min(len(lines), i + 10)
                context_block = lines[start_idx:end_idx]
                relevant_lines.extend(context_block)

                # Stop if we have enough content
                if len("\n".join(relevant_lines)) > 3000:
                    break

        # Add the relevant content
        context_parts.extend(relevant_lines[:100])  # Limit lines

    # Join and ensure we don't exceed max_chars
    result = "\n".join(context_parts)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... [content truncated to fit API limits]"

    return result


if __name__ == "__main__":
    main()
