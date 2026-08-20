"""Numbered RST citation normalisation for every docstring parser"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from great_docs.hooks import on_object_resolved

if TYPE_CHECKING:
    import griffe as gf

_RST_CITATION_MARKER_RE = re.compile(r"^([ \t]*)\.\.\s+\[(\d+)\](?:[ \t]+(.*))?$", re.MULTILINE)
_RST_CITATION_URL_RE = re.compile(r'(?<![<"])(https?://\S+)(?![>"])')


@on_object_resolved(priority=20)  # pyright: ignore[reportArgumentType]
def normalize_citations(obj: gf.Object | gf.Alias) -> gf.Object | gf.Alias:
    """
    Convert numbered RST citations in a resolved object's docstring

    Citation conversion applies to every docstring parser.

    Parameters
    ----------
    obj
        The resolved object.

    Returns
    -------
    The resolved object with converted citation markers.
    """
    docstring = obj.docstring
    if docstring is None:
        return obj

    docstring.value = _convert_rst_citations(docstring.value)
    return obj


def _convert_rst_citations(text: str) -> str:
    """Convert numbered RST citations to Markdown ordered-list items"""
    if not _RST_CITATION_MARKER_RE.search(text):
        return text

    lines = text.split("\n")
    result: list[str] = []
    index = 0
    while index < len(lines):
        match = _RST_CITATION_MARKER_RE.match(lines[index])
        if match is None:
            result.append(lines[index])
            index += 1
            continue

        indent, number, inline_body = match.group(1), match.group(2), match.group(3)
        marker_width = len(indent)
        parts = [inline_body.strip()] if inline_body and inline_body.strip() else []

        while index + 1 < len(lines):
            next_line = lines[index + 1]
            if not next_line.strip():
                break
            next_indent = len(next_line) - len(next_line.lstrip(" \t"))
            if next_indent <= marker_width or _RST_CITATION_MARKER_RE.match(next_line):
                break
            index += 1
            parts.append(next_line.strip())

        body = _RST_CITATION_URL_RE.sub(r"<\1>", " ".join(parts))
        result.append(f"{indent}{number}. {body}")
        index += 1

    return "\n".join(result)
