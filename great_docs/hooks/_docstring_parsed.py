"""
The `docstring_parsed` event for customizing structured docstring sections

Great Docs emits this event after Griffe parses a resolved object's final
docstring value and before the API-reference document is built. Objects
without docstrings do not receive this event.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from ._registry import HookRegistry

if TYPE_CHECKING:
    import griffe as gf

DocstringParsedHook = Callable[
    ["gf.Object | gf.Alias", "list[gf.DocstringSection]"],
    "list[gf.DocstringSection]",
]
"""A handler that customizes the parsed sections of a resolved object"""

REGISTRY: HookRegistry[DocstringParsedHook] = HookRegistry()
"""The `docstring_parsed` handlers, ordered by priority"""

on_docstring_parsed = REGISTRY.register
"""
Register a handler that customizes a parsed docstring

Great Docs emits `docstring_parsed` after Griffe parses the final docstring
value and before it builds the object's API-reference document. A handler
receives the resolved object and its parsed sections and returns the sections
to retain. Objects without docstrings do not receive this event.
"""


def emit_docstring_parsed(
    obj: gf.Object | gf.Alias,
) -> list[gf.DocstringSection]:
    """
    Apply the `docstring_parsed` handlers to an object's parsed sections

    Handlers run in priority order and each returned list becomes the input to
    the next handler. The final list becomes the docstring's cached parsed
    value.

    Parameters
    ----------
    obj
        A resolved object with a docstring.

    Returns
    -------
    The parsed sections produced by the handlers.

    Raises
    ------
    ValueError
        If the object has no docstring.
    TypeError
        If a handler returns `None`.
    """
    docstring = obj.docstring
    if docstring is None:
        raise ValueError("Cannot emit `docstring_parsed` for an object without a docstring")

    sections = docstring.parsed
    for hook in REGISTRY:
        result = cast("list[gf.DocstringSection] | None", hook(obj, sections))
        if result is None:
            raise TypeError(
                f"`docstring_parsed` handler {hook.__module__}.{hook.__name__} returned None"
            )
        sections = result

    docstring.__dict__["parsed"] = sections
    return sections
