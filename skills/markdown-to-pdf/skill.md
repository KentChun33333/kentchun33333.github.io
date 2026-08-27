# Markdown-to-PDF Conversion Skill

> **Audience**: Candidates · Job Seekers · Designers · Engineers  
> **Purpose**: Convert Markdown documents (especially resumes) into clean, professional, print-ready PDF files with elegant typography, structured layouts, and robust page-break safety.

This skill automates the compilation of Markdown documents into PDFs using a local Playwright rendering pipeline.

---

## Core Principles

1. **Clean Typography**: We load Google Font `Inter` or standard system-ui sans-serif fonts. Text color is charcoal (`#2d3748`) instead of pure black for a softer, premium appearance.
2. **Structural Formatting**: 
   - Sections (e.g., Experience, Education, Achievements) are elevated to clear section headers.
   - Job roles and dates are right-aligned to save vertical space and create clean grid alignment.
3. **Print-Safety (A4 Page Breaks)**: Keep margins tight (`12mm` top/bottom, `15mm` left/right) and apply custom CSS rules preventing headers or job titles from breaking awkwardly across pages (`page-break-after: avoid`).

---

## Usage Guidelines

The Python script `convert.py` is included in this skillset. It requires `playwright` and `markdown` libraries to run.

### Setup Dependencies
Before running, ensure python dependencies are installed:
```bash
pip3 install playwright markdown
playwright install chromium
```

### Run Commands

To convert a single markdown file:
```bash
python3 convert.py <input_file.md> [output_file.pdf]
```

To convert all markdown files in a directory:
```bash
python3 convert.py --all [directory_path]
```

---

## Quality Gates

Before submitting generated PDFs:
- [ ] Verify that no text wraps awkwardly or overflows margins.
- [ ] Confirm dates are aligned on the right margin.
- [ ] Ensure that page breaks do not separate job headers from their underlying bullet points.
- [ ] Validate that text size (12.5px body, 26px main name) reads comfortably in print.
