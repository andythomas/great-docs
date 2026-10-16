"""
Preferred page addresses for canonical links

Rendered pages receive canonical links during Quarto rendering. Raw custom
pages bypass Quarto and receive their links here. Older documentation
versions use the latest version's base address to link to matching pages.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from . import head

if TYPE_CHECKING:
    from ..config import Config

FILTER = "page-url"
BASE_URL_KEY = "gd-base-url"
CANONICAL_KEY = "gd-canonical"
_CANONICAL_LINK = re.compile(r"""rel=["']?canonical""")


def resolve_base_url(
    config: Config, github_owner: str | None, github_repo: str | None
) -> str | None:
    """
    Resolve the address that canonical links, sitemaps and robots files use

    Prefer `seo.canonical.base_url`, which names the preferred address when it
    differs from where the site is served. Then use `site_url`, then the GitHub
    Pages address of the repository.

    Parameters
    ----------
    config
        Project configuration.
    github_owner
        Owner of the project's GitHub repository, if it has one.
    github_repo
        Name of the project's GitHub repository, if it has one.

    Returns
    -------
    :
        The address with a trailing slash, or `None` when none is known.
    """
    base_url = config.canonical_base_url or config.site_url
    if base_url:
        return base_url.rstrip("/") + "/"
    if github_owner and github_repo:
        return f"https://{github_owner}.github.io/{github_repo}/"
    return None


def address(base_url: str, page_path: str) -> str:
    """
    Build the address of a page, mapping an `index.html` to its directory

    Parameters
    ----------
    base_url
        The site address with a trailing slash.
    page_path
        The page's path relative to the site root.

    Returns
    -------
    :
        The page's address.
    """
    if page_path == "index.html" or page_path.endswith("/index.html"):
        page_path = page_path.removesuffix("index.html")
    return base_url + page_path


def register(quarto_config: dict, config: Config, base_url: str | None, project_dir: Path) -> None:
    """
    Register the filter that adds a canonical link to each rendered page

    Register nothing when canonical links are disabled, `base_url` is empty, or
    the site's header includes already declare a canonical link.

    Parameters
    ----------
    quarto_config
        Contents of `_quarto.yml`, updated in place.
    config
        Project configuration.
    base_url
        The site address with a trailing slash.
    project_dir
        Base directory for relative header file paths.
    """
    if not config.canonical_enabled or not base_url:
        return
    if head.includes_match(quarto_config, project_dir, _CANONICAL_LINK):
        return
    filters = quarto_config.setdefault("filters", [])
    if FILTER not in filters:
        filters.append(FILTER)
    quarto_config[BASE_URL_KEY] = base_url
    quarto_config[CANONICAL_KEY] = True


def add_to_raw_page(html: str, config: Config, base_url: str | None, page_path: str) -> str:
    """
    Add a canonical link to a raw custom page

    Leave the page unchanged when canonical links are disabled, `base_url` is
    empty, the page has a canonical link already, or it has no `<head>`.

    Parameters
    ----------
    html
        The page source.
    config
        Project configuration.
    base_url
        The site address with a trailing slash.
    page_path
        The page's path relative to the site root.

    Returns
    -------
    :
        The page with the link added.
    """
    if not config.canonical_enabled or not base_url:
        return html
    tag = f'<link rel="canonical" href="{address(base_url, page_path)}">'
    return head.insert(html, tag, unless='rel="canonical"')
