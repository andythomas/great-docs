# pyright: reportPrivateUsage=false
"""Tests for Typer CLI support (`great_docs._typer_cli` and discovery paths).

Typer vendors its own copy of Click, so a `typer.Typer` app converts to a command whose classes are
*not* instances of the top-level `click` package. These tests exercise the conversion and the
duck-typed introspection helpers, as well as the discovery/snapshot code paths that document a Typer
CLI.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

import click
import pytest

from great_docs import GreatDocs

typer = pytest.importorskip("typer")


def _make_gd(tmp_path: Path) -> GreatDocs:
    (tmp_path / "great-docs.yml").write_text("module: mypkg\n", encoding="utf-8")
    return GreatDocs(project_path=str(tmp_path))


def _sample_app() -> "typer.Typer":
    """A Typer app with two top-level commands and a nested sub-app."""
    app = typer.Typer(help="Root help.")

    @app.command()
    def greet(name: str, count: int = 1, loud: bool = False):
        """Greet NAME."""

    @app.command()
    def version():
        """Show the version."""

    db = typer.Typer(help="Database commands.")
    app.add_typer(db, name="db")

    @db.command()
    def migrate(revision: str = "head"):
        """Run migrations."""

    return app


# ---------------------------------------------------------------------------
# Helpers in _typer_cli
# ---------------------------------------------------------------------------


class TestTyperHelpers:
    def test_is_typer_app_true(self):
        from great_docs._typer_cli import is_typer_app

        assert is_typer_app(typer.Typer()) is True

    def test_is_typer_app_false_for_other_objects(self):
        from great_docs._typer_cli import is_typer_app

        assert is_typer_app(click.Command("x")) is False
        assert is_typer_app("not an app") is False

    def test_to_click_command_converts_typer_app(self):
        from great_docs._typer_cli import is_cli_group, to_click_command

        cmd = to_click_command(_sample_app())

        assert cmd is not None

        # The converted top-level command is a group with the registered commands.
        assert is_cli_group(cmd)
        assert set(cmd.commands) == {"greet", "version", "db"}

    def test_to_click_command_passthrough_for_click(self):
        from great_docs._typer_cli import to_click_command

        c = click.Command("x")

        assert to_click_command(c) is c

        g = click.Group("g")

        assert to_click_command(g) is g

    def test_to_click_command_returns_none_for_non_cli(self):
        from great_docs._typer_cli import to_click_command

        assert to_click_command("nope") is None
        assert to_click_command(object()) is None
        assert to_click_command(None) is None

    def test_is_typer_app_false_when_typer_not_installed(self, monkeypatch):
        """Graceful degradation: no Typer installed -> not a Typer app (no raise)."""
        from great_docs._typer_cli import is_typer_app

        # A None entry in sys.modules makes `import typer` raise ImportError.
        monkeypatch.setitem(sys.modules, "typer", None)

        assert is_typer_app(object()) is False

    def test_to_click_command_returns_none_when_typer_not_installed(self, monkeypatch):
        """A non-Click object cannot be coerced when Typer is unavailable."""
        from great_docs._typer_cli import to_click_command

        monkeypatch.setitem(sys.modules, "typer", None)

        # Click is still importable, so this reaches (and survives) the failed
        # Typer import before returning None.
        assert to_click_command(object()) is None

    def test_is_cli_command(self):
        from great_docs._typer_cli import is_cli_command

        assert is_cli_command(_sample_app()) is True
        assert is_cli_command(click.Command("x")) is True
        assert is_cli_command(42) is False

    def test_is_cli_group_leaf_vs_group(self):
        from great_docs._typer_cli import is_cli_group, to_click_command

        # A single-command Typer app converts to a leaf command (no subcommands).
        leaf_app = typer.Typer()

        @leaf_app.command()
        def only(name: str):
            """Just one command."""

        leaf = to_click_command(leaf_app)

        assert is_cli_group(leaf) is False

        group = to_click_command(_sample_app())

        assert is_cli_group(group) is True

    def test_param_kind_classifies_typer_params(self):
        from great_docs._typer_cli import param_kind, to_click_command

        cmd = to_click_command(_sample_app())
        greet = cmd.commands["greet"]
        kinds = {p.name: param_kind(p) for p in greet.params}

        assert kinds["name"] == "argument"
        assert kinds["count"] == "option"
        assert kinds["loud"] == "option"


# ---------------------------------------------------------------------------
# Discovery + extraction through the GreatDocs API
# ---------------------------------------------------------------------------


class TestTyperDiscovery:
    def _patch_typer_module(self, monkeypatch):
        """Return a fake `mypkg.cli` module exposing a Typer `app`."""
        fake_mod = types.ModuleType("mypkg.cli")
        fake_mod.app = _sample_app()
        real_import = importlib.import_module

        def mock_import(name, *args, **kwargs):
            if name == "mypkg.cli":
                return fake_mod
            return real_import(name, *args, **kwargs)

        return fake_mod, mock_import

    def test_find_click_cli_obj_returns_converted_typer(self, tmp_path, monkeypatch):
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(
            gd,
            "_get_package_metadata",
            lambda: {"cli_enabled": True, "cli_module": "mypkg.cli"},
        )
        _fake, mock_import = self._patch_typer_module(monkeypatch)

        with patch("importlib.import_module", side_effect=mock_import):
            obj = gd._find_click_cli_obj("mypkg")

        assert obj is not None

        # Converted object is introspectable as a Click-style group.
        assert hasattr(obj, "commands")
        assert set(obj.commands) == {"greet", "version", "db"}

    def test_discover_click_cli_extracts_typer_tree(self, tmp_path, monkeypatch):
        gd = _make_gd(tmp_path)
        monkeypatch.setattr(
            gd,
            "_get_package_metadata",
            lambda: {"cli_enabled": True, "cli_module": "mypkg.cli"},
        )
        # No [project.scripts] in the temp project -> falls back to display name.
        monkeypatch.setattr(gd, "_get_cli_entry_point_name", lambda _pkg: "mytool")
        _fake, mock_import = self._patch_typer_module(monkeypatch)

        with patch("importlib.import_module", side_effect=mock_import):
            info = gd._discover_click_cli("mypkg", display_name="mypkg")

        assert info is not None
        assert info["is_group"] is True
        assert info["entry_point_name"] == "mytool"

        names = {c["name"] for c in info["commands"]}

        assert names == {"greet", "version", "db"}

        greet = next(c for c in info["commands"] if c["name"] == "greet")

        assert [a["name"] for a in greet["arguments"]] == ["name"]

        opt_names = {o["name_display"] for o in greet["options"]}

        assert "--count" in opt_names

        # The boolean flag carries no value-type (regression: Typer reports
        # the type name "boolean", which must not leak through as a type). Typer
        # renders a bool option as a `--loud/--no-loud` pair.
        loud = next(o for o in greet["options"] if "--loud" in o["names"])

        assert loud["is_flag"] is True
        assert loud["type"] is None

        # Nested sub-app becomes a nested group with its own subcommands.
        db = next(c for c in info["commands"] if c["name"] == "db")

        assert db["is_group"] is True
        assert [c["name"] for c in db["commands"]] == ["migrate"]


# ---------------------------------------------------------------------------
# API-diff CLI snapshots
# ---------------------------------------------------------------------------


class TestTyperSnapshot:
    def test_snapshot_cli_from_click_accepts_typer_app(self):
        from great_docs._api_diff import snapshot_cli_from_click

        snap = snapshot_cli_from_click(_sample_app())

        assert snap is not None
        assert snap.is_group is True

        sub_names = {c.name for c in snap.subcommands}

        assert sub_names == {"greet", "version", "db"}

        db = next(c for c in snap.subcommands if c.name == "db")

        assert db.is_group is True
        assert {c.name for c in db.subcommands} == {"migrate"}

    def test_snapshot_cli_from_click_rejects_non_cli(self):
        from great_docs._api_diff import snapshot_cli_from_click

        assert snapshot_cli_from_click("not a cli") is None
