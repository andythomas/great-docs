# pyright: reportPrivateUsage=false
"""Tests targeting specific uncovered lines in great_docs/core.py."""

from __future__ import annotations

import importlib
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import requests

from great_docs import GreatDocs


def _make_gd(tmp_path: Path) -> GreatDocs:
    """Create a GreatDocs instance in a temp directory with minimal config."""
    (tmp_path / "great-docs.yml").write_text("module: mypkg\n", encoding="utf-8")
    return GreatDocs(project_path=str(tmp_path))


# ===========================================================================
# _fetch_github_repo_stats
# ===========================================================================


class TestFetchGithubRepoStats:
    """Cover _fetch_github_repo_stats auth header and response paths."""

    def test_success_with_token(self, tmp_path, monkeypatch):
        """Token is used and success data returned."""
        gd = _make_gd(tmp_path)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"stargazers_count": 42, "forks_count": 7}

        monkeypatch.setattr(requests, "get", lambda *a, **kw: mock_resp)

        result = gd._fetch_github_repo_stats("posit-dev", "great-docs")
        assert result == {"stars": 42, "forks": 7}

    def test_request_exception_returns_empty(self, tmp_path, monkeypatch):
        """RequestException is swallowed, returns {}."""
        gd = _make_gd(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)

        def raise_exc(*a, **kw):
            raise requests.RequestException("network error")

        monkeypatch.setattr(requests, "get", raise_exc)

        result = gd._fetch_github_repo_stats("owner", "repo")
        assert result == {}

    def test_non_200_returns_empty(self, tmp_path, monkeypatch):
        """Non-200 status code returns empty dict."""
        gd = _make_gd(tmp_path)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 404

        monkeypatch.setattr(requests, "get", lambda *a, **kw: mock_resp)

        result = gd._fetch_github_repo_stats("owner", "repo")
        assert result == {}


# ===========================================================================
# _find_click_cli_obj
# ===========================================================================


class TestFindClickCliObj:
    """Cover all branches of _find_click_cli_obj."""

    def test_cli_not_enabled_returns_none(self, tmp_path, monkeypatch):
        """cli_enabled=False → None."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(gd, "_get_package_metadata", lambda: {"cli_enabled": False})
        assert gd._find_click_cli_obj("mypkg") is None

    def test_click_not_installed_returns_none(self, tmp_path, monkeypatch):
        """ImportError on click → None."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(gd, "_get_package_metadata", lambda: {"cli_enabled": True})

        import sys

        # Temporarily hide click from sys.modules so the function-level import fails
        click_mod = sys.modules.pop("click", None)
        click_testing = sys.modules.pop("click.testing", None)
        # Also hide submodules
        click_keys = [k for k in sys.modules if k.startswith("click")]
        hidden = {k: sys.modules.pop(k) for k in click_keys}
        try:
            with patch("builtins.__import__", side_effect=ImportError("no click")):
                result = gd._find_click_cli_obj("mypkg")
            assert result is None
        finally:
            if click_mod:
                sys.modules["click"] = click_mod
            if click_testing:
                sys.modules["click.testing"] = click_testing
            sys.modules.update(hidden)

    def test_no_cli_module_auto_discovers(self, tmp_path, monkeypatch):
        """auto-discovers CLI module from common names."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(gd, "_get_package_metadata", lambda: {"cli_enabled": True})

        # Make importlib.import_module fail for all candidates
        real_import = importlib.import_module

        def fail_import(name, *args, **kwargs):
            if name in ("mypkg.cli", "mypkg.__main__", "mypkg.main"):
                raise ImportError(f"no module {name}")
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=fail_import):
            result = gd._find_click_cli_obj("mypkg")
        assert result is None

    def test_auto_discovers_module_with_click_obj(self, tmp_path, monkeypatch):
        """finds a module with a Click command."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(gd, "_get_package_metadata", lambda: {"cli_enabled": True})

        # Create a fake module with a click.Command
        fake_mod = types.ModuleType("mypkg.cli")
        fake_cmd = click.Command("test")
        fake_mod.cli = fake_cmd

        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.cli":
                return fake_mod
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=mock_import):
            result = gd._find_click_cli_obj("mypkg")
        assert result is fake_cmd

    def test_explicit_cli_module_import_fails(self, tmp_path, monkeypatch):
        """explicit cli_module can't be imported → None."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(
            gd,
            "_get_package_metadata",
            lambda: {"cli_enabled": True, "cli_module": "mypkg.custom_cli"},
        )

        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.custom_cli":
                raise ImportError("no such module")
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=mock_import):
            result = gd._find_click_cli_obj("mypkg")
        assert result is None

    def test_explicit_cli_name_found(self, tmp_path, monkeypatch):
        """metadata has cli_name and it's found."""
        gd = _make_gd(tmp_path)
        fake_mod = types.ModuleType("mypkg.custom_cli")
        fake_cmd = click.Command("mycmd")
        fake_mod.mycmd = fake_cmd

        monkeypatch.setattr(
            gd,
            "_get_package_metadata",
            lambda: {"cli_enabled": True, "cli_module": "mypkg.custom_cli", "cli_name": "mycmd"},
        )

        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.custom_cli":
                return fake_mod
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=mock_import):
            result = gd._find_click_cli_obj("mypkg")
        assert result is fake_cmd

    def test_common_attr_names_found(self, tmp_path, monkeypatch):
        """finds click obj via common attr names (cli/main/app)."""
        gd = _make_gd(tmp_path)
        fake_mod = types.ModuleType("mypkg.cli_mod")
        fake_group = click.Group("main")
        fake_mod.main = fake_group

        monkeypatch.setattr(
            gd,
            "_get_package_metadata",
            lambda: {"cli_enabled": True, "cli_module": "mypkg.cli_mod"},
        )

        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.cli_mod":
                return fake_mod
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=mock_import):
            result = gd._find_click_cli_obj("mypkg")
        assert result is fake_group

    def test_scan_all_attrs_fallback(self, tmp_path, monkeypatch):
        """scans all module attrs to find click command."""
        gd = _make_gd(tmp_path)
        fake_mod = types.ModuleType("mypkg.cli_mod")
        fake_cmd = click.Command("hidden_cmd")
        # Not named cli/main/app/command/mypkg — will fall through to scan
        fake_mod.my_special_command = fake_cmd

        monkeypatch.setattr(
            gd,
            "_get_package_metadata",
            lambda: {"cli_enabled": True, "cli_module": "mypkg.cli_mod"},
        )

        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.cli_mod":
                return fake_mod
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=mock_import):
            result = gd._find_click_cli_obj("mypkg")
        assert result is fake_cmd

    def test_no_click_obj_found_returns_none(self, tmp_path, monkeypatch):
        """no Click object found at all → None."""
        gd = _make_gd(tmp_path)
        fake_mod = types.ModuleType("mypkg.cli_mod")
        fake_mod.something = "not a click command"

        monkeypatch.setattr(
            gd,
            "_get_package_metadata",
            lambda: {"cli_enabled": True, "cli_module": "mypkg.cli_mod"},
        )

        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.cli_mod":
                return fake_mod
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=mock_import):
            result = gd._find_click_cli_obj("mypkg")
        assert result is None


