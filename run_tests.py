import unittest
import sys
import os
import argparse
import tempfile
import shutil
import gc
import time
import contextlib

# Check if running on Windows
_ON_WINDOWS = os.name == 'nt'


@contextlib.contextmanager
def temp_directory_context(prefix="latex_llm_test_"):
    """Context manager for temporary directories with better Windows cleanup."""
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    try:
        # Store original temp directory
        original_temp = os.environ.get('TMPDIR')
        
        # Set temp directory for tests
        os.environ['TMPDIR'] = temp_dir
        
        # Yield control back to the with block
        yield temp_dir
    finally:
        # Restore original temp directory
        if original_temp:
            os.environ['TMPDIR'] = original_temp
        else:
            os.environ.pop('TMPDIR', None)
            
        # Force garbage collection to release file handles
        gc.collect()
        
        # On Windows, wait a bit for file handles to be released
        if _ON_WINDOWS:
            time.sleep(0.5)
            
        # Try to remove the temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            # On Windows, this is not a critical failure
            if not _ON_WINDOWS:
                print(f"Warning: Could not remove temporary directory {temp_dir}", file=sys.stderr)


def run_tests(verbosity=1, test_pattern=None):
    """Run the test suite with optional pattern matching and better Windows file handling"""
    # Always use the directory of this script as the base
    base_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, base_dir)
    tests_dir = os.path.join(base_dir, "tests")
    
    # Print informational message for Windows users
    if _ON_WINDOWS:
        print("\nNote: On Windows, some directory cleanup warnings may appear - this is expected behavior\n")

    # Use a custom temp directory for the test run
    with temp_directory_context() as tmp_dir:
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
        
        # Force cleanup
        gc.collect()
        
        # Extra cleanup for Windows
        if _ON_WINDOWS:
            time.sleep(0.5)
            
        return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LaTeX-to-LLM test suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-p", "--pattern", help="Only run tests matching this pattern (e.g., test_unit.TestLaTeXToLLM, test_integration, test_cli.py)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress directory cleanup warnings")
    args = parser.parse_args()

    verbosity = 2 if args.verbose else 1
    
    # If quiet mode is requested, suppress stderr temporarily
    if args.quiet and _ON_WINDOWS:
        original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        
    try:
        exit_code = run_tests(verbosity=verbosity, test_pattern=args.pattern)
    finally:
        # Restore stderr if it was redirected
        if args.quiet and _ON_WINDOWS:
            sys.stderr.close()
            sys.stderr = original_stderr
            
    sys.exit(exit_code)