import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from subprocess import call
from typing import Any

from dirsync import sync

from lndocs._generate_conf import generate_conf, get_variables

HERE = Path(__file__).parent


# https://stackoverflow.com/questions/41129921
def datetime_valid(s: str) -> bool:
    try:
        datetime.fromisoformat(s)
    except ValueError:
        try:  # catch MM-YY dates
            s = "2000-" + s[:5]
            datetime.fromisoformat(s)
        except ValueError:
            return False
    return True


# this here is difficult to test but I hope it's now safe and doesn't
# corrupt html files anymore
def remove_lines_with_db_args(path: Path):
    with open(path) as f:
        content = f.read()
    # now, find the line that contains *db_args and remove it
    previous_line = ""
    found_db_args = False
    for line in content.split("\n")[:1000]:
        if (
            "db_args" in line
            and line.endswith("</dt>")
            and previous_line == '<dt class="sig sig-object py">'
        ):
            found_db_args = True
            break
        previous_line = line
    if found_db_args:
        with open(path, "w") as f:
            f.write(content.replace(previous_line + "\n" + line, ""))


def sluggify_autosummary():
    import sphinx.ext.autosummary
    import sphinx.ext.autosummary.generate

    content = Path(sphinx.ext.autosummary.generate.__file__).read_text()
    original_line = (
        "filename = os.path.join(path, filename_map.get(name, name) + suffix)"
    )
    new_line = (
        "filename = os.path.join(path, filename_map.get(name, name).lower() + suffix)"
    )
    if original_line not in content:
        assert new_line in content
    else:
        Path(sphinx.ext.autosummary.generate.__file__).write_text(
            content.replace(original_line, new_line)
        )

    content = Path(sphinx.ext.autosummary.__file__).read_text()
    original_line = "real_name = filename_map.get(real_name, real_name)"
    new_line = "real_name = filename_map.get(real_name, real_name).lower()"
    if original_line not in content:
        assert new_line in content
    else:
        Path(sphinx.ext.autosummary.__file__).write_text(
            content.replace(original_line, new_line)
        )


ORIG_ANSI = """\
                        elif value == 49:
                            self.bg_color = None"""

NEW_ANSI = '''\
                        elif value == 49:
                            self.bg_color = None
                        elif value == 90:
                            self.fg_color = "Black"
                        elif value == 91:
                            self.fg_color = "Red"
                        elif value == 92:
                            self.fg_color = "Green"
                        elif value == 93:
                            self.fg_color = "Yellow"
                        elif value == 94:
                            self.fg_color = "Blue"
                        elif value == 95:
                            self.fg_color = "Magenta"
                        elif value == 96:
                            self.fg_color = "Cyan"
                        elif value == 97:
                            self.fg_color = "White"
                        elif value == 100:
                            self.bg_color = "Black"
                        elif value == 101:
                            self.bg_color = "Red"
                        elif value == 102:
                            self.bg_color = "Green"
                        elif value == 103:
                            self.bg_color = "Yellow"
                        elif value == 104:
                            self.bg_color = "Blue"
                        elif value == 105:
                            self.bg_color = "Magenta"
                        elif value == 106:
                            self.bg_color = "Cyan"
                        elif value == 107:
                            self.bg_color = "White"'''

ORIG_ANSI_TOKENS = """\
    tokens = {
        "root": [(r"\\x1b\\[([^\\x1b]*)", process), (r"[^\\x1b]+", pygments.token.Text)],
    }"""

NEW_ANSI_TOKENS = """\
    tokens = {
        "root": [
            (r"\\x1b\\[([^\\x1b]*)", process),
            (r"[^\\x1b]+", pygments.token.Text),
            (r"\\x1b", pygments.token.Text),
        ],
    }"""


def additional_ansi_colors():
    import myst_nb.core.lexers

    content = Path(myst_nb.core.lexers.__file__).read_text()
    if NEW_ANSI not in content and ORIG_ANSI in content:
        content = content.replace(ORIG_ANSI, NEW_ANSI)
    if NEW_ANSI_TOKENS not in content and ORIG_ANSI_TOKENS in content:
        content = content.replace(ORIG_ANSI_TOKENS, NEW_ANSI_TOKENS)
    Path(myst_nb.core.lexers.__file__).write_text(content)


