from pathlib import Path

from lndocs.__main__ import generate_llms_txt

CONF = """\
extensions = ["myst_parser", "sphinx_design", "lndocs.markdown"]
myst_enable_extensions = ["colon_fence"]
"""

INDEX = """\
# Docs

```{toctree}
:hidden:

tutorial
changelog
```
"""

TUTORIAL = """\
# Tutorial

```python
ln.track()
```

```python
--db postgresql://<user>:<pwd>@<hostname>:<port>/<dbname>
```

:::{dropdown} Via the R shell

```R
library(laminr)
```

:::

::::{tab-set}

:::{tab-item} Py

```python
ln.track()
```

:::

:::{tab-item} R

```R
ln$track()
```

:::

::::

See {doc}`changelog`.
"""

CHANGELOG = """\
# Changelog

Release notes.
"""

DESCRIPTION = (
    "LaminDB documentation for tracking, querying, curating, and versioning"
    " multimodal biological data."
)


def test_markdown_export_preserves_code_and_index(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "conf.py").write_text(CONF)
    (docs / "index.md").write_text(INDEX)
    (docs / "tutorial.md").write_text(TUTORIAL)
    (docs / "changelog.md").write_text(CHANGELOG)
    html = tmp_path / "_build" / "html"

    status = generate_llms_txt(
        str(docs),
        str(html),
        "llms.txt",
        project_name="Lamin Docs",
        description=DESCRIPTION,
    )
    assert status == 0

    page = (html / "tutorial.md").read_text()
    assert "```python\nln.track()\n```" in page
    assert "postgresql://<user>:<pwd>@<hostname>:<port>/<dbname>" in page
    assert "Via the R shell" in page
    assert "**Py**" in page
    assert "**R**" in page
    assert "```R\nln$track()\n```" in page
    assert "](changelog.md)" in page
    assert "-[ Py ]-" not in page

    index = (html / "llms.txt").read_text()
    assert index.startswith(f"# Lamin Docs\n\n> {DESCRIPTION}\n")
    assert "- [Tutorial](tutorial.md)" in index
    assert "## Optional\n" in index
    assert "## Changelog" not in index
    assert "- [Changelog](changelog.md)" in index
