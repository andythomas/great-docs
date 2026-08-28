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


# ===========================================================================
# _remove_mcp_from_ref_sections
# ===========================================================================


class TestRemoveMcpFromRefSections:
    """Cover _remove_mcp_from_ref_sections branching."""

    def test_no_quarto_yml_returns_early(self, tmp_path):
        """No _quarto.yml file → immediate return."""
        gd = _make_gd(tmp_path)
        gd.project_path = tmp_path / "subdir"
        gd.project_path.mkdir()
        gd._remove_mcp_from_ref_sections()

    def test_no_ref_sections_script_no_update(self, tmp_path, monkeypatch):
        """include-in-header has no data-gd-ref-sections → no write."""
        gd = _make_gd(tmp_path)
        gd.project_path = tmp_path
        quarto_yml = tmp_path / "_quarto.yml"
        quarto_yml.write_text(
            "format:\n  html:\n    include-in-header:\n      - text: 'unrelated'\n",
            encoding="utf-8",
        )
        written = []
        monkeypatch.setattr(gd, "_write_quarto_yml", lambda p, c: written.append(c))
        gd._remove_mcp_from_ref_sections()
        assert written == []

    def test_removes_mcp_from_multi_section_list(self, tmp_path, monkeypatch):
        """Sections 'api,cli,mcp' → 'api,cli', script kept."""
        gd = _make_gd(tmp_path)
        gd.project_path = tmp_path
        quarto_yml = tmp_path / "_quarto.yml"
        script_text = (
            "<script>document.body.setAttribute('data-gd-ref-sections','api,cli,mcp')</script>"
        )
        quarto_yml.write_text(
            f'format:\n  html:\n    include-in-header:\n      - text: "{script_text}"\n'
            f"    include-after-body:\n      - text: 'other.js'\n",
            encoding="utf-8",
        )
        written = []
        monkeypatch.setattr(gd, "_write_quarto_yml", lambda p, c: written.append(c))
        gd._remove_mcp_from_ref_sections()
        assert len(written) == 1
        header_items = written[0]["format"]["html"]["include-in-header"]
        assert "api,cli" in header_items[0]["text"]
        assert "mcp" not in header_items[0]["text"]

    def test_removes_script_entirely_when_only_api_remains(self, tmp_path, monkeypatch):
        """Sections 'api,mcp' → only 'api' remains → script removed entirely."""
        gd = _make_gd(tmp_path)
        gd.project_path = tmp_path
        quarto_yml = tmp_path / "_quarto.yml"
        ref_script = "<script>document.body.setAttribute('data-gd-ref-sections','api,mcp')</script>"
        switcher_script = "<script src='reference-switcher.js'></script>"
        quarto_yml.write_text(
            f'format:\n  html:\n    include-in-header:\n      - text: "{ref_script}"\n'
            f'    include-after-body:\n      - text: "{switcher_script}"\n',
            encoding="utf-8",
        )
        written = []
        monkeypatch.setattr(gd, "_write_quarto_yml", lambda p, c: written.append(c))
        gd._remove_mcp_from_ref_sections()
        assert len(written) == 1
        header_items = written[0]["format"]["html"]["include-in-header"]
        assert len(header_items) == 0
        after_body = written[0]["format"]["html"]["include-after-body"]
        assert all("reference-switcher" not in e.get("text", "") for e in after_body)


# ===========================================================================
# _discover_package_exports – griffe export validation
# ===========================================================================


