# 📄 **LaTeX Exporter for LLM Collaboration**

*An easy-to-use Python script that quickly prepares your LaTeX/Overleaf projects for collaboration with ChatGPT or other LLMs.*

---

**Ever wished you could easily show ChatGPT your entire LaTeX/Overleaf project?**  
This exporter takes your modular `.tex` repository—full of subfiles, includes, and references—and compiles it neatly into a single, structured text file. It ensures your LLM companion has exactly the context it needs, without manually copy-pasting dozens of files.

---

## ✨ **Why You Need This**

- ✅ **Save Time:** Automatically detect all files actively included in your main document.
- ✅ **Stay Organized:** Keep the structure clear with file paths and metadata included.
- ✅ **Control Exactly What You Share:** Easily exclude drafts, old versions, or irrelevant sections.
- ✅ **Perfect for LLM Collaboration:** Your entire project in one neat file, ready to paste directly into ChatGPT.

---

## 🚀 **Quick Start Guide**

### Step 1: **Install**

From your terminal, run:

```bash
git clone https://github.com/thenarfer/latex-to-llm
cd latex-to-llm
pip install -e .
```

*(Optional but recommended: create and activate a Python virtual environment before installing.)*

### Step 2: **Navigate to Your LaTeX Project**

```bash
cd path/to/your/latex/project
```

### Step 3: **Run the Exporter**

Simply type:

```bash
latex-to-llm
```

- Choose your main `.tex` file interactively when prompted.
- The output will appear neatly organized in the `export/` directory.

---

## 🎯 **Example Workflow**

**1. Preview Your Files (Dry-Run)**

Check exactly what will be exported:

```bash
latex-to-llm --dry-run
```

**2. Export the Project with a JSON Manifest**

Generates a single text file and a JSON manifest:

```bash
latex-to-llm --manifest json
```

**3. Exclude Drafts and Export by Folder**

Exclude specific folders (e.g., drafts or old appendices) easily:

```bash
latex-to-llm \
  --exclude-folder "_old/*" \
  --exclude-folder "appendix/drafts/*" \
  --per-folder \
  --manifest yaml
```

---

## ⚙️ **Advanced Configuration**

You can further control what’s included or excluded by creating a `.texexporterignore` file in your LaTeX project root:

```gitignore
# Example .texexporterignore
_old/
drafts/
*.sty
```

---

## 🧩 **All Command-Line Flags**

```
-e, --entry <FILE>         Manually specify main .tex file(s).
-d, --dry-run              Preview dependencies without exporting.
-p, --per-folder           Export to separate text files per folder.
-m, --manifest [json|yaml] Generate a manifest file for automated tooling.
--format [txt|md]          Choose output format (default: txt).
-x, --exclude-folder <PAT> Exclude folders matching the pattern.
-f, --exclude-file <PAT>   Exclude files matching the pattern.
-i, --ignore-file <PATH>   Specify custom .texexporterignore path.
-o, --output <DIR>         Set output directory (default: export/).
-h, --help                 Display detailed help message.
```

---

## 🌟 **Is this Tool Right for You?**

**👍 YES, if you:**

- Regularly collaborate with ChatGPT or other AI assistants on LaTeX projects.
- Have complex documents split across multiple `.tex` files.
- Want to provide clear, structured context to your LLM efficiently.

**👎 NO, if you:**

- Have very simple, single-file LaTeX documents.
- Prefer manual copy-pasting of text.

---

## 📖 **How Does it Work?**

The script intelligently:

- Scans your chosen main file for all referenced subfiles.
- Resolves recursive `\input`, `\include`, and `\subfile` commands.
- Respects your ignore rules.
- Exports cleanly formatted text dumps and manifests.

---

## 📜 **License**

MIT License © 2025 Your Name.  
See [LICENSE](LICENSE) for details.

---

Enjoy collaborating more effectively with your favorite LLMs! 🚀✨
