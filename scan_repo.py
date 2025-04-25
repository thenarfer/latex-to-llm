#!/usr/bin/env python3
"""
Scans the current directory (expected to be the latex-to-llm repo root)
and reports on the project structure, focusing on relevant files like
Python scripts, tests, fixtures, and config files.
"""

import os
import sys
import glob

# --- Configuration ---
EXPECTED_FILES = [
    "latex_to_llm.py",
    "setup.py",
    "README.md",
    "requirements.txt",
    "run_tests.py",
    ".gitignore", # Optional but good practice
    "LICENSE", # Optional but good practice
]

TEST_DIRS = ["tests"]
FIXTURE_BASE_DIR = "tests/fixtures"
EXPECTED_FIXTURES = [
    "project_basic",
    "project_advanced",
    "project_edgecases",
]
PYTHON_FILE_EXT = ".py"
TEST_FILE_PREFIX = "test_"
CONFIG_EXTS = [".yaml", ".yml", ".json", ".toml", ".ini"]
DOC_EXTS = [".md", ".rst", ".txt"]
LATEX_EXTS = [".tex", ".bib", ".cls", ".sty", ".tikz", ".png", ".jpg", ".jpeg", ".pdf", ".eps"]
IGNORE_EXTS = [".pyc", ".pyo"]
IGNORE_DIRS = ["__pycache__", ".git", ".pytest_cache", ".mypy_cache", "export", ".venv", "venv", "env"]
# --- End Configuration ---

