"""
The `object_resolved` event — emitted per object once its reference resolves to a griffe object

A registered handler receives the resolved object and returns it (optionally
annotated or replaced), or `None` to skip it, before the API-reference resolver
builds its `Doc`. great-docs registers its own built-in handlers here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._registry import HookRegistry

if TYPE_CHECKING:
    import griffe as gf

ObjectResolvedHook = Callable[["gf.Object | gf.Alias"], "gf.Object | gf.Alias | None"]
"""A handler that inspects, replaces, or skips a resolved object"""

REGISTRY: HookRegistry[ObjectResolvedHook] = HookRegistry()
"""The object_resolved handlers, ordered by priority"""

on_object_resolved = REGISTRY.register
"""
Register a handler that customizes an object after resolution

Great Docs emits `object_resolved` before it parses the object's final
docstring or builds its API-reference document. A handler may inspect, mutate,
or replace the resolved object, or return `None` to exclude it.

After all handlers run, Great Docs invalidates the resulting object's
parsed-docstring cache so later parsing reflects the final `docstring.value`.
"""


def emit_object_resolved(obj: gf.Object | gf.Alias) -> gf.Object | gf.Alias | None:
    """
    Emit the `object_resolved` event and return the object its handlers produce

    Handlers run in priority order (lower first, ties in registration order);
    the first to return `None` skips the object and the rest are not consulted.

    Parameters
    ----------
    obj
        The object just resolved from its reference.

    Returns
    -------
    The object to document, or `None` when a handler skips it.
    """
    for hook in REGISTRY:
        result = hook(obj)
        if result is None:
            return None
        obj = result

    docstring = getattr(obj, "docstring", None)
    if docstring is not None:
        docstring.__dict__.pop("parsed", None)
    return obj
