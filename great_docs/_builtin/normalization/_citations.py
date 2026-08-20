"""Numbered RST citation normalisation for every docstring parser"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from great_docs.hooks import on_object_resolved

if TYPE_CHECKING:
    import griffe as gf

_RST_CITATION_MARKER_RE = re.compile(r"^([ \t]*)\.\.\s+\[(\d+)\](?:[ \t]+(.*))?$", re.MULTILINE)
_RST_CITATION_URL_RE = re.compile(r'(?<![<"])(https?://\S+)(?![>"])')


def _wrap_url(match: re.Match[str]) -> str:
    """
    Wrap a detected URL without enclosing trailing punctuation

    URL detection consumes every non-space character, including a parenthesis
    that closes a surrounding Markdown link. Move only unmatched trailing
    parentheses outside the angle brackets so balanced URL paths remain intact.

    Parameters
    ----------
    match
        The detected URL.

    Returns
    -------
    The angle-bracketed URL followed by any unmatched closing parentheses.
    """
    url = match.group(1)
    trailer = ""
    while url.endswith(")") and url.count("(") < url.count(")"):
        trailer = url[-1] + trailer
        url = url[:-1]
    return f"<{url}>{trailer}"
_RST_CITATION_REF_RE = re.compile(r"\[(\d+)\]_")
_NON_ANCHOR_CHARS_RE = re.compile(r"[^A-Za-z0-9_]+")

_CITE_REF_CLASS = ".gd-cite-ref"
_CARET_CLASSES = ".gd-linkback-text .gd-linkback-caret"
_LETTER_CLASSES = ".gd-linkback-text .gd-linkback-letter"


@on_object_resolved(priority=20)  # pyright: ignore[reportArgumentType]
def normalize_citations(obj: gf.Object | gf.Alias) -> gf.Object | gf.Alias:
    """
    Convert numbered RST citations and references in a resolved object

    Citations and matching `[N]_` references link in both directions.
    Conversion applies to every docstring parser.

    Parameters
    ----------
    obj
        The resolved object.

    Returns
    -------
    The resolved object with converted citations and references.
    """
    docstring = obj.docstring
    if docstring is None:
        return obj

    docstring.value = _convert_rst_citations(docstring.value, _anchor_slug(obj.path))
    return obj


def _anchor_slug(path: str) -> str:
    """
    Convert an object path to a citation-anchor stem

    Keep letters, digits, and underscores as written. Replace each run of other
    characters with a hyphen so paths that differ by case or separator remain
    distinct.

    Parameters
    ----------
    path
        The resolved object's dotted path.

    Returns
    -------
    The path with other character runs replaced by hyphens.
    """
    return _NON_ANCHOR_CHARS_RE.sub("-", path).strip("-")


def _occurrence_label(index: int) -> str:
    """
    Return the backlink label for a zero-based reference index

    Parameters
    ----------
    index
        The reference's zero-based position among those naming one citation.

    Returns
    -------
    A letter sequence running `a` to `z`, then `aa`, `ab`, and onwards.
    """
    label = ""
    position = index + 1
    while position:
        position, remainder = divmod(position - 1, 26)
        label = chr(ord("a") + remainder) + label
    return label


def _backlinks(anchor_stem: str, number: str, count: int) -> str:
    """
    Build a citation's return links

    One reference receives a linked caret. Multiple references receive an
    inert caret followed by one lettered link for each occurrence.

    Parameters
    ----------
    anchor_stem
        The stem shared by this object's anchors.
    number
        The citation's label.
    count
        The number of references that name this citation.

    Returns
    -------
    Markdown ending in a space, or the empty string when nothing names it.
    """
    if not count:
        return ""

    def back(index: int, text: str, classes: str) -> str:
        anchor = f"ref-{anchor_stem}-{number}-{index + 1}"
        return f'[{text}](#{anchor}){{{classes} role="doc-backlink"}}'

    if count == 1:
        return f"{back(0, '^', _CARET_CLASSES)} "

    caret = f"[^]{{{_CARET_CLASSES}}}"
    letters = " ".join(
        back(index, _occurrence_label(index), _LETTER_CLASSES) for index in range(count)
    )
    return f"{caret} {letters} "


def _convert_rst_citations(text: str, anchor_stem: str) -> str:
    """
    Convert numbered RST citations and link their references

    Each `[N]_` reference links to its matching citation. The citation links
    back with a caret for one reference or lettered links for several.
    References without matching citations remain literal.

    Duplicate labels are invalid RST. Both definitions reuse the same citation
    ID and backlinks because references are counted by label. A reference in a
    citation body links back to that same in-body reference.

    Parameters
    ----------
    text
        The docstring text.
    anchor_stem
        The stem shared by this object's citation and reference anchors.

    Returns
    -------
    The text with converted citations and bidirectional reference links.
    """
    defined = {match.group(2) for match in _RST_CITATION_MARKER_RE.finditer(text)}
    if not defined:
        return text

    counts: dict[str, int] = {}
    for match in _RST_CITATION_REF_RE.finditer(text):
        number = match.group(1)
        if number in defined:
            counts[number] = counts.get(number, 0) + 1

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

        body = _RST_CITATION_URL_RE.sub(_wrap_url, " ".join(parts))
        result.append(
            f"{indent}{number}. []{{#cite-{anchor_stem}-{number}}}"
            f"{_backlinks(anchor_stem, number, counts.get(number, 0))}{body}"
        )
        index += 1

    seen: dict[str, int] = {}

    def link(match: re.Match[str]) -> str:
        number = match.group(1)
        if number not in defined:
            return match.group(0)
        seen[number] = seen.get(number, 0) + 1
        anchor = f"ref-{anchor_stem}-{number}-{seen[number]}"
        return (
            f"[[{number}]](#cite-{anchor_stem}-{number})"
            f'{{#{anchor} {_CITE_REF_CLASS} role="doc-noteref"}}'
        )

    return _RST_CITATION_REF_RE.sub(link, "\n".join(result))
