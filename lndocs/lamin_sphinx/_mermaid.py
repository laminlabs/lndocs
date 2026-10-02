# Render `.. code-block:: mermaid` with sphinxcontrib-mermaid.
# Docstrings use that directive. Pygments has no mermaid lexer, so the block
# has to become a mermaid node before the HTML writer highlights it.

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


def setup(app: Sphinx) -> None:
    app.connect("doctree-resolved", promote_mermaid_code_blocks)
