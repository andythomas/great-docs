"""Tests for the shipped `default-config.yml` single source of truth."""

import io
import re
import tokenize
from importlib import resources
from pathlib import Path
from typing import Any

from great_docs.config import DEFAULT_CONFIG, create_default_config

_FIXTURES = Path(__file__).parent / "data"

# Verbatim snapshot of DEFAULT_CONFIG captured at the start of the config
# single-source migration. Guards faithful transcription of VALUES into
# default-config.yml. Do NOT import DEFAULT_CONFIG for this constant -- that
# would defeat the check.
FROZEN_DEFAULT_CONFIG: dict[str, Any] = {'module': None,
 'display_name': None,
 'project_type': 'python',
 'parser': 'numpy',
 'dynamic': True,
 'jupyter': 'python3',
 'exclude': [],
 'auto_include': [],
 'no_auto_exclude': False,
 'pypi': True,
 'repo': None,
 'site_url': None,
 'github_style': 'widget',
 'source': {'enabled': True, 'branch': None, 'path': None, 'placement': 'usage'},
 'sidebar_filter': {'enabled': True, 'min_items': 20},
 'cli': {'enabled': False, 'module': None, 'name': None},
 'go_cli': {'enabled': False},
 'mcp': {'enabled': True,
         'module': None,
         'server_var': None,
         'name': None,
         'categories': {}},
 'dark_mode_toggle': True,
 'authors': [],
 'funding': None,
 'site': {'theme': 'flatly',
          'toc': True,
          'toc-depth': 2,
          'html-math-method': 'katex',
          'language': 'en',
          'show_dates': False,
          'date_format': '%B %d, %Y',
          'show_author': True,
          'show_security': True},
 'team_author': None,
 'changelog': {'enabled': True, 'max_releases': 50},
 'sections': [],
 'custom_pages': None,
 'homepage': 'index',
 'user_guide': None,
 'reference': [],
 'inline_methods': 5,
 'logo': None,
 'favicon': None,
 'hero': None,
 'markdown_pages': True,
 'announcement': None,
 'versions': [],
 'version_selector': {'enabled': True,
                      'placement': 'navbar-right',
                      'show_eol': True,
                      'warning_banner': True},
 'version_aliases': {'latest': True, 'stable': True, 'dev': True},
 'accent_color': None,
 'navbar_style': None,
 'navbar_color': None,
 'content_style': None,
 'scale_to_fit': None,
 'scale_to_fit_min_scale': None,
 'nav_icons': None,
 'keyboard_nav': True,
 'package_info_page': True,
 'back_to_top': True,
 'attribution': True,
 'include_in_header': [],
 'freeze': 'auto',
 'pre_render': None,
 'skill': {'enabled': True,
           'file': None,
           'well_known': True,
           'gotchas': [],
           'best_practices': [],
           'decision_table': [],
           'extra_body': None,
           'skills': []},
 'social_cards': {'enabled': True,
                  'image': None,
                  'twitter_card': None,
                  'twitter_site': None},
 'page_status': {'enabled': False,
                 'show_in_sidebar': True,
                 'show_on_pages': True,
                 'statuses': {'new': {'label': 'New',
                                      'icon': 'sparkles',
                                      'color': '#10b981',
                                      'description': 'Recently added'},
                              'updated': {'label': 'Updated',
                                          'icon': 'refresh-cw',
                                          'color': '#3b82f6',
                                          'description': 'Recently updated'},
                              'beta': {'label': 'Beta',
                                       'icon': 'flask-conical',
                                       'color': '#f59e0b',
                                       'description': 'Beta feature'},
                              'deprecated': {'label': 'Deprecated',
                                             'icon': 'triangle-alert',
                                             'color': '#ef4444',
                                             'description': 'May be removed in a '
                                                            'future release'},
                              'experimental': {'label': 'Experimental',
                                               'icon': 'beaker',
                                               'color': '#8b5cf6',
                                               'description': 'API may change without '
                                                              'notice'},
                              'upcoming': {'label': 'Upcoming',
                                           'icon': 'rocket',
                                           'color': '#e63946',
                                           'description': 'Coming in a future '
                                                          'release'}}},
 'tags': {'enabled': False,
          'index_page': True,
          'show_on_pages': True,
          'hierarchical': True,
          'icons': {},
          'shadow': [],
          'scoped': False},
 'seo': {'enabled': True,
         'sitemap': {'enabled': True,
                     'changefreq': {'homepage': 'weekly',
                                    'reference': 'monthly',
                                    'user_guide': 'monthly',
                                    'changelog': 'weekly',
                                    'default': 'monthly'},
                     'priority': {'homepage': 1.0,
                                  'reference': 0.8,
                                  'user_guide': 0.9,
                                  'changelog': 0.6,
                                  'default': 0.5}},
         'robots': {'enabled': True,
                    'allow_all': True,
                    'disallow': [],
                    'crawl_delay': None,
                    'extra_rules': []},
         'canonical': {'enabled': True, 'base_url': None},
         'title_template': '{page_title} | {site_name}',
         'structured_data': {'enabled': True, 'type': 'SoftwareSourceCode'},
         'default_description': None}}


