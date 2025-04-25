#!/usr/bin/env python3
"""
latex-to-llm.py

Recursively exports only the LaTeX files actually used by a main .tex entry
point (via \\subfile, \\input, \\include) into plain‐text dumps, with options
for dry-run, per-folder, manifest output, ignore rules, and more.
"""

import os
import sys
import re
import glob
import fnmatch
import argparse
import json

try:
    import yaml
except ImportError:
    yaml = None

INCLUDE_REGEX = re.compile(r'\\(?:subfile|input|include)\{([^}]+)\}')
BIB_REGEX = re.compile(r'\\(?:bibliography|addbibresource)\{([^}]+)\}')
GRAPHICS_REGEX = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}')

def load_ignore(path):
    patterns = []
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns

def matches_any(path, patterns):
    return any(fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(os.path.basename(path), pat)
               for pat in patterns)

def select_entry_points(args):
    if args.entry:
        return args.entry
    candidates = sorted(glob.glob("*.tex"))
    if not candidates:
        print("No .tex files found in the top folder.", file=sys.stderr)
        sys.exit(1)
    print("Select one or more entry-point files (comma-separated indices):")
    for idx, name in enumerate(candidates, 1):
        print(f"  {idx}. {name}")
    choice = input("Enter choice [1]: ").strip() or "1"
    selected = []
    for part in choice.split(","):
        try:
            i = int(part)
            selected.append(candidates[i-1])
        except:
            pass
    return selected

def resolve_tex_path(base_dir, ref):
    # add .tex if missing
    if not ref.endswith(".tex"):
        ref = ref + ".tex"
    return os.path.normpath(os.path.join(base_dir, ref))

def collect_dependencies(entry_files, ignore_folders, ignore_files):
    visited = []
    deps    = {}
    bibs    = set()
    images  = set()

    def recurse(path):
        # 1) Normalize this path to a project-relative, POSIX-style path
        rel = os.path.relpath(path).replace(os.sep, '/')
        if rel in visited:
            return
        if matches_any(rel, ignore_files):
            return
        # note: ignore_folders patterns are still matched against rel with '/'
        if any(rel.startswith(p.rstrip("*/") + '/') for p in ignore_folders):
            return

        if not os.path.isfile(path):
            return

        visited.append(rel)
        deps[rel] = []

        text = open(path, encoding="utf-8").read()

        # --- find subfiles/includes ---
        for ref in INCLUDE_REGEX.findall(text):
            child_abs = resolve_tex_path(os.path.dirname(path), ref)
            child_rel = os.path.relpath(child_abs).replace(os.sep, '/')
            if child_rel not in visited:
                deps[rel].append(child_rel)
                recurse(child_abs)

        # --- collect .bib references ---
        for ref in BIB_REGEX.findall(text):
            # ensure .bib extension
            bib_file = ref if ref.endswith(".bib") else ref + ".bib"
            bib_abs  = os.path.normpath(os.path.join(os.path.dirname(path), bib_file))
            # record as project-relative, POSIX path
            bib_rel  = os.path.relpath(bib_abs).replace(os.sep, '/')
            bibs.add(bib_rel)

        # --- collect graphics references ---
        for ref in GRAPHICS_REGEX.findall(text):
            images.add(ref)

    # kick off recursion from each entry file
    for entry in entry_files:
        recurse(os.path.abspath(entry))

    # return lists sorted for consistency
    return visited, deps, sorted(bibs), sorted(images)

def print_tree(deps, roots):
    def _print(node, prefix=""):
        print(prefix + node)
        for child in deps.get(node, []):
            _print(child, prefix + "  ")
    for r in roots:
        _print(r)

def write_outputs(visited, deps, bibs, images, args):
    os.makedirs(args.output, exist_ok=True)
    # manifest data
    manifest = {"files": [], "bibs": [], "images": images}

    # group by folder if needed
    grouped = {}
    for path in visited:
        folder = os.path.dirname(path) or "."
        grouped.setdefault(folder, []).append(path)

    # write per‐folder or single
    if args.per_folder:
        for folder, files in grouped.items():
            outpath = os.path.join(args.output, folder.replace(os.sep, "_") + ".txt")
            with open(outpath, "w", encoding="utf-8") as out:
                for fn in files:
                    out.write(f"=== File: {fn} ===\n")
                    out.write(open(fn, encoding="utf-8").read())
                    out.write("\n\n")
            manifest["files"].extend(files)
    else:
        full = os.path.join(args.output, "full-project.txt")
        with open(full, "w", encoding="utf-8") as out:
            for fn in visited:
                out.write(f"=== File: {fn} ===\n")
                out.write(open(fn, encoding="utf-8").read())
                out.write("\n\n")
        manifest["files"] = visited

    # append bibs
    bib_out = os.path.join(args.output, "bibliography.txt")
    if bibs:
        with open(bib_out, "w", encoding="utf-8") as out:
            for bib in bibs:
                if os.path.isfile(bib):
                    out.write(f"=== Bib: {bib} ===\n")
                    out.write(open(bib, encoding="utf-8").read())
                    out.write("\n\n")
                    manifest["bibs"].append(bib)

    # write manifest
    if args.manifest:
        if args.manifest == "yaml" and yaml:
            mf = os.path.join(args.output, "manifest.yaml")
            with open(mf, "w", encoding="utf-8") as out:
                yaml.safe_dump(manifest, out, sort_keys=False)
        else:
            mf = os.path.join(args.output, "manifest.json")
            with open(mf, "w", encoding="utf-8") as out:
                json.dump(manifest, out, indent=2)

def main():
    p = argparse.ArgumentParser(description="Export only used .tex files to text.")
    p.add_argument("-e", "--entry", nargs="+", help="Path(s) to main .tex file(s).")
    p.add_argument("-i", "--ignore-file", default=".texexporterignore",
                   help="Path to ignore-file (gitignore syntax).")
    p.add_argument("-x", "--exclude-folder", action="append", default=[],
                   help="Glob pattern of folders to exclude.")
    p.add_argument("-f", "--exclude-file", action="append", default=[],
                   help="Glob pattern of filenames to exclude.")
    p.add_argument("-d", "--dry-run", action="store_true", help="Show tree & file list only.")
    p.add_argument("-p", "--per-folder", action="store_true", help="One .txt per folder.")
    p.add_argument("-m", "--manifest", choices=["json","yaml"], help="Write manifest file.")
    p.add_argument("-o", "--output", default="export", help="Output directory.")
    args = p.parse_args()

    # entry point selection
    entries = select_entry_points(args)
    ignore_patterns = load_ignore(args.ignore_file)
    visited, deps, bibs, images = collect_dependencies(
        entries, args.exclude_folder + ignore_patterns, args.exclude_file + ignore_patterns
    )

    if args.dry_run:
        print("\nDependency tree:")
        print_tree(deps, entries)
        print("\nFiles to be exported:")
        for f in visited:
            print(" -", f)
        print("\n.bib files:")
        for b in bibs:
            print(" -", b)
        print("\nImages referenced (not dumped):")
        for im in images:
            print(" -", im)
        return

    write_outputs(visited, deps, bibs, images, args)
    print(f"Export complete → {os.path.abspath(args.output)}")

if __name__ == "__main__":
    main()