def parse_toctree_structure(docs_dir: str) -> list[tuple[str, int]]:
    """Parse the toctree structure from Sphinx documentation to get the correct ordering.

    Returns:
        List of (filename, depth) tuples in toctree order
    """
    docs_path = Path(docs_dir)
    toctree_order: list[Any] = []

    def parse_rst_file(file_path: Path, current_depth: int = 0):
        """Recursively parse RST files for toctree directives."""
        if not file_path.exists():
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return

        # Add the current file to the order
        stem = file_path.stem
        if stem not in [item[0] for item in toctree_order]:  # Avoid duplicates
            toctree_order.append((stem, current_depth))

        # Find toctree directives
        toctree_pattern = r"^\.\. toctree::\s*\n((?:\s+.*\n)*)"
        matches = re.finditer(toctree_pattern, content, re.MULTILINE)

        for match in matches:
            toctree_content = match.group(1)

            # Parse options and entries
            lines = toctree_content.split("\n")
            entries = []

            for line in lines:
                line = line.strip()
                if not line or line.startswith(":"):  # Skip options
                    continue

                # Remove inline titles (format: "title <filename>")
                if "<" in line and line.endswith(">"):
                    line = line.split("<")[1].rstrip(">")

                # Handle different file extensions
                if not line.endswith((".rst", ".md", ".ipynb")):
                    # Try common extensions
                    for ext in [".rst", ".md", ".ipynb"]:
                        if (docs_path / (line + ext)).exists():
                            line = line + ext
                            break

                entries.append(line)

            # Recursively process toctree entries
            for entry in entries:
                # Try to find the actual file with different extensions
                found_file = False

                # First try with common extensions
                for ext in [".rst", ".md", ".ipynb"]:
                    entry_path = docs_path / (entry + ext)
                    if entry_path.exists() and entry_path.is_file():
                        if entry_path.suffix == ".md":
                            parse_md_file(entry_path, current_depth + 1)
                        elif entry_path.suffix == ".ipynb":
                            parse_ipynb_file(entry_path, current_depth + 1)
                        else:
                            parse_rst_file(entry_path, current_depth + 1)
                        found_file = True
                        break

                # If not found, try the entry as-is (in case it already has extension)
                if not found_file:
                    entry_path = docs_path / entry
                    if entry_path.exists() and entry_path.is_file():
                        if entry_path.suffix == ".md":
                            parse_md_file(entry_path, current_depth + 1)
                        elif entry_path.suffix == ".ipynb":
                            parse_ipynb_file(entry_path, current_depth + 1)
                        else:
                            parse_rst_file(entry_path, current_depth + 1)
                        found_file = True
                    elif entry_path.is_dir():
                        # Look for index files in the directory
                        for index_name in ["index.rst", "index.md", "index.ipynb"]:
                            index_path = entry_path / index_name
                            if index_path.exists():
                                if index_path.suffix == ".md":
                                    parse_md_file(index_path, current_depth + 1)
                                elif index_path.suffix == ".ipynb":
                                    parse_ipynb_file(index_path, current_depth + 1)
                                else:
                                    parse_rst_file(index_path, current_depth + 1)
                                found_file = True
                                break

                # If still not found, add to order anyway
                if not found_file:
                    base_name = entry.split(".")[0] if "." in entry else entry
                    if base_name not in [item[0] for item in toctree_order]:
                        toctree_order.append((base_name, current_depth + 1))

    def _parse_myst_toctrees_from_content(content: str, current_depth: int):
        """Parse MyST toctree blocks from markdown-like content."""
        # Matches ```{toctree} followed by optional options, then entries
        toctree_pattern = r"```\{toctree\}([^`]*?)```"
        matches = re.finditer(toctree_pattern, content, re.DOTALL)

        for match in matches:
            full_toctree_content = match.group(1).strip()
            lines = full_toctree_content.split("\n")

            # Skip option lines (starting with :) and empty lines
            entry_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith(":"):
                    continue  # Skip options like :maxdepth:, :hidden:, etc.
                entry_lines.append(line)

            # Process each entry
            for entry in entry_lines:
                entry = entry.strip()
                if not entry:
                    continue

                # Handle inline titles (format: "title <filename>")
                if "<" in entry and entry.endswith(">"):
                    entry = entry.split("<")[1].rstrip(">")

                # Try to find the actual file
                found_file = False

                # First try with common extensions
                for ext in [".md", ".rst", ".ipynb"]:
                    test_path = docs_path / (entry + ext)
                    if test_path.exists() and test_path.is_file():
                        if test_path.suffix == ".md":
                            parse_md_file(test_path, current_depth + 1)
                        elif test_path.suffix == ".ipynb":
                            parse_ipynb_file(test_path, current_depth + 1)
                        else:
                            parse_rst_file(test_path, current_depth + 1)
                        found_file = True
                        break

                # If not found, try the entry as-is (in case it already has extension)
                if not found_file:
                    test_path = docs_path / entry
                    if test_path.exists() and test_path.is_file():
                        if test_path.suffix == ".md":
                            parse_md_file(test_path, current_depth + 1)
                        elif test_path.suffix == ".ipynb":
                            parse_ipynb_file(test_path, current_depth + 1)
                        else:
                            parse_rst_file(test_path, current_depth + 1)
                        found_file = True
                    elif test_path.is_dir():
                        # Look for index files in the directory
                        for index_name in ["index.md", "index.rst", "index.ipynb"]:
                            index_path = test_path / index_name
                            if index_path.exists():
                                if index_name.endswith(".md"):
                                    parse_md_file(index_path, current_depth + 1)
                                elif index_name.endswith(".ipynb"):
                                    parse_ipynb_file(index_path, current_depth + 1)
                                else:
                                    parse_rst_file(index_path, current_depth + 1)
                                found_file = True
                                break

                # If still not found, add to order anyway
                if not found_file:
                    base_name = entry.split(".")[0] if "." in entry else entry
                    if base_name not in [item[0] for item in toctree_order]:
                        toctree_order.append((base_name, current_depth + 1))

    def parse_md_file(file_path: Path, current_depth: int = 0):
        """Parse Markdown files for MyST toctree directives."""
        if not file_path.exists():
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return

        # Add the current file to the order
        stem = file_path.stem
        if stem not in [item[0] for item in toctree_order]:
            toctree_order.append((stem, current_depth))

        _parse_myst_toctrees_from_content(content, current_depth)

    def parse_ipynb_file(file_path: Path, current_depth: int = 0):
        """Parse Jupyter notebooks for MyST toctree directives in markdown cells."""
        if not file_path.exists():
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                notebook = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return

        stem = file_path.stem
        if stem not in [item[0] for item in toctree_order]:
            toctree_order.append((stem, current_depth))

        markdown_cells = []
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") != "markdown":
                continue
            source = cell.get("source", "")
            if isinstance(source, list):
                source = "".join(source)
            markdown_cells.append(source)

        if markdown_cells:
            _parse_myst_toctrees_from_content(
                "\n\n".join(markdown_cells), current_depth
            )

    # Start with index file
    index_files = ["index.rst", "index.md"]
    for index_file_name in index_files:
        index_file = docs_path / index_file_name
        if index_file.exists():
            if index_file_name.endswith(".md"):
                parse_md_file(index_file)
            else:
                parse_rst_file(index_file)
            break
    else:
        print("Warning: No index.rst or index.md found, using alphabetical order")
        # Fallback to all files if no index found
        for file_path in sorted(docs_path.glob("**/*.rst")):
            stem = file_path.stem
            if stem not in [item[0] for item in toctree_order]:
                toctree_order.append((stem, 0))
        for file_path in sorted(docs_path.glob("**/*.md")):
            stem = file_path.stem
            if stem not in [item[0] for item in toctree_order]:
                toctree_order.append((stem, 0))

    return toctree_order


