import sys
from pathlib import Path

import lndocs

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE)]
from lamin_sphinx import *  # noqa
from lamin_sphinx import html_context  # noqa

project = "lndocs"
html_title = f"{project} | Lamin Labs"
release = lndocs.__version__
html_context["github_repo"] = "lndocs"  # noqa

ogp_site_url = "https://lamin.ai/lndocs"
