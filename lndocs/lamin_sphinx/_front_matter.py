# -------------------------------------------------------------------------------------
# this renders the front matter

import yaml  # type: ignore
from myst_parser.mdit_to_docutils.base import (  # noqa
    DocutilsRenderer,
    SyntaxTreeNode,
    token_line,
)

from ._authors import authors


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
        docs = f"<a href={data['docs']}>Documentation</a>"
        html += f"{docs}"
    if data.get("repo"):
        if html != "" and not html.endswith(" · "):
            html += " · "
        html += f"<a href={data['repo']}>Repository</a>"
    if data.get("tweet"):
        if html != "" and not html.endswith(" · "):
            html += " · "
        html += f"<a href={data['tweet']}>Tweet</a>"
    if data.get("linkedin"):
        if html != "" and not html.endswith(" · "):
            html += " · "
        html += f"<a href={data['linkedin']}>LinkedIn</a>"
    if data.get("doi"):
        if html != "" and not html.endswith(" · "):
            html += " · "
        html += f'<a href=https://doi.org/{data["doi"]}>DOI</a>'
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