def _extract_document_title(content: str) -> str:
    """Extract the first heading/title from Sphinx text builder output.

    Sphinx uses a line of text followed by a line of =, *, -, etc. as headings.
    The first such heading is typically the document title.
    """
    lines = content.strip().split("\n")
    for i in range(len(lines) - 1):
        line = lines[i].strip()
        if not line:
            continue
        next_line = lines[i + 1].strip()
        if re.match(r"^[=*\-~^]{3,}$", next_line):
            return line
    # Fallback: first non-empty line
    for line in lines:
        if line.strip():
            return line.strip()
    return ""


def _is_toc_only(content: str) -> bool:
    """True if content has no paragraph, only a bullet/list (TOC-only page)."""
    lines = content.strip().split("\n")
    # Remove first heading (title line + underline) if present
    i = 0
    if len(lines) >= 2:
        for i in range(len(lines) - 1):
            line = lines[i].strip()
            if not line:
                continue
            next_line = lines[i + 1].strip()
            if re.match(r"^[=*\-~^]{3,}$", next_line):
                i += 2
                break
        else:
            i = 0
    remaining = "\n".join(lines[i:]).strip()
    if not remaining:
        return True
    # Any non-empty line that isn't a list item -> has a paragraph
    list_item = re.compile(r"^\s*(\*|\-|•|\d+\.)\s")
    for line in remaining.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        if not list_item.match(line):
            return False
    return True


