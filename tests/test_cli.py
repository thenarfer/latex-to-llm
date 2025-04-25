#!/usr/bin/env python3
"""
Command-line interface tests for latex_to_llm.py (Filtered Version)
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
import stat
import gc
import time

# Add parent directory to path to import latex_to_llm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import latex_to_llm  # For optional yaml check

# Check if running on Windows
_ON_WINDOWS = os.name == 'nt'

# Robust teardown helper
def _rmtree_onerror(func, path, exc_info):
    """
    Error handler for shutil.rmtree:
    If permission is denied, remove the read-only flag and retry.
    """
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass  # If it still fails, just continue

def robust_tearDown(instance):
    """Improved robust tearDown logic for Windows."""
    # Go back to original directory first
    os.chdir(instance.old_cwd)
    
    # Skip if temp_dir doesn't exist or is already removed
    if not hasattr(instance, 'temp_dir') or not os.path.exists(instance.temp_dir):
        return
    
    # Force Python garbage collection to release file handles
    gc.collect()
    
    # For Windows, try to close any open file handles
    if _ON_WINDOWS:
        # Try to set full permissions on all files before removal
        for root, dirs, files in os.walk(instance.temp_dir, topdown=False):
            for name in files:
                try:
                    path = os.path.join(root, name)
                    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass
        
        # Add short delay to allow Windows to release handles
        time.sleep(0.5)
    
    # Try to remove the directory
    try:
        shutil.rmtree(instance.temp_dir, onerror=_rmtree_onerror)
    except Exception:
        if _ON_WINDOWS:
            # On Windows, this is expected behavior sometimes - don't print warnings
            pass
        else:
            print(f"Note: Could not completely remove temp dir {instance.temp_dir}", file=sys.stderr)


class TestCLISimplified(unittest.TestCase):
    """Test the command-line interface (Filtered and Simplified)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_cli_simp_")
        self.old_cwd  = os.getcwd()
        # Copy fixtures
        shutil.copytree(
            os.path.join(os.path.dirname(__file__), 'fixtures'),
            os.path.join(self.temp_dir, 'fixtures'),
            dirs_exist_ok=True
        )
        # Path to script
        self.script_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'latex_to_llm.py'
        ))

    def tearDown(self):
        robust_tearDown(self)

    def run_script(self, args_list, cwd, stdin_input=None):
        base = [sys.executable, self.script_path] + args_list
        result = subprocess.run(
            base,
            input=stdin_input,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=cwd
        )
        if "--dry-run" not in args_list:
            self.assertEqual(
                result.returncode, 0,
                f"Script failed (exit {result.returncode}):\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        return result

    # --- Tests using project_basic ---

    def test_cli_basic_prompt_default(self):
        project = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        res = self.run_script([], cwd=project)
        self.assertIn("Auto-selected entry point: main.tex", res.stdout)
        self.assertTrue(
            os.path.exists(os.path.join(project, "export/full-project.txt"))
        )

    def test_cli_basic_output_dir(self):
        project = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        custom = "my_exports"
        self.run_script(["-e","main.tex","-o",custom], cwd=project)
        self.assertTrue(
            os.path.exists(os.path.join(project, custom, "full-project.txt"))
        )
        self.assertFalse(os.path.exists(os.path.join(project, "export")))

    # --- Tests using project_advanced ---

    def test_cli_advanced_entry_option(self):
        project = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        res = self.run_script(["--entry","report.tex"], cwd=project)
        out_file = os.path.join(project, "export", "full-project.txt")
        self.assertTrue(os.path.exists(out_file))
        with open(out_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # All included chapters should appear
        self.assertIn("=== File: report.tex ===", content)
        self.assertIn("=== File: chapters/chap1.tex ===", content)
        self.assertIn("=== File: chapters/chap2.tex ===", content)
        self.assertIn("=== File: appendix/appA.tex ===", content)
        # Comments are preserved
        self.assertIn("% \\input{_drafts/ideas.tex}", content)
        # The flow.tikz include remains inside chap2.tex
        self.assertIn("flow.tikz", content)

    def test_cli_advanced_dry_run(self):
        project = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        res = self.run_script(["--entry","report.tex","--dry-run"], cwd=project)
        self.assertEqual(res.returncode, 0)
        self.assertIn("--- Dry Run ---", res.stdout)
        # Dependencies tree should list both chapters and the tikz file
        self.assertIn("- report.tex", res.stdout)
        self.assertIn("- chapters/chap1.tex", res.stdout)
        self.assertIn("- chapters/chap2.tex", res.stdout)
        self.assertIn("flow.tikz", res.stdout)
        # Bibliography and images
        self.assertIn("- biblio/main_refs.bib", res.stdout)
        self.assertIn("- figures/plot.pdf", res.stdout)
        # No actual export directory created
        self.assertFalse(os.path.exists(os.path.join(project, "export")))

    def test_cli_advanced_excludes(self):
        project = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        res = self.run_script([
            "-e","report.tex",
            "-x","chapters/",
            "-f","*.bib"
        ], cwd=project)
        out = os.path.join(project, "export", "full-project.txt")
        self.assertTrue(os.path.exists(out))
        with open(out, 'r', encoding='utf-8') as f:
            content = f.read()
        # Only report and appendix remain
        self.assertIn("=== File: report.tex ===", content)
        self.assertIn("=== File: appendix/appA.tex ===", content)
        self.assertNotIn("chapters/chap1.tex", content)
        self.assertNotIn("chapters/chap2.tex", content)
        # Bibliography excluded
        bib = os.path.join(project, "export", "bibliography.txt")
        self.assertFalse(os.path.exists(bib) and os.path.getsize(bib) > 0)

if __name__ == '__main__':
    # Print a note about expected Windows behavior
    if _ON_WINDOWS:
        print("Note: On Windows, some directory cleanup warnings may appear - this is expected behavior")
    unittest.main(verbosity=2)