import sys
from pathlib import Path
from subprocess import run

from lndocs.lamin_sphinx._mermaid import mermaid_browser_url


def test_code_block_mermaid_renders(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    out = tmp_path / "out"
    src.mkdir()
    module = src / "sample.py"
    module.write_text(
        "def sync():\n"
        '    """Sync records.\n'
        "\n"
        "    .. code-block:: mermaid\n"
        "\n"
        "       flowchart TD\n"
        "         A --> B\n"
        '    """\n'
    )
    (src / "conf.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent))\n"
        "extensions = ['sphinx.ext.autodoc', 'sphinxcontrib.mermaid']\n"
        "from lndocs.lamin_sphinx._mermaid import setup\n"
    )
    (src / "index.rst").write_text("Sample\n======\n\n.. autofunction:: sample.sync\n")
    result = run(
        [sys.executable, "-m", "sphinx", "-W", "-b", "html", str(src), str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    html = (out / "index.html").read_text()
    assert 'class="mermaid"' in html
    assert "flowchart TD" in html
    assert "Pygments lexer name" not in result.stderr


def test_mermaid_browser_url() -> None:
    assert mermaid_browser_url("11.12.1").endswith(
        "mermaid@11.12.1/dist/mermaid.esm.min.mjs"
    )
    assert mermaid_browser_url("latest").endswith(
        "/npm/mermaid/dist/mermaid.esm.min.mjs"
    )


def test_instantclick_renders_mermaid_on_navigation(tmp_path: Path) -> None:
    src = tmp_path / "docs"
    out = tmp_path / "out"
    templates = src / "_templates"
    src.mkdir()
    templates.mkdir()
    lamin_templates = (
        Path(__file__).parents[1] / "lndocs" / "lamin_sphinx" / "_templates"
    )
    (templates / "layout.html").write_text(
        '{%- extends "basic/layout.html" %}\n'
        '{%- block footer %}{% include "footer.html" %}{%- endblock %}\n'
    )
    (src / "conf.py").write_text(
        "extensions = ['sphinxcontrib.mermaid']\n"
        "html_theme = 'basic'\n"
        "templates_path = ['_templates', r'" + str(lamin_templates) + "']\n"
        "from lndocs.lamin_sphinx._mermaid import setup\n"
    )
    (src / "index.rst").write_text("Home\n====\n\n.. toctree::\n\n   diagram\n")
    (src / "diagram.rst").write_text(
        "Diagram\n=======\n\n.. mermaid::\n\n   flowchart TD\n     A --> B\n"
    )
    result = run(
        [sys.executable, "-m", "sphinx", "-W", "-b", "html", str(src), str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    index = (out / "index.html").read_text()
    diagram = (out / "diagram.html").read_text()
    assert "laminRenderMermaid" in index
    assert 'InstantClick.on("change"' in index
    assert "isInitialLoad" in index
    assert 'script[type="module"]' in index
    assert 'class="mermaid"' in diagram
    assert "mermaid@11.12.1/dist/mermaid.esm.min.mjs" in diagram
