import os
from datetime import datetime
from textwrap import dedent

import yaml  # type: ignore
from sphinx.application import Sphinx
from zmq import has

author = "Lamin Labs"
copyright = f"{datetime.now():%Y}, {author}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",  # needs to be after napoleon
    "IPython.sphinxext.ipython_console_highlighting",  # noqa https://github.com/spatialaudio/nbsphinx/issues/24
    "myst_nb",
    "ablog",
    "sphinxext.opengraph",
]

templates_path = ["../lamin_sphinx/_templates"]
source_suffix = [".rst", ".md", ".ipynb"]
exclude_patterns = [
    ".nox",
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "node_modules",
    "README.md",
    "**/README.md",
    "profile",
    "private",
]
default_role = "literal"
html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "show_prev_next": False,
    "use_edit_page_button": False,  # currently unused
    "search_bar_text": "Search",  # currently unused
    "navbar_end": ["theme-switcher"],
    "navbar_align": "left",
    "footer_items": ["copyright"],
    "pygment_light_style": "tango",  # https://help.farbox.com/pygments.html
    "pygment_dark_style": "monokai",
}

html_context = {
    "default_mode": "auto",
    "github_user": "laminlabs",
    "github_version": "main",
}

html_logo = "../lamin_sphinx/_static/img/logo.svg"
html_favicon = "../lamin_sphinx/_static/img/favicon.ico"
html_static_path = ["../lamin_sphinx/_static"]

html_sidebars = {
    "*": ["sidebar-nav-bs"],
    "**/*": ["sidebar-nav-bs"],
}

# Other configurations
panels_add_bootstrap_css = False
myst_enable_extensions = [
    "deflist",
    "colon_fence",
]
myst_title_to_header = True  # allow frontmatter titles

autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
napoleon_google_docstring = True
napoleon_include_init_with_doc = False
napoleon_use_rtype = True  # a separate entry helps readability
napoleon_use_param = True
todo_include_todos = False

ogp_image = "https://lamin.ai/_static/img/logo.png"

# myst_nb options
nb_execution_mode = "off"

nitpicky = True  # report broken links


nitpick_ignore = [
    ("py:class", "pandas.core.frame.DataFrame"),
    ("py:class", "datetime.datetime"),
    ("py:class", "enum.Enum"),
    ("py:class", "pathlib.Path"),
    ("py:class", "Model"),
    ("py:class", "sqlmodel.main.SQLModel"),
    ("py:class", "MetaData"),
    ("py:class", "DictStrAny"),
    ("py:class", "unicode"),
    ("py:class", "typing.DictStrAny"),
    ("py:class", "typing.unicode"),
    ("py:data", "typing.Optional"),
    ("py:data", "typing.Literal"),
    ("py:data", "typing.Union"),
    ("py:data", "typing.Any"),
    ("py:obj", "bionty.Gene"),
    ("py:obj", "bionty.Species"),
]


# -------------------------------------------------------------------------------------
# this whole block enables a footnote tooltip by setting the title element

from docutils.nodes import footnote  # type: ignore  # noqa
from docutils.writers._html_base import HTMLTranslator  # type: ignore  # noqa


def visit_footnote_reference(self, node):
    href = "#" + node["refid"]
    classes = "footnote-reference " + self.settings.footnote_references
    # walk through all nodes of the current document to find the
    # corresponding footnote and retrieve the text
    title = "See bottom of page."
    for node_ in node.document.children[0].children:
        # check whether a node is a footnote
        if isinstance(node_, footnote):
            if node["refid"] in set(node_.attributes["ids"]):
                title = node_.children[1].rawsource
                break
        else:
            # repeat the same one level deeper in the tree
            if hasattr(node_, "children"):
                for node__ in node_.children:
                    if isinstance(node__, footnote):
                        if node["refid"] in set(node__.attributes["ids"]):
                            title = node__.children[1].rawsource
                            break
    if title == "See bottom of page.":
        print(f"WARNING: footnote text for footnote {node['refid']} not found")
    self.body.append(
        self.starttag(node, "a", "", CLASS=classes, href=href, title=title)
    )


HTMLTranslator.visit_footnote_reference = visit_footnote_reference

# -------------------------------------------------------------------------------------
# This block renders the author front matter

authors = {
    "falexwolf": ("Alex Wolf", "https://falexwolf.me"),
    "sunnyosun": ("Sunny Sun", "https://github.com/sunnyosun"),
    "koncopd": ("Sergei Rybakov", "https://github.com/koncopd"),
}

from myst_parser.docutils_renderer import (  # noqa
    DocutilsRenderer,
    SyntaxTreeNode,
    token_line,
)


# from https://github.com/executablebooks/MyST-Parser/blob/4bf38aca204b9643ca5dc84b30bdcad209519428/myst_parser/mdit_to_docutils/base.py#L792  # noqa
def render_front_matter(self, token: SyntaxTreeNode) -> None:
    """Pass document front matter data."""
    position = token_line(token, default=0)

    if isinstance(token.content, str):
        try:
            data = yaml.safe_load(token.content)
        except (yaml.parser.ParserError, yaml.scanner.ScannerError):
            self.create_warning(
                "Malformed YAML",
                line=position,
                append_to=self.current_node,
                subtype="topmatter",
            )
            return
    else:
        data = token.content

    if not isinstance(data, dict):
        self.create_warning(
            f"YAML is not a dict: {type(data)}",
            line=position,
            append_to=self.current_node,
            subtype="topmatter",
        )
        return

    fields = {
        k: v
        for k, v in data.items()
        if k not in ("myst", "mystnb", "substitutions", "html_meta")
    }
    if fields:
        field_list = self.dict_to_fm_field_list(
            fields, language_code=self.document.settings.language_code
        )
        self.current_node.append(field_list)

    if data.get("title") and self.md_config.title_to_header:
        self.nested_render_text(f"# {data['title']}", 0)

    # end of copy, the rest here is our code to add authors
    if data.get("author"):
        data["author"] = data["author"].split(", ")
        author_html = ", ".join(
            [f'<a href="{authors[k][1]}">{authors[k][0]}</a>' for k in data["author"]]
        )
        date_author = dedent(
            f"""
        <ul class="ablog-archive" style="padding-left: 0px">
          <li>{data['date']} ·</li>
          <li>{author_html}</li>
        </ul>
        """
        )
        self.nested_render_text(f"{date_author}", 0)


DocutilsRenderer.render_front_matter = render_front_matter

# -------------------------------------------------------------------------------------


def setup(app: Sphinx):
    app.warningiserror = os.getenv("GITHUB_ACTIONS") is not None
    app.add_css_file("custom.css")
