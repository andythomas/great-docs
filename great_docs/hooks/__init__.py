"""
Public registration surface for the API-reference pipeline events

Each event lives in its own module; only the `on_<event>` decorators are
public. The emitters are internal and imported from their event module.
"""

from ._docstring_parsed import on_docstring_parsed
from ._object_resolved import on_object_resolved

__all__ = ["on_docstring_parsed", "on_object_resolved"]
