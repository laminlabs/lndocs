import inspect
import os
from datetime import datetime

import sphinx.ext.autosummary.generate
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

from . import _front_matter  # noqa
from ._cite_commands import register_cite  # noqa
from ._footnote_title import visit_footnote_reference  # noqa
from ._html_tags import html_lamin_page_context  # noqa
from ._nitpick_ignore import nitpick_ignore  # noqa


def process_docstring(app, what, name, obj, options, lines):
    # https://gist.github.com/abulka/48b54ea4cbc7eb014308

    try:
        from django.db import models

        DjangoORM = models.Model
    except ImportError:
        DjangoORM = int  # a hack

    if inspect.isclass(obj):
        if issubclass(obj, DjangoORM):
            # first properties
            if obj.__name__ == "Artifact":
                lines.append(".. rubric:: Properties")
                lines.append(".. autoattribute:: path\n")
            elif obj.__name__ == "FeatureSet":
                lines.append(".. rubric:: Properties")
                lines.append(".. autoattribute:: members\n")

            # now fields
            lines.append(".. rubric:: Fields")
            fields = obj._meta.get_fields()
            # obj._meta.related_objects, do not include related objects for now
            non_many_to_many_fields = [
                field for field in fields if hasattr(field, "verbose_name")
            ]
            many_to_many_fields = [
                field for field in fields if not hasattr(field, "verbose_name")
            ]
            for field in non_many_to_many_fields:
                lines.append(f".. autoattribute:: {field.name}\n")
                annotation = f"{type(field).__name__}"
                # the following doesn't work currently
                # if isinstance(field, models.ForeignKey):
                #     to = field.related_model
                #     annotation += f" to :class:`~{to.__module__}.{to.__name__}`"
                lines.append(f"   :annotation: {annotation}")
                lines.append("   :noindex:")
            for field in many_to_many_fields:
                if field.model.__module__.startswith(
                    "lnschema_bionty"
                ) or field.related_model.__module__.startswith("lnschema_bionty"):
                    continue
                if field in obj._meta.related_objects:
                    continue
                lines.append(f".. autoattribute:: {field.name}\n")
                annotation = f"{type(field).__name__}"
                # the following doesn't work currently
                # if isinstance(field, models.ForeignKey):
                #     to = field.related_model
                #     annotation += f" to :class:`~{to.__module__}.{to.__name__}`"
                lines.append(f"   :annotation: {annotation}")
                lines.append("   :noindex:")
                if field in obj._meta.related_objects:
                    lines.append("   :noindex:")
        else:
            lines.append(".. rubric:: Attributes")
            attributes = inspect.getmembers(obj, lambda a: not (inspect.isroutine(a)))
            attributes = [a for a in attributes if not a[0].startswith(("__", "_"))]
            for attr_name, attr_value in attributes:
                annotation = (
                    "property"
                    if isinstance(attr_value, property)
                    else type(attr_value).__name__
                )
                docstring = ""
                is_linked_type = False
                if isinstance(attr_value, property):
                    getter = attr_value.fget
                    if (
                        getter
                        and hasattr(getter, "__annotations__")
                        and "return" in getter.__annotations__
                    ):
                        annotation = getter.__annotations__["return"]
                        if isinstance(annotation, str):
                            pass
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
                        annotation = type(attr_value).__name__
                    docstring = attr_value.__doc__
                lines.append(f".. attribute:: {attr_name}\n")
                if is_linked_type:
                    lines.append(f"   :type: {annotation}")
                else:
                    lines.append(f"   :annotation: {annotation}")
                if docstring:
                    lines.append("")
                    for line in docstring.split("\n"):
                        lines.append(f"   {line}")
                        break  # only show the first line because for general
                        # attributes, the full class docstring would be shown
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
