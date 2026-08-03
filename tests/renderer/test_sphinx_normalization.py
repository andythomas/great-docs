import griffe as gf
import pytest

from great_docs._builtin.normalization._sphinx import normalize_sphinx_markup


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
        (".. [1] Author. https://example.com", "1. Author. <https://example.com>"),
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


def test_sphinx_normalization_registers_on_import():
    from great_docs.hooks import _object_resolved

    assert normalize_sphinx_markup in _object_resolved.REGISTRY
