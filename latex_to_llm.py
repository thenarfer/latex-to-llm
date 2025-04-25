#!/usr/bin/env python3
"""
latex-to-llm.py (Simplified Version)

Recursively exports only the LaTeX files actually used by a main .tex entry
point (via \subfile, \input, \include) into plain‐text dumps, respecting
basic ignore rules. Does not handle \graphicspath.
"""

import os
import sys
import re
import glob
import fnmatch
import argparse
import json
from collections import OrderedDict

try:
    import yaml
except ImportError:
    yaml = None

# Regexes remain the same
INCLUDE_REGEX = re.compile(r'\\(?:subfile|input|include)\{([^}]+)\}')
BIB_REGEX = re.compile(r'\\(?:bibliography|addbibresource)\{([^}]+)\}')
GRAPHICS_REGEX = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}')

def load_ignore(path):
    """Loads ignore patterns from a file, ignoring comments and blank lines."""
    patterns = []
    if os.path.isfile(path):
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.split('#', 1)[0].strip() # Remove comments and strip whitespace
                    if line:
                        patterns.append(line)
        except Exception as e:
            print(f"Warning: Could not read ignore file {path}: {e}", file=sys.stderr)
    return patterns

def matches_any(rel_path, patterns):
    """
    Simple check if the relative path or its basename matches any pattern.
    Handles basic wildcards via fnmatch. Directory patterns ending in '/'
    are checked via startswith.
    """
    rel_path_norm = rel_path.replace(os.sep, '/')
    basename = os.path.basename(rel_path_norm)

    for pat in patterns:
        pat_norm = pat.replace(os.sep, '/')
        # Check full path match
        if fnmatch.fnmatch(rel_path_norm, pat_norm):
            return True
        # Check basename match
        if fnmatch.fnmatch(basename, pat_norm):
            return True
        # Check directory match (if pattern ends with /)
        if pat_norm.endswith('/') and rel_path_norm.startswith(pat_norm):
            return True
    return False


def select_entry_points(args):
    """Selects entry point files, prompting if necessary."""
    if args.entry:
        return args.entry
    # Use current working directory for glob
    candidates = sorted([f for f in glob.glob("*.tex") if os.path.isfile(f)])
    if not candidates:
        print("Error: No .tex files found in the current directory.", file=sys.stderr)
        sys.exit(1)
    # if there's exactly one .tex, just pick it—no prompt needed
    if len(candidates) == 1:
        print(f"Auto-selected entry point: {candidates[0]}")
        return candidates
    print("Select one or more entry-point files (comma-separated indices):")
    for idx, name in enumerate(candidates, 1):
        print(f"  {idx}. {name}")
    choice = input(f"Enter choice [1-{len(candidates)}]: ").strip()
    if not choice: # Default to 1 if user just presses Enter
        choice = "1"

    selected = []
    invalid_choices = []
    for part in choice.split(','):
        try:
            part = part.strip()
            if not part: continue
            i = int(part)
            if 1 <= i <= len(candidates):
                selected.append(candidates[i-1])
            else:
                invalid_choices.append(part)
        except ValueError:
            invalid_choices.append(part)

    if invalid_choices:
        print(f"Warning: Invalid choices ignored: {', '.join(invalid_choices)}", file=sys.stderr)
    if not selected:
        print("Error: No valid entry points selected.", file=sys.stderr)
        sys.exit(1)
    return selected

def resolve_tex_path(base_dir, ref):
    """Resolves a reference relative to a base directory.
       Adds .tex extension only if the reference doesn't appear to have one.
    """
    ref_path = ref
    _, ext = os.path.splitext(ref)
    # Only add .tex if there's no extension part
    if not ext:
        ref_path += '.tex'
    abs_path = os.path.abspath(os.path.join(base_dir, ref_path))
    return abs_path

def normalize_path(base_dir, ref_path):
    """Normalizes a path relative to a base directory, returning a
       project-relative path with forward slashes."""
    try:
        abs_path = os.path.abspath(os.path.join(base_dir, ref_path))
        rel_path = os.path.relpath(abs_path, start=os.getcwd()).replace(os.sep, '/')
        return rel_path
    except ValueError as e:
        # Fallback for path errors (e.g., different drives)
        print(f"Warning: Could not compute relative path for '{ref_path}' from '{base_dir}'. Using original. Error: {e}", file=sys.stderr)
        return ref_path.replace(os.sep, '/')

