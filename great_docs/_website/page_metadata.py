"""
Search descriptions and social card options for rendered pages

Prepend generated entries to page front matter before Quarto renders it.
Preserve the author's existing front matter, including comments.
"""

from __future__ import annotations

from collections.abc import Iterator
from fnmatch import fnmatchcase
from pathlib import Path
from typing import TYPE_CHECKING, Any

from yaml12 import format_yaml

from . import social_cards
from .seo import description

if TYPE_CHECKING:
    from ..config import Config


def rendered_pages(project_dir: Path, quarto_config: dict[str, Any]) -> Iterator[Path]:
    """
    Yield the Markdown pages eligible for Quarto rendering

    Parameters
    ----------
    project_dir
        The Quarto project directory.
    quarto_config
        Contents of its `_quarto.yml`.

    Returns
    -------
    :
        The `.qmd` and `.md` pages in path order.
    """
    render = quarto_config.get("project", {}).get("render", [])
    excluded = [p[1:] for p in render if isinstance(p, str) and p.startswith("!")]

    for path in sorted([*project_dir.rglob("*.qmd"), *project_dir.rglob("*.md")]):
        rel = path.relative_to(project_dir)
        # Quarto renders no file whose path has a part starting with `_` or `.`
        if any(part.startswith(("_", ".")) for part in rel.parts):
            continue
        if any(fnmatchcase(rel.as_posix(), pattern) for pattern in excluded):
            continue
        yield path


def add_to_page(content: str, entries: dict[str, Any]) -> str:
    """
    Add entries to the start of a page's front matter

    Parameters
    ----------
    content
        The page source.
    entries
        Front matter keys and their values. Values that are strings must
        already be escaped for Quarto's Markdown.

    Returns
    -------
    :
        The page with the entries prepended, creating front matter if needed.
    """
    block = format_yaml(entries).rstrip()
    if content.startswith("---\n"):
        return f"---\n{block}\n{content[4:]}"
    return f"---\n{block}\n---\n\n{content}"


def write_to_pages(
    project_dir: Path, quarto_config: dict[str, Any], config: Config, default: str | None
) -> list[Path]:
    """
    Write search descriptions and social card options into every rendered page

    When SEO is enabled, add `description-meta` to pages that lack a
    description. When social cards are enabled, add `open-graph` and
    `twitter-card` options to pages that set neither key. Skip each kind of
    metadata if the site's header includes already supply it. A page whose
    own header includes declare Open Graph tags gets options that switch the
    generated ones off.

    Parameters
    ----------
    project_dir
        The Quarto project directory.
    quarto_config
        Contents of its `_quarto.yml`, whose `website.title` names the site in
        card titles.
    config
        Project configuration.
    default
        The site's default description as plain text.

    Returns
    -------
    :
        The pages that were changed.
    """
    descriptions = description.applies(quarto_config, config, project_dir)
    cards = social_cards.applies(quarto_config, config, project_dir)
    if not (descriptions or cards):
        return []
    site_name = quarto_config.get("website", {}).get("title")
    header_description = description.header_description(quarto_config, project_dir)

    changed: list[Path] = []
    for path in rendered_pages(project_dir, quarto_config):
        content = path.read_text(encoding="utf-8")
        entries: dict[str, Any] = {}
        if descriptions and (value := description.page_description(content, default)):
            entries["description-meta"] = value
        if cards:
            entries.update(
                social_cards.page_entries(
                    content, path.parent, site_name, config, default, header_description
                )
            )
        if entries:
            path.write_text(add_to_page(content, entries), encoding="utf-8")
            changed.append(path)
    return changed
