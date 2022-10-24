from typing import Any, Dict

import docutils.nodes as nodes  # type: ignore
from sphinx.application import Sphinx
from sphinxext.opengraph import make_tag  # see below for implementation

# def make_tag(property: str, content: str) -> str:
#     # Parse quotation, so they won't break html tags if smart quotes are disabled
#     content = content.replace('"', "&quot;")
#     return f'<meta property="{property}" content="{content}" />'


def add_scholar_tags(
    app: Sphinx,
    context: Dict[str, Any],
    doctree: nodes.document,
    config: Dict[str, Any],
) -> None:
    # Get field lists for per-page overrides
    fields = context["meta"]
    if fields is None:
        fields = {}
    tags = {}

    # add citation tags and overwrite ogp tags
    if "doi" in fields:
        tags["citation_title"] = fields["title"]
        context["metatags"] = context["metatags"].replace(
            make_tag("og:type", "website"), make_tag("og:type", "article")
        )

    context["metatags"] += "\n".join([make_tag(k, v) for k, v in tags.items()]) + "\n"


def html_lamin_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: Dict[str, Any],
    doctree: nodes.document,
) -> None:
    if doctree:
        add_scholar_tags(app, context, doctree, app.config)
