import sys
from pathlib import Path

import {{ lamin_package_name }}

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from lamin_sphinx import *  # noqa
from lamin_sphinx import html_context  # noqa

project = "{{ lamin_project_name }}"
html_title = "{{ lamin_project_name }} | Lamin Labs"
release = {{ lamin_package_name }}.__version__
html_context["github_repo"] = "{{ lamin_repository_name }}"  # noqa

ogp_site_url = "https://lamin.ai/{{ lamin_project_slug }}"

def setup(app: Sphinx):
    app.warningiserror = False  # change to True once auto-summary is fixed!
    app.add_css_file("custom.css")
