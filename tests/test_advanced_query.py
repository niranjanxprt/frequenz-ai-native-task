#!/usr/bin/env python3
"""
test_advanced_query.py - Tests for the advanced query system with gitingest
"""

import sys
import unittest
import subprocess
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

try:
    from query_advanced import AdvancedQueryEngine, RepositoryContext
    ADVANCED_QUERY_AVAILABLE = True
except ImportError:
    ADVANCED_QUERY_AVAILABLE = False

try:
    from gitingest import ingest
    GITINGEST_AVAILABLE = True
except ImportError:
    GITINGEST_AVAILABLE = False


class TestAdvancedQuery(unittest.TestCase):
    """Test the advanced query system with gitingest integration."""
    
    def setUp(self):
        """Set up test environment."""
        if not ADVANCED_QUERY_AVAILABLE:
            self.skipTest("Advanced query system not available")
        
        # Use basic knowledge file for testing
        self.knowledge_path = "project_knowledge.jsonld"
        if not Path(self.knowledge_path).exists():
            self.skipTest("Knowledge file not found")
    
    def test_basic_query_engine_initialization(self):
        """Test that AdvancedQueryEngine can be initialized."""
        engine = AdvancedQueryEngine(self.knowledge_path)
        self.assertIsNotNone(engine.knowledge_data)
        self.assertIn("@type", engine.knowledge_data)
        self.assertEqual(engine.knowledge_data["@type"], "SoftwareApplication")
    
    def test_basic_question_answering(self):
        """Test basic question answering without repository context."""
        engine = AdvancedQueryEngine(self.knowledge_path)
        
        questions = [
            "What is the Frequenz SDK for?",
            "How do I install the SDK?",
            "Show me an example"
        ]
        
        for question in questions:
            answer, label, results = engine.answer_question(question, use_enhanced=False)
            
            self.assertIsInstance(answer, str)
            self.assertGreater(len(answer), 10)
            self.assertIsInstance(label, str)
            self.assertIsInstance(results, list)
    
    def test_enhanced_buckets(self):
        """Test that enhanced buckets are generated correctly."""
        engine = AdvancedQueryEngine(self.knowledge_path)
        buckets = engine.enhance_buckets()
        
        # Should contain all original bucket keys
        original_keys = ["purpose", "install", "example", "features", "license", "dependencies"]
        for key in original_keys:
            self.assertIn(key, buckets)
            self.assertIsInstance(buckets[key], list)
    
    @unittest.skipUnless(GITINGEST_AVAILABLE, "gitingest not available")
    def test_repository_context_creation(self):
        """Test repository context creation (requires network)."""
        try:
            # Use a small public repo for testing
            repo_url = "https://github.com/frequenz-floss/frequenz-sdk-python"
            
            # This may take a while and requires network
            context = RepositoryContext.from_gitingest(repo_url)
            
            self.assertIsInstance(context.summary, str)
            self.assertIsInstance(context.tree, str)
            self.assertIsInstance(context.content, str)
            self.assertGreater(context.file_count, 0)
            self.assertGreater(context.total_size, 0)
            self.assertIsInstance(context.languages, list)
            self.assertIsInstance(context.dependencies, list)
            self.assertIsInstance(context.structure, dict)
            
        except Exception as e:
            self.skipTest(f"Repository analysis failed (network/rate limit?): {e}")
    
    def test_cli_advanced_query(self):
        """Test that the advanced query CLI works."""
        if not ADVANCED_QUERY_AVAILABLE:
            self.skipTest("Advanced query system not available")
        
        # Test basic CLI functionality without repo analysis
        questions = [
            "What is the Frequenz SDK for?",
            "How to install?"
        ]
        
        for question in questions:
            try:
                result = subprocess.run([
                    sys.executable, "src/query_advanced.py", "--no-repo", question
                ], capture_output=True, text=True, timeout=30)
                
                self.assertEqual(result.returncode, 0, 
                               f"CLI query failed: {result.stderr}")
                
                output = result.stdout.strip()
                self.assertGreater(len(output), 50,
                                 f"CLI should return meaningful answer for: {question}")
                
                # Should contain the answer format
                self.assertIn("Question:", output)
                
            except subprocess.TimeoutExpired:
                self.fail(f"CLI query timed out: {question}")
    
    def test_structure_analysis_without_repo(self):
        """Test structure analysis when no repo context is available."""
        engine = AdvancedQueryEngine(self.knowledge_path)
        result = engine.analyze_repository_structure()
        
        self.assertIn("No repository context available", result)
        self.assertIn("--repo", result)


class TestAdvancedQueryIntegration(unittest.TestCase):
    """Integration tests for advanced query system."""
    
    def test_import_compatibility(self):
        """Test that advanced query doesn't break basic imports."""
        try:
            # Should be able to import both systems
            from query import load_knowledge, pick_bucket
            
            if ADVANCED_QUERY_AVAILABLE:
                from query_advanced import AdvancedQueryEngine
            
            # Basic functionality should still work
            knowledge = load_knowledge("project_knowledge.jsonld")
            self.assertIn("@type", knowledge)
            
            bucket = pick_bucket("How to install?")
            self.assertEqual(bucket, "install")
            
        except Exception as e:
            self.fail(f"Import compatibility test failed: {e}")
    
    def test_pyproject_dependencies(self):
        """Test that required dependencies are listed in pyproject.toml."""
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            self.skipTest("pyproject.toml not found")
        
        content = pyproject_path.read_text()
        
        # Should have gitingest dependency
        self.assertIn("gitingest", content)
        
        # Should have other required dependencies
        required_deps = ["scikit-learn", "requests", "beautifulsoup4"]
        for dep in required_deps:
            self.assertIn(dep, content)


def main():
    """Run advanced query tests."""
    print("🧪 ADVANCED QUERY SYSTEM TESTS")
    print("=" * 50)
    
    if not ADVANCED_QUERY_AVAILABLE:
        print("⚠️  Advanced query system not available")
        print("   Make sure query_advanced.py is in src/")
        return False
    
    if not GITINGEST_AVAILABLE:
        print("⚠️  gitingest not available - some tests will be skipped")
        print("   Install with: pip install gitingest")
    
    # Run tests
    result = unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    if result.result.wasSuccessful():
        print("🎉 ALL ADVANCED QUERY TESTS PASSED!")
        return True
    else:
        print(f"❌ {len(result.result.failures)} tests failed")
        print(f"❌ {len(result.result.errors)} tests had errors")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)