import inspect
import os
from datetime import datetime

from docutils.writers._html_base import HTMLTranslator  # type: ignore  # noqa
from sphinx.application import Sphinx

author = "Lamin Labs"
copyright = f"{datetime.now():%Y}, {author}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.jquery",
    # "sphinx.ext.autosectionlabel",  # gives some warnings even with autosectionlabel_prefix_document = True  # noqa
    "sphinx_autodoc_typehints",  # needs to be after napoleon
    "sphinx_design",
    "IPython.sphinxext.ipython_console_highlighting",  # noqa https://github.com/spatialaudio/nbsphinx/issues/24
    "myst_nb",
    "ablog",
    "sphinxext.opengraph",
    "sphinx_copybutton",
    # "sphinx_toolbox.more_autodoc.overloads",
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
    "use_edit_page_button": False,
    # "search_bar_text": "Search",  # currently unused
    "navbar_persistent": "search-button.html",
    "show_toc_level": 3,  # levels that are shown for table of contents
    # "show_nav_level": 2, # controls the default display level of the left navbar
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "navbar_align": "left",
    "footer_items": ["copyright"],
    "pygment_light_style": "tango",  # https://help.farbox.com/pygments.html
    "pygment_dark_style": "monokai",
}

html_context = {
    "default_mode": "auto",
    "github_user": "laminlabs",
    "github_version": "main",
    "logo": (
        "https://raw.githubusercontent.com/laminlabs/lamin-profile/main/assets/logo.svg"
    ),
    "favicon": "https://raw.githubusercontent.com/laminlabs/lamin-profile/main/assets/favicon.ico",  # noqa
}

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

# Netlify pretty URLs doesn't like if we switch this
html_link_suffix = "" if os.getenv("GITHUB_ACTIONS") is not None else None

# Other configurations
panels_add_bootstrap_css = False
myst_enable_extensions = [
    "deflist",
    "colon_fence",
]
myst_title_to_header = True  # allow frontmatter titles
myst_heading_anchors = 2  # create anchors for headings
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autodoc_type_aliases = {
    "UPathStr": "lamindb.core.types.UPathStr",
}
# autodoc_default_options = {
#     'inherited-members': False,
# }
autodoc_mock_imports = ["vitessce", "mudata"]
autodoc_inherit_docstrings = False
napoleon_numpy_docstring = False
napoleon_use_rtype = False
napoleon_use_param = True
typehints_defaults = "comma"
always_use_bars_union = True

ogp_image = (
    "https://raw.githubusercontent.com/laminlabs/lamin-about/main/assets/logo.svg"
)

intersphinx_mapping = dict(
    docs=("https://lamin.ai/docs", None),
)

# myst_nb options
nb_execution_mode = "off"

nitpicky = True  # report broken links

from functools import lru_cache  # noqa

import pydata_sphinx_theme  # noqa
from bs4 import BeautifulSoup as bs  # noqa
from pydata_sphinx_theme import (  # noqa
    _add_collapse_checkboxes,
    add_inline_math,
    index_toctree,
    logger,
    nodes,
    urlparse,
)
from sphinx.addnodes import toctree as toctree_node  # noqa
from sphinx.environment.adapters.toctree import TocTree  # noqa

from . import _front_matter  # noqa
from ._cite_commands import register_cite  # noqa
from ._footnote_title import visit_footnote_reference  # noqa
from ._html_tags import html_lamin_page_context  # noqa
from ._nitpick_ignore import nitpick_ignore  # noqa


