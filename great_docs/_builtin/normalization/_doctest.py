"""Parser-neutral doctest normalization"""

from __future__ import annotations

import griffe as gf

from great_docs.hooks import on_object_resolved


@on_object_resolved(priority=100)  # pyright: ignore[reportArgumentType]
def normalize_doctests(obj: gf.Object | gf.Alias) -> gf.Object | gf.Alias:
    """
    Fence unfenced doctest prompts as static Python examples

    Parameters
    ----------
    obj
        The resolved object.

    Returns
    -------
    The object with unfenced doctest groups converted to Python code fences.
    """
    docstring = obj.docstring
    if docstring is not None:
        docstring.value = _fence_doctest_blocks(docstring.value)
    return obj


def _fence_doctest_blocks(text: str) -> str:
    """
    Wrap each unfenced doctest prompt group in a static Python fence

    Parameters
    ----------
    text
        Docstring source that may contain doctest prompts.

    Returns
    -------
    The source with unfenced prompt groups wrapped in Python code fences.
    """
    lines = text.split("\n")
    result: list[str] = []
    doctest: list[str] = []
    in_fence = False

    def flush() -> None:
        """Append the pending doctest group as a static Python block"""
        if doctest:
            result.extend(["```python", *doctest, "```"])
            doctest.clear()

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```"):
            flush()
            in_fence = not in_fence
            result.append(line)
        elif not in_fence and (
            stripped.startswith(">>> ") or stripped == ">>>" or stripped.startswith("... ")
        ):
            doctest.append(line)
        else:
            flush()
            result.append(line)

    flush()
    return "\n".join(result)