def _extract_myst_toctree_group_starts(content: str) -> dict[str, str]:
    """Map first entry of a toctree block to that block's caption."""
    group_starts: dict[str, str] = {}
    toctree_pattern = r"```\{toctree\}([^`]*?)```"
    matches = re.finditer(toctree_pattern, content, re.DOTALL)

    for match in matches:
        caption = ""
        first_entry = ""
        for raw_line in match.group(1).split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(":caption:"):
                caption = line.split(":caption:", 1)[1].strip().strip("\"'")
                continue
            if line.startswith(":"):
                continue
            if not first_entry:
                entry = line
                if "<" in entry and entry.endswith(">"):
                    entry = entry.split("<", 1)[1].rstrip(">").strip()
                entry = entry.lstrip("/")
                for ext in (".md", ".rst", ".ipynb", ".txt"):
                    if entry.endswith(ext):
                        entry = entry[: -len(ext)]
                        break
                first_entry = entry
                break

        if caption and first_entry:
            group_starts[first_entry] = caption

    return group_starts


def generate_llms_txt(
    docs_dir: str,
    site: str,
    output_filename: str,
    skip_patterns: list[str] | None = None,
    project_name: str = "",
    summary: str = "",
):
    """Generate llms.txt and per-page .md files in _build/html/, following the llms.txt spec.

    Uses Sphinx text builder, copies each page to html/*.md, and writes one llms.txt
    with H1, blockquote, H2 file list using relative .md links (e.g. "query-search.md - Title").

    Args:
        docs_dir: Source documentation directory (e.g., "_docs_tmp")
        site: Main build directory (e.g., "_build/html")
        output_filename: Name of the llms.txt file (e.g. "llms.txt")
        skip_patterns: List of patterns to skip files whose stem contains any of these
        project_name: H1 title for llms.txt
        summary: Optional one-sentence blockquote summary
    """
    if skip_patterns is None:
        skip_patterns = []
    build_dir = Path(site).parent  # Get _build directory
    text_build_dir = build_dir / "text"
    html_dir = build_dir / "html"

    # Build documentation as text using Sphinx text builder
    print("Building documentation in text format...")
    os.environ["LNDOCS_SHOW_INHERITED_MEMBERS"] = "false"
    build_status = call(f"sphinx-build -b text {docs_dir} {text_build_dir}", shell=True)
    del os.environ["LNDOCS_SHOW_INHERITED_MEMBERS"]

    if build_status != 0:
        print("Error: Failed to build text documentation")
        return build_status

    # Get the toctree order
    print("Parsing toctree structure...")
    toctree_order = parse_toctree_structure(docs_dir)

    # Collect all .txt files from the text build
    all_txt_files = {f.stem: f for f in text_build_dir.glob("**/*.txt")}

    if not all_txt_files:
        print("Warning: No text files found in build output")
        return 1

    # Order files according to toctree structure
    ordered_files = []
    found_files = set()

    print("Ordering files according to toctree structure:")
    for file_stem, depth in toctree_order:
        if file_stem in all_txt_files:
            # Check if this file should be skipped
            should_skip = any(pattern in file_stem for pattern in skip_patterns)
            if should_skip:
                print(f"  {'  ' * depth}× {file_stem} (skipped)")
                continue

            ordered_files.append((all_txt_files[file_stem], depth))
            found_files.add(file_stem)
            print(f"  {'  ' * depth}- {file_stem}")

    # Add any remaining files that weren't in the toctree
    remaining_files = []
    for stem, f in all_txt_files.items():
        if stem not in found_files:
            # Check if this file should be skipped
            should_skip = any(pattern in stem for pattern in skip_patterns)
            if not should_skip:
                remaining_files.append((f, 0))

    remaining_files.sort(key=lambda x: x[0].stem)
    if remaining_files:
        print(f"Additional files not in toctree: {len(remaining_files)}")
        for f, _ in remaining_files:
            print(f"  - {f.stem}")
        ordered_files.extend(remaining_files)

    # Copy each .txt to _build/html/*.md (paired markdown pages per llms.txt spec)
    html_dir.mkdir(parents=True, exist_ok=True)
    for txt_file, depth in ordered_files:
        try:
            rel_path = txt_file.relative_to(text_build_dir)
            md_path = html_dir / rel_path.with_suffix(".md")
            md_path.parent.mkdir(parents=True, exist_ok=True)
            with open(txt_file, encoding="utf-8") as infile:
                content = infile.read().strip()
            if content:
                cleaned = clean_text_to_markdown(content, base_depth=depth)
                with open(md_path, "w", encoding="utf-8") as fp:
                    fp.write(cleaned)
        except Exception as e:
            print(f"Warning: Could not write {txt_file} to .md: {e}")

    # Write llms.txt (H1, blockquote, H2 file list with relative .md - title)
    output_path = html_dir / output_filename

    print(f"Writing {output_path}...")

    with open(output_path, "w", encoding="utf-8") as outfile:
        # H1 (required per llms.txt spec)
        title = project_name or "Documentation"
        outfile.write(f"# {title}\n\n")

        # Blockquote summary
        if summary:
            outfile.write(f"> {summary}\n\n")

        # Full list of all pages; top-level entries (depth 1) are H2 sections, index excluded.
        # Pages with "." in path (e.g. lamindb.artifact) are lumped under "API Reference" (api).
        sections_order: list[tuple[str, str]] = []  # (section_key, section_title)
        entries: list[
            tuple[str, str, str, int]
        ] = []  # (page_path, doc_title, section_key, depth)
        current_section_key: str | None = None
        current_section_title = ""

        for txt_file, depth in ordered_files:
            rel_path = txt_file.relative_to(text_build_dir)
            page_path = rel_path.with_suffix("").as_posix()
            if page_path == "index":
                continue
            try:
                with open(txt_file, encoding="utf-8") as infile:
                    content = infile.read().strip()
            except Exception:
                continue
            doc_title = re.sub(
                r"\s*\[image:[^\]]*\]\[image\]", "", _extract_document_title(content)
            ).strip()
            section_key = current_section_key
            if depth == 1:
                current_section_key = page_path
                current_section_title = doc_title or page_path
                if not any(s[0] == current_section_key for s in sections_order):
                    sections_order.append((current_section_key, current_section_title))
                if _is_toc_only(content):
                    continue
                section_key = (
                    current_section_key  # this page belongs to its own section
                )
            elif "." in page_path:
                section_key = "api"
                if not any(s[0] == "api" for s in sections_order):
                    sections_order.append(("api", "API Reference"))
            entries.append((page_path, doc_title, section_key or "", depth))

        guide_group_starts: dict[str, str] = {}
        guide_doc = Path(docs_dir) / "guide.md"
        if guide_doc.exists():
            try:
                guide_content = guide_doc.read_text(encoding="utf-8")
                guide_group_starts = _extract_myst_toctree_group_starts(guide_content)
            except Exception:
                guide_group_starts = {}

        first_section = True
        for section_key, section_title in sections_order:
            section_entries = [e for e in entries if e[2] == section_key]
            if not section_entries:
                continue
            if not first_section:
                outfile.write("\n")
            outfile.write(f"## {section_title}\n\n")
            first_section = False
            for page_path, doc_title, sk, depth in section_entries:
                if sk == "guide" and page_path in guide_group_starts:
                    outfile.write(f"\n### {guide_group_starts[page_path]}\n\n")
                if sk == "api" and "." in page_path:
                    indent = "  "
                else:
                    indent = "  " * (depth - 1) if depth >= 1 else ""
                if (
                    doc_title
                    and len(doc_title) >= 2
                    and doc_title[0] == '"'
                    and doc_title[-1] == '"'
                ):
                    doc_title = doc_title[1:-1]
                rel_link = f"{page_path}.md"
                line = (
                    f"- {rel_link} - {doc_title}\n" if doc_title else f"- {rel_link}\n"
                )
                outfile.write(f"{indent}{line}")

    print(f"✓ Per-page .md files written to: {html_dir}")
    print(f"✓ llms.txt saved to: {output_path}")

    # Show file statistics
    total_size = sum(f.stat().st_size for f, _ in ordered_files if f.exists())
    combined_size = output_path.stat().st_size

    # Read the combined file to get content statistics
    with open(output_path, encoding="utf-8") as f:  # type: ignore
        content = f.read()  # type: ignore

    # Calculate metrics
    char_count = len(content)
    word_count = len(content.split())

    # Estimate tokens using different methods
    tokens_simple = char_count / 4
    tokens_word_based = word_count * 0.75
    tokens_technical = word_count * 0.85

    print("\n📊 Content Statistics:")
    print(f"  Characters: {char_count:,}")
    print(f"  Words: {word_count:,}")
    print(f"  Estimated tokens (simple): {tokens_simple:,.0f}")
    print(f"  Estimated tokens (word-based): {tokens_word_based:,.0f}")
    print(f"  Estimated tokens (technical): {tokens_technical:,.0f}")
    print(
        "  Average token estimate:"
        f" {(tokens_simple + tokens_word_based + tokens_technical) / 3:,.0f}"
    )

    print("\n📁 File Statistics:")
    print(f"  Individual files total: {total_size / 1024 / 1024:.1f} MB")
    print(f"  Combined file size: {combined_size / 1024 / 1024:.1f} MB")
    print(f"  Files processed: {len(ordered_files)}")
    print(f"  Toctree entries found: {len(toctree_order)}")

    return 0


