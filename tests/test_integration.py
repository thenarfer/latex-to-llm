#!/usr/bin/env python3
"""
Integration tests for latex_to_llm.py (Simplified Version)
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
import latex_to_llm # For optional yaml check

# Define fixture directory relative to this test file
FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures'))

# Check if running on Windows
_ON_WINDOWS = os.name == 'nt'

def _rmtree_onerror(func, path, exc_info):
    """
    Error handler for shutil.rmtree:
    If permission is denied, remove the read-only flag and retry.
    """
    try:
        # Make the file/directory writable and retry the operation
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


class TestIntegrationSimplified(unittest.TestCase):
    """Integration tests running the simplified script as a subprocess"""

    def setUp(self):
        """Create temporary directory and copy fixtures"""
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_integ_simp_")
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

    def test_basic_project_defaults(self):
        """Test basic project with default settings"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        result = self.run_script([], cwd=project_path, stdin_input="1\n") # Select main.tex

        self.assertTrue(os.path.exists(os.path.join(project_path, "export/full-project.txt")))
        self.assertTrue(os.path.exists(os.path.join(project_path, "export/bibliography.txt")))
        # Basic content checks
        output_file = os.path.join(project_path, "export", "full-project.txt")
        with open(output_file, "r") as f: content = f.read()
        self.assertIn("=== File: main.tex ===", content)
        self.assertIn("=== File: sections/intro.tex ===", content)
        bib_file = os.path.join(project_path, "export", "bibliography.txt")
        with open(bib_file, "r") as f: content = f.read()
        self.assertIn("=== Bib: references.bib ===", content)

    def test_basic_project_dry_run(self):
        """Test dry run on basic project"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        result = self.run_script(["--dry-run"], cwd=project_path, stdin_input="1\n")
        self.assertEqual(result.returncode, 0) # Dry run should exit 0
        self.assertIn("--- Dry Run ---", result.stdout)
        self.assertIn("- main.tex", result.stdout)
        self.assertIn("- sections/intro.tex", result.stdout)
        self.assertIn("- references.bib", result.stdout)
        self.assertIn("- figures/logo.png", result.stdout)
        self.assertFalse(os.path.exists(os.path.join(project_path, "export")))


    # --- Tests using project_advanced (Simplified Expectations) ---

    def test_advanced_project_entry_manifest(self):
        """Test advanced project using --entry and json manifest (simplified)"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        result = self.run_script(["--entry", "report.tex", "--manifest", "json"], cwd=project_path)

        manifest_file = os.path.join(project_path, "export", "manifest.json")
        self.assertTrue(os.path.exists(manifest_file))
        with open(manifest_file, "r") as f: manifest = json.load(f)

        expected_files = {
            "report.tex", "chapters/chap1.tex", "chapters/sections/chap1_intro.tex",
            "chapters/chap2.tex", "appendix/appA.tex"
        }
        self.assertEqual(set(manifest["files"]), expected_files)
        self.assertEqual(manifest["bibs"], ["biblio/main_refs.bib"])
        # <<< Corrected expected image path relative to including file >>>
        self.assertEqual(manifest["images"], ["chapters/plot.pdf"])


    def test_advanced_project_per_folder(self):
        """Test advanced project with --per-folder output (simplified)"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        result = self.run_script(["--entry", "report.tex", "--per-folder"], cwd=project_path)

        self.assertTrue(os.path.exists(os.path.join(project_path, "export/_.txt"))) # report.tex
        self.assertTrue(os.path.exists(os.path.join(project_path, "export/chapters.txt"))) # chap1, chap2
        self.assertTrue(os.path.exists(os.path.join(project_path, "export/chapters_sections.txt"))) # chap1_intro
        self.assertTrue(os.path.exists(os.path.join(project_path, "export/appendix.txt"))) # appA
        # flow.tikz is not visited, so its folder shouldn't be created
        self.assertFalse(os.path.exists(os.path.join(project_path, "export/figures_diagrams.txt")))
        self.assertTrue(os.path.exists(os.path.join(project_path, "export/bibliography.txt")))


    # --- General CLI Tests ---

    def test_cli_no_entry_found_error(self):
        """Test error when no .tex files exist and no --entry provided"""
        empty_project_path = os.path.join(self.temp_dir, "empty_project")
        os.makedirs(empty_project_path)
        base_command = [sys.executable, self.script_path]
        result = subprocess.run(
            base_command, capture_output=True, text=True, encoding='utf-8', cwd=empty_project_path
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error: No .tex files found", result.stderr)

    @unittest.skipIf(latex_to_llm.yaml is None, "PyYAML not installed")
    def test_cli_yaml_manifest(self):
        """Test creating a YAML manifest"""
        project_path = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        result = self.run_script(["-e", "main.tex", "--manifest", "yaml"], cwd=project_path)
        manifest_file = os.path.join(project_path, "export", "manifest.yaml")
        self.assertTrue(os.path.exists(manifest_file))
        # Basic check: can it be loaded?
        import yaml
        with open(manifest_file, "r") as f:
            try:
                data = yaml.safe_load(f)
                self.assertIn("files", data)
            except yaml.YAMLError as e:
                self.fail(f"Failed to load YAML manifest: {e}")


if __name__ == "__main__":
    # Print a note about expected Windows behavior
    if _ON_WINDOWS:
        print("Note: On Windows, some directory cleanup warnings may appear - this is expected behavior")
    unittest.main(verbosity=2)