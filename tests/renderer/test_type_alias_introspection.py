"""
Tests for the dynamic (introspection) load path

Two subjects share these fixtures: objects whose canonical path cannot be read
off the runtime object, and the docstrings of PEP 695 type aliases.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import griffe as gf
import pytest

# Applied per-test rather than module-wide: the canonical-path tests below carry
# no PEP 695 syntax and must keep running on 3.11.
requires_pep695 = pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason="PEP 695 `type` statement requires Python 3.12+",
)

BOILERPLATE = "Type aliases are created through the type statement"


def _write_package(tmp_path: Path, name: str, files: dict[str, str]) -> Path:
    """Write an importable package into `tmp_path` and return its parent directory"""
    pkg = tmp_path / name
    pkg.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (pkg / filename).write_text(textwrap.dedent(content))
    return tmp_path


def _install(monkeypatch, root: Path) -> None:
    """Make `root` importable and drop any cached modules under it"""
    monkeypatch.syspath_prepend(str(root))
    for mod in list(sys.modules):
        if mod.startswith("gdta_"):
            monkeypatch.delitem(sys.modules, mod, raising=False)


def test_reexported_instance_resolves_to_its_definition_module(monkeypatch, tmp_path):
    """A re-exported instance documents the module that defines it, not the facade."""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_reexported_singleton",
        {
            "_conf.py": '''
                class Config:
                    """A config object."""

                SETTINGS = Config()
            ''',
            "__init__.py": '''
                """Package."""

                from gdta_reexported_singleton._conf import SETTINGS
            ''',
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_reexported_singleton:SETTINGS", dynamic=True)

    assert obj.canonical_path == "gdta_reexported_singleton._conf.SETTINGS"


def test_future_annotations_member_does_not_cycle(monkeypatch, tmp_path):
    """`from __future__ import annotations` leaves a member that reports no home."""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_future_annotations",
        {
            "__init__.py": '''
                """Package."""

                from __future__ import annotations
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_future_annotations:annotations", dynamic=True)

    assert obj.canonical_path == "__future__.annotations"


def test_instance_defined_in_the_accessing_module_keeps_the_access_path(monkeypatch, tmp_path):
    """An instance that is not re-exported is documented where it was found."""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_local_singleton",
        {
            "__init__.py": '''
                """Package."""

                class Config:
                    """A config object."""

                SETTINGS = Config()
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_local_singleton:SETTINGS", dynamic=True)

    assert obj.canonical_path == "gdta_local_singleton.SETTINGS"


def test_trailing_colon_module_path_does_not_self_alias():
    """A degenerate `module:` path resolves the module, not a self-referential alias."""
    from great_docs._apiref.introspect import get_object

    obj = get_object("json.decoder:", dynamic=True)

    if isinstance(obj, gf.Alias):
        assert obj.target_path != obj.path


def test_a_genuine_alias_cycle_still_raises(monkeypatch, tmp_path):
    """A cycle the package really authored is reported, not silently absorbed."""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_alias_cycle",
        {
            "a.py": """
                from typing import TYPE_CHECKING

                if TYPE_CHECKING:
                    from gdta_alias_cycle import x
                else:
                    x = 1
            """,
            "__init__.py": '''
                """Package."""

                from gdta_alias_cycle.a import x
            ''',
        },
    )
    _install(monkeypatch, root)

    with pytest.raises(gf.CyclicAliasError):
        _ = get_object("gdta_alias_cycle:x", dynamic=True).canonical_path


@requires_pep695
def test_documented_alias_keeps_the_author_docstring(monkeypatch, tmp_path):
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_documented",
        {
            "__init__.py": '''
                """Package."""
                type Contract = int | str
                """The author's own docstring."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_documented:Contract")
    replace_docstring(obj)

    assert obj.docstring is not None
    assert obj.docstring.value == "The author's own docstring."
    assert BOILERPLATE not in obj.docstring.value


@requires_pep695
def test_undocumented_alias_gets_no_boilerplate(monkeypatch, tmp_path):
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_undocumented",
        {
            "__init__.py": '''
                """Package."""
                type Contract = int | str
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_undocumented:Contract")
    replace_docstring(obj)

    assert obj.docstring is None or BOILERPLATE not in obj.docstring.value


@requires_pep695
@pytest.mark.xfail(
    reason=(
        "Pre-existing bug unrelated to PEP 695: replace_docstring overwrites the "
        "statically-parsed docstring of any attribute whose runtime value carries a "
        "__doc__. Here `Contract: TypeAlias = int` picks up int.__doc__."
    ),
    strict=True,
)
def test_legacy_spelling_docstring_overwritten(monkeypatch, tmp_path):
    """Pins the pre-existing overwrite bug for `X: TypeAlias = ...` until it is fixed"""
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_legacy",
        {
            "__init__.py": '''
                """Package."""
                from typing import TypeAlias

                Contract: TypeAlias = int
                """Legacy docstring."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_legacy:Contract")
    replace_docstring(obj)

    assert obj.docstring is not None
    assert obj.docstring.value == "Legacy docstring."


@requires_pep695
def test_facade_reexport_resolves_without_cyclic_alias(monkeypatch, tmp_path):
    """A facade re-exported alias resolves and keeps its own docstring"""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_facade",
        {
            "__init__.py": '''
                """Facade."""
                from ._impl import Contract

                __all__ = ["Contract"]
            ''',
            "_impl.py": '''
                """Impl."""
                type Contract = int | str
                """Real docstring."""
            ''',
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_facade:Contract", dynamic=True)

    assert obj.kind.value == "type alias"
    assert obj.docstring is not None
    assert obj.docstring.value == "Real docstring."


@requires_pep695
def test_class_nested_alias_is_not_shadowed_by_a_module_level_one(monkeypatch, tmp_path):
    """A class-nested alias must resolve to itself, not to a same-named module-level alias

    A `TypeAliasType` reports no `__qualname__`, so nothing about the runtime
    object distinguishes the nested alias from the module-level one of the same
    name. Only the enclosing-class walk does, which makes this the case that
    catches a canonical path guessed from `__module__` + `__name__`.
    """
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_shadow",
        {
            "__init__.py": '''
                """Package."""
                type Inner = str
                """Module-level alias."""


                class Holder:
                    """A holder."""

                    type Inner = int
                    """Inner alias."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_shadow:Holder.Inner", dynamic=True)

    assert obj.canonical_path == "gdta_shadow.Holder.Inner"
    assert str(obj.value) == "int"
    assert obj.docstring is not None
    assert obj.docstring.value == "Inner alias."


@requires_pep695
def test_plain_alias_still_resolves_dynamically(monkeypatch, tmp_path):
    """The plain, non-re-exported case keeps working"""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_plain",
        {
            "__init__.py": '''
                """Package."""
                type Contract = int | str
                """Plain docstring."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_plain:Contract", dynamic=True)

    assert obj.kind.value == "type alias"
    assert obj.docstring is not None
    assert obj.docstring.value == "Plain docstring."


def test_non_alias_canonical_paths_unchanged():
    from great_docs._apiref.introspect import _canonical_path

    assert _canonical_path(len, "") == "builtins:len"
    assert _canonical_path(42, "") is None
