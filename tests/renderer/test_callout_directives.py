import griffe as gf
import pytest

from great_docs._apiref._rst_converters import (
    convert_docstring_text,
)
from great_docs._builtin.directives import _callouts
from great_docs._builtin.directives._callouts import add_callouts, convert_directives
from great_docs._builtin.directives._rst_directives import convert_rst_directives
from great_docs.pandoc import blocks as pandoc_blocks


@pytest.mark.parametrize(
    ("name", "callout", "title"),
    [
        ("versionadded", "note", "Added in version 2.0"),
        ("versionchanged", "note", "Changed in version 2.0"),
        ("deprecated", "warning", "Deprecated since version 2.0"),
        ("note", "note", None),
        ("warning", "warning", None),
        ("caution", "caution", None),
        ("danger", "important", None),
        ("important", "important", None),
        ("tip", "tip", None),
        ("hint", "tip", None),
    ],
)
def test_great_docs_directive_names(name: str, callout: str, title: str | None):
    argument = "2.0 Description." if title else "Description."

    result = convert_directives(f"%{name} {argument}")

    assert f".callout-{callout}" in result
    assert "Description." in result
    if title:
        assert f'title="{title}"' in result


def test_block_body_preserves_markdown_and_paragraphs():
    text = "%warning\n    **First paragraph.**\n\n    Second paragraph."

    result = convert_directives(text)

    assert result == ("::: {.callout-warning}\n**First paragraph.**\n\nSecond paragraph.\n:::")


def test_inline_body_accepts_an_indented_continuation():
    text = "%note Intro.\n    More detail."

    result = convert_directives(text)

    assert result == "::: {.callout-note}\nIntro.\nMore detail.\n:::"


def test_version_directive_without_version_uses_generic_title():
    assert convert_directives("%versionadded") == (
        '::: {.callout-note title="Added in version"}\n\n:::'
    )


def test_directive_stops_before_dedented_prose():
    text = "%warning\n    Warning body.\nFollowing prose."

    result = convert_directives(text)

    assert result == ("::: {.callout-warning}\nWarning body.\n:::\nFollowing prose.")


def test_adjacent_directives_are_converted_independently():
    text = "%note First.\n%tip Second."

    result = convert_directives(text)

    assert result == ("::: {.callout-note}\nFirst.\n:::\n::: {.callout-tip}\nSecond.\n:::")


@pytest.mark.parametrize("name", ["nodoc", "seealso target", "unknown text"])
def test_non_callout_directives_are_unchanged(name: str):
    text = f"%{name}"

    assert convert_directives(text) == text


@pytest.mark.parametrize(
    ("great_docs", "sphinx"),
    [
        ("%warning Be careful.", ".. warning:: Be careful."),
        (
            "%versionchanged 2.1\n    Now returns a copy.",
            ".. versionchanged:: 2.1\n\n    Now returns a copy.",
        ),
        (
            "%note Intro.\n    More detail.\n\n    Final paragraph.",
            ".. note:: Intro.\n\n    More detail.\n\n    Final paragraph.",
        ),
    ],
)
def test_great_docs_and_sphinx_directives_are_equivalent(
    great_docs: str,
    sphinx: str,
):
    assert convert_directives(great_docs) == convert_rst_directives(sphinx)


@pytest.mark.parametrize("parser", ["numpy", "google", "sphinx"])
def test_great_docs_directives_are_parser_independent(parser: str):
    docstring = gf.Docstring(
        "Summary.\n\n%warning\n    Preserve the input.",
        parser=parser,
    )

    rendered = "\n".join(
        convert_docstring_text(section.value, heading_level=2)
        for section in docstring.parsed
        if isinstance(section, gf.DocstringSectionText)
    )

    assert ".callout-warning" in rendered
    assert "Preserve the input." in rendered


def test_add_callouts_replaces_directives_in_docstring_value():
    function = gf.Function("process")
    function.docstring = gf.Docstring(
        "Summary.\n\n%warning Be careful.",
        parent=function,
        parser="numpy",
    )

    result = add_callouts(function)

    assert result is function
    assert function.docstring is not None
    assert function.docstring.value == (
        "Summary.\n\n::: {.callout-warning}\nBe careful.\n:::"
    )


def test_add_callouts_preserves_cached_parsed_docstring():
    function = gf.Function("process")
    function.docstring = gf.Docstring("%warning Be careful.", parent=function)
    sentinel = object()
    function.docstring.__dict__["parsed"] = sentinel

    result = add_callouts(function)

    assert result is function
    assert function.docstring is not None
    assert function.docstring.value == "::: {.callout-warning}\nBe careful.\n:::"
    assert function.docstring.__dict__["parsed"] is sentinel
