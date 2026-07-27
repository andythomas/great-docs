"""
great-docs configuration.

`great-docs.default.yml` is the single source of truth for every default; this
module reads a user's merged config and exposes it as typed properties.

Contract for adding an option — keep the single source intact:

- Declare the option and its default in `great-docs.default.yml`, never here.
  This module holds no default values.
- Read through `config["dot.path"]`. The lookup is strict: a key absent from
  the merged config raises `KeyError`.
- Default to a typed empty container (`[]`, `{}`) rather than `null`, unless the
  option is an optional scalar, a genuine tri-state, or a single optional record.
- For an option whose value is a dict of sub-fields, declare those sub-fields
  live in the YAML and expand any scalar/bool shorthand to that dict at load.
  Accessors must not supply sub-field defaults.
- A property is the typed view of an option: a thin one returns `self["key"]`;
  a richer one may coerce shape or derive from other options, but adds no
  default value.
"""

import copy
import io
import re
from importlib import resources
from pathlib import Path
from typing import Any

from yaml12 import read_yaml


def _load_default_config() -> dict[str, Any]:
    """Load the packaged default configuration

    Returns
    -------
    dict
        The parsed contents of `great-docs.default.yml`, i.e. every config
        field at its default value.
    """
    text = (
        resources.files("great_docs")
        .joinpath("assets", "great-docs.default.yml")
        .read_text(encoding="utf-8")
    )
    return read_yaml(io.StringIO(text)) or {}


DEFAULT_CONFIG: dict[str, Any] = _load_default_config()

# great-docs-owned keys that older configs placed under `site`. They are
# top-level keys now; any found under `site` at load are lifted out so `site`
# stays a clean Quarto passthrough.
_LEGACY_SITE_KEYS: tuple[str, ...] = (
    "language",
    "show_dates",
    "date_format",
    "show_author",
    "show_security",
)