def clean_text_to_markdown(content: str, base_depth: int = 0) -> str:
    """Convert Sphinx text builder output to clean markdown.

    Removes excessive dashes and converts to proper markdown syntax.

    Args:
        content: Raw text content from Sphinx
        base_depth: Base depth for heading adjustment (from toctree)
    """
    lines = content.split("\n")
    cleaned_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip empty lines (will be preserved)
        if not line.strip():
            cleaned_lines.append(line)
            i += 1
            continue

        # Check for heading patterns (text followed by === or ---)
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if re.match(r"^[=*\-~^]{3,}$", next_line.strip()):
                # This is a heading - convert to markdown with proper depth
                heading_char = next_line.strip()[0]

                # Determine heading level based on Sphinx conventions
                # = is usually h1, * is h2, - is h3, ~ is h4, ^ is h5
                sphinx_level = {"=": 1, "*": 2, "-": 3, "~": 4, "^": 5}.get(
                    heading_char, 2
                )

                # Adjust level based on toctree depth
                # Start at h1 for top-level pages (no main title reserved)
                final_level = min(sphinx_level + base_depth, 6)

                heading_prefix = "#" * final_level
                cleaned_lines.append(f"{heading_prefix} {line.strip()}")
                i += 2  # Skip both the heading and underline
                continue

        # Clean up excessive dashes used for horizontal rules (10+ dashes)
        if re.match(r"^-{10,}$", line.strip()):
            cleaned_lines.append("---")
            i += 1
            continue

        # Clean up excessive equals signs (10+ equals)
        if re.match(r"^={10,}$", line.strip()):
            cleaned_lines.append("---")
            i += 1
            continue

        # Clean up box-drawing characters and convert to markdown tables
        if "|" in line or re.match(r"^[\s\-\+]+$", line):
            line = clean_table_line(line)

        # Clean up excessive whitespace
        line = re.sub(r" {3,}", " ", line)

        cleaned_lines.append(line)
        i += 1

    # Join lines and clean up multiple consecutive blank lines
    content = "\n".join(cleaned_lines)
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def clean_table_line(line: str) -> str:
    """Clean up table formatting to be markdown-friendly.

    Converts ASCII table borders to markdown table syntax.
    """
    # If line is mostly dashes, pipes, and plus signs, it's likely a table border
    if re.match(r"^[\s\-\+\|]+$", line):
        # Count the number of columns based on pipes or plus signs
        column_indicators = line.count("|") + line.count("+")
        if column_indicators > 1:
            # Create a clean markdown table separator
            # Subtract 1 because markdown table separators have n-1 pipes for n columns
            return "|" + " --- |" * (column_indicators - 1)
        else:
            # Single column or not a table, convert to horizontal rule
            return "---"

    # If line has pipes, clean up spacing for table rows
    if "|" in line:
        # Split by pipes and clean each cell
        parts = line.split("|")
        cleaned_parts = []

        for part in parts:
            # Clean up whitespace and remove box-drawing characters
            cleaned_part = re.sub(r"[┌┐└┘├┤┬┴┼─│]", "", part)
            cleaned_part = cleaned_part.strip()
            cleaned_parts.append(cleaned_part)

        # Filter out empty parts at the beginning and end
        while cleaned_parts and not cleaned_parts[0]:
            cleaned_parts.pop(0)
        while cleaned_parts and not cleaned_parts[-1]:
            cleaned_parts.pop()

        if cleaned_parts:
            return "| " + " | ".join(cleaned_parts) + " |"

    return line


