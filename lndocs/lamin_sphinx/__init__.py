import os
from datetime import datetime

import sphinx.ext.autosummary.generate
from docutils.writers._html_base import HTMLTranslator  # type: ignore  # noqa
from sphinx.application import Sphinx

author = "Lamin Labs"
copyright = f"{datetime.now():%Y}, {author}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",  # needs to be after napoleon
    "sphinx_design",
    "IPython.sphinxext.ipython_console_highlighting",  # noqa https://github.com/spatialaudio/nbsphinx/issues/24
    "myst_nb",
    "ablog",
    "sphinxext.opengraph",
    "sphinx_toolbox.more_autodoc.overloads",
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
    "navbar_persistent": "",  # hides the search/magnifier icon
    "show_nav_level": 2,
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
}

html_logo = (
    "https://raw.githubusercontent.com/laminlabs/lamin-profile/main/assets/logo.svg"
)
html_favicon = (
    "https://raw.githubusercontent.com/laminlabs/lamin-profile/main/assets/favicon.ico"
)
html_static_path = ["../lamin_sphinx/_static"]
html_css_files = ["../lamin_sphinx/_static/custom.css"]

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

# Other configurations
panels_add_bootstrap_css = False
myst_enable_extensions = [
    "deflist",
    "colon_fence",
]
myst_title_to_header = True  # allow frontmatter titles

autodoc_member_order = "bysource"
autodoc_typehints_format = "short"
napoleon_numpy_docstring = False
napoleon_use_rtype = True
napoleon_use_param = False

ogp_image = (
    "https://raw.githubusercontent.com/laminlabs/lamin-about/main/assets/logo.svg"
)

intersphinx_mapping = dict(
    docs=("https://lamin.ai/docs", None),
    lnschema_core=("https://lamin.ai/docs/lnschema-core", None),
    lnschema_bionty=("https://lamin.ai/docs/lnschema-bionty", None),
    lnschema_wetlab=("https://lamin.ai/docs/lnschema-wetlab", None),
    bionty=("https://lamin.ai/docs/bionty", None),
)

# myst_nb options
nb_execution_mode = "off"

nitpicky = True  # report broken links

from . import _front_matter  # noqa
from ._authors import authors  # noqa
from ._cite_commands import register_cite  # noqa
from ._footnote_title import visit_footnote_reference  # noqa
from ._html_tags import html_lamin_page_context  # noqa
from ._nitpick_ignore import nitpick_ignore  # noqa
from ._sort_autosummary import generate_autosummary_content  # noqa

# HTMLTranslator.visit_footnote_reference = visit_footnote_reference
sphinx.ext.autosummary.generate.generate_autosummary_content = (
    generate_autosummary_content  # noqa
)


def setup(app: Sphinx):
    app.warningiserror = os.getenv("GITHUB_ACTIONS") is not None
    app.add_css_file("custom.css")
    app.connect("html-page-context", html_lamin_page_context)
    app.connect("config-inited", register_cite)
