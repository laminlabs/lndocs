# Render `.. code-block:: mermaid` with sphinxcontrib-mermaid.
# Docstrings use that directive. Pygments has no mermaid lexer, so the block
# has to become a mermaid node before the HTML writer highlights it.

import json

import docutils.nodes as nodes  # type: ignore
from sphinx.application import Sphinx


def promote_mermaid_code_blocks(
    app: Sphinx, doctree: nodes.document, docname: str
) -> None:
    """Turn mermaid code blocks into mermaid diagram nodes."""
    from sphinxcontrib.mermaid import mermaid

    for node in list(doctree.traverse(nodes.literal_block)):
        if node.get("language") != "mermaid":
            continue
        diagram = mermaid()
        diagram["code"] = node.rawsource or node.astext()
        diagram["options"] = {}
        node.replace_self(diagram)


def _js_literal(value: object) -> str:
    return json.dumps(value).replace("<", "\\u003c")


def mermaid_browser_url(version: str) -> str:
    if version == "latest":
        return "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.esm.min.mjs"
    return f"https://cdn.jsdelivr.net/npm/mermaid@{version}/dist/mermaid.esm.min.mjs"


def add_mermaid_instantclick_context(
    app: Sphinx, pagename: str, templatename: str, context: dict, doctree
) -> None:
    """Expose the mermaid renderer settings to the InstantClick footer script."""
    version = getattr(app.config, "mermaid_version", None) or "11.12.1"
    context["mermaid_browser_url_json"] = _js_literal(mermaid_browser_url(version))
    context["mermaid_init_config_json"] = _js_literal(
        getattr(app.config, "mermaid_init_config", None) or {"startOnLoad": False}
    )
    context["mermaid_light_theme_json"] = _js_literal(
        getattr(app.config, "mermaid_light_theme", None) or "base"
    )
    context["mermaid_dark_theme_json"] = _js_literal(
        getattr(app.config, "mermaid_dark_theme", None) or "base"
    )


def setup(app: Sphinx) -> None:
    app.connect("doctree-resolved", promote_mermaid_code_blocks)
    app.connect("html-page-context", add_mermaid_instantclick_context)