def strip_notebook_outputs(directory="."):
    """Simple function to strip outputs from all notebooks in directory."""
    notebook_files = list(Path(directory).rglob("*.ipynb"))

    if not notebook_files:
        print("No notebooks found")
        return

    for nb_file in notebook_files:
        subprocess.run(["nbstripout", str(nb_file)])

    print(f"Processed {len(notebook_files)} notebooks")


def strip_bash_from_notebooks(directory="."):
    """Strip %%bash magic from notebooks before rendering."""
    try:
        import nbformat
    except ImportError:
        print("nbformat not installed, skipping bash stripping")
        return

    notebook_files = list(Path(directory).rglob("*.ipynb"))
    for nb_path in notebook_files:
        if ".ipynb_checkpoints" in str(nb_path):
            continue
        try:
            nb = nbformat.read(nb_path, as_version=4)
            modified = False
            for cell in nb.cells:
                if cell.cell_type == "code" and cell.source.startswith("%%bash"):
                    if cell.source.startswith("%%bash\n"):
                        cell.source = cell.source.replace("%%bash\n", "", 1)
                    else:
                        cell.source = cell.source.replace("%%bash", "", 1)
                    modified = True
            if modified:
                nbformat.write(nb, nb_path)
        except Exception as e:
            print(f"Error processing {nb_path} for bash stripping: {e}")


