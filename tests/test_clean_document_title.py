from lndocs.__main__ import (
    _clean_document_title,
    _extract_document_title,
    _format_llms_txt_entry,
)


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


def test_format_llms_txt_entry_uses_markdown_links() -> None:
    assert (
        _format_llms_txt_entry("introduction", "Introduction", 1)
        == "  - [Introduction](introduction.md)\n"
    )
    assert (
        _format_llms_txt_entry("tables", "Query tables in storage", 2)
        == "    - [Query tables in storage](tables.md)\n"
    )
    assert (
        _format_llms_txt_entry(
            "cellxgene-curate",
            'Curate "AnnData" based on the CELLxGENE schema',
            3,
        )
        == '      - [Curate "AnnData" based on the CELLxGENE schema](cellxgene-curate.md)\n'
    )
    assert (
        _format_llms_txt_entry("faq/search", "How does search work?", 2)
        == "    - [How does search work?](faq/search.md)\n"
    )
    assert (
        _format_llms_txt_entry("setup", '"Install & setup"', 1)
        == "  - [Install & setup](setup.md)\n"
    )
    assert (
        _format_llms_txt_entry("introduction", "", 0)
        == "- [introduction](introduction.md)\n"
    )
