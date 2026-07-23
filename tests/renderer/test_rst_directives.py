import griffe as gf
import pytest

from great_docs._apiref import RenderDocFunction, content
from great_docs._apiref._rst_converters import (
    convert_docstring_text,
    convert_rst_text,
)
from great_docs._builtin.directives._rst_directives import (
    add_rst_directives,
    convert_rst_directives,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("note", "::: {.callout-note}\nBody.\n:::"),
        ("warning", "::: {.callout-warning}\nBody.\n:::"),
        ("caution", "::: {.callout-caution}\nBody.\n:::"),
        ("danger", "::: {.callout-important}\nBody.\n:::"),
        ("important", "::: {.callout-important}\nBody.\n:::"),
        ("tip", "::: {.callout-tip}\nBody.\n:::"),
        ("hint", "::: {.callout-tip}\nBody.\n:::"),
        (
            "versionadded",
            '::: {.callout-note title="Added in version 2.0"}\nBody.\n:::',
        ),
        (
            "versionchanged",
            '::: {.callout-note title="Changed in version 2.0"}\nBody.\n:::',
        ),
        (
            "deprecated",
            '::: {.callout-warning title="Deprecated since version 2.0"}\nBody.\n:::',
        ),
    ],
)
def test_callout_directives_render_inline_bodies(name: str, expected: str):
    inline = "2.0 Body." if name.startswith("version") or name == "deprecated" else "Body."

    assert convert_rst_directives(f".. {name}:: {inline}") == expected


def test_math_directive_renders_display_math():
    assert convert_rst_directives(".. math::\n\n    x^2") == "$$\nx^2\n$$"


def test_seealso_directive_renders_a_numpy_section():
    assert convert_rst_directives(".. seealso:: other : Related") == (
        "See Also\n--------\nother : Related"
    )


def test_todo_directive_renders_a_titled_note():
    assert convert_rst_directives(".. todo:: Follow up") == (
        '::: {.callout-note title="Todo"}\nFollow up\n:::'
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            ":param value: Description.\n:type value: int",
            "## Parameters {.doc-section .doc-section-parameters}",
        ),
        ("Use :func:`run`.", "Use `run()`."),
        (
            "=====  =====\nA      B\n=====  =====\n1      2\n=====  =====",
            "| A | B |",
        ),
        (".. [1] Source.", "1. Source."),
        (">>> 1 + 1\n2", "```python\n>>> 1 + 1\n```"),
    ],
)
def test_general_rst_conversion_remains_after_directive_handling(
    source: str,
    expected: str,
):
    converted = convert_rst_directives(source)

    assert expected in convert_docstring_text(converted, heading_level=2)


@pytest.mark.parametrize("source", ["%note Keep this.", ".. note:: Keep this."])
def test_general_rst_conversion_leaves_directives_to_builtin_handlers(source: str):
    assert convert_rst_text(source) == source


def test_directive_bodies_preserve_indented_markdown_and_paragraphs():
    text = ".. note:: Intro.\n\n    **First paragraph.**\n\n    Second paragraph."

    assert convert_rst_directives(text) == (
        "::: {.callout-note}\nIntro.\n**First paragraph.**\n\nSecond paragraph.\n:::"
    )


def test_inline_directive_body_accepts_an_indented_continuation():
    text = ".. warning:: Important.\n\n    More detail."

    assert convert_rst_directives(text) == ("::: {.callout-warning}\nImportant.\nMore detail.\n:::")


def test_bare_directive_at_end_renders_an_empty_callout():
    assert convert_rst_directives(".. note::") == "::: {.callout-note}\n\n:::"


def test_directive_followed_by_dedented_prose_is_unchanged():
    text = ".. note::\nNot an indented body."

    assert convert_rst_directives(text) == text


def test_version_directive_splits_its_version_from_description():
    text = ".. versionadded:: 2.0\n\n    Use the new API."

    assert convert_rst_directives(text) == (
        '::: {.callout-note title="Added in version 2.0"}\nUse the new API.\n:::'
    )


def test_adjacent_and_mixed_directives_keep_their_positions():
    text = ".. note:: First.\n%tip Canonical.\n.. seealso:: second : Related"

    assert convert_rst_directives(text) == (
        "::: {.callout-note}\nFirst.\n:::\n%tip Canonical.\nSee Also\n--------\nsecond : Related"
    )


@pytest.mark.parametrize(
    "text",
    [
        ".. unknown:: Keep this.",
        ".. note: Missing a colon.",
    ],
)
def test_unsupported_or_malformed_directives_are_unchanged(text: str):
    assert convert_rst_directives(text) == text


def test_handler_replaces_value_without_touching_cached_parsed_docstring(
    monkeypatch: pytest.MonkeyPatch,
):
    function = gf.Function("process")
    function.docstring = gf.Docstring("Summary.\n\n.. note:: Be careful.", parent=function)
    sentinel = object()
    function.docstring.__dict__["parsed"] = sentinel

    def fail_if_read(_docstring: gf.Docstring) -> list[gf.DocstringSection]:
        raise AssertionError("handler read docstring.parsed")

    monkeypatch.setattr(gf.Docstring, "parsed", property(fail_if_read))

    result = add_rst_directives(function)

    assert result is function
    assert function.docstring is not None
    assert function.docstring.value == "Summary.\n\n::: {.callout-note}\nBe careful.\n:::"
    assert function.docstring.__dict__["parsed"] is sentinel


def test_add_rst_directives_passes_through_an_object_without_a_docstring():
    function = gf.Function("process")

    assert add_rst_directives(function) is function
    assert function.docstring is None


def test_add_rst_directives_passes_through_an_irrelevant_docstring():
    function = gf.Function("process")
    docstring = gf.Docstring("Summary.", parent=function)
    function.docstring = docstring

    assert add_rst_directives(function) is function
    assert function.docstring is docstring
    assert function.docstring.value == "Summary."


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            ".. warning:: Be careful.",
            "::: {.callout-warning}\nBe careful.\n:::",
        ),
        (
            ".. todo:: Follow up.",
            '::: {.callout-note title="Todo"}\nFollow up.\n:::',
        ),
        (
            ".. math:: x^2",
            "$$\nx^2\n$$",
        ),
    ],
)
def test_first_line_rst_directive_is_rendered_in_the_docstring_body(
    source: str,
    expected: str,
):
    function = gf.Function("process")
    function.docstring = gf.Docstring(
        source,
        parent=function,
        parser="numpy",
    )
    add_rst_directives(function)

    renderer = RenderDocFunction(content.Doc.from_griffe(function.name, function))

    assert renderer.docstring_subject is None
    assert expected in str(renderer.render_body())
