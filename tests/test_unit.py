# test_unit.py

import os
import sys
import unittest
import tempfile
import shutil
import stat
import gc
import time
from unittest.mock import patch, MagicMock

# Add parent directory to path to import latex_to_llm
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import latex_to_llm

# Check if running on Windows
_ON_WINDOWS = os.name == 'nt'

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


def tearDownModule():
    # (Optional) module-level cleanup if needed
    # Force garbage collection to help Windows release file handles
    gc.collect()
    if _ON_WINDOWS:
        time.sleep(0.5)  # Short delay


class TestCoreFunctions(unittest.TestCase):
    """Test non-filesystem functions like ignore parsing and matching"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_unit_core_")
        self.old_cwd  = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        robust_tearDown(self)

    def test_load_ignore(self):
        """Test loading ignore patterns from file"""
        ignore_content = "_build/\n*.log\n# Comment\n  temp.* # With comment"
        with open(".testignore", "w", encoding='utf-8') as f:
            f.write(ignore_content)

        patterns = latex_to_llm.load_ignore(".testignore")
        self.assertEqual(patterns, ["_build/", "*.log", "temp.*"])

    def test_matches_any_simple(self):
        """Test the simplified pattern matching"""
        patterns = ["_build/", "*.log", "temp.txt", "docs/specific.tex"]
        self.assertTrue(latex_to_llm.matches_any("_build/file.txt", patterns))
        self.assertTrue(latex_to_llm.matches_any("file.log", patterns))
        self.assertTrue(latex_to_llm.matches_any("subdir/file.log", patterns))
        self.assertTrue(latex_to_llm.matches_any("temp.txt", patterns))
        self.assertTrue(latex_to_llm.matches_any("docs/specific.tex", patterns))
        self.assertFalse(latex_to_llm.matches_any("build/file.txt", patterns))
        self.assertFalse(latex_to_llm.matches_any("file.txt", patterns))
        self.assertFalse(latex_to_llm.matches_any("docs/other.tex", patterns))

    def test_resolve_tex_path(self):
        """Test resolving various file references"""
        base = os.path.abspath(os.path.join(self.temp_dir, "chapter"))
        os.makedirs(base, exist_ok=True)
        self.assertEqual(
            latex_to_llm.resolve_tex_path(base, "section1"),
            os.path.abspath(os.path.join(base, "section1.tex"))
        )
        self.assertEqual(
            latex_to_llm.resolve_tex_path(base, "section2.tex"),
            os.path.abspath(os.path.join(base, "section2.tex"))
        )
        self.assertEqual(
            latex_to_llm.resolve_tex_path(base, "figure.pdf"),
            os.path.abspath(os.path.join(base, "figure.pdf"))
        )

    def test_normalize_path(self):
        """Test normalizing paths relative to CWD"""
        os.makedirs("subdir/nested", exist_ok=True)
        base_dir = os.path.abspath("subdir")
        self.assertEqual(
            latex_to_llm.normalize_path(base_dir, "file.txt"),
            "subdir/file.txt"
        )
        self.assertEqual(
            latex_to_llm.normalize_path(base_dir, "../other.pdf"),
            "other.pdf"
        )


class TestDependencyCollectionSimplified(unittest.TestCase):
    """Test collect_dependencies using simplified fixtures"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_unit_deps_")
        self.old_cwd  = os.getcwd()
        shutil.copytree(
            os.path.join(os.path.dirname(__file__), 'fixtures'),
            os.path.join(self.temp_dir, 'fixtures'),
            dirs_exist_ok=True
        )
        os.chdir(self.temp_dir)

    def tearDown(self):
        robust_tearDown(self)

    def test_collect_basic(self):
        """Test dependency collection on project_basic"""
        project_dir = os.path.join(self.temp_dir, 'fixtures', 'project_basic')
        os.chdir(project_dir)
        visited, deps, bibs, images = latex_to_llm.collect_dependencies(
            ["main.tex"], []
        )
        self.assertEqual(set(visited), {"main.tex", "sections/intro.tex"})
        self.assertEqual(set(deps["main.tex"]), {"sections/intro.tex"})
        self.assertEqual(set(bibs), {"references.bib"})
        self.assertEqual(set(images), {"figures/logo.png"})

    def test_collect_advanced_simplified(self):
        """Test dependency collection on project_advanced (without graphicspath)"""
        project_dir = os.path.join(self.temp_dir, 'fixtures', 'project_advanced')
        os.chdir(project_dir)
        ignore_patterns = latex_to_llm.load_ignore(".texexporterignore")
        visited, deps, bibs, images = latex_to_llm.collect_dependencies(
            ["report.tex"], ignore_patterns
        )

        expected = {
            "report.tex",
            "chapters/chap1.tex",
            "chapters/sections/chap1_intro.tex",
            "chapters/chap2.tex",
            "appendix/appA.tex",
        }
        self.assertEqual(set(visited), expected)
        self.assertIn("chapters/flow.tikz", deps.get("chapters/chap2.tex", []))
        self.assertEqual(set(bibs), {"biblio/main_refs.bib"})
        self.assertEqual(set(images), {"chapters/plot.pdf"})


