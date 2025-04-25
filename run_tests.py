import unittest
import sys
import os
import argparse


def run_tests(verbosity=1, test_pattern=None):
    """Run the test suite with optional pattern matching"""
    # Always use the directory of this script as the base
    base_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, base_dir)
    tests_dir = os.path.join(base_dir, "tests")

    # Discover and run tests
    loader = unittest.defaultTestLoader
    if test_pattern:
        # Assume pattern is for test discovery (e.g., "test_module.TestClass.test_method")
        # or a file pattern (e.g., "test_unit*").
        # For simplicity, let's support module/class/method pattern first.
        # Direct loading by name is often simpler if the pattern is specific.
        try:
            suite = loader.loadTestsFromName(test_pattern)
        except (ImportError, AttributeError):
            # If loadTestsFromName fails, try discovery with a pattern
            # This matches filenames like test_*.py
            print(f"Pattern '{test_pattern}' not found as name, trying discovery pattern...")
            suite = loader.discover(tests_dir, pattern=test_pattern if test_pattern.endswith(".py") else f"*{test_pattern}*.py")
    else:
        suite = loader.discover(tests_dir, pattern="test_*.py") # Ensure it looks for test_*.py

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LaTeX-to-LLM test suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-p", "--pattern", help="Only run tests matching this pattern (e.g., test_unit.TestLaTeXToLLM, test_integration, test_cli.py)")
    args = parser.parse_args()

    verbosity = 2 if args.verbose else 1
    sys.exit(run_tests(verbosity=verbosity, test_pattern=args.pattern))