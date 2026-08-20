import griffe as gf
import pytest

from great_docs._builtin.normalization._sphinx import (
    _convert_rst_citations,
    _convert_rst_grid_tables,
    _convert_rst_simple_tables,
    _smart_dedent,
    normalize_sphinx_markup,
)

_SPHINX_ROLE_NAMES = ("exc", "class", "func", "meth", "attr", "const", "mod", "obj", "data", "type")
_CALLABLE_RST_ROLES = frozenset({"func", "meth"})


def _function(text: str, parser: str) -> gf.Function:
    """Build a function with a docstring parsed in the selected style"""
    obj = gf.Function("process")
    obj.docstring = gf.Docstring("", parent=obj, parser=parser)
    obj.docstring.value = text
    return obj


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Use :func:`run`.", "Use `run()`."),
        ("The value is :math:`x^2`.", "The value is $x^2$."),
        (
            "Example::\n\n    value = 1",
            "Example:\n\n```python\nvalue = 1\n```",
        ),
        (
            "=====  =====\nA      B\n=====  =====\n1      2\n=====  =====",
            "| A | B |",
        ),
        (
            "+------+------+\n| A    | B    |\n+======+======+\n| 1    | 2    |\n+------+------+",
            "| A | B |",
        ),
    ],
)
def test_sphinx_markup_is_normalized(source: str, expected: str):
    obj = _function(source, "sphinx")

    result = normalize_sphinx_markup(obj)

    assert result is obj
    assert expected in obj.docstring.value


@pytest.mark.parametrize("parser", ["numpy", "google"])
def test_sphinx_markup_is_unchanged_for_other_parsers(parser: str):
    source = "Use :func:`run` with :math:`x^2`."
    obj = _function(source, parser)

    normalize_sphinx_markup(obj)

    assert obj.docstring.value == source


def test_sphinx_normalization_repairs_inconsistent_indentation():
    obj = _function("    First line.\n  Second line.\n    Third line.", "sphinx")

    normalize_sphinx_markup(obj)

    assert obj.docstring.value == "First line.\nSecond line.\nThird line."


@pytest.mark.parametrize(
    "source",
    [
        "```{python}\n#| eval: false\nprint('hi')\n```",
        "```python\nvalue = 1\n```",
    ],
)
def test_sphinx_normalization_preserves_existing_code_fences(source: str):
    obj = _function(source, "sphinx")

    normalize_sphinx_markup(obj)

    assert obj.docstring.value == source


@pytest.mark.parametrize("role", _SPHINX_ROLE_NAMES)
@pytest.mark.parametrize("prefix", ["", "py:"])
def test_sphinx_role_converts_to_code_span(role: str, prefix: str):
    obj = _function(f"See :{prefix}{role}:`thing`.", "sphinx")

    normalize_sphinx_markup(obj)

    if role in _CALLABLE_RST_ROLES:
        assert obj.docstring.value == "See `thing()`."
    else:
        assert obj.docstring.value == "See `thing`."


@pytest.mark.parametrize("role", sorted(_CALLABLE_RST_ROLES))
def test_callable_role_does_not_double_parens(role: str):
    obj = _function(f"See :{role}:`thing()`.", "sphinx")

    normalize_sphinx_markup(obj)

    assert obj.docstring.value == "See `thing()`."


def test_non_role_text_is_unchanged():
    source = "This is regular text with `code`."
    obj = _function(source, "sphinx")

    normalize_sphinx_markup(obj)

    assert obj.docstring.value == source


def test_sphinx_normalization_registers_on_import():
    from great_docs.hooks import _object_resolved

    assert normalize_sphinx_markup in _object_resolved.REGISTRY


# ---------------------------------------------------------------------------
# Coverage: _smart_dedent with blank lines
# ---------------------------------------------------------------------------


def test_smart_dedent_preserves_blank_lines():
    """Blank lines in indented text are passed through unchanged."""
    text = "    First line.\n\n    Third line.\n"
    result = _smart_dedent(text)
    assert result == "First line.\n\nThird line.\n"


# ---------------------------------------------------------------------------
# Coverage: _convert_rst_citations edge cases
# ---------------------------------------------------------------------------


def test_citations_with_non_citation_lines():
    """Non-citation lines are preserved verbatim."""
    text = "Some preamble.\n\n.. [1] Author. https://example.com\n\nSome epilogue."
    result = _convert_rst_citations(text)
    assert "Some preamble." in result
    assert "Some epilogue." in result
    assert "1. Author." in result


def test_citations_with_continuation_lines():
    """Multi-line citations are joined."""
    text = ".. [1] First part\n   continuation line\n   another continuation"
    result = _convert_rst_citations(text)
    assert "1. First part continuation line another continuation" in result


# ---------------------------------------------------------------------------
# Coverage: _convert_rst_simple_tables edge cases
# ---------------------------------------------------------------------------


def test_simple_table_two_separators_with_content():
    """Table with 2 separators and one row between them."""
    text = "=====  =====\nA      B\n=====  ====="
    result = _convert_rst_simple_tables(text)
    assert "| A | B |" in result
    assert "| --- | --- |" in result


def test_simple_table_single_separator_returns_unchanged():
    """Only 1 separator found → conversion fails, line preserved."""
    text = "=====  =====\nA      B\nC      D"
    result = _convert_rst_simple_tables(text)
    assert "=====  =====" in result
    assert "A      B" in result


def test_simple_table_adjacent_separators_no_content():
    """Two separators with nothing between → no header → returns None."""
    text = "=====  =====\n=====  ====="
    result = _convert_rst_simple_tables(text)
    assert "=====  =====" in result


# ---------------------------------------------------------------------------
# Coverage: _convert_rst_grid_tables edge cases
# ---------------------------------------------------------------------------


def test_grid_table_no_header_border():
    """No header border → first body row becomes header."""
    text = "+------+------+\n| A    | B    |\n| 1    | 2    |\n+------+------+"
    result = _convert_rst_grid_tables(text)
    assert "| A | B |" in result
    assert "| 1 | 2 |" in result


def test_grid_table_interrupted_by_non_table_line():
    """Non-matching line mid-collection triggers else-break."""
    text = "+------+------+\n| A    | B    |\nsomething else\n+------+------+"
    result = _convert_rst_grid_tables(text)
    assert "| A | B |" in result
    assert "something else" in result


def test_grid_table_header_border_but_no_header_rows():
    """Header border present but no rows before it → returns None."""
    text = "+------+------+\n+======+======+\n| 1    | 2    |\n+------+------+"
    result = _convert_rst_grid_tables(text)
    assert "+------+------+" in result
