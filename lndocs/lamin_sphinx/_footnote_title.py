# -------------------------------------------------------------------------------------
# this enables a footnote tooltip by setting the title element

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
