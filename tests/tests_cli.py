#!/usr/bin/env python3
"""
Command-line interface tests for latex_to_llm.py (Simplified Version)
Focuses on project_basic and project_advanced fixtures.
Excludes project_edgecases tests for now.
"""

import os
import sys
import unittest
import tempfile
import shutil
import subprocess
import json

# Add parent directory to path to import latex_to_llm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import latex_to_llm # For optional yaml check

# Define fixture directory relative to this test file
FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures'))

# Define a robust tearDown method once (copied from test_unit.py)
def robust_tearDown(instance):
    """Shared robust tearDown logic."""
    os.chdir(instance.old_cwd) # Go back first
    max_retries = 3
    delay = 1 # Longer delay for CLI tests if needed
    for i in range(max_retries):
        try:
            if os.path.exists(instance.temp_dir): # Check if it exists before trying
                shutil.rmtree(instance.temp_dir)
                break # Success
        except OSError as e:
            print(f"Warning: Attempt {i+1}/{max_retries} failed to remove temp dir {instance.temp_dir}: {e}", file=sys.stderr)
            if i < max_retries - 1:
                import time
                time.sleep(delay)
            else:
                print(f"Error: Failed to remove temp dir {instance.temp_dir} after {max_retries} attempts.", file=sys.stderr)

class TestCLISimplified(unittest.TestCase):
    """Test the command-line interface (Simplified)"""

    def setUp(self):
        """Create temporary directory and copy fixtures"""
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_cli_simp_")
        self.old_cwd = os.getcwd()
        shutil.copytree(FIXTURES_DIR, os.path.join(self.temp_dir, 'fixtures'), dirs_exist_ok=True)
        self.script_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'latex_to_llm.py'
        ))

    def tearDown(self):
        robust_tearDown(self)

    def run_script(self, args_list, cwd, stdin_input=None):
        """Helper to run the script via subprocess from a specific CWD"""
        base_command = [sys.executable, self.script_path]
        full_command = base_command + args_list
        result = subprocess.run(
            full_command, input=stdin_input, capture_output=True,
            text=True, encoding='utf-8', cwd=cwd
        )
        # Only assert returncode 0 if not a dry run
        if "--dry-run" not in args_list:
             self.assertEqual(result.returncode, 0, f"Script failed (exit code {result.returncode}) in {cwd}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    # --- Tests using project_basic ---

    def test_cli_basic_prompt_default(self):
        """Test CLI prompt defaults to first file in project_basic"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        # project_basic only has main.tex, so prompt won't appear
        result = self.run_script([], cwd=project_path)
        self.assertIn("Auto-selected entry point: main.tex", result.stdout)
        self.assertTrue(os.path.exists(os.path.join(project_path, "export/full-project.txt")))

    def test_cli_basic_output_dir(self):
        """Test --output option specifies custom directory"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        custom_output = "my_exports"
        result = self.run_script(["-e","main.tex", "-o", custom_output], cwd=project_path)
        self.assertTrue(os.path.exists(os.path.join(project_path, custom_output, "full-project.txt")))
        self.assertFalse(os.path.exists(os.path.join(project_path, "export")))


    # --- Tests using project_advanced (Simplified Expectations) ---

    def test_cli_advanced_entry_option(self):
        """Test --entry option with project_advanced"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        result = self.run_script(["--entry", "report.tex"], cwd=project_path)
        output_file = os.path.join(project_path, "export", "full-project.txt")
        self.assertTrue(os.path.exists(output_file))
        with open(output_file, "r") as f: content = f.read()
        self.assertIn("=== File: report.tex ===", content)
        self.assertIn("=== File: chapters/chap1.tex ===", content)
        self.assertNotIn("_drafts/ideas.tex", content) # Ignored by default ignore file
        self.assertNotIn("flow.tikz", content) # Not visited

    def test_cli_advanced_dry_run(self):
        """Test --dry-run with project_advanced"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        result = self.run_script(["--entry", "report.tex", "--dry-run"], cwd=project_path)
        self.assertEqual(result.returncode, 0) # Dry run should exit 0
        self.assertIn("--- Dry Run ---", result.stdout)
        self.assertIn("- report.tex", result.stdout)
        self.assertIn("- chapters/chap1.tex", result.stdout)
        # flow.tikz will NOT be listed in 'Files to be exported' as it's not found/visited
        self.assertNotIn("flow.tikz", result.stdout)
        self.assertIn("- biblio/main_refs.bib", result.stdout)
        self.assertIn("- figures/plot.pdf", result.stdout)
        self.assertFalse(os.path.exists(os.path.join(project_path, "export")))

    def test_cli_advanced_excludes(self):
        """Test CLI excludes with project_advanced"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        # Exclude chapters folder and the bib file
        result = self.run_script([
            "-e", "report.tex",
            "-x", "chapters/", # Exclude folder
            "-f", "*.bib"      # Exclude file type
            ], cwd=project_path)

        output_file = os.path.join(project_path, "export", "full-project.txt")
        self.assertTrue(os.path.exists(output_file))
        with open(output_file, "r") as f: content = f.read()
        # Only report.tex and appendix/appA.tex should remain
        self.assertIn("=== File: report.tex ===", content)
        self.assertIn("=== File: appendix/appA.tex ===", content)
        self.assertNotIn("chapters/chap1.tex", content)
        self.assertNotIn("chapters/chap2.tex", content)
        self.assertNotIn("chapters_sections", content) # Make sure subdir is gone too

        # Bib file should also be gone (or empty)
        bib_file = os.path.join(project_path, "export", "bibliography.txt")
        self.assertFalse(os.path.exists(bib_file) and os.path.getsize(bib_file) > 0)


    # --- Tests using project_edgecases (Skipped) ---

    # @unittest.skip("Skipping edge case tests in simplified version")
    # def test_cli_edgecases_excludes_and_ignore(self): ...


if __name__ == "__main__":
    unittest.main(verbosity=2)