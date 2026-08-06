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


def test_legacy_spelling_keeps_the_author_docstring(monkeypatch, tmp_path):
    """`X: TypeAlias = ...` keeps its own docstring rather than its value's"""
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


def test_subscripted_generic_keeps_the_author_docstring(monkeypatch, tmp_path):
    """`X: TypeAlias = list[int]` keeps its own docstring rather than `list`'s

    A `types.GenericAlias` forwards unknown attributes to its origin, so asking
    it for `__dict__` answers with `list.__dict__` — which does carry a
    `__doc__`. Both load paths must see through that.
    """
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_subscripted",
        {
            "__init__.py": '''
                """Package."""
                from typing import TypeAlias

                Row: TypeAlias = list[int]
                """One row of counts."""

                Table: TypeAlias = dict[str, int]
                """Counts by name."""
            '''
        },
    )
    _install(monkeypatch, root)

    static = get_object("gdta_subscripted:Row")
    replace_docstring(static)
    assert static.docstring is not None
    assert static.docstring.value == "One row of counts."

    dynamic = get_object("gdta_subscripted:Row", dynamic=True)
    assert dynamic.docstring is not None
    assert dynamic.docstring.value == "One row of counts."

    mapping = get_object("gdta_subscripted:Table", dynamic=True)
    assert mapping.docstring is not None
    assert mapping.docstring.value == "Counts by name."


