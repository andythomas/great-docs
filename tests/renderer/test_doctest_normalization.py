import griffe as gf
import pytest

from great_docs._builtin.normalization._doctest import normalize_doctests


def _function(text: str, parser: str) -> gf.Function:
    """Build a function with a docstring parsed in the selected style"""
    obj = gf.Function("process")
    obj.docstring = gf.Docstring(text, parent=obj, parser=parser)
    return obj


@pytest.mark.parametrize("parser", ["numpy", "google", "sphinx"])
def test_doctests_are_fenced_for_every_parser(parser: str):
    obj = _function("Example.\n\n>>> for i in range(2):\n...     print(i)\n0\n1", parser)

    result = normalize_doctests(obj)

    assert result is obj
    assert obj.docstring.value == (
        "Example.\n\n```python\n>>> for i in range(2):\n...     print(i)\n```\n0\n1"
    )


def test_separate_doctest_groups_get_separate_fences():
    obj = _function(">>> first()\nText.\n>>> second()", "numpy")

    normalize_doctests(obj)

    assert obj.docstring.value.count("```python") == 2
    assert obj.docstring.value.count("```") == 4


@pytest.mark.parametrize(
    "source",
    [
        "Ordinary prose.",
        "```python\n>>> already_fenced()\n```",
        "```{python}\n>>> executable_cell()\n```",
    ],
)
def test_doctest_normalization_preserves_non_targets(source: str):
    obj = _function(source, "numpy")

    normalize_doctests(obj)

    assert obj.docstring.value == source


def test_doctest_normalization_registers_on_import():
    from great_docs.hooks import _object_resolved

    assert normalize_doctests in _object_resolved.REGISTRY
