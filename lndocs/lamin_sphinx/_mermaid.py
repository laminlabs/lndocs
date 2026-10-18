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
        for css_class in node.get("classes", []):
            if css_class not in diagram["classes"]:
                diagram["classes"].append(css_class)
        node.replace_self(diagram)


def _install_mermaid_class_passthrough() -> None:
    """Keep `:class:` on the rendered `<pre>`.

    sphinxcontrib-mermaid writes `class="mermaid"` itself and ignores classes
    on the node. Size rules such as `mermaid-medium-fixed-height` need to land
    on that element.
    """
    import sphinxcontrib.mermaid as mermaid_module

    if getattr(mermaid_module, "_lamin_class_passthrough", False):
        return
    original = mermaid_module._render_mm_html_raw

    def render(self, node, code, options, prefix="mermaid", imgcls=None, alt=None):
        try:
            original(self, node, code, options, prefix=prefix, imgcls=imgcls, alt=alt)
        except nodes.SkipNode:
            extra = [c for c in node.get("classes", []) if c != "mermaid"]
            if extra and self.body and 'class="mermaid' in self.body[-1]:
                self.body[-1] = self.body[-1].replace(
                    'class="mermaid',
                    'class="mermaid ' + " ".join(extra),
                    1,
                )
            raise

    mermaid_module._render_mm_html_raw = render
    mermaid_module._lamin_class_passthrough = True


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
    _install_mermaid_class_passthrough()
    app.connect("doctree-resolved", promote_mermaid_code_blocks)
    app.connect("html-page-context", add_mermaid_instantclick_context)
