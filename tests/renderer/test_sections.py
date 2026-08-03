"""Tests for docstring section rendering and dispatch."""

from __future__ import annotations

import textwrap


def _render(source: str, name: str | None) -> str:
    """Render the named object from a source snippet to qmd"""
    from great_docs._apiref._tools import render_code_variable

    return render_code_variable(textwrap.dedent(source), name)


def test_examples_section_renders_code_and_prose():
    """
    An `Examples` section interleaves prose and code fragments

    Rendering must not depend on the unhandled-section fallback, which Task 3
    turns into a pure error path.
    """
    source = '''
        def f():
            """
            Do a thing.

            Examples
            --------
            Some explanatory prose.

            >>> f()
            3
            """
    '''
    qmd = _render(source, "f")

    assert "Some explanatory prose." in qmd
    assert "f()" in qmd
    assert "object at 0x" not in qmd


def test_example_fragment_renders_directly():
    """`_render_example_fragment` handles a fragment without re-entering dispatch"""
    from great_docs._apiref._docstring_sections import ExampleCode, ExampleText
    from great_docs._apiref._render.doc import __RenderDoc as RenderDocImpl  # noqa: N813

    render = object.__new__(RenderDocImpl)

    assert "x = 1" in str(render._render_example_fragment(ExampleCode("x = 1")))
    assert render._render_example_fragment(ExampleText("hello")) == "hello"