class Config:
    """
    Configuration manager for Great Docs.

    Loads configuration from great-docs.yml and provides access to settings
    with sensible defaults.
    """

    def __init__(self, project_root: Path):
        """
        Initialize configuration from great-docs.yml.

        Parameters
        ----------
        project_root
            Path to the project root directory where great-docs.yml is located.
        """
        self.project_root = project_root
        self.config_path = project_root / "great-docs.yml"
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """
        Load configuration from great-docs.yml.

        Returns
        -------
        dict
            The loaded configuration merged with defaults.
        """
        config = copy.deepcopy(DEFAULT_CONFIG)
        self._user_config: dict[str, Any] = {}

        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_config = read_yaml(f) or {}

                self._user_config = user_config
                # Deep merge user config with defaults
                config = self._merge(config, user_config)
            except ValueError as e:
                print(f"Warning: Error parsing great-docs.yml: {e}")
            except Exception as e:
                print(f"Warning: Could not read great-docs.yml: {e}")

        config = self._lift_legacy_site_keys(config)
        config = self._normalize_shorthands(config)
        return config

    def _lift_legacy_site_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        """Move legacy great-docs keys out of `site` to the top level

        Older configs placed language/date settings under `site`; those are
        great-docs-owned, not Quarto `format.html` keys, so they now live at
        the top level. Any that still appear under `site` are lifted out so
        `site` stays a clean Quarto passthrough. An explicit top-level value
        wins over a legacy `site` value on conflict.

        Parameters
        ----------
        config
            The merged configuration.

        Returns
        -------
        dict
            The configuration with the legacy keys normalized to the top level.
        """
        site = config.get("site")
        if not isinstance(site, dict):
            return config

        for key in _LEGACY_SITE_KEYS:
            if key in site:
                value = site.pop(key)
                if key not in self._user_config:
                    config[key] = value
        return config

    # Options accepting a bool shorthand that collapses their dict subtree.
    # The bool sets `enabled`; other sub-fields fall back to the packaged
    # defaults. Kept for backward compatibility; no longer documented.
    _BOOL_SHORTHAND_KEYS: tuple[str, ...] = (
        "page_status",
        "tags",
        "social_cards",
        "markdown_pages",
    )

    def _normalize_shorthands(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Expand shorthand config values into their canonical dict form

        A user may write a scalar where the canonical form is a dict (e.g.
        `page_status: true`, or an explicit `social_cards: null`). Each such
        value is rebuilt into the full dict, with `enabled` set from the
        scalar, so downstream access is always a plain nested lookup.

        Parameters
        ----------
        config
            The merged configuration.

        Returns
        -------
        dict
            The configuration with shorthand values expanded.
        """
        for key in self._BOOL_SHORTHAND_KEYS:
            raw = config.get(key)
            if isinstance(raw, bool) or raw is None:
                merged = copy.deepcopy(DEFAULT_CONFIG[key])
                merged["enabled"] = bool(raw)
                config[key] = merged

        # `hero` is excluded from the loop above: its `enabled` sub-field
        # defaults to `None` (auto — enable when a logo exists), which the
        # bool-shorthand loop would collapse to `False`.
        raw = config.get("hero")
        if not isinstance(raw, dict):
            merged = copy.deepcopy(DEFAULT_CONFIG["hero"])
            if isinstance(raw, bool):
                merged["enabled"] = raw
            # raw is None -> keep enabled: null (auto)
            config["hero"] = merged

        return config

    @staticmethod
    def _merge(defaults: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two config-shaped mappings

        Values in `user` win; dicts present in both are merged recursively.
        `defaults` is not mutated — a new mapping is returned. Also used to
        overlay the `site` subtree onto `_quarto.yml` `format.html`.

        Parameters
        ----------
        defaults
            Base configuration values.
        user
            Overriding configuration values (take precedence).

        Returns
        -------
        dict
            Merged configuration.
        """
        result = defaults.copy()

        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Config._merge(result[key], value)
            else:
                result[key] = value

        return result

    def __getitem__(self, key: str) -> Any:
        """
        Return the configuration value at a dot-separated key

        Parameters
        ----------
        key
            A dot-path such as `"seo.sitemap.enabled"`.

        Returns
        -------
        Any
            The value in the merged configuration at that path.

        Raises
        ------
        KeyError
            If any segment is absent or traversal reaches a non-mapping.
        """
        value: Any = self._config
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                raise KeyError(key)
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value at a dot-path, or `default` when it is absent"""
        try:
            return self[key]
        except KeyError:
            return default

    @property
    def exclude(self) -> list[str]:
        """Get the list of items to exclude."""
        return self.get("exclude", [])

    @property
    def auto_include(self) -> list[str]:
        """Get names to force-include even if they match AUTO_EXCLUDE."""
        return self.get("auto_include", [])

    @property
    def no_auto_exclude(self) -> bool:
        """Check if the built-in AUTO_EXCLUDE list should be bypassed."""
        return self.get("no_auto_exclude", False)

    @property
    def project_type(self) -> list[str]:
        """Get the project type(s).

        Describes the primary ecosystem(s) the project belongs to.

        Returns
        -------
        list[str]
            Always a list, e.g. `["python"]`, `["go"]`, or `["python", "go"]` for mixed projects.
        """
        val = self.get("project_type", "python")
        if isinstance(val, list):
            return [str(t).lower() for t in val]
        return [str(val).lower()]

    @property
    def is_python_project(self) -> bool:
        """Return `True` when the project includes a Python component."""
        return "python" in self.project_type

    @property
    def pypi(self) -> bool | str:
        """Get the PyPI link configuration.

        Returns
        -------
        bool | str
            - True: auto-detect package name and link to pypi.org (default for Python projects)
            - False: disable the PyPI link entirely
            - str: custom package index URL
        """
        # If the user has explicitly set pypi in great-docs.yml, honour it regardless of
        # project_type
        if "pypi" in self._user_config:
            return self._user_config["pypi"]
        # Non-Python projects default to no PyPI link
        if not self.is_python_project:
            return False
        return True

    @property
    def repo(self) -> str | None:
        """Get the GitHub repository URL override."""
        return self.get("repo")

    @property
    def site_url(self) -> str | None:
        """Get the site URL for subdirectory deployments."""
        return self.get("site_url")

    @property
    def github_style(self) -> str:
        """Get the GitHub link style."""
        return self.get("github_style", "widget")

    @property
    def source_enabled(self) -> bool:
        """Check if source links are enabled."""
        return self.get("source.enabled", True)

    @property
    def source_branch(self) -> str | None:
        """Get the source link branch."""
        return self.get("source.branch")

    @property
    def source_path(self) -> str | None:
        """Get the custom source path."""
        return self.get("source.path")

    @property
    def source_placement(self) -> str:
        """Get the source link placement."""
        return self.get("source.placement", "usage")

    @property
    def sidebar_filter_enabled(self) -> bool:
        """Check if sidebar filter is enabled."""
        return self.get("sidebar_filter.enabled", True)

    @property
    def sidebar_filter_min_items(self) -> int:
        """Get the minimum items for sidebar filter."""
        return self.get("sidebar_filter.min_items", 20)

    @property
    def cli_enabled(self) -> bool:
        """Check if CLI documentation is enabled."""
        return self.get("cli.enabled", False)

    @property
    def cli_module(self) -> str | None:
        """Get the CLI module path."""
        return self.get("cli.module")

    @property
    def cli_name(self) -> str | None:
        """Get the CLI command name."""
        return self.get("cli.name")

    @property
    def cli_title(self) -> str | None:
        """Get the custom CLI reference index title, if set.

        Supports `cli: {title: "Custom Title"}` in great-docs.yml. Returns `None` when no custom
        title is configured (the caller falls back to a translated default).
        """
        return self.get("cli.title")

    @property
    def cli_desc(self) -> str | None:
        """Get the CLI reference index intro paragraph, if set.

        Supports `cli: {desc: "Intro text..."}` in great-docs.yml. Returns `None` when no
        description is configured.
        """
        return self.get("cli.desc")

    @property
    def cli_sections(self) -> list[dict[str, Any]]:
        """Get the explicit CLI reference index sections.

        Mirrors the `reference:` config. Supports a list of section dicts under `cli.sections`::

            cli:
              sections:
                - title: Project setup
                  desc: "..."
                  contents: [init, config, uninstall]

        Each `contents` entry is a top-level command name (string). Returns an empty list when no
        explicit sections are configured (triggering auto-grouping by command group).
        """
        val = self.get("cli.sections", [])
        if isinstance(val, list):
            return val
        return []

    @property
    def go_cli_enabled(self) -> bool:
        """Check if Go CLI documentation is enabled.

        When `True`, great-docs will detect the Go CLI project at the package root, compile it, and
        extract the command tree via `--help` to generate a CLI reference section.
        """
        return self.get("go_cli.enabled", False)

    @property
    def mcp_enabled(self) -> bool:
        """Check if MCP server documentation is enabled."""
        return self.get("mcp.enabled", False)

    @property
    def mcp_module(self) -> str | None:
        """Get the MCP server module path."""
        return self.get("mcp.module")

    @property
    def mcp_server_var(self) -> str | None:
        """Get the MCP server variable name."""
        return self.get("mcp.server_var")

    @property
    def mcp_name(self) -> str | None:
        """Get the MCP server display name override."""
        return self.get("mcp.name")

    @property
    def mcp_categories(self) -> dict:
        """Get manual MCP tool categories."""
        return self.get("mcp.categories", {})

    @property
    def skill_enabled(self) -> bool:
        """Check if skill.md generation is enabled."""
        return self.get("skill.enabled", True)

    @property
    def skill_file(self) -> str | None:
        """Get the path to a hand-written SKILL.md override."""
        return self.get("skill.file")

    @property
    def skill_well_known(self) -> bool:
        """Check if .well-known/agent-skills/ discovery files should be generated."""
        return self.get("skill.well_known", True)

    @property
    def skill_gotchas(self) -> list[str]:
        """Get the list of gotcha strings for the SKILL.md Gotchas section."""
        return self.get("skill.gotchas", [])

    @property
    def skill_best_practices(self) -> list[str]:
        """Get the list of best-practice strings for the SKILL.md."""
        return self.get("skill.best_practices", [])

    @property
    def skill_decision_table(self) -> list[dict]:
        """Get manual decision table rows for the SKILL.md."""
        return self.get("skill.decision_table", [])

    @property
    def skill_extra_body(self) -> str | None:
        """Get the path to extra Markdown to append to the generated SKILL.md body."""
        return self.get("skill.extra_body")

    @property
    def skill_skills(self) -> list[dict]:
        """Get the list of named skills for multi-skill distribution.

        Each entry should have `name` and `file` keys. When non-empty, this overrides the single
        `skill.file` setting.
        """
        return self.get("skill.skills", [])

    @property
    def changelog_enabled(self) -> bool:
        """Check if changelog generation from GitHub Releases is enabled."""
        return self.get("changelog.enabled", True)

    @property
    def changelog_max_releases(self) -> int:
        """Get the maximum number of GitHub Releases to include."""
        return self.get("changelog.max_releases", 50)

    @property
    def sections(self) -> list[dict]:
        """Get the custom sections configuration."""
        return self.get("sections", [])

    @property
    def custom_pages(self) -> list[dict[str, str]]:
        """Get normalized custom static page source directories.

        Returns a list of dicts with `dir` and `output` keys.

        - When `custom_pages` is omitted, falls back to `custom/`.
        - When `custom_pages` is `false`, returns an empty list.
        - When `custom_pages` is a string, that path is used and the output prefix defaults to the
          basename of the path.
        - When `custom_pages` is a dict, it may specify `dir` and optional `output`.
        - When `custom_pages` is a list, each entry may be a string or dict.
        """
        raw = self.get("custom_pages")

        if raw is None:
            return [{"dir": "custom", "output": "custom"}]

        if raw is False:
            return []

        entries: list[Any]
        if isinstance(raw, list):
            entries = raw
        else:
            entries = [raw]

        normalized: list[dict[str, str]] = []

        for entry in entries:
            if isinstance(entry, str):
                output = Path(entry).name or entry
                normalized.append({"dir": entry, "output": output})
                continue

            if isinstance(entry, dict):
                source_dir = entry.get("dir")
                if not isinstance(source_dir, str) or not source_dir:
                    continue

                output = entry.get("output")
                if not isinstance(output, str) or not output:
                    output = Path(source_dir).name or source_dir

                normalized.append({"dir": source_dir, "output": output})

        return normalized

    @property
    def dark_mode_toggle(self) -> bool:
        """Check if dark mode toggle is enabled."""
        return self.get("dark_mode_toggle", True)

    @property
    def keyboard_nav(self) -> bool:
        """Check if keyboard navigation shortcuts are enabled."""
        return self.get("keyboard_nav", True)

    @property
    def package_info_page(self) -> bool:
        """Check if package info page generation is enabled."""
        return self.get("package_info_page", True)

    @property
    def back_to_top(self) -> bool:
        """Check if back-to-top button is enabled."""
        return self.get("back_to_top", True)

    @property
    def markdown_pages(self) -> bool:
        """Whether Markdown companion pages are generated"""
        return bool(self["markdown_pages.enabled"])

    @property
    def markdown_pages_widget(self) -> bool:
        """Whether the copy-page widget is shown (requires markdown_pages)"""
        return bool(self["markdown_pages.widget"]) and self.markdown_pages

    @property
    def parser(self) -> str:
        """Get the docstring parser format (numpy, google, or sphinx)."""
        return self.get("parser", "numpy")

    @property
    def dynamic(self) -> bool:
        """Get the dynamic introspection mode for API reference generation."""
        return self.get("dynamic", True)

    @property
    def module(self) -> str | None:
        """
        Get the explicit module name (importable name).

        Use this when the importable module name differs from the project name,
        e.g., project 'py-yaml12' with module 'yaml12'.
        """
        return self.get("module")

    @property
    def display_name(self) -> str | None:
        """
        Get the display name for the site.

        Use this to customize how the package name appears in the navbar/title,
        e.g., 'Great Docs' instead of 'great_docs' or 'great-docs'.
        """
        return self.get("display_name")

    @property
    def homepage(self) -> str:
        """Get the homepage mode ('index' or 'user_guide').

        Returns
        -------
        str
            The validated homepage mode. Falls back to 'index' if an
            invalid value is configured.
        """
        value = self.get("homepage", "index")
        if value not in ("index", "user_guide"):
            print(f"Warning: Invalid homepage value '{value}', defaulting to 'index'")
            return "index"
        return value

    @property
    def user_guide(self) -> str | list | None:
        """Get the user guide configuration.

        Returns
        -------
        str | list | None
            - None: auto-discover from conventional directories
            - str: custom directory path for user guide files
            - list: explicit section ordering (list of section dicts)
        """
        return self.get("user_guide")

    @property
    def user_guide_is_explicit(self) -> bool:
        """Check if user guide uses explicit section ordering."""
        return isinstance(self.get("user_guide"), list)

    @property
    def user_guide_dir(self) -> str | None:
        """Get the user guide directory path (only when it's a string)."""
        val = self.get("user_guide")
        return val if isinstance(val, str) else None

    @property
    def reference_enabled(self) -> bool:
        """Whether API reference generation is enabled.

        Returns `False` when the config contains `reference: false`. Defaults to `True`.
        """
        val = self.get("reference", [])
        if val is False:
            return False
        return True

    @property
    def reference(self) -> list[dict[str, Any]]:
        """Get the API reference configuration (explicit section ordering).

        Supports two forms in great-docs.yml:

        1. List form (sections directly)::

            reference:
              - title: Core
                contents: [...]

        2. Dict form with embedded sections::

            reference:
              title: "API Docs"
              desc: "..."
              sections:
                - title: Core
                  contents: [...]

        Returns the list of section dicts, or an empty list when no
        explicit sections are configured (triggering auto-discovery).
        """
        val = self.get("reference", [])
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            sections = val.get("sections")
            if isinstance(sections, list):
                return sections
        return []

    @property
    def reference_title(self) -> str | None:
        """Get the custom API reference title, if set.

        Supports `reference: {title: "Custom Title"}` in great-docs.yml. Returns `None` when no
        custom title is configured.
        """
        val = self.get("reference", [])
        if isinstance(val, dict):
            return val.get("title")
        return None

    @property
    def reference_desc(self) -> str | None:
        """Get the custom API reference description, if set.

        Supports `reference: {desc: "Description text..."}` in great-docs.yml. Returns `None` when
        no description is configured.
        """
        val = self.get("reference", [])
        if isinstance(val, dict):
            return val.get("desc")
        return None

    def should_split_methods(self, method_count: int) -> bool:
        """Whether a class with this many methods should split them to separate pages.

        Controlled by `inline_methods` in great-docs.yml:
        - true: never split (always inline)
        - false: always split
        - int N: split when method_count > N (default: 5)

        Items with no methods are never split regardless of the setting.
        """
        if method_count == 0:
            return False
        val = self.get("inline_methods", 5)
        if val is True:
            return False
        if val is False:
            return True
        try:
            return method_count > int(val)
        except (TypeError, ValueError):
            return method_count > 5

    @property
    def authors(self) -> list[dict[str, Any]]:
        """Get the rich author metadata."""
        return self.get("authors", [])

    @property
    def funding(self) -> dict[str, Any] | None:
        """
        Get the funding organization metadata.

        Returns a dict with keys: name, roles (list), ror (ROR URL).
        Example: {"name": "Posit Software, PBC", "roles": ["Copyright holder", "funder"], "ror": "https://ror.org/03wc8by49"}
        """
        return self.get("funding")

    @property
    def site(self) -> dict[str, Any]:
        """Get the site settings — a pure Quarto passthrough into format.html."""
        return self.get("site", {})

    @property
    def site_quarto(self) -> dict[str, Any]:
        """Get the `site` subtree destined for `_quarto.yml` `format.html`

        Legacy great-docs keys are already normalized out of `site` at load;
        `css` is removed here because great-docs copies the file and references
        it by basename separately.

        Returns
        -------
        dict
            The site settings safe to merge blindly into `format.html`.
        """
        site = dict(self.site)
        site.pop("css", None)
        return site

    @property
    def show_dates(self) -> bool:
        """Whether to show page metadata timestamps in the footer."""
        return bool(self.get("show_dates", False))

    @property
    def date_format(self) -> str:
        """Get the date format string (Python strftime format)."""
        return self.get("date_format", "%B %d, %Y")

    @property
    def show_author(self) -> bool:
        """Whether to show author attribution when dates are enabled."""
        return bool(self.get("show_author", True))

    @property
    def show_security(self) -> bool:
        """Whether to show the security policy page when SECURITY.md exists."""
        return bool(self.get("show_security", True))

    @property
    def language(self) -> str:
        """Get the site UI language (BCP 47 code, default 'en')."""
        return self.get("language", "en")

    @property
    def team_author(self) -> dict[str, Any] | None:
        """Get the team author configuration for auto-generated pages.

        Returns
        -------
        dict | None
            A dict with keys: name (str), image (str|None), url (str|None).
            Returns None when not configured.
        """
        raw = self.get("team_author")
        if raw is None:
            return None
        if isinstance(raw, dict) and raw.get("name"):
            return {
                "name": raw["name"],
                "image": raw.get("image"),
                "url": raw.get("url"),
            }
        return None

    @property
    def jupyter(self) -> str:
        """Get the Jupyter kernel for executing code cells."""
        return self.get("jupyter", "python3")

    @property
    def logo(self) -> dict[str, Any] | None:
        """Get the normalized logo configuration.

        Returns
        -------
        dict | None
            Normalized logo dict with at least `light` key, or `None` if no logo is configured. A
            bare string in `great-docs.yml` is expanded to `{"light": "<path>", "dark": "<path>"}`.
        """
        raw = self.get("logo")
        if raw is None:
            return None
        if isinstance(raw, str):
            return {"light": raw, "dark": raw}
        if isinstance(raw, dict):
            return raw
        return None

    @property
    def logo_show_title(self) -> bool:
        """Whether to show the text title alongside the logo."""
        logo = self.logo
        if isinstance(logo, dict):
            return bool(logo.get("show_title", False))
        return False

    @property
    def hero(self) -> dict[str, Any]:
        """Resolved hero configuration"""
        return self["hero"]

    @property
    def hero_enabled(self) -> bool:
        """Whether the hero section is shown"""
        enabled = self["hero.enabled"]
        if enabled is None:
            return self.logo is not None or self["hero.logo"] not in (None, False)
        return bool(enabled)

    @property
    def hero_explicitly_disabled(self) -> bool:
        """Whether the hero was turned off explicitly"""
        return self["hero.enabled"] is False

    @property
    def hero_logo(self) -> str | dict | None | bool:
        """The hero-specific logo, or `False` when suppressed"""
        return self["hero.logo"]

    @property
    def hero_logo_height(self) -> str:
        """The hero logo max-height CSS value"""
        return self["hero.logo_height"]

    @property
    def hero_name(self) -> str | bool | None:
        """The hero name, falling back to the display name"""
        val = self["hero.name"]
        if val is False:
            return False
        if val is not None:
            return val
        return self.display_name

    @property
    def hero_tagline(self) -> str | None:
        """The hero tagline, or `None` when suppressed"""
        val = self["hero.tagline"]
        return None if val is False else val

    @property
    def hero_starfield(self) -> bool:
        """Whether the starfield animation is enabled"""
        return bool(self["hero.starfield"])

    @property
    def hero_badges(self) -> str | list | None:
        """The hero badges config (`'auto'`, an explicit list, or `None`)"""
        val = self["hero.badges"]
        return None if val is False else val

    @property
    def favicon(self) -> dict[str, Any] | None:
        """Get the normalized favicon configuration.

        Returns
        -------
        dict | None
            Normalized favicon dict with at least `icon` key, or `None` if no favicon is explicitly
            configured (auto-generation may still produce one from the logo).
        """
        raw = self.get("favicon")
        if raw is None:
            return None
        if isinstance(raw, str):
            return {"icon": raw}
        if isinstance(raw, dict):
            return raw
        return None

    @property
    def announcement(self) -> dict[str, Any] | None:
        """Get the normalized announcement banner configuration.

        Returns
        -------
        dict | None
            Normalized dict with keys: `content`, `type`, `dismissable`, `url`, `style`,
            `position`. Returns `None` if no announcement is configured.
        """
        raw = self.get("announcement")
        if raw is None or raw is False:
            return None
        if isinstance(raw, str):
            return {
                "content": raw,
                "type": "info",
                "dismissable": True,
                "url": None,
                "style": None,
                "position": "above-navbar",
            }
        if isinstance(raw, dict):
            content = raw.get("content")
            if not content:
                return None
            position = raw.get("position", "above-navbar")
            if position not in ("above-navbar", "below-navbar"):
                position = "above-navbar"
            return {
                "content": content,
                "type": raw.get("type", "info"),
                "dismissable": raw.get("dismissable", True),
                "url": raw.get("url"),
                "style": raw.get("style"),
                "position": position,
            }
        return None

    @property
    def versions(self) -> list:
        """Get the raw versions list from config."""
        return self.get("versions", [])

    @property
    def has_versions(self) -> bool:
        """Whether multi-version documentation is enabled."""
        return bool(self.versions)

    @property
    def version_selector_enabled(self) -> bool:
        """Whether the version selector widget is enabled."""
        if not self.has_versions:
            return False
        return self.get("version_selector.enabled", True)

    @property
    def version_selector_placement(self) -> str:
        """Get the version selector placement."""
        return self.get("version_selector.placement", "navbar-right")

    @property
    def version_warning_banner(self) -> bool:
        """Whether to show warning banners on non-latest versions."""
        return self.get("version_selector.warning_banner", True)

    @property
    def version_aliases(self) -> dict:
        """Get the version aliases configuration."""
        return self.get("version_aliases", {"latest": True, "stable": True, "dev": True})

    @property
    def include_in_header(self) -> list[dict[str, str]]:
        """Get the normalized include-in-header entries.

        Returns a list of Quarto-compatible include-in-header items (each a dict with either a
        "text" or "file" key).
        """
        raw = self.get("include_in_header", [])
        if raw is None:
            return []
        if isinstance(raw, str):
            return [{"text": raw}]
        if isinstance(raw, list):
            result: list[dict[str, str]] = []
            for item in raw:
                if isinstance(item, str):
                    result.append({"text": item})
                elif isinstance(item, dict):
                    result.append(item)
            return result
        return []

    @property
    def freeze(self) -> str | bool | None:
        """Get the freeze mode for Quarto code execution caching.

        Returns
        -------
        str | bool | None
            - None or False: freeze disabled
            - "auto": re-render only when source changes
            - True: never re-render during project render
        """
        raw = self.get("freeze")
        if raw is None or raw is False:
            return None
        if isinstance(raw, dict):
            return raw.get("mode", "auto")
        if raw is True or raw == "auto":
            return raw
        # Accept string "true" as True
        if isinstance(raw, str) and raw.lower() == "true":
            return True
        return None

    @property
    def pre_render(self) -> list[str]:
        """Get the normalized list of pre-render script paths.

        Combines scripts from both ``freeze.pre_render`` and the top-level ``pre_render`` key.

        Returns
        -------
        list[str]
            List of script paths relative to the project root.
        """
        scripts: list[str] = []

        # Check freeze dict form for pre_render
        raw_freeze = self.get("freeze")
        if isinstance(raw_freeze, dict):
            freeze_scripts = raw_freeze.get("pre_render")
            if isinstance(freeze_scripts, str):
                scripts.append(freeze_scripts)
            elif isinstance(freeze_scripts, list):
                scripts.extend(s for s in freeze_scripts if isinstance(s, str))

        # Check top-level pre_render
        raw_pre = self.get("pre_render")
        if isinstance(raw_pre, str):
            if raw_pre not in scripts:
                scripts.append(raw_pre)
        elif isinstance(raw_pre, list):
            for s in raw_pre:
                if isinstance(s, str) and s not in scripts:
                    scripts.append(s)

        return scripts

    @property
    def bibliography(self) -> list[str]:
        """Get the normalized list of bibliography file paths.

        Accepts a single path string or a list of paths in `great-docs.yml`. Paths are relative to
        the project root.

        Returns
        -------
        list[str]
            List of bibliography (`.bib`) file paths, or an empty list if none.
        """
        raw = self.get("bibliography")
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, list):
            return [s for s in raw if isinstance(s, str)]
        return []

    @property
    def csl(self) -> str | None:
        """Get the citation style language (CSL) file path.

        Returns
        -------
        str | None
            Path to the `.csl` file relative to the project root, or `None`.
        """
        raw = self.get("csl")
        if isinstance(raw, str):
            return raw
        return None

    @property
    def css(self) -> list[str]:
        """Get the normalized list of custom CSS file paths.

        Accepts a single path string or a list of paths under `site.css` in
        `great-docs.yml`. Paths are relative to the project root.

        Returns
        -------
        list[str]
            List of `.css` file paths, or an empty list if none.
        """
        raw = self.site.get("css")
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, list):
            return [s for s in raw if isinstance(s, str)]
        return []

    @property
    def nav_icons(self) -> dict[str, dict[str, str]] | None:
        """Get the normalized navigation icons configuration.

        Returns
        -------
        dict | None
            A dict with optional `navbar` and `sidebar` keys, each mapping navigation label text to
            a Lucide icon name. Returns `None` when not configured.
        """
        raw = self.get("nav_icons")
        if raw is None or raw is False:
            return None
        if isinstance(raw, dict):
            result: dict[str, dict[str, str]] = {}
            for scope in ("navbar", "sidebar"):
                mapping = raw.get(scope)
                if isinstance(mapping, dict):
                    result[scope] = {str(k): str(v) for k, v in mapping.items()}
            return result if result else None
        return None

    @property
    def nav_icons_navbar(self) -> dict[str, str]:
        """Get the navbar icon mapping (label -> icon name)."""
        icons = self.nav_icons
        if icons is None:
            return {}
        return icons.get("navbar", {})

    @property
    def nav_icons_sidebar(self) -> dict[str, str]:
        """Get the sidebar icon mapping (label -> icon name)."""
        icons = self.nav_icons
        if icons is None:
            return {}
        return icons.get("sidebar", {})

    @property
    def attribution(self) -> bool:
        """Whether to show Great Docs attribution in the footer."""
        return bool(self.get("attribution", True))

    @property
    def accent_color(self) -> dict[str, str] | None:
        """Get the normalized accent color configuration.

        Returns
        -------
        dict[str, str] | None
            A dict with `"light"` and/or `"dark"` keys mapping to CSS color strings. Returns `None`
            when not configured.
        """
        raw = self.get("accent_color")
        if raw is None or raw is False:
            return None
        if isinstance(raw, str):
            return {"light": raw, "dark": raw}
        if isinstance(raw, dict):
            result: dict[str, str] = {}
            for key in ("light", "dark"):
                val = raw.get(key)
                if val and isinstance(val, str):
                    result[key] = val
            return result if result else None
        return None

    @property
    def navbar_style(self) -> str | None:
        """Get the navbar gradient preset name."""
        raw = self.get("navbar_style")
        if raw and isinstance(raw, str):
            return raw
        return None

    @property
    def navbar_color(self) -> dict[str, str] | None:
        """Get the normalized navbar color configuration.

        Returns
        -------
        dict[str, str] | None
            A dict with `"light"` and/or `"dark"` keys mapping to CSS color strings. Returns `None`
            when not configured or when `navbar_style` (gradient) takes precedence.
        """
        if self.navbar_style:
            return None
        raw = self.get("navbar_color")
        if raw is None or raw is False:
            return None
        if isinstance(raw, str):
            return {"light": raw, "dark": raw}
        if isinstance(raw, dict):
            result: dict[str, str] = {}
            for key in ("light", "dark"):
                val = raw.get(key)
                if val and isinstance(val, str):
                    result[key] = val
            return result if result else None
        return None

    @property
    def content_style(self) -> dict[str, str] | None:
        """Get the normalized content area gradient configuration."""
        raw = self.get("content_style")
        if raw is None or raw is False:
            return None
        if isinstance(raw, str):
            return {"preset": raw, "pages": "all"}
        if isinstance(raw, dict):
            preset = raw.get("preset")
            if not preset or not isinstance(preset, str):
                return None
            pages = raw.get("pages", "all")
            if pages not in ("all", "homepage"):
                pages = "all"
            return {"preset": preset, "pages": pages}
        return None

    @property
    def scale_to_fit(self) -> list[str] | None:
        """Get the list of CSS selectors for auto-scale-to-fit."""
        raw = self.get("scale_to_fit")
        if raw is None or raw is False:
            return None
        if isinstance(raw, list):
            return [s for s in raw if isinstance(s, str) and s.strip()]
        if isinstance(raw, str):
            return [raw]
        return None

    # ── Social Cards Properties ────────────────────────────────────────────

    _SCALE_KEYWORDS = frozenset({"mobile", "tablet", "desktop"})

    @property
    def scale_to_fit_min_scale(self) -> float | str | None:
        """Get the minimum scale threshold for scale-to-fit.

        Returns a float (0-1), a keyword (`"mobile"`, `"tablet"`, `"desktop"`), or `None`.
        """
        raw = self.get("scale_to_fit_min_scale")
        if raw is None or raw is False:
            return None
        if isinstance(raw, str):
            key = raw.strip().lower()
            if key in self._SCALE_KEYWORDS:
                return key
            return None
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return None
        if 0 < val < 1:
            return val
        return None

    @property
    def social_cards_enabled(self) -> bool:
        """Whether social card meta tags are enabled"""
        return bool(self["social_cards.enabled"])

    @property
    def social_cards_image(self) -> str | None:
        """Default social card image path"""
        return self["social_cards.image"]

    @property
    def social_cards_twitter_card(self) -> str | None:
        """Twitter card type override"""
        return self["social_cards.twitter_card"]

    @property
    def social_cards_twitter_site(self) -> str | None:
        """Twitter site `@handle`"""
        return self["social_cards.twitter_site"]

    # ── Page Status Properties ────────────────────────────────────────────

    @property
    def page_status_enabled(self) -> bool:
        """Whether page status badges are enabled"""
        return bool(self["page_status.enabled"])

    @property
    def page_status_show_in_sidebar(self) -> bool:
        """Whether status badges appear in the sidebar"""
        return self.page_status_enabled and self["page_status.show_in_sidebar"]

    @property
    def page_status_show_on_pages(self) -> bool:
        """Whether status indicators appear below page titles"""
        return self.page_status_enabled and self["page_status.show_on_pages"]

    @property
    def page_status_definitions(self) -> dict[str, dict[str, str]]:
        """Status definitions (built-in plus any user overrides)"""
        return self["page_status.statuses"]

    # ── Page Tags Properties ─────────────────────────────────────────────

    @property
    def tags_enabled(self) -> bool:
        """Whether page tags are enabled"""
        return bool(self["tags.enabled"])

    @property
    def tags_index_page(self) -> bool:
        """Whether a tags index page is generated"""
        return self.tags_enabled and self["tags.index_page"]

    @property
    def tags_show_on_pages(self) -> bool:
        """Whether tags are rendered above page titles"""
        return self.tags_enabled and self["tags.show_on_pages"]

    @property
    def tags_location(self) -> str:
        """Default tag pill placement, `"top"` or `"bottom"`"""
        val = self["tags.location"]
        if val in ("top", "bottom"):
            return val
        return "top"

    @property
    def tags_hierarchical(self) -> bool:
        """Whether hierarchical tags (using '/') are supported"""
        return self["tags.hierarchical"]

    @property
    def tags_icons(self) -> dict[str, str]:
        """Tag-to-icon mapping"""
        return self["tags.icons"]

    @property
    def tags_shadow(self) -> list[str]:
        """Shadow tags, hidden from public view"""
        return self["tags.shadow"]

    @property
    def tags_scoped(self) -> bool:
        """Whether scoped tag listings per section are enabled"""
        return self["tags.scoped"]

    # ── SEO Configuration Properties ─────────────────────────────────────────

    @property
    def seo_enabled(self) -> bool:
        """Check if SEO features are enabled."""
        return self.get("seo.enabled", True)

    @property
    def sitemap_enabled(self) -> bool:
        """Check if sitemap.xml generation is enabled."""
        return self.seo_enabled and self.get("seo.sitemap.enabled", True)

    @property
    def sitemap_changefreq(self) -> dict[str, str]:
        """Sitemap change frequency by page type"""
        return self["seo.sitemap.changefreq"]

    @property
    def sitemap_priority(self) -> dict[str, float]:
        """Sitemap priority by page type"""
        return self["seo.sitemap.priority"]

    @property
    def robots_enabled(self) -> bool:
        """Check if robots.txt generation is enabled."""
        return self.seo_enabled and self.get("seo.robots.enabled", True)

    @property
    def robots_allow_all(self) -> bool:
        """Check if robots.txt should allow all crawlers."""
        return self.get("seo.robots.allow_all", True)

    @property
    def robots_disallow(self) -> list[str]:
        """Get the list of paths to disallow in robots.txt."""
        return self.get("seo.robots.disallow", [])

    @property
    def robots_crawl_delay(self) -> int | None:
        """Get the optional crawl delay in seconds."""
        return self.get("seo.robots.crawl_delay")

    @property
    def robots_extra_rules(self) -> list[str]:
        """Get additional robots.txt rules."""
        return self.get("seo.robots.extra_rules", [])

    @property
    def canonical_enabled(self) -> bool:
        """Check if canonical URLs are enabled."""
        return self.seo_enabled and self.get("seo.canonical.enabled", True)

    @property
    def canonical_base_url(self) -> str | None:
        """Get the canonical base URL."""
        return self.get("seo.canonical.base_url")

    @property
    def seo_title_template(self) -> str:
        """Get the page title template."""
        return self.get("seo.title_template", "{page_title} | {site_name}")

    @property
    def structured_data_enabled(self) -> bool:
        """Check if JSON-LD structured data is enabled."""
        return self.seo_enabled and self.get("seo.structured_data.enabled", True)

    @property
    def structured_data_type(self) -> str:
        """Get the Schema.org type for structured data."""
        return self.get("seo.structured_data.type", "SoftwareSourceCode")

    @property
    def seo_default_description(self) -> str | None:
        """Get the default meta description."""
        return self.get("seo.default_description")

    def exists(self) -> bool:
        """Check if the configuration file exists."""
        return self.config_path.exists()

    def to_dict(self) -> dict[str, Any]:
        """
        Get the full configuration as a dictionary.

        Returns
        -------
        dict
            The complete configuration.
        """
        return self._config.copy()


