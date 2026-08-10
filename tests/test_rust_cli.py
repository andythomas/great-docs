# pyright: reportPrivateUsage=false
"""Tests for Rust CLI project detection and introspection.

Local fixtures in ``tests/fixtures/`` are used exclusively (no external repository clones are
required). Tests that actually compile Rust code are skipped automatically when the ``cargo``
compiler is not on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from great_docs._rust_cli import (
    RustCliProject,
    _find_binary_targets,
    _parse_clap_flag,
    _parse_clap_help,
    _parse_package_name,
    _short_help,
    _uses_clap,
    build_rust_binary,
    detect_rust_cli_project,
    introspect_rust_cli,
)
from great_docs.core import GreatDocs

# ---------------------------------------------------------------------------
# Paths to committed fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# rust_cli_hello: stdlib-only buildable CLI (src/main.rs, no external deps)
HELLO_FIXTURE = FIXTURES_DIR / "rust_cli_hello"

# rust_cli_clap: Cargo.toml only — declares clap, used for static _uses_clap tests
CLAP_FIXTURE = FIXTURES_DIR / "rust_cli_clap"

CARGO_AVAILABLE = shutil.which("cargo") is not None

requires_cargo = pytest.mark.skipif(not CARGO_AVAILABLE, reason="cargo not available")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rust_project(
    tmp_path: Path, cargo_toml: str = "", extra_files: dict[str, str] | None = None
) -> Path:
    """Write a minimal Rust project layout to *tmp_path*."""
    if not cargo_toml:
        cargo_toml = '[package]\nname = "myapp"\nversion = "0.1.0"\nedition = "2021"\n'
    (tmp_path / "Cargo.toml").write_text(cargo_toml, encoding="utf-8")
    for rel, content in (extra_files or {}).items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# _parse_package_name
# ---------------------------------------------------------------------------


class TestParsePackageName:
    def test_standard_package(self):
        cargo = '[package]\nname = "my-app"\nversion = "0.1.0"\n'
        assert _parse_package_name(cargo) == "my-app"

    def test_no_package_section(self):
        cargo = '[dependencies]\nclap = "4.5"\n'
        assert _parse_package_name(cargo) is None

    def test_package_name_with_underscores(self):
        cargo = '[package]\nname = "my_app"\n'
        assert _parse_package_name(cargo) == "my_app"

    def test_name_in_wrong_section_ignored(self):
        cargo = '[dependencies]\nname = "not-this"\n\n[package]\nname = "correct"\n'
        assert _parse_package_name(cargo) == "correct"

    def test_hello_fixture(self):
        text = (HELLO_FIXTURE / "Cargo.toml").read_text(encoding="utf-8")
        assert _parse_package_name(text) == "hello"

    def test_clap_fixture(self):
        text = (CLAP_FIXTURE / "Cargo.toml").read_text(encoding="utf-8")
        assert _parse_package_name(text) == "clap-example"


# ---------------------------------------------------------------------------
# _find_binary_targets
# ---------------------------------------------------------------------------


class TestFindBinaryTargets:
    def test_src_main_rs_layout(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.rs").write_text("fn main() {}\n")
        result = _find_binary_targets(tmp_path, '[package]\nname = "app"\n', "app")
        assert result == ["app"]

    def test_explicit_bin_section(self, tmp_path: Path):
        cargo = '[package]\nname = "app"\n\n[[bin]]\nname = "mycli"\npath = "src/cli.rs"\n'
        result = _find_binary_targets(tmp_path, cargo, "app")
        assert result == ["mycli"]

    def test_multiple_bin_sections(self, tmp_path: Path):
        cargo = (
            '[package]\nname = "app"\n\n'
            '[[bin]]\nname = "cli-a"\n\n'
            '[[bin]]\nname = "cli-b"\n'
        )
        result = _find_binary_targets(tmp_path, cargo, "app")
        assert result == ["cli-a", "cli-b"]

    def test_no_main_no_bin_returns_empty(self, tmp_path: Path):
        result = _find_binary_targets(tmp_path, '[package]\nname = "lib"\n', "lib")
        assert result == []

    def test_hello_fixture(self):
        text = (HELLO_FIXTURE / "Cargo.toml").read_text(encoding="utf-8")
        result = _find_binary_targets(HELLO_FIXTURE, text, "hello")
        assert result == ["hello"]


# ---------------------------------------------------------------------------
# _uses_clap
# ---------------------------------------------------------------------------


class TestUsesClap:
    def test_detects_clap(self):
        cargo = '[dependencies]\nclap = { version = "4.5", features = ["derive"] }\n'
        assert _uses_clap(cargo) is True

    def test_no_clap(self):
        cargo = "[dependencies]\nserde = \"1.0\"\n"
        assert _uses_clap(cargo) is False

    def test_clap_fixture_detected(self):
        text = (CLAP_FIXTURE / "Cargo.toml").read_text(encoding="utf-8")
        assert _uses_clap(text) is True

    def test_hello_fixture_has_no_clap(self):
        text = (HELLO_FIXTURE / "Cargo.toml").read_text(encoding="utf-8")
        assert _uses_clap(text) is False


# ---------------------------------------------------------------------------
# detect_rust_cli_project
# ---------------------------------------------------------------------------


class TestDetectRustCliProject:
    def test_returns_none_for_python_project(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mypkg'\n")
        assert detect_rust_cli_project(tmp_path) is None

    def test_returns_none_for_empty_dir(self, tmp_path: Path):
        assert detect_rust_cli_project(tmp_path) is None

    def test_returns_none_when_no_binary(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "mylib"\nversion = "0.1.0"\n\n[lib]\nname = "mylib"\n'
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text("pub fn hello() {}\n")
        assert detect_rust_cli_project(tmp_path) is None

    def test_detects_src_main_layout(self, tmp_path: Path):
        _make_rust_project(tmp_path, extra_files={"src/main.rs": "fn main() {}\n"})
        result = detect_rust_cli_project(tmp_path)
        assert result is not None
        assert result.binary_names == ["myapp"]
        assert result.package_name == "myapp"

    def test_detects_explicit_bin(self, tmp_path: Path):
        cargo = (
            '[package]\nname = "app"\nversion = "0.1.0"\n\n'
            '[[bin]]\nname = "mycli"\npath = "src/cli.rs"\n'
        )
        _make_rust_project(tmp_path, cargo_toml=cargo)
        result = detect_rust_cli_project(tmp_path)
        assert result is not None
        assert result.binary_names == ["mycli"]

    def test_uses_clap_flag_propagated(self, tmp_path: Path):
        cargo = (
            '[package]\nname = "app"\nversion = "0.1.0"\n\n'
            '[dependencies]\nclap = "4.5"\n'
        )
        _make_rust_project(tmp_path, cargo_toml=cargo, extra_files={"src/main.rs": "fn main() {}\n"})
        result = detect_rust_cli_project(tmp_path)
        assert result is not None
        assert result.uses_clap is True

    def test_hello_fixture_detection(self):
        result = detect_rust_cli_project(HELLO_FIXTURE)
        assert result is not None
        assert result.package_name == "hello"
        assert result.binary_names == ["hello"]
        assert result.uses_clap is False
        assert result.project_root == HELLO_FIXTURE

    def test_clap_fixture_not_a_cli(self):
        """rust_cli_clap has no src/main.rs, so it should not be detected as a CLI."""
        result = detect_rust_cli_project(CLAP_FIXTURE)
        assert result is None


# ---------------------------------------------------------------------------
# GreatDocs._detect_rust_cli_project and _find_package_root
# ---------------------------------------------------------------------------


class TestGreatDocsRustIntegration:
    def test_detect_rust_cli_project_on_hello_fixture(self):
        gd = GreatDocs(project_path=str(HELLO_FIXTURE))
        result = gd._detect_rust_cli_project()
        assert result is not None
        assert isinstance(result, RustCliProject)
        assert result.package_name == "hello"

    def test_detect_rust_cli_project_on_python_project(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mypkg'\n")
        gd = GreatDocs(project_path=str(tmp_path))
        assert gd._detect_rust_cli_project() is None

    def test_find_package_root_recognizes_cargo_toml(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "app"\nversion = "0.1.0"\n')
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.rs").write_text("fn main() {}\n")
        gd = GreatDocs(project_path=str(tmp_path))
        assert gd._find_package_root() == tmp_path

    def test_find_package_root_on_hello_fixture(self):
        gd = GreatDocs(project_path=str(HELLO_FIXTURE))
        assert gd._find_package_root() == HELLO_FIXTURE


# ---------------------------------------------------------------------------
# _parse_clap_flag
# ---------------------------------------------------------------------------


class TestParseClapFlag:
    def test_long_only_boolean(self):
        opt = _parse_clap_flag("      --verbose        Enable verbose output")
        assert opt is not None
        assert opt["names"] == ["--verbose"]
        assert opt["is_flag"] is True
        assert opt["type"] is None
        assert "verbose" in opt["help"]

    def test_short_and_long_boolean(self):
        opt = _parse_clap_flag("  -v, --verbose        Enable verbose output")
        assert opt is not None
        assert opt["names"] == ["-v", "--verbose"]
        assert opt["is_flag"] is True

    def test_with_value_name_and_default(self):
        opt = _parse_clap_flag("  -c, --config <PATH>  Config file path [default: hello.toml]")
        assert opt is not None
        assert opt["names"] == ["-c", "--config"]
        assert opt["type"] == "path"
        assert opt["default"] == "hello.toml"
        assert opt["is_flag"] is False
        assert "Config file path" in opt["help"]

    def test_short_and_long_with_value(self):
        opt = _parse_clap_flag("  -n, --name <NAME>  Name to greet [default: World]")
        assert opt is not None
        assert opt["names"] == ["-n", "--name"]
        assert opt["type"] == "name"
        assert opt["default"] == "World"

    def test_help_flag(self):
        opt = _parse_clap_flag("  -h, --help           Print help")
        assert opt is not None
        assert "--help" in opt["names"]
        assert opt["is_flag"] is True

    def test_version_flag(self):
        opt = _parse_clap_flag("  -V, --version        Print version")
        assert opt is not None
        assert "--version" in opt["names"]

    def test_unparseable_returns_none(self):
        assert _parse_clap_flag("not a flag line") is None
        assert _parse_clap_flag("") is None

    def test_repeatable_flag(self):
        opt = _parse_clap_flag("  -v, --verbose...     Increase verbosity")
        assert opt is not None
        assert "..." in opt["name_display"]


# ---------------------------------------------------------------------------
# _parse_clap_help
# ---------------------------------------------------------------------------

SAMPLE_CLAP_HELP = textwrap.dedent("""\
    A minimal Rust CLI fixture for great-docs testing.

    Usage: hello [OPTIONS] [COMMAND]

    Commands:
      greet    Print a personalised greeting
      version  Print the version

    Options:
      -c, --config <PATH>  Config file path [default: hello.toml]
      -v, --verbose        Enable verbose output
      -h, --help           Print help
      -V, --version        Print version
