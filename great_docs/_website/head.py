"""
The `<head>` of built pages: header includes and edits to raw pages

Quarto renders most pages, and the site's header includes add to every one of
them. Raw custom pages bypass Quarto, so tags are added to them directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import re
    from pathlib import Path


def search_includes(
    includes: Any, base_dir: Path, pattern: re.Pattern[str]
) -> re.Match[str] | None:
    """
    Find the first match for `pattern` in an `include-in-header` value

    Parameters
    ----------
    includes
        An `include-in-header` value: a file path, an entry with `text` or
        `file`, or a list of them.
    base_dir
        Base directory for relative header file paths.
    pattern
        The markup to look for.

    Returns
    -------
    :
        The match in an inline entry or a readable header file, or `None`.
    """
    if not isinstance(includes, list):
        includes = [includes]
    for item in includes:
        if isinstance(item, dict):
            text = item.get("text")
            path = item.get("file")
        else:
            text, path = None, item
        if text is None and path is not None:
            try:
                text = (base_dir / str(path)).read_text(encoding="utf-8")
            except OSError:
                continue
        if isinstance(text, str) and (match := pattern.search(text)):
            return match
    return None


def site_includes(quarto_config: dict[str, Any]) -> Any:
    """
    Return the site's `include-in-header` value

    Parameters
    ----------
    quarto_config
        Contents of `_quarto.yml`.

    Returns
    -------
    :
        The value, or an empty list when the site has none.
    """
    return quarto_config.get("format", {}).get("html", {}).get("include-in-header", [])


def includes_match(
    quarto_config: dict[str, Any], project_dir: Path, pattern: re.Pattern[str]
) -> bool:
    """
    Check whether the site's header includes contain a match for `pattern`

    Parameters
    ----------
    quarto_config
        Contents of `_quarto.yml`.
    project_dir
        Base directory for relative header file paths.
    pattern
        The markup to look for.

    Returns
    -------
    :
        `True` when an inline entry or a readable header file matches.
    """
    return search_includes(site_includes(quarto_config), project_dir, pattern) is not None


def insert(html: str, tag: str, *, unless: str) -> str:
    """
    Insert a tag at the end of a page's `<head>`

    Parameters
    ----------
    html
        The page source.
    tag
        The element to insert.
    unless
        A string whose presence in the page means the tag already exists.

    Returns
    -------
    :
        The page with the tag added, or `html` unchanged when it contains
        `unless` or has no `</head>`.
    """
    if unless in html or "</head>" not in html:
        return html
    return html.replace("</head>", f"{tag}\n</head>", 1)