def collect_dependencies(entry_files, all_ignore_patterns):
    """Recursively collects dependencies (.tex, .bib, image refs)."""
    visited_set = set()
    deps = OrderedDict()
    bibs = set()
    images = set()
    processed_order = []

    def recurse(path_abs):
        try:
            rel_path = os.path.relpath(path_abs).replace(os.sep, '/')
        except ValueError:
            # print(f"Warning: Cannot get relative path for {path_abs}. Skipping.", file=sys.stderr)
            return # Cannot process if relative path fails

        # Check ignore/visited status first
        if rel_path in visited_set or matches_any(rel_path, all_ignore_patterns):
            return

        # Check if file exists *after* ignore checks
        if not os.path.isfile(path_abs):
             print(f"Warning: Referenced file not found: {rel_path}", file=sys.stderr)
             visited_set.add(rel_path) # Mark as visited (attempted)
             return

        # Mark as visited and add to processing order
        visited_set.add(rel_path)
        processed_order.append(rel_path)
        deps[rel_path] = [] # Initialize dependencies for this file

        try:
            # Read whole file - simpler but cannot ignore commented includes easily
            with open(path_abs, encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Warning: Could not read file {rel_path}: {e}", file=sys.stderr)
            return # Cannot process children if unreadable

        current_dir = os.path.dirname(path_abs)
        project_root = os.getcwd()

        # --- Find subfiles/includes ---
        for ref in INCLUDE_REGEX.findall(text):
            # Resolve path relative to the current file
            child_abs = resolve_tex_path(current_dir, ref)
            try:
                child_rel = os.path.relpath(child_abs, start=project_root).replace(os.sep, '/')
            except ValueError:
                continue # Skip if relpath fails

            # Check if resolved path should be ignored
            if matches_any(child_rel, all_ignore_patterns):
                continue

            # Add dependency relationship
            if child_rel not in deps.get(rel_path, []):
                deps[rel_path].append(child_rel)

            # Recurse if not already visited
            if child_rel not in visited_set:
                recurse(child_abs)


        # --- Collect .bib references ---
        for ref in BIB_REGEX.findall(text):
            bib_file = ref if ref.lower().endswith('.bib') else ref + '.bib'
            bib_abs = os.path.abspath(os.path.join(current_dir, bib_file))
            bib_found = True
            if not os.path.isfile(bib_abs):
                 bib_abs_root = os.path.abspath(os.path.join(project_root, bib_file))
                 if os.path.isfile(bib_abs_root):
                     bib_abs = bib_abs_root
                 else:
                     bib_found = False
                     bib_rel = bib_file.replace(os.sep, '/') # Use original ref if not found

            if bib_found:
                 try:
                     bib_rel = os.path.relpath(bib_abs, start=project_root).replace(os.sep, '/')
                 except ValueError:
                     bib_rel = bib_file.replace(os.sep, '/') # Fallback

            if not matches_any(bib_rel, all_ignore_patterns):
                bibs.add(bib_rel)


        # --- Collect graphics references ---
        for ref in GRAPHICS_REGEX.findall(text):
            # Normalize path relative to project root (doesn't use graphicspath)
            img_rel_path = normalize_path(current_dir, ref)

            # Check ignores on the final relative path
            if not matches_any(img_rel_path, all_ignore_patterns):
                images.add(img_rel_path)

    # --- Main loop to process entry points ---
    initial_cwd = os.getcwd()
    for entry in entry_files:
        entry_abs = os.path.abspath(os.path.join(initial_cwd, entry))
        if not os.path.isfile(entry_abs):
             print(f"Error: Entry file not found: {entry}", file=sys.stderr)
             continue
        recurse(entry_abs)

    return processed_order, deps, sorted(list(bibs)), sorted(list(images))


def print_tree(deps, roots):
    """Prints the dependency tree structure."""
    processed = set()
    def _print(node, prefix=""):
        if node in processed:
            print(prefix + node + " (seen)")
            return
        print(prefix + node)
        processed.add(node)
        if node in deps:
            # Sort children for deterministic output
            for child in sorted(deps[node]):
                _print(child, prefix + "  ")

    print("\nDependency tree (based on collected dependencies):")
    valid_roots = [r for r in roots if os.path.exists(r)]
    if not valid_roots:
        print(" (No valid entry points found)")
        return

    processed_roots_in_deps = sorted([os.path.relpath(r).replace(os.sep, '/') for r in valid_roots if os.path.relpath(r).replace(os.sep, '/') in deps])

    if not processed_roots_in_deps:
        print(" (None of the entry points were processed or had dependencies)")
        return

    for r_rel in processed_roots_in_deps:
         _print(r_rel)


def write_outputs(visited, deps, bibs, images, args):
    """Writes the collected content to output files."""
    try:
        os.makedirs(args.output, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create output directory '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure manifest uses project-relative paths with forward slashes
    manifest = {
        "files": [p.replace(os.sep, '/') for p in visited],
        "bibs": [p.replace(os.sep, '/') for p in bibs],
        "images": [p.replace(os.sep, '/') for p in images]
    }

    # --- Write .tex file contents ---
    if args.per_folder:
        grouped = {}
        for rel_path in visited:
            abs_path = os.path.abspath(rel_path)
            if not os.path.isfile(abs_path):
                 print(f"Warning: Skipping file write for non-existent file: {rel_path}", file=sys.stderr)
                 continue
            folder = os.path.dirname(rel_path) or "."
            sanitized_folder = re.sub(r'[\\/*?:"<>|]', '_', folder)
            key = "_" if folder in ("", ".") else sanitized_folder
            grouped.setdefault(key, []).append((rel_path, abs_path))

        for folder_key, files_in_folder in grouped.items():
            outpath = os.path.join(args.output, f"{folder_key}.txt")
            try:
                with open(outpath, 'w', encoding='utf-8') as out:
                    for rel_path, abs_path in sorted(files_in_folder): # Sort within folder
                        out.write(f"=== File: {rel_path.replace(os.sep, '/')} ===\n")
                        try:
                            with open(abs_path, encoding='utf-8') as infile:
                                out.write(infile.read())
                        except Exception as e:
                            out.write(f"*** Error reading file: {e} ***\n")
                        out.write("\n\n")
            except Exception as e:
                 print(f"Error: Could not write output file {outpath}: {e}", file=sys.stderr)

    else: # Single file output
        full_outpath = os.path.join(args.output, "full-project.txt")
        try:
            with open(full_outpath, 'w', encoding='utf-8') as out:
                for rel_path in visited: # Use visited order
                    abs_path = os.path.abspath(rel_path)
                    if not os.path.isfile(abs_path):
                        # print(f"Warning: Skipping file write for non-existent file: {rel_path}", file=sys.stderr)
                        continue # Skip non-existent files
                    out.write(f"=== File: {rel_path.replace(os.sep, '/')} ===\n")
                    try:
                        with open(abs_path, encoding='utf-8') as infile:
                            out.write(infile.read())
                    except Exception as e:
                        out.write(f"*** Error reading file: {e} ***\n")
                    out.write("\n\n")
        except Exception as e:
            print(f"Error: Could not write output file {full_outpath}: {e}", file=sys.stderr)

    # --- Write bibliography contents ---
    bib_outpath = os.path.join(args.output, "bibliography.txt")
    found_any_bib_content = False
    if bibs:
        try:
            with open(bib_outpath, 'w', encoding='utf-8') as out:
                for bib_rel in manifest['bibs']:
                    bib_abs = os.path.abspath(bib_rel)
                    if os.path.isfile(bib_abs):
                        out.write(f"=== Bib: {bib_rel} ===\n")
                        try:
                            with open(bib_abs, encoding='utf-8') as infile:
                                out.write(infile.read())
                            found_any_bib_content = True # Mark that we wrote content
                        except Exception as e:
                             out.write(f"*** Error reading file: {e} ***\n")
                        out.write("\n\n")
                    else:
                        # Only write header for non-existent bib if requested?
                        # For now, let's skip writing anything for bibs not found.
                        # They are still listed in the manifest.
                        # out.write(f"=== Bib: {bib_rel} (Not Found) ===\n\n")
                         pass

        except Exception as e:
            print(f"Error: Could not write bibliography output file {bib_outpath}: {e}", file=sys.stderr)

    # Clean up empty bibliography.txt if no content was written
    if bibs and not found_any_bib_content and os.path.exists(bib_outpath):
        try:
            if os.path.getsize(bib_outpath) == 0:
                os.remove(bib_outpath)
        except OSError:
            pass # Ignore error during cleanup


    # --- Write manifest ---
    if args.manifest:
        manifest_filename = f'manifest.{args.manifest}'
        manifest_path = os.path.join(args.output, manifest_filename)
        try:
            with open(manifest_path, 'w', encoding='utf-8') as out:
                if args.manifest == 'yaml':
                    if yaml:
                        yaml.safe_dump(manifest, out, default_flow_style=False, sort_keys=False)
                    else:
                        print("Error: YAML output requested but PyYAML is not installed. Install it with 'pip install pyyaml'. Falling back to JSON.", file=sys.stderr)
                        json.dump(manifest, out, indent=2)
                        manifest_path += " (json fallback)"
                else: # Default to JSON
                    json.dump(manifest, out, indent=2)
            print(f"Manifest written to {manifest_path}")
        except Exception as e:
            print(f"Error: Could not write manifest file {manifest_path}: {e}", file=sys.stderr)


def main():
    """Parses arguments and orchestrates the export process."""
    initial_cwd = os.getcwd()
    p = argparse.ArgumentParser(
        description="Recursively exports used LaTeX files into text dumps for LLMs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument('-e', '--entry', nargs='+', help='Main .tex file(s). Prompts if not given.')
    p.add_argument('-i', '--ignore-file', default='.texexporterignore', help='Path to ignore-file (gitignore syntax).')
    p.add_argument('-x', '--exclude-folder', action='append', default=[], help='Folder patterns to exclude (e.g., "build/").')
    p.add_argument('-f', '--exclude-file', action='append', default=[], help='Filename patterns to exclude (e.g., "*.log").')
    p.add_argument('-d', '--dry-run', action='store_true', help='Show dependencies only; no output files.')
    p.add_argument('-p', '--per-folder', action='store_true', help='Output one .txt per folder instead of one large file.')
    p.add_argument('-m', '--manifest', choices=['json', 'yaml'], const='json', nargs='?', help='Write manifest file (default: json).')
    p.add_argument('-o', '--output', default='export', help='Output directory name.')
    args = p.parse_args()

    try:
        entries = select_entry_points(args)
        if not entries:
             sys.exit(1) # Error message already printed by select_entry_points

        # Load and combine ignore patterns
        ignore_file_path = os.path.join(initial_cwd, args.ignore_file)
        ignore_patterns_from_file = load_ignore(ignore_file_path) if os.path.exists(ignore_file_path) else []
        all_ignore_patterns = ignore_patterns_from_file + args.exclude_folder + args.exclude_file

        # Collect dependencies
        visited, deps, bibs, images = collect_dependencies(
            entries,
            all_ignore_patterns
        )

        if not visited and not bibs and not images:
            print("Warning: No dependencies found. Check entry points and ignore patterns.", file=sys.stderr)

        # Handle dry run
        if args.dry_run:
            print("\n--- Dry Run ---")
            print_tree(deps, entries)
            print("\nFiles to be exported:")
            print(" - " + "\n - ".join(visited) if visited else " (None)")
            print("\n.bib files referenced:")
            print(" - " + "\n - ".join(bibs) if bibs else " (None)")
            print("\nImages referenced:")
            print(" - " + "\n - ".join(images) if images else " (None)")
            print("--- End Dry Run ---")
            sys.exit(0)

        # Write output files
        write_outputs(visited, deps, bibs, images, args)
        print(f"\nExport complete. Output written to: {os.path.abspath(args.output)}")

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()