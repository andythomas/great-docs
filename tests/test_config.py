from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from great_docs.config import DEFAULT_CONFIG, Config, create_default_config, load_config


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Return a temp directory usable as a project root."""
    return tmp_path


def _make_config(tmp_path: Path, yaml_text: str) -> Config:
    """Helper: write *yaml_text* to great-docs.yml and return a Config."""
    (tmp_path / "great-docs.yml").write_text(yaml_text, encoding="utf-8")
    return Config(tmp_path)


def test_site_html_math_method_defaults_to_katex(tmp_project: Path):
    assert Config(tmp_project).site["html-math-method"] == "katex"


def test_site_html_math_method_accepts_override(tmp_project: Path):
    cfg = _make_config(tmp_project, "site:\n  html-math-method: mathjax\n")
    assert cfg.site["html-math-method"] == "mathjax"


class TestConfigInit:
    def test_no_config_file_uses_defaults(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg._config == DEFAULT_CONFIG.copy()


class TestConfigIsolation:
    def test_mutation_does_not_leak_into_defaults(self, tmp_project: Path):
        from great_docs.config import DEFAULT_CONFIG
        cfg = Config(tmp_project)
        cfg._config["changelog"]["max_releases"] = 999
        assert DEFAULT_CONFIG["changelog"]["max_releases"] == 50

    def test_loads_user_config(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "parser: google\n")
        assert cfg.parser == "google"

    def test_yaml_error_prints_warning(self, tmp_project: Path, capsys):
        """Covers lines 167-168 (YAMLError handler)."""
        (tmp_project / "great-docs.yml").write_text(
            "invalid: [\nunmatched bracket", encoding="utf-8"
        )
        cfg = Config(tmp_project)
        captured = capsys.readouterr()
        assert "Warning: Error parsing great-docs.yml" in captured.out
        # Falls back to defaults
        assert cfg.parser == "numpy"

    def test_generic_read_error_prints_warning(self, tmp_project: Path, capsys):
        """Covers lines 169-170 (generic Exception handler)."""
        (tmp_project / "great-docs.yml").write_text("parser: google\n")
        with patch("builtins.open", side_effect=PermissionError("denied")):
            cfg = Config(tmp_project)
        captured = capsys.readouterr()
        assert "Warning: Could not read great-docs.yml" in captured.out
        assert cfg.parser == "numpy"


class TestMergeConfig:
    def test_deep_merge_nested_dicts(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "source:\n  branch: develop\n")
        # branch overridden, other defaults preserved
        assert cfg.source_branch == "develop"
        assert cfg.source_enabled is True

    def test_scalar_replaces_default(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "parser: sphinx\n")
        assert cfg.parser == "sphinx"

    def test_new_key_in_user_config(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "custom_key: custom_value\n")
        assert cfg["custom_key"] == "custom_value"


class TestGetRemoved:
    def test_get_method_is_gone(self, tmp_project: Path):
        assert not hasattr(Config, "get")

    def test_lint_parser_read(self, tmp_project: Path):
        # _lint reads the parser through subscript now
        assert Config(tmp_project)["parser"] == "numpy"


class TestGetItem:
    def test_top_level_hit(self, tmp_project: Path):
        assert Config(tmp_project)["github_style"] == "widget"

    def test_nested_hit(self, tmp_project: Path):
        assert Config(tmp_project)["source.placement"] == "usage"

    def test_missing_top_level_raises(self, tmp_project: Path):
        with pytest.raises(KeyError):
            Config(tmp_project)["does_not_exist"]

    def test_traversal_into_scalar_raises(self, tmp_project: Path):
        # github_style is a string; indexing into it must fail loud
        with pytest.raises(KeyError):
            Config(tmp_project)["github_style.nope"]

    def test_new_is_old_default_is_none(self, tmp_project: Path):
        # new_is_old is a live default now, resolved via strict subscript
        assert Config(tmp_project)["new_is_old"] is None


class TestScalarProperties:
    def test_exclude_default(self, tmp_project: Path):
        assert Config(tmp_project).exclude == []

    def test_exclude_custom(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "exclude:\n  - Foo\n  - Bar\n")
        assert cfg.exclude == ["Foo", "Bar"]

    def test_repo_default(self, tmp_project: Path):
        assert Config(tmp_project).repo is None

    def test_repo_custom(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "repo: https://github.com/owner/repo\n")
        assert cfg.repo == "https://github.com/owner/repo"

    def test_github_style_default(self, tmp_project: Path):
        assert Config(tmp_project).github_style == "widget"

    def test_github_style_icon(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "github_style: icon\n")
        assert cfg.github_style == "icon"

    def test_source_enabled_default(self, tmp_project: Path):
        assert Config(tmp_project).source_enabled is True

    def test_source_branch_default(self, tmp_project: Path):
        assert Config(tmp_project).source_branch is None

    def test_source_path_default(self, tmp_project: Path):
        assert Config(tmp_project).source_path is None

    def test_source_placement_default(self, tmp_project: Path):
        assert Config(tmp_project).source_placement == "usage"

    def test_sidebar_filter_enabled_default(self, tmp_project: Path):
        assert Config(tmp_project).sidebar_filter_enabled is True

    def test_sidebar_filter_min_items_default(self, tmp_project: Path):
        assert Config(tmp_project).sidebar_filter_min_items == 20

    def test_cli_enabled_default(self, tmp_project: Path):
        assert Config(tmp_project).cli_enabled is False

    def test_cli_module_default(self, tmp_project: Path):
        assert Config(tmp_project).cli_module is None

    def test_cli_name_default(self, tmp_project: Path):
        assert Config(tmp_project).cli_name is None

    def test_changelog_enabled_default(self, tmp_project: Path):
        assert Config(tmp_project).changelog_enabled is True

    def test_changelog_max_releases_default(self, tmp_project: Path):
        assert Config(tmp_project).changelog_max_releases == 50

    def test_sections_default(self, tmp_project: Path):
        assert Config(tmp_project).sections == []

    def test_custom_pages_default(self, tmp_project: Path):
        assert Config(tmp_project).custom_pages == [{"dir": "custom", "output": "custom"}]

    def test_custom_pages_false_disables_processing(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "custom_pages: false\n")
        assert cfg.custom_pages == []

    def test_custom_pages_string_uses_basename_for_output(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "custom_pages: marketing/pages\n")
        assert cfg.custom_pages == [{"dir": "marketing/pages", "output": "pages"}]

    def test_custom_pages_dict_supports_output_override(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "custom_pages:\n  dir: marketing\n  output: py\n",
        )
        assert cfg.custom_pages == [{"dir": "marketing", "output": "py"}]

    def test_custom_pages_list_normalizes_multiple_entries(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "custom_pages:\n  - marketing\n  - dir: playgrounds/raw\n    output: demos\n",
        )
        assert cfg.custom_pages == [
            {"dir": "marketing", "output": "marketing"},
            {"dir": "playgrounds/raw", "output": "demos"},
        ]

    def test_dark_mode_toggle_default(self, tmp_project: Path):
        assert Config(tmp_project).dark_mode_toggle is True

    def test_back_to_top_default(self, tmp_project: Path):
        assert Config(tmp_project).back_to_top is True

    def test_back_to_top_false(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "back_to_top: false\n")
        assert cfg.back_to_top is False

    def test_keyboard_nav_default(self, tmp_project: Path):
        assert Config(tmp_project).keyboard_nav is True

    def test_keyboard_nav_false(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "keyboard_nav: false\n")
        assert cfg.keyboard_nav is False

    def test_parser_default(self, tmp_project: Path):
        assert Config(tmp_project).parser == "numpy"

    def test_dynamic_default(self, tmp_project: Path):
        assert Config(tmp_project).dynamic is True

    def test_module_default(self, tmp_project: Path):
        assert Config(tmp_project).module is None

    def test_display_name_default(self, tmp_project: Path):
        assert Config(tmp_project).display_name is None

    def test_authors_default(self, tmp_project: Path):
        assert Config(tmp_project).authors == []

    def test_funding_default(self, tmp_project: Path):
        assert Config(tmp_project).funding is None

    def test_site_default(self, tmp_project: Path):
        # `site` is now a pure Quarto passthrough; great-docs-owned keys
        # (language, show_dates, ...) are top-level, not under `site`.
        assert Config(tmp_project).site == {
            "theme": "flatly",
            "toc": True,
            "toc-depth": 2,
            "html-math-method": "katex",
        }

    def test_jupyter_default(self, tmp_project: Path):
        assert Config(tmp_project).jupyter == "python3"

    def test_language_default(self, tmp_project: Path):
        assert Config(tmp_project).language == "en"

    def test_language_custom(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "site:\n  language: fr\n")
        assert cfg.language == "fr"

    def test_attribution_default(self, tmp_project: Path):
        assert Config(tmp_project).attribution is True

    def test_attribution_false(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "attribution: false\n")
        assert cfg.attribution is False


class TestHomepage:
    def test_default(self, tmp_project: Path):
        assert Config(tmp_project).homepage == "index"

    def test_user_guide(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "homepage: user_guide\n")
        assert cfg.homepage == "user_guide"

    def test_invalid_value_falls_back(self, tmp_project: Path, capsys):
        """Covers lines 365-366 (invalid homepage value)."""
        cfg = _make_config(tmp_project, "homepage: bogus\n")
        assert cfg.homepage == "index"
        captured = capsys.readouterr()
        assert "Warning: Invalid homepage value" in captured.out


class TestUserGuide:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project).user_guide is None

    def test_string(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "user_guide: docs/guides\n")
        assert cfg.user_guide == "docs/guides"
        assert cfg.user_guide_dir == "docs/guides"
        assert cfg.user_guide_is_explicit is False

    def test_list_explicit(self, tmp_project: Path):
        """Covers line 385 (user_guide_is_explicit True branch)."""
        cfg = _make_config(
            tmp_project,
            "user_guide:\n  - section: Get Started\n    contents:\n      - intro.qmd\n",
        )
        assert isinstance(cfg.user_guide, list)
        assert cfg.user_guide_is_explicit is True
        assert cfg.user_guide_dir is None


class TestReference:
    def test_default_empty_list(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.reference == []
        assert cfg.reference_enabled is True
        assert cfg.reference_title is None
        assert cfg.reference_desc is None

    def test_list_form(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "reference:\n  - title: Core\n    contents:\n      - MyClass\n",
        )
        assert len(cfg.reference) == 1
        assert cfg.reference[0]["title"] == "Core"

    def test_dict_form_with_sections(self, tmp_project: Path):
        """Covers lines 432-436 (dict form with embedded sections)."""
        cfg = _make_config(
            tmp_project,
            (
                "reference:\n"
                "  title: API Docs\n"
                "  desc: Full reference\n"
                "  sections:\n"
                "    - title: Core\n"
                "      contents:\n"
                "        - MyClass\n"
            ),
        )
        assert cfg.reference == [{"title": "Core", "contents": ["MyClass"]}]
        assert cfg.reference_title == "API Docs"  # line 447
        assert cfg.reference_desc == "Full reference"  # line 460

    def test_dict_form_without_sections_key(self, tmp_project: Path):
        """Dict form but no 'sections' key → empty list."""
        cfg = _make_config(
            tmp_project,
            "reference:\n  title: API Docs\n",
        )
        assert cfg.reference == []

    def test_reference_disabled(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "reference: false\n")
        assert cfg.reference_enabled is False
        assert cfg.reference == []


class TestMarkdownPages:
    def test_default_true(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.markdown_pages is True
        assert cfg.markdown_pages_widget is True

    def test_false(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "markdown_pages: false\n")
        assert cfg.markdown_pages is False
        assert cfg.markdown_pages_widget is False

    def test_dict_widget_false(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "markdown_pages:\n  widget: false\n")
        assert cfg.markdown_pages is True
        assert cfg.markdown_pages_widget is False

    def test_dict_enabled_false(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "markdown_pages:\n  enabled: false\n")
        assert cfg.markdown_pages is False
        assert cfg.markdown_pages_widget is False


class TestMarkdownPagesCanonical:
    def test_default(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg["markdown_pages"] == {"enabled": True, "widget": True}
        assert cfg.markdown_pages is True
        assert cfg.markdown_pages_widget is True

    def test_bool_false(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "markdown_pages: false\n")
        assert cfg.markdown_pages is False
        assert cfg.markdown_pages_widget is False

    def test_widget_only(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "markdown_pages:\n  widget: false\n")
        assert cfg.markdown_pages is True
        assert cfg.markdown_pages_widget is False


class TestLogo:
    def test_default_none(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.logo is None
        assert cfg.logo_show_title is False

    def test_string(self, tmp_project: Path):
        """Covers line 503 (logo string → dict expansion)."""
        cfg = _make_config(tmp_project, "logo: assets/logo.svg\n")
        assert cfg.logo == {
            "light": "assets/logo.svg",
            "dark": "assets/logo.svg",
            "show_title": False,
        }

    def test_dark_only(self, tmp_project: Path):
        """A dark-only variant still counts as a logo being set."""
        cfg = _make_config(tmp_project, "logo:\n  dark: d.svg\n")
        assert cfg.logo is not None
        assert cfg.logo["dark"] == "d.svg"

    def test_dict(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "logo:\n  light: light.svg\n  dark: dark.svg\n  show_title: true\n",
        )
        assert cfg.logo == {"light": "light.svg", "dark": "dark.svg", "show_title": True}
        assert cfg.logo_show_title is True

    def test_unsupported_type_returns_none(self, tmp_project: Path):
        """Covers line 506 (logo fallback None for non-str/dict)."""
        cfg = _make_config(tmp_project, "logo: 123\n")
        assert cfg.logo is None


class TestHero:
    def test_default_no_logo(self, tmp_project: Path):
        """hero=None and no logo → hero disabled."""
        cfg = Config(tmp_project)
        assert cfg.hero_enabled is False
        assert cfg.hero_explicitly_disabled is False
        assert cfg.hero == {
            "enabled": None,
            "logo": None,
            "logo_height": "200px",
            "name": None,
            "tagline": None,
            "badges": "auto",
            "starfield": False,
        }

    def test_auto_enable_with_logo(self, tmp_project: Path):
        """hero=None + logo configured → hero auto-enabled."""
        cfg = _make_config(tmp_project, "logo: logo.svg\n")
        assert cfg.hero_enabled is True

    def test_hero_false(self, tmp_project: Path):
        """Covers line 525 (hero=False)."""
        cfg = _make_config(tmp_project, "hero: false\n")
        assert cfg.hero_enabled is False
        assert cfg.hero_explicitly_disabled is True

    def test_hero_true(self, tmp_project: Path):
        """Covers line 528 (hero=True → enabled)."""
        cfg = _make_config(tmp_project, "hero: true\n")
        assert cfg.hero_enabled is True

    def test_hero_dict_enabled(self, tmp_project: Path):
        """A dict form only enables via `enabled: true`, not by setting other sub-fields."""
        cfg = _make_config(tmp_project, "hero:\n  enabled: true\n  name: My Package\n")
        assert cfg.hero_enabled is True

    def test_hero_dict_other_fields_do_not_auto_enable(self, tmp_project: Path):
        """Setting a sub-field without `enabled` or a logo keeps hero in auto (off)."""
        cfg = _make_config(tmp_project, "hero:\n  name: My Package\n")
        assert cfg.hero_enabled is False

    def test_hero_logo_only_auto_enables(self, tmp_project: Path):
        """An explicit `hero.logo`, with no top-level `logo`, still auto-enables.

        The hero and navbar logos share one fallback chain (core._build_hero_section:
        explicit hero.logo -> detected hero logo -> navbar logo -> detected navbar
        logo), so "auto" must consider both ends of it, not just the navbar logo.
        """
        cfg = _make_config(tmp_project, "hero:\n  logo: x.svg\n")
        assert cfg.hero_enabled is True

    def test_empty_hero_no_logo_stays_disabled(self, tmp_project: Path):
        """An empty hero dict/null with no logo anywhere keeps auto resolving to off.

        The old "any hero dict force-enables" quirk is intentionally dropped.
        """
        cfg = _make_config(tmp_project, "hero: {}\n")
        assert cfg.hero_enabled is False

        cfg_null = _make_config(tmp_project, "hero: null\n")
        assert cfg_null.hero_enabled is False

    def test_hero_dict_explicitly_disabled(self, tmp_project: Path):
        """Covers line 540 (hero dict with enabled: false)."""
        cfg = _make_config(tmp_project, "hero:\n  enabled: false\n")
        assert cfg.hero_enabled is False
        assert cfg.hero_explicitly_disabled is True


class TestHeroLogo:
    def test_default_none(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.hero_logo is None

    def test_explicit_logo(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "hero:\n  logo: hero.svg\n")
        assert cfg.hero_logo == "hero.svg"

    def test_suppressed(self, tmp_project: Path):
        """Covers line 567 (hero logo = false)."""
        cfg = _make_config(tmp_project, "hero:\n  logo: false\n")
        assert cfg.hero_logo is False

    def test_hero_logo_height_default(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.hero_logo_height == "200px"

    def test_hero_logo_height_custom(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "hero:\n  logo_height: 300px\n")
        assert cfg.hero_logo_height == "300px"


class TestHeroName:
    def test_default_fallback_to_display_name(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "display_name: My Pkg\n")
        assert cfg.hero_name == "My Pkg"

    def test_custom(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "hero:\n  name: Custom Name\n")
        assert cfg.hero_name == "Custom Name"

    def test_suppressed(self, tmp_project: Path):
        """Covers line 587 (hero name = false → False)."""
        cfg = _make_config(tmp_project, "hero:\n  name: false\n")
        assert cfg.hero_name is False


class TestHeroTagline:
    def test_default_none(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.hero_tagline is None

    def test_custom(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "hero:\n  tagline: A great package\n")
        assert cfg.hero_tagline == "A great package"

    def test_suppressed(self, tmp_project: Path):
        """Covers line 602 (hero tagline = false → None)."""
        cfg = _make_config(tmp_project, "hero:\n  tagline: false\n")
        assert cfg.hero_tagline is None


class TestHeroBadges:
    def test_default_auto(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.hero_badges == "auto"

    def test_explicit_list(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "hero:\n  badges:\n    - url: https://badge.svg\n",
        )
        assert cfg.hero_badges == [{"url": "https://badge.svg"}]

    def test_suppressed(self, tmp_project: Path):
        """Covers line 615 (hero badges = false → None)."""
        cfg = _make_config(tmp_project, "hero:\n  badges: false\n")
        assert cfg.hero_badges is None


class TestHeroCanonical:
    def test_default_auto(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg["hero.logo_height"] == "200px"
        assert cfg["hero.badges"] == "auto"
        assert cfg.hero_enabled is False  # no logo -> auto resolves off
        assert cfg.hero_logo_height == "200px"
        assert cfg.hero_badges == "auto"

    def test_false_disables(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "hero: false\n")
        assert cfg.hero_enabled is False
        assert cfg.hero_explicitly_disabled is True

    def test_true_enables(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "hero: true\n")
        assert cfg.hero_enabled is True

    def test_dict_overrides(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "hero:\n  logo_height: 300px\n")
        assert cfg.hero_logo_height == "300px"
        assert cfg.hero_badges == "auto"  # untouched sub-default survives


class TestFavicon:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project).favicon is None

    def test_string(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "favicon: favicon.ico\n")
        assert cfg.favicon == {"icon": "favicon.ico"}

    def test_dict(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "favicon:\n  icon: favicon.ico\n  apple_touch: apple.png\n",
        )
        assert cfg.favicon == {"icon": "favicon.ico", "apple_touch": "apple.png"}

    def test_unsupported_type_returns_none(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "favicon: 42\n")
        assert cfg.favicon is None


class TestAnnouncement:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project).announcement is None

    def test_false(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "announcement: false\n")
        assert cfg.announcement is None

    def test_string(self, tmp_project: Path):
        """Covers line 655 (announcement string → normalized dict)."""
        cfg = _make_config(tmp_project, "announcement: New release!\n")
        assert cfg.announcement == {
            "content": "New release!",
            "type": "info",
            "dismissable": True,
            "url": None,
            "style": None,
            "position": "above-navbar",
        }

    def test_dict_full(self, tmp_project: Path):
        """Covers line 659 (announcement dict)."""
        cfg = _make_config(
            tmp_project,
            (
                "announcement:\n"
                "  content: Big news\n"
                "  type: warning\n"
                "  dismissable: false\n"
                "  url: https://example.com\n"
                "  style: custom\n"
                "  position: below-navbar\n"
            ),
        )
        assert cfg.announcement == {
            "content": "Big news",
            "type": "warning",
            "dismissable": False,
            "url": "https://example.com",
            "style": "custom",
            "position": "below-navbar",
        }

    def test_position_defaults_above_navbar_for_string(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "announcement: Hi\n")
        assert cfg.announcement["position"] == "above-navbar"

    def test_position_defaults_above_navbar_for_dict(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "announcement:\n  content: Hi\n")
        assert cfg.announcement["position"] == "above-navbar"

    def test_position_below_navbar(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project, "announcement:\n  content: Hi\n  position: below-navbar\n"
        )
        assert cfg.announcement["position"] == "below-navbar"

    def test_position_invalid_falls_back_to_above(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project, "announcement:\n  content: Hi\n  position: sideways\n"
        )
        assert cfg.announcement["position"] == "above-navbar"

    def test_dict_empty_content_returns_none(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "announcement:\n  type: info\n")
        assert cfg.announcement is None

    def test_unsupported_type_returns_none(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "announcement: 123\n")
        assert cfg.announcement is None


class TestAnnouncementCanonical:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project)["announcement.type"] == "info"
        assert Config(tmp_project).announcement is None  # content null

    def test_string_shorthand(self, tmp_path: Path):
        cfg = _make_config(tmp_path, 'announcement: "Heads up"\n')
        a = cfg.announcement
        assert a["content"] == "Heads up"
        assert a["type"] == "info"
        assert a["dismissable"] is True

    def test_dict_partial(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "announcement:\n  content: Hi\n  type: warning\n")
        a = cfg.announcement
        assert a["type"] == "warning"
        assert a["dismissable"] is True


class TestIncludeInHeader:
    def test_default_empty(self, tmp_project: Path):
        assert Config(tmp_project).include_in_header == []

    def test_none_value(self, tmp_project: Path):
        """Covers line 678 (include_in_header: null → [])."""
        cfg = _make_config(tmp_project, "include_in_header: null\n")
        assert cfg.include_in_header == []

    def test_string(self, tmp_project: Path):
        """Covers line 680 (string → [{"text": ...}])."""
        cfg = _make_config(
            tmp_project,
            "include_in_header: '<script src=\"x.js\"></script>'\n",
        )
        assert cfg.include_in_header == [{"text": '<script src="x.js"></script>'}]

    def test_list_of_strings(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "include_in_header:\n  - '<script>1</script>'\n  - '<script>2</script>'\n",
        )
        assert cfg.include_in_header == [
            {"text": "<script>1</script>"},
            {"text": "<script>2</script>"},
        ]

    def test_list_of_dicts(self, tmp_project: Path):
        """Covers lines 686-687 (dict items in list)."""
        cfg = _make_config(
            tmp_project,
            "include_in_header:\n  - file: extra.html\n",
        )
        assert cfg.include_in_header == [{"file": "extra.html"}]

    def test_list_mixed(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "include_in_header:\n  - '<script>x</script>'\n  - file: extra.html\n",
        )
        assert cfg.include_in_header == [
            {"text": "<script>x</script>"},
            {"file": "extra.html"},
        ]

    def test_list_with_unsupported_item_type(self, tmp_project: Path):
        """Covers branch 686→683 (list item neither str nor dict is skipped)."""
        cfg = Config(tmp_project)
        cfg._config["include_in_header"] = ["<script>x</script>", 42, {"file": "a.html"}]
        assert cfg.include_in_header == [
            {"text": "<script>x</script>"},
            {"file": "a.html"},
        ]

    def test_unsupported_type_returns_empty(self, tmp_project: Path):
        """Covers line 689 (non-str/list/None → [])."""
        cfg = _make_config(tmp_project, "include_in_header: 42\n")
        assert cfg.include_in_header == []


class TestFreeze:
    def test_default_auto(self, tmp_project: Path):
        assert Config(tmp_project).freeze == "auto"

    def test_auto_string(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "freeze: auto\n")
        assert cfg.freeze == "auto"

    def test_true_bool(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "freeze: true\n")
        assert cfg.freeze is True

    def test_false_disabled(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "freeze: false\n")
        assert cfg.freeze is None

    def test_dict_form_mode(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "freeze:\n  mode: auto\n  pre_render: restore.py\n")
        assert cfg.freeze == "auto"

    def test_dict_form_mode_true(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "freeze:\n  mode: true\n")
        # YAML parses `mode: true` as boolean True
        assert cfg.freeze is True

    def test_string_true(self, tmp_project: Path):
        """String 'true' is normalized to boolean True."""
        cfg = _make_config(tmp_project, 'freeze: "true"\n')
        assert cfg.freeze is True


class TestFreezeCanonical:
    def test_default_auto(self, tmp_project: Path):
        assert Config(tmp_project)["freeze.mode"] == "auto"
        assert Config(tmp_project).freeze == "auto"

    def test_null_disables(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "freeze: null\n")
        assert cfg.freeze is None

    def test_true(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "freeze: true\n")
        assert cfg.freeze is True

    def test_pre_render_from_dict(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "freeze:\n  mode: auto\n  pre_render: cp.sh\n")
        assert cfg.pre_render == ["cp.sh"]


class TestPreRender:
    def test_default_empty(self, tmp_project: Path):
        assert Config(tmp_project).pre_render == []

    def test_single_string(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "pre_render: scripts/restore.py\n")
        assert cfg.pre_render == ["scripts/restore.py"]

    def test_list(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "pre_render:\n  - scripts/a.py\n  - scripts/b.py\n")
        assert cfg.pre_render == ["scripts/a.py", "scripts/b.py"]

    def test_from_freeze_dict(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "freeze:\n  mode: auto\n  pre_render: scripts/restore.py\n")
        assert cfg.pre_render == ["scripts/restore.py"]

    def test_freeze_dict_list(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "freeze:\n  mode: auto\n  pre_render:\n    - a.py\n    - b.py\n",
        )
        assert cfg.pre_render == ["a.py", "b.py"]

    def test_combined_no_duplicates(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "freeze:\n  mode: auto\n  pre_render: scripts/restore.py\npre_render: scripts/restore.py\n",
        )
        assert cfg.pre_render == ["scripts/restore.py"]

    def test_combined_different_scripts(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "freeze:\n  mode: auto\n  pre_render: a.py\npre_render: b.py\n",
        )
        assert cfg.pre_render == ["a.py", "b.py"]


class TestNormalizeFreezeShorthand:
    """Test the page-level `freeze:` → `execute: freeze:` transformation."""

    def _make_docs(self, tmp_path: Path):
        """Create a minimal GreatDocs instance with a build directory."""
        from great_docs.core import GreatDocs

        (tmp_path / "great-docs.yml").write_text("freeze: auto\n")
        # Minimal pyproject.toml so GreatDocs doesn't error
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "testpkg"\nversion = "0.1"\n')
        docs = GreatDocs(project_path=str(tmp_path))
        # Create build dir manually for testing
        docs.project_path.mkdir(parents=True, exist_ok=True)
        return docs

    def test_shorthand_auto(self, tmp_project: Path):
        docs = self._make_docs(tmp_project)
        qmd = docs.project_path / "page.qmd"
        qmd.write_text("---\ntitle: Test\nfreeze: auto\n---\n\n# Hello\n")

        count = docs._normalize_freeze_shorthand()

        assert len(count) == 1
        result = qmd.read_text()
        assert "freeze: auto" not in result.split("---")[1].split("\n")[0:5] or "execute:" in result
        # Verify proper nesting
        assert "execute:\n  freeze: auto" in result

    def test_shorthand_true(self, tmp_project: Path):
        docs = self._make_docs(tmp_project)
        qmd = docs.project_path / "page.qmd"
        qmd.write_text("---\ntitle: Test\nfreeze: true\n---\n\n# Hello\n")

        count = docs._normalize_freeze_shorthand()

        assert len(count) == 1
        result = qmd.read_text()
        assert "execute:\n  freeze: true" in result

    def test_already_nested_unchanged(self, tmp_project: Path):
        docs = self._make_docs(tmp_project)
        qmd = docs.project_path / "page.qmd"
        original = "---\ntitle: Test\nexecute:\n  freeze: auto\n---\n\n# Hello\n"
        qmd.write_text(original)

        count = docs._normalize_freeze_shorthand()

        assert len(count) == 0
        assert qmd.read_text() == original

    def test_no_frontmatter_skipped(self, tmp_project: Path):
        docs = self._make_docs(tmp_project)
        qmd = docs.project_path / "page.qmd"
        qmd.write_text("# No frontmatter\n")

        count = docs._normalize_freeze_shorthand()
        assert len(count) == 0

    def test_no_freeze_key_skipped(self, tmp_project: Path):
        docs = self._make_docs(tmp_project)
        qmd = docs.project_path / "page.qmd"
        original = "---\ntitle: Normal Page\n---\n\n# Hello\n"
        qmd.write_text(original)

        count = docs._normalize_freeze_shorthand()

        assert len(count) == 0
        assert qmd.read_text() == original

    def test_existing_execute_block_gets_freeze_added(self, tmp_project: Path):
        docs = self._make_docs(tmp_project)
        qmd = docs.project_path / "page.qmd"
        qmd.write_text("---\ntitle: Test\nexecute:\n  echo: false\nfreeze: auto\n---\n\n# Hi\n")

        count = docs._normalize_freeze_shorthand()

        assert len(count) == 1
        result = qmd.read_text()
        # freeze: auto is inserted under execute: block
        assert "execute:" in result
        assert "  freeze: auto" in result
        assert "  echo: false" in result
        # The standalone freeze: line should be gone
        lines = result.split("---")[1].strip().split("\n")
        top_level_freeze = [l for l in lines if l == "freeze: auto"]
        assert top_level_freeze == []

    def test_multiple_files(self, tmp_project: Path):
        docs = self._make_docs(tmp_project)
        subdir = docs.project_path / "user-guide"
        subdir.mkdir()
        (docs.project_path / "a.qmd").write_text("---\nfreeze: auto\n---\n\n# A\n")
        (subdir / "b.qmd").write_text("---\nfreeze: true\n---\n\n# B\n")
        (docs.project_path / "c.qmd").write_text("---\ntitle: No freeze\n---\n\n# C\n")

        count = docs._normalize_freeze_shorthand()

        assert len(count) == 2


class TestNavbarStyle:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project).navbar_style is None

    def test_custom(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "navbar_style: sky\n")
        assert cfg.navbar_style == "sky"


class TestNavbarColor:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project).navbar_color is None

    def test_string(self, tmp_project: Path):
        """Covers line 720 (string → light+dark dict)."""
        cfg = _make_config(tmp_project, "navbar_color: '#336699'\n")
        assert cfg.navbar_color == {"light": "#336699", "dark": "#336699"}

    def test_dict(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "navbar_color:\n  light: '#fff'\n  dark: '#333'\n",
        )
        assert cfg.navbar_color == {"light": "#fff", "dark": "#333"}

    def test_dict_empty_returns_none(self, tmp_project: Path):
        """Covers line 728 (empty dict → None)."""
        cfg = _make_config(tmp_project, "navbar_color:\n  invalid_key: foo\n")
        assert cfg.navbar_color is None

    def test_overridden_by_navbar_style(self, tmp_project: Path):
        """navbar_style takes precedence → navbar_color returns None."""
        cfg = _make_config(
            tmp_project,
            "navbar_style: sky\nnavbar_color: '#336699'\n",
        )
        assert cfg.navbar_color is None

    def test_false_returns_none(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "navbar_color: false\n")
        assert cfg.navbar_color is None

    def test_unsupported_type_returns_none(self, tmp_project: Path):
        """Covers line 728 (non-str/dict → None)."""
        cfg = Config(tmp_project)
        cfg._config["navbar_color"] = 42
        assert cfg.navbar_color is None


class TestContentStyle:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project).content_style is None

    def test_string(self, tmp_project: Path):
        """Covers line 741 (string → preset+pages dict)."""
        cfg = _make_config(tmp_project, "content_style: peach\n")
        assert cfg.content_style == {"preset": "peach", "pages": "all"}

    def test_dict_with_homepage(self, tmp_project: Path):
        cfg = _make_config(
            tmp_project,
            "content_style:\n  preset: lilac\n  pages: homepage\n",
        )
        assert cfg.content_style == {"preset": "lilac", "pages": "homepage"}

    def test_dict_invalid_pages_falls_back(self, tmp_project: Path):
        """Covers line 744 (invalid pages value → 'all')."""
        cfg = _make_config(
            tmp_project,
            "content_style:\n  preset: sky\n  pages: invalid\n",
        )
        assert cfg.content_style == {"preset": "sky", "pages": "all"}

    def test_dict_missing_preset_returns_none(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "content_style:\n  pages: all\n")
        assert cfg.content_style is None

    def test_false_returns_none(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "content_style: false\n")
        assert cfg.content_style is None

    def test_unsupported_type_returns_none(self, tmp_project: Path):
        """Covers line 746 (non-str/dict → None)."""
        cfg = _make_config(tmp_project, "content_style: 42\n")
        assert cfg.content_style is None


class TestContentStyleCanonical:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project)["content_style.pages"] == "all"
        assert Config(tmp_project).content_style is None

    def test_string_shorthand(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "content_style: sky\n")
        assert cfg.content_style == {"preset": "sky", "pages": "all"}

    def test_dict(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "content_style:\n  preset: peach\n  pages: homepage\n")
        assert cfg.content_style == {"preset": "peach", "pages": "homepage"}


class TestLogoCanonical:
    def test_default_none(self, tmp_project: Path):
        assert Config(tmp_project)["logo.show_title"] is False
        assert Config(tmp_project).logo is None

    def test_string_shorthand(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "logo: assets/logo.svg\n")
        assert cfg.logo == {"light": "assets/logo.svg", "dark": "assets/logo.svg", "show_title": False}

    def test_dict_show_title(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "logo:\n  light: a.svg\n  show_title: true\n")
        assert cfg.logo_show_title is True


class TestExistsAndToDict:
    def test_exists_true(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "parser: google\n")
        assert cfg.exists() is True

    def test_exists_false(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.exists() is False

    def test_to_dict_returns_copy(self, tmp_project: Path):
        cfg = Config(tmp_project)
        d = cfg.to_dict()
        assert d == cfg._config
        assert d is not cfg._config  # must be a copy


class TestModuleFunctions:
    def test_load_config_str_path(self, tmp_project: Path):
        (tmp_project / "great-docs.yml").write_text("parser: sphinx\n")
        cfg = load_config(str(tmp_project))
        assert isinstance(cfg, Config)
        assert cfg.parser == "sphinx"

    def test_load_config_path_object(self, tmp_project: Path):
        cfg = load_config(tmp_project)
        assert isinstance(cfg, Config)

    def test_create_default_config_is_string(self):
        result = create_default_config()
        assert isinstance(result, str)
        assert "Great Docs Configuration" in result
        assert "parser:" in result


# ── custom_pages edge cases ────────────────────────────────────────────


def test_custom_pages_dict_no_output(tmp_path):
    """Dict entry with missing output falls back to dir name."""
    (tmp_path / "great-docs.yml").write_text("custom_pages:\n  - dir: my_pages\n")
    cfg = Config(tmp_path)
    result = cfg.custom_pages
    assert result == [{"dir": "my_pages", "output": "my_pages"}]


def test_custom_pages_dict_empty_output(tmp_path):
    """Dict entry with empty-string output falls back to dir name."""
    (tmp_path / "great-docs.yml").write_text('custom_pages:\n  - dir: my_pages\n    output: ""\n')
    cfg = Config(tmp_path)
    result = cfg.custom_pages
    assert result[0]["output"] == "my_pages"


# ── dark_mode_toggle ───────────────────────────────────────────────────


def test_dark_mode_toggle_false(tmp_path):
    """dark_mode_toggle returns False when explicitly disabled."""
    (tmp_path / "great-docs.yml").write_text("dark_mode_toggle: false\n")
    cfg = Config(tmp_path)
    assert cfg.dark_mode_toggle is False


# ── team_author ────────────────────────────────────────────────────────


def test_team_author_with_name(tmp_path):
    """team_author returns dict when configured with a name."""
    (tmp_path / "great-docs.yml").write_text(
        "team_author:\n  name: Team\n  image: avatar.png\n  url: https://team.dev\n"
    )
    cfg = Config(tmp_path)
    result = cfg.team_author
    assert result == {"name": "Team", "image": "avatar.png", "url": "https://team.dev"}


def test_team_author_missing_name(tmp_path):
    """team_author returns None when name is not set."""
    (tmp_path / "great-docs.yml").write_text("team_author:\n  image: avatar.png\n")
    cfg = Config(tmp_path)
    assert cfg.team_author is None


def test_team_author_none(tmp_path):
    """team_author returns None when not configured."""
    cfg = Config(tmp_path)
    assert cfg.team_author is None


# ── jupyter ────────────────────────────────────────────────────────────


def test_jupyter_custom_kernel(tmp_path):
    """jupyter returns custom kernel name when configured."""
    (tmp_path / "great-docs.yml").write_text("jupyter: ir\n")
    cfg = Config(tmp_path)
    assert cfg.jupyter == "ir"


# ── social_cards properties ────────────────────────────────────────────


def test_social_cards_image(tmp_path):
    """social_cards_image returns image path from dict config."""
    (tmp_path / "great-docs.yml").write_text("social_cards:\n  image: card.png\n")
    cfg = Config(tmp_path)
    assert cfg.social_cards_image == "card.png"


def test_social_cards_image_none(tmp_path):
    """social_cards_image returns None when not dict."""
    (tmp_path / "great-docs.yml").write_text("social_cards: true\n")
    cfg = Config(tmp_path)
    assert cfg.social_cards_image is None


def test_social_cards_twitter_card(tmp_path):
    """social_cards_twitter_card returns card type."""
    (tmp_path / "great-docs.yml").write_text("social_cards:\n  twitter_card: summary_large_image\n")
    cfg = Config(tmp_path)
    assert cfg.social_cards_twitter_card == "summary_large_image"


def test_social_cards_twitter_site(tmp_path):
    """social_cards_twitter_site returns handle."""
    (tmp_path / "great-docs.yml").write_text("social_cards:\n  twitter_site: '@myhandle'\n")
    cfg = Config(tmp_path)
    assert cfg.social_cards_twitter_site == "@myhandle"


# ── tags_index_page ───────────────────────────────────────────────────


def test_tags_index_page_true(tmp_path):
    """tags_index_page returns True when tags are enabled."""
    (tmp_path / "great-docs.yml").write_text("tags: true\n")
    cfg = Config(tmp_path)
    assert cfg.tags_index_page is True


def test_tags_index_page_false_when_disabled(tmp_path):
    """tags_index_page returns False when tags disabled."""
    cfg = Config(tmp_path)
    assert cfg.tags_index_page is False


# ── inline_methods / should_split_methods ─────────────────────────────


class TestShouldSplitMethods:
    def test_default_splits_above_5(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg.should_split_methods(5) is False
        assert cfg.should_split_methods(6) is True

    def test_true_never_splits(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: true\n")
        assert cfg.should_split_methods(0) is False
        assert cfg.should_split_methods(100) is False

    def test_false_always_splits(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: false\n")
        assert cfg.should_split_methods(1) is True
        assert cfg.should_split_methods(100) is True

    def test_false_does_not_split_zero_methods(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: false\n")
        assert cfg.should_split_methods(0) is False

    def test_custom_threshold(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: 10\n")
        assert cfg.should_split_methods(10) is False
        assert cfg.should_split_methods(11) is True

    def test_invalid_value_falls_back_to_default(self, tmp_project: Path):
        cfg = _make_config(tmp_project, 'inline_methods: "abc"\n')
        assert cfg.should_split_methods(5) is False
        assert cfg.should_split_methods(6) is True

    def test_null_falls_back_to_default(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: null\n")
        assert cfg.should_split_methods(5) is False
        assert cfg.should_split_methods(6) is True

    def test_zero_threshold_splits_any_methods(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: 0\n")
        assert cfg.should_split_methods(0) is False
        assert cfg.should_split_methods(1) is True

    def test_one_threshold(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: 1\n")
        assert cfg.should_split_methods(1) is False
        assert cfg.should_split_methods(2) is True

    def test_float_value_truncated_to_int(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: 3.9\n")
        # float 3.9 → int(3.9) = 3
        assert cfg.should_split_methods(3) is False
        assert cfg.should_split_methods(4) is True

    def test_negative_threshold_always_splits(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: -1\n")
        # Any method_count > -1 is always true
        assert cfg.should_split_methods(0) is False  # zero-methods guard
        assert cfg.should_split_methods(1) is True

    def test_large_threshold_never_splits_in_practice(self, tmp_project: Path):
        cfg = _make_config(tmp_project, "inline_methods: 1000\n")
        assert cfg.should_split_methods(999) is False
        assert cfg.should_split_methods(1000) is False
        assert cfg.should_split_methods(1001) is True

    def test_config_default_value_in_defaults(self, tmp_project: Path):
        """The inline_methods default should be 5 in DEFAULT_CONFIG."""
        from great_docs.config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["inline_methods"] == 5


def test_legacy_site_keys_lift_to_top_level(tmp_path: Path):
    cfg = _make_config(tmp_path, "site:\n  show_dates: true\n  language: fr\n")
    assert cfg.show_dates is True
    assert cfg.language == "fr"
    assert "show_dates" not in cfg.site
    assert "language" not in cfg.site


def test_explicit_top_level_wins_over_legacy_site(tmp_path: Path):
    cfg = _make_config(tmp_path, "site:\n  show_dates: false\nshow_dates: true\n")
    assert cfg.show_dates is True


def test_site_quarto_excludes_css_and_legacy_keys(tmp_path: Path):
    cfg = _make_config(
        tmp_path,
        "site:\n  grid: {sidebar-width: 250px}\n  css: custom.css\n  show_dates: true\n",
    )
    sq = cfg.site_quarto
    assert sq["grid"] == {"sidebar-width": "250px"}
    assert "css" not in sq
    assert "show_dates" not in sq


def _quarto_config_for(tmp_path: Path, gd_yaml: str) -> dict:
    """Build _quarto.yml via GreatDocs._update_quarto_config and return it parsed."""
    from yaml12 import read_yaml

    from great_docs import GreatDocs

    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (tmp_path / "great-docs.yml").write_text(gd_yaml, encoding="utf-8")
    docs = GreatDocs(project_path=str(tmp_path))
    docs.project_path.mkdir(parents=True, exist_ok=True)
    docs._update_quarto_config()
    with open(docs.project_path / "_quarto.yml") as f:
        return read_yaml(f)


def test_arbitrary_site_key_reaches_format_html(tmp_path: Path):
    cfg = _quarto_config_for(tmp_path, "site:\n  grid:\n    sidebar-width: 250px\n")
    html = cfg["format"]["html"]
    assert html["grid"] == {"sidebar-width": "250px"}
    theme = html["theme"]
    assert (theme[0] if isinstance(theme, list) else theme) == "flatly"


def test_legacy_site_key_does_not_leak_into_format_html(tmp_path: Path):
    cfg = _quarto_config_for(tmp_path, "site:\n  show_dates: true\n")
    assert "show_dates" not in cfg["format"]["html"]


class TestYamlCompleteness:
    def test_new_keys_present(self, tmp_project: Path):
        cfg = Config(tmp_project)
        assert cfg["bibliography"] == []
        assert cfg["csl"] is None
        assert cfg["cli.title"] is None
        assert cfg["cli.desc"] is None
        assert cfg["cli.sections"] == []
        assert cfg["tags.location"] == "top"


class TestTypedEmptyDefaults:
    def test_pre_render_default_is_empty_list(self, tmp_project: Path):
        assert Config(tmp_project)["pre_render"] == []
        assert Config(tmp_project).pre_render == []

    def test_nav_icons_default_is_empty_dict(self, tmp_project: Path):
        assert Config(tmp_project)["nav_icons"] == {}
        # Property still resolves empty -> None for consumers
        assert Config(tmp_project).nav_icons is None


class TestShorthandNormalization:
    def test_page_status_true(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "page_status: true\n")
        assert cfg["page_status.enabled"] is True
        assert cfg.page_status_show_in_sidebar is True  # sub-defaults survive

    def test_tags_false(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "tags: false\n")
        assert cfg["tags.enabled"] is False
        assert cfg["tags.hierarchical"] is True

    def test_social_cards_false(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "social_cards: false\n")
        assert cfg["social_cards.enabled"] is False
        assert cfg.social_cards_enabled is False


class TestSeoShorthandNormalization:
    def test_sitemap_true_expands(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "seo:\n  sitemap: true\n")
        assert cfg["seo.sitemap.enabled"] is True
        assert cfg.sitemap_enabled is True
        assert cfg.sitemap_changefreq["homepage"] == "weekly"   # full default dict, no KeyError
        assert cfg.sitemap_priority["homepage"] == 1.0

    def test_sitemap_false_expands(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "seo:\n  sitemap: false\n")
        assert cfg["seo.sitemap.enabled"] is False
        assert cfg.sitemap_enabled is False

    def test_robots_true_expands(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "seo:\n  robots: true\n")
        assert cfg["seo.robots.enabled"] is True
        assert cfg.robots_disallow == []          # sub-defaults survive

    def test_top_level_seo_false_expands(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "seo: false\n")
        assert cfg.seo_enabled is False

    def test_top_level_seo_true_expands(self, tmp_path: Path):
        cfg = _make_config(tmp_path, "seo: true\n")
        assert cfg.seo_enabled is True
        assert cfg.sitemap_enabled is True        # sub-defaults survive


class TestSingleSourceInvariant:
    """Guards the single-source-of-truth contract in `great_docs/config.py`.

    With no user `great-docs.yml`, `DEFAULT_CONFIG` is the entire merged
    config. Every direct passthrough property must return exactly that value,
    and every property (direct or derived) must resolve without `KeyError` —
    a `KeyError` here means a property reads a key `great-docs.default.yml`
    doesn't declare, i.e. a Python-side default snuck back in.
    """

    def test_every_scalar_property_matches_yaml_default(self, tmp_project: Path):
        cfg = Config(tmp_project)
        # Properties that are a direct top-level passthrough must equal the YAML value.
        direct = [
            "parser", "dynamic", "jupyter", "language", "date_format",
            "github_style", "homepage", "attribution",
            "package_info_page", "back_to_top", "keyboard_nav", "dark_mode_toggle",
            "show_dates", "show_author", "show_security",
        ]
        for name in direct:
            assert getattr(cfg, name) == DEFAULT_CONFIG[name], name

    def test_no_property_reads_an_undeclared_key(self, tmp_project: Path):
        """Every property resolves without KeyError against the packaged defaults."""
        cfg = Config(tmp_project)
        for name in dir(Config):
            attr = getattr(Config, name, None)
            if isinstance(attr, property):
                getattr(cfg, name)  # must not raise KeyError
