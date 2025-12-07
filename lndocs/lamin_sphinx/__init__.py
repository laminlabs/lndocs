import inspect
import os
import sys
from datetime import datetime

from docutils.writers._html_base import HTMLTranslator  # type: ignore
from sphinx.application import Sphinx

author = "Lamin Team"
copyright = f"{datetime.now():%Y}, {author}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.jquery",
    "sphinx_autodoc_typehints",  # needs to be after napoleon
    "sphinx_design",
    "IPython.sphinxext.ipython_console_highlighting",
    "myst_nb",
    "sphinxext.opengraph",
    "sphinx_copybutton",
]

try:
    import ablog

    extensions.append("ablog")
except ImportError:
    pass


templates_path = ["../lamin_sphinx/_templates"]
source_suffix = [".rst", ".md", ".ipynb"]
exclude_patterns = [
    "includes/*",
    "changelog/soon/*",
    "README.md",
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
        "https://raw.githubusercontent.com/laminlabs/lamin-about/main/assets/logo.svg"
    ),
}
html_favicon = (
    "https://raw.githubusercontent.com/laminlabs/lamin-about/main/assets/favicon.ico"
)
html_static_path = ["../lamin_sphinx/_static"]

# order matters below!
# https://stackoverflow.com/questions/45112812/sphinx-exclude-one-page-from-html-sidebars
# update 2024-08-03: https://claude.ai/share/e00e8810-a07f-4558-a11b-2abceee99488
html_sidebar = ["sidebar-nav-bs"]
html_sidebars = {  # type: ignore
    "changelog": [],
    "changelog/*": [],
}

# Netlify pretty URLs doesn't like if we switch this
html_link_suffix = "" if os.getenv("GITHUB_ACTIONS") is not None else None

# Other configurations
panels_add_bootstrap_css = False
myst_enable_extensions = [
    "deflist",
    "colon_fence",
    "linkify",  # urls are clickable
]
myst_title_to_header = True  # allow frontmatter titles
myst_heading_anchors = 2  # create anchors for headings
autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
autodoc_type_aliases = {
    "UPathStr": "lamindb.core.types.UPathStr",
    "Ontology": "bionty.base._ontology.Ontology",
    "InspectResult": "bionty.base.dev.InspectResult",
}
building_text = any(arg in sys.argv for arg in ["text"])
autodoc_default_options = {
    "inherited-members": False,
}
show_inherited = os.getenv("LNDOCS_SHOW_INHERITED_MEMBERS", "true").lower() != "false"
print("show inherited members:", show_inherited)
autodoc_mock_imports = [
    "vitessce",
    "mudata",
    "tiledbsoma",
    "universal-pathlib",
    "pronto",
    "polars",
    "lightning",
]
autodoc_inherit_docstrings = False
napoleon_numpy_docstring = False
napoleon_use_rtype = False
napoleon_use_param = True
typehints_defaults = "comma"
always_use_bars_union = True

ogp_image = (
    "https://raw.githubusercontent.com/laminlabs/lamin-about/main/assets/logo.svg"
)

intersphinx_mapping = {
    "docs": ("https://docs.lamin.ai", None),
}

# myst_nb options
nb_execution_mode = "off"
nb_render_text_lexer = "myst-ansi"


nitpicky = True  # report broken links

from functools import lru_cache, cache  # noqa

import pydata_sphinx_theme
from bs4 import BeautifulSoup as bs
from pydata_sphinx_theme import (
    _add_collapse_checkboxes,
    add_inline_math,
    index_toctree,
    logger,
    nodes,
    urlparse,
)
from sphinx.addnodes import toctree as toctree_node
from sphinx.environment.adapters.toctree import TocTree

from . import _front_matter
from ._cite_commands import register_cite
from ._footnote_title import visit_footnote_reference
from ._html_tags import html_lamin_page_context
from ._nitpick_ignore import nitpick_ignore


