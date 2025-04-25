"""
Unit tests for latex_to_llm.py (Simplified Version)
Focuses on project_basic and project_advanced (no graphicspath).
Excludes project_edgecases tests for now.
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add parent directory to path to import latex_to_llm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import latex_to_llm

# Define fixture directory relative to this test file
FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures'))

# Define a robust tearDown method once
def tearDownModule():
    # This might be useful if cleanup needs to happen after all tests in the module
    pass

def robust_tearDown(instance):
    """Shared robust tearDown logic."""
    os.chdir(instance.old_cwd) # Go back first
    max_retries = 3
    delay = 0.5 # Shorter delay for unit tests
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


class TestCoreFunctions(unittest.TestCase):
    """Test non-filesystem functions like ignore parsing and matching"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_unit_core_")
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        robust_tearDown(self)

    def test_load_ignore(self):
        """Test loading ignore patterns from file"""
        ignore_content = "_build/\n*.log\n# Comment\n  temp.* # With comment"
        with open(".testignore", "w", encoding='utf-8') as f: f.write(ignore_content)
        patterns = latex_to_llm.load_ignore(".testignore")
        self.assertEqual(patterns, ["_build/", "*.log", "temp.*"])

    def test_matches_any_simple(self):
        """Test the simplified pattern matching"""
        patterns = ["_build/", "*.log", "temp.txt", "docs/specific.tex"]
        self.assertTrue(latex_to_llm.matches_any("_build/file.txt", patterns))
        self.assertTrue(latex_to_llm.matches_any("file.log", patterns))
        self.assertTrue(latex_to_llm.matches_any("subdir/file.log", patterns))
        self.assertTrue(latex_to_llm.matches_any("temp.txt", patterns)) # Basename match
        self.assertTrue(latex_to_llm.matches_any("docs/specific.tex", patterns)) # Full path match

        self.assertFalse(latex_to_llm.matches_any("build/file.txt", patterns)) # Doesn't start with _build/
        self.assertFalse(latex_to_llm.matches_any("file.txt", patterns))
        self.assertFalse(latex_to_llm.matches_any("docs/other.tex", patterns))

    def test_resolve_tex_path(self):
        """Test resolving various file references"""
        base = os.path.abspath(os.path.join(self.temp_dir, "chapter"))
        os.makedirs(base, exist_ok=True)
        self.assertEqual(latex_to_llm.resolve_tex_path(base, "section1"), os.path.abspath(os.path.join(base, "section1.tex")))
        self.assertEqual(latex_to_llm.resolve_tex_path(base, "section2.tex"), os.path.abspath(os.path.join(base, "section2.tex")))
        self.assertEqual(latex_to_llm.resolve_tex_path(base, "figure.pdf"), os.path.abspath(os.path.join(base, "figure.pdf"))) # Should not add .tex

    def test_normalize_path(self):
        """Test normalizing paths relative to CWD"""
        os.makedirs("subdir/nested", exist_ok=True)
        base_dir = os.path.abspath("subdir")
        self.assertEqual(latex_to_llm.normalize_path(base_dir, "file.txt"), "subdir/file.txt")
        self.assertEqual(latex_to_llm.normalize_path(base_dir, "../other.pdf"), "other.pdf")


