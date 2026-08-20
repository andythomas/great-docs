"""Numbered RST citation normalisation for every docstring parser"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from great_docs.hooks import on_object_resolved

if TYPE_CHECKING:
    import griffe as gf

_RST_CITATION_RE = re.compile(r"^[ \t]*\.\.\s+\[(\d+)\]\s+", re.MULTILINE)
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
    if not _RST_CITATION_RE.search(text):
        return text

    lines = text.split("\n")
    result: list[str] = []
    index = 0
    while index < len(lines):
        match = _RST_CITATION_RE.match(lines[index])
        if match is None:
            result.append(lines[index])
            index += 1
            continue

        body = lines[index][match.end() :]
        while index + 1 < len(lines) and lines[index + 1] and lines[index + 1][0] in (" ", "\t"):
            index += 1
            body += " " + lines[index].strip()
        body = _RST_CITATION_URL_RE.sub(r"<\1>", body.strip())
        result.append(f"{match.group(1)}. {body}")
        index += 1

    return "\n".join(result)