def load_config(project_root: Path | str) -> Config:
    """
    Load Great Docs configuration from a project.

    Parameters
    ----------
    project_root
        Path to the project root directory.

    Returns
    -------
    Config
        The loaded configuration.
    """
    return Config(Path(project_root))


_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][\w-]*):")


def create_default_config(overrides: dict[str, str] | None = None) -> str:
    """
    Generate great-docs.yml content from the shipped default template

    The `great-docs.default.yml` template is emitted with every live value line
    commented out, so a fresh file documents every option without overriding
    the packaged defaults. Any top-level key named in `overrides` is instead
    emitted live, with its default (and any indented block body) replaced by
    the supplied text.

    Parameters
    ----------
    overrides
        Maps a top-level key to pre-rendered YAML text that replaces the
        commented default for that key. Used by `great-docs init` to splice in
        detected values (`parser`, `dynamic`, `module`, `authors`, `reference`).

    Returns
    -------
    str
        The rendered great-docs.yml content.
    """
    text = (
        resources.files("great_docs")
        .joinpath("assets", "great-docs.default.yml")
        .read_text(encoding="utf-8")
    )
    overrides = overrides or {}
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            out.append(line)
            continue
        match = _TOP_LEVEL_KEY.match(line)
        key = match.group(1) if match else None
        if key is not None and key in overrides:
            out.append(overrides[key] + "\n")
            # Drop the replaced key's old block body (indented lines).
            while i < len(lines) and lines[i].strip() and lines[i][:1] in (" ", "\t"):
                i += 1
        else:
            out.append(f"# {line}")
    return "".join(out)
