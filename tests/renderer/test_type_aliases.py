"""Tests for PEP 695 type alias support (`type X = ...`)."""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason="PEP 695 `type` statement requires Python 3.12+",
)


def _load_type_parameters(code: str, name: str):
    """Load the type parameters of the named alias from a source snippet"""
    import griffe as gf

    with gf.temporary_visited_package("package", {"__init__.py": code}) as m:
        return m[name].type_parameters


@pytest.mark.parametrize(
    ("source", "name", "expected"),
    [
        ("type Simple = int | str", "Simple", ""),
        ("type ListOrSet[T] = list[T] | set[T]", "ListOrSet", "[T]"),
        ("type Bounded[T: str] = list[T]", "Bounded", "[T: str]"),
        ("type Constrained[S: (str, bytes)] = list[S]", "Constrained", "[S: (str, bytes)]"),
        ("type Variadic[T, *Ts] = tuple[T, *Ts]", "Variadic", "[T, *Ts]"),
        ("type Callback[**P] = dict[P, int]", "Callback", "[**P]"),
        ("type WithDefault[T = int] = list[T]", "WithDefault", "[T = int]"),
    ],
)
def test_render_type_parameters(source: str, name: str, expected: str):
    from great_docs._apiref._render._type_parameters import render_type_parameters

    assert render_type_parameters(_load_type_parameters(source, name)) == expected


def test_render_type_parameters_none():
    from great_docs._apiref._render._type_parameters import render_type_parameters

    assert render_type_parameters(None) == ""


def _load_member(code: str, name: str):
    """Load a single named member from a source snippet"""
    import griffe as gf

    with gf.temporary_visited_package("package", {"__init__.py": code}) as m:
        return m[name]


def test_label_pep695_spelling():
    from great_docs._apiref._render._label import get_label

    obj = _load_member("type Contract = int | str", "Contract")
    assert get_label(obj) == "typealias"


def test_label_legacy_spelling():
    from great_docs._apiref._render._label import get_label

    code = "from typing import TypeAlias\nContract: TypeAlias = int | str\n"
    obj = _load_member(code, "Contract")
    assert get_label(obj) == "typealias"


def test_label_bare_typevar_is_constant():
    """A bare `T = TypeVar("T")` has no annotation, so it labels as a constant"""
    from great_docs._apiref._render._label import get_label

    code = 'from typing import TypeVar\nT = TypeVar("T")\n'
    assert get_label(_load_member(code, "T")) == "constant"


def test_label_plain_constant_still_works():
    from great_docs._apiref._render._label import get_label

    assert get_label(_load_member("MAX: int = 3\n", "MAX")) == "constant"


def test_from_griffe_builds_a_type_alias_node():
    from great_docs._apiref.content import DocTypeAlias, Doc

    obj = _load_member("type Contract = int | str", "Contract")
    doc = Doc.from_griffe("Contract", obj)

    assert isinstance(doc, DocTypeAlias)
    assert doc.kind == "type alias"
    assert doc.name == "Contract"
    assert doc.anchor == "package.Contract"


def _render_alias(source: str, name: str) -> str:
    """Render the named alias from a source snippet to qmd"""
    from great_docs._apiref._tools import render_code_variable

    return render_code_variable(source, name)


def test_reported_crash_no_longer_raises():
    """The reproducer from issue #288."""
    source = 'from typing import Literal\n\ntype Contract = Literal["a", "b"]\n'
    qmd = _render_alias(source, "Contract")
    assert "Contract" in qmd


