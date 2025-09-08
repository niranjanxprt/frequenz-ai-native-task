#!/usr/bin/env python3
"""
semantic_query.py
------------------
Enhanced Semantic Query Engine for the Frequenz SDK knowledge base.

This module implements semantic search over the JSON‑LD knowledge using
either sentence-transformers (if available) or a TF‑IDF cosine fallback.

It can be used from the terminal:
  python semantic_query.py "How do I install the sdk?"
  python semantic_query.py --interactive
or imported by the Streamlit app as an advanced semantic tab.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import argparse

# Optional dependency for semantic search
try:  # optional heavy dependency
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    _HAS_ST = True
except Exception:
    _HAS_ST = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as _cos
    _HAS_SK = True
except Exception:
    _HAS_SK = False


class SemanticQueryEngine:
    """Self-contained semantic query engine with optional embeddings.

    Falls back to TF‑IDF if sentence-transformers is not installed.
    """

    def __init__(self, knowledge_file: str = "project_knowledge.jsonld"):
        self.knowledge_file = knowledge_file
        self.knowledge_base = json.loads(Path(knowledge_file).read_text(encoding="utf-8"))

        self.semantic_model = None
        self.knowledge_chunks: List[Dict[str, Any]] = []
        self.chunk_embeddings = None
        self._tfidf_vec = None
        self._tfidf_mat = None

        # Build chunks always
        self._create_knowledge_chunks()
        # Prefer embeddings, else TFIDF fallback
        if _HAS_ST:
            self._initialize_semantic_search()
        elif _HAS_SK:
            self._initialize_tfidf()
        else:
            print("⚠️  Neither sentence-transformers nor scikit-learn available.\n"
                  "    Install one of them for semantic search.")
    
    def _initialize_semantic_search(self):
        """Initialize the semantic search model and create embeddings."""
        print("🔄 Initializing semantic search model...")
        
        try:
            self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            if self.knowledge_chunks:
                texts = [c['text'] for c in self.knowledge_chunks]
                self.chunk_embeddings = self.semantic_model.encode(texts)
                print(f"✅ Semantic search initialized ({len(texts)} chunks)")
        except Exception as e:
            print(f"❌ Failed to initialize sentence-transformers: {e}")
            self.semantic_model = None

    def _initialize_tfidf(self):
        if not _HAS_SK:
            return
        texts = [c['text'] for c in self.knowledge_chunks]
        self._tfidf_vec = TfidfVectorizer(stop_words="english")
        self._tfidf_mat = self._tfidf_vec.fit_transform(texts)
        print(f"✅ TF‑IDF fallback initialized ({len(texts)} chunks)")
    
    def _create_knowledge_chunks(self):
        """Create searchable text chunks from the knowledge base."""
        chunks = []
        
        # Add basic project information
        if self.knowledge_base.get('description'):
            chunks.append({
                'text': f"{self.knowledge_base['name']}: {self.knowledge_base['description']}",
                'type': 'description',
                'data': {
                    'name': self.knowledge_base.get('name'),
                    'description': self.knowledge_base.get('description'),
                    'targetProduct': self.knowledge_base.get('targetProduct')
                }
            })
        
        # Add installation instructions (schema.org HowTo)
        install = self.knowledge_base.get('installInstructions') or {}
        steps = install.get('step') or []
        if steps:
            text = "Installation: " + " ".join(s.get('text', '') for s in steps)
            chunks.append({'text': text, 'type': 'installation', 'data': install})
        
        # Add code examples
        examples = self.knowledge_base.get('exampleOfWork', [])
        for ex in examples:
            text = ex.get('text', '') or ''
            name = ex.get('name', 'Example')
            example_text = f"{name}: {text}"
            chunks.append({'text': example_text, 'type': 'example', 'data': ex})
        
        # Add features
        features = self.knowledge_base.get('featureList', [])
        if isinstance(features, list):
            for f in features:
                chunks.append({'text': str(f), 'type': 'feature', 'data': {'text': f}})
        
        # Add dependencies
        deps = self.knowledge_base.get('softwareRequirements', [])
        if deps:
            if isinstance(deps, list):
                deps_text = "Dependencies: " + ", ".join(map(str, deps))
            else:
                deps_text = f"Dependencies: {deps}"
            chunks.append({'text': deps_text, 'type': 'dependencies', 'data': deps})
        
        # Add license information
        license_info = self.knowledge_base.get('license')
        if license_info:
            chunks.append({'text': f"License: {license_info}", 'type': 'license', 'data': {'license': license_info}})
        
        self.knowledge_chunks = chunks
    
    def semantic_search(self, query: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        """Perform semantic search to find the most relevant knowledge chunks."""
        # Prefer sentence-transformers
        if self.semantic_model is not None and self.chunk_embeddings is not None:
            qv = self.semantic_model.encode([query])
            sims = cosine_similarity(qv, self.chunk_embeddings)[0]
            order = np.argsort(sims)[::-1][:top_k]
            return [(self.knowledge_chunks[i], float(sims[i])) for i in order if sims[i] > 0.1]
        # Fallback to TF‑IDF if available
        if self._tfidf_vec is not None and self._tfidf_mat is not None:
            qv = self._tfidf_vec.transform([query])
            sims = _cos(qv, self._tfidf_mat).ravel()
            order = np.argsort(sims)[::-1][:top_k]
            return [(self.knowledge_chunks[i], float(sims[i])) for i in order if sims[i] > 0.0]
        return []
    
    def query_with_semantic_search(self, question: str) -> str:
        """Process a query using semantic search."""
        # Try semantic search; if no results, fall back to naive match
        # Perform semantic search
        search_results = self.semantic_search(question, top_k=3)
        
        if not search_results:
            return self._fallback(question)
        
        # Format the response based on the most relevant chunk
        best_chunk, similarity = search_results[0]
        chunk_type = best_chunk['type']
        chunk_data = best_chunk['data']
        
        response = f"**Semantic Search Result** (Similarity: {similarity:.2f})\n\n"
        
        if chunk_type == 'description':
            response += f"**{chunk_data.get('name', 'Frequenz Python SDK')}**\n\n"
            response += f"{chunk_data.get('description', '')}\n\n"
            target = chunk_data.get('targetProduct', {})
            if target:
                response += f"**Target Platform:** {target.get('name', '')} ({target.get('category', '')})\n"
        
        elif chunk_type == 'installation':
            response += self._format_installation_steps(chunk_data)
        
        elif chunk_type == 'example':
            response += f"**{chunk_data.get('name', 'Code Example')}**\n\n"
            if chunk_data.get('description'):
                response += f"{chunk_data['description']}\n\n"
            if chunk_data.get('text'):
                response += f"```python\n{chunk_data['text']}\n```\n"
        
        elif chunk_type == 'feature':
            response += f"**Feature: {chunk_data.get('name', 'Unknown')}**\n\n"
            response += f"{chunk_data.get('description', 'No description available')}\n"
        
        elif chunk_type == 'dependencies':
            response += self._format_dependencies(chunk_data)
        
        elif chunk_type == 'license':
            response += f"**License:** {chunk_data.get('name', 'Unknown')}\n"
            if chunk_data.get('url'):
                response += f"**URL:** {chunk_data['url']}\n"
        
        # Add additional relevant results if available
        if len(search_results) > 1:
            response += f"\n**Additional Relevant Information:**\n"
            for chunk, sim in search_results[1:]:
                if chunk['type'] != chunk_type:  # Avoid duplicating the same type
                    response += f"- {chunk['type'].title()}: {chunk['data'].get('name', chunk['data'].get('description', 'N/A')[:50])} (Similarity: {sim:.2f})\n"
        
        return response.strip()
    
    def _fallback(self, question: str) -> str:
        # Simple keyword routing similar to query.py buckets
        ql = question.lower()
        if any(k in ql for k in ["install", "pip"]):
            return "Installation information not found in knowledge base."
        if any(k in ql for k in ["example", "code", "snippet"]):
            for c in self.knowledge_chunks:
                if c['type'] == 'example':
                    return f"```python\n{c['text']}\n```"
        if any(k in ql for k in ["license", "mit", "apache"]):
            return next((c['text'] for c in self.knowledge_chunks if c['type'] == 'license'), "License info not found.")
        if any(k in ql for k in ["feature", "capability", "supports"]):
            feats = [c['text'] for c in self.knowledge_chunks if c['type'] == 'feature']
            return "\n".join(feats) if feats else "No features found."
        return "No relevant information found for your query."

    def query(self, question: str) -> str:
        return self.query_with_semantic_search(question)


def main():
    """Main function to run the enhanced semantic query engine."""
    parser = argparse.ArgumentParser(
        description="Query the Frequenz SDK knowledge base with semantic search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python semantic_query.py "What is this SDK used for?"
  python semantic_query.py "How to set it up?"
  python semantic_query.py "Give me a code sample"
  python semantic_query.py --interactive
        """
    )
    
    parser.add_argument(
        'question',
        nargs='?',
        help='Natural language question about the Frequenz SDK'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '-k', '--knowledge-file',
        default='project_knowledge.jsonld',
        help='Path to the knowledge base file'
    )
    
    args = parser.parse_args()
    
    # Initialize semantic query engine
    try:
        query_engine = SemanticQueryEngine(args.knowledge_file)
    except Exception as e:
        print(f"Error initializing semantic query engine: {e}")
        return 1
    
    # Handle interactive mode
    if args.interactive:
        print("Enhanced Semantic Query System for Frequenz SDK")
        print("=" * 50)
        if SEMANTIC_SEARCH_AVAILABLE:
            print("✅ Semantic search enabled (sentence-transformers)")
        else:
            print("⚠️  Semantic search disabled - using pattern matching fallback")
        print("Ask questions about the Frequenz SDK Python project.")
        print("Type 'quit' or 'exit' to end the session.\n")
        
        while True:
            try:
                question = input("Question: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                if not question:
                    continue
                
                print("\nAnswer:")
                print("-" * 20)
                answer = query_engine.query(question)
                print(answer)
                print("\n" + "=" * 50 + "\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except EOFError:
                print("\nGoodbye!")
                break
        return 0
    
    # Handle single question
    if args.question:
        answer = query_engine.query(args.question)
        print(answer)
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    exit(main())
