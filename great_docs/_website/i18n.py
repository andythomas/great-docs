"""
Translations and text direction for sites in languages other than English

Quarto renders the translation bundle from a metadata partial and sets text
direction through its `dir` option. Raw custom pages bypass Quarto, so their
translation bundle is added directly.
"""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING

from .._translations import get_translations_bundle, is_rtl
from . import head

if TYPE_CHECKING:
    from ..config import Config

_META_NAME = 'name="gd-i18n"'


def register(quarto_config: dict, config: Config) -> None:
    """
    Default to right-to-left text for RTL languages

    Preserve an explicit `dir` setting in `site`. Leave the configuration
    unchanged if it has no HTML mapping.

    Parameters
    ----------
    quarto_config
        Contents of `_quarto.yml`, updated in place.
    config
        Project configuration.
    """
    html_config = quarto_config.get("format", {}).get("html")
    if isinstance(html_config, dict) and is_rtl(config.lang):
        html_config.setdefault("dir", "rtl")


def meta_tag(config: Config) -> str | None:
    """
    Build a meta element containing the translation bundle

    The `content` attribute contains an HTML-escaped JSON object of translated
    interface strings for client-side scripts.

    Parameters
    ----------
    config
        Project configuration.

    Returns
    -------
    :
        The element, or `None` for English. Client-side scripts already
        contain the English strings.
    """
    if config.lang == "en":
        return None
    bundle = json.dumps(
        get_translations_bundle(config.lang), ensure_ascii=False, separators=(",", ":")
    )
    return f'<meta {_META_NAME} content="{html.escape(bundle, quote=True)}">'


def add_to_raw_page(page: str, config: Config) -> str:
    """
    Add the translation bundle to a raw custom page

    Parameters
    ----------
    page
        The page source.
    config
        Project configuration.

    Returns
    -------
    :
        The page with the bundle in its `<head>`. Return `page` unchanged for
        English or when the page already contains the bundle.
    """
    tag = meta_tag(config)
    if tag is None:
        return page
    return head.insert(page, tag, unless=_META_NAME)