def main():
    parser = argparse.ArgumentParser(description="Build Lamin docs site.")
    aa = parser.add_argument
    aa("--show", action="store_true", help="launch server & show")
    aa("--docs", type=str, default="docs", help="directory with docs sources")
    aa("--site", type=str, default="_build/html", help="output directory")
    aa("--live", action="store_true", help="use autobuild")
    aa("--strict", action="store_true", help="error upon warning")
    aa("--blog", action="store_true", help="enable blog layout styling")
    aa(
        "--error-on-index",
        action="store_true",
        help=(
            "error if encountering nested index files (needed for composite Next.js"
            " site)"
        ),
    )
    aa("--strip-prefix", action="store_true", help="error upon warning")
    aa("--clean", action="store_true", help="clean build directory")
    aa("--format", type=str, default="html", help="provide 'text' or 'html'")
    args = parser.parse_args()

    if args.clean:
        paths_to_delete = ["lamin_sphinx", "_docs_tmp", "_build"]
        for path in paths_to_delete:
            path = Path(f"{Path.cwd()}/{path}")
            print(f"Removing directory: {path}")
            import shutil

            if path.exists():
                shutil.rmtree(path)

        return

    if not Path(args.docs).exists():
        sys.exit(
            f"The source directory {args.docs} does not exist! Change to repo root!"
        )

    sync(str(HERE / "lamin_sphinx"), "./lamin_sphinx", "sync", create=True, ctime=True)
    # check whether we need to generate the conf.py for Sphinx
    # input for it is the lamin-project.yaml file
    generate_conf_check = False
    conf_file = Path(args.docs) / "conf.py"
    if not conf_file.exists():
        generate_conf_check = True
    else:
        with open(conf_file) as f:
            first_line = f.readline()
        if first_line == "# auto-generated by lndocs\n":
            generate_conf_check = True
    if generate_conf_check:
        variables = generate_conf(args.docs)
    else:
        variables = get_variables()

    if args.live:
        build_command = "sphinx-autobuild"
    else:
        build_command = "sphinx-build"

    docs_dir = Path(f"_{args.docs}_tmp/")
    sync(
        args.docs,
        docs_dir,
        "sync",
        create=True,
    )
    for path in docs_dir.glob("**/*"):
        if args.error_on_index:
            if path.name == "index.md" and not path == docs_dir / "index.md":
                raise ValueError(f"Please replace {path} with {path.parent}.md")
        if path.suffix not in {".md", ".ipynb"}:
            continue
        if ".ipynb_checkpoints/" in str(path):
            continue
        if path.suffix == ".ipynb" and args.strip_prefix:
            # test whether prefix is capital letter or digit and if so,
            # strip them for pretty & persistent urls
            # we need the prefixes
            # on notebooks to allow users to navigate downloaded notebooks
            # that should display in order in a file browser
            # ignore dates!
            prefix = path.stem[0]
            if not datetime_valid(path.stem[:10]) and (
                prefix.isdigit() or prefix.isupper() and "-" in path.stem
            ):
                new_stem = "-".join(path.stem.split("-")[1:])
                # path.with_stem() is >3.9
                new_path = path.with_name(f"{new_stem}{path.suffix}")
                path.rename(new_path)

    strip_bash_from_notebooks(docs_dir)

    sluggify_autosummary()
    additional_ansi_colors()

    if args.strict:
        os.environ["LNDOCS_WARNING_IS_ERROR"] = "1"
    if args.blog:
        os.environ["LNDOCS_BLOG"] = "1"
    if args.format == "html":
        build_status = call(
            f"{build_command} {docs_dir} {args.site}", shell=True
        )  # to debug, add -vv
    elif args.format == "text":
        filename = "llms.txt"
        skip_patterns = [
            "wetlab.",
            "clinicore.",
            "lamindb.base",
            "lamindb.core",
            "lamindb.models",
            "lamindb.curators.core",
            "lamindb.core.loaders",
            "lamindb.base.types",
            "lamindb.core.storage",
            "lamindb.errors",
            "lamindb.setup.errors",
            "bionty.base",
            "bionty.core",
            "lamindb.setup",
            "bionty.celltype",
            "bionty.developmentalstage",
            "bionty.disease",
            "bionty.ethnicity",
            "bionty.experimentalfactor",
            "bionty.gene",
            "bionty.organism",
            "bionty.pathway",
            "bionty.phenotype",
            "bionty.protein",
            "bionty.settings",
            "bionty.source",
            "bionty.tissue",
        ]
        strip_notebook_outputs(str(docs_dir))
        build_status = generate_llms_txt(
            str(docs_dir),
            args.site,
            filename,
            skip_patterns=skip_patterns,
            project_name=variables.get("project_name", "Documentation"),
            summary=variables.get("summary", ""),
        )
        if build_status != 0:
            print("Warning: Text export failed")
    else:
        raise ValueError(f"Unknown format: {args.format}. Use 'html' or 'text'.")
    if args.strict:
        del os.environ["LNDOCS_WARNING_IS_ERROR"]
    if args.blog:
        os.environ.pop("LNDOCS_BLOG", None)

    if args.format == "html":
        # remove db_args from registries documentation
        for package_name in [
            "lamindb",
            "bionty",
            "omop",
            "lrex",
            "wetlab",
        ]:
            for generated in Path(docs_dir).glob(f"{package_name}.*.rst"):
                remove_lines_with_db_args(
                    Path(args.site) / generated.with_suffix(".html").name
                )

    if not args.show:
        return build_status
    else:
        if build_status == 0:
            call("python -m http.server", shell=True, cwd="./_build/html")