class TestDiscoverPackageExportsValidation:
    """Cover the griffe export validation block inside _discover_package_exports."""

    def _setup(self, tmp_path, monkeypatch):
        """Set up a GreatDocs instance with mocked griffe package."""
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(gd, "_get_package_metadata", lambda: {})
        return gd

    def _make_mock_pkg(self, members_dict, exports=None):
        """Build a mock griffe package with controlled members."""
        pkg = MagicMock()
        pkg.members = members_dict
        pkg.exports = exports
        return pkg

    def test_not_found_in_pkg_members(self, tmp_path, monkeypatch):
        """Name not in pkg.members → 'not found' and excluded from safe_exports."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)
        good_obj = MagicMock()
        good_obj.kind.value = "function"
        good_obj.members = {}
        good_obj.is_alias = False
        pkg = self._make_mock_pkg(
            {"good_func": good_obj},
            exports=["good_func", "MissingClass"],
        )
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert "good_func" in result
        assert "MissingClass" not in result

    def test_cyclic_alias_on_kind(self, tmp_path, monkeypatch):
        """CyclicAliasError on obj.kind → excluded."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        type(obj).kind = property(
            lambda s: (_ for _ in ()).throw(griffe.CyclicAliasError(["x", "y"]))
        )
        pkg = self._make_mock_pkg({"BadAlias": obj}, exports=["BadAlias"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_alias_resolution_error_on_kind(self, tmp_path, monkeypatch):
        """AliasResolutionError on obj.kind → excluded."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        type(obj).kind = property(
            lambda s: (_ for _ in ()).throw(griffe.AliasResolutionError(MagicMock()))
        )
        pkg = self._make_mock_pkg({"Unresolvable": obj}, exports=["Unresolvable"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_key_error_on_kind(self, tmp_path, monkeypatch):
        """KeyError on obj.kind → 'not found (likely Rust/PyO3)'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        type(obj).kind = property(lambda s: (_ for _ in ()).throw(KeyError("missing")))
        pkg = self._make_mock_pkg({"RustObj": obj}, exports=["RustObj"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_generic_exception_on_kind(self, tmp_path, monkeypatch):
        """Generic Exception on obj.kind → excluded with type name."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        type(obj).kind = property(lambda s: (_ for _ in ()).throw(RuntimeError("oops")))
        pkg = self._make_mock_pkg({"Broken": obj}, exports=["Broken"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_module_kind_passes_without_members_check(self, tmp_path, monkeypatch):
        """Module kind passes directly to safe_exports (no .members access)."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "module"
        obj.is_alias = False
        pkg = self._make_mock_pkg({"submod": obj}, exports=["submod"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert "submod" in result

    def test_cyclic_alias_on_members_access(self, tmp_path, monkeypatch):
        """CyclicAliasError accessing .members → excluded."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "class"
        type(obj).members = property(
            lambda s: (_ for _ in ()).throw(griffe.CyclicAliasError(["x", "y"]))
        )
        pkg = self._make_mock_pkg({"CyclicClass": obj}, exports=["CyclicClass"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_alias_resolution_error_on_members_access(self, tmp_path, monkeypatch):
        """AliasResolutionError accessing .members → excluded."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "class"
        type(obj).members = property(
            lambda s: (_ for _ in ()).throw(griffe.AliasResolutionError(MagicMock()))
        )
        pkg = self._make_mock_pkg({"Unresolvable": obj}, exports=["Unresolvable"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_generic_exception_on_members_access(self, tmp_path, monkeypatch):
        """Generic Exception accessing .members → excluded."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "class"
        type(obj).members = property(lambda s: (_ for _ in ()).throw(TypeError("bad")))
        pkg = self._make_mock_pkg({"BadClass": obj}, exports=["BadClass"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_external_re_export_excluded(self, tmp_path, monkeypatch):
        """Alias pointing to external package → excluded as 're-export'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "class"
        obj.members = {}
        obj.is_alias = True
        obj.canonical_path = "other_package.SomeClass"
        pkg = self._make_mock_pkg({"SomeClass": obj}, exports=["SomeClass"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert result == []

    def test_internal_alias_passes(self, tmp_path, monkeypatch):
        """Alias pointing inside the package → passes."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "class"
        obj.members = {}
        obj.is_alias = True
        obj.canonical_path = "mypkg.internal.MyClass"
        pkg = self._make_mock_pkg({"MyClass": obj}, exports=["MyClass"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert "MyClass" in result

    def test_canonical_path_raises_still_passes(self, tmp_path, monkeypatch):
        """Exception on canonical_path → alias passes (doesn't exclude)."""
        gd = self._setup(tmp_path, monkeypatch)

        class _FakeAlias:
            class kind:
                value = "function"

            members = {}
            is_alias = True

            @property
            def canonical_path(self):
                raise AttributeError("oops")

        obj = _FakeAlias()
        pkg = self._make_mock_pkg({"myfn": obj}, exports=["myfn"])
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._discover_package_exports("mypkg")
        assert "myfn" in result


# ===========================================================================
# _categorize_referenced_objects
# ===========================================================================


class TestCategorizeReferencedObjects:
    """Cover _categorize_referenced_objects classification logic."""

    def _setup(self, tmp_path, monkeypatch):
        gd = _make_gd(tmp_path)
        return gd

    def test_griffe_load_fails_returns_empty(self, tmp_path, monkeypatch):
        """Exception from _get_griffe_package → empty categories."""
        gd = self._setup(tmp_path, monkeypatch)
        monkeypatch.setattr(
            gd, "_get_griffe_package", lambda name: (_ for _ in ()).throw(RuntimeError("fail"))
        )
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["Foo"]}])
        assert result["classes"] == []
        assert result["functions"] == []

    def test_non_dict_section_skipped(self, tmp_path, monkeypatch):
        """Non-dict entries in reference_config are skipped (line 8920)."""
        gd = self._setup(tmp_path, monkeypatch)
        pkg = MagicMock()
        pkg.members = {}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", ["not_a_dict", {"contents": []}])
        assert result["other"] == []

    def test_classifies_function(self, tmp_path, monkeypatch):
        """Function kind → categorized into 'functions'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "function"
        obj.labels = set()
        pkg = MagicMock()
        pkg.members = {"my_func": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_function", lambda o: "function")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["my_func"]}])
        assert "my_func" in result["functions"]

    def test_classifies_async_function(self, tmp_path, monkeypatch):
        """Async function → categorized into 'async_functions'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "function"
        obj.labels = {"async"}
        pkg = MagicMock()
        pkg.members = {"afunc": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_function", lambda o: "async")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["afunc"]}])
        assert "afunc" in result["async_functions"]

    def test_classifies_class_as_dataclass(self, tmp_path, monkeypatch):
        """Class sub-classified as dataclass → 'dataclasses'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "class"
        obj.members = {"__init__": MagicMock()}
        obj.members["__init__"].kind.value = "function"
        pkg = MagicMock()
        pkg.members = {"MyDC": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "dataclass")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyDC"]}])
        assert "MyDC" in result["dataclasses"]

    def test_classifies_attribute_as_constant(self, tmp_path, monkeypatch):
        """Attribute kind → 'constants'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "attribute"
        obj.labels = set()
        obj.annotation = None
        pkg = MagicMock()
        pkg.members = {"MY_CONST": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_attribute", lambda o: "constant")
        monkeypatch.setattr(gd, "_extract_constant_metadata", lambda o, n, c: None)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MY_CONST"]}])
        assert "MY_CONST" in result["constants"]

    def test_classifies_type_alias(self, tmp_path, monkeypatch):
        """Type alias attribute → 'type_aliases'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        obj.kind.value = "type alias"
        obj.labels = set()
        pkg = MagicMock()
        pkg.members = {"MyAlias": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_attribute", lambda o: "type_alias")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyAlias"]}])
        assert "MyAlias" in result["type_aliases"]

    def test_cyclic_alias_on_kind_goes_to_other(self, tmp_path, monkeypatch):
        """CyclicAliasError on obj.kind → goes to 'other'."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        type(obj).kind = property(
            lambda s: (_ for _ in ()).throw(griffe.CyclicAliasError(["x", "y"]))
        )
        pkg = MagicMock()
        pkg.members = {"CyclicThing": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["CyclicThing"]}])
        assert "CyclicThing" in result["other"]

    def test_generic_exception_on_kind_goes_to_other(self, tmp_path, monkeypatch):
        """Generic Exception on obj.kind → goes to 'other'."""
        gd = self._setup(tmp_path, monkeypatch)
        obj = MagicMock()
        type(obj).kind = property(lambda s: (_ for _ in ()).throw(ValueError("bad")))
        pkg = MagicMock()
        pkg.members = {"BrokenObj": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["BrokenObj"]}])
        assert "BrokenObj" in result["other"]

    def test_missing_name_with_installed_package_raises(self, tmp_path, monkeypatch):
        """Missing name + installed package → SystemExit."""
        import pytest

        gd = self._setup(tmp_path, monkeypatch)
        pkg = MagicMock()
        pkg.members = {}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr("importlib.metadata.version", lambda name: "1.2.3")
        with pytest.raises(SystemExit, match="not found"):
            gd._categorize_referenced_objects("mypkg", [{"contents": ["Missing"]}])

    def test_missing_name_uninstalled_package_goes_to_other(self, tmp_path, monkeypatch):
        """Missing name + uninstalled package → falls to 'other'."""
        gd = self._setup(tmp_path, monkeypatch)
        pkg = MagicMock()
        pkg.members = {}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(
            "importlib.metadata.version",
            lambda name: (_ for _ in ()).throw(Exception("not installed")),
        )
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["Missing"]}])
        assert "Missing" in result["other"]

    def test_class_method_counting(self, tmp_path, monkeypatch):
        """Class with public methods → class_methods count populated."""
        gd = self._setup(tmp_path, monkeypatch)

        method_obj = MagicMock()
        method_obj.kind.value = "function"

        private_obj = MagicMock()
        private_obj.kind.value = "function"

        prop_obj = MagicMock()
        prop_obj.kind.value = "attribute"
        prop_obj.labels = {"property"}

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {
            "do_stuff": method_obj,
            "_private": private_obj,
            "value": prop_obj,
        }

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass"]}])
        assert result["class_methods"]["MyClass"] == 2
        assert "do_stuff" in result["class_method_names"]["MyClass"]
        assert "value" in result["class_method_names"]["MyClass"]
        assert "_private" not in result["class_method_names"]["MyClass"]

    def test_class_member_cyclic_alias_skipped(self, tmp_path, monkeypatch):
        """CyclicAliasError on member.kind → member skipped."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)

        bad_member = MagicMock()
        type(bad_member).kind = property(
            lambda s: (_ for _ in ()).throw(griffe.CyclicAliasError(["x", "y"]))
        )

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"bad_member": bad_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass"]}])
        assert result["class_methods"]["MyClass"] == 0

    def test_class_member_generic_exception_skipped(self, tmp_path, monkeypatch):
        """Generic Exception on member.kind → member skipped."""
        gd = self._setup(tmp_path, monkeypatch)

        bad_member = MagicMock()
        type(bad_member).kind = property(lambda s: (_ for _ in ()).throw(TypeError("oops")))

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"broken": bad_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass"]}])
        assert result["class_methods"]["MyClass"] == 0

    def test_module_kind_expands_members(self, tmp_path, monkeypatch):
        """Module kind → expands members into qualified names."""
        gd = self._setup(tmp_path, monkeypatch)

        sub_class = MagicMock()
        sub_class.kind.value = "class"
        sub_func = MagicMock()
        sub_func.kind.value = "function"
        sub_attr = MagicMock()
        sub_attr.kind.value = "attribute"

        mod_obj = MagicMock()
        mod_obj.kind.value = "module"
        mod_obj.members = {
            "SubClass": sub_class,
            "sub_func": sub_func,
            "CONST": sub_attr,
            "_private": MagicMock(),
        }

        # A class must be processed before the module so _CLASS_SUB_MAP is defined
        anchor_cls = MagicMock()
        anchor_cls.kind.value = "class"
        anchor_cls.members = {}
        anchor_cls.labels = set()
        anchor_cls.bases = []

        pkg = MagicMock()
        pkg.members = {"AClass": anchor_cls, "mymod": mod_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["AClass", "mymod"]}])
        assert "mymod.SubClass" in result["classes"]
        assert "mymod.sub_func" in result["functions"]
        assert "mymod.CONST" in result["constants"]

    def test_module_member_cyclic_alias_skipped(self, tmp_path, monkeypatch):
        """CyclicAliasError on module member's kind → skipped."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)

        bad_member = MagicMock()
        type(bad_member).kind = property(
            lambda s: (_ for _ in ()).throw(griffe.CyclicAliasError(["x", "y"]))
        )

        mod_obj = MagicMock()
        mod_obj.kind.value = "module"
        mod_obj.members = {"broken": bad_member}

        pkg = MagicMock()
        pkg.members = {"mymod": mod_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["mymod"]}])
        assert "mymod.broken" not in result.get("other", [])

    def test_module_members_iteration_raises(self, tmp_path, monkeypatch):
        """Exception iterating module.members → outer except passes."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)

        mod_obj = MagicMock()
        mod_obj.kind.value = "module"
        type(mod_obj).members = property(
            lambda s: (_ for _ in ()).throw(griffe.CyclicAliasError(["x", "y"]))
        )

        pkg = MagicMock()
        pkg.members = {"mymod": mod_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["mymod"]}])
        assert "mymod" not in result.get("classes", [])

    def test_qualified_method_ref_classifies_method(self, tmp_path, monkeypatch):
        """'ClassName.method_name' → classified as method."""
        gd = self._setup(tmp_path, monkeypatch)

        method_member = MagicMock()
        method_member.kind.value = "function"
        method_member.labels = set()

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"do_thing": method_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        monkeypatch.setattr(gd, "_sub_classify_function", lambda o: "function")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.do_thing"]}])
        assert result["class_member_types"]["MyClass.do_thing"] == "method"

    def test_qualified_method_ref_classmethod(self, tmp_path, monkeypatch):
        """'ClassName.cls_method' → classified as classmethod."""
        gd = self._setup(tmp_path, monkeypatch)

        method_member = MagicMock()
        method_member.kind.value = "function"
        method_member.labels = {"classmethod"}

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"from_config": method_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        monkeypatch.setattr(gd, "_sub_classify_function", lambda o: "classmethod")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.from_config"]}])
        assert result["class_member_types"]["MyClass.from_config"] == "classmethod"

    def test_qualified_method_ref_attribute_property(self, tmp_path, monkeypatch):
        """'ClassName.prop' with attribute kind + property label → 'property'."""
        gd = self._setup(tmp_path, monkeypatch)

        attr_member = MagicMock()
        attr_member.kind.value = "attribute"
        attr_member.labels = {"property"}

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"name": attr_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.name"]}])
        assert result["class_member_types"]["MyClass.name"] == "property"

    def test_qualified_method_ref_attribute_non_property(self, tmp_path, monkeypatch):
        """'ClassName.field' with attribute kind + no property label → 'attribute'."""
        gd = self._setup(tmp_path, monkeypatch)

        attr_member = MagicMock()
        attr_member.kind.value = "attribute"
        attr_member.labels = set()

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"field": attr_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.field"]}])
        assert result["class_member_types"]["MyClass.field"] == "attribute"

    def test_qualified_method_ref_unknown_kind_defaults_method(self, tmp_path, monkeypatch):
        """'ClassName.thing' with unexpected kind → 'method'."""
        gd = self._setup(tmp_path, monkeypatch)

        weird_member = MagicMock()
        weird_member.kind.value = "module"

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"thing": weird_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.thing"]}])
        assert result["class_member_types"]["MyClass.thing"] == "method"

    def test_qualified_method_ref_cyclic_alias_defaults_method(self, tmp_path, monkeypatch):
        """CyclicAliasError resolving method → defaults to 'method'."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)

        bad_member = MagicMock()
        type(bad_member).kind = property(
            lambda s: (_ for _ in ()).throw(griffe.CyclicAliasError(["x", "y"]))
        )

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"broken": bad_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.broken"]}])
        assert result["class_member_types"]["MyClass.broken"] == "method"

    def test_qualified_method_ref_generic_exception_defaults_method(self, tmp_path, monkeypatch):
        """Generic Exception resolving method → defaults to 'method'."""
        gd = self._setup(tmp_path, monkeypatch)

        bad_member = MagicMock()
        type(bad_member).kind = property(lambda s: (_ for _ in ()).throw(RuntimeError("fail")))

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"broken": bad_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.broken"]}])
        assert result["class_member_types"]["MyClass.broken"] == "method"

    def test_qualified_method_not_in_class_members(self, tmp_path, monkeypatch):
        """Method name not in class.members → defaults to 'method'."""
        gd = self._setup(tmp_path, monkeypatch)

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects(
            "mypkg", [{"contents": ["MyClass.missing_method"]}]
        )
        assert result["class_member_types"]["MyClass.missing_method"] == "method"

    def test_qualified_method_class_not_in_pkg(self, tmp_path, monkeypatch):
        """Class not in pkg.members → method ref skipped."""
        gd = self._setup(tmp_path, monkeypatch)

        pkg = MagicMock()
        pkg.members = {}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["Ghost.method"]}])
        assert "Ghost.method" not in result.get("class_member_types", {})

    def test_qualified_method_class_not_actually_class(self, tmp_path, monkeypatch):
        """Class name resolves to non-class → skipped."""
        gd = self._setup(tmp_path, monkeypatch)

        not_a_class = MagicMock()
        not_a_class.kind.value = "function"

        pkg = MagicMock()
        pkg.members = {"NotClass": not_a_class}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["NotClass.method"]}])
        assert "NotClass.method" not in result.get("class_member_types", {})

    def test_qualified_method_class_kind_raises(self, tmp_path, monkeypatch):
        """Exception checking class kind → skipped."""
        gd = self._setup(tmp_path, monkeypatch)

        bad_obj = MagicMock()
        type(bad_obj).kind = property(lambda s: (_ for _ in ()).throw(RuntimeError("fail")))

        pkg = MagicMock()
        pkg.members = {"Bad": bad_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["Bad.method"]}])
        assert "Bad.method" not in result.get("class_member_types", {})

    def test_attribute_labels_raises_defaults_to_set(self, tmp_path, monkeypatch):
        """Exception accessing member.labels → defaults to empty set."""
        gd = self._setup(tmp_path, monkeypatch)

        class _FakeMemberBadLabels:
            class kind:
                value = "attribute"

            @property
            def labels(self):
                raise AttributeError("no labels")

        attr_member = _FakeMemberBadLabels()

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"broken_attr": attr_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass.broken_attr"]}])
        assert result["class_member_types"]["MyClass.broken_attr"] == "attribute"

    def test_dict_item_in_contents(self, tmp_path, monkeypatch):
        """Dict item with 'name' key in contents is recognized."""
        gd = self._setup(tmp_path, monkeypatch)

        obj = MagicMock()
        obj.kind.value = "function"
        obj.labels = set()

        pkg = MagicMock()
        pkg.members = {"named_func": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_function", lambda o: "function")
        result = gd._categorize_referenced_objects(
            "mypkg", [{"contents": [{"name": "named_func"}]}]
        )
        assert "named_func" in result["functions"]

    def test_class_property_member_counted(self, tmp_path, monkeypatch):
        """@property attribute counted as method."""
        gd = self._setup(tmp_path, monkeypatch)

        prop_member = MagicMock()
        prop_member.kind.value = "attribute"
        prop_member.labels = {"property"}

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"name": prop_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass"]}])
        assert result["class_methods"]["MyClass"] == 1
        assert "name" in result["class_method_names"]["MyClass"]

    def test_class_init_dunder_skipped(self, tmp_path, monkeypatch):
        """__init__ dunder is skipped in method count."""
        gd = self._setup(tmp_path, monkeypatch)

        init_member = MagicMock()
        init_member.kind.value = "function"

        public_method = MagicMock()
        public_method.kind.value = "function"

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"__init__": init_member, "run": public_method}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass"]}])
        assert result["class_methods"]["MyClass"] == 1
        assert "run" in result["class_method_names"]["MyClass"]
        assert "__init__" not in result["class_method_names"]["MyClass"]

    def test_class_property_labels_raises(self, tmp_path, monkeypatch):
        """Exception accessing member.labels for property check → passes."""
        gd = self._setup(tmp_path, monkeypatch)

        attr_member = MagicMock()
        attr_member.kind.value = "attribute"
        type(attr_member).labels = property(
            lambda s: (_ for _ in ()).throw(RuntimeError("no labels"))
        )

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = {"prop": attr_member}

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass"]}])
        assert result["class_methods"]["MyClass"] == 0

    def test_class_members_outer_cyclic_alias(self, tmp_path, monkeypatch):
        """CyclicAliasError iterating class members → outer except."""
        import griffe

        gd = self._setup(tmp_path, monkeypatch)

        class _BadItems(dict):
            def items(self):
                raise griffe.CyclicAliasError(["x", "y"])

        cls_obj = MagicMock()
        cls_obj.kind.value = "class"
        cls_obj.members = _BadItems()

        pkg = MagicMock()
        pkg.members = {"MyClass": cls_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["MyClass"]}])
        assert result["class_methods"]["MyClass"] == 0

    def test_typevar_attribute(self, tmp_path, monkeypatch):
        """TypeVar attribute → type_aliases."""
        gd = self._setup(tmp_path, monkeypatch)

        obj = MagicMock()
        obj.kind.value = "attribute"
        obj.labels = set()

        pkg = MagicMock()
        pkg.members = {"T": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_attribute", lambda o: "typevar")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["T"]}])
        assert "T" in result["type_aliases"]

    def test_module_member_generic_exception_skipped(self, tmp_path, monkeypatch):
        """Generic Exception on module member's kind → skipped."""
        gd = self._setup(tmp_path, monkeypatch)

        bad_member = MagicMock()
        type(bad_member).kind = property(lambda s: (_ for _ in ()).throw(ValueError("bad")))

        # Need a class processed first to define _CLASS_SUB_MAP
        anchor = MagicMock()
        anchor.kind.value = "class"
        anchor.members = {}

        mod_obj = MagicMock()
        mod_obj.kind.value = "module"
        mod_obj.members = {"broken": bad_member}

        pkg = MagicMock()
        pkg.members = {"AClass": anchor, "mymod": mod_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["AClass", "mymod"]}])
        assert "mymod.broken" not in result.get("functions", [])

    def test_module_members_outer_exception(self, tmp_path, monkeypatch):
        """Generic Exception iterating module members → outer except."""
        gd = self._setup(tmp_path, monkeypatch)

        class _BadItems(dict):
            def items(self):
                raise TypeError("bad iteration")

        # Need a class processed first to define _CLASS_SUB_MAP
        anchor = MagicMock()
        anchor.kind.value = "class"
        anchor.members = {}

        mod_obj = MagicMock()
        mod_obj.kind.value = "module"
        mod_obj.members = _BadItems()

        pkg = MagicMock()
        pkg.members = {"AClass": anchor, "mymod": mod_obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["AClass", "mymod"]}])
        assert "mymod" not in result.get("classes", [])

    def test_other_kind_goes_to_other(self, tmp_path, monkeypatch):
        """Unknown kind value → goes to 'other'."""
        gd = self._setup(tmp_path, monkeypatch)

        # Need a class processed first for _CLASS_SUB_MAP
        anchor = MagicMock()
        anchor.kind.value = "class"
        anchor.members = {}

        obj = MagicMock()
        obj.kind.value = "alias"

        pkg = MagicMock()
        pkg.members = {"AClass": anchor, "weird": obj}
        monkeypatch.setattr(gd, "_get_griffe_package", lambda name: pkg)
        monkeypatch.setattr(gd, "_sub_classify_class", lambda o: "class")
        result = gd._categorize_referenced_objects("mypkg", [{"contents": ["AClass", "weird"]}])

        assert "weird" in result["other"]
