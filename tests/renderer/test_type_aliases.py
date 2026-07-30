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