@pytest.mark.parametrize(
    ("source", "name", "expected"),
    [
        (
            'from typing import Literal\ntype Contract = Literal["a", "b"]\n',
            "Contract",
            "[type]{.doc-type-alias-keyword .kw} [Contract]{.doc-parameter-name}"
            " [=]{.doc-parameter-default-sep .op}"
            " [Literal[[&quot;a&quot;]{.st}, [&quot;b&quot;]{.st}]]{.doc-parameter-default}",
        ),
        (
            "type ListOrSet[T] = list[T] | set[T]\n",
            "ListOrSet",
            "[type]{.doc-type-alias-keyword .kw} [ListOrSet[T]]{.doc-parameter-name}"
            " [=]{.doc-parameter-default-sep .op}"
            " [list[T] | set[T]]{.doc-parameter-default}",
        ),
        (
            "from typing import Callable\ntype Callback[**P] = Callable[P, int]\n",
            "Callback",
            "[type]{.doc-type-alias-keyword .kw} [Callback[**P]]{.doc-parameter-name}"
            " [=]{.doc-parameter-default-sep .op}"
            " [Callable[P, int]]{.doc-parameter-default}",
        ),
        (
            "type Bounded[T: str] = list[T]\n",
            "Bounded",
            "[type]{.doc-type-alias-keyword .kw} [Bounded[T: str]]{.doc-parameter-name}"
            " [=]{.doc-parameter-default-sep .op}"
            " [list[T]]{.doc-parameter-default}",
        ),
        (
            "type Constrained[S: (str, bytes)] = list[S]\n",
            "Constrained",
            "[type]{.doc-type-alias-keyword .kw}"
            " [Constrained[S: (str, bytes)]]{.doc-parameter-name}"
            " [=]{.doc-parameter-default-sep .op}"
            " [list[S]]{.doc-parameter-default}",
        ),
        (
            "type Variadic[T, *Ts] = tuple[T, *Ts]\n",
            "Variadic",
            "[type]{.doc-type-alias-keyword .kw} [Variadic[T, *Ts]]{.doc-parameter-name}"
            " [=]{.doc-parameter-default-sep .op}"
            " [tuple[T, *Ts]]{.doc-parameter-default}",
        ),
        (
            "type WithDefault[T = int] = list[T]\n",
            "WithDefault",
            "[type]{.doc-type-alias-keyword .kw} [WithDefault[T = int]]{.doc-parameter-name}"
            " [=]{.doc-parameter-default-sep .op}"
            " [list[T]]{.doc-parameter-default}",
        ),
    ],
)
def test_signature_rendering(source: str, name: str, expected: str):
    assert expected in _render_alias(source, name)


def test_css_class_slug_is_hyphenated():
    """A space in the class attribute would silently become two classes."""
    qmd = _render_alias("type Contract = int | str\n", "Contract")
    assert "doc-type-alias" in qmd
    assert "doc-type alias" not in qmd


def test_label_class_is_emitted():
    """The label class matches the existing `.doc-label-typealias` scss rule."""
    qmd = _render_alias("type Contract = int | str\n", "Contract")
    assert "doc-label-typealias" in qmd


def test_docstring_is_rendered():
    source = 'type Contract = int | str\n"""A contract kind."""\n'
    assert "A contract kind." in _render_alias(source, "Contract")


def test_recursive_alias_renders():
    """Lazy evaluation means the value is never resolved, so this must not raise."""
    qmd = _render_alias("type Recursive = Recursive | None\n", "Recursive")
    assert "[Recursive | None]{.doc-parameter-default}" in qmd


def test_forward_reference_alias_renders():
    """The static `.value` expression is unresolved, so an undefined name is fine."""
    qmd = _render_alias("type Broken = NotDefinedAnywhere\n", "Broken")
    assert "NotDefinedAnywhere" in qmd


def test_valueless_alias_omits_default_clause():
    """A `TypeAlias` with no `.value` must not render the literal string 'None'.

    `type X = ...` always has a value when parsed from source, so this state
    is constructed directly rather than via `_render_alias`.
    """
    import griffe as gf

    from great_docs._apiref._render import get_render_type
    from great_docs._apiref.content import Doc

    obj = gf.TypeAlias(name="Empty", lineno=1)
    assert obj.value is None

    doc = Doc.from_griffe("Empty", obj)
    qmd = str(get_render_type(doc)(doc, 1))

    assert "None" not in qmd
    assert "doc-parameter-default-sep" not in qmd