""")


class TestShortHelp:
    def test_empty(self):
        assert _short_help("") == ""
        assert _short_help("   ") == ""

    def test_short_description_unchanged(self):
        assert _short_help("Fetch from all configured sources") == (
            "Fetch from all configured sources"
        )

    def test_first_sentence_preferred(self):
        desc = "Fetch metrics. Also does other things across many sources and registries."
        assert _short_help(desc) == "Fetch metrics"

    def test_long_first_sentence_truncated_on_word_boundary(self):
        desc = (
            "yamark tracks your formatter's pulse across YAML and Markdown files "
            "collecting daily metrics from many different services "
            "including GitHub, VS Code, and local file systems every day"
        )
        result = _short_help(desc)
        assert result.endswith("...")
        assert len(result) <= 153  # limit (150) + "..."

    def test_no_ellipsis_when_within_limit(self):
        desc = "A single sentence that stays under the character limit for summaries"
        assert not _short_help(desc).endswith("...")


class TestParseClapHelp:
    def test_description_extracted(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        assert "minimal Rust CLI" in result["help"]

    def test_builtin_commands_excluded(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        names = [c["name"] for c in result["commands"]]
        assert "help" not in names

    def test_user_commands_included(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        names = [c["name"] for c in result["commands"]]
        assert "greet" in names
        assert "version" in names

    def test_options_parsed(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        long_names = [n for opt in result["options"] for n in opt["names"]]
        assert "--verbose" in long_names
        assert "--config" in long_names

    def test_option_type_extracted(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        config_opt = next(o for o in result["options"] if "--config" in o["names"])
        assert config_opt["type"] == "path"
        assert config_opt["default"] == "hello.toml"

    def test_boolean_flag_detected(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        verbose_opt = next(o for o in result["options"] if "--verbose" in o["names"])
        assert verbose_opt["is_flag"] is True
        assert verbose_opt["type"] is None

    def test_name_preserved(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        assert result["name"] == "hello"

    def test_help_text_preserved(self):
        result = _parse_clap_help(SAMPLE_CLAP_HELP, "hello", Path("/tmp/bin"), [])
        assert result["help_text"] == SAMPLE_CLAP_HELP

    def test_empty_input(self):
        result = _parse_clap_help("", "myapp", Path("/tmp/bin"), [])
        assert result["name"] == "myapp"
        assert result["commands"] == []
        assert result["options"] == []

    def test_nested_subcommands(self):
        """clap CLIs with nested commands (e.g. ``tool run``) are parsed correctly."""
        help_text = textwrap.dedent("""\
            Manage tools

            Usage: app tool [COMMAND]

            Commands:
              run      Run a tool
              install  Install a tool

            Options:
              -h, --help  Print help
        """)
        result = _parse_clap_help(help_text, "tool", Path("/tmp/bin"), ["tool"], "app tool")
        assert result["full_path"] == "app tool"
        names = [c["name"] for c in result["commands"]]
        assert "run" in names
        assert "install" in names


# ---------------------------------------------------------------------------
# build_rust_binary / introspect_rust_cli (mocked)
# ---------------------------------------------------------------------------


class TestBuildRustBinary:
    def test_returns_none_when_cargo_not_found(self, tmp_path: Path):
        rust_project = RustCliProject(
            project_root=tmp_path,
            package_name="app",
            binary_names=["app"],
            uses_clap=False,
        )
        with patch("great_docs._rust_cli.subprocess.run", side_effect=FileNotFoundError):
            result = build_rust_binary(rust_project, output_dir=tmp_path)
        assert result is None

    def test_returns_none_on_build_failure(self, tmp_path: Path):
        rust_project = RustCliProject(
            project_root=tmp_path,
            package_name="app",
            binary_names=["app"],
            uses_clap=False,
        )
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "build error"
        with patch("great_docs._rust_cli.subprocess.run", return_value=mock_result):
            result = build_rust_binary(rust_project, output_dir=tmp_path)
        assert result is None

    def test_returns_none_on_timeout(self, tmp_path: Path):
        rust_project = RustCliProject(
            project_root=tmp_path,
            package_name="app",
            binary_names=["app"],
            uses_clap=False,
        )
        with patch(
            "great_docs._rust_cli.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="cargo", timeout=300),
        ):
            result = build_rust_binary(rust_project, output_dir=tmp_path)
        assert result is None

    def test_returns_binary_path_on_success(self, tmp_path: Path):
        rust_project = RustCliProject(
            project_root=tmp_path,
            package_name="app",
            binary_names=["app"],
            uses_clap=False,
        )
        # Create the expected binary path so the exists() check passes
        release_dir = tmp_path / "_cargo_target" / "release"
        release_dir.mkdir(parents=True)
        (release_dir / "app").write_text("")

        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("great_docs._rust_cli.subprocess.run", return_value=mock_result):
            result = build_rust_binary(rust_project, output_dir=tmp_path)
        assert result == release_dir / "app"


class TestIntrospectRustCli:
    def test_returns_none_when_build_fails(self, tmp_path: Path):
        rust_project = RustCliProject(
            project_root=tmp_path,
            package_name="app",
            binary_names=["app"],
            uses_clap=False,
        )
        with patch("great_docs._rust_cli.build_rust_binary", return_value=None):
            result = introspect_rust_cli(rust_project)
        assert result is None

    def test_entry_point_name_set_on_success(self, tmp_path: Path):
        binary = tmp_path / "app"
        binary.write_text("")

        rust_project = RustCliProject(
            project_root=tmp_path,
            package_name="app",
            binary_names=["app"],
            uses_clap=False,
        )

        mock_proc = MagicMock()
        mock_proc.stdout = "My CLI tool\n\nUsage: app [COMMAND]\n"
        mock_proc.stderr = ""
        mock_proc.returncode = 0

        with (
            patch("great_docs._rust_cli.build_rust_binary", return_value=binary),
            patch("great_docs._rust_cli.subprocess.run", return_value=mock_proc),
        ):
            result = introspect_rust_cli(rust_project)

        assert result is not None
        assert result["entry_point_name"] == "app"
        assert "My CLI tool" in result["help"]


# ---------------------------------------------------------------------------
# Integration: build + introspect the committed rust_cli_hello fixture
# Requires 'cargo' on PATH; auto-skipped otherwise.
# ---------------------------------------------------------------------------


@requires_cargo
class TestRustHelloFixtureIntegration:
    """End-to-end tests using the committed stdlib-only rust_cli_hello fixture."""

    def test_detect_hello_fixture(self):
        result = detect_rust_cli_project(HELLO_FIXTURE)
        assert result is not None
        assert result.package_name == "hello"

    def test_build_hello_binary(self, tmp_path: Path):
        rust_project = detect_rust_cli_project(HELLO_FIXTURE)
        assert rust_project is not None
        binary = build_rust_binary(rust_project, output_dir=tmp_path)
        assert binary is not None
        assert binary.exists()

    def test_introspect_hello_returns_commands(self):
        rust_project = detect_rust_cli_project(HELLO_FIXTURE)
        assert rust_project is not None
        cli_info = introspect_rust_cli(rust_project)
        assert cli_info is not None
        assert cli_info["entry_point_name"] == "hello"
        names = [c["name"] for c in cli_info["commands"]]
        assert "greet" in names
        assert "version" in names

    def test_introspect_excludes_builtin_commands(self):
        rust_project = detect_rust_cli_project(HELLO_FIXTURE)
        assert rust_project is not None
        cli_info = introspect_rust_cli(rust_project)
        assert cli_info is not None
        names = [c["name"] for c in cli_info["commands"]]
        assert "help" not in names

    def test_binary_produces_help_text(self, tmp_path: Path):
        """The compiled binary should emit meaningful --help output."""
        rust_project = detect_rust_cli_project(HELLO_FIXTURE)
        assert rust_project is not None
        binary = build_rust_binary(rust_project, output_dir=tmp_path)
        assert binary is not None
        result = subprocess.run(
            [str(binary), "--help"], capture_output=True, text=True, timeout=5
        )
        output = result.stdout + result.stderr
        assert "greet" in output
        assert "version" in output
