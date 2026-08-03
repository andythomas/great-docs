"""
Great-docs' own handlers for the pipeline events

Importing this package imports each handler submodule, which registers its
handlers as a side effect.
"""

from . import directives as directives
from . import normalization as normalization

__all__: list[str] = []
