"""Tests targeting great_docs/config.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from great_docs.config import Config


def _make_config(tmp_path: Path, yaml_text: str) -> Config:
    """Write yaml_text to great-docs.yml and return a Config."""
    (tmp_path / "great-docs.yml").write_text(yaml_text, encoding="utf-8")
    return Config(tmp_path)


# ---------------------------------------------------------------------------
# _lift_legacy_site_keys when site is not a dict
# ---------------------------------------------------------------------------


class TestLiftLegacySiteKeys:
    def test_site_not_dict_returns_config_unchanged(self, tmp_path):
        """When site is a scalar (not dict), legacy key lifting is skipped."""
        cfg = _make_config(tmp_path, "site: plain_string\n")
        # Should not raise; config is returned as-is with site as string
        assert cfg._config.get("site") == "plain_string"

    def test_site_is_list_returns_config_unchanged(self, tmp_path):
        """When site is a list, legacy key lifting is skipped."""
        cfg = _make_config(tmp_path, "site:\n  - item1\n  - item2\n")
        assert cfg._config.get("site") == ["item1", "item2"]


# ---------------------------------------------------------------------------
# cli_sections returns [] when value is not a list
# ---------------------------------------------------------------------------


class TestCliSections:
    def test_cli_sections_not_list_returns_empty(self, tmp_path):
        """When cli.sections is a non-list value, returns empty list."""
        cfg = _make_config(tmp_path, "cli:\n  sections: false\n")
        assert cfg.cli_sections == []

    def test_cli_sections_string_returns_empty(self, tmp_path):
        """When cli.sections is a string, returns empty list."""
        cfg = _make_config(tmp_path, "cli:\n  sections: auto\n")
        assert cfg.cli_sections == []


# ---------------------------------------------------------------------------
# marimo_version returns explicit string version from config
# ---------------------------------------------------------------------------


class TestMarimoVersion:
    def test_explicit_version_from_config(self, tmp_path):
        """When marimo.version is set, returns that string."""
        cfg = _make_config(tmp_path, "marimo:\n  version: 0.9.1\n")
        assert cfg.marimo_version == "0.9.1"


# ---------------------------------------------------------------------------
# custom_pages skips dict entry with invalid dir
# ---------------------------------------------------------------------------


class TestCustomPages:
    def test_dict_entry_with_empty_dir_skipped(self, tmp_path):
        """Dict entry whose dir is empty string is skipped."""
        cfg = _make_config(tmp_path, 'custom_pages:\n  - dir: ""\n    output: out\n')
        assert cfg.custom_pages == []

    def test_dict_entry_with_non_string_dir_skipped(self, tmp_path):
        """Dict entry with numeric dir is skipped."""
        cfg = _make_config(tmp_path, "custom_pages:\n  - dir: 42\n    output: out\n")
        assert cfg.custom_pages == []

    def test_dict_entry_missing_dir_skipped(self, tmp_path):
        """Dict entry without a dir key is skipped."""
        cfg = _make_config(tmp_path, "custom_pages:\n  - output: out\n")
        assert cfg.custom_pages == []


# ---------------------------------------------------------------------------
# version_selector_enabled when versions exist
# ---------------------------------------------------------------------------


class TestVersionSelectorEnabled:
    def test_enabled_when_versions_configured(self, tmp_path):
        """Returns the config value when versions are defined."""
        cfg = _make_config(
            tmp_path,
            "versions:\n  - tag: v1.0\n    label: '1.0'\nversion_selector:\n  enabled: true\n",
        )
        assert cfg.version_selector_enabled is True


# ---------------------------------------------------------------------------
# freeze_mode returns None for unknown string
# ---------------------------------------------------------------------------


class TestFreezeMode:
    def test_unknown_string_returns_none(self, tmp_path):
        """An unrecognized string freeze mode returns None."""
        cfg = _make_config(tmp_path, "freeze:\n  mode: invalid_mode\n")
        assert cfg.freeze is None

    def test_string_true_returns_bool_true(self, tmp_path):
        """String 'true' (case-insensitive) returns boolean True."""
        cfg = _make_config(tmp_path, "freeze:\n  mode: 'True'\n")
        assert cfg.freeze is True


# ---------------------------------------------------------------------------
# bibliography returns [] for non-str non-list value
# ---------------------------------------------------------------------------


class TestBibliography:
    def test_non_str_non_list_returns_empty(self, tmp_path):
        """When bibliography is not a string or list, returns []."""
        cfg = _make_config(tmp_path, "bibliography: false\n")
        assert cfg.bibliography == []

    def test_string_returns_single_item_list(self, tmp_path):
        """When bibliography is a string, wraps it in a list."""
        cfg = _make_config(tmp_path, "bibliography: refs.bib\n")
        assert cfg.bibliography == ["refs.bib"]


# ---------------------------------------------------------------------------
# css_files string and list branches
# ---------------------------------------------------------------------------


class TestCssFiles:
    def test_single_string_returns_list(self, tmp_path):
        """A single CSS string is wrapped in a list."""
        cfg = _make_config(tmp_path, "site:\n  css: styles.css\n")
        assert cfg.css == ["styles.css"]

    def test_list_filters_non_strings(self, tmp_path):
        """A list of CSS files filters out non-string entries."""
        cfg = _make_config(tmp_path, "site:\n  css:\n    - custom.css\n    - 42\n    - theme.css\n")
        assert cfg.css == ["custom.css", "theme.css"]


# ---------------------------------------------------------------------------
# nav_icons returns None for non-dict truthy value
# ---------------------------------------------------------------------------


class TestNavIcons:
    def test_non_dict_truthy_returns_none(self, tmp_path):
        """When nav_icons is a truthy non-dict (e.g., string), returns None."""
        cfg = _make_config(tmp_path, "nav_icons: enabled\n")
        assert cfg.nav_icons is None

    def test_dict_with_valid_scopes(self, tmp_path):
        """Dict with navbar/sidebar scopes returns properly normalized."""
        cfg = _make_config(
            tmp_path,
            "nav_icons:\n  navbar:\n    Reference: book-open\n  sidebar:\n    Guide: map\n",
        )
        result = cfg.nav_icons
        assert result == {
            "navbar": {"Reference": "book-open"},
            "sidebar": {"Guide": "map"},
        }

    def test_dict_empty_scopes_returns_none(self, tmp_path):
        """Dict with no valid scopes returns None."""
        cfg = _make_config(tmp_path, "nav_icons:\n  footer:\n    About: info\n")
        assert cfg.nav_icons is None


# ---------------------------------------------------------------------------
# accent_color branches
# ---------------------------------------------------------------------------


class TestAccentColor:
    def test_string_returns_both_light_dark(self, tmp_path):
        """A single color string is used for both light and dark."""
        cfg = _make_config(tmp_path, "accent_color: '#ff6600'\n")
        assert cfg.accent_color == {"light": "#ff6600", "dark": "#ff6600"}

    def test_dict_with_light_and_dark(self, tmp_path):
        """Dict with light and dark keys."""
        cfg = _make_config(tmp_path, "accent_color:\n  light: '#333'\n  dark: '#eee'\n")
        assert cfg.accent_color == {"light": "#333", "dark": "#eee"}

    def test_dict_empty_values_returns_none(self, tmp_path):
        """Dict where all values are falsy returns None."""
        cfg = _make_config(tmp_path, "accent_color:\n  light: ''\n  dark: ''\n")
        assert cfg.accent_color is None

    def test_non_str_non_dict_returns_none(self, tmp_path):
        """A non-str, non-dict truthy value returns None."""
        cfg = _make_config(tmp_path, "accent_color:\n  - red\n  - blue\n")
        assert cfg.accent_color is None


# ---------------------------------------------------------------------------
# navbar_order KeyError case
# ---------------------------------------------------------------------------


class TestNavbarOrder:
    def test_key_missing_raises_keyerror_returns_none(self, tmp_path):
        """When navbar_order key is absent from config entirely, returns None."""
        cfg = Config(tmp_path)
        # Remove the key from the internal config to trigger KeyError in __getitem__
        del cfg._config["navbar_order"]
        assert cfg.navbar_order is None

    def test_valid_list_returns_list(self, tmp_path):
        """When navbar_order is a list of strings, returns it."""
        cfg = _make_config(tmp_path, "navbar_order:\n  - Reference\n  - Guide\n  - Changelog\n")
        assert cfg.navbar_order == ["Reference", "Guide", "Changelog"]


# ---------------------------------------------------------------------------
# scale_to_fit branches
# ---------------------------------------------------------------------------


class TestScaleToFit:
    def test_list_filters_empty_strings(self, tmp_path):
        """List of selectors filters out empty/whitespace-only strings."""
        cfg = _make_config(
            tmp_path, "scale_to_fit:\n  - '.wide-table'\n  - ''\n  - '.code-block'\n"
        )
        assert cfg.scale_to_fit == [".wide-table", ".code-block"]

    def test_single_string_returns_list(self, tmp_path):
        """A single string selector is wrapped in a list."""
        cfg = _make_config(tmp_path, "scale_to_fit: '.data-frame'\n")
        assert cfg.scale_to_fit == [".data-frame"]

    def test_non_list_non_str_returns_none(self, tmp_path):
        """A numeric value (not list/str/None/False) returns None."""
        cfg = _make_config(tmp_path, "scale_to_fit: 42\n")
        assert cfg.scale_to_fit is None


# ---------------------------------------------------------------------------
# scale_to_fit_min_scale branches
# ---------------------------------------------------------------------------


class TestScaleToFitMinScale:
    def test_keyword_mobile(self, tmp_path):
        """Recognized keyword 'mobile' is returned lowercased."""
        cfg = _make_config(tmp_path, "scale_to_fit_min_scale: Mobile\n")
        assert cfg.scale_to_fit_min_scale == "mobile"

    def test_keyword_tablet(self, tmp_path):
        """Recognized keyword 'tablet'."""
        cfg = _make_config(tmp_path, "scale_to_fit_min_scale: tablet\n")
        assert cfg.scale_to_fit_min_scale == "tablet"

    def test_unknown_string_returns_none(self, tmp_path):
        """Unrecognized string keyword returns None."""
        cfg = _make_config(tmp_path, "scale_to_fit_min_scale: xlarge\n")
        assert cfg.scale_to_fit_min_scale is None

    def test_valid_float(self, tmp_path):
        """Float between 0 and 1 is returned as float."""
        cfg = _make_config(tmp_path, "scale_to_fit_min_scale: 0.5\n")
        assert cfg.scale_to_fit_min_scale == 0.5

    def test_float_out_of_range_returns_none(self, tmp_path):
        """Float >= 1 returns None."""
        cfg = _make_config(tmp_path, "scale_to_fit_min_scale: 1.5\n")
        assert cfg.scale_to_fit_min_scale is None

    def test_float_zero_returns_none(self, tmp_path):
        """Float == 0 returns None (not in (0,1) range)."""
        cfg = _make_config(tmp_path, "scale_to_fit_min_scale: 0\n")
        assert cfg.scale_to_fit_min_scale is None

    def test_invalid_type_returns_none(self, tmp_path):
        """A list value returns None (cannot convert to float)."""
        cfg = _make_config(tmp_path, "scale_to_fit_min_scale:\n  - 0.5\n")
        assert cfg.scale_to_fit_min_scale is None