def test_annotated_scalar_keeps_its_own_docstring(monkeypatch, tmp_path):
    """`count: int = 1` documents the count, not `int`'s constructor

    Only dynamic loading can get this wrong: reaching `count` at run time yields
    the value `1`, whose `__doc__` is `int`'s, while the static model reads the
    docstring under the declaration and nothing else.
    """
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_annotated_scalar",
        {
            "__init__.py": '''
                """Package."""

                count: int = 1
                """The count"""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_annotated_scalar:count", dynamic=True)

    assert obj.kind.value == "attribute"
    assert obj.docstring is not None
    assert obj.docstring.value == "The count"


def test_attribute_holding_a_module_keeps_the_author_docstring(monkeypatch, tmp_path):
    """`parser = json` documented by its author keeps that docstring, not the module's"""
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_module_value",
        {
            "__init__.py": '''
                """Package."""
                import json

                parser = json
                """The JSON parser we standardised on."""
            '''
        },
    )
    _install(monkeypatch, root)

    static = get_object("gdta_module_value:parser")
    replace_docstring(static)
    assert static.docstring is not None
    assert static.docstring.value == "The JSON parser we standardised on."

    dynamic = get_object("gdta_module_value:parser", dynamic=True)
    assert dynamic.docstring is not None
    assert dynamic.docstring.value == "The JSON parser we standardised on."


def test_documented_callable_alias_is_one_consistent_node(monkeypatch, tmp_path):
    """A documented `g = f` renders as a function carrying the author's docstring

    The attribute is still promoted so it gets a signature, but the docstring
    the author wrote under the assignment outranks `f`'s own, and the parent's
    member is the promoted function rather than the attribute it replaced.
    """
    from great_docs._apiref.introspect import get_object, make_loader

    root = _write_package(
        tmp_path,
        "gdta_callable_alias",
        {
            "__init__.py": '''
                """Package."""


                def f(x, y=1):
                    """The real f."""


                g = f
                """The g alias."""
            '''
        },
    )
    _install(monkeypatch, root)

    loader = make_loader()
    obj = get_object("gdta_callable_alias:g", dynamic=True, loader=loader)
    again = get_object("gdta_callable_alias:g", dynamic=True, loader=loader)

    for resolved in (obj, again):
        assert resolved.kind.value == "function"
        assert resolved.docstring is not None
        assert resolved.docstring.value == "The g alias."
        assert [p.name for p in resolved.parameters] == ["x", "y"]

    # The promotion re-registers the member on the parent; returning the
    # attribute it replaced would leave the module listing disagreeing with the
    # per-object page.
    assert obj.parent is not None
    assert obj.parent.members["g"] is obj


def test_documented_alias_to_an_undocumented_function_is_still_promoted(monkeypatch, tmp_path):
    """`g = f` renders as a function even when `f` carries no docstring of its own

    The kind follows the value, so an absent runtime docstring is nothing for
    the promotion to depend on.
    """
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_undocumented_callable",
        {
            "__init__.py": '''
                """Package."""


                def f(x, y=1): ...


                g = f
                """The g alias."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_undocumented_callable:g", dynamic=True)

    assert obj.kind.value == "function"
    assert [p.name for p in obj.parameters] == ["x", "y"]
    assert obj.docstring is not None
    assert obj.docstring.value == "The g alias."


def test_promoting_an_alias_leaves_the_function_it_points_at_alone(monkeypatch, tmp_path):
    """Documenting `g = f` must not rewrite what `f`'s own page says

    The promotion registers a separate node for `g`, which is what keeps the
    author's words about one name off the other's page.
    """
    from great_docs._apiref.introspect import get_object, make_loader

    root = _write_package(
        tmp_path,
        "gdta_no_docstring_leak",
        {
            "__init__.py": '''
                """Package."""


                def f(x):
                    """The real f."""


                g = f
                """The g alias."""
            '''
        },
    )
    _install(monkeypatch, root)

    # One loader, so both reads share the static model a leak would show up in.
    loader = make_loader()
    g = get_object("gdta_no_docstring_leak:g", dynamic=True, loader=loader)
    f = get_object("gdta_no_docstring_leak:f", dynamic=True, loader=loader)

    assert g.docstring is not None
    assert g.docstring.value == "The g alias."
    assert f.docstring is not None
    assert f.docstring.value == "The real f."


def test_documenting_a_reexport_leaves_the_class_it_points_at_alone(monkeypatch, tmp_path):
    """Documenting `Widget = Thing` must not rewrite what `Thing`'s own page says

    Both names are documented here, so a docstring written for one of them
    landing on the other would make each page depend on which was read last.
    """
    from great_docs._apiref.introspect import get_object, make_loader

    root = _write_package(
        tmp_path,
        "gdta_class_docstring_leak",
        {
            "__init__.py": '''
                """Package."""


                class Thing:
                    """The implementation class."""

                    def press(self):
                        """Press it."""


                Widget = Thing
                """Our widget."""
            '''
        },
    )
    _install(monkeypatch, root)

    # One loader, so both reads share the static model a leak would show up in.
    loader = make_loader()
    widget = get_object("gdta_class_docstring_leak:Widget", dynamic=True, loader=loader)
    thing = get_object("gdta_class_docstring_leak:Thing", dynamic=True, loader=loader)

    assert thing.docstring is not None
    assert thing.docstring.value == "The implementation class."
    assert widget.docstring is not None
    assert widget.docstring.value == "Our widget."
    assert "press" in widget.members


def test_documented_class_reexport_documents_the_class(monkeypatch, tmp_path):
    """A documented `Widget = _W` documents the class under the name and docstring given it

    The value decides the kind, so the class's members survive the re-export;
    the docstring written under the assignment is the newer of the two and wins,
    and the name it documents is the one the reader reaches the class by.
    """
    from great_docs._apiref.introspect import get_object, make_loader

    root = _write_package(
        tmp_path,
        "gdta_documented_reexport",
        {
            "__init__.py": '''
                """Package."""


                class _W:
                    """The implementation class."""

                    def press(self):
                        """Press it."""


                Widget = _W
                """Our widget."""
            '''
        },
    )
    _install(monkeypatch, root)

    loader = make_loader()
    obj = get_object("gdta_documented_reexport:Widget", dynamic=True, loader=loader)
    again = get_object("gdta_documented_reexport:Widget", dynamic=True, loader=loader)

    for resolved in (obj, again):
        assert resolved.kind.value == "class"
        assert resolved.canonical_path == "gdta_documented_reexport.Widget"
        assert "press" in resolved.members
        assert resolved.docstring is not None
        assert resolved.docstring.value == "Our widget."
        assert resolved.docstring.parent is resolved


def test_module_level_value_that_owns_its_docstring_is_used(monkeypatch, tmp_path):
    """A module attribute whose value sets its own `__doc__` documents that value's docstring"""
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_owned_module",
        {
            "__init__.py": '''
                """Package."""


                class Holder:
                    """A holder."""

                    def __init__(self, doc):
                        self.__doc__ = doc


                setting = Holder("Set at import time.")
                """Static docstring."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_owned_module:setting")
    replace_docstring(obj)

    assert obj.docstring is not None
    assert obj.docstring.value == "Set at import time."


def test_class_attribute_value_that_owns_its_docstring_is_used(monkeypatch, tmp_path):
    """A class attribute holding a plain instance with its own `__doc__` uses it"""
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_owned_class",
        {
            "__init__.py": '''
                """Package."""


                class Holder:
                    """A holder."""

                    def __init__(self, doc):
                        self.__doc__ = doc


                class Client:
                    """A client."""

                    handler = Holder("Set at class-body time.")
                    """Static docstring."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_owned_class:Client.handler")
    replace_docstring(obj)

    assert obj.docstring is not None
    assert obj.docstring.value == "Set at class-body time."


def test_class_level_descriptor_keeps_the_static_docstring(monkeypatch, tmp_path):
    """A descriptor's computed value must not document the attribute

    `_locate_runtime_object` reaches the attribute with plain `getattr`, which
    invokes `__get__`, so the runtime object is the computed value (an `int`
    here) and never the descriptor. The author's docstring is the only truthful
    source in that case.
    """
    from great_docs._apiref.introspect import get_object, replace_docstring

    root = _write_package(
        tmp_path,
        "gdta_descriptor",
        {
            "__init__.py": '''
                """Package."""


                class DocProperty:
                    """A descriptor."""

                    def __init__(self, doc):
                        self.__doc__ = doc

                    def __get__(self, obj, cls=None):
                        return 42


                class Client:
                    """A client."""

                    retries = DocProperty("Runtime docstring.")
                    """How many times a failed request is retried."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_descriptor:Client.retries")
    replace_docstring(obj)

    assert obj.docstring is not None
    assert obj.docstring.value == "How many times a failed request is retried."


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


def test_documented_legacy_alias_is_not_swapped_for_its_value(monkeypatch, tmp_path):
    """A documented `X: TypeAlias = ...` documents the name, not the typing object"""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_swap_documented",
        {
            "__init__.py": '''
                """Package."""
                from typing import Literal, TypeAlias

                Mode: TypeAlias = Literal["r", "w"]
                """How the file is opened."""
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_swap_documented:Mode", dynamic=True)

    assert obj.canonical_path == "gdta_swap_documented.Mode"
    assert obj.kind.value == "attribute"
    assert obj.docstring is not None
    assert obj.docstring.value == "How the file is opened."


def test_annotated_alias_is_not_swapped_when_undocumented(monkeypatch, tmp_path):
    """A typing construct is neither a class nor a function, so the name keeps documenting itself"""
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_swap_annotated",
        {
            "__init__.py": '''
                """Package."""
                from typing import Literal, TypeAlias

                Mode: TypeAlias = Literal["r", "w"]
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_swap_annotated:Mode", dynamic=True)

    assert obj.canonical_path == "gdta_swap_annotated.Mode"
    assert obj.kind.value == "attribute"
    assert obj.docstring is None


def test_bare_assignment_still_documents_its_value(monkeypatch, tmp_path):
    """A bare `Handler = dict` documents the class, as any name holding a class does

    Documented or not, a class-valued name resolves to the class; here there is
    no docstring of the author's for it to carry over.
    """
    from great_docs._apiref.introspect import get_object

    root = _write_package(
        tmp_path,
        "gdta_swap_bare",
        {
            "__init__.py": '''
                """Package."""

                Handler = dict
            '''
        },
    )
    _install(monkeypatch, root)

    obj = get_object("gdta_swap_bare:Handler", dynamic=True)

    assert obj.canonical_path == "builtins.dict"
    assert obj.kind.value == "class"