# when upgrading beyond pydata-sphinx-theme, note that this function moved to
# the toctree module
def add_toctree_functions(app, pagename, templatename, context, doctree):
    """Add functions so Jinja templates can add toctree objects."""

    @cache
    def generate_header_nav_html(n_links_before_dropdown=5):
        """Generate top-level links that are meant for the header navigation.

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
            ) from None
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
                  <a class="nav-link nav-external" href="{external_link["url"]}">
                    {external_link["name"]}
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
            """

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
    @cache
    def generate_toctree_html(kind, startdepth=1, show_nav_level=1, **kwargs):
        """Return the navigation link structure in HTML.

        This is similar to Sphinx's own default TocTree generation, but it is modified to generate TocTrees
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

        Returns:
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

    @cache
    def generate_toc_html(kind="html"):
        """Return the within-page TOC links in HTML."""
        if "toc" not in context:
            return ""

        soup = bs(context["toc"], "html.parser")

        # added by Alex -----------
        soupbody = bs(context["body"], "html.parser")

        build_toc = None
        if soup.ul is None:
            return ""
        elif soup.ul.li is None:
            build_toc = False
        else:
            target_ul = soup.ul.li.ul
        if build_toc is None:
            # determines whether its an autodoc-generated page or not
            # autodoc uses the docutils StateMachine to build the object graph
            # and automatically adds objects in the index to the TOC
            if "docutils" in str(target_ul):
                build_toc = True
            else:
                build_toc = False

        if build_toc:
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


def get_class_methods(cls, include_inherited=True):
    class_methods = []
    classes_to_check = cls.__mro__ if include_inherited else [cls]

    for c in classes_to_check:
        # Use __dict__ to get only attributes defined directly on this class
        for name, obj in c.__dict__.items():
            if isinstance(obj, classmethod) and name not in class_methods:
                class_methods.append(name)
    return class_methods


def get_instance_methods(cls, include_inherited=True):
    instance_methods = []
    classes_to_check = cls.__mro__ if include_inherited else [cls]

    for c in classes_to_check:
        # Use __dict__ to get only attributes defined directly on this class
        for name, obj in c.__dict__.items():
            if (
                inspect.isfunction(obj)
                and not isinstance(obj, (classmethod, staticmethod))
                and name not in instance_methods
            ):
                instance_methods.append(name)
    return instance_methods


def attach_func_to_class_method(func_name, cls, globals):
    implementation = globals[func_name]
    target = getattr(cls, func_name)
    # assigning the original class definition docstring
    # to the implementation only has an effect for regular methods
    # not for class methods
    # this is why we need @doc_args for class methods
    implementation.__doc__ = target.__doc__
    setattr(cls, func_name, implementation)


from typing import NamedTuple

try:
    import pandas as pd
    from lamindb.base import doc_args
    from lamindb.base.types import StrField
    from lamindb.models import QuerySet, SQLRecord

    # from lamindb.models.record import T

    @classmethod  # type:ignore
    @doc_args(SQLRecord.filter.__doc__)
    def filter(cls, *queries, **expressions) -> QuerySet:
        """{}"""  # noqa: D415
        pass

    @classmethod  # type:ignore
    @doc_args(SQLRecord.get.__doc__)
    def get(
        cls,
        idlike: int | str | None = None,
        **expressions,
    ) -> SQLRecord:  # adding T as a type hint doesn't resolve on Sphinx
        """{}"""  # noqa: D415
        pass

    @classmethod  # type:ignore
    @doc_args(SQLRecord.to_dataframe.__doc__)
    def to_dataframe(
        cls,
        include: str | list[str] | None = None,
        features: bool | list[str] = False,
        limit: int = 100,
    ) -> pd.DataFrame:
        """{}"""  # noqa: D415
        pass

    @classmethod  # type: ignore
    @doc_args(SQLRecord.search.__doc__)
    def search(
        cls,
        string: str,
        *,
        field: StrField | None = None,
        limit: int | None = 20,
        case_sensitive: bool = False,
    ) -> QuerySet:
        """{}"""  # noqa: D415
        pass

    @classmethod  # type: ignore
    @doc_args(SQLRecord.lookup.__doc__)
    def lookup(  # type: ignore
        cls,
        field: StrField | None = None,
        return_field: StrField | None = None,
    ) -> NamedTuple:
        """{}"""  # noqa: D415
        pass

    @classmethod  # type: ignore
    @doc_args(SQLRecord.connect.__doc__)
    def connect(
        cls,
        instance: str | None,
    ) -> QuerySet:
        """{}"""  # noqa: D415
        pass

except Exception as err:
    print("WARNING: DID NOT IMPORT LAMINDB", err)


def get_all_annotations(obj):
    """Get all annotations, including inherited ones."""
    all_annotations = {}

    # Get the class or use the object's class
    if isinstance(obj, type):
        cls = obj
    else:
        cls = obj.__class__

    # Traverse the MRO (Method Resolution Order) in reverse to
    # prioritize direct class annotations
    for base in reversed(cls.__mro__):
        if hasattr(base, "__annotations__"):
            all_annotations.update(base.__annotations__)

    return all_annotations


from typing import Union


def update_all_annotations(obj, types_dict):
    """Update annotations with actual types from types_dict."""
    # First, get all annotations including inherited ones
    all_annotations = get_all_annotations(obj)

    # Create a function to resolve complex annotation strings
    def resolve_type(type_annotation):
        # If it's already a type (not a string), return it
        if not isinstance(type_annotation, str):
            return type_annotation

        # Handle union types with | syntax (Python 3.10+)
        if "|" in type_annotation:
            # Split by | and strip whitespace
            parts = [part.strip() for part in type_annotation.split("|")]
            # Resolve each part
            resolved_parts = [types_dict.get(part, part) for part in parts]
            # Attempt to create a union
            try:
                # For Python 3.10+
                return Union[tuple(resolved_parts)]  # noqa
            except (TypeError, SyntaxError):
                # Fall back to string if we can't create a proper Union
                return type_annotation

        # Handle simple types
        return types_dict.get(type_annotation, type_annotation)

    # Update the annotations with resolved types
    resolved_annotations = {
        key: resolve_type(value) for key, value in all_annotations.items()
    }

    # Ensure obj has an __annotations__ attribute
    if not hasattr(obj, "__annotations__"):
        obj.__annotations__ = {}

    # Update the object's annotations with all resolved annotations
    obj.__annotations__.update(resolved_annotations)

    return obj.__annotations__


def process_docstring(app, what, name, obj, options, lines):
    # https://gist.github.com/abulka/48b54ea4cbc7eb014308
    try:
        from django.db import models
        from lamindb.models import (
            Artifact,
            BaseSQLRecord,
            Branch,
            Collection,
            Feature,
            Project,
            Record,
            Reference,
            Registry,
            Run,
            Schema,
            Space,
            SQLRecord,
            Storage,
            Transform,
            ULabel,
            User,
        )
        from lamindb.models._feature_manager import FeatureManager
        from lamindb.models.sqlrecord import SQLRecordInfo
        from lamindb_setup.errors import ModuleWasntConfigured

        # What follows under METHOD_NAMES is ridiculous because Sphinx should be able to
        # interpret the methods added through the Registry metaclass as classmethods
        # but out-of-the-box it just doesn't and so we're hacking this
        METHOD_NAMES = [
            "filter",
            "get",
            "to_dataframe",
            "search",
            "lookup",
            "connect",
        ]
        for name in METHOD_NAMES:
            attach_func_to_class_method(name, BaseSQLRecord, globals())
            attach_func_to_class_method(name, SQLRecord, globals())

        types = {
            "Space": Space,
            "User": User,
            "Run": Run,
            "Schema": Schema,
            "Collection": Collection,
            "Feature": Feature,
            "Branch": Branch,
            "ULabel": ULabel,
            "Record": Record,
            "Transform": Transform,
            "Artifact": Artifact,
            "Project": Project,
            "Reference": Reference,
            "Storage": Storage,
            "FeatureManager": FeatureManager,
        }

    except ImportError as err:
        BaseSQLRecord = int
        print("WARNING: DID NOT IMPORT LAMINDB", err)

    try:
        from bionty.base import PublicOntology
    except ModuleWasntConfigured:
        PublicOntology = int  # mock

    add_headings = False
    if inspect.isclass(obj):
        field_lines = []
        attributes_to_exclude = set()

        if issubclass(obj, BaseSQLRecord):
            if obj not in {BaseSQLRecord, SQLRecord}:
                add_headings = True
            update_all_annotations(obj, types)
            registry_info = SQLRecordInfo(obj)
            simple_fields = registry_info.get_simple_fields()
            if simple_fields and add_headings:
                field_lines.append("")
                field_lines.append("Simple fields")
                field_lines.append("-------------")
                field_lines.append("")
            for field in simple_fields:
                attributes_to_exclude.add(field.name)
                if obj is Schema and field.name in {
                    "slot",
                }:
                    continue
                field_lines.append(f".. autoattribute:: {field.name}\n")
            (
                core_relations,
                _,
            ) = registry_info.get_relational_fields()
            if core_relations and add_headings:
                field_lines.append("")
                field_lines.append("Relational fields")
                field_lines.append("-----------------")
                field_lines.append("")
            for field in core_relations:
                if obj is Schema and field.name in {
                    "validated_by",
                    "validated_schemas",
                    "composite",
                }:
                    continue
                field_lines.append(f".. autoattribute:: {field.name}\n")
            fields = obj._meta.get_fields()
            non_many_to_many_fields = [
                field for field in fields if hasattr(field, "verbose_name")
            ]
            for field in non_many_to_many_fields:
                attributes_to_exclude.add(field.name)
                attributes_to_exclude.add(f"{field.name}_id")
            many_to_many_fields = [
                field for field in fields if not hasattr(field, "verbose_name")
            ]
            for field in many_to_many_fields:
                attributes_to_exclude.add(field.name)
            for field in obj._meta.related_objects:
                attributes_to_exclude.add(field.name + "_set")

            attributes_to_exclude.update(
                [
                    "MultipleObjectsReturned",
                    "Meta",
                    "DoesNotExist",
                    "pk",
                    "objects",
                    "backed",
                ]
            )
        if issubclass(obj, (Exception, SystemExit, models.Field, PublicOntology)):
            attributes = []
        elif show_inherited:
            attributes = inspect.getmembers(obj, lambda a: not (inspect.isroutine(a)))
        else:
            attributes = [
                (name, value)
                for name, value in obj.__dict__.items()
                if not inspect.isroutine(value)
            ]
        attributes = [
            a
            for a in attributes
            if (not a[0].startswith(("__", "_")) and a[0] not in attributes_to_exclude)
        ]

        attr_lines = []
        documented_attrs = set()
        if hasattr(obj, "__annotations__"):
            for attr_name, attr_type in obj.__annotations__.items():
                if (
                    attr_name not in attributes_to_exclude
                    and not attr_name.startswith("_")
                    and attr_name not in documented_attrs
                ):
                    # QueryDB has many annotation typehints without explicit docstrings so we autogenerate them here
                    if obj.__name__ == "QueryDB":
                        type_str = (
                            str(attr_type)
                            .replace("typing.", "")
                            .replace("<class ", "")
                            .replace(">", "")
                            .strip("'")
                        )
                        attr_lines.append(f".. attribute:: {attr_name}")
                        attr_lines.append(f"   :type: {type_str}")
                        attr_lines.append("")
                        attr_lines.append(f"   QuerySet for {attr_name} registry")
                        attr_lines.append("")
                    else:
                        attr_lines.append(f".. autoattribute:: {attr_name}")
                    documented_attrs.add(attr_name)

        for attr_name, attr_value in attributes:
            if attr_name in documented_attrs:
                continue
            docstring = ""
            autoattribute = True
            is_property = isinstance(attr_value, property)
            if is_property:
                autoproperty = True
                autoattribute = False
                if hasattr(attr_value.fget, "__deprecated"):
                    continue
            else:
                if not hasattr(attr_value, "__name__"):
                    autoattribute = True
                docstring = attr_value.__doc__
            if autoattribute:
                attr_lines.append(f".. autoattribute:: {attr_name}")
            elif autoproperty:
                attr_lines.append(f".. autoproperty:: {attr_name}")
            else:
                # don't use this anymore because formatting the docstring becomes impossible
                attr_lines.append(f".. attribute:: {attr_name}")
            if docstring and not autoattribute:
                attr_lines.append("")
                attr_lines.append("")
                for line in docstring.split("\n"):
                    # Unclear why we have to unindent with the replace below but that seems to be required
                    attr_lines.append("    " + line.replace("        ", ""))
                attr_lines.append("")
                attr_lines.append("")

        # class methods
        if issubclass(obj, (models.Field, PublicOntology)):
            class_methods = []
        elif show_inherited:
            class_methods = get_class_methods(obj)
        else:
            class_methods = get_class_methods(obj, include_inherited=False)
        filtered_class_methods = []
        for method_name in class_methods:
            if method_name.startswith(("__", "_", "from_db", "check")):
                continue
            try:
                method_obj = getattr(obj, method_name)
                if hasattr(method_obj, "__deprecated"):
                    continue
            except AttributeError:
                pass
            filtered_class_methods.append(method_name)

        # instance methods
        if issubclass(obj, (models.Field, PublicOntology)):
            methods = []
        elif show_inherited:
            methods = get_instance_methods(obj)
        else:
            methods = get_instance_methods(obj, include_inherited=False)
        filtered_methods = []
        for method_name in methods:
            if method_name.startswith(
                ("__", "_", "get_next", "get_previous", "full_clean")
            ):
                continue
            try:
                method_obj = getattr(obj, method_name)
                if hasattr(method_obj, "__deprecated"):
                    continue
            except AttributeError:
                pass
            filtered_methods.append(method_name)
        if obj is Record:
            if "to_dataframe" in filtered_class_methods:
                filtered_class_methods.remove("to_dataframe")
            if "to_dataframe" not in filtered_methods:
                filtered_methods.append("to_dataframe")
                filtered_methods = sorted(filtered_methods)

        # print attributes and fields
        # we don't want to print big headings if there are only 2 sections
        # actually we only want these headings if we have one page per class
        # but we haven't figured out a reliable way to detect that yet
        at_least_two_sections = add_headings and (
            bool(attr_lines)
            + bool(field_lines)
            + bool(filtered_class_methods)
            + bool(filtered_methods)
            >= 3
        )
        # Special case for QueryDB: always show Attributes heading
        if obj.__name__ == "QueryDB" and attr_lines:
            lines.append("Attributes")
            lines.append("----------")
            lines.append("")
            for line in attr_lines:
                lines.append(line)
        if attr_lines and at_least_two_sections:
            lines.append("Attributes")
            lines.append("----------")
            lines.append("")
        if attr_lines:
            for line in attr_lines:
                lines.append(line)
        for line in field_lines:
            lines.append(line)
        lines.append("")
        if filtered_class_methods and at_least_two_sections:
            lines.append("Class methods")
            lines.append("-------------")
            lines.append("")
        for meth in filtered_class_methods:
            lines.append(f".. automethod:: {meth}\n")
        if filtered_class_methods:
            lines.append("")
        if filtered_methods and at_least_two_sections:
            lines.append("Methods")
            lines.append("-------")
            lines.append("")
        for meth in filtered_methods:
            lines.append(f".. automethod:: {meth}\n")
        if filtered_methods:
            lines.append("")
    return lines


# this here _might_ work for non-class methods, need to double check
# all class members are handled above
def skip_deprecated(app, what, name, obj, skip, options):
    return hasattr(obj, "__deprecated") or skip


def setup(app: Sphinx):
    try:
        # fix UPath.open docs
        from upath import UPath

        if UPath.open.__doc__ is not None:
            UPath.open.__doc__ = UPath.open.__doc__.split("Parameters")[0]
    except ImportError:
        pass

    app.warningiserror = os.getenv("LNDOCS_WARNING_IS_ERROR") is not None
    app.add_css_file("custom.css")
    app.connect("html-page-context", html_lamin_page_context)
    app.connect("config-inited", register_cite)
    app.connect("autodoc-process-docstring", process_docstring)
    app.connect("autodoc-skip-member", skip_deprecated)
