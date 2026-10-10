from lndocs.__main__ import _format_llms_txt_entry


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
