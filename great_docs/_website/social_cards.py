"""
Open Graph and Twitter card metadata for shared links

Generate social card tags unless the site's header includes already contain
an Open Graph property. Quarto does not check for existing tags, so this
avoids duplicates. Configure Quarto's `open-graph` and `twitter-card` options
for most tags, and add the page type and preferred URL separately.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import head

if TYPE_CHECKING:
    from ..config import Config

OG_TYPE_TAG = '<meta property="og:type" content="website">'
_OG_PROPERTY = re.compile(r"""property=["']?og:""")


def applies(quarto_config: dict[str, Any], config: Config, project_dir: Path) -> bool:
    """
    Check whether to generate social card tags for rendered pages

    Parameters
    ----------
    quarto_config
        Contents of `_quarto.yml`.
    config
        Project configuration.
    project_dir
        Base directory for relative header file paths.

    Returns
    -------
    :
        `True` when social cards are enabled and the site's header includes
        contain no Open Graph property.
    """
    return config.social_cards_enabled and not head.includes_match(
        quarto_config, project_dir, _OG_PROPERTY
    )


def twitter_handle(handle: str) -> str:
    """
    Normalise a Twitter/X handle to start with `@`

    Parameters
    ----------
    handle
        The handle, with or without its `@`.

    Returns
    -------
    :
        The handle, prefixed with `@` if needed.
    """
    return handle if handle.startswith("@") else f"@{handle}"


def register(
    quarto_config: dict[str, Any], config: Config, image_url: str | None, project_dir: Path
) -> None:
    """
    Enable Quarto's Open Graph and Twitter card tags for the whole site

    Without `image_url`, Quarto picks each page's preview image from its
    content.

    Parameters
    ----------
    quarto_config
        Contents of `_quarto.yml`, updated in place.
    config
        Project configuration.
    image_url
        The default card image address, or `None` to use page images.
    project_dir
        Base directory for relative header file paths.
    """
    if not applies(quarto_config, config, project_dir):
        return

    open_graph: dict[str, str] = {}
    twitter_card: dict[str, str] = {}
    if image_url:
        open_graph["image"] = image_url
        twitter_card["image"] = image_url
    if config.social_cards_twitter_card:
        twitter_card["card-style"] = config.social_cards_twitter_card
    if config.social_cards_twitter_site:
        twitter_card["site"] = twitter_handle(config.social_cards_twitter_site)

    website = quarto_config.setdefault("website", {})
    website["open-graph"] = open_graph or True
    website["twitter-card"] = twitter_card or True