# when upgrading beyond pydata-sphinx-theme, note that this function moved to
# the toctree module
def add_toctree_functions(app, pagename, templatename, context, doctree):
    """Add functions so Jinja templates can add toctree objects."""

    @lru_cache(maxsize=None)
    def generate_header_nav_html(n_links_before_dropdown=5):
        """
        Generate top-level links that are meant for the header navigation.
        We use this function instead of the TocTree-based one used for the
        sidebar because this one is much faster for generating the links and
        we don't need the complexity of the full Sphinx TocTree.

        This includes two kinds of links:

        - Links to pages described listed in the root_doc TocTrees
        - External links defined in theme configuration

        Additionally it will create a dropdown list for several links after
        a cutoff.

        Parameters
        ----------
        n_links_before_dropdown : int (default: 5)
            The number of links to show before nesting the remaining links in
            a Dropdown element.
        """

        try:
            n_links_before_dropdown = int(n_links_before_dropdown)
        except Exception:
            raise ValueError(
                f"n_links_before_dropdown is not an int: {n_links_before_dropdown}"
            )
        toctree = TocTree(app.env)

        # Find the active header navigation item so we decide whether to highlight
        # Will be empty if there is no active page (root_doc, or genindex etc)
        active_header_page = toctree.get_toctree_ancestors(pagename)
        if active_header_page:
            # The final list item will be the top-most ancestor
            active_header_page = active_header_page[-1]

        # Find the root document because it lists our top-level toctree pages
        root = app.env.tocs[app.config.root_doc]

        # Iterate through each toctree node in the root document
        # Grab the toctree pages and find the relative link + title.
        links_html = []
        # TODO: just use "findall" once docutils min version >=0.18.1
        meth = "findall" if hasattr(root, "findall") else "traverse"
        for toc in getattr(root, meth)(toctree_node):
            for title, page in toc.attributes["entries"]:
                # if the page is using "self" use the correct link
                page = toc.attributes["parent"] if page == "self" else page

                # If this is the active ancestor page, add a class so we highlight it
                current = " current active" if page == active_header_page else ""

                # sanitize page title for use in the html output if needed
                if title is None:
                    title = ""
                    for node in app.env.titles[page].children:
                        if isinstance(node, nodes.math):
                            title += add_inline_math(node)
                        else:
                            title += node.astext()

                # set up the status of the link and the path
                # if the path is relative then we use the context for the path
                # resolution and the internal class.
                # If it's an absolute one then we use the external class and
                # the complete url.
                is_absolute = bool(urlparse(page).netloc)
                link_status = "external" if is_absolute else "internal"
                link_href = page if is_absolute else context["pathto"](page)

                # create the html output
                links_html.append(
                    f"""
                    <li class="nav-item{current}">
                      <a class="nav-link nav-{link_status}" href="{link_href}">
                        {title}
                      </a>
                    </li>
                """
                )

        # Add external links defined in configuration as sibling list items
        for external_link in context["theme_external_links"]:
            links_html.append(
                f"""
                <li class="nav-item">
                  <a class="nav-link nav-external" href="{ external_link["url"] }">
                    { external_link["name"] }
                  </a>
                </li>
                """
            )

        # The first links will always be visible
        links_solo = links_html[:n_links_before_dropdown]
        out = "\n".join(links_solo)

        # Wrap the final few header items in a "more" dropdown
        links_dropdown = links_html[n_links_before_dropdown:]
        if links_dropdown:
            links_dropdown_html = "\n".join(links_dropdown)
            out += f"""
            <div class="nav-item dropdown">
                <button class="btn dropdown-toggle nav-item" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    More
                </button>
                <div class="dropdown-menu">
                    {links_dropdown_html}
                </div>
            </div>
            """  # noqa

        return out

    # TODO: Deprecate after v0.12
    def generate_nav_html(*args, **kwargs):
        logger.warning(
            "`generate_nav_html` is deprecated and will be removed."
            "Use `generate_toctree_html` instead."
        )
        generate_toctree_html(*args, **kwargs)

    # Cache this function because it is expensive to run, and becaues Sphinx
    # somehow runs this twice in some circumstances in unpredictable ways.
    @lru_cache(maxsize=None)
    def generate_toctree_html(kind, startdepth=1, show_nav_level=1, **kwargs):
        """
        Return the navigation link structure in HTML. This is similar to Sphinx's
        own default TocTree generation, but it is modified to generate TocTrees
        for *second*-level pages and below (not supported by default in Sphinx).
        This is used for our sidebar, which starts at the second-level page.

        It also modifies the generated TocTree slightly for Bootstrap classes
        and structure (via BeautifulSoup).

        Arguments are passed to Sphinx "toctree" function (context["toctree"] below).

        ref: https://www.sphinx-doc.org/en/master/templating.html#toctree

        Parameters
        ----------
        kind : "sidebar" or "raw"
            Whether to generate HTML meant for sidebar navigation ("sidebar")
            or to return the raw BeautifulSoup object ("raw").
        startdepth : int
            The level of the toctree at which to start. By default, for
            the navbar uses the normal toctree (`startdepth=0`), and for
            the sidebar starts from the second level (`startdepth=1`).
        show_nav_level : int
            The level of the navigation bar to toggle as visible on page load.
            By default, this level is 1, and only top-level pages are shown,
            with drop-boxes to reveal children. Increasing `show_nav_level`
            will show child levels as well.

        kwargs: passed to the Sphinx `toctree` template function.

        Returns
        -------
        HTML string (if kind == "sidebar") OR
        BeautifulSoup object (if kind == "raw")
        """
        if startdepth == 0:
            toc_sphinx = context["toctree"](**kwargs)
        else:
            # select the "active" subset of the navigation tree for the sidebar
            toc_sphinx = index_toctree(app, pagename, startdepth, **kwargs)

        soup = bs(toc_sphinx, "html.parser")

        # pair "current" with "active" since that's what we use w/ bootstrap
        for li in soup("li", {"class": "current"}):
            li["class"].append("active")

        # Remove sidebar links to sub-headers on the page
        for li in soup.select("li"):
            # Remove
            if li.find("a"):
                href = li.find("a")["href"]
                if "#" in href and href != "#":
                    li.decompose()

        if kind == "sidebar":
            # Add bootstrap classes for first `ul` items
            for ul in soup("ul", recursive=False):
                ul.attrs["class"] = ul.attrs.get("class", []) + ["nav", "bd-sidenav"]

            # Add collapse boxes for parts/captions.
            # Wraps the TOC part in an extra <ul> to behave like chapters with toggles
            # show_nav_level: 0 means make parts collapsible.
            if show_nav_level == 0:
                partcaptions = soup.find_all("p", attrs={"class": "caption"})
                if len(partcaptions):
                    new_soup = bs("<ul class='list-caption'></ul>", "html.parser")
                    for caption in partcaptions:
                        # Assume that the next <ul> element is the TOC list
                        # for this part
                        for sibling in caption.next_siblings:
                            if sibling.name == "ul":
                                toclist = sibling
                                break
                        li = soup.new_tag("li", attrs={"class": "toctree-l0"})
                        li.extend([caption, toclist])
                        new_soup.ul.append(li)
                    soup = new_soup

            # Add icons and labels for collapsible nested sections
            _add_collapse_checkboxes(soup)

            # Open the sidebar navigation to the proper depth
            for ii in range(int(show_nav_level)):
                for checkbox in soup.select(
                    f"li.toctree-l{ii} > input.toctree-checkbox"
                ):
                    checkbox.attrs["checked"] = None

        return soup

    @lru_cache(maxsize=None)
    def generate_toc_html(kind="html"):
        """Return the within-page TOC links in HTML."""

        if "toc" not in context:
            return ""

        soup = bs(context["toc"], "html.parser")

        # added by Alex -----------
        if True:
            soupbody = bs(context["body"], "html.parser")

            if soup.ul is None:
                return ""
            if soup.ul.li is None:
                return ""
            target_ul = soup.ul.li.ul
            if target_ul is None:
                return ""
            for li in target_ul.find_all("li"):
                li.decompose()

            # Find all h2 elements
            for h2 in soupbody.find_all("h2"):
                # Create a new li for the h2 element
                h2_li = soup.new_tag("li")
                h2_link = soup.new_tag("a", href=h2.find("a")["href"])
                h2_link.string = h2.get_text(strip=True).replace("¶", "")
                h2_li.append(h2_link)

                # Create a nested ul for this h2 section
                nested_ul = soup.new_tag("ul")

                # Find all headerlink objects within the same section
                section = h2.find_parent("section")
                if section:
                    for headerlink in section.find_all("a", class_="headerlink"):
                        # Skip the h2 headerlink itself
                        if headerlink == h2.find("a"):
                            continue
                        # Create a new li for each headerlink
                        link_li = soup.new_tag("li")
                        # Create a new a tag for each headerlink
                        link = soup.new_tag("a", href=headerlink["href"])
                        link.string = headerlink["href"].split(".")[-1]
                        # Add the a tag to the li
                        link_li.append(link)
                        # Add the li to the nested ul
                        nested_ul.append(link_li)

                # Add the nested ul to the h2 li
                h2_li.append(nested_ul)
                # Add the h2 li to the root ul
                target_ul.append(h2_li)

        # finish added by Alex -----------

        # Add toc-hN + visible classes
        def add_header_level_recursive(ul, level):
            if ul is None:
                return
            if level <= (context["theme_show_toc_level"] + 1):
                ul["class"] = ul.get("class", []) + ["visible"]
            for li in ul("li", recursive=False):
                li["class"] = li.get("class", []) + [f"toc-h{level}"]
                add_header_level_recursive(li.find("ul", recursive=False), level + 1)

        add_header_level_recursive(soup.find("ul"), 1)

        # Add in CSS classes for bootstrap
        for ul in soup("ul"):
            ul["class"] = ul.get("class", []) + ["nav", "section-nav", "flex-column"]

        for li in soup("li"):
            li["class"] = li.get("class", []) + ["nav-item", "toc-entry"]
            if li.find("a"):
                a = li.find("a")
                a["class"] = a.get("class", []) + ["nav-link"]

        # If we only have one h1 header, assume it's a title
        h1_headers = soup.select(".toc-h1")
        if len(h1_headers) == 1:
            title = h1_headers[0]
            # If we have no sub-headers of a title then we won't have a TOC
            if not title.select(".toc-h2"):
                out = ""
            else:
                out = title.find("ul").prettify()
        # Else treat the h1 headers as sections
        else:
            out = soup.prettify()

        # Return the toctree object
        if kind == "html":
            return out
        else:
            return soup

    def navbar_align_class():
        """Return the class that aligns the navbar based on config."""
        align = context.get("theme_navbar_align", "content")
        align_options = {
            "content": ("col-lg-9", "mr-auto"),
            "left": ("", "mr-auto"),
            "right": ("", "ml-auto"),
        }
        if align not in align_options:
            raise ValueError(
                "Theme option navbar_align must be one of"
                f"{align_options.keys()}, got: {align}"
            )
        return align_options[align]

    context["generate_header_nav_html"] = generate_header_nav_html
    context["generate_toctree_html"] = generate_toctree_html
    context["generate_toc_html"] = generate_toc_html
    context["navbar_align_class"] = navbar_align_class

    # TODO: Deprecate after v0.12
    context["generate_nav_html"] = generate_nav_html


