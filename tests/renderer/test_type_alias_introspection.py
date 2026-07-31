"""Tests for objects whose canonical path cannot be read off the runtime object."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import griffe as gf
import pytest


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