def scan_directory(start_path="."):
    """Recursively scans the directory and reports findings."""
    print(f"Scanning repository structure starting from: {os.path.abspath(start_path)}\n")

    found_structure = {
        "root_files": [],
        "python_scripts": [],
        "test_scripts": [],
        "fixture_projects": {}, # Key: project name, Value: list of files
        "other_configs": [],
        "documentation": [],
        "unknown_files": [],
        "directories": set(),
        "issues": []
    }

    # Check expected root files first
    print("--- Root Directory Files ---")
    missing_expected = []
    for fname in EXPECTED_FILES:
        fpath = os.path.join(start_path, fname)
        if os.path.isfile(fpath):
            print(f"[ OK ] Found expected root file: {fname}")
            found_structure["root_files"].append(fname)
            if fname.endswith(PYTHON_FILE_EXT):
                 found_structure["python_scripts"].append(fname)
            elif fname.endswith(tuple(DOC_EXTS)):
                 found_structure["documentation"].append(fname)
        else:
            if fname not in ["LICENSE", ".gitignore"]: # Only warn if core files missing
                print(f"[WARN] Expected root file NOT found: {fname}")
                missing_expected.append(fname)
            else:
                print(f"[INFO] Optional root file not found: {fname}")

    if missing_expected:
        found_structure["issues"].append(f"Missing expected root files: {', '.join(missing_expected)}")

    # Walk through the directory tree
    print("\n--- Directory Scan ---")
    for root, dirs, files in os.walk(start_path, topdown=True):
        # Modify dirs in-place to prevent descending into ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        rel_root = os.path.relpath(root, start_path).replace(os.sep, '/')
        if rel_root == ".":
            rel_root = "" # Represent root as empty string for cleaner paths

        # Record directories (excluding ignored ones)
        for d in dirs:
            dir_path = f"{rel_root}/{d}" if rel_root else d
            found_structure["directories"].add(dir_path)
            print(f"[DIR ] Found directory: {dir_path}")


        # Process files in the current directory
        for file in files:
            _, ext = os.path.splitext(file)
            if ext in IGNORE_EXTS:
                continue # Skip ignored extensions

            file_rel_path = f"{rel_root}/{file}" if rel_root else file
            print(f"[FILE] Found file: {file_rel_path}")

            # Categorize files
            is_test_dir = any(rel_root.startswith(tdir) for tdir in TEST_DIRS)
            is_fixture_dir = rel_root.startswith(FIXTURE_BASE_DIR)

            if ext == PYTHON_FILE_EXT:
                if is_test_dir and file.startswith(TEST_FILE_PREFIX):
                    found_structure["test_scripts"].append(file_rel_path)
                elif rel_root == "": # Already handled root scripts
                    pass
                else:
                    found_structure["python_scripts"].append(file_rel_path)

            elif is_fixture_dir:
                 # Determine which fixture project this file belongs to
                 fixture_project_rel_path = rel_root[len(FIXTURE_BASE_DIR):].lstrip('/')
                 fixture_project_name = fixture_project_rel_path.split('/')[0]
                 if fixture_project_name:
                     if fixture_project_name not in found_structure["fixture_projects"]:
                         found_structure["fixture_projects"][fixture_project_name] = []
                     found_structure["fixture_projects"][fixture_project_name].append(file_rel_path)
                 else:
                     # File directly under tests/fixtures? Unlikely but handle.
                     found_structure["unknown_files"].append(file_rel_path)


            elif ext in CONFIG_EXTS or file == ".texexporterignore":
                found_structure["other_configs"].append(file_rel_path)
            elif ext in DOC_EXTS and rel_root != "": # Root docs handled above
                found_structure["documentation"].append(file_rel_path)
            elif ext in LATEX_EXTS and not is_fixture_dir:
                 # LaTeX files outside fixtures? Unexpected.
                 print(f"[WARN] Found LaTeX file outside fixtures: {file_rel_path}")
                 found_structure["unknown_files"].append(file_rel_path)
            elif not is_fixture_dir and ext not in IGNORE_EXTS and file not in EXPECTED_FILES and rel_root == "":
                 # Other files in root not explicitly expected
                 found_structure["unknown_files"].append(file_rel_path)


    # --- Summary and Checks ---
    print("\n--- Scan Summary ---")
    print(f"* Root Files Found: {len(found_structure['root_files'])}")
    print(f"* Python Scripts (non-test): {len(found_structure['python_scripts'])}")
    print(f"* Test Scripts: {len(found_structure['test_scripts'])}")
    print(f"* Config/Ignore Files: {len(found_structure['other_configs'])}")
    print(f"* Documentation Files: {len(found_structure['documentation'])}")
    print(f"* Directories Found: {len(found_structure['directories'])}")
    print(f"* Fixture Projects Found: {len(found_structure['fixture_projects'])}")
    for name, files in found_structure["fixture_projects"].items():
        print(f"  - {name}: {len(files)} files")

    # Check for expected fixtures
    print("\n--- Fixture Checks ---")
    missing_fixtures = []
    for expected_fix in EXPECTED_FIXTURES:
        if expected_fix not in found_structure["fixture_projects"]:
            print(f"[FAIL] Expected fixture project '{expected_fix}' NOT found.")
            missing_fixtures.append(expected_fix)
        else:
            print(f"[ OK ] Expected fixture project '{expected_fix}' found.")
            # You could add more detailed checks here, e.g., minimum file count
            if not found_structure["fixture_projects"][expected_fix]:
                print(f"[WARN] Fixture project '{expected_fix}' seems empty.")
                found_structure["issues"].append(f"Fixture project '{expected_fix}' has no files.")

    if missing_fixtures:
         found_structure["issues"].append(f"Missing expected fixtures: {', '.join(missing_fixtures)}")


    # Check for expected test files
    print("\n--- Test File Checks ---")
    if not found_structure["test_scripts"]:
        print("[FAIL] No test scripts found (expected files like test_*.py in tests/).")
        found_structure["issues"].append("No test scripts found.")
    else:
        # Check if specific important test files exist
        expected_test_files = ['tests/test_unit.py', 'tests/test_integration.py', 'tests/test_cli.py'] # Assuming you might add test_cli.py
        missing_tests = []
        current_tests = set(found_structure["test_scripts"])
        for test_file in expected_test_files:
            if test_file not in current_tests:
                 print(f"[WARN] Expected test file '{test_file}' not found.")
                 missing_tests.append(test_file)
            else:
                 print(f"[ OK ] Found expected test file: {test_file}")
        if missing_tests:
            found_structure["issues"].append(f"Missing expected test files: {', '.join(missing_tests)}")


    if found_structure["unknown_files"]:
        print("\n--- Unknown/Unexpected Files ---")
        print("These files were found but not categorized:")
        for f in found_structure["unknown_files"]:
            print(f"  - {f}")
        found_structure["issues"].append(f"Found {len(found_structure['unknown_files'])} unexpected files.")

    print("\n--- Issues Summary ---")
    if not found_structure["issues"]:
        print("[ OK ] No major structural issues detected.")
    else:
        print("[FAIL] Potential structural issues detected:")
        for issue in found_structure["issues"]:
            print(f"  - {issue}")

    print("\nScan complete.")
    return len(found_structure["issues"]) # Return number of issues

if __name__ == "__main__":
    exit_code = scan_directory()
    sys.exit(exit_code) # Exit with 0 if no issues, >0 otherwise