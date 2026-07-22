"""The built-in `%seealso` section directive"""

from __future__ import annotations

import re

import griffe as gf

from great_docs._utils import parse_seealso
from great_docs.hooks import on_object_resolved

_SEEALSO_LINE_RE = re.compile(
    r"^[^\S\r\n]*%seealso(?:[^\S\r\n]+[^\r\n]*)?[^\S\r\n]*\r?$\n?",
    re.MULTILINE,
)
_SEEALSO_TITLE = "see also"


@on_object_resolved(priority=100)  # pyright: ignore[reportArgumentType]
def add_seealso(obj: gf.Object | gf.Alias) -> gf.Object | gf.Alias:
    """
    Merge an object's `%seealso` entries into its See Also section

    Parameters
    ----------
    obj
        The resolved object.

    Returns
    -------
    The object with directive lines removed and their unique entries merged
    into its See Also section.
    """
    docstring = obj.docstring
    if docstring is None or "%seealso" not in docstring.value:
        return obj

    value = docstring.value
    cleaned = _strip_seealso(value)
    if cleaned == value:
        return obj

    docstring.value = cleaned
    docstring.__dict__.pop("parsed", None)

    entries = parse_seealso(value)
    if not entries:
        return obj

    sections = docstring.parsed
    existing = _find_see_also(sections)
    seen: set[str] = _existing_names(existing.value.contents) if existing is not None else set()
    added: list[str] = []
    for name, description in entries:
        if name in seen:
            continue
        seen.add(name)
        added.append(_entry_line(name, description))

    if existing is not None:
        if added:
            existing.value.contents = "\n".join([existing.value.contents, *added])
    else:
        body = "\n".join(added)
        sections.append(gf.DocstringSectionAdmonition(kind="see-also", text=body, title="See Also"))

    return obj


def _strip_seealso(text: str) -> str:
    """
    Remove `%seealso` directive lines and collapse excess gaps

    Parameters
    ----------
    text
        Docstring text containing `%seealso` directives.

    Returns
    -------
    The text with directive lines removed and excess blank lines collapsed.
    """
    cleaned = _SEEALSO_LINE_RE.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _entry_line(name: str, description: str) -> str:
    """
    Format a See Also entry with its optional description

    Parameters
    ----------
    name
        The referenced object name.
    description
        An optional description of the referenced object.

    Returns
    -------
    A formatted See Also entry.
    """
    return f"{name} : {description}" if description else name


def _find_see_also(
    sections: list[gf.DocstringSection],
) -> gf.DocstringSectionAdmonition | None:
    """
    Return the first See Also admonition in a sequence of sections

    Parameters
    ----------
    sections
        Parsed docstring sections to search.

    Returns
    -------
    The first matching See Also section, or `None` when none exists.
    """
    for section in sections:
        if (
            isinstance(section, gf.DocstringSectionAdmonition)
            and (section.title or "").lower() == _SEEALSO_TITLE
        ):
            return section
    return None


def _existing_names(contents: str) -> set[str]:
    """
    Collect qualified names already represented in a See Also body

    Parameters
    ----------
    contents
        The contents of a See Also section.

    Returns
    -------
    The qualified names represented in the section.
    """
    names: set[str] = set()
    for line in contents.splitlines():
        name_part = line.split(":", 1)[0]
        for part in name_part.split(","):
            if match := re.match(r"\s*([\w.]+)", part):
                names.add(match.group(1))
    return names
