import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from subprocess import call
from typing import Any

from dirsync import sync

from lndocs._generate_conf import generate_conf, get_variables

HERE = Path(__file__).parent


# https://stackoverflow.com/questions/41129921
def datetime_valid(s: str):
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
                        elif value == 92:  # Special case for bright green
                            self.fg_color = "Green"
                        elif value == 94:  # Special case for bright blue
                            self.fg_color = "Blue"'''


def additional_ansi_colors():
    import myst_nb.core.lexers

    content = Path(myst_nb.core.lexers.__file__).read_text()
    if NEW_ANSI not in content:
        assert ORIG_ANSI in content
        Path(myst_nb.core.lexers.__file__).write_text(
            content.replace(ORIG_ANSI, NEW_ANSI)
        )


def parse_toctree_structure(docs_dir: str) -> list[tuple[str, int]]:
    """
    Parse the toctree structure from Sphinx documentation to get the correct ordering.

    Returns:
        List of (filename, depth) tuples in toctree order
    """
    docs_path = Path(docs_dir)
    toctree_order: list[Any] = []

    def parse_rst_file(file_path: Path, current_depth: int = 0):
        """Recursively parse RST files for toctree directives"""
        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
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
                        parse_rst_file(entry_path, current_depth + 1)
                        found_file = True
                        break

                # If not found, try the entry as-is (in case it already has extension)
                if not found_file:
                    entry_path = docs_path / entry
                    if entry_path.exists() and entry_path.is_file():
                        parse_rst_file(entry_path, current_depth + 1)
                        found_file = True
                    elif entry_path.is_dir():
                        # Look for index files in the directory
                        for index_name in ["index.rst", "index.md", "index.ipynb"]:
                            index_path = entry_path / index_name
                            if index_path.exists():
                                parse_rst_file(index_path, current_depth + 1)
                                found_file = True
                                break

                # If still not found, add to order anyway
                if not found_file:
                    base_name = entry.split(".")[0] if "." in entry else entry
                    if base_name not in [item[0] for item in toctree_order]:
                        toctree_order.append((base_name, current_depth + 1))

    def parse_md_file(file_path: Path, current_depth: int = 0):
        """Parse Markdown files for MyST toctree directives"""
        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return

        # Add the current file to the order
        stem = file_path.stem
        if stem not in [item[0] for item in toctree_order]:
            toctree_order.append((stem, current_depth))

        # Find MyST toctree directives - more flexible pattern
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
                                else:
                                    parse_rst_file(index_path, current_depth + 1)
                                found_file = True
                                break

                # If still not found, add to order anyway
                if not found_file:
                    base_name = entry.split(".")[0] if "." in entry else entry
                    if base_name not in [item[0] for item in toctree_order]:
                        toctree_order.append((base_name, current_depth + 1))

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


def generate_single_markdown_file(
    docs_dir: str, site: str, output_filename: str, skip_patterns: list[str] = None
):
    """
    Generate a single markdown file containing the entire documentation.
    Uses Sphinx text builder and converts output to clean markdown.
    Follows the toctree structure for proper ordering.

    Args:
        docs_dir: Source documentation directory (e.g., "_docs_tmp")
        site: Main build directory (e.g., "_build/html")
        output_filename: Name of the output markdown file
        skip_patterns: List of patterns to skip files whose stem
            contains any of these patterns
    """
    if skip_patterns is None:
        skip_patterns = []
    build_dir = Path(site).parent  # Get _build directory
    text_build_dir = build_dir / "text"

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

    # Combine all text files into one markdown file
    output_path = build_dir / f"html/{output_filename}"

    print(f"Combining {len(ordered_files)} text files into {output_path}...")

    with open(output_path, "w", encoding="utf-8") as outfile:
        # Add table of contents with hierarchical structure
        outfile.write("## Table of Contents\n\n")
        for txt_file, depth in ordered_files:
            rel_path = txt_file.relative_to(text_build_dir)
            indent = "  " * depth
            # Simple list without links
            outfile.write(f"{indent}- {rel_path.stem}\n")
        outfile.write("\n")

        # Add content from each file in toctree order
        for txt_file, depth in ordered_files:
            try:
                with open(txt_file, "r", encoding="utf-8") as infile:
                    content = infile.read().strip()

                    if content:  # Only include non-empty files
                        rel_path = txt_file.relative_to(text_build_dir)

                        # Add invisible page marker for reference
                        outfile.write(f"\n<!-- Page: {rel_path.stem} -->\n\n")

                        # Clean up the content to be markdown-friendly
                        # No page separator, content flows directly
                        cleaned_content = clean_text_to_markdown(
                            content, base_depth=depth
                        )

                        # Add content
                        outfile.write(cleaned_content)
                        outfile.write("\n\n")

            except Exception as e:
                print(f"Warning: Could not read {txt_file}: {e}")
                continue

    print(f"✓ Individual text files available in: {text_build_dir}")
    print(f"✓ Complete documentation saved to: {output_path}")

    # Show file statistics
    total_size = sum(f.stat().st_size for f, _ in ordered_files if f.exists())
    combined_size = output_path.stat().st_size

    # Read the combined file to get content statistics
    with open(output_path, "r", encoding="utf-8") as f:  # type: ignore
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
    """
    Convert Sphinx text builder output to clean markdown.
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
    """
    Clean up table formatting to be markdown-friendly.
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


def main():
    parser = argparse.ArgumentParser(description="Build Lamin docs site.")
    aa = parser.add_argument
    aa("--show", action="store_true", help="launch server & show")
    aa("--docs", type=str, default="docs", help="directory with docs sources")
    aa("--site", type=str, default="_build/html", help="output directory")
    aa("--live", action="store_true", help="use autobuild")
    aa("--strict", action="store_true", help="error upon warning")
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
        paths_to_delete = ["lamin_sphinx", "_docs_tmp"]
        for path in paths_to_delete:
            path = Path(f"{os.getcwd()}/{path}")
            print(f"Removing directory: {path}")
            import shutil

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

    sluggify_autosummary()
    additional_ansi_colors()

    if args.strict:
        os.environ["LNDOCS_WARNING_IS_ERROR"] = "1"
    if args.format == "html":
        build_status = call(
            f"{build_command} {docs_dir} {args.site}", shell=True
        )  # to debug, add -vv
    elif args.format == "text":
        filename = f"{variables['repository_name']}.md"
        if filename == "lamin-docs.md":
            filename = "summary.md"
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
        build_status = generate_single_markdown_file(
            str(docs_dir), args.site, filename, skip_patterns=skip_patterns
        )
        if build_status != 0:
            print("Warning: Text export failed")
    else:
        raise ValueError(f"Unknown format: {args.format}. Use 'html' or 'text'.")
    if args.strict:
        del os.environ["LNDOCS_WARNING_IS_ERROR"]

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
