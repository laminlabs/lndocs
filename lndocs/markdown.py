"""Sphinx builder that writes one markdown file per page from the doctree."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from docutils import nodes  # type: ignore
from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

logger = logging.getLogger(__name__)


def _language(node: nodes.literal_block) -> str:
    language = node.get("language") or ""
    if language:
        return str(language)
    for class_name in node.get("classes") or []:
        if class_name.startswith("highlight-"):
            return class_name.removeprefix("highlight-")
        if class_name not in {"code", "literal-block", "code-block"}:
            return str(class_name)
    return ""


def _fence_for(code: str) -> str:
    fence = "```"
    while fence in code:
        fence += "`"
    return fence


def _is_design(node: nodes.Node, name: str) -> bool:
    try:
        return node.get("design_component") == name
    except AttributeError:
        return False


class MarkdownTranslator(nodes.NodeVisitor):
    """Render a resolved doctree as markdown, keeping fenced code."""

    def __init__(self, document: nodes.document, builder: MarkdownBuilder) -> None:
        super().__init__(document)
        self.builder = builder
        self.body: list[str] = []
        self._section_level = 0
        # None marks a bullet list. A one-item list is the enumerated counter.
        self._list_stack: list[list[int] | None] = []

    def astext(self) -> str:
        text = "".join(self.body)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"

    def unknown_visit(self, node: nodes.Node) -> None:
        return None

    def unknown_departure(self, node: nodes.Node) -> None:
        return None

    def visit_Text(self, node: nodes.Text) -> None:
        self.body.append(node.astext())

    def depart_Text(self, node: nodes.Text) -> None:
        return None

    def visit_comment(self, node: nodes.comment) -> None:
        raise nodes.SkipNode

    def visit_target(self, node: nodes.target) -> None:
        raise nodes.SkipNode

    def visit_substitution_definition(
        self, node: nodes.substitution_definition
    ) -> None:
        raise nodes.SkipNode

    def visit_system_message(self, node: nodes.system_message) -> None:
        raise nodes.SkipNode

    def visit_index(self, node: nodes.Element) -> None:
        raise nodes.SkipNode

    def visit_raw(self, node: nodes.raw) -> None:
        if node.get("format") == "html":
            raise nodes.SkipNode
        self.body.append(node.astext())
        raise nodes.SkipNode

    def visit_section(self, node: nodes.section) -> None:
        self._section_level += 1

    def depart_section(self, node: nodes.section) -> None:
        self._section_level -= 1

    def visit_title(self, node: nodes.title) -> None:
        if isinstance(node.parent, nodes.section):
            level = max(self._section_level, 1)
        else:
            level = 3
        self.body.append(f"\n{'#' * min(level, 6)} ")

    def depart_title(self, node: nodes.title) -> None:
        self.body.append("\n\n")

    def visit_subtitle(self, node: nodes.subtitle) -> None:
        self.body.append("\n### ")

    def depart_subtitle(self, node: nodes.subtitle) -> None:
        self.body.append("\n\n")

    def visit_rubric(self, node: nodes.rubric) -> None:
        self.body.append(f"\n**{node.astext()}**\n\n")
        raise nodes.SkipNode

    def visit_paragraph(self, node: nodes.paragraph) -> None:
        if self.body and self.body[-1].endswith(" "):
            return
        self.body.append("\n")

    def depart_paragraph(self, node: nodes.paragraph) -> None:
        self.body.append("\n")

    def visit_emphasis(self, node: nodes.emphasis) -> None:
        self.body.append("*")

    def depart_emphasis(self, node: nodes.emphasis) -> None:
        self.body.append("*")

    def visit_strong(self, node: nodes.strong) -> None:
        self.body.append("**")

    def depart_strong(self, node: nodes.strong) -> None:
        self.body.append("**")

    def visit_literal(self, node: nodes.literal) -> None:
        self.body.append(f"`{node.astext()}`")
        raise nodes.SkipNode

    def visit_literal_block(self, node: nodes.literal_block) -> None:
        self._append_fence(_language(node), node.rawsource or node.astext())
        raise nodes.SkipNode

    def visit_doctest_block(self, node: nodes.doctest_block) -> None:
        self._append_fence("python", node.rawsource or node.astext())
        raise nodes.SkipNode

    def _append_fence(self, language: str, code: str) -> None:
        code = code.replace("\r\n", "\n").strip("\n")
        fence = _fence_for(code)
        self.body.append(f"\n{fence}{language}\n{code}\n{fence}\n\n")

    def visit_reference(self, node: nodes.reference) -> None:
        uri = node.get("refuri") or ""
        if uri:
            uri = uri.replace(".html", ".md")
            self.body.append(f"[{node.astext()}]({uri})")
            raise nodes.SkipNode
        refid = node.get("refid")
        if refid:
            self.body.append(f"[{node.astext()}](#{refid})")
            raise nodes.SkipNode

    def visit_bullet_list(self, node: nodes.bullet_list) -> None:
        self._list_stack.append(None)
        self.body.append("\n")

    def depart_bullet_list(self, node: nodes.bullet_list) -> None:
        self._list_stack.pop()
        self.body.append("\n")

    def visit_enumerated_list(self, node: nodes.enumerated_list) -> None:
        self._list_stack.append([0])
        self.body.append("\n")

    def depart_enumerated_list(self, node: nodes.enumerated_list) -> None:
        self._list_stack.pop()
        self.body.append("\n")

    def visit_list_item(self, node: nodes.list_item) -> None:
        indent = "  " * max(len(self._list_stack) - 1, 0)
        top = self._list_stack[-1] if self._list_stack else None
        if top is None:
            marker = "-"
        else:
            top[0] += 1
            marker = f"{top[0]}."
        self.body.append(f"{indent}{marker} ")

    def depart_list_item(self, node: nodes.list_item) -> None:
        if not self.body or not self.body[-1].endswith("\n"):
            self.body.append("\n")

    def visit_container(self, node: nodes.container) -> None:
        if _is_design(node, "dropdown"):
            self._render_dropdown(node)
            raise nodes.SkipNode
        if _is_design(node, "tab-set"):
            self._render_tab_set(node)
            raise nodes.SkipNode

    def _render_dropdown(self, node: nodes.container) -> None:
        children = list(node.children)
        if children and isinstance(children[0], nodes.rubric):
            title = children[0].astext().strip()
            children = children[1:]
            if title:
                self.body.append(f"\n**{title}**\n\n")
        for child in children:
            child.walkabout(self)

    def _render_tab_set(self, node: nodes.container) -> None:
        for child in node.children:
            if not _is_design(child, "tab-item"):
                child.walkabout(self)
                continue
            label = ""
            content: list[nodes.Node] = []
            for part in child.children:
                if isinstance(part, nodes.rubric) and not label:
                    label = part.astext().strip()
                else:
                    content.append(part)
            if label:
                self.body.append(f"\n**{label}**\n\n")
            for part in content:
                part.walkabout(self)

    def visit_desc_signature(self, node: nodes.Element) -> None:
        signature = " ".join(node.astext().split())
        if signature:
            self._append_fence("python", signature)
        raise nodes.SkipNode

    def visit_field(self, node: nodes.field) -> None:
        name = ""
        body = None
        for child in node.children:
            if isinstance(child, nodes.field_name):
                name = child.astext()
            elif isinstance(child, nodes.field_body):
                body = child
        if name:
            self.body.append(f"\n**{name}**\n\n")
        if body is not None:
            body.walkabout(self)
        raise nodes.SkipNode

    def visit_term(self, node: nodes.term) -> None:
        self.body.append(f"\n**{node.astext()}**\n\n")
        raise nodes.SkipNode

    def visit_image(self, node: nodes.image) -> None:
        alt = node.get("alt") or ""
        uri = node.get("uri") or ""
        self.body.append(f"\n![{alt}]({uri})\n\n")
        raise nodes.SkipNode

    def visit_figure(self, node: nodes.figure) -> None:
        self.body.append("\n")

    def depart_figure(self, node: nodes.figure) -> None:
        self.body.append("\n")

    def visit_caption(self, node: nodes.caption) -> None:
        self.body.append(f"\n*{node.astext()}*\n\n")
        raise nodes.SkipNode

    def visit_table(self, node: nodes.table) -> None:
        rows: list[list[str]] = []
        for row in node.traverse(nodes.row):
            owner = row
            while owner is not None and not isinstance(owner, nodes.table):
                owner = owner.parent
            if owner is not node:
                continue
            cells = []
            for entry in row.children:
                if isinstance(entry, nodes.entry):
                    text = entry.astext().replace("|", "\\|").replace("\n", " ").strip()
                    cells.append(text)
            if cells:
                rows.append(cells)
        if not rows:
            raise nodes.SkipNode
        width = max(len(row) for row in rows)

        def format_row(cells: list[str]) -> str:
            padded = cells + [""] * (width - len(cells))
            return "| " + " | ".join(padded) + " |"

        self.body.append("\n" + format_row(rows[0]) + "\n")
        self.body.append("| " + " | ".join("---" for _ in range(width)) + " |\n")
        for row in rows[1:]:
            self.body.append(format_row(row) + "\n")
        self.body.append("\n")
        raise nodes.SkipNode

    def visit_note(self, node: nodes.note) -> None:
        self.body.append("\n**Note**\n\n")

    def visit_warning(self, node: nodes.warning) -> None:
        self.body.append("\n**Warning**\n\n")

    def visit_tip(self, node: nodes.tip) -> None:
        self.body.append("\n**Tip**\n\n")

    def visit_important(self, node: nodes.important) -> None:
        self.body.append("\n**Important**\n\n")

    def visit_caution(self, node: nodes.caution) -> None:
        self.body.append("\n**Caution**\n\n")

    def visit_admonition(self, node: nodes.admonition) -> None:
        self.body.append("\n")

    def visit_math(self, node: nodes.math) -> None:
        self.body.append(f"${node.astext()}$")
        raise nodes.SkipNode

    def visit_math_block(self, node: nodes.math_block) -> None:
        self.body.append(f"\n$$\n{node.astext()}\n$$\n\n")
        raise nodes.SkipNode

    def visit_transition(self, node: nodes.transition) -> None:
        self.body.append("\n---\n\n")
        raise nodes.SkipNode

    def visit_problematic(self, node: nodes.problematic) -> None:
        self.body.append(node.astext())
        raise nodes.SkipNode


class MarkdownBuilder(Builder):
    """Write resolved doctrees to markdown pages."""

    name = "laminmd"
    format = "markdown"
    epilog = __("The markdown files are in %(outdir)s.")
    out_suffix = ".md"
    allow_parallel = False

    def _out_path(self, docname: str) -> Path:
        return (
            Path(self.outdir).joinpath(*docname.split("/")).with_suffix(self.out_suffix)
        )

    def get_outdated_docs(self) -> Iterator[str]:
        for docname in self.env.found_docs:
            if docname not in self.env.all_docs:
                yield docname
                continue
            target = self._out_path(docname)
            try:
                targetmtime = target.stat().st_mtime
            except OSError:
                targetmtime = 0
            try:
                srcmtime = Path(self.env.doc2path(docname)).stat().st_mtime
                if srcmtime > targetmtime:
                    yield docname
            except OSError:
                pass

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        return docname + self.out_suffix

    def prepare_writing(self, docnames: set[str]) -> None:
        return None

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        translator = MarkdownTranslator(doctree, self)
        doctree.walkabout(translator)
        outfile = self._out_path(docname)
        outfile.parent.mkdir(parents=True, exist_ok=True)
        try:
            outfile.write_text(translator.astext(), encoding="utf-8")
        except OSError as err:
            logger.warning(__("error writing file %s: %s"), outfile, err)

    def finish(self) -> None:
        return None


def setup(app: Sphinx) -> ExtensionMetadata:
    app.add_builder(MarkdownBuilder)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