def _py_comment_bodies(src: str) -> set[str]:
    """Collect comment text from Python source, ignoring `#` inside strings."""
    bodies: set[str] = set()
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            body = tok.string.lstrip("#").strip()
            if body:
                bodies.add(body)
    return bodies


def _yaml_comment_bodies(text: str) -> set[str]:
    """Collect comment text from own-line YAML comments."""
    bodies: set[str] = set()
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            body = stripped.lstrip("#").strip()
            if body:
                bodies.add(body)
    return bodies


def _is_prose(body: str) -> bool:
    """Whether a comment body is documentation prose

    Excludes example config lines (`key:` / `key: value`), list items, and
    pure section dividers -- Option-3 promotes commented example keys to live
    values, so only genuine prose must survive verbatim.
    """
    if re.fullmatch(r"[-=]+", body):
        return False
    if body == "-" or body.startswith("- "):
        return False
    if re.match(r"^[A-Za-z0-9_.\-]+:(\s|$)", body):
        return False
    return True


def _default_config_text() -> str:
    return (
        resources.files("great_docs")
        .joinpath("default-config.yml")
        .read_text(encoding="utf-8")
    )


def test_config_defaults_yaml_matches_frozen_defaults():
    assert DEFAULT_CONFIG == FROZEN_DEFAULT_CONFIG


def test_config_defaults_yaml_is_packaged():
    resource = resources.files("great_docs").joinpath("default-config.yml")
    assert resource.is_file()
    assert resource.read_text(encoding="utf-8").strip()


def test_every_top_level_key_has_a_comment():
    lines = _default_config_text().splitlines()
    for i, line in enumerate(lines):
        # Top-level key: no indentation, not a comment, not blank.
        if line and line[0] not in " #" and ":" in line:
            prev = lines[i - 1].strip() if i > 0 else ""
            assert prev.startswith("#"), f"undocumented top-level key: {line!r}"


def test_every_legacy_comment_survives():
    legacy = _py_comment_bodies(
        (_FIXTURES / "legacy_literal.py").read_text(encoding="utf-8")
    ) | _yaml_comment_bodies(
        (_FIXTURES / "legacy_template.txt").read_text(encoding="utf-8")
    )
    legacy_prose = {b for b in legacy if _is_prose(b)}
    new = _yaml_comment_bodies(_default_config_text())
    missing = legacy_prose - new
    assert not missing, f"legacy comment lines dropped: {sorted(missing)}"


def test_create_default_config_is_fully_commented():
    output = create_default_config()
    for line in output.splitlines():
        # No live mapping key at column 0 -- every real key must be commented.
        assert not re.match(r"^[A-Za-z0-9_-]+:", line), f"uncommented key: {line!r}"


def test_create_default_config_lists_every_top_level_key():
    output = create_default_config()
    for key in DEFAULT_CONFIG:
        assert f"# {key}:" in output, f"missing key in template: {key}"


def test_emitted_template_comments_out_exactly_the_source():
    # The template is default-config.yml with every live value line commented
    # out and prose/blank lines untouched. Verifying this line-by-line (rather
    # than trying to invert the transform, which is lossy for prose) confirms
    # nothing is dropped or altered: the live content the template would
    # restore is exactly default-config.yml, which parses to DEFAULT_CONFIG.
    from yaml12 import read_yaml

    source = _default_config_text()
    assert read_yaml(io.StringIO(source)) == DEFAULT_CONFIG

    src_lines = source.splitlines()
    emt_lines = create_default_config().splitlines()
    assert len(src_lines) == len(emt_lines)
    for src, emt in zip(src_lines, emt_lines):
        if not src.strip() or src.lstrip().startswith("#"):
            assert emt == src
        else:
            assert emt == f"# {src}"