class TestWriteOutputsSimplified(unittest.TestCase):
    """Test output writing functionality (using simple setup)"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="latex_llm_unit_out_")
        self.old_cwd  = os.getcwd()
        os.chdir(self.temp_dir)
        os.makedirs("sections", exist_ok=True)
        with open("main.tex", "w") as f:
            f.write("Main")
        with open("sections/intro.tex", "w") as f:
            f.write("Intro")
        with open("refs.bib", "w") as f:
            f.write("Bib")

        self.visited = ["main.tex", "sections/intro.tex"]
        self.deps    = {"main.tex": ["sections/intro.tex"]}
        self.bibs    = ["refs.bib", "missing.bib"]
        self.images  = ["figs/fig1.png"]

    def tearDown(self):
        robust_tearDown(self)

    def test_write_single_output(self):
        """Test writing to a single file"""
        args = MagicMock(output="export_single", per_folder=False, manifest=None, exclude_folder=[])
        latex_to_llm.write_outputs(
            self.visited, self.deps, self.bibs, self.images, args
        )
        main_file = os.path.join(args.output, "full-project.txt")
        bib_file  = os.path.join(args.output, "bibliography.txt")
        self.assertTrue(os.path.exists(main_file))
        self.assertTrue(os.path.exists(bib_file))
        with open(main_file) as f:
            text = f.read()
            self.assertIn("=== File: main.tex ===", text)
            self.assertIn("=== File: sections/intro.tex ===", text)
        with open(bib_file) as f:
            text = f.read()
            self.assertIn("=== Bib: refs.bib ===", text)
            self.assertNotIn("missing.bib", text)

    def test_write_per_folder(self):
        """Test writing output files per folder"""
        args = MagicMock(output="export_pfolder", per_folder=True, manifest=None, exclude_folder=[])
        latex_to_llm.write_outputs(
            self.visited, self.deps, self.bibs, self.images, args
        )
        self.assertTrue(os.path.exists(os.path.join(args.output, "_.txt")))
        self.assertTrue(os.path.exists(os.path.join(args.output, "sections.txt")))
        self.assertTrue(os.path.exists(os.path.join(args.output, "bibliography.txt")))

    def test_write_manifest_json(self):
        """Test writing JSON manifest"""
        args = MagicMock(output="export_manifest", per_folder=False, manifest="json", exclude_folder=[])
        latex_to_llm.write_outputs(
            self.visited, self.deps, self.bibs, self.images, args
        )
        manifest_file = os.path.join(args.output, "manifest.json")
        self.assertTrue(os.path.exists(manifest_file))
        import json
        with open(manifest_file) as f:
            data = json.load(f)
        self.assertEqual(data["files"], ["main.tex", "sections/intro.tex"])
        self.assertEqual(set(data["bibs"]), {"refs.bib", "missing.bib"})
        self.assertEqual(data["images"], ["figs/fig1.png"])

    @unittest.skipIf(latex_to_llm.yaml is None, "PyYAML not installed")
    def test_write_manifest_yaml(self):
        """Test writing YAML manifest"""
        args = MagicMock(output="export_yaml", per_folder=False, manifest="yaml", exclude_folder=[])
        latex_to_llm.write_outputs(
            self.visited, self.deps, self.bibs, self.images, args
        )
        manifest_file = os.path.join(args.output, "manifest.yaml")
        self.assertTrue(os.path.exists(manifest_file))
        import yaml
        with open(manifest_file) as f:
            yaml.safe_load(f)


if __name__ == "__main__":
    # Print a note about expected Windows behavior
    if _ON_WINDOWS:
        print("Note: On Windows, some directory cleanup warnings may appear - this is expected behavior")
    unittest.main(verbosity=2)