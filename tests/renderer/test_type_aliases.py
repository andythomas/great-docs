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
