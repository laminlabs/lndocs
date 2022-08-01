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
    "show_prev_next": True,
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

html_logo = (
    "https://raw.githubusercontent.com/laminlabs/lamin-profile/main/assets/logo.svg"
)
html_favicon = "../lamin_sphinx/_static/img/favicon.ico"
html_static_path = ["../lamin_sphinx/_static"]

# order matters below!
# https://stackoverflow.com/questions/45112812/sphinx-exclude-one-page-from-html-sidebars # noqa
html_sidebars = {
    "*": ["sidebar-nav-bs"],
    "**/*": ["sidebar-nav-bs"],
    "index": [],
    "impressum": [],
    "products": [],
    "docs": [],
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
napoleon_numpy_docstring = False
napoleon_use_rtype = True
napoleon_use_param = False

ogp_image = "https://lamin.ai/_static/img/logo.png"

# myst_nb options
nb_execution_mode = "off"

nitpicky = True  # report broken links


nitpick_ignore = [
    ("py:class", "pandas.core.frame.DataFrame"),
    ("py:class", "sqlmodel.orm.session.Session"),
    ("py:class", "numpy.ndarray"),
    ("py:class", "datetime.datetime"),
    ("py:class", "pydantic.main.BaseModel"),
    ("py:class", "cloudpathlib.cloudpath.CloudPath"),
    ("py:class", "anndata._core.anndata.AnnData"),
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

from io import StringIO  # type: ignore  # noqa

from markdown import Markdown  # type: ignore  # noqa


def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# patching Markdown
Markdown.output_formats["plain"] = unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False


def unmark(text):
    return __md.convert(text)


from docutils.nodes import footnote  # type: ignore  # noqa
from docutils.writers._html_base import HTMLTranslator  # type: ignore  # noqa


def visit_footnote_reference(self, node):
    href = "#" + node["refid"]
    classes = "footnote-reference " + self.settings.footnote_references
    # walk through all nodes of the current document to find the
    # corresponding footnote and retrieve the text
    title = "See bottom of page."
    content = (
        node.document.children[0]
        if len(node.document.children[0]) > 1
        else node.document.children[1]
    )
    for node_ in content.children:
        # check whether a node is a footnote
        if isinstance(node_, footnote):
            print(node)
            print(node_.attributes["ids"])
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
    else:  # remove markup
        title = unmark(title)
    self.body.append(
        self.starttag(node, "a", "", CLASS=classes, href=href, title=title)
    )


HTMLTranslator.visit_footnote_reference = visit_footnote_reference

# -------------------------------------------------------------------------------------
# This block renders the author front matter

authors = {
    "falexwolf": ("Alex Wolf", "https://falexwolf.me"),
    "sunnyosun": ("Sunny Sun", "https://github.com/sunnyosun"),
    "Koncopd": ("Sergei Rybakov", "https://github.com/Koncopd"),
    "Zethson": ("Lukas Heumos", "https://github.com/Zethson"),
}

from myst_parser.mdit_to_docutils.base import (  # noqa
    DocutilsRenderer,
    SyntaxTreeNode,
    token_line,
)


# from myst_parser 0.18.0
# https://github.com/executablebooks/MyST-Parser/blob/391a8cd1097db16f122ce4736e8924ecfb23e621/myst_parser/mdit_to_docutils/base.py#L792-L831  # noqa
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

    # end of copy of this function, the rest here is our code
    def format_date():
        if isinstance(data["date"], str):
            return data["date"].split(" ")[0]  # do not display time!
        else:
            return data["date"]

    html = ""
    # some posts might not have software, hence the · at the end
    if data.get("docs"):
        docs = f"<a href={data['docs']}>Docs</a> · "
        html += f"{docs}"
    if data.get("repo"):
        html += f"<a href={data['repo']}>Repository</a> · "
    # if something has twitter, it will also have a linkedin post!
    if data.get("tweet"):
        html += f"<a href={data['tweet']}>Tweet</a> · "
    if data.get("linkedin"):
        html += f"<a href={data['linkedin']}>LinkedIn</a>"
    if data.get("doi"):
        html += f' · <a href=https://doi.org/{data["doi"]}>doi</a>'
    float_right = ""
    if data.get("number"):
        float_right += f'<li> ⸻ #{data["number"]}</li>'
    html = f"""<ul class="ablog-archive" style="padding-left: 0px"><li>{html}</li>{float_right}</ul>"""  # noqa
    self.nested_render_text(f"{html}", 0)

    if data.get("title") and self.md_config.title_to_header:
        self.nested_render_text(f"# {data['title']}", 0)

    def format_authors():
        if data.get("affiliation"):
            affiliation = data["affiliation"]
        else:
            affiliation = {}

        def format_title(k):
            return f'title="{affiliation[k]}"' if affiliation else ""

        return ", ".join(
            [
                f'<a href="{authors[k][1]}" {format_title(k)}>{authors[k][0]}</a>'
                for k in data["author"].split(", ")
            ]
        )

    if data.get("author"):
        html = f"{format_date()} · "
        html += f"{format_authors()}"
        html = f"""<ul class="ablog-archive" style="padding-left: 0px"><li>{html}</li></ul>"""  # noqa
        self.nested_render_text(f"{html}", 0)


DocutilsRenderer.render_front_matter = render_front_matter

# -------------------------------------------------------------------------------------
# citations

from types import MappingProxyType  # noqa
from typing import Any, Mapping, NamedTuple, Sequence  # noqa

from docutils import nodes  # type:ignore # noqa
from docutils.parsers.rst.directives import class_option  # type:ignore # noqa
from docutils.parsers.rst.states import Inliner  # type:ignore # noqa
from sphinx.application import Sphinx  # noqa
from sphinx.config import Config  # noqa


class AutoLink(NamedTuple):
    class_name: str
    url_template: str
    title_template: str = "{}"  # noqa
    options: Mapping[str, Any] = MappingProxyType({"class": class_option})  # noqa

    def __call__(  # noqa
        self,
        name: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: Inliner,
        options: Mapping[str, Any] = MappingProxyType({}),
        content: Sequence[str] = (),
    ):
        url = self.url_template.format(text)
        title = self.title_template.format(text)
        options = {**dict(classes=[self.class_name]), **options}
        node = nodes.reference(rawtext, title, refuri=url, **options)
        return [node], []


def register_links(app: Sphinx, config: Config):
    app.add_role("ct", AutoLink("ct", "#{}", "[{}]"))
    app.add_role("cp", AutoLink("cp", "#{}", "{}"))


# -------------------------------------------------------------------------------------


def setup(app: Sphinx):
    app.warningiserror = os.getenv("GITHUB_ACTIONS") is not None
    app.add_css_file("custom.css")
    app.connect("config-inited", register_links)