# ===========================================================================
# _discover_mcp_server
# ===========================================================================


class TestDiscoverMcpServer:
    """Cover the auto-discovery path in _discover_mcp_server."""

    def test_no_mcp_module_all_imports_fail(self, tmp_path, monkeypatch):
        """no module configured, all candidates fail → None."""
        gd = _make_gd(tmp_path)
        # Ensure mcp_module returns None
        monkeypatch.setattr(type(gd._config), "mcp_module", property(lambda self: None))

        real_import = importlib.import_module

        def fail_import(name, *args, **kwargs):
            if name.startswith("mypkg."):
                raise ImportError(f"no {name}")
            return real_import(name, *args, **kwargs)

        with patch("importlib.import_module", side_effect=fail_import):
            result = gd._discover_mcp_server()
        assert result is None

    def test_auto_discovers_mcp_module(self, tmp_path, monkeypatch):
        """finds a candidate MCP module successfully."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(type(gd._config), "mcp_module", property(lambda self: None))

        fake_mcp_mod = types.ModuleType("mypkg.mcp")
        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.mcp":
                return fake_mcp_mod
            if name.startswith("mypkg."):
                raise ImportError(f"no {name}")
            return real_import(name, *args, **kwargs)

        fake_discovery_result = {"name": "test-server", "tools": []}

        with patch("importlib.import_module", side_effect=mock_import):
            with patch(
                "great_docs._mcp_docs.discover_mcp_server",
                return_value=fake_discovery_result,
            ) as mock_discover:
                result = gd._discover_mcp_server()

        assert result == fake_discovery_result
        mock_discover.assert_called_once()


# ===========================================================================
# _update_sidebar_with_mcp
# ===========================================================================


class TestUpdateSidebarWithMcp:
    """Cover _update_sidebar_with_mcp branching."""

    def test_empty_mcp_files_returns_early(self, tmp_path):
        """empty list → return immediately."""
        gd = _make_gd(tmp_path)
        gd.project_path.mkdir(parents=True, exist_ok=True)
        quarto_yml = gd.project_path / "_quarto.yml"
        quarto_yml.write_text("website:\n  sidebar: []\n", encoding="utf-8")
        gd._update_sidebar_with_mcp([])
        # File unchanged
        content = quarto_yml.read_text()
        assert "mcp-reference" not in content

    def test_no_quarto_yml_returns_early(self, tmp_path):
        """no _quarto.yml → return."""
        gd = _make_gd(tmp_path)
        gd.project_path.mkdir(parents=True, exist_ok=True)
        # Don't create _quarto.yml
        gd._update_sidebar_with_mcp(["reference/mcp/tools.qmd"])

    def test_adds_mcp_section_to_sidebar(self, tmp_path, monkeypatch):
        """creates MCP section in sidebar and writes."""
        gd = _make_gd(tmp_path)
        gd.project_path.mkdir(parents=True, exist_ok=True)
        quarto_yml = gd.project_path / "_quarto.yml"
        quarto_yml.write_text(
            "website:\n  sidebar:\n    - id: api-reference\n      contents: []\n",
            encoding="utf-8",
        )

        # Mock _write_quarto_yml to avoid complex YAML formatting
        written = {}

        def fake_write(path, config):
            written["config"] = config

        monkeypatch.setattr(gd, "_write_quarto_yml", fake_write)

        mcp_files = ["reference/mcp/tools.qmd", "reference/mcp/resources.qmd"]
        gd._update_sidebar_with_mcp(mcp_files)

        assert "config" in written
        sidebar = written["config"]["website"]["sidebar"]
        mcp_section = next(s for s in sidebar if s.get("id") == "mcp-reference")
        assert "MCP Reference" in mcp_section["title"]

    def test_updates_existing_mcp_section(self, tmp_path, monkeypatch):
        """existing mcp-reference section gets updated."""
        gd = _make_gd(tmp_path)
        gd.project_path.mkdir(parents=True, exist_ok=True)
        quarto_yml = gd.project_path / "_quarto.yml"
        quarto_yml.write_text(
            "website:\n  sidebar:\n    - id: mcp-reference\n      title: MCP Reference\n      contents:\n        - old.qmd\n",
            encoding="utf-8",
        )

        written = {}

        def fake_write(path, config):
            written["config"] = config

        monkeypatch.setattr(gd, "_write_quarto_yml", fake_write)

        new_files = ["new-tools.qmd"]
        gd._update_sidebar_with_mcp(new_files)

        sidebar = written["config"]["website"]["sidebar"]
        mcp_section = next(s for s in sidebar if s.get("id") == "mcp-reference")
        assert mcp_section["contents"] == new_files

    def test_creates_website_and_sidebar_keys(self, tmp_path, monkeypatch):
        """creates website.sidebar when absent."""
        gd = _make_gd(tmp_path)
        gd.project_path.mkdir(parents=True, exist_ok=True)
        quarto_yml = gd.project_path / "_quarto.yml"
        quarto_yml.write_text("project:\n  type: website\n", encoding="utf-8")

        written = {}

        def fake_write(path, config):
            written["config"] = config

        monkeypatch.setattr(gd, "_write_quarto_yml", fake_write)

        gd._update_sidebar_with_mcp(["tool.qmd"])

        assert "website" in written["config"]
        assert "sidebar" in written["config"]["website"]


# ===========================================================================
# _generate_mcp_manifest
# ===========================================================================


class TestGenerateMcpManifest:
    """Cover _generate_mcp_manifest orchestration."""

    def test_calls_generate_mcp_manifest(self, tmp_path, monkeypatch):
        """Gathers metadata and calls generate_mcp_manifest."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(gd, "_detect_package_name", lambda: "mypkg")
        monkeypatch.setattr(
            gd,
            "_get_github_repo_info",
            lambda: ("posit-dev", "mypkg", "https://github.com/posit-dev/mypkg"),
        )
        # Set site_url in config
        gd._config._config["site_url"] = "https://mypkg.readthedocs.io"

        called_with = {}

        def fake_gen(**kwargs):
            called_with.update(kwargs)

        with patch("great_docs.core.generate_mcp_manifest", create=True):
            monkeypatch.setattr("great_docs._mcp_docs.generate_mcp_manifest", fake_gen)
            gd._generate_mcp_manifest({"name": "test", "tools": []})

        assert called_with["package_name"] == "mypkg"
        assert called_with["repo_url"] == "https://github.com/posit-dev/mypkg"
        assert called_with["site_url"] == "https://mypkg.readthedocs.io"
        assert called_with["server_info"] == {"name": "test", "tools": []}


# ===========================================================================
# _reorder_navbar early return
# ===========================================================================


class TestReorderNavbar:
    """Cover _reorder_navbar edge case."""

    def test_empty_navbar_left_returns_early(self, tmp_path, monkeypatch):
        """Navbar left is empty → return early."""
        gd = _make_gd(tmp_path)
        # Set navbar_order to something non-empty so we pass the first check
        monkeypatch.setattr(
            type(gd._config), "navbar_order", property(lambda self: ["Reference", "API"])
        )
        config = {"website": {"navbar": {"left": []}}}
        gd._reorder_navbar(config)

        # Should not crash and config unchanged
        assert config["website"]["navbar"]["left"] == []
