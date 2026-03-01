from typing import Any
from urllib.parse import urljoin

import docutils.nodes as nodes  # type: ignore
from sphinx.application import Sphinx
from sphinxext.opengraph import make_tag  # see below for implementation

# def make_tag(property: str, content: str) -> str:
#     content = content.replace('"', "&quot;")
#     return f'<meta property="{property}" content="{content}" />'


def make_name_tag(name: str, content: Any) -> str:
    # Google Scholar reads Highwire/Scholar metadata from `name="citation_*"` tags,
    # not from OpenGraph-style `property="..."` tags.
    value = str(content).replace('"', "&quot;")
    return f'<meta name="{name}" content="{value}" />'


def fix_og_url(context: dict[str, Any], config: dict[str, Any]):
    old_url = urljoin(
        config["ogp_site_url"], context["pagename"] + context["file_suffix"]
    )
    if "ogp_site_url" not in config or config["ogp_site_url"] is None:
        raise RuntimeError("Please define ogp_site_url in conf.py.")
    new_url = config["ogp_site_url"] + "/" + context["pagename"]
    context["metatags"] = context["metatags"].replace(
        make_tag("og:url", old_url), make_tag("og:url", new_url)
    )


def fix_og_type(context: dict[str, Any], config: dict[str, Any]):
    context["metatags"] = context["metatags"].replace(
        make_tag("og:type", "website"), make_tag("og:type", "article")
    )


def add_authors(context, fields):
    import lndocs

    if "author" in fields:
        for key in fields["author"].split(", "):
            # does not work with tag dict as key is the same for all authors
            context["metatags"] += "\n" + make_name_tag(
                "citation_author", lndocs.authors[key.rstrip("*")][0]
            )


def add_scholar_tags(
    app: Sphinx,
    context: dict[str, Any],
    doctree: nodes.document,
    config: dict[str, Any],
) -> None:
    # Get field lists for per-page overrides
    fields = context["meta"]
    if fields is None:
        fields = {}
    tags = {}

    fix_og_url(context, config)
    tags["twitter:image"] = (
        "https://raw.githubusercontent.com/laminlabs/lamin-about/main/assets/logo.svg"
    )

    # Use title/author/date as the minimum gate so posts without DOI still get
    # Scholar metadata and can be considered for indexing.
    required_fields = ("title", "author", "date")
    if all(key in fields for key in required_fields):
        tags["citation_title"] = fields["title"]
        fix_og_type(context, config)
        add_authors(context, fields)
        tags["citation_publication_date"] = str(fields["date"]).replace("-", "/")
        tags["citation_journal_title"] = "Lamin Blog"
        tags["citation_publisher"] = "Lamin Labs"
        tags["citation_article_type"] = "Article"
        tags["citation_language"] = "en"
        tags["citation_abstract_html_url"] = (
            config["ogp_site_url"] + "/" + context["pagename"]
        )
        if "doi" in fields:
            tags["citation_doi"] = fields["doi"]
            tags["DOI"] = fields["doi"]
        if "pdf" in fields:
            tags["citation_pdf_url"] = fields["pdf"]

    context["metatags"] += (
        "\n"
        + "\n".join(
            [
                make_name_tag(k, v) if k.startswith("citation_") else make_tag(k, v)
                for k, v in tags.items()
            ]
        )
        + "\n"
    )


def html_lamin_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree: nodes.document,
) -> None:
    if doctree:
        add_scholar_tags(app, context, doctree, app.config)
