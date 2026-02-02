# -------------------------------------------------------------------------------------
# Inject a source .md badge on the H1 heading for pages that don't have one

import docutils.nodes as nodes  # type: ignore
from sphinx.application import Sphinx

BADGE_IMG_URI = "https://img.shields.io/badge/.md-orange"


def _has_badge(title: nodes.title) -> bool:
    """True if the title already contains a badge (reference to shields.io)."""
    for node in title.traverse():
        if isinstance(node, nodes.reference):
            refuri = node.get("refuri", "")
            if "shields.io" in refuri:
                return True
    return False


def inject_source_badge(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """Add a .md badge with relative link on the H1 for pages that don't have one."""
    if app.builder.name != "html":
        return

    # Find first section and its title (the H1)
    for section in doctree.traverse(nodes.section):
        title = section.next_node(nodes.title)
        if title is None:
            continue
        # Only modify the document's main title (first section)
        break
    else:
        return  # No section with title found

    if _has_badge(title):
        return

    rel_md = docname.split("/")[-1] + ".md"
    # Use raw HTML to avoid Sphinx image transforms expecting 'candidates' attribute
    badge_html = (
        f' <a href="{rel_md}" class="reference external">'
        f'<img src="{BADGE_IMG_URI}" alt=".md" /></a>'
    )
    title += nodes.raw("", badge_html, format="html")
