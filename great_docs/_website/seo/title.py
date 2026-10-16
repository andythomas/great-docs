"""
Page title templates

Apply `seo.title_template` when SEO is enabled, the template is valid, and
both the page title and site name are available. Otherwise retain Quarto's
title format.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from ...config import Config

PAGE_KEY = "{page_title}"
SITE_KEY = "{site_name}"
_KEYS = re.compile(r"(\{page_title\}|\{site_name\})")


def is_valid(template: object) -> TypeGuard[str]:
    """
    Check whether a configured title template can be applied

    Parameters
    ----------
    template
        Value of `seo.title_template`, which may have any type.

    Returns
    -------
    :
        `True` for a string containing `{page_title}` and no `$`. Pandoc
        interprets `$` as the start of a template expression.
    """
    return isinstance(template, str) and "$" not in template and PAGE_KEY in template


def template(config: Config) -> str | None:
    """
    Return the title template that shapes page titles

    Parameters
    ----------
    config
        Project configuration.

    Returns
    -------
    :
        The template, or `None` when SEO is disabled or the template is invalid.
    """
    value = config.seo_title_template
    return value if config.seo_enabled and is_valid(value) else None


def apply(
    template: str,
    page_title: str,
    site_name: str,
    *,
    escape: Callable[[str], str] | None = None,
) -> str:
    """
    Fill a title template with a page's title and the site's name

    Parameters
    ----------
    template
        A valid title template.
    page_title
        Text for `{page_title}`, inserted as given.
    site_name
        Text for `{site_name}`, inserted as given.
    escape
        Optional escaping function for the template's literal text. The
        inserted page title and site name are left unchanged.

    Returns
    -------
    :
        The title. Text in the arguments that looks like a key stays as written.
    """
    values = {PAGE_KEY: page_title, SITE_KEY: site_name}
    parts = _KEYS.split(template)
    return "".join(
        values[part] if part in values else (escape(part) if escape else part) for part in parts
    )
