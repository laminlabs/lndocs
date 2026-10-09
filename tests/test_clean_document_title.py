from lndocs.__main__ import _clean_document_title, _extract_document_title


def test_clean_document_title_strips_badge_links() -> None:
    title = (
        "Introduction [llms.txt](https://docs.lamin.ai/llms.txt)"
        " [pypi](https://pypi.org/project/lamindb)"
        " [cran](https://cran.r-project.org/package=laminr)"
        " [.md](https://github.com/laminlabs/lamindb/blob/main/docs/tutorial.md)"
    )
    assert _clean_document_title(title) == "Introduction"
    schema_title = (
        "Curate `AnnData` based on the CELLxGENE schema"
        " [.md](https://github.com/laminlabs/cellxgene-lamin/blob/main/docs/"
        "cellxgene-curate.md)"
    )
    assert (
        _clean_document_title(schema_title)
        == "Curate `AnnData` based on the CELLxGENE schema"
    )
    assert _clean_document_title("Install & setup") == "Install & setup"
    assert _clean_document_title("Tutorial [image:.md][image]") == "Tutorial"


def test_extract_document_title_cleans_sphinx_and_markdown_headings() -> None:
    sphinx = (
        "Tutorial [.md](https://github.com/laminlabs/lamindb/blob/main/docs/tutorial.md)\n"
        "=============================================================================\n"
        "\n"
        "Body.\n"
    )
    assert _extract_document_title(sphinx) == "Tutorial"

    markdown = "# Introduction [llms.txt](https://docs.lamin.ai/llms.txt)\n\nBody.\n"
    assert _extract_document_title(markdown) == "Introduction"
