import sys
from pathlib import Path
from subprocess import run


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
