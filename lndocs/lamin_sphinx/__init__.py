from datetime import datetime

from sphinx.application import Sphinx

author = "Lamin Labs"
copyright = f"{datetime.now():%Y}, {author}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx_autodoc_typehints",  # needs to be after napoleon
    "IPython.sphinxext.ipython_console_highlighting",  # noqa https://github.com/spatialaudio/nbsphinx/issues/24
    "myst_nb",
    "ablog",
    "sphinxext.opengraph",
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
    "show_prev_next": False,
    "use_edit_page_button": False,  # currently unused
    "search_bar_text": "Search",  # currently unused
    "navbar_end": ["theme-switcher"],
    "navbar_align": "left",
    "footer_items": ["copyright"],
}

html_context = {
    "default_mode": "auto",
    "github_user": "laminlabs",
    "github_version": "main",
}

html_logo = "../lamin_sphinx/_static/img/logo.svg"
html_favicon = "../lamin_sphinx/_static/img/favicon.ico"
html_static_path = ["../lamin_sphinx/_static"]

html_sidebars = {
    "*": ["sidebar-nav-bs"],
    "**/*": ["sidebar-nav-bs"],
}

# Other configurations
panels_add_bootstrap_css = False
myst_enable_extensions = [
    "deflist",
    "colon_fence",
]
myst_title_to_header = True  # allow frontmatter titles

autodoc_member_order = "bysource"
napoleon_google_docstring = True
napoleon_include_init_with_doc = False
napoleon_use_rtype = True  # a separate entry helps readability
napoleon_use_param = True
todo_include_todos = False

ogp_image = "https://lamin.ai/_static/img/logo.png"

# myst_nb options
nb_execution_mode = "off"

nitpicky = True  # report broken links


nitpick_ignore = [
    ("py:class", "pandas.core.frame.DataFrame"),
    ("py:class", "pathlib.Path"),
    ("py:data", "typing.Optional"),
    ("py:data", "typing.Literal"),
]


def setup(app: Sphinx):
    app.warningiserror = True
    app.add_css_file("custom.css")
