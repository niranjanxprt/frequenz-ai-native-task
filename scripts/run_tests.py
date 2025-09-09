#!/usr/bin/env python3
"""
Production-quality test runner for the AI-Native knowledge graph project.
Runs comprehensive quality checks including linting, testing, and compliance validation.
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"✅ {description}: PASSED")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description}: FAILED")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run hiring task compliance and quality checks"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slower quality checks, run only compliance",
    )
    parser.add_argument(
        "--skip-compliance",
        action="store_true",
        help="Skip hiring task compliance tests",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("🚀 HIRING TASK QUALITY ASSURANCE")
    print("=" * 50)

    # Change to project root
    project_root = Path(__file__).parent.parent
    print(f"📁 Project root: {project_root.absolute()}")

    results = []

    # 1. Code Quality with Ruff (always run unless --fast)
    if not args.fast:
        print("\n📋 CODE QUALITY & FORMATTING")
        print("-" * 30)

        # Ruff linting (entire repo)
        results.append(run_command(["ruff", "check", "."], "Code linting"))

        # Ruff formatting check
        results.append(
            run_command(["ruff", "format", "--check", "."], "Code formatting")
        )

    # 2. Hiring Task Compliance Tests (combined)
    if not args.skip_compliance:
        print("\n🎯 HIRING TASK COMPLIANCE (combined)")
        print("-" * 30)
        results.append(
            run_command(["python", "tests/test_compliance.py"], "Compliance tests")
        )

    # 3. Basic Syntax Checks moved into compliance test

    # 5. Final Summary
    print(f"\n{'=' * 50}")
    print("🏆 FINAL QUALITY REPORT")
    print(f"{'=' * 50}")

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("🎉 Code is production-ready!")
        sys.exit(0)
    else:
        print(f"⚠️  SOME CHECKS FAILED ({passed}/{total})")
        print("🔧 Please fix the issues above before deployment.")
        sys.exit(1)


if __name__ == "__main__":
    main()