pydata_sphinx_theme.add_toctree_functions = add_toctree_functions


def process_docstring(app, what, name, obj, options, lines):
    # https://gist.github.com/abulka/48b54ea4cbc7eb014308

    try:
        from django.db import models

        DjangoORM = models.Model
    except ImportError:
        DjangoORM = int  # a hack

    if inspect.isclass(obj):
        field_lines = []
        attributes_to_exclude = set()
        if issubclass(obj, DjangoORM):
            field_lines.append("")
            field_lines.append("Fields")
            field_lines.append("------")
            field_lines.append("")
            fields = obj._meta.get_fields()
            # obj._meta.related_objects, do not include related objects for now
            non_many_to_many_fields = [
                field for field in fields if hasattr(field, "verbose_name")
            ]
            many_to_many_fields = [
                field for field in fields if not hasattr(field, "verbose_name")
            ]
            for field in non_many_to_many_fields:
                attributes_to_exclude.add(field.name)
                attributes_to_exclude.add(f"{field.name}_id")
                field_lines.append(f".. autoattribute:: {field.name}\n")
                annotation = f"{type(field).__name__}"
                # the following doesn't work currently
                # if isinstance(field, models.ForeignKey):
                #     to = field.related_model
                #     annotation += f" to :class:`~{to.__module__}.{to.__name__}`"
                field_lines.append(f"   :annotation: {annotation}")
                # field_lines.append("   :noindex:")
            for field in many_to_many_fields:
                attributes_to_exclude.add(field.name)
                if field.model.__module__.startswith(
                    "lnschema_bionty"
                ) or field.related_model.__module__.startswith("lnschema_bionty"):
                    continue
                if field in obj._meta.related_objects:
                    continue
                field_lines.append(f".. autoattribute:: {field.name}\n")
                annotation = f"{type(field).__name__}"
                # the following doesn't work currently
                # if isinstance(field, models.ForeignKey):
                #     to = field.related_model
                #     annotation += f" to :class:`~{to.__module__}.{to.__name__}`"
                field_lines.append(f"   :annotation: {annotation}")
                # field_lines.append("   :noindex:")
                # if field in obj._meta.related_objects:
                #     field_lines.append("   :noindex:")
            attributes_to_exclude.update(
                ["MultipleObjectsReturned", "Meta", "DoesNotExist", "pk"]
            )
        attributes = inspect.getmembers(obj, lambda a: not (inspect.isroutine(a)))
        attributes = [
            a
            for a in attributes
            if (not a[0].startswith(("__", "_")) and a[0] not in attributes_to_exclude)
        ]
        attr_lines = []
        for attr_name, attr_value in attributes:
            docstring = ""
            annotation = ""
            autoattribute = False
            is_linked_type = False
            is_property = isinstance(attr_value, property)
            if is_property:
                getter = attr_value.fget
                if (
                    getter
                    and hasattr(getter, "__annotations__")
                    and "return" in getter.__annotations__
                ):
                    annotation = getter.__annotations__["return"]
                    if isinstance(annotation, str):
                        is_linked_type = True
                    elif hasattr(annotation, "__name__"):
                        annotation = annotation.__name__
                        is_linked_type = True
                    else:
                        annotation = "property"
                if getter and getter.__doc__:
                    docstring = getter.__doc__.strip()
            else:
                if hasattr(attr_value, "__name__"):
                    annotation = attr_value.__name__
                    is_linked_type = True
                else:
                    autoattribute = True
                    annotation = type(attr_value).__name__
                docstring = attr_value.__doc__
            if annotation in {"FeatureManagerArtifact", "FeatureManagerCollection"}:
                annotation = "FeatureManager"
            if autoattribute:
                attr_lines.append(f".. autoattribute:: {attr_name}")
            else:
                attr_lines.append(f".. attribute:: {attr_name}")
            if is_linked_type:
                attr_lines.append(f"   :type: {annotation}")
            else:
                attr_lines.append(f"   :annotation: {annotation}")
            if docstring and not autoattribute:
                attr_lines.append("")
                for line in docstring.split("\n"):
                    attr_lines.append(f"   {line}\n")
                    break  # only show the first line because for general
                    # attributes, the full class docstring would be shown
        if attr_lines:
            lines.append("Attributes")
            lines.append("----------")
            lines.append("")
            for line in attr_lines:
                lines.append(line)
        for line in field_lines:
            lines.append(line)
        # print("\n".join(lines))
        # the following is more complicated than expected, leave this in template for now  # noqa
        # lines.append(f".. rubric:: Methods")
        # methods = inspect.getmembers(obj, lambda a:not(inspect.isroutine(a) or inspect.isfunction(a)))  # noqa
        # methods = [a for a in methods if not(a[0].startswith('__') or a[0].startswith('_'))]  # noqa
        # for meth in methods:
        #     lines.append(f".. automethod:: {meth[0]}\n")
    return lines


def setup(app: Sphinx):
    app.warningiserror = os.getenv("LNDOCS_WARNING_IS_ERROR") is not None
    app.add_css_file("custom.css")
    app.connect("html-page-context", html_lamin_page_context)
    app.connect("config-inited", register_cite)
    app.connect("autodoc-process-docstring", process_docstring)
