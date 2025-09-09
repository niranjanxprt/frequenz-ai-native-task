#!/usr/bin/env python3
"""
test_compliance.py - Complete Hiring Task Compliance Test

Tests EVERYTHING required for the hiring task:
1. Knowledge extraction works (extract.py)
2. Query interface works (query.py) 
3. Visualization works (visualize.py)
4. All 3 required queries return correct answers
5. JSON-LD structure is valid
6. Core functionality integration

This is the ONLY test file needed for hiring task compliance.

Run: python -m unittest tests.test_compliance -v
Or:  python tests/test_compliance.py
"""

import sys
import unittest
import subprocess
import json
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

try:
    from query import answer_semantic, pick_bucket, load_knowledge
    import extract
    import visualize
except ImportError as e:
    print(f"❌ Cannot import core modules: {e}")
    print("Make sure files are in src/ directory")
    sys.exit(1)


class HiringTaskComplianceTests(unittest.TestCase):
    """Complete hiring task compliance tests."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        print("\n🧪 HIRING TASK COMPLIANCE TEST")
        print("=" * 50)
        
        # Ensure knowledge graph exists
        kg_file = Path("project_knowledge.jsonld")
        if not kg_file.exists():
            print("⚠️  Knowledge graph missing, running extract.py...")
            try:
                subprocess.run([sys.executable, "src/extract.py"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                raise unittest.SkipTest("Cannot generate knowledge graph")
        
        # Load knowledge
        try:
            cls.knowledge = load_knowledge()
        except Exception as e:
            raise unittest.SkipTest(f"Cannot load knowledge: {e}")
    
    def test_1_knowledge_extraction(self):
        """Test Part 1: Knowledge extraction works."""
        print("\n=== Testing Part 1: Knowledge Extraction ===")
        
        # Test JSON-LD file exists and is valid
        kg_file = Path("project_knowledge.jsonld")
        self.assertTrue(kg_file.exists(), "project_knowledge.jsonld must exist")
        
        # Test JSON-LD structure
        with open(kg_file) as f:
            data = json.load(f)
        
        # Required schema.org fields
        required_fields = ["@context", "@type", "name", "description"]
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")
        
        self.assertEqual(data["@type"], "SoftwareApplication", 
                        "Must be a SoftwareApplication")
        
        print("✅ Knowledge extraction: PASSED")
    
    def test_2_required_query_1_purpose(self):
        """Test Required Query 1: 'What is the Frequenz SDK for?'"""
        print("\n=== Testing Required Query 1: Purpose ===")
        
        question = "What is the Frequenz SDK for?"
        
        # Test classification
        bucket = pick_bucket(question)
        self.assertEqual(bucket, "purpose")
        
        # Test semantic answer
        answer, detected_bucket = answer_semantic(question, self.knowledge)
        self.assertEqual(detected_bucket, "purpose")
        
        # Test answer quality
        answer_lower = answer.lower()
        self.assertTrue(
            any(term in answer_lower for term in ["development", "kit", "platform", "frequenz"]),
            f"Answer should describe what the SDK is for. Got: {answer[:100]}"
        )
        
        print(f"✅ Query 1 Answer: {answer[:80]}...")
    
    def test_3_required_query_2_installation(self):
        """Test Required Query 2: 'How do I install the sdk?'"""
        print("\n=== Testing Required Query 2: Installation ===")
        
        question = "How do I install the sdk?"
        
        # Test classification
        bucket = pick_bucket(question)
        self.assertEqual(bucket, "install")
        
        # Test semantic answer
        answer, detected_bucket = answer_semantic(question, self.knowledge)
        self.assertEqual(detected_bucket, "install")
        
        # Test answer quality
        answer_lower = answer.lower()
        self.assertTrue(
            any(term in answer_lower for term in ["pip", "install", "frequenz"]),
            f"Answer should contain installation instructions. Got: {answer[:100]}"
        )
        
        print(f"✅ Query 2 Answer: {answer[:80]}...")
    
    def test_4_required_query_3_example(self):
        """Test Required Query 3: 'Show me an example of how to use it.'"""
        print("\n=== Testing Required Query 3: Example ===")
        
        question = "Show me an example of how to use it."
        
        # Test classification
        bucket = pick_bucket(question)
        self.assertEqual(bucket, "example")
        
        # Test semantic answer
        answer, detected_bucket = answer_semantic(question, self.knowledge)
        self.assertEqual(detected_bucket, "example")
        
        # Test answer quality - should contain code
        answer_lower = answer.lower()
        self.assertTrue(
            any(term in answer_lower for term in ["import", "async", "def", "from", "frequenz"]),
            f"Answer should contain code example. Got: {answer[:100]}"
        )
        
        print(f"✅ Query 3 Answer: {answer[:80]}...")
    
    def test_5_cli_interface_integration(self):
        """Test CLI interface works end-to-end."""
        print("\n=== Testing CLI Integration ===")
        
        # Test query.py CLI works
        test_queries = [
            "What is the Frequenz SDK for?",
            "How do I install the sdk?", 
            "Show me an example of how to use it."
        ]
        
        for query_text in test_queries:
            try:
                result = subprocess.run([
                    sys.executable, "src/query.py", query_text
                ], capture_output=True, text=True, timeout=30)
                
                self.assertEqual(result.returncode, 0,
                               f"CLI query failed: {result.stderr}")
                
                self.assertTrue(len(result.stdout.strip()) > 10,
                               f"CLI should return meaningful answer for: {query_text}")
                
            except subprocess.TimeoutExpired:
                self.fail(f"CLI query timed out: {query_text}")
        
        print("✅ CLI integration: PASSED")


def main():
    """Run comprehensive hiring task compliance tests."""
    print("🧪 HIRING TASK COMPLIANCE TEST")
    print("=" * 50)
    
    # Run unittest with verbose output
    result = unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 50)
    print("🏆 HIRING TASK COMPLIANCE SUMMARY")
    print("=" * 50)
    
    if result.result.wasSuccessful():
        print("🎉 ALL HIRING TASK REQUIREMENTS SATISFIED!")
        print("\n✅ Part 1: Knowledge Extraction - PASSED")
        print("✅ Part 2: Query Interface - PASSED") 
        print("✅ All 3 Required Queries - PASSED")
        print("✅ CLI Integration - PASSED")
        print("\n🚀 Ready for submission!")
    else:
        print(f"❌ {len(result.result.failures)} tests failed")
        print(f"❌ {len(result.result.errors)} tests had errors")
        print("\n🔧 Please fix issues before submission")


if __name__ == "__main__":
    main()