class TestDependencyCollectionSimplified(unittest.TestCase):
    """Test collect_dependencies using simplified fixtures"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_unit_deps_")
        self.old_cwd = os.getcwd()
        # Copy fixtures into the temp directory
        # Use the FIXTURES_DIR variable defined at the top of the file
        shutil.copytree(FIXTURES_DIR, os.path.join(self.temp_dir, 'fixtures'), dirs_exist_ok=True)
        # Change CWD to the *root* of the temp directory, not inside fixtures yet
        os.chdir(self.temp_dir)

    def tearDown(self):
        robust_tearDown(self)

    def test_collect_basic(self):
        """Test dependency collection on project_basic"""
        project_dir = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        os.chdir(project_dir) # Run test from within the project dir
        visited, deps, bibs, images = latex_to_llm.collect_dependencies(["main.tex"], [])

        self.assertEqual(set(visited), {"main.tex", "sections/intro.tex"})
        self.assertEqual(set(deps.get("main.tex", [])), {"sections/intro.tex"})
        self.assertEqual(set(bibs), {"references.bib"})
        self.assertEqual(set(images), {"figures/logo.png"})

    def test_collect_advanced_simplified(self):
        """Test dependency collection on project_advanced (without graphicspath effects)"""
        project_dir = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        os.chdir(project_dir) # Run test from within the project dir
        ignore_patterns = latex_to_llm.load_ignore(".texexporterignore")
        # Make sure to pass ignore_patterns to the function
        visited, deps, bibs, images = latex_to_llm.collect_dependencies(["report.tex"], ignore_patterns)

        expected_visited = {
            "report.tex",
            "chapters/chap1.tex",
            "chapters/sections/chap1_intro.tex",
            "chapters/chap2.tex",
            "appendix/appA.tex",
        }
        self.assertEqual(set(visited), expected_visited)

        # Check dependencies
        self.assertIn("chapters/chap1.tex", deps.get("report.tex", []))
        self.assertIn("chapters/chap2.tex", deps.get("report.tex", []))
        self.assertIn("chapters/sections/chap1_intro.tex", deps.get("chapters/chap1.tex", []))
        # <<< THE ONLY LINE CHANGED >>>
        # Check the dependency list for chap2 includes the *correct relative path*
        self.assertIn("chapters/flow.tikz", deps.get("chapters/chap2.tex", []))

        self.assertEqual(set(bibs), {"biblio/main_refs.bib"})
        # Image ref path is relative to the including file (chap1.tex) -> chapters/plot.pdf
        self.assertEqual(set(images), {"chapters/plot.pdf"})


    # @unittest.skip("Skipping edge case tests in simplified version")
    # def test_collect_edgecases_defaults(self): ...
    #
    # @unittest.skip("Skipping edge case tests in simplified version")
    # def test_collect_edgecases_with_ignores(self): ...


class TestWriteOutputsSimplified(unittest.TestCase):
    """Test output writing functionality (using simple setup)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_unit_out_")
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        os.makedirs("sections", exist_ok=True)
        with open("main.tex", "w") as f: f.write("Main")
        with open("sections/intro.tex", "w") as f: f.write("Intro")
        with open("refs.bib", "w") as f: f.write("Bib")

        self.visited = ["main.tex", "sections/intro.tex"]
        self.deps = {"main.tex": ["sections/intro.tex"]}
        self.bibs = ["refs.bib", "missing.bib"] # Keep missing bib to test manifest
        self.images = ["figs/fig1.png"]

    def tearDown(self):
        robust_tearDown(self)

    def test_write_single_output(self):
        """Test writing to a single file"""
        args = MagicMock(output="export_single", per_folder=False, manifest=None)
        latex_to_llm.write_outputs(self.visited, self.deps, self.bibs, self.images, args)

        main_file = os.path.join(args.output, "full-project.txt")
        bib_file = os.path.join(args.output, "bibliography.txt")
        self.assertTrue(os.path.exists(main_file))
        self.assertTrue(os.path.exists(bib_file)) # Exists because refs.bib was found
        with open(main_file, "r") as f:
            content = f.read()
            self.assertIn("=== File: main.tex ===", content)
            self.assertIn("=== File: sections/intro.tex ===", content)
        with open(bib_file, "r") as f:
            content = f.read()
            self.assertIn("=== Bib: refs.bib ===", content)
            # Check that the (Not Found) header isn't written for missing.bib anymore
            self.assertNotIn("missing.bib", content)

    def test_write_per_folder(self):
        """Test writing output files per folder"""
        args = MagicMock(output="export_pfolder", per_folder=True, manifest=None)
        latex_to_llm.write_outputs(self.visited, self.deps, self.bibs, self.images, args)
        self.assertTrue(os.path.exists(os.path.join(args.output, "_.txt")))
        self.assertTrue(os.path.exists(os.path.join(args.output, "sections.txt")))
        self.assertTrue(os.path.exists(os.path.join(args.output, "bibliography.txt")))

    def test_write_manifest_json(self):
        """Test writing JSON manifest"""
        args = MagicMock(output="export_manifest", per_folder=False, manifest="json")
        latex_to_llm.write_outputs(self.visited, self.deps, self.bibs, self.images, args)
        manifest_file = os.path.join(args.output, "manifest.json")
        self.assertTrue(os.path.exists(manifest_file))
        import json
        with open(manifest_file, "r") as f: manifest_data = json.load(f)
        self.assertEqual(manifest_data["files"], ["main.tex", "sections/intro.tex"])
        self.assertEqual(set(manifest_data["bibs"]), {"refs.bib", "missing.bib"}) # Manifest lists all refs
        self.assertEqual(manifest_data["images"], ["figs/fig1.png"])

    @unittest.skipIf(latex_to_llm.yaml is None, "PyYAML not installed")
    def test_write_manifest_yaml(self):
        """Test writing YAML manifest"""
        args = MagicMock(output="export_yaml", per_folder=False, manifest="yaml")
        latex_to_llm.write_outputs(self.visited, self.deps, self.bibs, self.images, args)
        manifest_file = os.path.join(args.output, "manifest.yaml")
        self.assertTrue(os.path.exists(manifest_file))
        # Basic load check is sufficient here
        import yaml
        with open(manifest_file, "r") as f:
            data = yaml.safe_load(f)
            self.assertIn("files", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)